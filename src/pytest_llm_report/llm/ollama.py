# SPDX-License-Identifier: MIT
"""Ollama LLM provider.

Connects to a local or remote Ollama server for LLM annotations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.models import LlmAnnotation

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
    ) -> LlmAnnotation:
        """Generate an annotation using Ollama.

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

        import time

        # Build prompt with current context
        prompt = self._build_prompt(test, test_source, context_files)

        from pytest_llm_report.llm.base import SYSTEM_PROMPT

        max_retries = self.config.llm_max_retries
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self._call_ollama(prompt, SYSTEM_PROMPT)
                annotation = self._parse_response(response)

                if not annotation.error:
                    return annotation

                # If "context too long", fail immediately so base class can fallback
                if "context too long" in annotation.error.lower():
                    return annotation

                last_error = annotation.error

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

    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Make a request to the Ollama API.

        Args:
            prompt: User prompt.
            system_prompt: System prompt.

        Returns:
            Response text.
        """
        import httpx

        url = f"{self.config.ollama_host}/api/generate"
        payload = {
            "model": self.config.model or "llama3.2",
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
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
        return data.get("response", "")
