# SPDX-License-Identifier: MIT
"""Integration tests for pytest-llm-report plugin hooks."""

import pytest

from pytest_llm_report.options import Config, load_config


class TestPluginConfigLoading:
    """Tests for plugin configuration loading."""

    def test_config_defaults(self, pytestconfig):
        """Config should have safe defaults."""
        cfg = load_config(pytestconfig)
        assert isinstance(cfg, Config)
        # Can't check exact values since pytest may not have our options registered

    def test_markers_exist_in_config(self, pytestconfig):
        """Config should be accessible."""
        # Just verify we can access the config
        assert pytestconfig is not None


class TestPluginIntegration:
    """Basic integration tests."""

    @pytest.mark.llm_opt_out
    def test_llm_opt_out_marker(self):
        """Marker should not cause errors."""
        assert True

    @pytest.mark.llm_context("balanced")
    def test_llm_context_marker(self):
        """Context marker should not cause errors."""
        assert True

    @pytest.mark.requirement("REQ-001", "REQ-002")
    def test_requirement_marker(self):
        """Requirement marker should not cause errors."""
        assert True


class TestReportGeneration:
    """Tests for report generation flow."""

    def test_report_writer_integration(self, tmp_path):
        """Full report generation flow."""
        from pytest_llm_report.models import TestCaseResult
        from pytest_llm_report.report_writer import ReportWriter

        config = Config(
            report_json=str(tmp_path / "report.json"),
            report_html=str(tmp_path / "report.html"),
        )
        writer = ReportWriter(config)

        tests = [
            TestCaseResult(
                nodeid="test_a.py::test_pass", outcome="passed", duration=0.1
            ),
            TestCaseResult(
                nodeid="test_b.py::test_fail",
                outcome="failed",
                duration=0.2,
                error_message="AssertionError",
            ),
        ]

        writer.write_report(tests)

        # Verify JSON
        assert (tmp_path / "report.json").exists()
        import json

        data = json.loads((tmp_path / "report.json").read_text())
        assert data["summary"]["total"] == 2
        assert data["summary"]["passed"] == 1

        # Verify HTML
        assert (tmp_path / "report.html").exists()
        html = (tmp_path / "report.html").read_text()
        assert "test_a.py" in html
        assert "test_b.py" in html
