# SPDX-License-Identifier: MIT
"""Gemini LLM provider.

Connects to the Gemini API for LLM annotations.
"""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.models import LlmAnnotation, LlmTokenUsage

if TYPE_CHECKING:
    from pytest_llm_report.models import TestCaseResult
    from pytest_llm_report.options import Config


@dataclass(frozen=True)
class _GeminiRateLimitConfig:
    requests_per_minute: int | None = None
    tokens_per_minute: int | None = None
    requests_per_day: int | None = None


class _GeminiRateLimitExceeded(Exception):
    def __init__(self, limit_type: str, retry_after: float | None = None) -> None:
        super().__init__(limit_type)
        self.limit_type = limit_type
        self.retry_after = retry_after


class _GeminiRateLimiter:
    def __init__(self, limits: _GeminiRateLimitConfig) -> None:
        self._limits = limits
        self._request_times: deque[float] = deque()
        self._token_usage: deque[tuple[float, int]] = deque()
        self._daily_requests: deque[float] = deque()

    def next_available_in(self, request_tokens: int) -> float | None:
        now = time.monotonic()
        self._prune(now)

        if self._limits.requests_per_day:
            if len(self._daily_requests) >= self._limits.requests_per_day:
                return None

        return max(
            self._seconds_until_rpm_available(now),
            self._seconds_until_tpm_available(now, request_tokens),
        )

    def wait_for_slot(self, request_tokens: int) -> None:
        wait_for = self.next_available_in(request_tokens)
        if wait_for is None:
            raise _GeminiRateLimitExceeded("requests_per_day")
        if wait_for > 0:
            time.sleep(wait_for)
        self.record_request()

    def record_tokens(self, tokens_used: int) -> None:
        if tokens_used <= 0:
            return
        now = time.monotonic()
        self._token_usage.append((now, tokens_used))
        self._prune(now)

    def record_request(self) -> None:
        self._record_request(time.monotonic())

    def _record_request(self, now: float) -> None:
        self._request_times.append(now)
        self._daily_requests.append(time.time())
        self._prune(now)

    def _prune(self, now: float) -> None:
        cutoff_minute = now - 60.0
        while self._request_times and self._request_times[0] < cutoff_minute:
            self._request_times.popleft()
        while self._token_usage and self._token_usage[0][0] < cutoff_minute:
            self._token_usage.popleft()

        cutoff_day = time.time() - 86400.0
        while self._daily_requests and self._daily_requests[0] < cutoff_day:
            self._daily_requests.popleft()

    def _seconds_until_rpm_available(self, now: float) -> float:
        limit = self._limits.requests_per_minute
        if not limit:
            return 0.0
        if len(self._request_times) < limit:
            return 0.0
        return max(0.0, self._request_times[0] + 60.0 - now)

    def _seconds_until_tpm_available(self, now: float, request_tokens: int) -> float:
        limit = self._limits.tokens_per_minute
        if not limit:
            return 0.0
        if request_tokens <= 0:
            return 0.0
        if request_tokens >= limit and not self._token_usage:
            return 0.0
        tokens_used = sum(tokens for _, tokens in self._token_usage)
        if tokens_used + request_tokens <= limit:
            return 0.0
        remaining = tokens_used
        for timestamp, tokens in self._token_usage:
            remaining -= tokens
            if remaining + request_tokens <= limit:
                return max(0.0, timestamp + 60.0 - now)
        if self._token_usage:
            return max(0.0, self._token_usage[0][0] + 60.0 - now)
        return 0.0


# Time windows for recovery logic
_DAILY_LIMIT_WINDOW = 24 * 3600  # 24 hours for daily limit reset
_MODEL_LIST_REFRESH_INTERVAL = 6 * 3600  # 6 hours for model list refresh


class GeminiProvider(LlmProvider):
    """Gemini LLM provider."""

    def __init__(self, config: Config) -> None:
        """Initialize the Gemini provider.

        Args:
            config: Plugin configuration.
        """
        super().__init__(config)
        self._api_key = os.getenv("GEMINI_API_TOKEN")
        # self._available handled by base
        self._rate_limits: dict[str, _GeminiRateLimitConfig] = {}
        self._rate_limiters: dict[str, _GeminiRateLimiter] = {}
        self._models: list[str] | None = None
        self._token_limits: dict[str, int] = {}  # Map model name to input token limit
        self._models_fetched_at: float = 0.0
        # Track when each model hit its daily limit (for recovery after 24h)
        self._model_exhausted_at: dict[str, float] = {}
        self._cooldowns: dict[str, float] = {}

    def _annotate_internal(
        self,
        test: TestCaseResult,
        test_source: str,
        context_files: dict[str, str] | None = None,
        prompt_override: str | None = None,
    ) -> LlmAnnotation:
        """Generate an annotation using Gemini.

        Args:
            test: Test result to annotate.
            test_source: Source code of the test function.
            context_files: Optional context files.
            prompt_override: Optional pre-constructed prompt.

        Returns:
            LlmAnnotation with parsed response.
        """
        try:
            import google.generativeai as genai  # type: ignore
            from google.api_core import exceptions  # type: ignore
        except ImportError:
            return LlmAnnotation(
                error="google-generativeai not installed. Install with: pip install google-generativeai"
            )

        # Configure the model
        genai.configure(api_key=self._api_key)
        model_name = self.config.model or "gemini-1.5-flash"
        model = genai.GenerativeModel(model_name)

        # Select system prompt
        system_prompt = self._select_system_prompt(test_source)

        # Build prompt or use override
        if prompt_override:
            prompt = prompt_override
        else:
            prompt = self._build_prompt(test, test_source, context_files)

        api_token = os.getenv("GEMINI_API_TOKEN")
        if not api_token:
            return LlmAnnotation(error="GEMINI_API_TOKEN is not set")
        estimated_tokens = self._estimate_request_cost(prompt, system_prompt)

        try:
            models = self._ensure_models_and_limits(api_token)
        except ImportError:
            return LlmAnnotation(
                error="httpx not installed. Install with: pip install httpx"
            )

        daily_limit_hit = False
        attempts = 0
        max_attempts = max(1, len(models) * 2)
        while attempts < max_attempts:
            attempts += 1
            now = time.monotonic()
            wall_now = time.time()
            candidates: list[tuple[float, str]] = []
            for model in models:
                # Check if model was exhausted but has since recovered (24h passed)
                exhausted_at = self._model_exhausted_at.get(model)
                if exhausted_at is not None:
                    if wall_now - exhausted_at >= _DAILY_LIMIT_WINDOW:
                        # Model's daily limit has reset - recover it
                        del self._model_exhausted_at[model]
                        if model in self._rate_limiters:
                            # Reset rate limiter for fresh tracking
                            limits = self._rate_limits.get(
                                model, _GeminiRateLimitConfig()
                            )
                            self._rate_limiters[model] = _GeminiRateLimiter(limits)
                    else:
                        # Still exhausted, skip this model
                        continue
                limiter = self._get_rate_limiter(api_token, model)
                wait_for = limiter.next_available_in(estimated_tokens)
                if wait_for is None:
                    daily_limit_hit = True
                    self._model_exhausted_at[model] = wall_now
                    continue
                cooldown_until = self._cooldowns.get(model, 0.0)
                cooldown_wait = max(0.0, cooldown_until - now)
                candidates.append((max(wait_for, cooldown_wait), model))

            if not candidates:
                break

            wait_for, model = min(candidates, key=lambda item: item[0])
            if wait_for > 0:
                time.sleep(wait_for)

            for _ in range(self.config.llm_max_retries):
                try:
                    limiter = self._get_rate_limiter(api_token, model)
                    limiter.record_request()
                    response, token_usage = self._call_gemini(
                        prompt, api_token, model, system_prompt
                    )
                    if token_usage is not None:
                        limiter.record_tokens(token_usage.total_tokens)

                    annotation = self._parse_response(response)
                    if token_usage:
                        annotation.token_usage = token_usage
                    if annotation.error:
                        # If "context too long", fail immediately so base class can fallback
                        if "context too long" in annotation.error.lower():
                            return annotation

                        # Fail immediately on other parsing errors.
                        # Retrying with the same prompt won't help with bad JSON.
                        return annotation

                    return annotation

                except (
                    genai.types.GenerationFailure,
                    exceptions.ResourceExhausted,
                ) as e:
                    # Handle specific Gemini API errors
                    if isinstance(e, exceptions.ResourceExhausted):
                        # This typically means rate limit exceeded
                        # We need to determine if it's daily, minute, or token limit
                        # The Gemini API error message might contain clues, or we fall back to a default
                        msg = str(e).lower()
                        if "daily" in msg:
                            daily_limit_hit = True
                            self._model_exhausted_at[model] = time.time()
                            break  # Try next model
                        else:
                            # Assume minute/token limit, apply cooldown
                            retry_after = 60.0  # Default cooldown
                            if "retry-after" in msg:  # Attempt to parse if available
                                try:
                                    # This is a heuristic, actual header parsing is better in httpx response
                                    retry_after_str = (
                                        msg.split("retry-after:")[1]
                                        .split(" ")[0]
                                        .strip()
                                    )
                                    retry_after = float(retry_after_str)
                                except ValueError:
                                    pass
                            self._cooldowns[model] = time.monotonic() + retry_after
                            break  # Try next model
                    elif isinstance(e, genai.types.GenerationFailure):
                        # Other generation failures, e.g., safety filters, bad prompt
                        return LlmAnnotation(error=f"Gemini generation failed: {e}")
                    else:
                        # Fallback for unexpected errors caught by this block
                        raise  # Re-raise if not specifically handled
                except _GeminiRateLimitExceeded as exc:
                    if exc.limit_type == "requests_per_day":
                        daily_limit_hit = True
                        self._model_exhausted_at[model] = time.time()
                        break  # Try next model
                    if exc.limit_type in {"requests_per_minute", "tokens_per_minute"}:
                        retry_after = (
                            exc.retry_after if exc.retry_after is not None else 60.0
                        )
                        self._cooldowns[model] = time.monotonic() + retry_after
                        break  # Try next model
                    raise
                except (RuntimeError, ValueError, AttributeError) as e:
                    return LlmAnnotation(error=str(e))
                except Exception as e:
                    return LlmAnnotation(error=f"Unexpected Gemini error: {e}")

                time.sleep(1)

        if daily_limit_hit:
            return LlmAnnotation(
                error="Gemini requests-per-day limit reached; skipping annotation"
            )
        return LlmAnnotation(
            error="Gemini rate limits reached for all available models"
        )

    def _check_availability(self) -> bool:
        """Check if Gemini provider is available.

        Returns:
            True if httpx is installed and token is set.
        """
        try:
            import httpx  # noqa: F401

            return bool(os.getenv("GEMINI_API_TOKEN"))
        except ImportError:
            return False

    def _get_rate_limiter(self, api_token: str, model: str) -> _GeminiRateLimiter:
        if model not in self._rate_limiters:
            limits = self._ensure_rate_limits(api_token, model)
            self._rate_limiters[model] = _GeminiRateLimiter(limits)
        return self._rate_limiters[model]

    def _ensure_rate_limits(self, api_token: str, model: str) -> _GeminiRateLimitConfig:
        if model in self._rate_limits:
            return self._rate_limits[model]
        try:
            limits = self._fetch_rate_limits(api_token, model)
        except Exception:
            limits = _GeminiRateLimitConfig()
        if limits.requests_per_minute is None:
            limits = _GeminiRateLimitConfig(
                requests_per_minute=self.config.llm_requests_per_minute,
                tokens_per_minute=limits.tokens_per_minute,
                requests_per_day=limits.requests_per_day,
            )
        if limits.requests_per_minute is not None:
            limits = _GeminiRateLimitConfig(
                requests_per_minute=min(
                    limits.requests_per_minute, self.config.llm_requests_per_minute
                ),
                tokens_per_minute=limits.tokens_per_minute,
                requests_per_day=limits.requests_per_day,
            )
        self._rate_limits[model] = limits
        return limits

    def _call_gemini(
        self, prompt: str, api_token: str, model: str, system_prompt: str
    ) -> tuple[str, LlmTokenUsage | None]:
        """Make a request to the Gemini API.

        Args:
            prompt: User prompt.
            api_token: Gemini API token.
            model: Model name.
            system_prompt: System instruction.

        Returns:
            Response text and token usage if available.
        """
        import httpx

        model = self._normalize_model_name(model)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_token}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {
                "temperature": 0.3,
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "scenario": {"type": "string"},
                        "why_needed": {"type": "string"},
                        "key_assertions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["scenario", "why_needed"],
                },
            },
        }
        response = httpx.post(
            url, json=payload, timeout=self.config.llm_timeout_seconds
        )
        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", 60.0))
            raise _GeminiRateLimitExceeded(
                "requests_per_minute", retry_after=retry_after
            )
        response.raise_for_status()
        data = response.json()
        text = ""
        for part in data.get("candidates", [])[0].get("content", {}).get("parts", []):
            text += part.get("text", "")

        token_usage = None
        if "usageMetadata" in data:
            meta = data["usageMetadata"]
            token_usage = LlmTokenUsage(
                prompt_tokens=meta.get("promptTokenCount", 0),
                completion_tokens=meta.get("candidatesTokenCount", 0),
                total_tokens=meta.get("totalTokenCount", 0),
            )
        return text, token_usage

    def _fetch_rate_limits(self, api_token: str, model: str) -> _GeminiRateLimitConfig:
        import httpx

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._normalize_model_name(model)}?key={api_token}"
        )
        response = httpx.get(url, timeout=self.config.llm_timeout_seconds)
        response.raise_for_status()
        data = response.json()
        return self._parse_rate_limits(data.get("rateLimits", []))

    def _parse_rate_limits(
        self, rate_limits: list[dict[str, object]]
    ) -> _GeminiRateLimitConfig:
        rpm = None
        tpm = None
        rpd = None
        for limit in rate_limits:
            name = str(limit.get("name", "")).lower().replace(" ", "").replace("-", "")
            value = limit.get("value")
            if not isinstance(value, int):
                continue
            if "requestsperminute" in name or name in {"rpm", "requests_per_minute"}:
                rpm = value
            elif "tokensperminute" in name or name in {"tpm", "tokens_per_minute"}:
                tpm = value
            elif "requestsperday" in name or name in {"rpd", "requests_per_day"}:
                rpd = value
        return _GeminiRateLimitConfig(
            requests_per_minute=rpm,
            tokens_per_minute=tpm,
            requests_per_day=rpd,
        )

    def _estimate_request_cost(self, prompt: str, system_prompt: str) -> int:
        # Estimate ~4 characters per token for prompt and system prompt
        estimated_prompt_tokens = len(prompt) // 4
        estimated_system_prompt_tokens = len(system_prompt) // 4
        return max(1, estimated_prompt_tokens + estimated_system_prompt_tokens)

    def _normalize_model_name(self, model: str) -> str:
        if model.startswith("models/"):
            return model.split("/", 1)[1]
        return model

    def get_max_context_tokens(self) -> int:
        """Get the maximum number of input tokens allowed for the current model.

        Returns:
            Max input tokens.
        """
        model_name = self.get_model_name()
        # Ensure models are fetched to populate limits
        if not self._token_limits:
            api_token = os.getenv("GEMINI_API_TOKEN")
            if api_token:
                self._ensure_models_and_limits(api_token)

        return self._token_limits.get(model_name, 4096)

    def _ensure_models_and_limits(self, api_token: str) -> list[str]:
        # Check if we should refresh the model list (every 6 hours for long sessions)
        now = time.time()
        should_refresh = self._models is None or (
            now - self._models_fetched_at >= _MODEL_LIST_REFRESH_INTERVAL
        )

        if should_refresh:
            self._models, self._token_limits = self._fetch_available_models(api_token)
            self._models_fetched_at = now
            if not self._models:
                self._models = [self.config.model or "gemini-1.5-flash-latest"]
            preferred = self._parse_preferred_models()
            available_set = set(self._models)

            # Start with preferred models that are available, in preferred order.
            ordered_models = [m for m in preferred if m in available_set]

            # Add other available models, preserving their original relative order.
            seen_models = set(ordered_models)
            ordered_models.extend([m for m in self._models if m not in seen_models])
            self._models = ordered_models

        assert self._models is not None
        for model in self._models:
            self._ensure_rate_limits(api_token, model)
        return self._models

    def _parse_preferred_models(self) -> list[str]:
        if not self.config.model:
            return []
        if self.config.model.strip().lower() == "all":
            return []
        return [
            self._normalize_model_name(part.strip())
            for part in self.config.model.split(",")
            if part.strip()
        ]

    def _fetch_available_models(
        self, api_token: str
    ) -> tuple[list[str], dict[str, int]]:
        import httpx

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_token}"
        try:
            response = httpx.get(url, timeout=self.config.llm_timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return [], {}

        models = []
        limits = {}

        for model_info in data.get("models", []):
            name = model_info.get("name")
            if not isinstance(name, str):
                continue
            methods = model_info.get("supportedGenerationMethods", [])
            if not isinstance(methods, list):
                continue
            if "generateContent" in methods:
                normalized_name = self._normalize_model_name(name)
                models.append(normalized_name)

                # Extract input token limit
                input_limit = model_info.get("inputTokenLimit")
                if isinstance(input_limit, int):
                    limits[normalized_name] = input_limit
                else:
                    # Fallback defaults for common models if API doesn't return it
                    if "flash" in normalized_name:
                        limits[normalized_name] = 1_000_000
                    elif "pro" in normalized_name:
                        limits[normalized_name] = (
                            2_000_000 if "1.5" in normalized_name else 32_000
                        )

        return models, limits
