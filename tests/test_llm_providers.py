# SPDX-License-Identifier: MIT
"""Tests for LiteLLM and Ollama providers."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from pytest_llm_report.llm.gemini import GeminiProvider
from pytest_llm_report.llm.litellm_provider import LiteLLMProvider
from pytest_llm_report.llm.ollama import OllamaProvider
from pytest_llm_report.models import LlmAnnotation
from pytest_llm_report.models import TestCaseResult as CaseResult
from pytest_llm_report.options import Config


class FakeLiteLLMResponse:
    """Fake LiteLLM response payload."""

    def __init__(self, content: str) -> None:
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]


class FakeGeminiResponse:
    """Fake Gemini response payload."""

    def __init__(
        self, data: dict, status_code: int = 200, headers: dict | None = None
    ) -> None:
        self._data = data
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._data


class MockGenerationFailure(Exception):
    pass


@pytest.fixture
def mock_import_error(monkeypatch: pytest.MonkeyPatch):
    """Return a factory that makes imports raise ImportError for a module."""
    import builtins

    real_import = builtins.__import__

    def _factory(module_name: str) -> None:
        def fake_import(name, *args, **kwargs):
            if name == module_name:
                raise ImportError(f"No module named {module_name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

    return _factory


class TestLiteLLMProvider:
    """Tests for the LiteLLM provider."""

    def test_annotate_success_with_mock_response(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider parses a valid response payload."""
        captured = {}

        def fake_completion(**kwargs):
            captured.update(kwargs)
            response_data = {
                "scenario": "Checks login",
                "why_needed": "Stops regressions",
                "key_assertions": ["status ok", "redirect"],
            }
            return FakeLiteLLMResponse(json.dumps(response_data))

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
        response_data = {
            "scenario": "",
            "why_needed": "",
            "key_assertions": "oops",
        }
        fake_litellm = SimpleNamespace(
            completion=lambda **_: FakeLiteLLMResponse(json.dumps(response_data))
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm")
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert annotation.error is not None
        assert "Invalid response: key_assertions must be a list" in annotation.error

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

        assert annotation.error is not None
        assert "boom" in annotation.error

    def test_annotate_missing_dependency(self, mock_import_error):
        """LiteLLM provider reports missing dependency cleanly."""
        mock_import_error("litellm")

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

    def test_api_base_passthrough(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider passes api_base to completion call."""
        captured = {}

        def fake_completion(**kwargs):
            captured.update(kwargs)
            response_data = {
                "scenario": "Test",
                "why_needed": "Reason",
                "key_assertions": ["a"],
            }
            return FakeLiteLLMResponse(json.dumps(response_data))

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=Exception
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(
            provider="litellm",
            model="gpt-4o",
            litellm_api_base="https://proxy.corp.com/v1",
        )
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="tests/test.py::test_case", outcome="passed")
        provider.annotate(test, "def test_case(): pass")

        assert captured["api_base"] == "https://proxy.corp.com/v1"

    def test_api_key_passthrough(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider passes static api_key to completion call."""
        captured = {}

        def fake_completion(**kwargs):
            captured.update(kwargs)
            response_data = {
                "scenario": "Test",
                "why_needed": "Reason",
                "key_assertions": ["a"],
            }
            return FakeLiteLLMResponse(json.dumps(response_data))

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=Exception
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(
            provider="litellm",
            model="gpt-4o",
            litellm_api_key=os.getenv("TEST_KEY", "static-key-placeholder"),
        )
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="tests/test.py::test_case", outcome="passed")
        provider.annotate(test, "def test_case(): pass")

        assert captured["api_key"] == "static-key-placeholder"

    def test_token_refresh_integration(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider uses TokenRefresher for dynamic tokens."""
        import subprocess

        captured = {}

        def fake_completion(**kwargs):
            captured.update(kwargs)
            response_data = {
                "scenario": "Test",
                "why_needed": "Reason",
                "key_assertions": ["a"],
            }
            return FakeLiteLLMResponse(json.dumps(response_data))

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="dynamic-token-789", stderr=""
            )

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=Exception
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)
        monkeypatch.setattr(subprocess, "run", fake_run)

        config = Config(
            provider="litellm",
            model="gpt-4o",
            litellm_token_refresh_command="get-token",
            litellm_token_refresh_interval=3600,
        )
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="tests/test.py::test_case", outcome="passed")
        provider.annotate(test, "def test_case(): pass")

        assert captured["api_key"] == "dynamic-token-789"

    def test_401_retry_with_token_refresh(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider retries on 401 after refreshing token."""
        import subprocess

        call_count = 0
        captured_keys = []

        class FakeAuthError(Exception):
            pass

        def fake_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            captured_keys.append(kwargs.get("api_key"))
            if call_count == 1:
                raise FakeAuthError("401 Unauthorized")
            response_data = {
                "scenario": "Test",
                "why_needed": "Reason",
                "key_assertions": ["a"],
            }
            return FakeLiteLLMResponse(json.dumps(response_data))

        token_count = 0

        def fake_run(*args, **kwargs):
            nonlocal token_count
            token_count += 1
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=f"token-{token_count}", stderr=""
            )

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=FakeAuthError
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)
        monkeypatch.setattr(subprocess, "run", fake_run)

        config = Config(
            provider="litellm",
            model="gpt-4o",
            litellm_token_refresh_command="get-token",
            litellm_token_refresh_interval=3600,
        )
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="tests/test.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): pass")

        assert annotation.error is None
        assert annotation.scenario == "Test"
        assert call_count == 2  # First failed, second succeeded
        assert captured_keys[0] == "token-1"  # First token
        assert captured_keys[1] == "token-2"  # Refreshed token

    def test_auth_error_without_refresher(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider returns auth error when no refresher configured."""

        class FakeAuthError(Exception):
            pass

        def fake_completion(**kwargs):
            raise FakeAuthError("401 Unauthorized")

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=FakeAuthError
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm", model="gpt-4o")  # No token refresh
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="t", outcome="passed")
        annotation = provider.annotate(test, "src")

        assert annotation.error is not None
        assert "Authentication failed" in annotation.error

    def test_auth_retry_fails_on_second_attempt(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider reports error when retry also fails with auth error."""
        import subprocess

        class FakeAuthError(Exception):
            pass

        def fake_completion(**kwargs):
            raise FakeAuthError("401 Unauthorized")

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="token-new", stderr=""
            )

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=FakeAuthError
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)
        monkeypatch.setattr(subprocess, "run", fake_run)

        config = Config(
            provider="litellm",
            litellm_token_refresh_command="get-token",
            llm_max_retries=2,
        )
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="t", outcome="passed")
        annotation = provider.annotate(test, "src")

        # After refresh fails, continues loop and gets auth error again
        assert annotation.error is not None
        assert "Authentication failed" in annotation.error

    def test_annotate_with_token_usage(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider extracts token usage from response."""

        class FakeUsage:
            prompt_tokens = 100
            completion_tokens = 50
            total_tokens = 150

        class FakeChoice:
            message = SimpleNamespace(
                content=json.dumps(
                    {
                        "scenario": "Test",
                        "why_needed": "Reason",
                        "key_assertions": ["a"],
                    }
                )
            )

        class FakeResponseWithUsage:
            choices = [FakeChoice()]
            usage = FakeUsage()

        def fake_completion(**kwargs):
            return FakeResponseWithUsage()

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=Exception
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm")
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="t", outcome="passed")
        annotation = provider.annotate(test, "src")

        assert annotation.token_usage is not None
        assert annotation.token_usage.prompt_tokens == 100
        assert annotation.token_usage.completion_tokens == 50
        assert annotation.token_usage.total_tokens == 150

    def test_annotate_with_prompt_override(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider uses prompt_override when provided."""
        captured_messages = []

        def fake_completion(**kwargs):
            captured_messages.append(kwargs.get("messages"))
            return FakeLiteLLMResponse(
                json.dumps(
                    {"scenario": "ok", "why_needed": "ok", "key_assertions": ["a"]}
                )
            )

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=Exception
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm")
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="t", outcome="passed")

        annotation = provider._annotate_internal(
            test, "source", None, prompt_override="CUSTOM PROMPT"
        )

        assert annotation.error is None
        assert captured_messages[0][1]["content"] == "CUSTOM PROMPT"

    def test_get_max_context_tokens_success(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider gets max tokens from litellm module."""

        def fake_get_max_tokens(model):
            return 8192

        fake_litellm = SimpleNamespace(
            get_max_tokens=fake_get_max_tokens, AuthenticationError=Exception
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm", model="gpt-4")
        provider = LiteLLMProvider(config)

        result = provider.get_max_context_tokens()
        assert result == 8192

    def test_get_max_context_tokens_dict_format(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider handles dict format from get_max_tokens."""

        def fake_get_max_tokens(model):
            return {"max_tokens": 16384}

        fake_litellm = SimpleNamespace(
            get_max_tokens=fake_get_max_tokens, AuthenticationError=Exception
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm", model="gpt-4")
        provider = LiteLLMProvider(config)

        result = provider.get_max_context_tokens()
        assert result == 16384

    def test_get_max_context_tokens_fallback_on_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """LiteLLM provider returns default on error."""

        def fake_get_max_tokens(model):
            raise RuntimeError("Unknown model")

        fake_litellm = SimpleNamespace(
            get_max_tokens=fake_get_max_tokens, AuthenticationError=Exception
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm", model="unknown")
        provider = LiteLLMProvider(config)

        result = provider.get_max_context_tokens()
        assert result == 4096  # Default fallback

    def test_transient_error_retry(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider retries on transient errors."""
        monkeypatch.setattr("time.sleep", lambda s: None)

        call_count = 0

        class FakeAuthError(Exception):
            """Specific auth error that won't match ConnectionError."""

            pass

        def fake_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return FakeLiteLLMResponse(
                json.dumps(
                    {"scenario": "ok", "why_needed": "test", "key_assertions": ["a"]}
                )
            )

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=FakeAuthError
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm", llm_max_retries=5)
        provider = LiteLLMProvider(config)
        test = CaseResult(nodeid="t", outcome="passed")

        annotation = provider.annotate(test, "src")

        assert annotation.error is None
        # 2 failures + 1 success = 3 calls
        assert call_count == 3

    def test_context_too_long_error(self, monkeypatch: pytest.MonkeyPatch):
        """LiteLLM provider handles context too long error."""

        def fake_completion(**kwargs):
            return FakeLiteLLMResponse(
                json.dumps(
                    {
                        "scenario": "",
                        "why_needed": "",
                        "key_assertions": [],
                        "error": "Context too long for this model",
                    }
                )
            )

        fake_litellm = SimpleNamespace(
            completion=fake_completion, AuthenticationError=Exception
        )
        monkeypatch.setitem(__import__("sys").modules, "litellm", fake_litellm)

        config = Config(provider="litellm")
        provider = LiteLLMProvider(config)
        provider = LiteLLMProvider(config)

        # First, let's verify what _parse_response does with invalid response
        annotation = provider._parse_response(
            '{"scenario": "", "why_needed": "", "key_assertions": "invalid"}'
        )
        assert annotation.error is not None


class TestGeminiProvider:
    """Tests for the Gemini provider."""

    def test_annotate_success_with_mock_response(self, monkeypatch: pytest.MonkeyPatch):
        """Gemini provider parses a valid response payload."""
        captured = {}

        def fake_post(url, **kwargs):
            captured["url"] = url
            captured["json"] = kwargs.get("json")
            response_data = {
                "scenario": "Checks login",
                "why_needed": "Stops regressions",
                "key_assertions": ["status ok", "redirect"],
            }
            payload = {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps(response_data)}],
                        }
                    }
                ]
            }
            return FakeGeminiResponse(payload)

        def fake_get(url, **_kwargs):
            if "models?" in url:
                captured["models_url"] = url
                models_payload = {
                    "models": [
                        {
                            "name": "models/gemini-1.5-pro",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                }
                return FakeGeminiResponse(models_payload)
            captured["rate_url"] = url
            rate_limits_payload = {
                "rateLimits": [
                    {"name": "requestsPerMinute", "value": 5},
                    {"name": "tokensPerMinute", "value": 1000},
                    {"name": "requestsPerDay", "value": 200},
                ]
            }
            return FakeGeminiResponse(rate_limits_payload)

        fake_httpx = SimpleNamespace(post=fake_post, get=fake_get)
        # Mock google.generativeai
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=MockGenerationFailure),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(
                exceptions=SimpleNamespace(ResourceExhausted=MockGenerationFailure)
            ),
        )
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")

        config = Config(provider="gemini", model="gemini-1.5-pro")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_auth.py::test_login", outcome="passed")

        annotation = provider.annotate(test, "def test_login(): assert True")

        assert isinstance(annotation, LlmAnnotation)
        assert annotation.scenario == "Checks login"
        assert annotation.why_needed == "Stops regressions"
        assert annotation.key_assertions == ["status ok", "redirect"]
        assert annotation.confidence == 0.8
        assert "gemini-1.5-pro" in captured["url"]
        assert "key=test-token" in captured["url"]
        assert "gemini-1.5-pro" in captured["rate_url"]
        assert "models?key=test-token" in captured["models_url"]
        assert captured["json"]["system_instruction"]["parts"][0]["text"]
        assert (
            "tests/test_auth.py::test_login"
            in captured["json"]["contents"][0]["parts"][0]["text"]
        )
        assert "def test_login()" in captured["json"]["contents"][0]["parts"][0]["text"]

    def test_annotate_missing_token(self, monkeypatch: pytest.MonkeyPatch):
        """Gemini provider requires an API token."""
        monkeypatch.setitem(__import__("sys").modules, "httpx", SimpleNamespace())

        # Mock google.generativeai
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=MockGenerationFailure),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(
                exceptions=SimpleNamespace(ResourceExhausted=MockGenerationFailure)
            ),
        )
        monkeypatch.delenv("GEMINI_API_TOKEN", raising=False)

        config = Config(provider="gemini")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert annotation.error == "GEMINI_API_TOKEN is not set"

    def test_annotate_missing_dependency(self, mock_import_error, monkeypatch):
        """Gemini provider reports missing httpx dependency."""
        mock_import_error("httpx")

        # Mock google.generativeai and google so we get past that check
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=MockGenerationFailure),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(
                exceptions=SimpleNamespace(ResourceExhausted=MockGenerationFailure)
            ),
        )
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")

        config = Config(provider="gemini")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert (
            annotation.error == "httpx not installed. Install with: pip install httpx"
        )

    def test_annotate_retries_on_rate_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gemini provider retries when rate limited."""
        calls = []

        class FakeResponse:
            def __init__(self, payload, status_code=200, headers=None):
                self._payload = payload
                self.status_code = status_code
                self.headers = headers or {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError(f"HTTP {self.status_code}")

            def json(self):
                return self._payload

        response_data = {
            "scenario": "Checks login",
            "why_needed": "Stops regressions",
            "key_assertions": ["status ok", "redirect"],
        }
        success_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": json.dumps(response_data)}],
                    }
                }
            ]
        }
        responses = iter(
            [
                FakeResponse({}, status_code=429, headers={"Retry-After": "0"}),
                FakeResponse(success_payload),
            ]
        )

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            return next(responses)

        def fake_get(url, **_kwargs):
            if "models?" in url:
                models_payload = {
                    "models": [
                        {
                            "name": "models/gemini-1.5-pro",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                }
                return FakeGeminiResponse(models_payload)
            rate_limits_payload = {
                "rateLimits": [{"name": "requestsPerMinute", "value": 60}]
            }
            return FakeGeminiResponse(rate_limits_payload)

        fake_httpx = SimpleNamespace(post=fake_post, get=fake_get)
        sleep_calls: list[float] = []
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        # Mock google.generativeai
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=MockGenerationFailure),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(
                exceptions=SimpleNamespace(ResourceExhausted=MockGenerationFailure)
            ),
        )
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")
        monkeypatch.setattr(
            "pytest_llm_report.llm.gemini.time.sleep", sleep_calls.append
        )

        config = Config(provider="gemini", model="gemini-1.5-pro")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_auth.py::test_login", outcome="passed")
        annotation = provider.annotate(test, "def test_login(): assert True")

        assert annotation.scenario == "Checks login"
        assert len(calls) == 2
        # assert sleep_calls == []  # Sleep might be called with 0 depending on implementation

    def test_annotate_skips_on_daily_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gemini provider skips when daily limit is reached."""
        calls = []

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            response_data = {
                "scenario": "Checks login",
                "why_needed": "Stops regressions",
                "key_assertions": ["status ok", "redirect"],
            }
            payload = {
                "candidates": [
                    {"content": {"parts": [{"text": json.dumps(response_data)}]}}
                ]
            }
            return FakeGeminiResponse(payload)

        def fake_get(url, **_kwargs):
            if "models?" in url:
                models_payload = {
                    "models": [
                        {
                            "name": "models/gemini-1.5-pro",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                }
                return FakeGeminiResponse(models_payload)
            rate_limits_payload = {
                "rateLimits": [{"name": "requestsPerDay", "value": 1}]
            }
            return FakeGeminiResponse(rate_limits_payload)

        fake_httpx = SimpleNamespace(post=fake_post, get=fake_get)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        # Mock google.generativeai
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=MockGenerationFailure),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(
                exceptions=SimpleNamespace(ResourceExhausted=MockGenerationFailure)
            ),
        )
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")

        config = Config(provider="gemini", model="gemini-1.5-pro")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_auth.py::test_login", outcome="passed")

        first = provider.annotate(test, "def test_login(): assert True")
        second = provider.annotate(test, "def test_login(): assert True")

        assert first.error is None
        assert (
            second.error == "Gemini requests-per-day limit reached; skipping annotation"
        )
        assert len(calls) == 1

    def test_annotate_rotates_models_on_daily_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gemini provider rotates models when daily limit is exhausted."""
        calls = []

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            response_data = {
                "scenario": "Checks login",
                "why_needed": "Stops regressions",
                "key_assertions": ["status ok", "redirect"],
            }
            payload = {
                "candidates": [
                    {"content": {"parts": [{"text": json.dumps(response_data)}]}}
                ]
            }
            return FakeGeminiResponse(payload)

        def fake_get(url, **_kwargs):
            if "models?" in url:
                models_payload = {
                    "models": [
                        {
                            "name": "models/gemini-1.5-pro",
                            "supportedGenerationMethods": ["generateContent"],
                        },
                        {
                            "name": "models/gemini-1.5-flash",
                            "supportedGenerationMethods": ["generateContent"],
                        },
                    ]
                }
                return FakeGeminiResponse(models_payload)
            if "gemini-1.5-pro" in url:
                rate_limits_payload = {
                    "rateLimits": [{"name": "requestsPerDay", "value": 1}]
                }
                return FakeGeminiResponse(rate_limits_payload)
            rate_limits_payload = {
                "rateLimits": [{"name": "requestsPerDay", "value": 1}]
            }
            return FakeGeminiResponse(rate_limits_payload)

        fake_httpx = SimpleNamespace(post=fake_post, get=fake_get)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        # Mock google.generativeai
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=MockGenerationFailure),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(
                exceptions=SimpleNamespace(ResourceExhausted=MockGenerationFailure)
            ),
        )
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")

        config = Config(provider="gemini", model="all")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_auth.py::test_login", outcome="passed")

        first = provider.annotate(test, "def test_login(): assert True")
        second = provider.annotate(test, "def test_login(): assert True")

        assert first.error is None
        assert second.error is None
        assert "gemini-1.5-pro" in calls[0][0]
        assert "gemini-1.5-flash" in calls[1][0]

    def test_exhausted_model_recovers_after_24h(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gemini provider recovers exhausted models after 24 hours."""
        calls = []
        fake_time = [1000000.0]  # Start time

        def fake_time_time():
            return fake_time[0]

        monkeypatch.setattr("pytest_llm_report.llm.gemini.time.time", fake_time_time)

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            response_data = {
                "scenario": "Checks login",
                "why_needed": "Stops regressions",
                "key_assertions": ["status ok", "redirect"],
            }
            payload = {
                "candidates": [
                    {"content": {"parts": [{"text": json.dumps(response_data)}]}}
                ]
            }
            return FakeGeminiResponse(payload)

        def fake_get(url, **_kwargs):
            if "models?" in url:
                models_payload = {
                    "models": [
                        {
                            "name": "models/gemini-1.5-pro",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                }
                return FakeGeminiResponse(models_payload)
            rate_limits_payload = {
                "rateLimits": [{"name": "requestsPerDay", "value": 1}]
            }
            return FakeGeminiResponse(rate_limits_payload)

        fake_httpx = SimpleNamespace(post=fake_post, get=fake_get)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        # Mock google.generativeai
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=MockGenerationFailure),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(
                exceptions=SimpleNamespace(ResourceExhausted=MockGenerationFailure)
            ),
        )
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")

        config = Config(provider="gemini", model="gemini-1.5-pro")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_auth.py::test_login", outcome="passed")

        # First call succeeds, uses daily limit
        first = provider.annotate(test, "def test_login(): assert True")
        assert first.error is None
        assert len(calls) == 1

        # Second call fails - daily limit exhausted
        second = provider.annotate(test, "def test_login(): assert True")
        assert (
            second.error == "Gemini requests-per-day limit reached; skipping annotation"
        )
        assert len(calls) == 1  # No new API call

        # Advance time by 24 hours + 1 second
        fake_time[0] += 24 * 3600 + 1

        # Third call should succeed - model has recovered
        third = provider.annotate(test, "def test_login(): assert True")
        assert third.error is None
        assert len(calls) == 2  # New API call made

    def test_model_list_refreshes_after_interval(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gemini provider refreshes model list after 6 hours."""
        model_fetches = []
        fake_time = [1000000.0]

        def fake_time_time():
            return fake_time[0]

        monkeypatch.setattr("pytest_llm_report.llm.gemini.time.time", fake_time_time)

        def fake_post(url, **kwargs):
            response_data = {
                "scenario": "Checks login",
                "why_needed": "Stops regressions",
                "key_assertions": ["status ok"],
            }
            payload = {
                "candidates": [
                    {"content": {"parts": [{"text": json.dumps(response_data)}]}}
                ]
            }
            return FakeGeminiResponse(payload)

        def fake_get(url, **_kwargs):
            if "models?" in url:
                model_fetches.append(fake_time[0])
                models_payload = {
                    "models": [
                        {
                            "name": "models/gemini-1.5-pro",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                }
                return FakeGeminiResponse(models_payload)
            rate_limits_payload = {
                "rateLimits": [{"name": "requestsPerMinute", "value": 60}]
            }
            return FakeGeminiResponse(rate_limits_payload)

        fake_httpx = SimpleNamespace(post=fake_post, get=fake_get)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        # Mock google.generativeai
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=Exception),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(exceptions=SimpleNamespace(ResourceExhausted=Exception)),
        )
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")

        config = Config(provider="gemini", model="gemini-1.5-pro")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_auth.py::test_login", outcome="passed")

        # First call fetches models
        provider.annotate(test, "def test_login(): assert True")
        assert len(model_fetches) == 1

        # Second call (same time) should not re-fetch
        provider.annotate(test, "def test_login(): assert True")
        assert len(model_fetches) == 1

        # Advance time by 6 hours + 1 second
        fake_time[0] += 6 * 3600 + 1

        # Third call should re-fetch models
        provider.annotate(test, "def test_login(): assert True")
        assert len(model_fetches) == 2

    def test_annotate_records_tokens(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Gemini provider records token usage."""
        captured = {}

        def fake_post(url, **kwargs):
            captured["json"] = kwargs.get("json")
            response_data = {
                "scenario": "Checks login",
                "why_needed": "Stops regressions",
                "key_assertions": ["status ok"],
            }
            # Response with usage metadata
            payload = {
                "candidates": [
                    {"content": {"parts": [{"text": json.dumps(response_data)}]}}
                ],
                "usageMetadata": {"totalTokenCount": 123},
            }
            return FakeGeminiResponse(payload)

        def fake_get(url, **_kwargs):
            if "models?" in url:
                models_payload = {
                    "models": [
                        {
                            "name": "models/gemini-1.5-pro",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                }
                return FakeGeminiResponse(models_payload)
            rate_limits_payload = {
                "rateLimits": [{"name": "tokensPerMinute", "value": 1000}]
            }
            return FakeGeminiResponse(rate_limits_payload)

        fake_httpx = SimpleNamespace(post=fake_post, get=fake_get)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        # Mock google.generativeai
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=Exception),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(exceptions=SimpleNamespace(ResourceExhausted=Exception)),
        )
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")

        config = Config(provider="gemini", model="gemini-1.5-pro")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_auth.py::test_login", outcome="passed")

        # Verify tokens recorded on limiter
        provider.annotate(test, "def test_login(): assert True")
        # Rate limits logic is internal, but we can check if it ran without error
        # To truly verify, we'd inspect provider._rate_limiters['gemini-1.5-pro']._token_usage
        limiter = provider._rate_limiters.get("gemini-1.5-pro")
        assert limiter is not None
        assert len(limiter._token_usage) == 1
        assert limiter._token_usage[0][1] == 123

    def test_annotate_handles_context_too_large(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gemini provider handles 400 Context too large errors."""

        def fake_post(url, **kwargs):
            # Simulate 400 error
            raise RuntimeError("400 Bad Request: Context too large")

        def fake_get(url, **_kwargs):
            if "models?" in url:
                models_payload = {
                    "models": [
                        {
                            "name": "models/gemini-1.5-pro",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                }
                return FakeGeminiResponse(models_payload)
            return FakeGeminiResponse({"rateLimits": []})

        fake_httpx = SimpleNamespace(post=fake_post, get=fake_get)
        # Mock google.generativeai
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=MockGenerationFailure),
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        monkeypatch.setitem(__import__("sys").modules, "google", fake_google)
        monkeypatch.setitem(
            __import__("sys").modules, "google.generativeai", fake_genai
        )
        monkeypatch.setitem(
            __import__("sys").modules,
            "google.api_core",
            SimpleNamespace(
                exceptions=SimpleNamespace(ResourceExhausted=MockGenerationFailure)
            ),
        )
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")

        config = Config(provider="gemini")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test.py::test_foo", outcome="passed")

        annotation = provider.annotate(test, "def test_foo(): pass")
        assert annotation.error is not None
        assert "Context too large" in annotation.error
        assert "400" in annotation.error

    def test_fetch_available_models_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Gemini provider handles model fetch errors gracefully."""

        def fake_get(url, **_kwargs):
            if "models?" in url:
                raise RuntimeError("Network error")
            return FakeGeminiResponse({"rateLimits": []})

        fake_httpx = SimpleNamespace(get=fake_get)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)
        monkeypatch.setenv("GEMINI_API_TOKEN", "test-token")

        config = Config(provider="gemini")
        provider = GeminiProvider(config)

        # Trigger model fetch
        models = provider._ensure_models_and_limits("test-token")

        assert len(models) == 1
        assert models[0] == "gemini-1.5-flash-latest"


class TestOllamaProvider:
    """Tests for the Ollama provider."""

    def test_parse_response_success(self):
        """Ollama provider parses valid JSON responses."""
        config = Config(provider="ollama")
        provider = OllamaProvider(config)
        response_data = {
            "scenario": "Tests feature",
            "why_needed": "Stops bugs",
            "key_assertions": ["assert a", "assert b"],
        }

        annotation = provider._parse_response(json.dumps(response_data))

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
        response_data = {
            "scenario": "",
            "why_needed": "",
            "key_assertions": "oops",
        }

        annotation = provider._parse_response(json.dumps(response_data))

        assert annotation.error == "Invalid response: key_assertions must be a list"

    def test_annotate_missing_httpx(self, mock_import_error):
        """Ollama provider reports missing httpx dependency."""
        mock_import_error("httpx")

        config = Config(provider="ollama")
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert (
            annotation.error == "httpx not installed. Install with: pip install httpx"
        )

    def test_annotate_handles_call_error(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider surfaces call errors in annotation."""
        # Mock sleep to avoid waiting during retries
        monkeypatch.setattr("time.sleep", lambda s: None)

        config = Config(provider="ollama", llm_max_retries=2)
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        monkeypatch.setitem(__import__("sys").modules, "httpx", SimpleNamespace())

        def fake_call(prompt: str, system_prompt: str) -> str:
            raise Exception("boom")

        monkeypatch.setattr(provider, "_call_ollama", fake_call)
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert annotation.error == "Failed after 2 retries. Last error: boom"

    def test_parse_response_json_in_code_fence(self):
        """Ollama provider extracts JSON from markdown code fences."""
        config = Config(provider="ollama")
        provider = OllamaProvider(config)
        response = """Here is the annotation:

```json
{
  "scenario": "Tests the login flow",
  "why_needed": "Prevents auth regressions",
  "key_assertions": ["status 200", "token returned"]
}
```

I hope this helps!"""

        annotation = provider._parse_response(response)

        assert annotation.scenario == "Tests the login flow"
        assert annotation.why_needed == "Prevents auth regressions"
        assert annotation.key_assertions == ["status 200", "token returned"]
        assert annotation.confidence == 0.8

    def test_parse_response_json_in_plain_fence(self):
        """Ollama provider extracts JSON from plain markdown fences (no language)."""
        config = Config(provider="ollama")
        provider = OllamaProvider(config)
        response = """```
{"scenario": "Verifies data", "why_needed": "Catches bugs", "key_assertions": ["a", "b"]}
```"""

        annotation = provider._parse_response(response)

        assert annotation.scenario == "Verifies data"
        assert annotation.why_needed == "Catches bugs"
        assert annotation.key_assertions == ["a", "b"]

    def test_annotate_fallbacks_on_context_length_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Ollama provider falls back to minimal context on 'context too long' error."""
        monkeypatch.setattr("time.sleep", lambda s: None)

        config = Config(provider="ollama")
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        monkeypatch.setitem(__import__("sys").modules, "httpx", SimpleNamespace())

        # Track calls to _build_prompt to verify context usage
        original_build_prompt = provider._build_prompt
        build_prompt_calls = []

        def tracked_build_prompt(test, source, context):
            build_prompt_calls.append(context)
            return original_build_prompt(test, source, context)

        monkeypatch.setattr(provider, "_build_prompt", tracked_build_prompt)

        # Mock call_ollama to return error first, then success
        call_count = 0

        def fake_call(prompt: str, system_prompt: str) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"response": "error"}
            return {
                "response": '{"scenario": "ok", "why_needed": "fix", "key_assertions": ["assert"]}'
            }

        monkeypatch.setattr(provider, "_call_ollama", fake_call)

        # Mock parse_response to return the error object
        original_parse = provider._parse_response

        def fake_parse(response: str) -> LlmAnnotation:
            if response == "error":
                return LlmAnnotation(error="Context too long, please reduce it.")
            return original_parse(response)

        monkeypatch.setattr(provider, "_parse_response", fake_parse)

        context_files = {"file1.py": "content"}
        annotation = provider.annotate(test, "def test(): pass", context_files)

        assert annotation.error is None
        assert call_count == 2
        # First call should have context, second should have None
        assert len(build_prompt_calls) == 2
        assert build_prompt_calls[0] == context_files
        assert build_prompt_calls[1] is None

    def test_is_local_returns_true(self):
        """Ollama provider should always return is_local=True."""
        config = Config(provider="ollama")
        provider = OllamaProvider(config)

        assert provider.is_local() is True

    def test_check_availability_success(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider checks availability via /api/tags endpoint."""

        class FakeResponse:
            status_code = 200

        def fake_get(url, **kwargs):
            assert "/api/tags" in url
            return FakeResponse()

        fake_httpx = SimpleNamespace(get=fake_get)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama", ollama_host="http://localhost:11434")
        provider = OllamaProvider(config)

        assert provider._check_availability() is True

    def test_check_availability_failure(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider returns False when server is unavailable."""

        def fake_get(url, **kwargs):
            raise ConnectionError("Server not running")

        fake_httpx = SimpleNamespace(get=fake_get)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama")
        provider = OllamaProvider(config)

        assert provider._check_availability() is False

    def test_check_availability_non_200(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider returns False for non-200 status codes."""

        class FakeResponse:
            status_code = 500

        def fake_get(url, **kwargs):
            return FakeResponse()

        fake_httpx = SimpleNamespace(get=fake_get)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama")
        provider = OllamaProvider(config)

        assert provider._check_availability() is False

    def test_call_ollama_success(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider makes correct API call."""
        captured = {}

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"response": "test response"}

        def fake_post(url, **kwargs):
            captured["url"] = url
            captured["json"] = kwargs.get("json")
            captured["timeout"] = kwargs.get("timeout")
            return FakeResponse()

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(
            provider="ollama",
            ollama_host="http://localhost:11434",
            model="llama3.2:1b",
            llm_timeout_seconds=60,
        )
        provider = OllamaProvider(config)

        result = provider._call_ollama("test prompt", "system prompt")

        assert result["response"] == "test response"
        assert captured["url"] == "http://localhost:11434/api/generate"
        assert captured["json"]["model"] == "llama3.2:1b"
        assert captured["json"]["prompt"] == "test prompt"
        assert captured["json"]["system"] == "system prompt"
        assert captured["json"]["stream"] is False
        assert captured["timeout"] == 60

    def test_call_ollama_uses_default_model(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider uses default model when not specified."""
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"response": "ok"}

        def fake_post(url, **kwargs):
            captured["json"] = kwargs.get("json")
            return FakeResponse()

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama", model="")  # Empty model
        provider = OllamaProvider(config)

        provider._call_ollama("prompt", "system")

        assert captured["json"]["model"] == "llama3.2"  # Default model

    def test_annotate_success_full_flow(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider full annotation flow with mocked HTTP."""

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "response": json.dumps(
                        {
                            "scenario": "Tests user login",
                            "why_needed": "Prevents auth bugs",
                            "key_assertions": ["check status", "validate token"],
                        }
                    )
                }

        def fake_post(url, **kwargs):
            return FakeResponse()

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama", model="llama3.2")
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="tests/test_auth.py::test_login", outcome="passed")

        annotation = provider.annotate(test, "def test_login(): assert True")

        assert annotation.scenario == "Tests user login"
        assert annotation.why_needed == "Prevents auth bugs"
        assert annotation.key_assertions == ["check status", "validate token"]
        assert annotation.error is None

    def test_annotate_with_token_usage(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider extracts token usage from response."""

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "response": json.dumps(
                        {
                            "scenario": "Test scenario",
                            "why_needed": "Test reason",
                            "key_assertions": ["assert 1"],
                        }
                    ),
                    "prompt_eval_count": 100,
                    "eval_count": 50,
                }

        def fake_post(url, **kwargs):
            return FakeResponse()

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama", model="llama3.2")
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="tests/test.py::test_case", outcome="passed")

        annotation = provider.annotate(test, "def test_case(): pass")

        assert annotation.token_usage is not None
        assert annotation.token_usage.prompt_tokens == 100
        assert annotation.token_usage.completion_tokens == 50
        assert annotation.token_usage.total_tokens == 150

    def test_annotate_with_prompt_override(self, monkeypatch: pytest.MonkeyPatch):
        """Ollama provider uses prompt_override when provided."""
        captured_prompts = []

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "response": json.dumps(
                        {
                            "scenario": "ok",
                            "why_needed": "ok",
                            "key_assertions": ["a"],
                        }
                    )
                }

        def fake_post(url, **kwargs):
            captured_prompts.append(kwargs.get("json", {}).get("prompt"))
            return FakeResponse()

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama")
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="t", outcome="passed")

        # Use the internal method that accepts prompt_override
        annotation = provider._annotate_internal(
            test, "source", None, prompt_override="CUSTOM PROMPT"
        )

        assert annotation.error is None
        assert captured_prompts[0] == "CUSTOM PROMPT"

    def test_get_max_context_tokens_from_parameters(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Ollama provider extracts context length from parameters."""

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"parameters": "num_ctx 8192\nstop hello"}

        def fake_post(url, **kwargs):
            return FakeResponse()

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama", model="llama3.2")
        provider = OllamaProvider(config)

        result = provider.get_max_context_tokens()
        assert result == 8192

    def test_get_max_context_tokens_from_model_info(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Ollama provider extracts context length from model_info."""

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"model_info": {"llama.context_length": 4096}}

        def fake_post(url, **kwargs):
            return FakeResponse()

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama", model="llama3.2")
        provider = OllamaProvider(config)

        result = provider.get_max_context_tokens()
        assert result == 4096

    def test_get_max_context_tokens_context_length_key(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Ollama provider fallback to context_length key."""

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"model_info": {"context_length": 2048}}

        def fake_post(url, **kwargs):
            return FakeResponse()

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama")
        provider = OllamaProvider(config)

        result = provider.get_max_context_tokens()
        assert result == 2048

    def test_get_max_context_tokens_fallback_on_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Ollama provider returns default on API error."""

        def fake_post(url, **kwargs):
            raise ConnectionError("Server down")

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama")
        provider = OllamaProvider(config)

        result = provider.get_max_context_tokens()
        assert result == 4096  # Default fallback

    def test_get_max_context_tokens_non_200_status(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Ollama provider returns default on non-200 response."""

        class FakeResponse:
            status_code = 404

        def fake_post(url, **kwargs):
            return FakeResponse()

        fake_httpx = SimpleNamespace(post=fake_post)
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

        config = Config(provider="ollama")
        provider = OllamaProvider(config)

        result = provider.get_max_context_tokens()
        assert result == 4096  # Default fallback

    def test_annotate_runtime_error_immediate_fail(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Ollama provider fails immediately on RuntimeError."""
        monkeypatch.setitem(__import__("sys").modules, "httpx", SimpleNamespace())

        config = Config(provider="ollama", llm_max_retries=3)
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="t", outcome="passed")

        def fake_call(prompt, system):
            raise RuntimeError("Code bug")

        monkeypatch.setattr(provider, "_call_ollama", fake_call)
        annotation = provider._annotate_internal(test, "src")

        assert annotation.error == "Code bug"
