# SPDX-License-Identifier: MIT
"""Tests for collector module."""

from unittest.mock import MagicMock

from pytest_llm_report.collector import TestCollector
from pytest_llm_report.models import TestCaseResult
from pytest_llm_report.options import Config


class TestCollectorInternals:
    """Tests for internal processing logic of TestCollector."""

    def test_extract_error_string(self):
        """Should return string longrepr directly."""
        config = Config()
        collector = TestCollector(config)
        report = MagicMock()
        report.longrepr = "Some error occurred"
        assert collector._extract_error(report) == "Some error occurred"

    def test_extract_error_repr_crash(self):
        """Should handle ReprFileLocation causing crash report."""
        config = Config()
        collector = TestCollector(config)
        report = MagicMock()
        # Simulate ReprFileLocation behavior where str() might be used
        report.longrepr = MagicMock()
        report.longrepr.__str__.return_value = "Crash report"
        assert collector._extract_error(report) == "Crash report"

    def test_extract_skip_reason_tuple(self):
        """Should extract skip message from tuple longrepr."""
        config = Config()
        collector = TestCollector(config)
        report = MagicMock()
        # (file, line, message)
        report.longrepr = ("test_file.py", 10, "Skipped for reason")
        # Implementation just uses str() on the tuple
        assert str(report.longrepr) in collector._extract_skip_reason(report)

    def test_extract_skip_reason_string(self):
        """Should return string longrepr as skip reason."""
        config = Config()
        collector = TestCollector(config)
        report = MagicMock()
        report.longrepr = "Just skipped"
        assert collector._extract_skip_reason(report) == "Just skipped"

    def test_extract_skip_reason_fallback(self):
        """Should return None if no longrepr."""
        config = Config()
        collector = TestCollector(config)
        report = MagicMock()
        report.longrepr = None
        assert collector._extract_skip_reason(report) is None

    def test_capture_output_stdout(self):
        """Should capture stdout."""
        config = Config(capture_failed_output=True)
        collector = TestCollector(config)
        result = TestCaseResult(nodeid="t", outcome="failed")
        report = MagicMock()
        report.capstdout = "Some output"
        report.capstderr = ""

        collector._capture_output(result, report)
        assert result.captured_stdout == "Some output"

    def test_capture_output_stderr(self):
        """Should capture stderr."""
        config = Config(capture_failed_output=True)
        collector = TestCollector(config)
        result = TestCaseResult(nodeid="t", outcome="failed")
        report = MagicMock()
        report.capstdout = ""
        report.capstderr = "Some error"

        collector._capture_output(result, report)
        assert result.captured_stderr == "Some error"

    def test_capture_output_truncated(self):
        """Should truncate output exceeding max chars."""
        config = Config(capture_failed_output=True, capture_output_max_chars=10)
        collector = TestCollector(config)
        result = TestCaseResult(nodeid="t", outcome="failed")
        report = MagicMock()
        report.capstdout = "123456789012345"
        report.capstderr = ""

        collector._capture_output(result, report)
        assert result.captured_stdout == "1234567890"

    def test_capture_output_disabled_via_handle_report(self):
        """Should not capture if config disabled (integration via handle_runtest_logreport)."""
        config = Config(capture_failed_output=False)
        collector = TestCollector(config)
        report = MagicMock()
        report.nodeid = "t"
        report.outcome = "failed"
        report.when = "call"
        report.passed = False
        report.failed = True
        report.skipped = False
        report.capstdout = "output"
        del report.wasxfail

        collector.handle_runtest_logreport(report)
        result = collector.results["t"]
        assert result.captured_stdout is None

    def test_create_result_with_item_markers(self):
        """Should extract markers from item."""
        config = Config()
        collector = TestCollector(config)
        report = MagicMock()
        report.nodeid = "test_mk.py::test_mk"

        item = MagicMock()
        item.callspec.id = "param1"

        # Mock getters for markers
        def get_closest_marker(name):
            if name == "llm_opt_out":
                return MagicMock()
            if name == "llm_context":
                m = MagicMock()
                m.args = ["complete"]
                return m
            if name == "requirement":
                m = MagicMock()
                m.args = ["REQ-1", "REQ-2"]
                return m
            return None

        item.get_closest_marker.side_effect = get_closest_marker

        result = collector._create_result(report, item)
        assert result.param_id == "param1"
        assert result.llm_opt_out is True
        assert result.llm_context_override == "complete"
        assert result.requirements == ["REQ-1", "REQ-2"]


class TestCollectorReportHandling:
    """Tests for report handling logic."""

    def test_handle_collection_report_failure(self):
        """Should record collection error."""
        config = Config()
        collector = TestCollector(config)
        report = MagicMock()
        report.outcome = "failed"
        report.failed = True
        report.nodeid = "test_broken.py"
        report.longrepr = "SyntaxError"

        collector.handle_collection_report(report)

        assert len(collector.collection_errors) == 1
        assert collector.collection_errors[0].nodeid == "test_broken.py"
        assert collector.collection_errors[0].message == "SyntaxError"

    def test_handle_runtest_setup_failure(self):
        """Should record setup error."""
        config = Config()
        collector = TestCollector(config)
        report = MagicMock()
        report.nodeid = "t::f"
        report.when = "setup"
        report.failed = True
        report.passed = False
        report.skipped = False
        report.longrepr = "Setup failed"
        del report.wasxfail  # Explicitly delete to emulate regular failure

        collector.handle_runtest_logreport(report)

        res = collector.results["t::f"]
        assert res.outcome == "error"
        assert res.phase == "setup"
        assert res.error_message == "Setup failed"

    def test_handle_runtest_teardown_failure(self):
        """Should record error if teardown fails after pass."""
        config = Config()
        collector = TestCollector(config)

        # First simulate a pass
        call_report = MagicMock()
        call_report.nodeid = "t::f"
        call_report.when = "call"
        call_report.passed = True
        call_report.failed = False
        call_report.skipped = False
        call_report.duration = 0.1
        del call_report.wasxfail
        collector.handle_runtest_logreport(call_report)

        # Then teardown failure
        teardown_report = MagicMock()
        teardown_report.nodeid = "t::f"
        teardown_report.when = "teardown"
        teardown_report.failed = True
        teardown_report.passed = False
        teardown_report.longrepr = "Cleanup failed"
        del teardown_report.wasxfail

        collector.handle_runtest_logreport(teardown_report)

        res = collector.results["t::f"]
        assert res.outcome == "error"
        assert res.phase == "teardown"
        assert res.error_message == "Cleanup failed"

    def test_handle_runtest_rerun(self):
        """Should handle rerun attribute."""
        config = Config()
        collector = TestCollector(config)
        report = MagicMock()
        report.nodeid = "t::r"
        report.when = "call"
        report.passed = False
        report.failed = True
        report.rerun = 1
        del report.wasxfail

        collector.handle_runtest_logreport(report)

        res = collector.results["t::r"]
        assert res.rerun_count == 1
        assert res.final_outcome == "failed"
