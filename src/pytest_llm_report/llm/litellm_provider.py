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

        import time

        from pytest_llm_report.llm.base import SYSTEM_PROMPT

        # Build prompt
        prompt = self._build_prompt(test, test_source, context_files)

        max_retries = self.config.llm_max_retries
        last_error = None

        for attempt in range(max_retries):
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
                annotation = self._parse_response(content)

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
        """Check if LiteLLM is available.

        Returns:
            True if litellm is installed.
        """
        try:
            import litellm  # noqa: F401

            return True
        except ImportError:
            return False
