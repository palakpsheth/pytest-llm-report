# SPDX-License-Identifier: MIT
"""Gemini LLM provider.

Connects to the Gemini API for LLM annotations.
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pytest_llm_report.llm.base import LlmProvider, LlmRateLimits
from pytest_llm_report.models import LlmAnnotation

if TYPE_CHECKING:
    from pytest_llm_report.models import TestCaseResult
    from pytest_llm_report.options import Config


SYSTEM_PROMPT = """You are a helpful assistant that analyzes Python test code.
Given a test function, provide a structured annotation with:
1. scenario: What the test verifies (1-3 sentences)
2. why_needed: What bug or regression this test prevents (1-3 sentences)
3. key_assertions: The critical checks performed (3-8 bullet points)

Respond ONLY with valid JSON in this exact format:
{
  "scenario": "...",
  "why_needed": "...",
  "key_assertions": ["...", "..."]
}"""


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
        self._available: bool | None = None
        self._rate_limits: dict[str, _GeminiRateLimitConfig] = {}
        self._rate_limiters: dict[str, _GeminiRateLimiter] = {}
        self._models: list[str] | None = None
        self._models_fetched_at: float = 0.0
        # Track when each model hit its daily limit (for recovery after 24h)
        self._model_exhausted_at: dict[str, float] = {}
        self._cooldowns: dict[str, float] = {}

    def annotate(
        self,
        test: TestCaseResult,
        test_source: str,
        context_files: dict[str, str] | None = None,
    ) -> LlmAnnotation:
        """Generate an annotation using Gemini.

        Args:
            test: Test result to annotate.
            test_source: Source code of the test function.
            context_files: Optional context files.

        Returns:
            LlmAnnotation with parsed response.
        """
        try:
            import httpx  # noqa: F401
        except ImportError:
            return LlmAnnotation(
                error="httpx not installed. Install with: pip install httpx"
            )

        api_token = os.getenv("GEMINI_API_TOKEN")
        if not api_token:
            return LlmAnnotation(error="GEMINI_API_TOKEN is not set")

        prompt = self._build_prompt(test, test_source, context_files)
        estimated_tokens = self._estimate_tokens(prompt)

        models = self._ensure_models_and_limits(api_token)

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

            try:
                limiter = self._get_rate_limiter(api_token, model)
                limiter.record_request()
                response, tokens_used = self._call_gemini(prompt, api_token, model)
                if tokens_used is not None:
                    limiter.record_tokens(tokens_used)
                return self._parse_response(response)
            except _GeminiRateLimitExceeded as exc:
                if exc.limit_type == "requests_per_day":
                    daily_limit_hit = True
                    self._model_exhausted_at[model] = time.time()
                    continue
                if exc.limit_type in {"requests_per_minute", "tokens_per_minute"}:
                    retry_after = exc.retry_after or 60.0
                    self._cooldowns[model] = time.monotonic() + retry_after
                    continue
                raise
            except Exception as e:
                return LlmAnnotation(error=str(e))

        if daily_limit_hit:
            return LlmAnnotation(
                error="Gemini requests-per-day limit reached; skipping annotation"
            )
        return LlmAnnotation(
            error="Gemini rate limits reached for all available models"
        )

    def is_available(self) -> bool:
        """Check if Gemini provider is available.

        Returns:
            True if httpx is installed and token is set.
        """
        if self._available is not None:
            return self._available

        try:
            import httpx  # noqa: F401

            self._available = bool(os.getenv("GEMINI_API_TOKEN"))
        except ImportError:
            self._available = False

        return self._available

    def get_rate_limits(self) -> LlmRateLimits | None:
        """Get rate limits for the configured Gemini model."""
        api_token = os.getenv("GEMINI_API_TOKEN")
        if not api_token:
            return None
        models = self._ensure_models_and_limits(api_token)
        if not models:
            return None
        limits = self._rate_limits.get(models[0])
        if not limits:
            return None
        return LlmRateLimits(
            requests_per_minute=limits.requests_per_minute,
            tokens_per_minute=limits.tokens_per_minute,
            requests_per_day=limits.requests_per_day,
        )

    def _build_prompt(
        self,
        test: TestCaseResult,
        test_source: str,
        context_files: dict[str, str] | None = None,
    ) -> str:
        """Build the prompt for the LLM.

        Args:
            test: Test result.
            test_source: Test source code.
            context_files: Optional context files.

        Returns:
            Prompt string.
        """
        parts = [f"Test: {test.nodeid}", "", "```python", test_source, "```"]

        if context_files:
            parts.append("\nRelevant context:")
            for path, content in list(context_files.items())[:5]:
                parts.append(f"\n{path}:")
                parts.append("```python")
                parts.append(content[:2000])
                parts.append("```")

        return "\n".join(parts)

    def _call_gemini(
        self, prompt: str, api_token: str, model: str
    ) -> tuple[str, int | None]:
        """Make a request to the Gemini API.

        Args:
            prompt: User prompt.
            api_token: Gemini API token.

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
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {"temperature": 0.3},
        }

        max_retries = 3
        base_backoff = 1.0
        response = None
        last_delay = None
        for attempt in range(max_retries + 1):
            response = httpx.post(
                url,
                json=payload,
                timeout=self.config.llm_timeout_seconds,
            )
            if response.status_code != 429:
                response.raise_for_status()
                break
            if attempt >= max_retries:
                raise _GeminiRateLimitExceeded(
                    "requests_per_minute", retry_after=last_delay
                )
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = base_backoff * (2**attempt)
            else:
                delay = base_backoff * (2**attempt)
            last_delay = delay
            time.sleep(delay)

        if response is None:
            raise RuntimeError(
                "Failed to get a response from Gemini API after retries."
            )
        data = response.json()
        tokens_used = None
        usage_metadata = data.get("usageMetadata") or {}
        total_tokens = usage_metadata.get("totalTokenCount")
        if isinstance(total_tokens, int):
            tokens_used = total_tokens
        candidates = data.get("candidates", [])
        if not candidates:
            return "", tokens_used
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return "", tokens_used
        return str(parts[0].get("text", "")), tokens_used

    def _parse_response(self, response: str) -> LlmAnnotation:
        """Parse the LLM response into an annotation.

        Args:
            response: Raw LLM response.

        Returns:
            Parsed LlmAnnotation.
        """
        from pytest_llm_report.llm.schemas import extract_json_from_response

        json_str = extract_json_from_response(response)
        if not json_str:
            return LlmAnnotation(error="Failed to parse LLM response as JSON")

        try:
            data = json.loads(json_str)

            scenario = data.get("scenario", "")
            why_needed = data.get("why_needed", "")
            key_assertions = data.get("key_assertions", [])

            if not isinstance(scenario, str):
                scenario = str(scenario) if scenario else ""
            if not isinstance(why_needed, str):
                why_needed = str(why_needed) if why_needed else ""
            if not isinstance(key_assertions, list):
                return LlmAnnotation(
                    error="Invalid response: key_assertions must be a list"
                )
            key_assertions = [str(a) for a in key_assertions if a]

            return LlmAnnotation(
                scenario=scenario,
                why_needed=why_needed,
                key_assertions=key_assertions,
                confidence=0.8,
            )
        except json.JSONDecodeError:
            return LlmAnnotation(error="Failed to parse LLM response as JSON")

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

    def _estimate_tokens(self, prompt: str) -> int:
        combined = f"{SYSTEM_PROMPT}\n{prompt}"
        return max(1, len(combined) // 4)

    def _normalize_model_name(self, model: str) -> str:
        if model.startswith("models/"):
            return model.split("/", 1)[1]
        return model

    def _ensure_models_and_limits(self, api_token: str) -> list[str]:
        # Check if we should refresh the model list (every 6 hours for long sessions)
        now = time.time()
        should_refresh = self._models is None or (
            now - self._models_fetched_at >= _MODEL_LIST_REFRESH_INTERVAL
        )

        if should_refresh:
            self._models = self._fetch_available_models(api_token)
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

    def _fetch_available_models(self, api_token: str) -> list[str]:
        import httpx

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_token}"
        try:
            response = httpx.get(url, timeout=self.config.llm_timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []
        models = []
        for model_info in data.get("models", []):
            name = model_info.get("name")
            if not isinstance(name, str):
                continue
            methods = model_info.get("supportedGenerationMethods", [])
            if not isinstance(methods, list):
                continue
            if "generateContent" in methods:
                models.append(self._normalize_model_name(name))
        return models
