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

from pytest_llm_report.models import LlmAnnotation

if TYPE_CHECKING:
    from pytest_llm_report.models import TestCaseResult
    from pytest_llm_report.options import Config


# System prompts for test annotation (tiered by complexity)

# Minimal prompt for simple tests (~60 tokens)
MINIMAL_SYSTEM_PROMPT = """Analyze test, return JSON: {"scenario":"...","why_needed":"...","key_assertions":["..."]}"""

# Standard prompt for typical tests (~180 tokens)
STANDARD_SYSTEM_PROMPT = """You are a helpful assistant that analyzes Python test code.
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

# Legacy alias for backward compatibility
SYSTEM_PROMPT = STANDARD_SYSTEM_PROMPT

# Threshold for determining simple vs complex tests
COMPLEXITY_THRESHOLD = 10


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
        prompt_override: str | None = None,
    ) -> LlmAnnotation:
        """Generate an LLM annotation for a test.

        Args:
            test: Test result to annotate.
            test_source: Source code of the test function.
            context_files: Optional dict of file paths to content.
            prompt_override: Optional pre-constructed prompt (skips build_prompt).

        Returns:
            LlmAnnotation with scenario, why_needed, key_assertions.
        """
        # Attempt 1: Try with full context (or override)
        try:
            annotation = self._annotate_internal(
                test, test_source, context_files, prompt_override
            )
        except Exception as e:
            return LlmAnnotation(error=str(e))

        # Handle "context too long" - retry with minimal context (first time only)
        # Only relevant if NOT using prompt_override (which is fixed)
        if (
            not prompt_override
            and annotation.error
            and "context too long" in annotation.error.lower()
        ):
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
        prompt_override: str | None = None,
    ) -> LlmAnnotation:
        """Internal annotation method implemented by subclasses.

        Args:
            test: Test result.
            test_source: Test source code.
            context_files: Optional context files.
            prompt_override: Optional pre-constructed prompt.

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

    def _estimate_test_complexity(self, test_source: str | None) -> int:
        """Estimate test complexity for prompt tier selection.

        Args:
            test_source: Test function source code.

        Returns:
            Complexity score (0-100+).
        """
        if not test_source:
            return 0

        import re

        # Count complexity indicators using word boundaries for accuracy
        score = 0
        score += len(re.findall(r"\bassert\b", test_source)) * 3
        score += len(re.findall(r"\bmock\b", test_source, re.IGNORECASE)) * 5
        score += len(re.findall(r"\bpatch\b", test_source)) * 5
        score += len(re.findall(r"\bfixture\b", test_source)) * 2
        score += test_source.count("pytest.raises") * 3
        score += test_source.count("@") * 2  # Decorators
        score += len(test_source) // 100  # Length factor

        return score

    def _select_system_prompt(self, test_source: str | None) -> str:
        """Select appropriate system prompt based on test complexity.

        Args:
            test_source: Test function source code.

        Returns:
            Selected system prompt string.
        """
        # Check config override
        prompt_tier = getattr(self.config, "prompt_tier", "auto")

        if prompt_tier == "minimal":
            return MINIMAL_SYSTEM_PROMPT
        elif prompt_tier == "standard":
            return STANDARD_SYSTEM_PROMPT
        else:  # "auto"
            complexity = self._estimate_test_complexity(test_source)
            if complexity < COMPLEXITY_THRESHOLD:
                return MINIMAL_SYSTEM_PROMPT
            return STANDARD_SYSTEM_PROMPT

    def get_max_context_tokens(self) -> int:
        """Get the maximum number of input tokens allowed for the current model.

        Returns:
            Max input tokens (default: 4096).
        """
        return 4096

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in a string.

        This is a rough estimation (chars / 4) suitable for budgeting.

        Args:
            text: Input text.

        Returns:
             Estimated token count.
        """
        from pytest_llm_report.llm.utils import estimate_tokens

        return estimate_tokens(text)

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
        # Base prompt structure
        header = f"Test: {test.nodeid}\n\n```python\n{test_source}\n```"

        if not context_files:
            return header

        # Calculate budget
        max_tokens = self.get_max_context_tokens()
        current_tokens = self._estimate_tokens(SYSTEM_PROMPT + "\n" + header)
        available_token_budget = max(0, max_tokens - current_tokens - 100)  # Buffer

        if available_token_budget <= 0:
            return header

        from pytest_llm_report.llm.utils import distribute_token_budget

        allocations = distribute_token_budget(
            context_files, available_token_budget, max_files=5
        )

        if not allocations:
            return header

        parts = [header, "\nRelevant context:"]

        # 3. Build prompt (in original order to maintain stability)
        # Use iterating over context_files to preserve order from input
        for path, content in context_files.items():
            if path not in allocations:
                continue

            limit_tokens = allocations[path]
            if limit_tokens <= 0:
                continue

            parts.append(f"\n{path}:")
            parts.append("```python")

            # Check if we need to truncate
            # We re-estimate content tokens here or just trust allocation
            # Allocation is exact amount of tokens we can use.
            # Convert to chars:
            limit_chars = limit_tokens * 4

            if len(content) <= limit_chars:
                parts.append(content)
            else:
                parts.append(content[:limit_chars] + "\n[... truncated]")

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
