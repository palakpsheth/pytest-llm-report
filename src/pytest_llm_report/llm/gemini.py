# SPDX-License-Identifier: MIT
"""Gemini LLM provider.

Connects to the Gemini API for LLM annotations.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from pytest_llm_report.llm.base import LlmProvider
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


class GeminiProvider(LlmProvider):
    """Gemini LLM provider."""

    def __init__(self, config: Config) -> None:
        """Initialize the Gemini provider.

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

        try:
            response = self._call_gemini(prompt, api_token)
            return self._parse_response(response)
        except Exception as e:
            return LlmAnnotation(error=str(e))

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

    def _call_gemini(self, prompt: str, api_token: str) -> str:
        """Make a request to the Gemini API.

        Args:
            prompt: User prompt.
            api_token: Gemini API token.

        Returns:
            Response text.
        """
        import httpx

        model = self.config.model or "gemini-1.5-flash"
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_token}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generation_config": {"temperature": 0.3},
        }

        response = httpx.post(
            url,
            json=payload,
            timeout=self.config.llm_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return ""
        return str(parts[0].get("text", ""))

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
