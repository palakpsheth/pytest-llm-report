# SPDX-License-Identifier: MIT
from unittest.mock import MagicMock


class TestPluginMaximal:
    """Targeted unit tests for plugin.py to reach maximal coverage."""

    def test_load_config_from_pytest(self):
        """Test config loading from pytest objects (CLI + INI)."""
        from pytest_llm_report.plugin import _load_config_from_pytest

        mock_config = MagicMock()
        mock_config.option.llm_report_html = "out.html"
        mock_config.option.llm_report_json = "out.json"

        mock_config.getini.side_effect = lambda key: None
        mock_config.rootpath = "/root"

        cfg = _load_config_from_pytest(mock_config)
        assert cfg.report_html == "out.html"

    def test_terminal_summary_worker_skip(self):
        """Test that terminal summary skips on xdist worker."""
        from pytest_llm_report.plugin import pytest_terminal_summary

        mock_config = MagicMock()
        mock_config.workerinput = {"workerid": "gw0"}  # Simulate xdist worker

        # Should return early without doing anything
        result = pytest_terminal_summary(MagicMock(), 0, mock_config)
        assert result is None

    def test_terminal_summary_disabled(self):
        """Test that terminal summary skips when plugin is disabled."""
        from pytest_llm_report.plugin import _enabled_key, pytest_terminal_summary

        mock_config = MagicMock()
        # No workerinput, so not a worker
        del mock_config.workerinput

        # Mock stash to return False for enabled
        mock_config.stash.get.return_value = False

        result = pytest_terminal_summary(MagicMock(), 0, mock_config)
        assert result is None

        # Should have checked if enabled
        mock_config.stash.get.assert_called_once_with(_enabled_key, False)
