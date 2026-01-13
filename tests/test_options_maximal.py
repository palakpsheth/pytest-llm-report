# SPDX-License-Identifier: MIT
"""Tests for options module."""

from pytest_llm_report.options import Config, get_default_config


class TestConfigValidationMaximal:
    """Tests for Config.validate() method."""

    def test_validate_valid_config(self):
        """Should return empty list for valid config."""
        config = Config()
        assert config.validate() == []

    def test_validate_invalid_provider(self):
        """Should return error for invalid provider."""
        config = Config(provider="invalid")
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid provider 'invalid'" in errors[0]

    def test_validate_invalid_context_mode(self):
        """Should return error for invalid context mode."""
        config = Config(llm_context_mode="invalid")
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid llm_context_mode 'invalid'" in errors[0]

    def test_validate_invalid_aggregate_policy(self):
        """Should return error for invalid aggregate policy."""
        config = Config(aggregate_policy="invalid")
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid aggregate_policy 'invalid'" in errors[0]

    def test_validate_invalid_include_phase(self):
        """Should return error for invalid include phase."""
        config = Config(include_phase="invalid")
        errors = config.validate()
        assert len(errors) == 1
        assert "Invalid include_phase 'invalid'" in errors[0]

    def test_validate_numeric_bounds(self):
        """Should return errors for invalid numeric values."""
        config = Config(
            llm_context_bytes=999,
            llm_max_tests=-1,
            llm_requests_per_minute=0,
            llm_timeout_seconds=0,
        )
        errors = config.validate()
        assert len(errors) == 4
        assert any("llm_context_bytes" in e for e in errors)
        assert any("llm_max_tests" in e for e in errors)
        assert any("llm_requests_per_minute" in e for e in errors)
        assert any("llm_timeout_seconds" in e for e in errors)


class TestConfigDefaultsMaximal:
    """Tests for Config defaults."""

    def test_default_values(self):
        """Should have correct default values."""
        config = get_default_config()
        assert config.provider == "none"
        assert config.llm_context_mode == "minimal"
        assert config.llm_context_bytes == 32000
        assert config.omit_tests_from_coverage is True
        assert config.include_phase == "run"

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


class TestConfigHelpersMaximal:
    """Tests for Config helper methods."""

    def test_is_llm_enabled(self):
        """Should return correct enabled status."""
        assert Config(provider="none").is_llm_enabled() is False
        assert Config(provider="ollama").is_llm_enabled() is True
        assert Config(provider="litellm").is_llm_enabled() is True
        assert Config(provider="gemini").is_llm_enabled() is True
