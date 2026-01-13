from unittest.mock import MagicMock, Mock, patch

import pytest

from pytest_llm_report.llm.gemini import (
    GeminiProvider,
    _GeminiRateLimitConfig,
    _GeminiRateLimiter,
)
from pytest_llm_report.models import TestCaseResult
from pytest_llm_report.options import Config


@pytest.fixture
def mock_config():
    return Config(
        provider="gemini",
        model="gemini-1.5-flash",
        llm_requests_per_minute=10,
        llm_timeout_seconds=30,
    )


class TestGeminiRateLimiter:
    def test_rpm_limit(self):
        limits = _GeminiRateLimitConfig(requests_per_minute=2)
        limiter = _GeminiRateLimiter(limits)

        # First two requests should not wait
        assert limiter.next_available_in(100) == 0.0
        limiter.record_request()
        assert limiter.next_available_in(100) == 0.0
        limiter.record_request()

        # Third request should wait
        wait = limiter.next_available_in(100)
        assert wait > 0
        assert wait <= 60.0

    def test_rpd_limit(self):
        limits = _GeminiRateLimitConfig(requests_per_day=1)
        limiter = _GeminiRateLimiter(limits)

        limiter.record_request()
        assert limiter.next_available_in(100) is None


class TestGeminiProvider:
    @patch("httpx.post")
    @patch("httpx.get")
    def test_annotate_success(self, mock_get, mock_post, mock_config):
        # Mock model list fetch
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "models": [
                {
                    "name": "models/gemini-1.5-flash",
                    "supportedGenerationMethods": ["generateContent"],
                    "rateLimits": [{"name": "rpm", "value": 15}],
                }
            ]
        }

        # Mock actual call
        mock_post.return_value.status_code = 200
        # GeminiProvider expects a certain JSON structure in _call_gemini
        mock_post.return_value.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Success Scenario"}]}}],
            "usageMetadata": {"totalTokenCount": 100},
        }

        test_result = TestCaseResult(nodeid="test1", outcome="passed")

        with patch.dict("os.environ", {"GEMINI_API_TOKEN": "test-token"}):
            provider = GeminiProvider(mock_config)
            # We need to mock _build_prompt to avoid complex dependency
            with patch.object(provider, "_build_prompt", return_value="prompt"):
                # _annotate_internal returns LlmAnnotation
                # But _parse_response is called which might expect a specific format.
                # Actually _call_gemini returns text and tokens.
                # _annotate_internal calls _parse_response(response) where response is the text.
                with patch.object(provider, "_parse_response") as mock_parse:
                    mock_parse.return_value = Mock(
                        scenario="Success Scenario", error=None
                    )
                    annotation = provider._annotate_internal(test_result, "source")
                    assert annotation.scenario == "Success Scenario"
                    assert not annotation.error

    @patch("httpx.post")
    @patch("httpx.get")
    def test_annotate_rate_limit_retry(self, mock_get, mock_post, mock_config):
        # Mock model list fetch
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "models": [
                {"name": "models/m1", "supportedGenerationMethods": ["generateContent"]}
            ]
        }

        # First call fails with 429, second succeeds
        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.headers = {"Retry-After": "0.1"}

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Recovered Scenario"}]}}]
        }

        mock_post.side_effect = [mock_resp_429, mock_resp_200]

        test_result = TestCaseResult(nodeid="test1", outcome="passed")

        with patch.dict("os.environ", {"GEMINI_API_TOKEN": "test-token"}):
            provider = GeminiProvider(mock_config)
            with patch.object(provider, "_build_prompt", return_value="prompt"):
                # Mock _parse_response to avoid actual parsing logic
                with patch.object(provider, "_parse_response") as mock_parse:
                    mock_parse.return_value = Mock(
                        scenario="Recovered Scenario", error=None
                    )
                    # Use a small sleep mock to speed up test
                    with patch("time.sleep"):
                        annotation = provider._annotate_internal(test_result, "source")
                        assert annotation.scenario == "Recovered Scenario"
                        assert mock_post.call_count == 2

    def test_availability(self):
        with patch.dict("os.environ", {}, clear=True):
            provider = GeminiProvider(Config(provider="gemini"))
            assert provider._check_availability() is False

        with patch.dict("os.environ", {"GEMINI_API_TOKEN": "token"}):
            provider = GeminiProvider(Config(provider="gemini"))
            assert provider._check_availability() is True
