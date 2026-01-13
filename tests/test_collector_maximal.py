# SPDX-License-Identifier: MIT
from unittest.mock import MagicMock

from pytest_llm_report.collector import TestCollector
from pytest_llm_report.options import Config


class TestCollectorMaximal:
    """Maximum coverage for TestCollector."""

    def test_handle_collection_report_failure(self):
        config = Config()
        collector = TestCollector(config)

        report = MagicMock()
        # Ensure it doesn't have attributes we don't want
        del report.wasxfail
        report.nodeid = "root"
        report.failed = True
        report.skipped = False
        report.longrepr = "Error: some collection error\nIn some file"

        collector.handle_collection_report(report)

        assert len(collector.collection_errors) == 1
        assert "Error: some collection error" in collector.collection_errors[0].message

    def test_handle_runtest_skipped_in_call(self):
        config = Config()
        collector = TestCollector(config)

        report = MagicMock()
        del report.wasxfail
        report.nodeid = "test_skip"
        report.when = "call"
        report.passed = False
        report.failed = False
        report.skipped = True
        report.duration = 0.5
        report.longrepr = "Skipped: manually"

        collector.handle_runtest_logreport(report)

        result = collector.results["test_skip"]
        assert result.outcome == "skipped"
        assert "manually" in result.error_message

    def test_handle_teardown_failure(self):
        config = Config()
        collector = TestCollector(config)

        # First it passes
        report_pass = MagicMock()
        del report_pass.wasxfail
        report_pass.nodeid = "test_tear"
        report_pass.when = "call"
        report_pass.passed = True
        report_pass.failed = False
        report_pass.skipped = False
        report_pass.duration = 0.1
        collector.handle_runtest_logreport(report_pass)

        # Then teardown fails
        report_tear = MagicMock()
        del report_tear.wasxfail
        report_tear.nodeid = "test_tear"
        report_tear.when = "teardown"
        report_tear.passed = False
        report_tear.failed = True
        report_tear.skipped = False
        report_tear.longrepr = "E Teardown failed"
        collector.handle_runtest_logreport(report_tear)

        result = collector.results["test_tear"]
        assert result.outcome == "error"
        assert result.phase == "teardown"

    def test_capture_output_on_failure(self):
        config = Config(capture_failed_output=True)
        collector = TestCollector(config)

        report = MagicMock()
        del report.wasxfail
        report.nodeid = "test_out"
        report.when = "call"
        report.passed = False
        report.failed = True
        report.skipped = False
        report.capstdout = "some stdout output"
        report.capstderr = "some stderr output"
        report.longrepr = "E AssertionError"

        collector.handle_runtest_logreport(report)

        result = collector.results["test_out"]
        assert result.captured_stdout == "some stdout output"
        assert result.captured_stderr == "some stderr output"

    def test_extract_error_loop_coverage(self):
        config = Config()
        collector = TestCollector(config)

        # Test the loop in _extract_error by providing multiple lines,
        # some starting with E and some not.
        report = MagicMock()
        report.longrepr = "Some intro text\nMore text\nE Actual Error message"

        msg = collector._extract_error(report)
        assert msg == "Actual Error message"

        # Test fallback
        report.longrepr = "One line"
        assert collector._extract_error(report) == "One line"

    def test_rerun_count_coverage(self):
        config = Config()
        collector = TestCollector(config)

        report = MagicMock()
        del report.wasxfail
        report.nodeid = "test_rerun"
        report.when = "call"
        report.passed = False
        report.failed = True
        report.skipped = False
        report.longrepr = "fail"
        report.rerun = 2

        collector.handle_runtest_logreport(report)

        result = collector.results["test_rerun"]
        assert result.rerun_count == 2
        assert result.final_outcome == "failed"
