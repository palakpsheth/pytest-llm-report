# SPDX-License-Identifier: MIT
"""Tests for pytest_llm_report.coverage_map module."""

from pytest_llm_report.coverage_map import CoverageMapper
from pytest_llm_report.options import Config


class TestCoverageMapper:
    """Tests for CoverageMapper class."""

    def test_create_mapper(self):
        """Mapper should initialize with config."""
        config = Config()
        mapper = CoverageMapper(config)
        assert mapper.config is config
        assert mapper.warnings == []

    def test_map_coverage_no_coverage_file(self):
        """Should return empty dict when no coverage file."""
        from unittest.mock import patch

        config = Config()
        mapper = CoverageMapper(config)

        # Mock Path.exists to return False and glob to return empty
        with patch("pytest_llm_report.coverage_map.Path.exists", return_value=False):
            with patch("pytest_llm_report.coverage_map.glob.glob", return_value=[]):
                result = mapper.map_coverage()

                assert result == {}
                # Should have at least one warning
                assert len(mapper.warnings) >= 1

    def test_get_warnings(self):
        """Should return list of warnings."""
        config = Config()
        mapper = CoverageMapper(config)
        warnings = mapper.get_warnings()
        assert isinstance(warnings, list)


class TestCoverageMapperContextExtraction:
    """Tests for context extraction in CoverageMapper."""

    def test_extract_nodeid_with_run_phase(self):
        """Should extract nodeid from run phase context."""
        config = Config(include_phase="run")
        mapper = CoverageMapper(config)

        nodeid = mapper._extract_nodeid("test.py::test_foo|run")
        assert nodeid == "test.py::test_foo"

    def test_extract_nodeid_filters_setup(self):
        """Should filter out setup phase when include_phase=run."""
        config = Config(include_phase="run")
        mapper = CoverageMapper(config)

        nodeid = mapper._extract_nodeid("test.py::test_foo|setup")
        assert nodeid is None

    def test_extract_nodeid_all_phases(self):
        """Should include all phases when include_phase=all."""
        config = Config(include_phase="all")
        mapper = CoverageMapper(config)

        assert mapper._extract_nodeid("test.py::test_foo|run") == "test.py::test_foo"
        assert mapper._extract_nodeid("test.py::test_foo|setup") == "test.py::test_foo"
        assert (
            mapper._extract_nodeid("test.py::test_foo|teardown") == "test.py::test_foo"
        )

    def test_extract_nodeid_empty_context(self):
        """Should return None for empty context."""
        config = Config()
        mapper = CoverageMapper(config)

        assert mapper._extract_nodeid("") is None
        assert mapper._extract_nodeid(None) is None
