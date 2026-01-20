# SPDX-License-Identifier: MIT
"""Coverage data ingestion and context mapping.

This module reads .coverage files and maps test contexts to
file and line ranges using coverage.py APIs.

Component Contract:
    Input: .coverage file(s), Config
    Output: dict[nodeid, list[CoverageEntry]]
    Dependencies: coverage.py, Config, util.ranges, util.fs
"""

from __future__ import annotations

import glob
from pathlib import Path
from typing import TYPE_CHECKING, cast

from pytest_llm_report.errors import WarningCode, make_warning
from pytest_llm_report.models import CoverageEntry, ReportWarning, SourceCoverageEntry
from pytest_llm_report.util.fs import make_relative, normalize_path, should_skip_path
from pytest_llm_report.util.ranges import compress_ranges

if TYPE_CHECKING:
    from coverage import Coverage, CoverageData

    from pytest_llm_report.options import Config


class CoverageMapper:
    """Maps coverage contexts to per-test coverage entries.

    Attributes:
        config: Plugin configuration.
        warnings: Warnings generated during mapping.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the coverage mapper.

        Args:
            config: Plugin configuration.
        """
        self.config = config
        self.warnings: list[ReportWarning] = []

    def map_coverage(
        self, data: CoverageData | None = None
    ) -> dict[str, list[CoverageEntry]]:
        """Map coverage data to per-test entries.

        Args:
            data: Optional CoverageData to use instead of loading from disk.

        Returns:
            Dictionary mapping nodeids to coverage entries.
        """
        coverage_data = data or self._load_coverage_data()
        if coverage_data is None:
            return {}

        return self._extract_contexts(coverage_data)

    def _load_coverage_data(self) -> CoverageData | None:
        """Load coverage data from .coverage file(s).

        Handles xdist/parallel mode by combining .coverage.* files.

        Returns:
            CoverageData instance, or None if not available.
        """
        try:
            from coverage import CoverageData
        except ImportError:
            self.warnings.append(
                ReportWarning(
                    code=WarningCode.W001_NO_COVERAGE.value,
                    message="coverage.py not installed",
                )
            )
            return None

        coverage_file = Path.cwd() / ".coverage"

        # Check for parallel mode files
        parallel_files = list(glob.glob(".coverage.*"))

        if not coverage_file.exists() and not parallel_files:
            self.warnings.append(make_warning(WarningCode.W001_NO_COVERAGE))
            return None

        try:
            # Initialize with the main coverage file if it exists
            if coverage_file.exists():
                data = CoverageData(basename=str(coverage_file))
                data.read()
            else:
                data = CoverageData()

            # Combine parallel files (xdist mode)
            for pfile in parallel_files:
                pdata = CoverageData(basename=pfile)
                pdata.read()
                data.update(pdata)

            return data
        except Exception as e:
            self.warnings.append(
                ReportWarning(
                    code=WarningCode.W001_NO_COVERAGE.value,
                    message=f"Failed to read coverage data: {e}",
                )
            )
            return None

    def _extract_contexts(self, data: CoverageData) -> dict[str, list[CoverageEntry]]:
        """Extract per-test coverage from coverage data."""
        result: dict[str, list[CoverageEntry]] = {}

        # Get all measured files
        try:
            measured_files = data.measured_files()
        except AttributeError:
            # Older coverage.py API
            measured_files = cast(set[str], getattr(data, "_lines", {}).keys())

        if not measured_files:
            return result

        # Check if contexts are available
        has_contexts = False
        for path in measured_files:
            try:
                contexts = data.contexts_by_lineno(path)
                if contexts:
                    # check if contexts are not empty strings
                    non_empty = [c for lines in contexts.values() for c in lines if c]
                    if non_empty:
                        has_contexts = True
                        break
            except Exception:
                continue

        if not has_contexts:
            self.warnings.append(make_warning(WarningCode.W002_NO_CONTEXTS))
            return result

        repo_root = self.config.repo_root or Path.cwd()

        for file_path in measured_files:
            # Skip non-Python files
            if not file_path.endswith(".py"):
                continue

            # Skip excluded paths
            if should_skip_path(file_path):
                continue

            # Skip test files if configured
            if self.config.omit_tests_from_coverage:
                norm_path = normalize_path(file_path)
                if "test" in norm_path and (
                    norm_path.startswith("test") or "/test" in norm_path
                ):
                    continue

            try:
                contexts = data.contexts_by_lineno(file_path)
            except Exception:
                continue

            # Make path relative to repo root
            rel_path = make_relative(file_path, repo_root)

            # Group lines by nodeid
            nodeid_lines: dict[str, list[int]] = {}

            for line_no, line_contexts in contexts.items():
                for ctx in line_contexts:
                    nodeid = self._extract_nodeid(ctx)
                    if nodeid:
                        if nodeid not in nodeid_lines:
                            nodeid_lines[nodeid] = []
                        nodeid_lines[nodeid].append(line_no)

            # Create coverage entries
            for nodeid, lines in nodeid_lines.items():
                if nodeid not in result:
                    result[nodeid] = []

                entry = CoverageEntry(
                    file_path=rel_path,
                    line_ranges=compress_ranges(lines),
                    line_count=len(lines),
                )
                result[nodeid].append(entry)

        # Sort entries by file path
        for nodeid in result:
            result[nodeid].sort(key=lambda e: e.file_path)

        return result

    def _extract_nodeid(self, context: str) -> str | None:
        """Extract nodeid from a coverage context.

        Contexts are typically in format "nodeid|phase" (e.g., "test.py::test_foo|run").
        We prefer the "run" phase.

        Args:
            context: Coverage context string.

        Returns:
            Extracted nodeid, or None if not applicable.
        """
        if not context:
            return None

        # Skip empty context
        if context == "":
            return None

        # Parse context
        if "|" in context:
            nodeid, phase = context.rsplit("|", 1)

            # Filter by phase if configured
            include_phase = self.config.include_phase
            if include_phase == "run" and phase != "run":
                return None
            if include_phase == "setup" and phase != "setup":
                return None
            if include_phase == "teardown" and phase != "teardown":
                return None

            return nodeid

        # Context without phase delimiter
        return context

    def map_source_coverage(self, cov: Coverage) -> list[SourceCoverageEntry]:
        """Build per-file coverage summary from a Coverage instance."""
        entries: list[SourceCoverageEntry] = []
        repo_root = self.config.repo_root or Path.cwd()

        measured_files = cov.get_data().measured_files()
        for file_path in measured_files:
            if not file_path.endswith(".py"):
                continue
            if should_skip_path(file_path):
                continue
            if self.config.omit_tests_from_coverage:
                norm_path = normalize_path(file_path)
                if "test" in norm_path and (
                    norm_path.startswith("test") or "/test" in norm_path
                ):
                    continue

            try:
                _filename, statements, _excluded, missing, _missing_branches = (
                    cov.analysis2(file_path)
                )
            except Exception as e:
                self.warnings.append(
                    ReportWarning(
                        code="COVERAGE_ANALYSIS_FAILED",
                        message=f"Failed to analyze coverage for {file_path}",
                        detail=str(e),
                    )
                )
                continue

            if not statements:
                continue

            statement_set = set(statements)
            missing_set = set(missing)
            covered_lines = sorted(statement_set - missing_set)
            missed_lines = sorted(missing_set)

            covered = len(covered_lines)
            total = len(statements)
            coverage_percent = round((covered / total) * 100, 2) if total else 0.0

            entries.append(
                SourceCoverageEntry(
                    file_path=make_relative(file_path, repo_root),
                    statements=total,
                    missed=len(missed_lines),
                    covered=covered,
                    coverage_percent=coverage_percent,
                    covered_ranges=compress_ranges(covered_lines)
                    if covered_lines
                    else "",
                    missed_ranges=compress_ranges(missed_lines) if missed_lines else "",
                )
            )

        entries.sort(key=lambda entry: entry.file_path)
        return entries

    def get_warnings(self) -> list[ReportWarning]:
        """Get warnings generated during mapping.

        Returns:
            List of warning dictionaries.
        """
        return self.warnings
