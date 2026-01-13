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

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_llm_report.models import LlmAnnotation, TestCaseResult
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
        self._available: bool | None = None

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
        # Attempt 1: Try with full context
        annotation = self._annotate_internal(test, test_source, context_files)

        # Handle "context too long" - retry with minimal context (first time only)
        if annotation.error and "context too long" in annotation.error.lower():
            if context_files:
                # Retry with no context
                return self._annotate_internal(test, test_source, None)

        return annotation

    @abstractmethod
    def _annotate_internal(
        self,
        test: TestCaseResult,
        test_source: str,
        context_files: dict[str, str] | None = None,
    ) -> LlmAnnotation:
        """Internal annotation method implemented by subclasses.

        Args:
            test: Test result.
            test_source: Test source code.
            context_files: Optional context files.

        Returns:
            Annotation result.
        """
        pass

    def is_available(self) -> bool:
        """Check if the provider is available.

        Returns:
            True if the provider can make requests.
        """
        if self._available is not None:
            return self._available

        self._available = self._check_availability()
        return self._available

    @abstractmethod
    def _check_availability(self) -> bool:
        """Check availability (implemented by subclasses).

        Returns:
            True if available.
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

    def is_local(self) -> bool:
        """Check if this is a local provider (no rate limiting needed).

        Local providers like Ollama run on the user's machine and don't need
        rate limiting to avoid API quotas.

        Returns:
            True if the provider runs locally.
        """
        return False

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

    def _parse_response(self, response: str) -> LlmAnnotation:
        """Parse the LLM response into an annotation.

        Args:
            response: Raw LLM response.

        Returns:
            Parsed LlmAnnotation.
        """
        from pytest_llm_report.llm.schemas import extract_json_from_response
        from pytest_llm_report.models import LlmAnnotation

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
