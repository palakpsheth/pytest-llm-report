# SPDX-License-Identifier: MIT
"""Collector for test outcomes and durations.

This module captures test results via pytest hooks including:
- Test outcomes (passed, failed, skipped, xfailed, xpassed)
- Setup and teardown failures
- Parameter IDs for parametrized tests
- Rerun counts from pytest-rerunfailures
- Collection errors
- LLM markers (opt-out, context override)
- Captured stdout/stderr for failed tests (opt-in)

Component Contract:
    Input: pytest hooks, Config
    Output: list[TestCaseResult], list[CollectionError]
    Dependencies: Config, models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

import pytest

from pytest_llm_report.models import CollectionError, TestCaseResult
from pytest_llm_report.options import Config

if TYPE_CHECKING:
    from _pytest.reports import TestReport


@dataclass
class TestCollector:
    """Collects test outcomes and metadata during a pytest run.

    Attributes:
        config: Plugin configuration.
        results: Collected test results by nodeid.
        collection_errors: Errors during test collection.
        collected_count: Number of tests collected.
        deselected_count: Number of tests deselected.
    """

    config: Config
    results: dict[str, TestCaseResult] = field(default_factory=dict)
    collection_errors: list[CollectionError] = field(default_factory=list)
    collected_count: int = 0
    deselected_count: int = 0
    __test__: ClassVar[bool] = False

    def handle_collection_report(self, report: pytest.CollectReport) -> None:
        """Handle a collection report.

        Args:
            report: pytest collection report.
        """
        if report.failed:
            # Extract first line of error for short summary
            longrepr = str(report.longrepr) if report.longrepr else "Collection failed"
            first_line = longrepr.split("\n")[0][:200]
            self.collection_errors.append(
                CollectionError(
                    nodeid=report.nodeid,
                    message=first_line,
                )
            )

    def handle_collection_finish(
        self, items: list[pytest.Item], deselected: list[pytest.Item] | None = None
    ) -> None:
        """Handle collection finish.

        Args:
            items: Collected test items.
            deselected: Deselected test items (if any).
        """
        self.collected_count = len(items)
        self.deselected_count = len(deselected) if deselected else 0

    def handle_runtest_logreport(
        self, report: TestReport, item: pytest.Item | None = None
    ) -> None:
        """Handle a test report from pytest_runtest_logreport.

        Args:
            report: pytest test report.
            item: Test item (may be None in some cases).
        """
        nodeid = report.nodeid

        # Get or create result
        if nodeid not in self.results:
            self.results[nodeid] = self._create_result(report, item)

        result = self.results[nodeid]

        # Update based on report phase and outcome
        if report.when == "setup":
            if report.failed:
                result.outcome = "error"
                result.phase = "setup"
                result.error_message = self._extract_error(report)
            elif report.skipped:
                # Skip during setup (e.g., @pytest.mark.skip)
                result.outcome = "skipped"
                result.error_message = self._extract_skip_reason(report)

            self._apply_xfail_outcome(report, result)
        elif report.when == "call":
            result.duration = report.duration
            result.phase = "call"

            if report.passed:
                result.outcome = "passed"
            elif report.failed:
                result.outcome = "failed"
                result.error_message = self._extract_error(report)
            elif report.skipped:
                # Check for xfail
                result.outcome = "skipped"
                result.error_message = self._extract_skip_reason(report)

            self._apply_xfail_outcome(report, result)

            # Check for rerun (pytest-rerunfailures)
            if hasattr(report, "rerun"):
                result.rerun_count = getattr(report, "rerun", 0)
                # Set final_outcome to the current outcome (may be updated on future reports)
                result.final_outcome = result.outcome

        elif report.when == "teardown":
            if report.failed and result.outcome == "passed":
                # Teardown failure after passing test
                result.outcome = "error"
                result.phase = "teardown"
                result.error_message = self._extract_error(report)

        # Capture stdout/stderr for failed tests if enabled
        if self.config.capture_failed_output and result.outcome == "failed":
            self._capture_output(result, report)

    def _create_result(
        self, report: TestReport, item: pytest.Item | None = None
    ) -> TestCaseResult:
        """Create a new TestCaseResult for a test.

        Args:
            report: pytest test report.
            item: Test item.

        Returns:
            New TestCaseResult instance.
        """
        result = TestCaseResult(
            nodeid=report.nodeid,
            outcome="pending",
            duration=0.0,
            phase="setup",
        )

        # Extract parameter id if parametrized
        if item and hasattr(item, "callspec"):
            result.param_id = item.callspec.id

        # Extract LLM markers if item is available
        if item:
            self._extract_llm_markers(result, item)
            self._extract_requirements(result, item)

        return result

    def _extract_llm_markers(self, result: TestCaseResult, item: pytest.Item) -> None:
        """Extract LLM-related markers from test item.

        Args:
            result: Test result to update.
            item: Test item.
        """
        # Check for llm_opt_out marker
        if item.get_closest_marker("llm_opt_out"):
            result.llm_opt_out = True

        # Check for llm_context marker
        context_marker = item.get_closest_marker("llm_context")
        if context_marker and context_marker.args:
            mode = context_marker.args[0]
            if mode in ("minimal", "balanced", "complete"):
                result.llm_context_override = mode

    def _extract_requirements(self, result: TestCaseResult, item: pytest.Item) -> None:
        """Extract requirement markers from test item.

        Args:
            result: Test result to update.
            item: Test item.
        """
        req_marker = item.get_closest_marker("requirement")
        if req_marker:
            result.requirements = list(req_marker.args)

    def _apply_xfail_outcome(self, report: TestReport, result: TestCaseResult) -> None:
        """Apply xfail/xpass outcomes based on pytest report flags.

        Args:
            report: pytest test report.
            result: Test result to update.
        """
        if not hasattr(report, "wasxfail"):
            return

        if report.passed:
            result.outcome = "xpassed"
            result.error_message = None
        else:
            result.outcome = "xfailed"

    def _extract_error(self, report: TestReport) -> str:
        """Extract a short error message from a report.

        Args:
            report: pytest test report.

        Returns:
            Short error message (first line, truncated).
        """
        if report.longrepr:
            longrepr = str(report.longrepr)
            # Get first meaningful line
            lines = longrepr.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("E "):
                    continue
                if line.startswith("E "):
                    return line[2:][:200]
            # Fall back to last line
            return lines[-1][:200] if lines else "Test failed"
        return "Test failed"

    def _extract_skip_reason(self, report: TestReport) -> str | None:
        """Extract skip reason from a report.

        Args:
            report: pytest test report.

        Returns:
            Skip reason or None.
        """
        if report.longrepr:
            return str(report.longrepr)[:200]
        return None

    def _capture_output(self, result: TestCaseResult, report: TestReport) -> None:
        """Capture stdout/stderr from a failed test.

        Args:
            result: Test result to update.
            report: pytest test report.
        """
        max_chars = self.config.capture_output_max_chars

        # Capture stdout
        if hasattr(report, "capstdout") and report.capstdout:
            result.captured_stdout = report.capstdout[:max_chars]

        # Capture stderr
        if hasattr(report, "capstderr") and report.capstderr:
            result.captured_stderr = report.capstderr[:max_chars]

    def get_results(self) -> list[TestCaseResult]:
        """Get all collected test results.

        Returns:
            List of test results sorted by nodeid.
        """
        return sorted(self.results.values(), key=lambda r: r.nodeid)

    def get_collection_errors(self) -> list[CollectionError]:
        """Get all collection errors.

        Returns:
            List of collection errors.
        """
        return self.collection_errors
