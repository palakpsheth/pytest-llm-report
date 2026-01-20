# SPDX-License-Identifier: MIT
"""Report writer for assembling and outputting reports.

This module combines test results and coverage data into a
stable JSON report and optionally generates HTML.

Component Contract:
    Input: TestCaseResult list, coverage map, Config
    Output: JSON + HTML files + artifact manifest
    Dependencies: models, render, util.hashing
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pytest_llm_report.__about__ import __version__
from pytest_llm_report.errors import WARNING_MESSAGES, WarningCode
from pytest_llm_report.models import (
    ArtifactEntry,
    ReportRoot,
    ReportWarning,
    RunMeta,
    Summary,
)

if TYPE_CHECKING:
    from pytest_llm_report.models import (
        CollectionError,
        SourceCoverageEntry,
        TestCaseResult,
    )
    from pytest_llm_report.options import Config


def compute_sha256(content: bytes) -> str:
    """Compute SHA256 hash of content.

    Args:
        content: Bytes to hash.

    Returns:
        Hex digest string.
    """
    return hashlib.sha256(content).hexdigest()


def get_git_info(path: str | Path = ".") -> tuple[str | None, bool | None]:
    """Get git commit SHA and dirty flag for a path.

    Args:
        path: Path to run git command in.

    Returns:
        Tuple of (sha, dirty) or (None, None) if git is unavailable.
    """
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(path),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        ).strip()

        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(path),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        dirty = bool(status.strip())
        return sha, dirty
    except Exception:
        return None, None


def get_repo_version(root_path: Path) -> str | None:
    """Get version of the analyzed repository from pyproject.toml.

    Args:
        root_path: Root directory of the repository.

    Returns:
        Version string or None.
    """
    toml_path = root_path / "pyproject.toml"
    if not toml_path.exists():
        return None

    try:
        # Simple parsing to avoid extra dependencies (tomli/tomllib)
        # We look for `version = "x.y.z"` or `[project] ... version = "x.y.z"`
        content = toml_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("version") and "=" in line:
                # version = "1.0.0" -> 1.0.0
                return line.split("=", 1)[1].strip().strip("\"'")
    except Exception:
        pass
    return None


def get_plugin_git_info() -> tuple[str | None, bool | None]:
    """Get git info for the plugin itself.

    Tries to:
    1. Import _git_info (generated at build time).
    2. Check git repo relative to this file (dev mode).

    Returns:
        Tuple of (sha, dirty).
    """
    # 1. Try build-time generated module
    try:
        from pytest_llm_report import _git_info

        return _git_info.GIT_SHA, _git_info.GIT_DIRTY
    except ImportError:
        pass

    # 2. Try git runtime (dev mode)
    try:
        here = Path(__file__).parent
        return get_git_info(here)
    except Exception:
        return None, None


class ReportWriter:
    """Assembles and writes test reports.

    Attributes:
        config: Plugin configuration.
        warnings: Warnings generated during report assembly.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the report writer.

        Args:
            config: Plugin configuration.
        """
        self.config = config
        self.warnings: list[ReportWarning] = []
        self.artifacts: list[ArtifactEntry] = []

    def write_report(
        self,
        tests: list[TestCaseResult],
        coverage: dict[str, list] | None = None,
        coverage_percent: float | None = None,
        source_coverage: list[SourceCoverageEntry] | None = None,
        collection_errors: list[CollectionError] | None = None,
        exit_code: int = 0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        llm_info: dict | None = None,
    ) -> ReportRoot:
        """Assemble and write the report.

        Args:
            tests: List of test results.
            coverage: Coverage mapping by nodeid.
            collection_errors: Collection errors.
            exit_code: pytest exit code.
            start_time: Session start time.
            end_time: Session end time.

        Returns:
            The assembled ReportRoot.
        """
        # Merge coverage into tests
        if coverage:
            for test in tests:
                if test.nodeid in coverage:
                    test.coverage = coverage[test.nodeid]

        # Build run metadata
        run_meta = self._build_run_meta(
            tests, exit_code, start_time, end_time, llm_info
        )

        # Build summary
        summary = self._build_summary(tests)
        if coverage_percent is not None:
            summary.coverage_total_percent = coverage_percent

        # Warn if no tests were collected
        if summary.total == 0:
            self.warnings.append(
                ReportWarning(
                    code="W100",
                    message="No tests were collected. Report may be empty.",
                )
            )

        # Assemble report
        report = ReportRoot(
            run_meta=run_meta,
            summary=summary,
            tests=tests,
            collection_errors=collection_errors or [],
            warnings=self.warnings,
            artifacts=self.artifacts,
            source_coverage=source_coverage or [],
        )

        # Write JSON
        if self.config.report_json:
            self.write_json(report, self.config.report_json)

        # Write HTML
        if self.config.report_html:
            self.write_html(report, self.config.report_html)

        # Write PDF
        if self.config.report_pdf:
            self.write_pdf(report, self.config.report_pdf)

        return report

    def _build_run_meta(
        self,
        tests: list[TestCaseResult],
        exit_code: int,
        start_time: datetime | None,
        end_time: datetime | None,
        llm_info: dict | None = None,
    ) -> RunMeta:
        """Build run metadata.

        Args:
            tests: List of test results.
            exit_code: pytest exit code.
            start_time: Session start time.
            end_time: Session end time.

        Returns:
            RunMeta instance.
        """
        import pytest

        now = datetime.now(UTC)
        start = start_time or now
        end = end_time or now
        duration = (end - start).total_seconds()

        # repo_root should be set by plugin, but fallback to "." if not
        root = self.config.repo_root or Path(".")
        repo_sha, repo_dirty = get_git_info(root)
        repo_version = get_repo_version(root)

        plugin_sha, plugin_dirty = get_plugin_git_info()

        return RunMeta(
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            duration=duration,
            pytest_version=pytest.__version__,
            plugin_version=__version__,
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            # Legacy fields (mapped to repo info for compat)
            git_sha=repo_sha,
            git_dirty=repo_dirty,
            # New distinct fields
            repo_version=repo_version,
            repo_git_sha=repo_sha,
            repo_git_dirty=repo_dirty,
            plugin_git_sha=plugin_sha,
            plugin_git_dirty=plugin_dirty,
            exit_code=exit_code,
            collected_count=len(tests),
            selected_count=len(tests),
            run_id=self.config.aggregate_run_id,
            run_group_id=self.config.aggregate_group_id,
            # LLM traceability fields
            llm_provider=llm_info.get("provider") if llm_info else None,
            llm_model=llm_info.get("model") if llm_info else None,
            llm_context_mode=llm_info.get("context_mode") if llm_info else None,
            llm_annotations_enabled=bool(llm_info),
            llm_annotations_count=llm_info.get("annotations_count")
            if llm_info
            else None,
            llm_annotations_errors=llm_info.get("annotations_errors")
            if llm_info
            else None,
            llm_total_input_tokens=llm_info.get("total_input_tokens")
            if llm_info
            else None,
            llm_total_output_tokens=llm_info.get("total_output_tokens")
            if llm_info
            else None,
            llm_total_tokens=llm_info.get("total_tokens") if llm_info else None,
        )

    def _build_summary(self, tests: list[TestCaseResult]) -> Summary:
        """Build summary statistics.

        Args:
            tests: List of test results.

        Returns:
            Summary instance.
        """
        summary = Summary(total=len(tests))

        for test in tests:
            summary.total_duration += test.duration

            if test.outcome == "passed":
                summary.passed += 1
            elif test.outcome == "failed":
                summary.failed += 1
            elif test.outcome == "skipped":
                summary.skipped += 1
            elif test.outcome == "xfailed":
                summary.xfailed += 1
            elif test.outcome == "xpassed":
                summary.xpassed += 1
            elif test.outcome == "error":
                summary.error += 1

        return summary

    def write_json(self, report: ReportRoot, path: str) -> None:
        """Write JSON report to file.

        Args:
            report: Report to write.
            path: Output path.
        """
        # Ensure directory exists
        self._ensure_dir(path)

        # Serialize to JSON
        report_dict = report.to_dict()
        json_content = json.dumps(report_dict, indent=2, sort_keys=True)
        json_bytes = json_content.encode("utf-8")

        # Compute hash
        sha256 = compute_sha256(json_bytes)
        report.sha256 = sha256

        # Re-serialize with hash included
        report_dict["sha256"] = sha256
        json_content = json.dumps(report_dict, indent=2, sort_keys=True)
        json_bytes = json_content.encode("utf-8")

        # Write atomically
        self._atomic_write(path, json_bytes)

        # Track artifact
        self.artifacts.append(
            ArtifactEntry(
                path=path,
                sha256=sha256,
                size_bytes=len(json_bytes),
            )
        )

    def write_html(self, report: ReportRoot, path: str) -> None:
        """Write HTML report to file.

        Args:
            report: Report to write.
            path: Output path.
        """
        # Import render lazily to avoid circular import
        from pytest_llm_report.render import render_html

        html_content = render_html(report)
        html_bytes = html_content.encode("utf-8")

        # Ensure directory exists
        self._ensure_dir(path)

        # Compute hash
        sha256 = compute_sha256(html_bytes)

        # Write atomically
        self._atomic_write(path, html_bytes)

        # Track artifact
        self.artifacts.append(
            ArtifactEntry(
                path=path,
                sha256=sha256,
                size_bytes=len(html_bytes),
            )
        )

    def write_pdf(self, report: ReportRoot, path: str) -> None:
        """Write PDF report to file using Playwright."""
        if importlib.util.find_spec("playwright.sync_api") is None:
            self.warnings.append(
                ReportWarning(
                    code=WarningCode.W204_PDF_PLAYWRIGHT_MISSING.value,
                    message=WARNING_MESSAGES[WarningCode.W204_PDF_PLAYWRIGHT_MISSING],
                )
            )
            return

        from playwright.sync_api import sync_playwright

        self._ensure_dir(path)

        html_path, is_temp = self._resolve_pdf_html_source(report)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.goto(f"{html_path.resolve().as_uri()}?pdf=1")
                page.wait_for_load_state("networkidle")
                page.emulate_media(media="print")
                page.pdf(path=path, format="A4", print_background=True)
                browser.close()
        except Exception as exc:
            self.warnings.append(
                ReportWarning(
                    code=WarningCode.W201_OUTPUT_PATH_INVALID.value,
                    message=WARNING_MESSAGES[WarningCode.W201_OUTPUT_PATH_INVALID],
                    detail=str(exc),
                )
            )
            return
        finally:
            if is_temp:
                html_path.unlink(missing_ok=True)

        pdf_bytes = Path(path).read_bytes()
        sha256 = compute_sha256(pdf_bytes)
        self.artifacts.append(
            ArtifactEntry(
                path=path,
                sha256=sha256,
                size_bytes=len(pdf_bytes),
            )
        )

    def _resolve_pdf_html_source(self, report: ReportRoot) -> tuple[Path, bool]:
        if self.config.report_html:
            html_path = Path(self.config.report_html)
            if html_path.exists():
                return html_path, False

        from pytest_llm_report.render import render_html

        html_content = render_html(report)
        # Use a temporary file that we can write to and get the path of.
        # It will be cleaned up by the `write_pdf` method.
        with tempfile.NamedTemporaryFile(
            "w", suffix=".html", delete=False, encoding="utf-8"
        ) as f:
            f.write(html_content)
        return Path(f.name), True

    def _ensure_dir(self, path: str) -> None:
        """Ensure the directory for a path exists.

        Args:
            path: File path.
        """
        dir_path = Path(path).parent
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                self.warnings.append(
                    ReportWarning(
                        code="W202",
                        message=f"Created directory: {dir_path}",
                    )
                )
            except OSError as e:
                self.warnings.append(
                    ReportWarning(
                        code="W201",
                        message=f"Failed to create directory: {e}",
                    )
                )

    def _atomic_write(self, path: str, content: bytes) -> None:
        """Write content atomically (temp file then rename).

        Args:
            path: Target file path.
            content: Content to write.
        """
        dir_path = Path(path).parent

        try:
            # Write to temp file in same directory
            fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
            try:
                os.write(fd, content)
            finally:
                os.close(fd)

            # Rename atomically
            os.replace(temp_path, path)
        except OSError:
            # Fall back to direct write
            self.warnings.append(
                ReportWarning(
                    code="W203",
                    message="Atomic write failed, using direct write",
                )
            )
            with open(path, "wb") as f:
                f.write(content)
