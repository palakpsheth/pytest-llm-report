# SPDX-License-Identifier: MIT
"""Ollama LLM provider.

Connects to a local or remote Ollama server for LLM annotations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.models import LlmAnnotation, LlmTokenUsage

if TYPE_CHECKING:
    from pytest_llm_report.models import TestCaseResult


class OllamaProvider(LlmProvider):
    """Ollama LLM provider.

    Connects to a local or remote Ollama server.
    """

    def _annotate_internal(
        self,
        test: TestCaseResult,
        test_source: str,
        context_files: dict[str, str] | None = None,
        prompt_override: str | None = None,
    ) -> LlmAnnotation:
        """Generate an annotation using Ollama.

        Args:
            test: Test result to annotate.
            test_source: Source code of the test function.
            context_files: Optional context files.
            prompt_override: Optional pre-constructed prompt.

        Returns:
            LlmAnnotation with parsed response.
        """
        try:
            import httpx  # noqa: F401
        except ImportError:
            return LlmAnnotation(
                error="httpx not installed. Install with: pip install httpx"
            )

        import time

        # Build prompt with current context defined or use override
        if prompt_override:
            prompt = prompt_override
        else:
            prompt = self._build_prompt(test, test_source, context_files)

        # Select appropriate system prompt based on test complexity
        system_prompt = self._select_system_prompt(test_source)

        max_retries = self.config.llm_max_retries
        last_error = None

        for attempt in range(max_retries):
            try:
                response_data = self._call_ollama(prompt, system_prompt)
                response_text = response_data.get("response", "")
                annotation = self._parse_response(response_text)

                # Extract token usage
                if (
                    "prompt_eval_count" in response_data
                    or "eval_count" in response_data
                ):
                    prompt_tokens = response_data.get("prompt_eval_count", 0)
                    completion_tokens = response_data.get("eval_count", 0)
                    total = prompt_tokens + completion_tokens
                    annotation.token_usage = LlmTokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total,
                    )

                if annotation.error:
                    # If "context too long", fail immediately so base class can fallback
                    if "context too long" in annotation.error.lower():
                        return annotation

                    # Fail immediately on other parsing errors.
                    # Retrying with the same prompt won't help with bad JSON.
                    return annotation

                return annotation

            except (RuntimeError, ValueError, AttributeError) as e:
                # Common errors that are likely not transient (e.g. mock failures, code bugs)
                return LlmAnnotation(error=str(e))
            except Exception as e:
                last_error = str(e)

            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))

        return LlmAnnotation(
            error=f"Failed after {max_retries} retries. Last error: {last_error}"
        )

    def _check_availability(self) -> bool:
        """Check availability (implemented by subclasses).

        Returns:
            True if available.
        """
        try:
            import httpx

            url = f"{self.config.ollama_host}/api/tags"
            response = httpx.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def is_local(self) -> bool:
        """Ollama runs locally - no rate limiting needed.

        Returns:
            True, as Ollama is a local provider.
        """
        return True

    def get_max_context_tokens(self) -> int:
        """Get the maximum number of input tokens allowed for the current model.

        Tries to inspector model info, defaults to 4096.

        Returns:
            Max input tokens.
        """
        import httpx

        model = self.config.model or "llama3.2"
        # Try to show model info
        url = f"{self.config.ollama_host}/api/show"
        try:
            response = httpx.post(
                url,
                json={"name": model},
                timeout=2.0,  # Quick timeout for metadata
            )
            if response.status_code == 200:
                data = response.json()
                # Ollama models often list context window in details or parameters
                # But standardization varies.
                # "model_info" might contain "llama.context_length" or similar.

                # Check model parameters if available
                if "parameters" in data:
                    # Try to parse num_ctx
                    import re

                    match = re.search(r"num_ctx\s+(\d+)", data["parameters"])
                    if match:
                        return int(match.group(1))

                # Check model_info
                if "model_info" in data:
                    info = data["model_info"]
                    for key in [
                        "llama.context_length",
                        "context_length",
                        "general.file.context_length",
                    ]:
                        if key in info:
                            return int(info[key])

        except Exception:
            pass

        return 4096  # Safe default for many Ollama models

    def _call_ollama(self, prompt: str, system_prompt: str) -> dict[str, Any]:
        """Make a request to the Ollama API.

        Args:
            prompt: User prompt.
            system_prompt: System prompt.

        Returns:
            Full response dictionary.
        """
        import httpx

        url = f"{self.config.ollama_host}/api/generate"
        payload = {
            "model": self.config.model or "llama3.2",
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json",  # Request JSON output for compatible models
            "options": {
                "temperature": 0.3,
            },
        }

        response = httpx.post(
            url,
            json=payload,
            timeout=self.config.llm_timeout_seconds,
        )
        response.raise_for_status()

        data = response.json()
        return cast(dict[str, Any], data)
