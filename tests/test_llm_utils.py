# SPDX-License-Identifier: MIT
"""Tests for LLM utilities."""

from pytest_llm_report.llm.utils import distribute_token_budget, estimate_tokens


def test_estimate_tokens():
    """Verify rough token estimation (chars / 4)."""
    assert estimate_tokens("") == 1  # Minimum 1
    assert estimate_tokens("a") == 1
    assert estimate_tokens("aaaa") == 1
    assert estimate_tokens("aaaa" * 10) == 10


def test_distribute_token_budget_empty():
    """Verify behavior with empty input or no budget."""
    assert distribute_token_budget({}, 100) == {}
    assert distribute_token_budget({"f1": "c"}, 0) == {}


def test_distribute_token_budget_sufficient():
    """Verify all files get full content when budget is sufficient."""
    files = {
        "f1.py": "a" * 40,  # ~10 tokens
        "f2.py": "b" * 40,  # ~10 tokens
    }
    # Need approx 20 tokens + overhead for headers
    # Overhead per file is estimate("\n{path}:\n```python\n\n```")
    # path="f1.py" -> ~25 chars -> ~6 tokens
    # Total needed ~ 16 per file = 32
    budget = 100
    allocations = distribute_token_budget(files, budget)

    assert len(allocations) == 2
    assert allocations["f1.py"] == 10
    assert allocations["f2.py"] == 10


def test_distribute_token_budget_constrained():
    """Verify water-fill algorithm satisfies smaller files first."""
    # f1 needs ~10 tokens content + ~6 overhead = 16
    # f2 needs ~100 tokens content + ~6 overhead = 106
    # Total needed = 122

    files = {
        "small.py": "a" * 40,  # ~10 tokens
        "large.py": "b" * 400,  # ~100 tokens
    }

    # Budget of 60.
    # Fair share for 2 files = 30 each.
    # small.py needs 16. It fits in 30. So it gets full 10 content.
    # Remaining budget = 60 - 16 = 44.
    # Remaining files = 1 (large.py).
    # large.py gets 44. Minus overhead (~6) -> ~38 content tokens.

    budget = 60
    allocations = distribute_token_budget(files, budget)

    assert allocations["small.py"] == 10
    # Allow some wiggle room for overhead estimation changes
    assert 30 <= allocations["large.py"] <= 45


def test_distribute_token_budget_max_files():
    """Verify max_files limit."""
    files = {f"f{i}.py": "content" for i in range(10)}
    allocations = distribute_token_budget(files, 1000, max_files=3)
    assert len(allocations) == 3


def test_distribute_token_budget_fair_share():
    """Verify fair sharing when neither fits."""
    # Two large files, budget only enough for partial both
    files = {
        "l1.py": "a" * 400,  # ~100 tokens
        "l2.py": "b" * 400,  # ~100 tokens
    }
    # Budget 100. overhead ~12 total. ~88 content.
    # Each gets ~44 content.
    budget = 100
    allocations = distribute_token_budget(files, budget)

    assert 35 <= allocations["l1.py"] <= 50
    assert 35 <= allocations["l2.py"] <= 50
    # Should be roughly equal
    assert abs(allocations["l1.py"] - allocations["l2.py"]) <= 1
