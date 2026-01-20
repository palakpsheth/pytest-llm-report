# SPDX-License-Identifier: MIT
from unittest.mock import MagicMock, patch

import pytest


class TestPluginMaximal:
    """Targeted unit tests for plugin.py to reach maximal coverage."""

    def testload_config(self, tmp_path):
        """Test config loading from pytest objects (CLI)."""
        from pytest_llm_report.options import load_config

        mock_config = MagicMock()
        mock_config.option.llm_report_html = "out.html"
        mock_config.option.llm_report_json = "out.json"
        mock_config.option.llm_report_pdf = None
        mock_config.option.llm_evidence_bundle = None
        mock_config.option.llm_dependency_snapshot = None
        mock_config.option.llm_requests_per_minute = None
        mock_config.option.llm_aggregate_dir = None
        mock_config.option.llm_aggregate_policy = None
        mock_config.option.llm_aggregate_run_id = None
        mock_config.option.llm_aggregate_group_id = None
        mock_config.option.llm_max_retries = None
        mock_config.option.llm_coverage_source = None
        mock_config.option.llm_prompt_tier = None
        mock_config.option.llm_batch_parametrized = None
        mock_config.option.llm_context_compression = None
        mock_config.option.llm_context_bytes = None
        mock_config.option.llm_context_file_limit = None
        mock_config.option.llm_max_tests = None
        mock_config.option.llm_max_concurrency = None
        mock_config.option.llm_timeout_seconds = None
        mock_config.option.llm_capture_failed = None
        mock_config.option.llm_ollama_host = None
        mock_config.option.llm_litellm_api_base = None
        mock_config.option.llm_litellm_api_key = None
        mock_config.option.llm_litellm_token_refresh_command = None
        mock_config.option.llm_litellm_token_refresh_interval = None
        mock_config.option.llm_litellm_token_output_format = None
        mock_config.option.llm_litellm_token_json_key = None
        mock_config.option.llm_cache_dir = None
        mock_config.option.llm_cache_ttl = None
        mock_config.option.llm_metadata_file = None
        mock_config.option.llm_hmac_key_file = None
        mock_config.option.llm_include_params = None
        mock_config.option.llm_strip_docstrings = None

        mock_config.rootpath = tmp_path

        cfg = load_config(mock_config)
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


class TestPluginLoadConfig:
    """Tests for load_config with all option variations."""

    def test_load_config_from_pyproject(self, tmp_path):
        """Test loading all options from pyproject.toml."""
        from pytest_llm_report.options import load_config

        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "ollama"
model = "llama3.2"
context_mode = "complete"
requests_per_minute = 10
""")

        mock_config = MagicMock()
        # CLI options are None (not set)
        mock_config.option.llm_report_html = None
        mock_config.option.llm_report_json = None
        mock_config.option.llm_report_pdf = None
        mock_config.option.llm_evidence_bundle = None
        mock_config.option.llm_dependency_snapshot = None
        mock_config.option.llm_requests_per_minute = None
        mock_config.option.llm_aggregate_dir = None
        mock_config.option.llm_aggregate_policy = None
        mock_config.option.llm_aggregate_run_id = None
        mock_config.option.llm_aggregate_group_id = None
        mock_config.option.llm_max_retries = None
        mock_config.option.llm_coverage_source = None
        mock_config.option.llm_provider = None
        mock_config.option.llm_model = None
        mock_config.option.llm_context_mode = None
        mock_config.option.llm_prompt_tier = None
        mock_config.option.llm_batch_parametrized = None
        mock_config.option.llm_context_compression = None
        mock_config.option.llm_context_bytes = None
        mock_config.option.llm_context_file_limit = None
        mock_config.option.llm_max_tests = None
        mock_config.option.llm_max_concurrency = None
        mock_config.option.llm_timeout_seconds = None
        mock_config.option.llm_capture_failed = None
        mock_config.option.llm_ollama_host = None
        mock_config.option.llm_litellm_api_base = None
        mock_config.option.llm_litellm_api_key = None
        mock_config.option.llm_litellm_token_refresh_command = None
        mock_config.option.llm_litellm_token_refresh_interval = None
        mock_config.option.llm_litellm_token_output_format = None
        mock_config.option.llm_litellm_token_json_key = None
        mock_config.option.llm_cache_dir = None
        mock_config.option.llm_cache_ttl = None
        mock_config.option.llm_metadata_file = None
        mock_config.option.llm_hmac_key_file = None
        mock_config.option.llm_include_params = None
        mock_config.option.llm_strip_docstrings = None

        mock_config.rootpath = tmp_path

        cfg = load_config(mock_config)

        assert cfg.provider == "ollama"
        assert cfg.model == "llama3.2"
        assert cfg.llm_context_mode == "complete"
        assert cfg.llm_requests_per_minute == 10

    def test_load_config_cli_overrides_pyproject(self, tmp_path):
        """Test CLI options override pyproject.toml options."""
        from pytest_llm_report.options import load_config

        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "ollama"
""")

        mock_config = MagicMock()
        # CLI overrides
        mock_config.option.llm_report_html = "cli.html"
        mock_config.option.llm_report_json = "cli.json"
        mock_config.option.llm_report_pdf = "cli.pdf"
        mock_config.option.llm_evidence_bundle = "bundle.zip"
        mock_config.option.llm_dependency_snapshot = "deps.json"
        mock_config.option.llm_requests_per_minute = 20
        mock_config.option.llm_aggregate_dir = "/agg"
        mock_config.option.llm_aggregate_policy = "merge"
        mock_config.option.llm_aggregate_run_id = "run-123"
        mock_config.option.llm_aggregate_group_id = "group-abc"
        mock_config.option.llm_max_retries = None
        mock_config.option.llm_coverage_source = None
        mock_config.option.llm_prompt_tier = None
        mock_config.option.llm_batch_parametrized = None
        mock_config.option.llm_context_compression = None
        mock_config.option.llm_context_bytes = None
        mock_config.option.llm_context_file_limit = None
        mock_config.option.llm_max_tests = None
        mock_config.option.llm_max_concurrency = None
        mock_config.option.llm_timeout_seconds = None
        mock_config.option.llm_capture_failed = None
        mock_config.option.llm_ollama_host = None
        mock_config.option.llm_litellm_api_base = None
        mock_config.option.llm_litellm_api_key = None
        mock_config.option.llm_litellm_token_refresh_command = None
        mock_config.option.llm_litellm_token_refresh_interval = None
        mock_config.option.llm_litellm_token_output_format = None
        mock_config.option.llm_litellm_token_json_key = None
        mock_config.option.llm_cache_dir = None
        mock_config.option.llm_cache_ttl = None
        mock_config.option.llm_metadata_file = None
        mock_config.option.llm_hmac_key_file = None
        mock_config.option.llm_include_params = None
        mock_config.option.llm_strip_docstrings = None

        mock_config.rootpath = tmp_path

        cfg = load_config(mock_config)

        assert cfg.report_html == "cli.html"
        assert cfg.report_json == "cli.json"
        assert cfg.report_pdf == "cli.pdf"
        assert cfg.report_evidence_bundle == "bundle.zip"
        assert cfg.report_dependency_snapshot == "deps.json"
        assert cfg.llm_requests_per_minute == 20
        assert cfg.aggregate_dir == "/agg"
        assert cfg.aggregate_policy == "merge"
        assert cfg.aggregate_run_id == "run-123"
        assert cfg.aggregate_group_id == "group-abc"


class TestPluginConfigure:
    """Tests for pytest_configure hook."""

    def test_pytest_configure_worker_skip(self):
        """Test that configure skips on xdist workers."""
        from pytest_llm_report.plugin import pytest_configure

        mock_config = MagicMock()
        mock_config.workerinput = {"workerid": "gw0"}

        # Should return early without calling addinivalue_line
        pytest_configure(mock_config)
        # addinivalue_line is still called for markers before worker check
        assert mock_config.addinivalue_line.called

    def test_pytest_configure_validation_errors(self, tmp_path):
        """Test that validation errors raise UsageError."""
        from pytest_llm_report.plugin import pytest_configure

        # Create invalid pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "invalid_provider"
""")

        mock_config = MagicMock()
        del mock_config.workerinput  # Not a worker

        mock_config.option.llm_report_html = None
        mock_config.option.llm_report_json = None
        mock_config.option.llm_report_pdf = None
        mock_config.option.llm_evidence_bundle = None
        mock_config.option.llm_dependency_snapshot = None
        mock_config.option.llm_requests_per_minute = None
        mock_config.option.llm_aggregate_dir = None
        mock_config.option.llm_aggregate_policy = None
        mock_config.option.llm_aggregate_run_id = None
        mock_config.option.llm_aggregate_group_id = None
        mock_config.option.llm_max_retries = None
        mock_config.option.llm_coverage_source = None
        mock_config.option.llm_provider = None
        mock_config.option.llm_model = None
        mock_config.option.llm_context_mode = None
        mock_config.option.llm_prompt_tier = None
        mock_config.option.llm_batch_parametrized = None
        mock_config.option.llm_context_compression = None
        mock_config.option.llm_context_bytes = None
        mock_config.option.llm_context_file_limit = None
        mock_config.option.llm_max_tests = None
        mock_config.option.llm_max_concurrency = None
        mock_config.option.llm_timeout_seconds = None
        mock_config.option.llm_capture_failed = None
        mock_config.option.llm_ollama_host = None
        mock_config.option.llm_litellm_api_base = None
        mock_config.option.llm_litellm_api_key = None
        mock_config.option.llm_litellm_token_refresh_command = None
        mock_config.option.llm_litellm_token_refresh_interval = None
        mock_config.option.llm_litellm_token_output_format = None
        mock_config.option.llm_litellm_token_json_key = None
        mock_config.option.llm_cache_dir = None
        mock_config.option.llm_cache_ttl = None
        mock_config.option.llm_metadata_file = None
        mock_config.option.llm_hmac_key_file = None
        mock_config.option.llm_include_params = None
        mock_config.option.llm_strip_docstrings = None

        mock_config.rootpath = tmp_path
        mock_config.stash = {}

        with pytest.raises(pytest.UsageError, match="configuration errors"):
            pytest_configure(mock_config)

    def test_pytest_configure_llm_enabled_warning(self, tmp_path):
        """Test that LLM enabled warning is raised."""
        from pytest_llm_report.plugin import pytest_configure

        # Create valid pyproject.toml with LLM enabled
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "ollama"
model = "llama3.2"
context_mode = "minimal"
""")

        mock_config = MagicMock()
        del mock_config.workerinput

        mock_config.option.llm_report_html = None
        mock_config.option.llm_report_json = None
        mock_config.option.llm_report_pdf = None
        mock_config.option.llm_evidence_bundle = None
        mock_config.option.llm_dependency_snapshot = None
        mock_config.option.llm_requests_per_minute = None
        mock_config.option.llm_aggregate_dir = None
        mock_config.option.llm_aggregate_policy = None
        mock_config.option.llm_aggregate_run_id = None
        mock_config.option.llm_aggregate_group_id = None
        mock_config.option.llm_max_retries = None
        mock_config.option.llm_coverage_source = None
        mock_config.option.llm_provider = None
        mock_config.option.llm_model = None
        mock_config.option.llm_context_mode = None
        mock_config.option.llm_prompt_tier = None
        mock_config.option.llm_batch_parametrized = None
        mock_config.option.llm_context_compression = None
        mock_config.option.llm_context_bytes = None
        mock_config.option.llm_context_file_limit = None
        mock_config.option.llm_max_tests = None
        mock_config.option.llm_max_concurrency = None
        mock_config.option.llm_timeout_seconds = None
        mock_config.option.llm_capture_failed = None
        mock_config.option.llm_ollama_host = None
        mock_config.option.llm_litellm_api_base = None
        mock_config.option.llm_litellm_api_key = None
        mock_config.option.llm_litellm_token_refresh_command = None
        mock_config.option.llm_litellm_token_refresh_interval = None
        mock_config.option.llm_litellm_token_output_format = None
        mock_config.option.llm_litellm_token_json_key = None
        mock_config.option.llm_cache_dir = None
        mock_config.option.llm_cache_ttl = None
        mock_config.option.llm_metadata_file = None
        mock_config.option.llm_hmac_key_file = None
        mock_config.option.llm_include_params = None
        mock_config.option.llm_strip_docstrings = None

        mock_config.rootpath = tmp_path
        mock_config.stash = {}

        with pytest.warns(UserWarning, match="LLM provider 'ollama' is enabled"):
            pytest_configure(mock_config)


class TestPluginSessionHooks:
    """Tests for session-level hooks."""

    def test_pytest_sessionstart_disabled(self):
        """Test sessionstart skips when disabled."""
        from pytest_llm_report.plugin import _enabled_key, pytest_sessionstart

        mock_session = MagicMock()
        mock_session.config.stash.get.return_value = False

        pytest_sessionstart(mock_session)

        # Should have checked enabled status
        mock_session.config.stash.get.assert_called_with(_enabled_key, False)

    def test_pytest_sessionstart_enabled(self):
        """Test sessionstart initializes collector when enabled."""
        from pytest_llm_report.options import Config
        from pytest_llm_report.plugin import (
            _collector_key,
            _config_key,
            _enabled_key,
            _start_time_key,
            pytest_sessionstart,
        )

        mock_session = MagicMock()
        stash_dict = {}
        stash_dict[_enabled_key] = True
        stash_dict[_config_key] = Config()

        # Create a proper stash that supports both get() and []
        class MockStash(dict):
            pass

        mock_stash = MockStash(stash_dict)
        mock_session.config.stash = mock_stash

        pytest_sessionstart(mock_session)

        # Collector should be created
        assert _collector_key in mock_stash
        assert _start_time_key in mock_stash

    def test_pytest_collection_finish_disabled(self):
        """Test collection_finish skips when disabled."""
        from pytest_llm_report.plugin import _enabled_key, pytest_collection_finish

        mock_session = MagicMock()
        mock_session.config.stash.get.return_value = False

        pytest_collection_finish(mock_session)
        mock_session.config.stash.get.assert_called_with(_enabled_key, False)

    def test_pytest_collection_finish_enabled(self):
        """Test collection_finish calls collector when enabled."""
        from pytest_llm_report.plugin import (
            _collector_key,
            _enabled_key,
            pytest_collection_finish,
        )

        mock_session = MagicMock()
        mock_collector = MagicMock()

        def stash_get(key, default=None):
            if key == _enabled_key:
                return True
            if key == _collector_key:
                return mock_collector
            return default

        mock_session.config.stash.get = stash_get
        mock_session.items = [MagicMock(), MagicMock()]

        pytest_collection_finish(mock_session)

        mock_collector.handle_collection_finish.assert_called_once_with(
            mock_session.items
        )


class TestPluginCollectReport:
    """Tests for pytest_collectreport hook."""

    def test_pytest_collectreport_no_session(self):
        """Test collectreport skips when session not available."""
        from pytest_llm_report.plugin import pytest_collectreport

        mock_report = MagicMock()
        del mock_report.session  # No session attribute

        # Should not raise
        pytest_collectreport(mock_report)

    def test_pytest_collectreport_session_none(self):
        """Test collectreport skips when session is None."""
        from pytest_llm_report.plugin import pytest_collectreport

        mock_report = MagicMock()
        mock_report.session = None

        # Should not raise
        pytest_collectreport(mock_report)

    def test_pytest_collectreport_disabled(self):
        """Test collectreport skips when disabled."""
        from pytest_llm_report.plugin import _enabled_key, pytest_collectreport

        mock_report = MagicMock()
        mock_report.session.config.stash.get.return_value = False

        pytest_collectreport(mock_report)
        mock_report.session.config.stash.get.assert_called_with(_enabled_key, False)

    def test_pytest_collectreport_enabled(self):
        """Test collectreport calls collector when enabled."""
        from pytest_llm_report.plugin import (
            _collector_key,
            _enabled_key,
            pytest_collectreport,
        )

        mock_report = MagicMock()
        mock_collector = MagicMock()

        def stash_get(key, default=None):
            if key == _enabled_key:
                return True
            if key == _collector_key:
                return mock_collector
            return default

        mock_report.session.config.stash.get = stash_get

        pytest_collectreport(mock_report)

        mock_collector.handle_collection_report.assert_called_once_with(mock_report)


class TestPluginRuntest:
    """Tests for pytest_runtest_makereport hook."""

    def test_runtest_makereport_disabled(self):
        """Test makereport skips when disabled."""
        from pytest_llm_report.plugin import pytest_runtest_makereport

        mock_item = MagicMock()
        mock_item.config.stash.get.return_value = False
        mock_call = MagicMock()

        # This is a hookwrapper, need to handle the generator
        gen = pytest_runtest_makereport(mock_item, mock_call)
        next(gen)  # yield point

        # Send a result and complete
        mock_outcome = MagicMock()
        mock_outcome.get_result.return_value = MagicMock()
        try:
            gen.send(mock_outcome)
        except StopIteration:
            pass

    def test_runtest_makereport_enabled(self):
        """Test makereport calls collector when enabled."""
        from pytest_llm_report.plugin import (
            _collector_key,
            _enabled_key,
            pytest_runtest_makereport,
        )

        mock_item = MagicMock()
        mock_collector = MagicMock()

        def stash_get(key, default=None):
            if key == _enabled_key:
                return True
            if key == _collector_key:
                return mock_collector
            return default

        mock_item.config.stash.get = stash_get
        mock_call = MagicMock()
        mock_report = MagicMock()

        gen = pytest_runtest_makereport(mock_item, mock_call)
        next(gen)  # yield point

        mock_outcome = MagicMock()
        mock_outcome.get_result.return_value = mock_report
        try:
            gen.send(mock_outcome)
        except StopIteration:
            pass

        mock_collector.handle_runtest_logreport.assert_called_once_with(
            mock_report, mock_item
        )


class TestPluginTerminalSummary:
    """Tests for pytest_terminal_summary hook - full flow coverage."""

    def test_terminal_summary_with_aggregation(self):
        """Test terminal summary with aggregation enabled."""
        from pytest_llm_report.options import Config
        from pytest_llm_report.plugin import (
            _config_key,
            _enabled_key,
            pytest_terminal_summary,
        )

        mock_config = MagicMock()
        del mock_config.workerinput  # Not a worker

        cfg = Config(
            report_html="out.html",
            report_json="out.json",
            aggregate_dir="/agg",
        )

        # Create a proper stash that supports both get() and []
        class MockStash(dict):
            pass

        stash = MockStash({_enabled_key: True, _config_key: cfg})
        mock_config.stash = stash

        mock_terminalreporter = MagicMock()

        with patch("pytest_llm_report.aggregation.Aggregator") as mock_agg_cls:
            mock_agg = MagicMock()
            mock_agg.aggregate.return_value = MagicMock()  # Return a report
            mock_agg_cls.return_value = mock_agg

            with patch(
                "pytest_llm_report.report_writer.ReportWriter"
            ) as mock_writer_cls:
                mock_writer = MagicMock()
                mock_writer_cls.return_value = mock_writer

                pytest_terminal_summary(mock_terminalreporter, 0, mock_config)

                mock_agg.aggregate.assert_called_once()
                mock_writer.write_json.assert_called_once()
                mock_writer.write_html.assert_called_once()

    def test_terminal_summary_no_collector(self):
        """Test terminal summary creates collector if missing."""
        from pytest_llm_report.options import Config
        from pytest_llm_report.plugin import (
            _config_key,
            _enabled_key,
            pytest_terminal_summary,
        )

        mock_config = MagicMock()
        del mock_config.workerinput

        cfg = Config(report_html="out.html")

        # Create a proper stash that supports both get() and []
        class MockStash(dict):
            pass

        stash = MockStash({_enabled_key: True, _config_key: cfg})
        mock_config.stash = stash

        mock_terminalreporter = MagicMock()

        with patch("pytest_llm_report.report_writer.ReportWriter") as mock_writer_cls:
            mock_writer = MagicMock()
            mock_writer_cls.return_value = mock_writer

            with patch(
                "pytest_llm_report.coverage_map.CoverageMapper"
            ) as mock_mapper_cls:
                mock_mapper = MagicMock()
                mock_mapper.map_coverage.return_value = {}
                mock_mapper_cls.return_value = mock_mapper

                pytest_terminal_summary(mock_terminalreporter, 0, mock_config)

    def test_terminal_summary_llm_enabled(self):
        """Test terminal summary with LLM enabled runs annotations."""
        from pytest_llm_report.options import Config
        from pytest_llm_report.plugin import (
            _config_key,
            _enabled_key,
            pytest_terminal_summary,
        )

        mock_config = MagicMock()
        del mock_config.workerinput

        # Provider enabled
        cfg = Config(provider="ollama", report_html="out.html")
        stash = {_enabled_key: True, _config_key: cfg}

        # Proper stash mock
        class MockStash(dict):
            pass

        mock_config.stash = MockStash(stash)

        mock_terminalreporter = MagicMock()
        mock_terminalreporter.stats = {}

        # Patch dependencies at source
        with (
            patch("pytest_llm_report.coverage_map.CoverageMapper"),
            patch("pytest_llm_report.report_writer.ReportWriter") as mock_writer_cls,
            patch("pytest_llm_report.llm.annotator.annotate_tests") as mock_annotate,
            patch("pytest_llm_report.llm.base.get_provider") as mock_get_provider,
        ):
            mock_writer = MagicMock()
            mock_writer_cls.return_value = mock_writer

            mock_provider = MagicMock()
            mock_provider.get_model_name.return_value = "gpt-4"
            mock_get_provider.return_value = mock_provider

            pytest_terminal_summary(mock_terminalreporter, 0, mock_config)

            mock_annotate.assert_called_once()
            assert mock_annotate.call_args[0][1] == cfg  # Verify config passed

    def test_terminal_summary_coverage_calculation(self):
        """Test coverage percentage calculation logic."""
        from pytest_llm_report.options import Config
        from pytest_llm_report.plugin import (
            _config_key,
            _enabled_key,
            pytest_terminal_summary,
        )

        mock_config = MagicMock()
        del mock_config.workerinput
        cfg = Config(report_html="out.html")
        stash = {_enabled_key: True, _config_key: cfg}

        class MockStash(dict):
            pass

        mock_config.stash = MockStash(stash)

        # Mock coverage file existence and Coverage class
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("coverage.Coverage") as mock_cov_cls,
            patch("pytest_llm_report.coverage_map.CoverageMapper"),
            patch("pytest_llm_report.report_writer.ReportWriter"),
        ):
            mock_cov = MagicMock()
            mock_cov_cls.return_value = mock_cov
            mock_cov.report.return_value = 85.5

            pytest_terminal_summary(MagicMock(), 0, mock_config)

            mock_cov.load.assert_called_once()
            mock_cov.report.assert_called_once()

    def test_pytest_addoption(self):
        """Test pytest_addoption adds expected arguments."""
        from pytest_llm_report.plugin import pytest_addoption

        parser = MagicMock()
        group = MagicMock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        parser.getgroup.assert_called_with("llm-report", "LLM-enhanced test reports")
        # Verify specific option
        calls = [c[0] for c in group.addoption.call_args_list]
        assert any("--llm-report" in args[0] for args in calls)
        assert any("--llm-coverage-source" in args[0] for args in calls)

    def test_pytest_addoption_no_ini(self):
        """Test pytest_addoption no longer adds INI options."""
        from pytest_llm_report.plugin import pytest_addoption

        parser = MagicMock()
        pytest_addoption(parser)
        # Verify NO ini additions (we removed them)
        assert not parser.addini.called


class TestPluginTerminalSummaryErrors:
    """Tests for error branches in terminal summary."""

    def test_terminal_summary_coverage_error(self):
        """Test coverage calculation error (lines 322-328)."""
        from pytest_llm_report.options import Config
        from pytest_llm_report.plugin import (
            _config_key,
            _enabled_key,
            pytest_terminal_summary,
        )

        mock_config = MagicMock()
        del mock_config.workerinput
        cfg = Config(report_html="out.html", llm_coverage_source=".coverage")
        mock_config.stash = {_enabled_key: True, _config_key: cfg}

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("coverage.Coverage") as mock_cov_cls,
            patch("pytest_llm_report.coverage_map.CoverageMapper"),
            patch("pytest_llm_report.report_writer.ReportWriter"),
        ):
            mock_cov = MagicMock()
            mock_cov_cls.return_value = mock_cov
            # Force OSError during load
            mock_cov.load.side_effect = OSError("Disk full")

            with pytest.warns(
                UserWarning, match="Failed to compute coverage percentage"
            ):
                pytest_terminal_summary(MagicMock(), 0, mock_config)


class TestPluginConfigureFallback:
    """Tests for configuration fallback paths."""

    def test_pytest_configure_fallback_load(self, tmp_path):
        """Test fallback to load_config if Config.load is missing."""
        from pytest_llm_report.plugin import pytest_configure

        mock_config = MagicMock()
        del mock_config.workerinput
        mock_config.stash = {}
        mock_config.option.llm_report_html = None
        mock_config.option.llm_report_json = None
        mock_config.option.llm_report_pdf = None
        mock_config.option.llm_evidence_bundle = None
        mock_config.option.llm_dependency_snapshot = None
        mock_config.option.llm_requests_per_minute = None
        mock_config.option.llm_aggregate_dir = None
        mock_config.option.llm_aggregate_policy = None
        mock_config.option.llm_aggregate_run_id = None
        mock_config.option.llm_aggregate_group_id = None
        mock_config.option.llm_max_retries = None
        mock_config.option.llm_coverage_source = None
        mock_config.option.llm_provider = None
        mock_config.option.llm_model = None
        mock_config.option.llm_context_mode = None
        mock_config.option.llm_prompt_tier = None
        mock_config.option.llm_batch_parametrized = None
        mock_config.option.llm_context_compression = None
        mock_config.option.llm_context_bytes = None
        mock_config.option.llm_context_file_limit = None
        mock_config.option.llm_max_tests = None
        mock_config.option.llm_max_concurrency = None
        mock_config.option.llm_timeout_seconds = None
        mock_config.option.llm_capture_failed = None
        mock_config.option.llm_ollama_host = None
        mock_config.option.llm_litellm_api_base = None
        mock_config.option.llm_litellm_api_key = None
        mock_config.option.llm_litellm_token_refresh_command = None
        mock_config.option.llm_litellm_token_refresh_interval = None
        mock_config.option.llm_litellm_token_output_format = None
        mock_config.option.llm_litellm_token_json_key = None
        mock_config.option.llm_cache_dir = None
        mock_config.option.llm_cache_ttl = None
        mock_config.option.llm_metadata_file = None
        mock_config.option.llm_hmac_key_file = None
        mock_config.option.llm_include_params = None
        mock_config.option.llm_strip_docstrings = None

        mock_config.rootpath = tmp_path

        with (
            patch("pytest_llm_report.options.Config", spec=[]),  # No load() method
            patch("pytest_llm_report.options.load_config") as mock_load,
        ):
            mock_cfg = MagicMock()
            mock_cfg.validate.return_value = []
            mock_load.return_value = mock_cfg
            pytest_configure(mock_config)
            mock_load.assert_called_once()
