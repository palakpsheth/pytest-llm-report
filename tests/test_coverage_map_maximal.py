# SPDX-License-Identifier: MIT
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from pytest_llm_report.coverage_map import CoverageMapper
from pytest_llm_report.options import Config


class TestCoverageMapperMaximal:
    """Maximum coverage for CoverageMapper."""

    def test_extract_contexts_full_logic(self):
        """Should exercise all paths in _extract_contexts."""
        config = Config(omit_tests_from_coverage=True)
        mapper = CoverageMapper(config)

        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["app.py", "test_app.py", "README.md"]

        # Mock contexts_by_lineno
        mock_data.contexts_by_lineno.side_effect = (
            lambda p: {
                1: ["test_app.py::test_one|run"],
                2: ["test_app.py::test_two|run", "test_app.py::test_one|run"],
            }
            if p == "app.py"
            else {}
        )

        result = mapper._extract_contexts(mock_data)

        assert "test_app.py::test_one" in result
        assert "test_app.py::test_two" in result

        # Verify app.py is in test_one's coverage
        one_cov = [
            c for c in result["test_app.py::test_one"] if "app.py" in c.file_path
        ]
        assert len(one_cov) == 1
        assert one_cov[0].line_count == 2  # lines 1 and 2

    def test_map_source_coverage_comprehensive(self):
        """Should exercise all paths in map_source_coverage."""
        config = Config(omit_tests_from_coverage=False)
        mapper = CoverageMapper(config)

        mock_cov = MagicMock()
        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["app.py"]
        mock_cov.get_data.return_value = mock_data

        # Mock analysis2
        mock_cov.analysis2.return_value = ("app.py", [1, 2, 3], [], [2], [])

        entries = mapper.map_source_coverage(mock_cov)

        assert len(entries) == 1
        assert entries[0].file_path == "app.py"
        assert entries[0].statements == 3
        assert entries[0].covered == 2
        assert entries[0].missed == 1
        assert entries[0].coverage_percent == 66.67

    def test_extract_nodeid_variants(self):
        """Target missing lines in _extract_nodeid."""
        mapper = CoverageMapper(Config(include_phase="setup"))
        assert mapper._extract_nodeid("test.py::test|setup") == "test.py::test"
        assert mapper._extract_nodeid("test.py::test|run") is None  # filtered

        mapper = CoverageMapper(Config(include_phase="teardown"))
        assert mapper._extract_nodeid("test.py::test|teardown") == "test.py::test"
        assert mapper._extract_nodeid("test.py::test|run") is None  # filtered

        # Context without pipe
        assert (
            mapper._extract_nodeid("test.py::test_no_phase") == "test.py::test_no_phase"
        )

    def test_load_coverage_data_with_parallel_files(self):
        """Should handle parallel coverage files from xdist."""
        config = Config()
        mapper = CoverageMapper(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Create mock parallel coverage files
                Path(".coverage.gw0").touch()
                Path(".coverage.gw1").touch()

                # Mock coverage module's CoverageData
                with patch("coverage.CoverageData") as mock_data_cls:
                    mock_main_data = MagicMock()
                    mock_parallel_data1 = MagicMock()
                    mock_parallel_data2 = MagicMock()

                    # Return different mock instances
                    mock_data_cls.side_effect = [
                        mock_main_data,
                        mock_parallel_data1,
                        mock_parallel_data2,
                    ]

                    _ = mapper._load_coverage_data()

                    # Should have called update for parallel files
                    assert mock_main_data.update.call_count >= 2

            finally:
                os.chdir(old_cwd)

    def test_load_coverage_data_read_error(self):
        """Should handle errors reading coverage files."""
        config = Config()
        mapper = CoverageMapper(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Create a .coverage file
                Path(".coverage").touch()

                # Mock coverage module's CoverageData to raise an error on read
                with patch("coverage.CoverageData") as mock_data_cls:
                    mock_data = MagicMock()
                    mock_data.read.side_effect = Exception("Corrupt coverage file")
                    mock_data_cls.return_value = mock_data

                    result = mapper._load_coverage_data()

                    assert result is None
                    assert any(
                        "Failed to read coverage data" in w.message
                        for w in mapper.warnings
                    )

            finally:
                os.chdir(old_cwd)

    def test_load_coverage_data_no_files(self):
        """Should warn when no coverage files exist."""
        config = Config()
        mapper = CoverageMapper(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # No .coverage files
                result = mapper._load_coverage_data()

                assert result is None
                assert len(mapper.warnings) == 1
                assert mapper.warnings[0].code == "W001"

            finally:
                os.chdir(old_cwd)

    def test_map_coverage_no_data(self):
        """Should handle when _load_coverage_data returns None."""
        config = Config()
        mapper = CoverageMapper(config)

        with patch.object(mapper, "_load_coverage_data", return_value=None):
            result = mapper.map_coverage()

            # Should return empty dict when no data
            assert result == {}

    def test_map_source_coverage_analysis_error(self):
        """Should handle errors during analysis."""
        config = Config()
        mapper = CoverageMapper(config)

        mock_cov = MagicMock()
        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["app.py"]
        mock_cov.get_data.return_value = mock_data

        # Mock analysis2 to raise an error
        mock_cov.analysis2.side_effect = Exception("Analysis failed")

        entries = mapper.map_source_coverage(mock_cov)

        # Should skip files with errors
        assert len(entries) == 0

    def test_extract_contexts_no_contexts(self):
        """Should handle data with no test contexts."""
        config = Config()
        mapper = CoverageMapper(config)

        mock_data = MagicMock()
        mock_data.measured_files.return_value = ["app.py"]
        # contexts_by_lineno returns empty dict for all files
        mock_data.contexts_by_lineno.return_value = {}

        result = mapper._extract_contexts(mock_data)

        # Should return empty dict
        assert result == {}
