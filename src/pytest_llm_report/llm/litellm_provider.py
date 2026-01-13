# SPDX-License-Identifier: MIT
"""LiteLLM provider for multiple LLM backends.

Uses LiteLLM to support OpenAI, Anthropic, and other providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.models import LlmAnnotation

if TYPE_CHECKING:
    from pytest_llm_report.models import TestCaseResult


class LiteLLMProvider(LlmProvider):
    """LiteLLM provider for multiple LLM backends."""

    def _annotate_internal(
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

        from pytest_llm_report.llm.base import SYSTEM_PROMPT

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
            msg = str(e)
            # Map specific errors if needed, though most providers return clear messages
            if "context_length_exceeded" in msg or "maximum context length" in msg:
                # Ensure we trigger the base class fallback
                return LlmAnnotation(error=f"Context too long: {msg}")
            return LlmAnnotation(error=msg)

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
