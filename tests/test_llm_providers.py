# SPDX-License-Identifier: MIT
"""Tests for LiteLLM and Ollama providers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pytest_llm_report.llm.litellm_provider import LiteLLMProvider
from pytest_llm_report.llm.ollama import OllamaProvider
from pytest_llm_report.models import LlmAnnotation
from pytest_llm_report.models import TestCaseResult as CaseResult
from pytest_llm_report.options import Config


class FakeLiteLLMResponse:
    """Fake LiteLLM response payload."""

    def __init__(self, content: str) -> None:
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]


class TestLiteLLMProvider:
    """Tests for the LiteLLM provider."""

    def test_annotate_success_with_mock_response(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider parses a valid response payload."""
        captured = {}

        def fake_completion(**kwargs):
            captured.update(kwargs)
            return FakeLiteLLMResponse(
                '{"scenario": "Checks login", "why_needed": "Stops regressions", '
                '"key_assertions": ["status ok", "redirect"]}'
            )

        fake_litellm = SimpleNamespace(completion=fake_completion)
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm", model="gpt-4o")
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="tests/test_auth.py::test_login", outcome="passed")
        annotation = provider.annotate(test, "def test_login(): assert True")

        assert isinstance(annotation, LlmAnnotation)
        assert annotation.scenario == "Checks login"
        assert annotation.why_needed == "Stops regressions"
        assert annotation.key_assertions == ["status ok", "redirect"]
        assert annotation.confidence == 0.8
        assert captured["model"] == "gpt-4o"
        assert captured["messages"][0]["role"] == "system"
        assert "tests/test_auth.py::test_login" in captured["messages"][1]["content"]
        assert "def test_login()" in captured["messages"][1]["content"]

    def test_annotate_invalid_key_assertions(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider rejects invalid key_assertions payloads."""
        fake_litellm = SimpleNamespace(
            completion=lambda **_: FakeLiteLLMResponse(
                '{"scenario": "", "why_needed": "", "key_assertions": "oops"}'
            )
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm")
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert annotation.error == "Invalid response: key_assertions must be a list"

    def test_annotate_handles_completion_error(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider surfaces completion errors in annotation."""

        def fake_completion(**_):
            raise RuntimeError("boom")

        fake_litellm = SimpleNamespace(completion=fake_completion)
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm")
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert annotation.error == "boom"

    def test_annotate_missing_dependency(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider reports missing dependency cleanly."""
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "litellm":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        config = Config(provider="litellm")
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert (
            annotation.error
            == "litellm not installed. Install with: pip install litellm"
        )

    def test_is_available_with_module(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider detects installed module."""
        fake_litellm = SimpleNamespace()
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm")
        provider = LiteLLMProvider(config)

        assert provider.is_available() is True


class TestOllamaProvider:
    """Tests for the Ollama provider."""

    def test_parse_response_success(self):
        """Ollama provider parses valid JSON responses."""
        config = Config(provider="ollama")
        provider = OllamaProvider(config)

        annotation = provider._parse_response(
            '{"scenario": "Tests feature", "why_needed": "Stops bugs", '
            '"key_assertions": ["assert a", "assert b"]}'
        )

        assert annotation.scenario == "Tests feature"
        assert annotation.why_needed == "Stops bugs"
        assert annotation.key_assertions == ["assert a", "assert b"]
        assert annotation.confidence == 0.8

    def test_parse_response_invalid_json(self):
        """Ollama provider reports invalid JSON responses."""
        config = Config(provider="ollama")
        provider = OllamaProvider(config)

        annotation = provider._parse_response("not-json")

        assert annotation.error == "Failed to parse LLM response as JSON"

    def test_parse_response_invalid_key_assertions(self):
        """Ollama provider rejects invalid key_assertions payloads."""
        config = Config(provider="ollama")
        provider = OllamaProvider(config)

        annotation = provider._parse_response(
            '{"scenario": "", "why_needed": "", "key_assertions": "oops"}'
        )

        assert annotation.error == "Invalid response: key_assertions must be a list"

    def test_annotate_missing_httpx(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider reports missing httpx dependency."""
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "httpx":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        config = Config(provider="ollama")
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert (
            annotation.error == "httpx not installed. Install with: pip install httpx"
        )

    def test_annotate_handles_call_error(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider surfaces call errors in annotation."""
        config = Config(provider="ollama")
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        monkeypatch.setitem(__import__("sys").modules, "httpx", SimpleNamespace())

        def fake_call(prompt: str) -> str:
            raise RuntimeError("boom")

        monkeypatch.setattr(provider, "_call_ollama", fake_call)
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert annotation.error == "boom"
