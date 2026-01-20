# SPDX-License-Identifier: MIT
"""Integration gate tests for pytest-llm-report.

These tests validate the full pipeline without LLM and verify
required output fields. They should be fast and run in CI.
"""

import json
from pathlib import Path

from pytest_llm_report.models import (
    SCHEMA_VERSION,
    ReportRoot,
    RunMeta,
    Summary,
    TestCaseResult,
)
from pytest_llm_report.options import Config, get_default_config
from pytest_llm_report.report_writer import ReportWriter


class TestConfigDefaults:
    """Contract tests for Config defaults."""

    def test_provider_default_none(self):
        """Provider defaults to none for privacy."""
        config = get_default_config()
        assert config.provider == "none"

    def test_context_mode_default_minimal(self):
        """Context mode defaults to minimal."""
        config = get_default_config()
        assert config.llm_context_mode == "minimal"

    def test_llm_not_enabled_by_default(self):
        """LLM is not enabled by default."""
        config = get_default_config()
        assert not config.is_llm_enabled()

    def test_omit_tests_default_true(self):
        """Omit tests from coverage by default."""
        config = get_default_config()
        assert config.omit_tests_from_coverage is True

    def test_aggregation_defaults(self):
        """Aggregation has sensible defaults."""
        config = get_default_config()
        assert config.aggregate_dir is None
        assert config.aggregate_policy == "latest"
        assert config.aggregate_include_history is False

    def test_capture_failed_output_default_true(self):
        """Captured output is enabled by default."""
        config = get_default_config()
        assert config.capture_failed_output is True

    def test_secret_exclude_globs(self):
        """Secret files are excluded by default."""
        config = get_default_config()
        excludes = config.llm_context_exclude_globs
        assert any("secret" in g for g in excludes)
        assert any(".env" in g for g in excludes)


class TestSchemaCompatibility:
    """Contract tests for schema compatibility."""

    def test_schema_version_defined(self):
        """Schema version is defined."""
        assert SCHEMA_VERSION
        assert "." in SCHEMA_VERSION  # semver-like

    def test_report_root_has_required_fields(self):
        """ReportRoot has required fields."""
        report = ReportRoot(
            schema_version=SCHEMA_VERSION,
            run_meta=RunMeta(),
            summary=Summary(),
            tests=[],
        )
        data = report.to_dict()

        # Required fields
        assert "schema_version" in data
        assert "run_meta" in data
        assert "summary" in data
        assert "tests" in data

    def test_run_meta_has_status_fields(self):
        """RunMeta has run status fields."""
        meta = RunMeta()
        data = meta.to_dict()

        # Status fields
        assert "exit_code" in data
        assert "interrupted" in data
        assert "collect_only" in data
        assert "collected_count" in data
        assert "selected_count" in data

    def test_run_meta_has_aggregation_fields(self):
        """RunMeta has aggregation fields."""
        meta = RunMeta()
        data = meta.to_dict()

        assert "is_aggregated" in data
        # aggregation_policy only included when is_aggregated is True
        assert "run_count" in data

    def test_test_case_has_required_fields(self):
        """TestCaseResult has required fields."""
        test = TestCaseResult(nodeid="test.py::test_foo", outcome="passed")
        data = test.to_dict()

        assert "nodeid" in data
        assert "outcome" in data
        assert "duration" in data


class TestFullPipeline:
    """Integration tests for the full report pipeline."""

    def test_json_report_generation(self, tmp_path: Path):
        """Full pipeline generates valid JSON report."""
        # Create test results
        tests = [
            TestCaseResult(
                nodeid="tests/test_a.py::test_one", outcome="passed", duration=0.1
            ),
            TestCaseResult(
                nodeid="tests/test_a.py::test_two", outcome="failed", duration=0.2
            ),
            TestCaseResult(
                nodeid="tests/test_b.py::test_skip", outcome="skipped", duration=0.0
            ),
        ]

        # Configure report writer
        config = Config(
            report_json=str(tmp_path / "report.json"),
            report_html=str(tmp_path / "report.html"),
        )
        writer = ReportWriter(config)

        # Generate report
        writer.write_report(tests)

        # Verify JSON output
        json_path = tmp_path / "report.json"
        assert json_path.exists()

        data = json.loads(json_path.read_text())
        assert data["schema_version"] == SCHEMA_VERSION
        assert data["summary"]["total"] == 3
        assert data["summary"]["passed"] == 1
        assert data["summary"]["failed"] == 1
        assert data["summary"]["skipped"] == 1

    def test_html_report_generation(self, tmp_path: Path):
        """Full pipeline generates HTML report."""
        tests = [
            TestCaseResult(nodeid="tests/test.py::test_pass", outcome="passed"),
        ]

        config = Config(
            report_html=str(tmp_path / "report.html"),
        )
        writer = ReportWriter(config)
        writer.write_report(tests)

        html_path = tmp_path / "report.html"
        assert html_path.exists()

        content = html_path.read_text()
        assert "<html" in content
        assert "test_pass" in content

    def test_deterministic_output(self, tmp_path: Path):
        """Reports are deterministic (sorted by nodeid)."""
        tests = [
            TestCaseResult(nodeid="z_test.py::test_z", outcome="passed"),
            TestCaseResult(nodeid="a_test.py::test_a", outcome="passed"),
            TestCaseResult(nodeid="m_test.py::test_m", outcome="passed"),
        ]

        config = Config(report_json=str(tmp_path / "report.json"))
        writer = ReportWriter(config)
        writer.write_report(tests)

        data = json.loads((tmp_path / "report.json").read_text())
        nodeids = [t["nodeid"] for t in data["tests"]]

        # Should be sorted
        assert nodeids == sorted(nodeids)

    def test_empty_test_suite(self, tmp_path: Path):
        """Empty test suite produces valid report."""
        config = Config(report_json=str(tmp_path / "report.json"))
        writer = ReportWriter(config)
        report = writer.write_report([])

        assert report.summary.total == 0
        data = json.loads((tmp_path / "report.json").read_text())
        assert data["summary"]["total"] == 0
