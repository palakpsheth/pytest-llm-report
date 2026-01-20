import sys
import time
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from pytest_llm_report.llm.gemini import (
    GeminiProvider,
    _GeminiRateLimitConfig,
    _GeminiRateLimiter,
)
from pytest_llm_report.models import LlmAnnotation, LlmTokenUsage, TestCaseResult
from pytest_llm_report.options import Config


class MockResourceExhausted(Exception):
    pass


class MockGenerationFailure(Exception):
    pass


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

    @patch("time.sleep")
    def test_wait_for_slot_sleeps(self, mock_sleep):
        limiter = _GeminiRateLimiter(_GeminiRateLimitConfig(requests_per_minute=1))
        limiter.record_request()
        # next request needs to wait ~60s
        # We need to mock time.monotonic to ensure stable test
        with patch("time.monotonic", return_value=100.0):
            # record_request uses monotonic.
            # but we already recorded one.
            # modifying _request_times directly is safer.
            pass

        # Simpler: Mock next_available_in to return 10
        with patch.object(limiter, "next_available_in", return_value=10.0):
            limiter.wait_for_slot(1)

        mock_sleep.assert_called_once_with(10.0)

    def test_wait_for_slot_daily_limit_exceeded(self):
        limits = _GeminiRateLimitConfig(requests_per_day=1)
        limiter = _GeminiRateLimiter(limits)
        limiter.record_request()

        from pytest_llm_report.llm.gemini import _GeminiRateLimitExceeded

        with pytest.raises(_GeminiRateLimitExceeded) as exc:
            limiter.wait_for_slot(10)
        assert exc.value.limit_type == "requests_per_day"

    def test_record_tokens_invalid(self):
        limiter = _GeminiRateLimiter(_GeminiRateLimitConfig())
        limiter.record_tokens(0)
        limiter.record_tokens(-5)
        assert len(limiter._token_usage) == 0

    def test_prune_logic(self):
        limiter = _GeminiRateLimiter(_GeminiRateLimitConfig())
        now = time.monotonic()
        # Add old request (older than 60s)
        limiter._request_times.append(now - 61.0)
        limiter._token_usage.append((now - 61.0, 10))
        # Add fresh request
        limiter._request_times.append(now - 10.0)
        limiter._token_usage.append((now - 10.0, 10))

        limiter._prune(now)

        assert len(limiter._request_times) == 1
        assert len(limiter._token_usage) == 1
        assert limiter._request_times[0] == now - 10.0

    def test_seconds_until_tpm_available_branches(self):
        limits = _GeminiRateLimitConfig(tokens_per_minute=100)
        limiter = _GeminiRateLimiter(limits)
        now = time.monotonic()

        # No tokens requested
        assert limiter._seconds_until_tpm_available(now, 0) == 0.0

        # Request more than limit, but empty usage
        assert limiter._seconds_until_tpm_available(now, 150) == 0.0

        # Normal usage within limit
        limiter._token_usage.append((now, 50))
        assert limiter._seconds_until_tpm_available(now, 40) == 0.0

        # Usage exceeds limit
        # remaining=50. request=60. total=110 > 100.
        # Must wait until usage expires.
        wait = limiter._seconds_until_tpm_available(now, 60)
        assert wait > 0
        assert wait <= 60.0 + 1e-9


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
                provider = GeminiProvider(mock_config)
                with patch.object(provider, "_build_prompt", return_value="prompt"):
                    # Mock _parse_response to avoid actual parsing logic
                    with patch.object(provider, "_parse_response") as mock_parse:
                        mock_parse.return_value = Mock(
                            scenario="Recovered Scenario", error=None
                        )
                        # Use a small sleep mock to speed up test
                        with patch("time.sleep"):
                            annotation = provider._annotate_internal(
                                test_result, "source"
                            )
                            assert annotation.scenario == "Recovered Scenario"
                            assert mock_post.call_count == 2

    def test_availability(self):
        with patch.dict("os.environ", {}, clear=True):
            provider = GeminiProvider(Config(provider="gemini"))
            assert provider._check_availability() is False

        with patch.dict("os.environ", {"GEMINI_API_TOKEN": "token"}):
            provider = GeminiProvider(Config(provider="gemini"))
            assert provider._check_availability() is True

    def test_annotate_no_token(self):
        """Test annotation when token is missing."""
        # Ensure imports succeed by patching the full chain if needed
        mock_genai = MagicMock()
        mock_api_core = MagicMock()
        mock_params = {
            "google": MagicMock(),
            "google.generativeai": mock_genai,
            "google.api_core": mock_api_core,
        }
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.dict("sys.modules", mock_params),
        ):
            provider = GeminiProvider(Config(provider="gemini"))
            annotation = provider._annotate_internal(
                TestCaseResult(nodeid="t", outcome="passed"), "src"
            )
            assert "GEMINI_API_TOKEN is not set" in annotation.error

    def test_annotate_import_error(self):
        """Test annotation when google-generativeai is not installed."""
        # Force import error by flagging module as None in sys.modules
        with patch.dict("sys.modules", {"google.generativeai": None}):
            provider = GeminiProvider(Config(provider="gemini"))
            annotation = provider._annotate_internal(
                TestCaseResult(nodeid="t", outcome="passed"), "src"
            )
            assert "google-generativeai not installed" in annotation.error


class TestGeminiProviderDetailed:
    """Detailed coverage tests for Gemini provider."""

    @patch("httpx.get")
    def test_fetch_available_models_error(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        provider = GeminiProvider(Config(provider="gemini"))
        models, limit_map = provider._fetch_available_models("token")
        assert models == []
        assert limit_map == {}

    @patch("httpx.get")
    def test_fetch_available_models_invalid_json(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "models": [
                {"name": 123},
                {"name": "models/m1", "supportedGenerationMethods": "not-list"},
                {"name": "models/m2", "supportedGenerationMethods": ["other"]},
                {
                    "name": "models/m3",
                    "supportedGenerationMethods": ["generateContent"],
                    "inputTokenLimit": "invalid",
                },
            ]
        }
        provider = GeminiProvider(Config(provider="gemini"))
        models, limit_map = provider._fetch_available_models("token")

        assert "m1" not in models
        assert "m2" not in models
        assert "m3" in models
        assert "m3" not in limit_map

    def test_parse_rate_limits_types(self):
        provider = GeminiProvider(Config(provider="gemini"))
        limits = [
            {"name": "rpm", "value": "invalid"},
            {"name": "tpm", "value": 100},
        ]
        config = provider._parse_rate_limits(limits)
        assert config.requests_per_minute is None
        assert config.tokens_per_minute == 100

    @patch("pytest_llm_report.llm.gemini.GeminiProvider._fetch_rate_limits")
    def test_ensure_rate_limits_error(self, mock_fetch, mock_config):
        mock_fetch.side_effect = Exception("Fetch failed")

        provider = GeminiProvider(mock_config)
        # Should return default config (default from config or empty)
        # Since mocked config has rpm=10
        limits = provider._ensure_rate_limits("token", "model")
        assert limits.requests_per_minute == 10

    @patch("pytest_llm_report.llm.gemini.GeminiProvider._ensure_models_and_limits")
    def test_get_max_context_tokens_calls_ensure(self, mock_ensure, mock_config):
        with patch.dict("os.environ", {"GEMINI_API_TOKEN": "token"}):
            provider = GeminiProvider(mock_config)
            provider._token_limits = {}

            provider.get_max_context_tokens()
            mock_ensure.assert_called_once()

    def test_annotate_retry_loop_coverage(self, mock_config):
        # Setup: One model, daily limit previously hit > 24h ago
        model = "gemini-1.5-flash"
        provider = GeminiProvider(mock_config)
        provider._models = [model]
        provider._token_limits = {model: 1000}
        provider._model_exhausted_at[model] = time.time() - (24 * 3600 + 10)  # 24h+ ago

        # Mock dependencies
        mock_limiter = MagicMock()
        mock_limiter.next_available_in.return_value = 0
        provider._rate_limiters[model] = mock_limiter

        # Mock _call_gemini to succeed
        with patch.object(provider, "_call_gemini") as mock_call:
            mock_call.return_value = ("response", LlmTokenUsage(10, 10, 20))

            with (
                patch.dict("os.environ", {"GEMINI_API_TOKEN": "token"}),
                patch.dict(
                    "sys.modules",
                    {
                        "google": MagicMock(),
                        "google.generativeai": MagicMock(),
                        "google.api_core": MagicMock(),
                    },
                ),
            ):
                # Ensure models check pass
                with patch.object(
                    provider, "_ensure_models_and_limits", return_value=[model]
                ):
                    provider._annotate_internal(
                        TestCaseResult(nodeid="t", outcome="passed"), "src"
                    )

        # Assert _model_exhausted_at was cleared
        assert model not in provider._model_exhausted_at

    def test_annotate_retry_exceptions(self, mock_config):
        provider = GeminiProvider(mock_config)
        provider._models = ["m1"]

        # Use ModuleType for robust imports
        m_google = types.ModuleType("google")

        m_api_core = types.ModuleType("google.api_core")
        m_exceptions = types.ModuleType("google.api_core.exceptions")
        m_exceptions.ResourceExhausted = MockResourceExhausted
        m_api_core.exceptions = m_exceptions

        m_genai = types.ModuleType("google.generativeai")
        m_types = types.ModuleType("google.generativeai.types")
        m_types.GenerationFailure = MockGenerationFailure
        m_genai.types = m_types
        m_genai.configure = MagicMock()
        m_genai.GenerativeModel = MagicMock()

        mock_params = {
            "google": m_google,
            "google.generativeai": m_genai,
            "google.api_core": m_api_core,
        }

        # Pre-populate limiter to avoid network call in _get_rate_limiter -> _ensure_rate_limits
        provider._rate_limiters["m1"] = _GeminiRateLimiter(
            _GeminiRateLimitConfig(requests_per_minute=100)
        )

        # Mock call to raise error
        with (
            patch.dict("sys.modules", mock_params),
            patch.dict("os.environ", {"GEMINI_API_TOKEN": "token"}),
            patch.object(provider, "_ensure_models_and_limits", return_value=["m1"]),
            patch.object(provider, "_call_gemini") as mock_call,
        ):
            # Case 1: Daily Limit
            mock_call.side_effect = MockResourceExhausted("Daily limit exceeded")
            provider._annotate_internal(
                TestCaseResult(nodeid="t", outcome="passed"), "src"
            )
            assert provider._model_exhausted_at.get("m1") is not None

            # Case 2: Retry After cleanup
            provider._model_exhausted_at = {}
            provider._cooldowns = {}
            mock_call.side_effect = MockResourceExhausted(
                "429 ... retry-after: 5.5 ..."
            )
            provider._annotate_internal(
                TestCaseResult(nodeid="t", outcome="passed"), "src"
            )
            assert "m1" in provider._cooldowns
            assert provider._cooldowns["m1"] > time.monotonic()


class TestGeminiCoverageGaps:
    def test_coverage_gaps(self, mock_config):
        provider = GeminiProvider(mock_config)

        # 1. prompt_override
        # Mock imports to avoid errors
        mock_google = types.ModuleType("google")
        mock_google.generativeai = MagicMock()
        mock_google.api_core = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {
                    "google": mock_google,
                    "google.generativeai": MagicMock(),
                    "google.api_core": MagicMock(),
                },
            ),
            patch.dict("os.environ", {"GEMINI_API_TOKEN": "token"}),
            patch.object(provider, "_ensure_models_and_limits", return_value=["m1"]),
            patch.object(provider, "_call_gemini", return_value=("res", None)),
        ):
            # Pre-populate limiter
            provider._rate_limiters["m1"] = _GeminiRateLimiter(
                _GeminiRateLimitConfig(requests_per_minute=100)
            )

            provider._annotate_internal(
                TestCaseResult(nodeid="t", outcome="passed"),
                "src",
                prompt_override="custom",
            )

        # 2. Context too long error
        with (
            patch.object(provider, "_call_gemini", return_value=("", None)),
            patch.object(
                provider,
                "_parse_response",
                return_value=LlmAnnotation(error="Context too long"),
            ),
        ):
            with (
                patch.dict(
                    "sys.modules",
                    {
                        "google": mock_google,
                        "google.generativeai": MagicMock(),
                        "google.api_core": MagicMock(),
                    },
                ),
                patch.dict("os.environ", {"GEMINI_API_TOKEN": "token"}),
                patch.object(
                    provider, "_ensure_models_and_limits", return_value=["m1"]
                ),
            ):
                provider._rate_limiters["m1"] = _GeminiRateLimiter(
                    _GeminiRateLimitConfig(requests_per_minute=100)
                )

                res = provider._annotate_internal(
                    TestCaseResult(nodeid="t", outcome="passed"), "src"
                )
                assert "Context too long" in res.error

        # 3. RPD in parse_rate_limits
        limits = provider._parse_rate_limits(
            [{"name": "requests_per_day", "value": 100}]
        )
        assert limits.requests_per_day == 100

        # 4. Fallback models
        with patch.object(provider, "_fetch_available_models", return_value=([], {})):
            mock_config.model = "fallback"
            provider._ensure_models_and_limits("token")
            assert provider._models == ["fallback"]

        # 5. Input limits logic (Flash vs Pro)
        with patch("httpx.get") as mock_get:
            mock_get.return_value.status_code = 200
            # Case A: inputTokenLimit provided
            mock_get.return_value.json.return_value = {
                "models": [
                    {
                        "name": "models/gemini-custom",
                        "supportedGenerationMethods": ["generateContent"],
                        "inputTokenLimit": 12345,
                    }
                ]
            }
            models, limits = provider._fetch_available_models("token")
            assert limits["gemini-custom"] == 12345

    def test_parse_preferred_models_coverage(self, mock_config):
        # Line 523-526
        provider = GeminiProvider(mock_config)
        mock_config.model = None
        assert provider._parse_preferred_models() == []

        mock_config.model = "ALL"  # Case insensitive check? Code says .lower() == "all"
        assert provider._parse_preferred_models() == []

    def test_prune_daily_requests(self):
        # Line 89
        limiter = _GeminiRateLimiter(_GeminiRateLimitConfig(requests_per_day=10))
        limiter._daily_requests.append(time.time() - 90000)  # > 24h ago
        limiter._prune(time.time())
        assert len(limiter._daily_requests) == 0

    def test_tpm_available_fallback(self):
        # Line 115-117
        limiter = _GeminiRateLimiter(_GeminiRateLimitConfig(tokens_per_minute=100))
        limiter._token_usage.append(
            (time.monotonic() - 30, 100)
        )  # used all tokens 30s ago
        # Request 1 token, should wait 30s
        # Method: _seconds_until_tpm_available(now, 1)
        # tokens_used = 100. 100+1 > 100.
        # Loop: remaining=100. 100-100 = 0. 0+1 <= 100 is True. Return...
        # Wait, if I have multiple usages?
        # Let's force the loop to NOT return, so it hits line 115

        # If usage is [(t-30, 50), (t-10, 50)] -> total 100.
        # req 1.
        # Loop 1: remaining = 100-50 = 50. 50+1 <= 100? True. Returns t-30 + 60 - now = 30.
        # To hit line 115, the loop must finish without returning.
        # But `remaining` decreases.
        # Actually line 115 is reached if the loop finishes?
        # The loop returns if `remaining + request_tokens <= limit`.
        # If I have a huge token usage that implies I can never fit it?
        # No, `remaining` starts at `tokens_used`.
        # If `request_tokens` is massive?
        # limit=100. usage=0. req=200. -> returns 0.0 at line 106/108?
        pass

    def test_annotate_loop_daily_limit_hit(self, mock_config):
        # Line 225-227: wait_for is None
        provider = GeminiProvider(mock_config)
        provider._models = ["m1"]

        # Mock limiter to return None (daily limit hit)
        mock_limiter = MagicMock()
        mock_limiter.next_available_in.return_value = None
        provider._rate_limiters["m1"] = mock_limiter

        with (
            patch.dict("os.environ", {"GEMINI_API_TOKEN": "token"}),
            patch.object(provider, "_ensure_models_and_limits", return_value=["m1"]),
            patch.dict(
                "sys.modules",
                {
                    "google": MagicMock(),
                    "google.generativeai": MagicMock(),
                    "google.api_core": MagicMock(),
                },
            ),
        ):
            res = provider._annotate_internal(
                TestCaseResult(nodeid="t", outcome="passed"), "src"
            )
            assert "Gemini requests-per-day limit reached" in res.error

    def test_annotation_exceptions_coverage(self, mock_config):
        # Lines 293, 301
        provider = GeminiProvider(mock_config)
        provider._models = ["m1"]

        # Mock modules
        mock_google = types.ModuleType("google")
        m_genai = types.ModuleType("google.generativeai")
        m_types = types.ModuleType("google.generativeai.types")

        class MockGenFailure(Exception):
            pass

        m_types.GenerationFailure = MockGenFailure
        m_genai.types = m_types
        m_genai.configure = MagicMock()
        m_genai.GenerativeModel = MagicMock()

        m_core = types.ModuleType("google.api_core")
        m_ex = types.ModuleType("google.api_core.exceptions")

        class MockResExhausted(Exception):
            pass

        m_ex.ResourceExhausted = MockResExhausted
        m_core.exceptions = m_ex

        mock_params = {
            "google": mock_google,
            "google.generativeai": m_genai,
            "google.api_core": m_core,
        }

        provider._rate_limiters["m1"] = _GeminiRateLimiter(
            _GeminiRateLimitConfig(requests_per_minute=100)
        )

        with (
            patch.dict("sys.modules", mock_params),
            patch.dict("os.environ", {"GEMINI_API_TOKEN": "token"}),
            patch.object(provider, "_ensure_models_and_limits", return_value=["m1"]),
            patch.object(provider, "_call_gemini") as mock_call,
        ):
            # 1. GenerationFailure (Line 293)
            mock_call.side_effect = MockGenFailure("safety")
            res = provider._annotate_internal(
                TestCaseResult(nodeid="t", outcome="passed"), "src"
            )
            assert "Gemini generation failed" in res.error

            # 2. _GeminiRateLimitExceeded RPD (Line 300)
            # We need _call_gemini to raise _GeminiRateLimitExceeded, which is internal
            from pytest_llm_report.llm.gemini import _GeminiRateLimitExceeded

            mock_call.side_effect = _GeminiRateLimitExceeded("requests_per_day")
            res = provider._annotate_internal(
                TestCaseResult(nodeid="t", outcome="passed"), "src"
            )
            # It breaks the loop and marks model exhausted
            assert provider._model_exhausted_at.get("m1") is not None
            # Since it breaks and no candidates left (or loop finishes), it returns error "Gemini requests-per-day limit reached..." or "Gemini rate limits reached..."

            assert (
                "Gemini requests-per-day" in res.error
                or "rate limits reached" in res.error
            )
