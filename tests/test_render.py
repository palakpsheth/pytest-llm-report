# SPDX-License-Identifier: MIT
"""Tests for pytest_llm_report.render module."""

from pytest_llm_report.models import (
    CoverageEntry,
    LlmAnnotation,
    ReportRoot,
    RunMeta,
    Summary,
    TestCaseResult,
)
from pytest_llm_report.render import (
    format_duration,
    outcome_to_css_class,
    render_fallback_html,
)


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_seconds(self):
        """Should format as seconds for >= 1s."""
        assert format_duration(1.23) == "1.23s"
        assert format_duration(60.0) == "60.00s"

    def test_milliseconds(self):
        """Should format as milliseconds for < 1s."""
        assert format_duration(0.5) == "500ms"
        assert format_duration(0.001) == "1ms"
        assert format_duration(0.0) == "0ms"


class TestOutcomeToCssClass:
    """Tests for outcome_to_css_class function."""

    def test_all_outcomes(self):
        """All outcomes should map to CSS classes."""
        assert outcome_to_css_class("passed") == "outcome-passed"
        assert outcome_to_css_class("failed") == "outcome-failed"
        assert outcome_to_css_class("skipped") == "outcome-skipped"
        assert outcome_to_css_class("xfailed") == "outcome-xfailed"
        assert outcome_to_css_class("xpassed") == "outcome-xpassed"
        assert outcome_to_css_class("error") == "outcome-error"

    def test_unknown_outcome(self):
        """Unknown outcome should get default class."""
        assert outcome_to_css_class("unknown") == "outcome-unknown"


class TestRenderFallbackHtml:
    """Tests for render_fallback_html function."""

    def test_renders_basic_report(self):
        """Should render a complete HTML document."""
        report = ReportRoot(
            run_meta=RunMeta(
                end_time="2024-01-01T12:00:00",
                duration=5.0,
            ),
            summary=Summary(total=2, passed=1, failed=1),
            tests=[
                TestCaseResult(nodeid="test::passed", outcome="passed", duration=0.5),
                TestCaseResult(
                    nodeid="test::failed",
                    outcome="failed",
                    duration=1.5,
                    error_message="AssertionError",
                ),
            ],
        )

        html = render_fallback_html(report)

        assert "<!DOCTYPE html>" in html
        assert "Test Report" in html
        assert "test::passed" in html
        assert "test::failed" in html
        assert "PASSED" in html
        assert "FAILED" in html

    def test_renders_coverage(self):
        """Should include coverage information."""
        report = ReportRoot(
            run_meta=RunMeta(end_time="2024-01-01"),
            summary=Summary(total=1, passed=1),
            tests=[
                TestCaseResult(
                    nodeid="test::foo",
                    outcome="passed",
                    coverage=[
                        CoverageEntry(
                            file_path="src/foo.py", line_ranges="1-5", line_count=5
                        )
                    ],
                ),
            ],
        )

        html = render_fallback_html(report)

        assert "src/foo.py" in html
        assert "5 lines" in html

    def test_renders_llm_annotation(self):
        """Should include LLM annotations."""
        report = ReportRoot(
            run_meta=RunMeta(end_time="2024-01-01"),
            summary=Summary(total=1, passed=1),
            tests=[
                TestCaseResult(
                    nodeid="test::foo",
                    outcome="passed",
                    llm_annotation=LlmAnnotation(
                        scenario="Tests login flow",
                        why_needed="Prevents auth bypass",
                    ),
                ),
            ],
        )

        html = render_fallback_html(report)

        assert "Tests login flow" in html
        assert "Prevents auth bypass" in html

    def test_renders_xpass_summary(self):
        """Should include xfailed/xpassed summary entries."""
        report = ReportRoot(
            run_meta=RunMeta(end_time="2024-01-01"),
            summary=Summary(total=2, xfailed=1, xpassed=1),
            tests=[
                TestCaseResult(nodeid="test::xfail", outcome="xfailed"),
                TestCaseResult(nodeid="test::xpass", outcome="xpassed"),
            ],
        )

        html = render_fallback_html(report)

        assert "XFailed" in html
        assert "XPassed" in html
