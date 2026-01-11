# SPDX-License-Identifier: MIT
"""LiteLLM provider for multiple LLM backends.

Uses LiteLLM to support OpenAI, Anthropic, and other providers.
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


class LiteLLMProvider(LlmProvider):
    """LiteLLM provider for multiple LLM backends."""

    def __init__(self, config: Config) -> None:
        """Initialize the LiteLLM provider.

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
        """Generate an annotation using LiteLLM.

        Args:
            test: Test result to annotate.
            test_source: Source code of the test function.
            context_files: Optional context files.

        Returns:
            LlmAnnotation with parsed response.
        """
        try:
            import litellm
        except ImportError:
            return LlmAnnotation(
                error="litellm not installed. Install with: pip install litellm"
            )

        # Build prompt
        prompt = self._build_prompt(test, test_source, context_files)

        # Make request
        try:
            response = litellm.completion(
                model=self.config.model or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                timeout=self.config.llm_timeout_seconds,
            )

            content = response.choices[0].message.content
            return self._parse_response(content)
        except Exception as e:
            return LlmAnnotation(error=str(e))

    def is_available(self) -> bool:
        """Check if LiteLLM is available.

        Returns:
            True if litellm is installed.
        """
        if self._available is not None:
            return self._available

        try:
            import litellm  # noqa: F401

            self._available = True
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

    def _parse_response(self, response: str) -> LlmAnnotation:
        """Parse the LLM response into an annotation.

        Args:
            response: Raw LLM response.

        Returns:
            Parsed LlmAnnotation.
        """
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                return LlmAnnotation(
                    scenario=data.get("scenario", ""),
                    why_needed=data.get("why_needed", ""),
                    key_assertions=data.get("key_assertions", []),
                    confidence=0.8,
                )
        except json.JSONDecodeError:
            # Fall through to return error annotation below
            pass

        return LlmAnnotation(error="Failed to parse LLM response as JSON")
