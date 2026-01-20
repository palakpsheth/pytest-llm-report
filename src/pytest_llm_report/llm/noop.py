# SPDX-License-Identifier: MIT
"""No-op LLM provider.

This provider returns empty annotations and is used when
LLM features are disabled (provider="none").
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.models import LlmAnnotation

if TYPE_CHECKING:
    from pytest_llm_report.models import TestCaseResult
    from pytest_llm_report.options import Config


class NoopProvider(LlmProvider):
    """No-op LLM provider that returns empty annotations.

    Used when LLM features are disabled.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the no-op provider.

        Args:
            config: Plugin configuration.
        """
        super().__init__(config)

    def _annotate_internal(
        self,
        test: TestCaseResult,
        test_source: str,
        context_files: dict[str, str] | None = None,
        prompt_override: str | None = None,
    ) -> LlmAnnotation:
        """Return an empty annotation.

        Args:
            test: Test result (ignored).
            test_source: Test source (ignored).
            context_files: Context files (ignored).

        Returns:
            Empty LlmAnnotation.
        """
        return LlmAnnotation()

    def _check_availability(self) -> bool:
        """Always available.

        Returns:
            True.
        """
        return True

    def get_model_name(self) -> str:
        """Return empty model name.

        Returns:
            Empty string.
        """
        return ""
