# SPDX-License-Identifier: MIT
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from pytest_llm_report.llm.gemini import (
    GeminiProvider,
    _GeminiRateLimitConfig,
    _GeminiRateLimiter,
    _GeminiRateLimitExceeded,
)
from pytest_llm_report.models import TestCaseResult
from pytest_llm_report.options import Config


class MockGenerationFailure(Exception):
    pass


def test_gemini_limiter_requests_per_day_exhaustion():
    """Cover line 60: raising daily limit error."""
    limits = _GeminiRateLimitConfig(requests_per_day=1)
    limiter = _GeminiRateLimiter(limits)
    limiter.record_request()

    with pytest.raises(_GeminiRateLimitExceeded, match="requests_per_day"):
        limiter.wait_for_slot(10)


def test_gemini_limiter_record_zero_tokens():
    """Cover line 67: record_tokens early return."""
    limits = _GeminiRateLimitConfig(tokens_per_minute=100)
    limiter = _GeminiRateLimiter(limits)
    limiter.record_tokens(0)
    assert len(limiter._token_usage) == 0


def test_gemini_limiter_tpm_fallback_wait():
    """Cover lines 115-117: tpm wait time fallback."""
    limits = _GeminiRateLimitConfig(tokens_per_minute=10)
    limiter = _GeminiRateLimiter(limits)
    # Fill up TPM
    limiter.record_tokens(10)

    now = time.monotonic()
    wait = limiter._seconds_until_tpm_available(now, 5)
    assert wait > 0
    # Line 116 hit because tokens_used + request_tokens > limit AND token_usage is not empty


def test_gemini_provider_rpm_cooldown():
    """Cover lines 230-234: RPM rate limit cooldown handling."""
    from pytest_llm_report.llm.gemini import _GeminiRateLimitExceeded

    captured_calls = []

    def fake_call(*args, **kwargs):
        captured_calls.append(args)
        if len(captured_calls) == 1:
            # First call fails with RPM limit
            raise _GeminiRateLimitExceeded("requests_per_minute", retry_after=0.1)
        return '{"scenario": "ok", "why_needed": "ok", "key_assertions": []}', 10

    config = Config(provider="gemini", model="models/gemini-pro")
    provider = GeminiProvider(config)

    with (
        patch("os.getenv", return_value="fake-token"),
        patch.object(
            provider, "_ensure_models_and_limits", return_value=["models/gemini-pro"]
        ),
        patch.object(provider, "_call_gemini", side_effect=fake_call),
        patch("pytest_llm_report.llm.gemini.time.sleep"),
        patch("pytest_llm_report.llm.gemini.time.time", return_value=1000.0),
        patch("pytest_llm_report.llm.gemini.time.monotonic", return_value=1000.0),
    ):
        fake_genai = SimpleNamespace(
            configure=lambda api_key: None,
            GenerativeModel=lambda name: SimpleNamespace(),
            types=SimpleNamespace(GenerationFailure=MockGenerationFailure),
        )
        fake_api_core = SimpleNamespace(
            exceptions=SimpleNamespace(ResourceExhausted=MockGenerationFailure)
        )
        fake_google = SimpleNamespace(__path__=[])
        fake_google.generativeai = fake_genai
        with patch.dict(
            sys.modules,
            {
                "google": fake_google,
                "google.generativeai": fake_genai,
                "google.api_core": fake_api_core,
            },
        ):
            # This will hit RPM limit on first call, then retry and succeed
            provider._annotate_internal(
                TestCaseResult(nodeid="t", outcome="passed"), "source"
            )

            # Line 242 should have set the cooldown
            assert "models/gemini-pro" in provider._cooldowns
            assert provider._cooldowns["models/gemini-pro"] > 1000.0
