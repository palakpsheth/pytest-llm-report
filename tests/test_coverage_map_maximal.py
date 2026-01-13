# SPDX-License-Identifier: MIT
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
        # app.py has contexts
        mock_data.contexts_by_lineno.side_effect = (
            lambda p: {
                1: ["test_app.py::test_one|run"],
                2: ["test_app.py::test_two|run", "test_app.py::test_one|run"],
            }
            if p == "app.py"
            else {}
        )

        # Force has_contexts to True check
        # First call to contexts_by_lineno in the check loop
        # Then calls in the main loop

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
        # filename, statements, excluded, missing, missing_branches
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

    def test_load_coverage_data_missing_coverage_lib(self):
        """Should handle missing coverage library."""
        config = Config()
        mapper = CoverageMapper(config)

        # Mock import failure
        with patch(
            "builtins.__import__",
            side_effect=lambda name, *args, **kwargs: MagicMock()
            if name != "coverage"
            else exec("raise ImportError"),
        ):
            result = mapper._load_coverage_data()
            assert result is None
            assert any(
                "coverage.py not installed" in w.message for w in mapper.warnings
            )
