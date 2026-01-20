from unittest.mock import MagicMock

import pytest

from pytest_llm_report.options import Config, get_default_config, load_config


class TestConfig:
    def test_default_values(self):
        """Test that default values are set correctly."""
        cfg = Config()
        assert cfg.provider == "none"
        assert cfg.llm_context_mode == "minimal"
        assert cfg.llm_max_tests == 0
        assert cfg.llm_max_retries == 10
        # Additional defaults
        assert cfg.llm_context_bytes == 32000
        assert cfg.llm_context_file_limit == 10
        assert cfg.llm_requests_per_minute == 5
        assert cfg.llm_timeout_seconds == 30
        assert cfg.llm_cache_ttl_seconds == 86400
        assert cfg.include_phase == "run"
        assert cfg.aggregate_policy == "latest"
        assert cfg.is_llm_enabled() is False
        assert cfg.omit_tests_from_coverage is True

    def test_default_exclude_globs(self):
        """Should have correct default exclude globs."""
        config = Config()
        defaults = config.llm_context_exclude_globs
        assert "*.pyc" in defaults
        assert "__pycache__/*" in defaults
        assert "*secret*" in defaults
        assert "*password*" in defaults

    def test_default_redact_patterns(self):
        """Should have correct default redact patterns."""
        config = Config()
        patterns = config.invocation_redact_patterns
        assert any("--password" in p for p in patterns)
        assert any("--token" in p for p in patterns)
        assert any("--api[_-]?key" in p for p in patterns)

    def test_is_llm_enabled(self):
        """Test is_llm_enabled check."""
        assert Config(provider="none").is_llm_enabled() is False
        assert Config(provider="ollama").is_llm_enabled() is True
        assert Config(provider="litellm").is_llm_enabled() is True
        assert Config(provider="gemini").is_llm_enabled() is True
        cfg = Config()
        assert not cfg.is_llm_enabled()
        cfg.provider = "ollama"
        assert cfg.is_llm_enabled()

    def test_get_default_config(self):
        """Test the factory function."""
        cfg = get_default_config()
        assert isinstance(cfg, Config)
        assert cfg.provider == "none"

    def test_validate_valid_config(self):
        """Test validation with a valid configuration."""
        cfg = Config()
        errors = cfg.validate()
        assert not errors

    def test_validate_invalid_provider(self):
        """Test validation with an invalid provider."""
        cfg = Config(provider="invalid_provider")
        errors = cfg.validate()
        assert len(errors) == 1
        assert "Invalid provider 'invalid_provider'" in errors[0]

    def test_validate_invalid_context_mode(self):
        """Test validation with an invalid context mode."""
        cfg = Config(llm_context_mode="mega_max")
        errors = cfg.validate()
        assert len(errors) == 1
        assert "Invalid llm_context_mode 'mega_max'" in errors[0]

    def test_validate_invalid_aggregate_policy(self):
        """Test validation with an invalid aggregation policy."""
        cfg = Config(aggregate_policy="random")
        errors = cfg.validate()
        assert len(errors) == 1
        assert "Invalid aggregate_policy 'random'" in errors[0]

    def test_validate_invalid_include_phase(self):
        """Test validation with an invalid include phase."""
        cfg = Config(include_phase="lunch_break")
        errors = cfg.validate()
        assert len(errors) == 1
        assert "Invalid include_phase 'lunch_break'" in errors[0]

    def test_validate_numeric_ranges(self):
        """Test validation of numeric constraints."""
        cfg = Config(
            llm_context_bytes=500,  # < 1000
            llm_max_tests=-1,
            llm_requests_per_minute=0,
            llm_timeout_seconds=0,
            llm_max_retries=-1,
        )
        errors = cfg.validate()
        assert len(errors) >= 5
        assert "llm_context_bytes must be at least 1000" in errors
        assert "llm_max_tests must be 0 (no limit) or positive" in errors
        assert "llm_requests_per_minute must be at least 1" in errors
        assert "llm_timeout_seconds must be at least 1" in errors
        assert "llm_max_retries must be 0 or positive" in errors


class TestLoadConfig:
    @pytest.fixture
    def mock_pytest_config(self, tmp_path):
        config = MagicMock()
        # Mock CLI options as an object with attributes
        config.option = MagicMock()
        # Set all potential CLI options to None by default
        for attr in [
            "llm_report_html",
            "llm_report_json",
            "llm_report_pdf",
            "llm_evidence_bundle",
            "llm_dependency_snapshot",
            "llm_requests_per_minute",
            "llm_aggregate_dir",
            "llm_aggregate_policy",
            "llm_aggregate_run_id",
            "llm_aggregate_group_id",
            "llm_coverage_source",
            "llm_max_retries",
            "llm_provider",
            "llm_model",
            "llm_context_mode",
            # Token Optimization CLI Flags
            "llm_prompt_tier",
            "llm_batch_parametrized",
            "llm_context_compression",
        ]:
            setattr(config.option, attr, None)

        config.rootpath = tmp_path
        return config

    def test_load_defaults(self, mock_pytest_config):
        """Test loading configuration when no options are set."""
        cfg = load_config(mock_pytest_config)
        assert cfg.provider == "none"
        assert cfg.report_html is None

    def test_load_from_pyproject(self, tmp_path):
        """Test loading values from pyproject.toml."""

        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "ollama"
model = "llama3"
context_mode = "balanced"
requests_per_minute = 10
max_retries = 2
""")

        # Mock config
        from unittest.mock import MagicMock

        mock_pytest_config = MagicMock()
        for attr in [
            "llm_report_html",
            "llm_report_json",
            "llm_report_pdf",
            "llm_evidence_bundle",
            "llm_dependency_snapshot",
            "llm_requests_per_minute",
            "llm_aggregate_dir",
            "llm_aggregate_policy",
            "llm_aggregate_run_id",
            "llm_aggregate_group_id",
            "llm_coverage_source",
            "llm_max_retries",
            # New Core CLI Flags
            "llm_provider",
            "llm_model",
            "llm_context_mode",
            # Token Optimization CLI Flags
            "llm_prompt_tier",
            "llm_batch_parametrized",
            "llm_context_compression",
        ]:
            setattr(mock_pytest_config.option, attr, None)
        mock_pytest_config.rootpath = tmp_path

        cfg = load_config(mock_pytest_config)
        assert cfg.provider == "ollama"
        assert cfg.model == "llama3"
        assert cfg.llm_context_mode == "balanced"
        assert cfg.llm_requests_per_minute == 10
        assert cfg.llm_max_retries == 2

    def test_load_config_missing_pyproject(self, tmp_path):
        """Test handling when pyproject.toml doesn't exist."""
        from unittest.mock import MagicMock

        mock_pytest_config = MagicMock()
        for attr in [
            "llm_report_html",
            "llm_report_json",
            "llm_report_pdf",
            "llm_evidence_bundle",
            "llm_dependency_snapshot",
            "llm_requests_per_minute",
            "llm_aggregate_dir",
            "llm_aggregate_policy",
            "llm_aggregate_run_id",
            "llm_aggregate_group_id",
            "llm_coverage_source",
            "llm_max_retries",
            # New Core CLI Flags
            "llm_provider",
            "llm_model",
            "llm_context_mode",
            # Token Optimization CLI Flags
            "llm_prompt_tier",
            "llm_batch_parametrized",
            "llm_context_compression",
        ]:
            setattr(mock_pytest_config.option, attr, None)
        mock_pytest_config.rootpath = tmp_path  # No pyproject.toml here

        cfg = load_config(mock_pytest_config)
        # Should fallback to defaults
        assert cfg.llm_max_retries == 10

    def test_load_from_cli_overrides_pyproject(self, tmp_path):
        """Test that CLI options override pyproject.toml options."""
        from unittest.mock import MagicMock

        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "ollama"
""")

        # Mock config
        mock_pytest_config = MagicMock()
        # Set CLI values
        mock_pytest_config.option.llm_report_html = "cli_report.html"
        mock_pytest_config.option.llm_requests_per_minute = 100
        for attr in [
            "llm_report_json",
            "llm_report_pdf",
            "llm_evidence_bundle",
            "llm_dependency_snapshot",
            "llm_aggregate_dir",
            "llm_aggregate_policy",
            "llm_aggregate_run_id",
            "llm_aggregate_group_id",
            "llm_coverage_source",
            "llm_max_retries",
            # New Core CLI Flags
            "llm_provider",
            "llm_model",
            "llm_context_mode",
            # Token Optimization CLI Flags
            "llm_prompt_tier",
            "llm_batch_parametrized",
            "llm_context_compression",
        ]:
            setattr(mock_pytest_config.option, attr, None)
        mock_pytest_config.rootpath = tmp_path

        cfg = load_config(mock_pytest_config)

        # CLI should win for html
        assert cfg.report_html == "cli_report.html"
        # CLI should set values not in pyproject
        assert cfg.llm_requests_per_minute == 100

    def test_load_from_cli_provider_override(self, tmp_path):
        """Test that CLI provider option overrides pyproject.toml."""
        from unittest.mock import MagicMock

        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "none"
model = "base"
""")

        # Mock config
        mock_pytest_config = MagicMock()

        # Reset other options
        for attr in [
            "llm_report_html",
            "llm_report_json",
            "llm_report_pdf",
            "llm_evidence_bundle",
            "llm_dependency_snapshot",
            "llm_requests_per_minute",
            "llm_aggregate_dir",
            "llm_aggregate_policy",
            "llm_aggregate_run_id",
            "llm_aggregate_group_id",
            "llm_coverage_source",
            "llm_max_retries",
            # New Core CLI Flags
            "llm_provider",
            "llm_model",
            "llm_context_mode",
            # Token Optimization CLI Flags
            "llm_prompt_tier",
            "llm_batch_parametrized",
            "llm_context_compression",
        ]:
            setattr(mock_pytest_config.option, attr, None)
        mock_pytest_config.rootpath = tmp_path

        # Set overrides
        mock_pytest_config.option.llm_provider = "ollama"
        mock_pytest_config.option.llm_model = "llama3"

        cfg = load_config(mock_pytest_config)

        assert cfg.provider == "ollama"
        assert cfg.model == "llama3"

    def test_load_from_cli_retries(self, mock_pytest_config):
        """Test loading retries from CLI."""
        mock_pytest_config.option.llm_max_retries = 2
        cfg = load_config(mock_pytest_config)
        assert cfg.llm_max_retries == 2

    def test_load_aggregation_options(self, mock_pytest_config):
        """Test loading aggregation options."""
        mock_pytest_config.option.llm_aggregate_dir = "aggr_dir"
        mock_pytest_config.option.llm_aggregate_policy = "merge"
        mock_pytest_config.option.llm_aggregate_run_id = "run-123"
        mock_pytest_config.option.llm_aggregate_group_id = "group-abc"

        cfg = load_config(mock_pytest_config)

        assert cfg.aggregate_dir == "aggr_dir"
        assert cfg.aggregate_policy == "merge"
        assert cfg.aggregate_run_id == "run-123"
        assert cfg.aggregate_group_id == "group-abc"

    def test_load_coverage_source(self, mock_pytest_config):
        """Test loading coverage source option."""
        mock_pytest_config.option.llm_coverage_source = "cov_dir"
        cfg = load_config(mock_pytest_config)
        assert cfg.llm_coverage_source == "cov_dir"

    def test_load_token_optimization_options(self, mock_pytest_config):
        """Test loading token optimization options from CLI."""
        mock_pytest_config.option.llm_prompt_tier = "minimal"
        mock_pytest_config.option.llm_batch_parametrized = False
        mock_pytest_config.option.llm_context_compression = "none"

        cfg = load_config(mock_pytest_config)

        assert cfg.prompt_tier == "minimal"
        assert cfg.batch_parametrized_tests is False
        assert cfg.context_compression == "none"

    def test_load_batch_flag_conflict(self, mock_pytest_config):
        """Test that disabled batch flag works."""
        mock_pytest_config.option.llm_batch_parametrized = None
        # Should be default (True)
        cfg = load_config(mock_pytest_config)
        assert cfg.batch_parametrized_tests is True
