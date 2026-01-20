# SPDX-License-Identifier: MIT
"""LiteLLM provider for multiple LLM backends.

Uses LiteLLM to support OpenAI, Anthropic, and other providers.
Supports custom proxy URLs and dynamic token refresh for corporate environments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.models import LlmAnnotation, LlmTokenUsage

if TYPE_CHECKING:
    from pytest_llm_report.llm.token_refresh import TokenRefresher
    from pytest_llm_report.models import TestCaseResult
    from pytest_llm_report.options import Config


class LiteLLMProvider(LlmProvider):
    """LiteLLM provider for multiple LLM backends.

    Supports:
    - Custom API base URL for proxy servers
    - Static API key override
    - Dynamic token refresh via CLI command
    - Automatic retry on 401 (expired token)
    """

    def __init__(self, config: Config) -> None:
        """Initialize the LiteLLM provider.

        Args:
            config: Plugin configuration.
        """
        super().__init__(config)
        self._token_refresher: TokenRefresher | None = None

        # Initialize token refresher if command is configured
        if config.litellm_token_refresh_command:
            from pytest_llm_report.llm.token_refresh import TokenRefresher

            self._token_refresher = TokenRefresher(
                command=config.litellm_token_refresh_command,
                refresh_interval=config.litellm_token_refresh_interval,
                output_format=config.litellm_token_output_format,
                json_key=config.litellm_token_json_key,
            )

    def _get_api_key(self, force_refresh: bool = False) -> str | None:
        """Get the API key, refreshing if using dynamic tokens.

        Args:
            force_refresh: If True, bypass cache and refresh immediately.

        Returns:
            API key string or None to use environment variable.
        """
        if self._token_refresher:
            return self._token_refresher.get_token(force=force_refresh)
        return self.config.litellm_api_key  # Static key or None (use env)

    def _annotate_internal(
        self,
        test: TestCaseResult,
        test_source: str,
        context_files: dict[str, str] | None = None,
        prompt_override: str | None = None,
    ) -> LlmAnnotation:
        """Generate an annotation using LiteLLM.

        Args:
            test: Test result to annotate.
            test_source: Source code of the test function.
            context_files: Optional context files.
            prompt_override: Optional pre-constructed prompt.

        Returns:
            LlmAnnotation with parsed response.
        """
        try:
            import litellm
        except ImportError:
            return LlmAnnotation(
                error="litellm not installed. Install with: pip install litellm"
            )

        import time

        # Select appropriate system prompt based on test complexity
        system_prompt = self._select_system_prompt(test_source)

        # Build prompt or use override
        if prompt_override:
            prompt = prompt_override
        else:
            prompt = self._build_prompt(test, test_source, context_files)

        max_retries = self.config.llm_max_retries
        last_error = None

        # Get the Authentication error class dynamically (may not exist in test mocks)
        auth_error_cls = getattr(litellm, "AuthenticationError", None)

        for attempt in range(max_retries):
            try:
                # _make_request handles the API call and response parsing.
                # It returns an LlmAnnotation on success or for non-retriable
                # parsing errors. We can return this directly. The surrounding
                # retry loop is for transient API errors caught as exceptions.
                return self._make_request(litellm, prompt, system_prompt)

            except Exception as e:
                # Check if this is an authentication error (401)
                is_auth_error = auth_error_cls is not None and isinstance(
                    e, auth_error_cls
                )

                if is_auth_error:
                    # 401 - token may be expired
                    if self._token_refresher and attempt == 0:
                        # Force refresh and retry once
                        self._token_refresher.invalidate()
                        try:
                            return self._make_request(
                                litellm, prompt, system_prompt, force_refresh=True
                            )
                        except Exception as retry_e:
                            last_error = f"Auth retry failed: {retry_e}"
                    else:
                        return LlmAnnotation(
                            error="Authentication failed. Check API key or token."
                        )
                elif isinstance(e, (RuntimeError, ValueError, AttributeError)):
                    # Common errors that are likely not transient
                    return LlmAnnotation(error=str(e))
                else:
                    last_error = str(e)

            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))

        return LlmAnnotation(
            error=f"Failed after {max_retries} retries. Last error: {last_error}"
        )

    def _make_request(
        self,
        litellm: Any,
        prompt: str,
        system_prompt: str,
        force_refresh: bool = False,
    ) -> LlmAnnotation:
        """Make a single request to LiteLLM.

        Args:
            litellm: The litellm module.
            prompt: User prompt.
            system_prompt: System prompt.
            force_refresh: If True, force token refresh before request.

        Returns:
            LlmAnnotation on success, None if parsing failed (caller should retry).

        Raises:
            Exception: On API errors (caller should handle).
        """
        # Build completion kwargs
        kwargs = {
            "model": self.config.model or "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "timeout": self.config.llm_timeout_seconds,
            "response_format": {"type": "json_object"},  # Structured output
        }

        # Add api_base if configured
        if self.config.litellm_api_base:
            kwargs["api_base"] = self.config.litellm_api_base

        # Add api_key if available
        api_key = self._get_api_key(force_refresh=force_refresh)
        if api_key:
            kwargs["api_key"] = api_key

        response = litellm.completion(**kwargs)

        content = response.choices[0].message.content
        annotation = self._parse_response(content)

        # Extract token usage if available
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            annotation.token_usage = LlmTokenUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0),
                completion_tokens=getattr(usage, "completion_tokens", 0),
                total_tokens=getattr(usage, "total_tokens", 0),
            )

        if annotation.error:
            # If "context too long", fail immediately so base class can fallback
            if "context too long" in annotation.error.lower():
                return annotation

            # Fail immediately on other parsing errors.
            # Retrying with the same prompt won't help with bad JSON.
            return annotation

        return annotation

    def get_max_context_tokens(self) -> int:
        """Get the maximum number of input tokens allowed for the current model.

        Returns:
            Max input tokens.
        """
        try:
            import litellm

            model = self.config.model or "gpt-3.5-turbo"
            # litellm.get_max_tokens() returns dict sometimes or int?
            # It usually returns total context window.
            limit = litellm.get_max_tokens(model)
            if isinstance(limit, int):
                return limit
            if isinstance(limit, dict) and "max_tokens" in limit:
                return int(limit["max_tokens"])
        except Exception:
            pass
        return 4096

    def _check_availability(self) -> bool:
        """Check if LiteLLM is available.

        Returns:
            True if litellm is installed.
        """
        try:
            import litellm  # noqa: F401

            return True
        except ImportError:
            return False
