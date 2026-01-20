# SPDX-License-Identifier: MIT
"""Tests for adaptive system prompts and structured output."""

from pytest_llm_report.llm.base import (
    MINIMAL_SYSTEM_PROMPT,
    STANDARD_SYSTEM_PROMPT,
    get_provider,
)
from pytest_llm_report.options import Config


class TestComplexityEstimation:
    """Test test complexity estimation for prompt tier selection."""

    def test_simple_test_low_complexity(self):
        """Simple tests should have low complexity scores."""
        config = Config(provider="none")
        provider = get_provider(config)

        simple_test = """
def test_add():
    assert 1 + 1 == 2
"""
        complexity = provider._estimate_test_complexity(simple_test)
        assert complexity < 10, "Simple test should have complexity < 10"

    def test_complex_test_high_complexity(self):
        """Complex tests with mocks and multiple assertions should score higher."""
        config = Config(provider="none")
        provider = get_provider(config)

        complex_test = """
@patch('module.function')
def test_complex_scenario(mock_func):
    mock_func.return_value = 42
    result = function_under_test()
    assert result.status == 'success'
    assert result.code == 200
    assert mock_func.called
    pytest.raises(ValueError, lambda: other_function())
"""
        complexity = provider._estimate_test_complexity(complex_test)
        assert complexity >= 10, "Complex test should have complexity >= 10"

    def test_empty_source_zero_complexity(self):
        """Empty source should return zero complexity."""
        config = Config(provider="none")
        provider = get_provider(config)

        assert provider._estimate_test_complexity("") == 0
        assert provider._estimate_test_complexity(None) == 0


class TestPromptTierSelection:
    """Test system prompt selection based on configuration and complexity."""

    def test_minimal_tier_override(self):
        """Config override to minimal should always use minimal prompt."""
        config = Config(provider="none", prompt_tier="minimal")
        provider = get_provider(config)

        complex_test = """
@patch('module.function')
def test_complex():
    assert True
"""
        selected = provider._select_system_prompt(complex_test)
        assert selected == MINIMAL_SYSTEM_PROMPT

    def test_standard_tier_override(self):
        """Config override to standard should always use standard prompt."""
        config = Config(provider="none", prompt_tier="standard")
        provider = get_provider(config)

        simple_test = "def test_simple(): assert True"
        selected = provider._select_system_prompt(simple_test)
        assert selected == STANDARD_SYSTEM_PROMPT

    def test_auto_tier_simple_test(self):
        """Auto mode should use minimal prompt for simple tests."""
        config = Config(provider="none", prompt_tier="auto")
        provider = get_provider(config)

        simple_test = "def test_simple(): assert 1 == 1"
        selected = provider._select_system_prompt(simple_test)
        assert selected == MINIMAL_SYSTEM_PROMPT

    def test_auto_tier_complex_test(self):
        """Auto mode should use standard prompt for complex tests."""
        config = Config(provider="none", prompt_tier="auto")
        provider = get_provider(config)

        complex_test = """
@patch('module')
def test_complex(mock):
    assert mock.called
    assert result.ok
"""
        selected = provider._select_system_prompt(complex_test)
        assert selected == STANDARD_SYSTEM_PROMPT


class TestConfigValidation:
    """Test prompt_tier configuration validation."""

    def test_valid_prompt_tiers(self):
        """Valid prompt_tier values should pass validation."""
        for tier in ["minimal", "standard", "auto"]:
            config = Config(provider="none", prompt_tier=tier)
            errors = config.validate()
            assert len(errors) == 0, f"{tier} should be valid"

    def test_invalid_prompt_tier(self):
        """Invalid prompt_tier should fail validation."""
        config = Config(provider="none", prompt_tier="invalid")
        errors = config.validate()
        assert any("prompt_tier" in err for err in errors)
