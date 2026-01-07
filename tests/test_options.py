# SPDX-License-Identifier: MIT
"""Tests for pytest_llm_report.options module."""

from pytest_llm_report.options import Config, get_default_config


class TestConfigDefaults:
    """Tests for Config default values."""

    def test_provider_defaults_to_none(self):
        """Provider should default to 'none' for privacy."""
        config = Config()
        assert config.provider == "none"

    def test_context_mode_defaults_to_minimal(self):
        """Context mode should default to 'minimal' for safety."""
        config = Config()
        assert config.llm_context_mode == "minimal"

    def test_llm_include_param_values_defaults_to_false(self):
        """Parameter values should not be included by default."""
        config = Config()
        assert config.llm_include_param_values is False

    def test_capture_failed_output_defaults_to_false(self):
        """Captured output should be opt-in."""
        config = Config()
        assert config.capture_failed_output is False

    def test_aggregate_policy_defaults_to_latest(self):
        """Aggregation policy should default to 'latest'."""
        config = Config()
        assert config.aggregate_policy == "latest"

    def test_default_exclude_globs_include_secrets(self):
        """Default excludes should include common secret patterns."""
        config = Config()
        assert ".env" in config.llm_context_exclude_globs
        assert "*secret*" in config.llm_context_exclude_globs
        assert "*password*" in config.llm_context_exclude_globs

    def test_omit_tests_from_coverage_defaults_to_true(self):
        """Test files should be omitted from coverage by default."""
        config = Config()
        assert config.omit_tests_from_coverage is True


class TestConfigValidation:
    """Tests for Config validation."""

    def test_valid_config_has_no_errors(self):
        """Valid config should pass validation."""
        config = Config()
        errors = config.validate()
        assert errors == []

    def test_invalid_provider_produces_error(self):
        """Invalid provider should produce validation error."""
        config = Config(provider="invalid")
        errors = config.validate()
        assert len(errors) == 1
        assert "provider" in errors[0]

    def test_invalid_context_mode_produces_error(self):
        """Invalid context mode should produce validation error."""
        config = Config(llm_context_mode="invalid")
        errors = config.validate()
        assert len(errors) == 1
        assert "llm_context_mode" in errors[0]

    def test_invalid_aggregate_policy_produces_error(self):
        """Invalid aggregation policy should produce validation error."""
        config = Config(aggregate_policy="invalid")
        errors = config.validate()
        assert len(errors) == 1
        assert "aggregate_policy" in errors[0]

    def test_invalid_include_phase_produces_error(self):
        """Invalid include_phase should produce validation error."""
        config = Config(include_phase="invalid")
        errors = config.validate()
        assert len(errors) == 1
        assert "include_phase" in errors[0]

    def test_context_bytes_too_small_produces_error(self):
        """Context bytes below minimum should produce error."""
        config = Config(llm_context_bytes=100)
        errors = config.validate()
        assert len(errors) == 1
        assert "llm_context_bytes" in errors[0]

    def test_max_tests_too_small_produces_error(self):
        """Max tests below 1 should produce error."""
        config = Config(llm_max_tests=0)
        errors = config.validate()
        assert len(errors) == 1
        assert "llm_max_tests" in errors[0]

    def test_timeout_too_small_produces_error(self):
        """Timeout below 1 should produce error."""
        config = Config(llm_timeout_seconds=0)
        errors = config.validate()
        assert len(errors) == 1
        assert "llm_timeout_seconds" in errors[0]

    def test_multiple_errors_reported(self):
        """Multiple validation errors should all be reported."""
        config = Config(
            provider="invalid",
            llm_context_mode="invalid",
        )
        errors = config.validate()
        assert len(errors) == 2


class TestConfigIsLlmEnabled:
    """Tests for is_llm_enabled method."""

    def test_none_provider_not_enabled(self):
        """Provider 'none' should not be enabled."""
        config = Config(provider="none")
        assert config.is_llm_enabled() is False

    def test_ollama_provider_is_enabled(self):
        """Provider 'ollama' should be enabled."""
        config = Config(provider="ollama")
        assert config.is_llm_enabled() is True

    def test_litellm_provider_is_enabled(self):
        """Provider 'litellm' should be enabled."""
        config = Config(provider="litellm")
        assert config.is_llm_enabled() is True


class TestGetDefaultConfig:
    """Tests for get_default_config function."""

    def test_returns_config_instance(self):
        """Should return a Config instance."""
        config = get_default_config()
        assert isinstance(config, Config)

    def test_returns_defaults(self):
        """Should return config with default values."""
        config = get_default_config()
        assert config.provider == "none"
        assert config.llm_context_mode == "minimal"


class TestConfigAggregationFields:
    """Tests for aggregation-related config fields."""

    def test_aggregate_dir_defaults_to_none(self):
        """Aggregate dir should default to None."""
        config = Config()
        assert config.aggregate_dir is None

    def test_aggregate_run_id_defaults_to_none(self):
        """Run ID should default to None."""
        config = Config()
        assert config.aggregate_run_id is None

    def test_aggregate_group_id_defaults_to_none(self):
        """Group ID should default to None."""
        config = Config()
        assert config.aggregate_group_id is None

    def test_aggregate_include_history_defaults_to_false(self):
        """Include history should default to False."""
        config = Config()
        assert config.aggregate_include_history is False
