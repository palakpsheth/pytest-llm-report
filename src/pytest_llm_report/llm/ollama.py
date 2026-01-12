# SPDX-License-Identifier: MIT
"""Ollama LLM provider.

Connects to a local or remote Ollama server for LLM annotations.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.models import LlmAnnotation

if TYPE_CHECKING:
    from pytest_llm_report.models import TestCaseResult
    from pytest_llm_report.options import Config


# System prompt for test annotation
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


class OllamaProvider(LlmProvider):
    """Ollama LLM provider.

    Connects to a local or remote Ollama server.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the Ollama provider.

        Args:
            config: Plugin configuration.
        """
        super().__init__(config)
        self._available: bool | None = None

    def annotate(
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

        # Build prompt
        prompt = self._build_prompt(test, test_source, context_files)

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self._call_ollama(prompt)
                annotation = self._parse_response(response)

                # If we got a valid annotation (no error), return it
                if not annotation.error:
                    return annotation

                # Store the error and prepare to retry.
                # Avoid retrying on permanent errors
                if "context too long" in annotation.error.lower():
                    return annotation

                last_error = annotation.error

                # If we are here, we have a JSON error, so we retry

            except Exception as e:
                last_error = str(e)
                # Network errors etc.

            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # 2s, 4s, 6s backoff

        return LlmAnnotation(
            error=f"Failed after {max_retries} retries. Last error: {last_error}"
        )

    def is_available(self) -> bool:
        """Check if Ollama is available.

        Returns:
            True if Ollama server responds.
        """
        if self._available is not None:
            return self._available

        try:
            import httpx

            url = f"{self.config.ollama_host}/api/tags"
            response = httpx.get(url, timeout=5.0)
            self._available = response.status_code == 200
        except Exception:
            self._available = False

        return self._available

    def is_local(self) -> bool:
        """Ollama runs locally - no rate limiting needed.

        Returns:
            True, as Ollama is a local provider.
        """
        return True

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
                parts.append(content[:2000])  # Truncate long files
                parts.append("```")

        return "\n".join(parts)

    def _call_ollama(self, prompt: str) -> str:
        """Make a request to the Ollama API.

        Args:
            prompt: User prompt.

        Returns:
            Response text.
        """
        import httpx

        url = f"{self.config.ollama_host}/api/generate"
        payload = {
            "model": self.config.model or "llama3.2",
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
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

    def _parse_response(self, response: str) -> LlmAnnotation:
        """Parse the LLM response into an annotation.

        Args:
            response: Raw LLM response.

        Returns:
            Parsed LlmAnnotation.
        """
        from pytest_llm_report.llm.schemas import extract_json_from_response

        # Try to extract JSON from response (handles code fences)
        json_str = extract_json_from_response(response)
        if not json_str:
            return LlmAnnotation(error="Failed to parse LLM response as JSON")

        try:
            data = json.loads(json_str)

            # Validate response structure
            scenario = data.get("scenario", "")
            why_needed = data.get("why_needed", "")
            key_assertions = data.get("key_assertions", [])

            # Ensure types are correct
            if not isinstance(scenario, str):
                scenario = str(scenario) if scenario else ""
            if not isinstance(why_needed, str):
                why_needed = str(why_needed) if why_needed else ""
            if not isinstance(key_assertions, list):
                return LlmAnnotation(
                    error="Invalid response: key_assertions must be a list"
                )
            # Ensure all assertions are strings
            key_assertions = [str(a) for a in key_assertions if a]

            return LlmAnnotation(
                scenario=scenario,
                why_needed=why_needed,
                key_assertions=key_assertions,
                confidence=0.8,  # Default confidence for successful parse
            )
        except json.JSONDecodeError:
            return LlmAnnotation(error="Failed to parse LLM response as JSON")
