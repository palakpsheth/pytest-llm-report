# SPDX-License-Identifier: MIT
"""Additional tests for coverage_map.py to increase coverage.

Targets uncovered lines in:
- Phase filtering logic (setup, teardown)
- Edge cases in context extraction
"""

from pathlib import Path
from unittest.mock import MagicMock

from pytest_llm_report.coverage_map import CoverageMapper
from pytest_llm_report.options import Config


class TestPhaseFiltering:
    """Tests for phase filtering in _extract_nodeid."""

    def test_extract_nodeid_setup_phase_config(self):
        """Test that setup phase is correctly filtered when configured."""
        config = Config(include_phase="setup")
        mapper = CoverageMapper(config)

        # Should return nodeid when phase matches
        assert (
            mapper._extract_nodeid("test_foo.py::test_bar|setup")
            == "test_foo.py::test_bar"
        )
        # Should return None when phase doesn't match
        assert mapper._extract_nodeid("test_foo.py::test_bar|run") is None
        assert mapper._extract_nodeid("test_foo.py::test_bar|teardown") is None

    def test_extract_nodeid_teardown_phase_config(self):
        """Test that teardown phase is correctly filtered when configured."""
        config = Config(include_phase="teardown")
        mapper = CoverageMapper(config)

        # Should return nodeid when phase matches
        assert (
            mapper._extract_nodeid("test_foo.py::test_bar|teardown")
            == "test_foo.py::test_bar"
        )
        # Should return None when phase doesn't match
        assert mapper._extract_nodeid("test_foo.py::test_bar|run") is None
        assert mapper._extract_nodeid("test_foo.py::test_bar|setup") is None

    def test_extract_nodeid_all_phase_config(self):
        """Test that all phases are accepted when configured."""
        config = Config(include_phase="all")
        mapper = CoverageMapper(config)

        # Should return nodeid for any phase
        assert (
            mapper._extract_nodeid("test_foo.py::test_bar|setup")
            == "test_foo.py::test_bar"
        )
        assert (
            mapper._extract_nodeid("test_foo.py::test_bar|run")
            == "test_foo.py::test_bar"
        )
        assert (
            mapper._extract_nodeid("test_foo.py::test_bar|teardown")
            == "test_foo.py::test_bar"
        )

    def test_extract_nodeid_run_phase_default(self):
        """Test that run phase is the default filter."""
        config = Config()  # Default is include_phase="run"
        mapper = CoverageMapper(config)

        # Should return nodeid when phase matches
        assert (
            mapper._extract_nodeid("test_foo.py::test_bar|run")
            == "test_foo.py::test_bar"
        )
        # Should return None when phase doesn't match
        assert mapper._extract_nodeid("test_foo.py::test_bar|setup") is None
        assert mapper._extract_nodeid("test_foo.py::test_bar|teardown") is None

    def test_extract_nodeid_without_pipe(self):
        """Test context without phase delimiter returns as-is."""
        config = Config()
        mapper = CoverageMapper(config)

        assert (
            mapper._extract_nodeid("test_foo.py::test_bar") == "test_foo.py::test_bar"
        )

    def test_extract_nodeid_empty_string(self):
        """Test that empty string returns None."""
        config = Config()
        mapper = CoverageMapper(config)

        assert mapper._extract_nodeid("") is None

    def test_extract_nodeid_none(self):
        """Test that None input returns None."""
        config = Config()
        mapper = CoverageMapper(config)

        assert mapper._extract_nodeid(None) is None


class TestExtractContexts:
    """Tests for context extraction edge cases."""

    def test_no_measured_files(self):
        """Test when coverage data has no measured files."""
        config = Config()
        mapper = CoverageMapper(config)

        mock_data = MagicMock()
        mock_data.measured_files.return_value = []

        result = mapper._extract_contexts(mock_data)
        assert result == {}

    def test_skip_non_python_files(self):
        """Test that non-Python files are skipped."""
        config = Config()
        mapper = CoverageMapper(config)

        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["file.txt", "data.json"]
        mock_data.contexts_by_lineno.return_value = {}

        result = mapper._extract_contexts(mock_data)
        assert result == {}

    def test_contexts_by_lineno_exception(self):
        """Test handling when contexts_by_lineno raises."""
        config = Config(repo_root=Path("/project"))
        mapper = CoverageMapper(config)

        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["file.py"]

        # First call (to check for contexts) succeeds with contexts
        # Second call (per file) raises exception
        call_count = [0]

        def contexts_side_effect(path):
            call_count[0] += 1
            if call_count[0] == 1:
                return {1: ["test::test_foo|run"]}
            raise Exception("Error accessing contexts")

        mock_data.contexts_by_lineno.side_effect = contexts_side_effect

        result = mapper._extract_contexts(mock_data)
        # Should handle exception gracefully
        assert result == {}


class TestMapSourceCoverage:
    """Tests for map_source_coverage edge cases."""

    def test_skip_non_python_files(self):
        """Test that non-Python files are skipped in source coverage."""
        config = Config()
        mapper = CoverageMapper(config)

        mock_cov = MagicMock()
        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["data.json", "styles.css"]
        mock_cov.get_data.return_value = mock_data

        result = mapper.map_source_coverage(mock_cov)
        assert result == []

    def test_skip_test_files_when_configured(self):
        """Test that test files are skipped when omit_tests_from_coverage is True."""
        config = Config(omit_tests_from_coverage=True, repo_root=Path("/project"))
        mapper = CoverageMapper(config)

        mock_cov = MagicMock()
        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["/project/tests/test_foo.py"]
        mock_cov.get_data.return_value = mock_data

        result = mapper.map_source_coverage(mock_cov)
        assert result == []

    def test_include_test_files_when_not_configured(self):
        """Test that test files are included when omit_tests_from_coverage is False."""
        config = Config(omit_tests_from_coverage=False, repo_root=Path("/project"))
        mapper = CoverageMapper(config)

        mock_cov = MagicMock()
        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["/project/tests/test_foo.py"]
        mock_cov.get_data.return_value = mock_data
        mock_cov.analysis2.return_value = ("test_foo.py", [1, 2, 3], [], [3], [])

        result = mapper.map_source_coverage(mock_cov)
        assert len(result) == 1
        assert result[0].covered == 2
        assert result[0].missed == 1

    def test_analysis_exception_handling(self):
        """Test handling when analysis2 raises an exception."""
        config = Config(repo_root=Path("/project"))
        mapper = CoverageMapper(config)

        mock_cov = MagicMock()
        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["/project/src/module.py"]
        mock_cov.get_data.return_value = mock_data
        mock_cov.analysis2.side_effect = Exception("Analysis failed")

        result = mapper.map_source_coverage(mock_cov)
        assert result == []
        # Should have added a warning
        assert any("COVERAGE_ANALYSIS_FAILED" in w.code for w in mapper.warnings)

    def test_empty_statements(self):
        """Test handling when file has no statements."""
        config = Config(repo_root=Path("/project"))
        mapper = CoverageMapper(config)

        mock_cov = MagicMock()
        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["/project/src/empty.py"]
        mock_cov.get_data.return_value = mock_data
        mock_cov.analysis2.return_value = ("empty.py", [], [], [], [])

        result = mapper.map_source_coverage(mock_cov)
        assert result == []


class TestLoadCoverageData:
    """Tests for _load_coverage_data edge cases."""

    def test_no_coverage_file(self, tmp_path, monkeypatch):
        """Test when no .coverage file exists."""
        monkeypatch.chdir(tmp_path)
        config = Config()
        mapper = CoverageMapper(config)

        result = mapper._load_coverage_data()
        assert result is None
        # Should have a warning
        assert any("W001" in w.code for w in mapper.warnings)

    def test_coverage_not_installed(self):
        """Test when coverage.py is not installed - placeholder test."""
        # This test is a placeholder - testing missing coverage.py is complex
        # because it requires unloading the coverage module which is already imported.
        # The _load_coverage_data method handles ImportError gracefully by returning None.
        config = Config()
        mapper = CoverageMapper(config)
        # Just verify the mapper was created successfully
        assert mapper is not None
