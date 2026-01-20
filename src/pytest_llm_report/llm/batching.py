# SPDX-License-Identifier: MIT
"""Test batching for LLM token optimization.

Groups tests that share the same source code (parametrized tests, class methods)
to reduce the number of LLM calls and system prompt overhead.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_llm_report.models import TestCaseResult
    from pytest_llm_report.options import Config


MAX_CONTEXT_FILES_IN_PROMPT = 5


@dataclass
class BatchedRequest:
    """A group of tests to be annotated together."""

    tests: list[TestCaseResult] = field(default_factory=list)
    source_hash: str = ""
    base_nodeid: str = ""

    @property
    def primary_test(self) -> TestCaseResult | None:
        """Get the first test in the batch as the primary."""
        return self.tests[0] if self.tests else None

    @property
    def is_parametrized(self) -> bool:
        """Check if this batch represents parametrized tests."""
        return len(self.tests) > 1 and "[" in (
            self.primary_test.nodeid if self.primary_test else ""
        )


def _get_base_nodeid(nodeid: str) -> str:
    """Extract base nodeid without parameter suffix.

    Args:
        nodeid: Full test nodeid like "tests/test_foo.py::test_add[1+1=2]"

    Returns:
        Base nodeid without params: "tests/test_foo.py::test_add"
    """
    if "[" in nodeid:
        return nodeid.split("[")[0]
    return nodeid


def _compute_source_hash(source: str) -> str:
    """Compute hash of test source for grouping.

    Args:
        source: Test function source code.

    Returns:
        SHA256 hash of the source.
    """
    if not source:
        return ""
    # Use full hash or at least 32 chars to minimize collision risk
    return hashlib.sha256(source.encode()).hexdigest()[:32]


def group_tests_for_batching(
    tests: list[TestCaseResult],
    config: Config,
    get_source: Callable[[str], str],
) -> list[BatchedRequest]:
    """Group tests that can be annotated together.

    Creates batches based on:
    1. Parametrized tests (same function, different parameters)
    2. Tests with identical source code

    Args:
        tests: List of tests to group.
        config: Plugin configuration.
        get_source: Function to get test source code by nodeid.

    Returns:
        List of batched requests.
    """
    batch_parametrized = getattr(config, "batch_parametrized_tests", True)
    batch_max_size = getattr(config, "batch_max_tests", 5)

    if not batch_parametrized or batch_max_size <= 1:
        # No batching - return each test as its own batch
        return [
            BatchedRequest(tests=[t], base_nodeid=t.nodeid, source_hash="")
            for t in tests
        ]

    # Group by base nodeid (strips parameter suffix)
    by_base: dict[str, list[TestCaseResult]] = {}
    for test in tests:
        base = _get_base_nodeid(test.nodeid)
        by_base.setdefault(base, []).append(test)

    batches: list[BatchedRequest] = []
    for base_nodeid, group in by_base.items():
        if len(group) == 1:
            # Single test, no batching benefit
            batches.append(
                BatchedRequest(
                    tests=group,
                    base_nodeid=base_nodeid,
                    source_hash="",
                )
            )
        else:
            # Multiple tests with same base - these are parametrized
            # Get source from first test
            source = get_source(group[0].nodeid)
            source_hash = _compute_source_hash(source)

            # Split into batches of max size
            for i in range(0, len(group), batch_max_size):
                chunk = group[i : i + batch_max_size]
                batches.append(
                    BatchedRequest(
                        tests=chunk,
                        base_nodeid=base_nodeid,
                        source_hash=source_hash,
                    )
                )

    return batches


def build_batch_prompt(
    batch: BatchedRequest,
    test_source: str,
    context_files: dict[str, str] | None = None,
    max_tokens: int = 4096,
) -> str:
    """Build a prompt for a batch of tests.

    Args:
        batch: Batched request with tests.
        test_source: Source code of the test function.
        context_files: Optional context files.
        max_tokens: Maximum allowed input tokens (default: 4096).

    Returns:
        Prompt string for the batch.
    """
    primary = batch.primary_test
    if not primary:
        return ""

    parts = []

    if batch.is_parametrized and len(batch.tests) > 1:
        # Parametrized test batch
        parts.append(f"Test Group: {batch.base_nodeid}[*]")
        parts.append(f"Parameterizations ({len(batch.tests)} variants):")
        for test in batch.tests:
            param_suffix = (
                test.nodeid.split("[", 1)[1].rstrip("]") if "[" in test.nodeid else ""
            )
            parts.append(f"  - [{param_suffix}]")
        parts.append("")
        parts.append("```python")
        parts.append(test_source)
        parts.append("```")
        parts.append("")
        parts.append(
            "Provide ONE annotation that describes what this parameterized test verifies across all its variants."
        )
    else:
        # Single test
        parts.append(f"Test: {primary.nodeid}")
        parts.append("")
        parts.append("```python")
        parts.append(test_source)
        parts.append("```")

    from pytest_llm_report.llm.base import SYSTEM_PROMPT
    from pytest_llm_report.llm.utils import distribute_token_budget, estimate_tokens

    if context_files:
        # Calculate budget
        current_prompt = "\n".join(parts)
        current_tokens = estimate_tokens(SYSTEM_PROMPT + "\n" + current_prompt)
        available_token_budget = max(0, max_tokens - current_tokens - 100)  # Buffer

        if available_token_budget > 0:
            allocations = distribute_token_budget(
                context_files,
                available_token_budget,
                max_files=MAX_CONTEXT_FILES_IN_PROMPT,
            )

            if allocations:
                parts.append("\nRelevant context:")
                for path, content in context_files.items():
                    if path not in allocations:
                        continue

                    limit_tokens = allocations[path]
                    if limit_tokens <= 0:
                        continue

                    parts.append(f"\n{path}:")
                    parts.append("```python")

                    limit_chars = limit_tokens * 4
                    if len(content) <= limit_chars:
                        parts.append(content)
                    else:
                        parts.append(content[:limit_chars] + "\n[... truncated]")

                    parts.append("```")

    return "\n".join(parts)
