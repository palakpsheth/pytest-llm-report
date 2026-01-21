import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from pytest_llm_report.aggregation import Aggregator
from pytest_llm_report.models import (
    CoverageEntry,
    LlmAnnotation,
    LlmTokenUsage,
    SourceCoverageEntry,
    Summary,
    TestCaseResult,
)
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

            with pytest.warns(UserWarning, match="Skipping invalid report file"):
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

        # Create a mock latest summary with coverage
        latest_summary = Summary(
            total=6,
            passed=1,
            failed=1,
            skipped=1,
            xfailed=1,
            xpassed=1,
            error=1,
            coverage_total_percent=85.5,
        )
        summary = aggregator._recalculate_summary(tests, latest_summary)

        assert summary.total == 6
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.skipped == 1
        assert summary.xfailed == 1
        assert summary.xpassed == 1
        assert summary.error == 1
        # Verify coverage percentage is preserved
        assert summary.coverage_total_percent == 85.5
        assert summary.total_duration == 5.0

    def test_aggregate_with_coverage_and_llm_annotations(self, aggregator):
        """Test that coverage and LLM annotations are properly deserialized and can be re-serialized."""
        t1 = "2024-01-01T10:00:00"

        # Create a test with coverage and LLM annotation including token_usage
        test_case = {
            "nodeid": "tests/test_foo.py::test_bar",
            "outcome": "passed",
            "duration": 0.5,
            "phase": "call",
            "coverage": [
                {
                    "file_path": "src/module.py",
                    "line_ranges": "1-10, 15-20",
                    "line_count": 16,
                },
                {
                    "file_path": "src/helper.py",
                    "line_ranges": "5-8",
                    "line_count": 4,
                },
            ],
            "llm_annotation": {
                "scenario": "Tests the feature works correctly",
                "why_needed": "Prevents regression in core functionality",
                "key_assertions": ["Assert A", "Assert B", "Assert C"],
                "confidence": 0.95,
                "token_usage": {
                    "prompt_tokens": 150,
                    "completion_tokens": 50,
                    "total_tokens": 200,
                },
            },
        }

        report1 = self.create_dummy_report("run1", t1, [test_case])

        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator.config.aggregate_dir = tmpdir

            # Write report
            with open(Path(tmpdir) / "report_1.json", "w") as f:
                json.dump(report1, f)

            # Aggregate (loads from JSON)
            result = aggregator.aggregate()

            assert result is not None
            assert len(result.tests) == 1

            test = result.tests[0]

            # Verify coverage was properly deserialized
            assert len(test.coverage) == 2
            assert isinstance(test.coverage[0], CoverageEntry)
            assert test.coverage[0].file_path == "src/module.py"
            assert test.coverage[0].line_ranges == "1-10, 15-20"
            assert test.coverage[0].line_count == 16
            assert isinstance(test.coverage[1], CoverageEntry)
            assert test.coverage[1].file_path == "src/helper.py"

            # Verify LLM annotation was properly deserialized
            assert test.llm_annotation is not None
            assert isinstance(test.llm_annotation, LlmAnnotation)
            assert test.llm_annotation.scenario == "Tests the feature works correctly"
            assert (
                test.llm_annotation.why_needed
                == "Prevents regression in core functionality"
            )
            assert len(test.llm_annotation.key_assertions) == 3
            assert test.llm_annotation.confidence == 0.95

            # Verify token_usage was properly deserialized (this was the CI bug fix)
            assert test.llm_annotation.token_usage is not None
            assert isinstance(test.llm_annotation.token_usage, LlmTokenUsage)
            assert test.llm_annotation.token_usage.prompt_tokens == 150
            assert test.llm_annotation.token_usage.completion_tokens == 50
            assert test.llm_annotation.token_usage.total_tokens == 200

            # Most importantly: verify it can be re-serialized (this would fail before the fix)
            serialized = test.to_dict()
            assert "coverage" in serialized
            assert len(serialized["coverage"]) == 2
            assert serialized["coverage"][0]["file_path"] == "src/module.py"
            assert "llm_annotation" in serialized
            assert (
                serialized["llm_annotation"]["scenario"]
                == "Tests the feature works correctly"
            )
            # Verify token_usage serialization
            assert "token_usage" in serialized["llm_annotation"]
            assert serialized["llm_annotation"]["token_usage"]["prompt_tokens"] == 150
            assert serialized["llm_annotation"]["token_usage"]["total_tokens"] == 200

    def test_aggregate_with_source_coverage(self, aggregator):
        """Source coverage summary should be deserialized."""
        t1 = "2024-01-01T10:00:00"
        report1 = self.create_dummy_report("run1", t1, [])
        report1["source_coverage"] = [
            {
                "file_path": "src/foo.py",
                "statements": 12,
                "missed": 2,
                "covered": 10,
                "coverage_percent": 83.33,
                "covered_ranges": "1-5, 7-11",
                "missed_ranges": "6, 12",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator.config.aggregate_dir = tmpdir

            with open(Path(tmpdir) / "report_1.json", "w") as f:
                json.dump(report1, f)

            result = aggregator.aggregate()

            assert result is not None
            assert len(result.source_coverage) == 1
            assert isinstance(result.source_coverage[0], SourceCoverageEntry)
            assert result.source_coverage[0].file_path == "src/foo.py"

    def test_load_coverage_from_source(self, aggregator):
        """Test loading coverage from configured source file."""
        # 1. Test when option is not set
        aggregator.config.llm_coverage_source = None
        assert aggregator._load_coverage_from_source() is None

        # 2. Test when file doesn't exist
        aggregator.config.llm_coverage_source = "/nonexistent/coverage"
        with pytest.warns(UserWarning, match="Coverage source not found"):
            assert aggregator._load_coverage_from_source() is None

        # 3. Test successful loading (mocking coverage.py)
        aggregator.config.llm_coverage_source = ".coverage"
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("coverage.Coverage") as mock_cov_cls,
            patch("pytest_llm_report.coverage_map.CoverageMapper") as mock_mapper_cls,
        ):
            mock_cov = MagicMock()
            mock_cov_cls.return_value = mock_cov
            # Mock cov.report() to return the coverage percentage
            mock_cov.report.return_value = 80.0

            mock_mapper = MagicMock()
            mock_mapper_cls.return_value = mock_mapper

            # Setup mock return values
            entry = SourceCoverageEntry(
                file_path="src/foo.py",
                statements=10,
                missed=2,
                covered=8,
                coverage_percent=80.0,
                covered_ranges="1-8",
                missed_ranges="9-10",
            )
            mock_mapper.map_source_coverage.return_value = [entry]

            # Run method under test
            result = aggregator._load_coverage_from_source()

            # Verify interactions
            mock_cov_cls.assert_called_with(data_file=".coverage")
            mock_cov.load.assert_called_once()
            mock_cov.report.assert_called_once()  # Verify cov.report() was called
            mock_mapper.map_source_coverage.assert_called_with(mock_cov)

            # Verify result
            assert result is not None
            entries, percent = result
            assert len(entries) == 1
            assert entries[0] == entry
            assert percent == 80.0
