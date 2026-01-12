# SPDX-License-Identifier: MIT
"""Tests for LiteLLM and Ollama providers."""

from __future__ import annotations

import json
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
        monkeypatch.delenv("GEMINI_API_TOKEN", raising=False)

        config = Config(provider="gemini")
        provider = GeminiProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert annotation.error == "GEMINI_API_TOKEN is not set"

    def test_annotate_missing_dependency(self, mock_import_error):
        """Gemini provider reports missing httpx dependency."""
        mock_import_error("httpx")

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
        sleep_calls = []
        monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)
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
        assert sleep_calls == [0.0]

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

        config = Config(provider="ollama")
        provider = OllamaProvider(config)
        test = CaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
        monkeypatch.setitem(__import__("sys").modules, "httpx", SimpleNamespace())

        def fake_call(prompt: str) -> str:
            raise RuntimeError("boom")

        monkeypatch.setattr(provider, "_call_ollama", fake_call)
        annotation = provider.annotate(test, "def test_case(): assert True")

        assert annotation.error == "Failed after 3 retries. Last error: boom"

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
