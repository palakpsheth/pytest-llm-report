# SPDX-License-Identifier: MIT
"""Pytester smoke tests for end-to-end plugin validation.

These tests use pytester to run a sample project with the plugin
and validate that reports are generated correctly.
"""

import json

import pytest


class TestPluginRegistration:
    """Tests for plugin registration and markers."""

    def test_plugin_registered(self, pytester: pytest.Pytester):
        """Plugin is registered via pytest11."""
        result = pytester.runpytest("--help")
        result.stdout.fnmatch_lines(["*--llm-report*"])

    def test_markers_registered(self, pytester: pytest.Pytester):
        """LLM markers are registered."""
        result = pytester.runpytest("--markers")
        result.stdout.fnmatch_lines(["*llm_opt_out*"])
        result.stdout.fnmatch_lines(["*llm_context*"])
        result.stdout.fnmatch_lines(["*requirement*"])

    def test_help_contains_examples(self, pytester: pytest.Pytester):
        """CLI help text includes usage examples."""
        result = pytester.runpytest("--help")
        result.stdout.fnmatch_lines(["*Example:*--llm-report*"])


class TestBasicReportGeneration:
    """Tests for basic report generation."""

    def test_json_report_created(self, pytester: pytest.Pytester):
        """JSON report is created."""
        pytester.makepyfile(
            """
            def test_pass():
                assert True

            def test_fail():
                assert False
            """
        )

        report_path = pytester.path / "report.json"
        pytester.runpytest(f"--llm-report-json={report_path}")

        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["schema_version"]
        assert data["summary"]["total"] == 2
        assert data["summary"]["passed"] == 1
        assert data["summary"]["failed"] == 1

    def test_html_report_created(self, pytester: pytest.Pytester):
        """HTML report is created."""
        pytester.makepyfile(
            """
            def test_simple():
                assert 1 + 1 == 2
            """
        )

        report_path = pytester.path / "report.html"
        pytester.runpytest(f"--llm-report={report_path}")

        assert report_path.exists()
        content = report_path.read_text()
        assert "<html" in content
        assert "test_simple" in content


class TestOutcomes:
    """Tests for different test outcomes."""

    def test_skip_outcome(self, pytester: pytest.Pytester):
        """Skipped tests are recorded."""
        pytester.makepyfile(
            """
            import pytest

            @pytest.mark.skip(reason="test skip")
            def test_skipped():
                pass
            """
        )

        report_path = pytester.path / "report.json"
        pytester.runpytest(f"--llm-report-json={report_path}")

        data = json.loads(report_path.read_text())
        assert data["summary"]["skipped"] == 1

    def test_xfail_outcome(self, pytester: pytest.Pytester):
        """Xfailed tests are recorded."""
        pytester.makepyfile(
            """
            import pytest

            @pytest.mark.xfail
            def test_xfail():
                assert False
            """
        )

        report_path = pytester.path / "report.json"
        pytester.runpytest(f"--llm-report-json={report_path}")

        data = json.loads(report_path.read_text())
        assert data["summary"]["xfailed"] == 1

    def test_multiple_xfail_outcomes(self, pytester: pytest.Pytester):
        """Multiple xfailed tests are recorded in the report."""
        pytester.makepyfile(
            """
            import pytest

            @pytest.mark.xfail
            def test_xfail_one():
                assert False

            @pytest.mark.xfail
            def test_xfail_two():
                assert False
            """
        )

        report_path = pytester.path / "report.json"
        pytester.runpytest(f"--llm-report-json={report_path}")

        data = json.loads(report_path.read_text())
        assert data["summary"]["xfailed"] == 2
        outcomes = [test["outcome"] for test in data["tests"]]
        assert outcomes == ["xfailed", "xfailed"]


class TestParametrization:
    """Tests for parameterized tests."""

    def test_parametrized_tests(self, pytester: pytest.Pytester):
        """Parameterized tests are recorded separately."""
        pytester.makepyfile(
            """
            import pytest

            @pytest.mark.parametrize("x", [1, 2, 3])
            def test_param(x):
                assert x > 0
            """
        )

        report_path = pytester.path / "report.json"
        pytester.runpytest(f"--llm-report-json={report_path}")

        data = json.loads(report_path.read_text())
        assert data["summary"]["total"] == 3
        assert data["summary"]["passed"] == 3


class TestMarkers:
    """Tests for LLM markers."""

    def test_llm_opt_out_marker(self, pytester: pytest.Pytester):
        """LLM opt-out marker is recorded."""
        pytester.makepyfile(
            """
            import pytest

            @pytest.mark.llm_opt_out
            def test_opt_out():
                pass
            """
        )

        report_path = pytester.path / "report.json"
        pytester.runpytest(f"--llm-report-json={report_path}")

        data = json.loads(report_path.read_text())
        tests = data["tests"]
        assert len(tests) == 1
        assert tests[0].get("llm_opt_out", False) is True

    def test_requirement_marker(self, pytester: pytest.Pytester):
        """Requirement marker is recorded."""
        pytester.makepyfile(
            """
            import pytest

            @pytest.mark.requirement("REQ-001", "REQ-002")
            def test_with_req():
                pass
            """
        )

        report_path = pytester.path / "report.json"
        pytester.runpytest(f"--llm-report-json={report_path}")

        data = json.loads(report_path.read_text())
        tests = data["tests"]
        assert len(tests) == 1
        reqs = tests[0].get("requirements", [])
        assert "REQ-001" in reqs
        assert "REQ-002" in reqs


class TestSpecialCharacters:
    """Tests for special characters in nodeids."""

    def test_special_chars_in_nodeid(self, pytester: pytest.Pytester):
        """Special characters in nodeid are handled."""
        pytester.makepyfile(
            """
            import pytest

            @pytest.mark.parametrize("s", ["hello<world>", "foo&bar"])
            def test_special(s):
                assert s
            """
        )

        report_path = pytester.path / "report.html"
        pytester.runpytest(f"--llm-report={report_path}")

        # Should not crash and HTML should be valid
        assert report_path.exists()
        content = report_path.read_text()
        assert "<html" in content
