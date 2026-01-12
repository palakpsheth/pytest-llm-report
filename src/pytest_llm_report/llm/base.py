# SPDX-License-Identifier: MIT
"""Base class for LLM providers.

All LLM providers must implement the LlmProvider protocol to ensure
consistent behavior across different backends.

Component Contract:
    Input: Test code, context, Config
    Output: LlmAnnotation
    Dependencies: models
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_llm_report.models import LlmAnnotation, TestCaseResult
    from pytest_llm_report.options import Config


class LlmProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers must implement this interface.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the provider.

        Args:
            config: Plugin configuration.
        """
        self.config = config

    @abstractmethod
    def annotate(
        self,
        test: TestCaseResult,
        test_source: str,
        context_files: dict[str, str] | None = None,
    ) -> LlmAnnotation:
        """Generate an LLM annotation for a test.

        Args:
            test: Test result to annotate.
            test_source: Source code of the test function.
            context_files: Optional dict of file paths to content.

        Returns:
            LlmAnnotation with scenario, why_needed, key_assertions.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available.

        Returns:
            True if the provider can make requests.
        """
        pass

    def get_rate_limits(self) -> LlmRateLimits | None:
        """Get rate limits for the provider/model, if available.

        Returns:
            LlmRateLimits when the provider can supply rate limits.
        """
        return None

    def get_model_name(self) -> str:
        """Get the model name being used.

        Returns:
            Model name or empty string.
        """
        return self.config.model or ""


@dataclass(frozen=True)
class LlmRateLimits:
    """Rate limit information for LLM providers."""

    requests_per_minute: int | None = None
    tokens_per_minute: int | None = None
    requests_per_day: int | None = None


def get_provider(config: Config) -> LlmProvider:
    """Get the appropriate LLM provider for the config.

    Args:
        config: Plugin configuration.

    Returns:
        LlmProvider instance.

    Raises:
        ValueError: If provider is unknown.
    """
    from pytest_llm_report.llm.noop import NoopProvider

    provider_name = config.provider.lower()

    if provider_name == "none":
        return NoopProvider(config)

    if provider_name == "ollama":
        from pytest_llm_report.llm.ollama import OllamaProvider

        return OllamaProvider(config)

    if provider_name == "litellm":
        from pytest_llm_report.llm.litellm_provider import LiteLLMProvider

        return LiteLLMProvider(config)

    if provider_name == "gemini":
        from pytest_llm_report.llm.gemini import GeminiProvider

        return GeminiProvider(config)

    raise ValueError(f"Unknown LLM provider: {provider_name}")
