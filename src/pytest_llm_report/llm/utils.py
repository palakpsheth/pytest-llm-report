# SPDX-License-Identifier: MIT
"""Utilities for LLM operations."""

from __future__ import annotations

from typing import cast


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a string.

    This is a rough estimation (chars / 4) suitable for budgeting.

    Args:
        text: Input text.

    Returns:
         Estimated token count.
    """
    return max(1, (len(text) + 3) // 4)


def distribute_token_budget(
    files: dict[str, str],
    available_budget: int,
    max_files: int = 5,
) -> dict[str, int]:
    """Distribute token budget among files using a 'water-fill' algorithm.

    Allocates budget to smaller files first to satisfy them completely,
    then distributes remaining budget to larger files.

    Args:
        files: Dictionary of {path: content}.
        available_budget: Total tokens available for context.
        max_files: Maximum number of files to include.

    Returns:
        Dictionary of {path: allocated_tokens}. Files with 0 allocation
        should be excluded.
    """
    if not files or available_budget <= 0:
        return {}

    # Limit to max_files
    files_to_include = list(files.items())[:max_files]
    if not files_to_include:
        return {}

    # 1. Analyze files
    file_data = []
    for path, content in files_to_include:
        est = estimate_tokens(content)
        # Add a small overhead for file path line in prompt
        overhead = estimate_tokens(f"\n{path}:\n```python\n\n```")
        file_data.append(
            {
                "path": path,
                "needed": est + overhead,
                "content_tokens": est,
            }
        )

    # 2. Distribute budget
    # Sort by needed size (asc) to satisfy small files first
    sorted_indices = sorted(
        range(len(file_data)), key=lambda i: cast(int, file_data[i]["needed"])
    )

    remaining_budget = available_budget
    remaining_files = len(file_data)

    allocations: dict[str, int] = {}

    for idx in sorted_indices:
        # Calculate fair share of what's left
        if remaining_files == 0:
            break
        fair_share = remaining_budget // remaining_files

        needed = cast(int, file_data[idx]["needed"])
        path = cast(str, file_data[idx]["path"])

        if needed <= fair_share:
            # Fully satisfy this file
            allocations[path] = cast(int, file_data[idx]["content_tokens"])
            remaining_budget -= needed
        else:
            # Give it the fair share (minus overhead)
            overhead = cast(int, file_data[idx]["needed"]) - cast(
                int, file_data[idx]["content_tokens"]
            )
            allocations[path] = max(0, fair_share - overhead)
            remaining_budget -= fair_share

        remaining_files -= 1

    return allocations
