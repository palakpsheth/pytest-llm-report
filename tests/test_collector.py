# SPDX-License-Identifier: MIT
"""Tests for pytest_llm_report.collector module."""

from pytest_llm_report.collector import TestCollector
from pytest_llm_report.models import CollectionError
from pytest_llm_report.options import Config


class TestTestCollector:
    """Tests for TestCollector class."""

    def test_create_collector(self):
        """Collector should initialize with empty results."""
        config = Config()
        collector = TestCollector(config=config)
        assert collector.results == {}
        assert collector.collection_errors == []
        assert collector.collected_count == 0

    def test_handle_collection_finish(self):
        """Should track collected and deselected counts."""
        config = Config()
        collector = TestCollector(config=config)

        # Simulate items (using empty list for simplicity)
        items = [None, None, None]  # 3 collected
        deselected = [None]  # 1 deselected

        collector.handle_collection_finish(items, deselected)

        assert collector.collected_count == 3
        assert collector.deselected_count == 1

    def test_get_results_sorted(self):
        """Results should be sorted by nodeid."""
        config = Config()
        collector = TestCollector(config=config)

        # Manually add results out of order
        from pytest_llm_report.models import TestCaseResult

        collector.results["z_test.py::test_z"] = TestCaseResult(
            nodeid="z_test.py::test_z", outcome="passed"
        )
        collector.results["a_test.py::test_a"] = TestCaseResult(
            nodeid="a_test.py::test_a", outcome="passed"
        )

        results = collector.get_results()
        nodeids = [r.nodeid for r in results]
        assert nodeids == ["a_test.py::test_a", "z_test.py::test_z"]


class TestCollectorMarkerExtraction:
    """Tests for marker extraction in collector."""

    def test_llm_opt_out_default_false(self):
        """Default llm_opt_out should be False."""
        from pytest_llm_report.models import TestCaseResult

        result = TestCaseResult(nodeid="test.py::test_foo", outcome="passed")
        assert result.llm_opt_out is False

    def test_llm_context_override_default_none(self):
        """Default llm_context_override should be None."""
        from pytest_llm_report.models import TestCaseResult

        result = TestCaseResult(nodeid="test.py::test_foo", outcome="passed")
        assert result.llm_context_override is None


class TestCollectorOutputCapture:
    """Tests for output capture in collector."""

    def test_capture_enabled_by_default(self):
        """Output capture should be enabled by default."""
        config = Config()
        assert config.capture_failed_output is True

    def test_capture_max_chars_default(self):
        """Default max chars should be 4000."""
        config = Config()
        assert config.capture_output_max_chars == 4000


class TestCollectorCollectionErrors:
    """Tests for collection error handling."""

    def test_get_collection_errors_initially_empty(self):
        """Should return empty list initially."""
        config = Config()
        collector = TestCollector(config=config)
        assert collector.get_collection_errors() == []

    def test_collection_error_structure(self):
        """Collection errors should have correct structure."""
        error = CollectionError(nodeid="test_bad.py", message="SyntaxError")
        assert error.nodeid == "test_bad.py"
        assert error.message == "SyntaxError"


class TestCollectorXfailHandling:
    """Tests for xfail/xpass handling in collector."""

    def test_xfail_failed_is_xfailed(self):
        """xfail failures should be recorded as xfailed."""
        from types import SimpleNamespace

        config = Config()
        collector = TestCollector(config=config)

        report = SimpleNamespace(
            nodeid="test_xfail.py::test_expected_fail",
            when="call",
            passed=False,
            failed=True,
            skipped=False,
            duration=0.01,
            longrepr="AssertionError",
            wasxfail="expected failure",
        )

        collector.handle_runtest_logreport(report)

        result = collector.results[report.nodeid]
        assert result.outcome == "xfailed"

    def test_xfail_passed_is_xpassed(self):
        """xfail passes should be recorded as xpassed."""
        from types import SimpleNamespace

        config = Config()
        collector = TestCollector(config=config)

        report = SimpleNamespace(
            nodeid="test_xfail.py::test_unexpected_pass",
            when="call",
            passed=True,
            failed=False,
            skipped=False,
            duration=0.01,
            longrepr="",
            wasxfail="expected failure",
        )

        collector.handle_runtest_logreport(report)

        result = collector.results[report.nodeid]
        assert result.outcome == "xpassed"
