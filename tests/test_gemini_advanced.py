# SPDX-License-Identifier: MIT
import time
from unittest.mock import patch

from pytest_llm_report.llm.gemini import _GeminiRateLimitConfig, _GeminiRateLimiter


class TestGeminiRateLimiter:
    """Direct tests for the internal rate limiter logic."""

    def test_rpm_limit(self):
        limits = _GeminiRateLimitConfig(requests_per_minute=1)
        limiter = _GeminiRateLimiter(limits)

        limiter.record_request()
        # Should be unavailable now
        wait = limiter.next_available_in(1)
        assert wait > 0
        assert wait <= 60.0

    def test_tpm_limit(self):
        limits = _GeminiRateLimitConfig(tokens_per_minute=100)
        limiter = _GeminiRateLimiter(limits)

        limiter.record_tokens(90)
        # 10 left. Next 20 should wait.
        wait = limiter.next_available_in(20)
        assert wait > 0

        # record_tokens updates state
        limiter.record_tokens(10)
        assert len(limiter._token_usage) == 2

    def test_pruning(self):
        limits = _GeminiRateLimitConfig(requests_per_minute=10)
        limiter = _GeminiRateLimiter(limits)

        # Add a request in the past
        limiter._request_times.append(time.monotonic() - 61)
        limiter._token_usage.append((time.monotonic() - 61, 100))

        # Pruning should clear them
        limiter._prune(time.monotonic())
        assert len(limiter._request_times) == 0
        assert len(limiter._token_usage) == 0

    def test_wait_for_slot(self):
        limits = _GeminiRateLimitConfig(requests_per_minute=1)
        limiter = _GeminiRateLimiter(limits)
        limiter.record_request()

        # Should sleep
        with patch("time.sleep") as mock_sleep:
            limiter.wait_for_slot(1)
            assert mock_sleep.called
