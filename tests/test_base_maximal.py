from __future__ import annotations

import pytest

from pytest_llm_report.llm.base import LlmProvider, get_provider
from pytest_llm_report.llm.gemini import GeminiProvider
from pytest_llm_report.llm.litellm_provider import LiteLLMProvider
from pytest_llm_report.llm.noop import NoopProvider

# Imports for type checking / verification
from pytest_llm_report.llm.ollama import OllamaProvider
from pytest_llm_report.options import Config


class TestGetProvider:
    """Tests for get_provider factory function."""

    def test_get_noop_provider(self):
        config = Config(provider="none")
        provider = get_provider(config)
        assert isinstance(provider, NoopProvider)

    def test_get_ollama_provider(self):
        config = Config(provider="ollama")
        provider = get_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_get_litellm_provider(self):
        config = Config(provider="litellm")
        provider = get_provider(config)
        assert isinstance(provider, LiteLLMProvider)

    def test_get_gemini_provider(self):
        config = Config(provider="gemini")
        provider = get_provider(config)
        assert isinstance(provider, GeminiProvider)

    def test_get_invalid_provider(self):
        config = Config(provider="invalid")
        with pytest.raises(ValueError, match="Unknown LLM provider: invalid"):
            get_provider(config)


class ConcreteProvider(LlmProvider):
    def _annotate_internal(self, test, test_source, context_files=None):
        return None

    def _check_availability(self):
        return True


class TestLlmProviderDefaults:
    """Tests for LlmProvider default methods."""

    def test_is_local_defaults_to_false(self):
        config = Config()
        provider = ConcreteProvider(config)
        assert provider.is_local() is False

    def test_get_rate_limits_defaults_to_none(self):
        config = Config()
        provider = ConcreteProvider(config)
        assert provider.get_rate_limits() is None

    def test_get_model_name_defaults_to_config(self):
        config = Config(model="test-model")
        provider = ConcreteProvider(config)
        assert provider.get_model_name() == "test-model"

    def test_available_caches_result(self, monkeypatch):
        # We need a provider that implements _check_availability
        class MockProvider(LlmProvider):
            def __init__(self, config):
                super().__init__(config)
                self.checks = 0

            def _annotate_internal(self, *args):
                pass

            def _check_availability(self):
                self.checks += 1
                return True

        provider = MockProvider(Config())
        assert provider.is_available() is True
        assert provider.is_available() is True
        assert provider.checks == 1
