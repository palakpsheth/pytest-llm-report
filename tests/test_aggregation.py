import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pytest_llm_report.aggregation import Aggregator
from pytest_llm_report.models import TestCaseResult
from pytest_llm_report.options import Config


class TestAggregator:
    @pytest.fixture
    def mock_config(self):
        config = Mock(spec=Config)
        config.aggregate_dir = "/tmp/fake-agg-dir"
        config.aggregate_policy = "latest"
        config.repo_root = Path("/tmp")
        return config

    @pytest.fixture
    def aggregator(self, mock_config):
        return Aggregator(mock_config)

    def create_dummy_report(self, run_id, timestamp, tests):
        return {
            "run_meta": {
                "run_id": run_id,
                "start_time": timestamp,
                "end_time": timestamp,
                "duration": 1.0,
                "pytest_version": "0.0.0",
                "plugin_version": "0.0.0",
                "python_version": "3.x",
                "platform": "linux",
                "exit_code": 0,
                "collected_count": len(tests),
                "selected_count": len(tests),
            },
            "summary": {
                "total": len(tests),
                "passed": sum(1 for t in tests if t["outcome"] == "passed"),
                "failed": sum(1 for t in tests if t["outcome"] == "failed"),
                "skipped": 0,
                "xfailed": 0,
                "xpassed": 0,
                "error": 0,
                "total_duration": sum(t.get("duration", 0) for t in tests),
            },
            "tests": tests,
            "collection_errors": [],
            "warnings": [],
            "artifacts": [],
        }

    def test_aggregate_no_dir_configured(self, mock_config):
        mock_config.aggregate_dir = None
        agg = Aggregator(mock_config)
        assert agg.aggregate() is None

    def test_aggregate_dir_not_exists(self, aggregator):
        with patch("pathlib.Path.exists", return_value=False):
            assert aggregator.aggregate() is None

    def test_aggregate_no_reports(self, aggregator):
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.glob", return_value=[]),
        ):
            assert aggregator.aggregate() is None

    def test_aggregate_latest_policy(self, aggregator):
        # Setup: 2 reports, same test, different times. Should pick latest.
        t1 = "2024-01-01T10:00:00"
        t2 = "2024-01-01T11:00:00"

        test_case = {
            "nodeid": "tests/test_foo.py::test_bar",
            "outcome": "passed",
            "duration": 0.1,
            "phase": "call",
        }

        report1 = self.create_dummy_report(
            "run1", t1, [{**test_case, "outcome": "failed"}]
        )
        report2 = self.create_dummy_report(
            "run2", t2, [{**test_case, "outcome": "passed"}]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator.config.aggregate_dir = tmpdir

            # Write files
            for i, r in enumerate([report1, report2]):
                with open(Path(tmpdir) / f"report_{i}.json", "w") as f:
                    json.dump(r, f)

            result = aggregator.aggregate()

            assert result is not None
            assert len(result.tests) == 1
            assert result.tests[0].outcome == "passed"  # From report2 (latest)
            assert result.run_meta.is_aggregated is True
            assert result.run_meta.run_count == 2
            assert result.summary.passed == 1
            assert result.summary.failed == 0

    def test_aggregate_all_policy(self, aggregator):
        aggregator.config.aggregate_policy = "all"

        t1 = "2024-01-01T10:00:00"
        test_case = {
            "nodeid": "tests/test_foo.py::test_bar",
            "outcome": "passed",
            "duration": 0.1,
            "phase": "call",
        }

        report1 = self.create_dummy_report("run1", t1, [test_case])
        report2 = self.create_dummy_report("run2", t1, [test_case])

        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator.config.aggregate_dir = tmpdir

            for i, r in enumerate([report1, report2]):
                with open(Path(tmpdir) / f"report_{i}.json", "w") as f:
                    json.dump(r, f)

            result = aggregator.aggregate()

            assert result is not None
            assert len(result.tests) == 2  # Both retained

    def test_skips_invalid_json(self, aggregator):
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator.config.aggregate_dir = tmpdir

            # Valid report
            valid_report = self.create_dummy_report("run1", "2024-01-01T10:00:00", [])
            with open(Path(tmpdir) / "valid.json", "w") as f:
                json.dump(valid_report, f)

            # Invalid json
            with open(Path(tmpdir) / "invalid.json", "w") as f:
                f.write("not json")

            # Missing fields
            with open(Path(tmpdir) / "missing_fields.json", "w") as f:
                json.dump({"foo": "bar"}, f)

            result = aggregator.aggregate()
            assert result is not None
            assert result.run_meta.run_count == 1  # Only valid report counted

    def test_recalculate_summary(self, aggregator):
        tests = [
            TestCaseResult(nodeid="1", outcome="passed", duration=1.0, phase="call"),
            TestCaseResult(nodeid="2", outcome="failed", duration=1.0, phase="call"),
            TestCaseResult(nodeid="3", outcome="skipped", duration=0.0, phase="call"),
            TestCaseResult(nodeid="4", outcome="xfailed", duration=1.0, phase="call"),
            TestCaseResult(nodeid="5", outcome="xpassed", duration=1.0, phase="call"),
            TestCaseResult(nodeid="6", outcome="error", duration=1.0, phase="call"),
        ]

        summary = aggregator._recalculate_summary(tests)

        assert summary.total == 6
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.skipped == 1
        assert summary.xfailed == 1
        assert summary.xpassed == 1
        assert summary.error == 1
        assert summary.total_duration == 5.0
