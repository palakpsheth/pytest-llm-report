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
from pytest_llm_report.models import (
    ArtifactEntry,
    ReportRoot,
    ReportWarning,
    RunMeta,
    Summary,
)

if TYPE_CHECKING:
    from pytest_llm_report.models import CollectionError, TestCaseResult
    from pytest_llm_report.options import Config


def compute_sha256(content: bytes) -> str:
    """Compute SHA256 hash of content.

    Args:
        content: Bytes to hash.

    Returns:
        Hex digest string.
    """
    return hashlib.sha256(content).hexdigest()


def get_git_info() -> tuple[str | None, bool | None]:
    """Get git commit SHA and dirty flag.

    Returns:
        Tuple of (sha, dirty) or (None, None) if git is unavailable.
    """
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,  # Prevent hanging on slow/network-mounted repos
        ).strip()

        # Check for uncommitted changes
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,  # Prevent hanging
        )
        dirty = bool(status.strip())

        return sha, dirty
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
        collection_errors: list[CollectionError] | None = None,
        exit_code: int = 0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
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
        run_meta = self._build_run_meta(tests, exit_code, start_time, end_time)

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
        )

        # Write JSON
        if self.config.report_json:
            self._write_json(report, self.config.report_json)

        # Write HTML
        if self.config.report_html:
            self._write_html(report, self.config.report_html)

        return report

    def _build_run_meta(
        self,
        tests: list[TestCaseResult],
        exit_code: int,
        start_time: datetime | None,
        end_time: datetime | None,
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

        git_sha, git_dirty = get_git_info()

        return RunMeta(
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            duration=duration,
            pytest_version=pytest.__version__,
            plugin_version=__version__,
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            git_sha=git_sha,
            git_dirty=git_dirty,
            exit_code=exit_code,
            collected_count=len(tests),
            selected_count=len(tests),
            run_id=self.config.aggregate_run_id,
            run_group_id=self.config.aggregate_group_id,
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

    def _write_json(self, report: ReportRoot, path: str) -> None:
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

    def _write_html(self, report: ReportRoot, path: str) -> None:
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
