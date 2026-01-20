# SPDX-License-Identifier: MIT
"""LLM context assembly.

Assembles context for LLM prompts based on test coverage and
configuration. Supports minimal, balanced, and complete modes.

Component Contract:
    Input: TestCaseResult, coverage, Config
    Output: dict of file paths to content
    Dependencies: Config, models
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_llm_report.models import TestCaseResult
    from pytest_llm_report.options import Config


class ContextAssembler:
    """Assembles context for LLM prompts."""

    def __init__(self, config: Config) -> None:
        """Initialize the context assembler.

        Args:
            config: Plugin configuration.
        """
        self.config = config

    def assemble(
        self,
        test: TestCaseResult,
        repo_root: Path | None = None,
    ) -> tuple[str, dict[str, str]]:
        """Assemble context for a test.

        Args:
            test: Test result with coverage info.
            repo_root: Repository root path.

        Returns:
            Tuple of (test_source, context_files).
        """
        repo_root = repo_root or self.config.repo_root or Path.cwd()

        # Get test source
        test_source = self._get_test_source(test.nodeid, repo_root)

        # Determine context mode
        mode = test.llm_context_override or self.config.llm_context_mode

        # Get context files based on mode
        if mode == "minimal":
            context_files = {}
        elif mode == "balanced":
            context_files = self._get_balanced_context(test, repo_root)
        else:  # complete
            context_files = self._get_complete_context(test, repo_root)

        return test_source, context_files

    def _get_test_source(self, nodeid: str, repo_root: Path) -> str:
        """Extract test function source from nodeid.

        Args:
            nodeid: Test nodeid.
            repo_root: Repository root.

        Returns:
            Test function source code.
        """
        # Parse nodeid: path/to/test.py::TestClass::test_method
        parts = nodeid.split("::")
        if not parts:
            return ""

        file_path = repo_root / parts[0]
        if not file_path.exists():
            return ""

        try:
            source = file_path.read_text()
        except Exception:
            return ""

        # Find the test function
        test_name = parts[-1]
        # Remove any [param] suffix
        if "[" in test_name:
            test_name = test_name.split("[")[0]

        # Simple extraction: find def test_name
        lines = source.split("\n")
        in_func = False
        func_lines = []
        indent = None

        for line in lines:
            if f"def {test_name}(" in line:
                in_func = True
                indent = len(line) - len(line.lstrip())
                func_lines.append(line)
            elif in_func:
                if line.strip() == "":
                    func_lines.append(line)
                elif line.startswith(" " * (indent + 1)) or line.startswith("\t"):
                    func_lines.append(line)
                else:
                    break

        return "\n".join(func_lines)

    def _get_balanced_context(
        self, test: TestCaseResult, repo_root: Path
    ) -> dict[str, str]:
        """Get balanced context from coverage.

        Includes files covered by the test, limited by config.
        Uses line-range extraction for compression when enabled.

        Args:
            test: Test result.
            repo_root: Repository root.

        Returns:
            Dict of file paths to content.
        """
        if not test.coverage:
            return {}

        context = {}
        total_bytes = 0
        max_bytes = self.config.llm_context_bytes
        max_files = self.config.llm_context_file_limit

        # Check for compression mode
        compression_mode = getattr(self.config, "context_compression", "none")
        line_padding = getattr(self.config, "context_line_padding", 2)

        for entry in test.coverage[:max_files]:
            if total_bytes >= max_bytes:
                break

            file_path = repo_root / entry.file_path
            if not file_path.exists():
                continue

            if self._should_exclude(entry.file_path):
                continue

            try:
                full_content = file_path.read_text()
                lines = full_content.split("\n")

                # Apply compression if enabled and we have line range info
                if (
                    compression_mode == "lines"
                    and hasattr(entry, "lines")
                    and entry.lines
                ):
                    content = self._extract_covered_lines(
                        lines, entry.lines, line_padding
                    )
                else:
                    content = full_content

                # Truncate if needed
                remaining = max_bytes - total_bytes
                if len(content) > remaining:
                    content = content[:remaining] + "\n# ... truncated"

                context[entry.file_path] = content
                total_bytes += len(content)
            except Exception:
                continue

        return context

    def _extract_covered_lines(
        self, lines: list[str], covered_lines: set[int] | list[int], padding: int = 2
    ) -> str:
        """Extract only covered lines with padding for context.

        Args:
            lines: All lines in the file.
            covered_lines: Set/list of 1-indexed line numbers that were covered.
            padding: Number of context lines to include around covered lines.

        Returns:
            Extracted content with line numbers as comments.
        """
        if not covered_lines:
            return ""

        covered_set = set(covered_lines)
        total_lines = len(lines)

        # Expand covered lines with padding
        expanded_lines: set[int] = set()
        for line_num in covered_set:
            for offset in range(-padding, padding + 1):
                adj_line = line_num + offset
                if 1 <= adj_line <= total_lines:
                    expanded_lines.add(adj_line)

        # Sort and group into contiguous ranges
        sorted_lines = sorted(expanded_lines)
        if not sorted_lines:
            return ""

        result_parts: list[str] = []
        current_range_start = sorted_lines[0]
        prev_line = sorted_lines[0]

        for line_num in sorted_lines[1:] + [sorted_lines[-1] + 2]:  # sentinel
            if line_num - prev_line > 1:
                # End of a range, add lines
                if result_parts:
                    result_parts.append("# ...")  # Gap indicator
                for ln in range(current_range_start, prev_line + 1):
                    result_parts.append(f"# L{ln}: {lines[ln - 1]}")
                current_range_start = line_num
            prev_line = line_num

        return "\n".join(result_parts)

    def _get_complete_context(
        self, test: TestCaseResult, repo_root: Path
    ) -> dict[str, str]:
        """Get complete context from coverage.

        Includes all covered files up to limits.

        Args:
            test: Test result.
            repo_root: Repository root.

        Returns:
            Dict of file paths to content.
        """
        # Same as balanced but with higher limits
        return self._get_balanced_context(test, repo_root)

    def _should_exclude(self, path: str) -> bool:
        """Check if a path should be excluded from context.

        Args:
            path: File path to check.

        Returns:
            True if path should be excluded.
        """
        for pattern in self.config.llm_context_exclude_globs:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False
