# SPDX-License-Identifier: MIT
"""Tests for LLM provider modules."""

from pytest_llm_report.llm.base import get_provider
from pytest_llm_report.llm.noop import NoopProvider
from pytest_llm_report.models import LlmAnnotation, TestCaseResult
from pytest_llm_report.options import Config


class TestNoopProvider:
    """Tests for NoopProvider."""

    def test_is_available(self):
        """Noop provider should always be available."""
        config = Config()
        provider = NoopProvider(config)
        assert provider.is_available() is True

    def test_annotate_returns_empty(self):
        """Noop provider should return empty annotation."""
        config = Config()
        provider = NoopProvider(config)

        test = TestCaseResult(nodeid="test::foo", outcome="passed")
        annotation = provider.annotate(test, "def test_foo(): pass")

        assert isinstance(annotation, LlmAnnotation)
        assert annotation.scenario == ""
        assert annotation.why_needed == ""
        assert annotation.key_assertions == []

    def test_get_model_name_empty(self):
        """Noop provider should return empty model name."""
        config = Config()
        provider = NoopProvider(config)
        assert provider.get_model_name() == ""


class TestGetProvider:
    """Tests for get_provider factory function."""

    def test_none_returns_noop(self):
        """provider='none' should return NoopProvider."""
        config = Config(provider="none")
        provider = get_provider(config)
        assert isinstance(provider, NoopProvider)

    def test_unknown_raises(self):
        """Unknown provider should raise ValueError."""
        config = Config(provider="unknown")
        try:
            get_provider(config)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "unknown" in str(e).lower()

    def test_ollama_returns_provider(self):
        """provider='ollama' should return OllamaProvider."""
        config = Config(provider="ollama", model="llama3.2")
        provider = get_provider(config)
        # Check it's the right type (import here to avoid import errors if httpx missing)
        assert provider.__class__.__name__ == "OllamaProvider"

    def test_litellm_returns_provider(self):
        """provider='litellm' should return LiteLLMProvider."""
        config = Config(provider="litellm", model="gpt-3.5-turbo")
        provider = get_provider(config)
        assert provider.__class__.__name__ == "LiteLLMProvider"

    def test_gemini_returns_provider(self):
        """provider='gemini' should return GeminiProvider."""
        config = Config(provider="gemini", model="gemini-1.5-flash")
        provider = get_provider(config)
        assert provider.__class__.__name__ == "GeminiProvider"


class TestLlmProviderContract:
    """Tests for LlmProvider contract."""

    def test_noop_implements_interface(self):
        """NoopProvider should implement LlmProvider."""
        config = Config()
        provider = NoopProvider(config)

        # Should have required methods
        assert hasattr(provider, "annotate")
        assert hasattr(provider, "is_available")
        assert hasattr(provider, "get_model_name")
        assert hasattr(provider, "config")
