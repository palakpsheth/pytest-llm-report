from unittest.mock import MagicMock

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.models import TestCaseResult


class MockProvider(LlmProvider):
    def __init__(self, limit: int):
        self.config = MagicMock()
        self.config.model = "mock-model"
        self._limit = limit

    def get_max_context_tokens(self) -> int:
        return self._limit

    def _annotate_internal(self, *args, **kwargs):
        pass

    def _check_availability(self):
        return True


def test_truncation_logic():
    # Setup
    limit = 100
    provider = MockProvider(limit=limit)

    test_result = TestCaseResult(nodeid="tests/test_foo.py::test_bar", outcome="passed")
    test_source = "def test_bar(): pass"  # very short

    # Create large context files
    # Each "A" is ~0.25 tokens.
    # 400 chars = ~100 tokens.
    large_context = "A" * 800  # ~200 tokens

    context_files = {"file1.py": large_context}

    # Act
    prompt = provider._build_prompt(test_result, test_source, context_files)

    # Assert
    # The prompt should be truncated to fit within 100 tokens
    # minus system prompt overhead (~40-50 tokens)
    # minus header overhead (~20 tokens)
    # So context should be very small or empty

    assert len(prompt) < (limit * 5)  # Rough char check (allow some slack)
    assert (
        "[... truncated]" in prompt or "Relevant context" not in prompt
    )  # Should be heavily truncated or skipped if no budget


def test_splitting_logic():
    limit = 300
    provider = MockProvider(limit=limit)

    test_result = TestCaseResult(nodeid="t", outcome="passed")
    test_source = "s"

    # Two files, both large
    files = {
        "f1": "A" * 400,  # ~100 tok
        "f2": "B" * 400,  # ~100 tok
    }

    prompt = provider._build_prompt(test_result, test_source, files)

    # Budget roughly 200 tokens total.
    # Overhead small.
    # Budget per file ~ 80 tokens?
    # Strings should be truncated but Present.

    assert "f1" in prompt
    assert "f2" in prompt
    assert "truncated" in prompt


def test_no_truncation_needed():
    limit = 1000
    provider = MockProvider(limit=limit)

    test_result = TestCaseResult(nodeid="t", outcome="passed")
    test_source = "s"

    files = {"f1": "short content"}

    prompt = provider._build_prompt(test_result, test_source, files)

    assert "short content" in prompt
    assert "truncated" not in prompt


def test_smart_distribution():
    # Overhead: System prompt (~80 tokens) + Buffer (100 tokens) = ~180 tokens
    # We need budget for files.
    limit = 400
    provider = MockProvider(limit=limit)

    test_result = TestCaseResult(nodeid="t", outcome="passed")
    test_source = "s"

    # Budget roughly: 400 - 180 = ~220 tokens.

    # F1 needs 40 tokens (160 chars).
    # F2 needs 200 tokens (800 chars).

    # Algorithm:
    # 1. Sort by needed: [F1, F2]
    # 2. Loop 1 (F1):
    #    Remaining Budget: 220. Files: 2. Fair share: 110.
    #    F1 needed (40) <= 110? Yes.
    #    Allocate 40 to F1.
    #    Remaining Budget: 180. Remaining Files: 1.
    # 3. Loop 2 (F2):
    #    Remaining Budget: 180. Files: 1. Fair share: 180.
    #    F2 needed (200) <= 180? No.
    #    Allocate 180 to F2.

    # Result: F1=40 (Full), F2=180 (Truncated).

    # Comparison to Equal Split:
    # Budget 220. 2 Files. 110 each.
    # F1 gets 110 (Full, wasted 70 potential tokens if forced equal split logic isn't smart).
    # Wait, my previous "equal split" logic was: `tokens_per_file = budget // n`.
    # So F1 would get 110 cap, use 40. F2 would get 110 cap.
    # Total used: 40 + 110 = 150. Wasted: 70.

    # Smart split logic uses 40 + 180 = 220. Zero waste.
    # F2 gets 180 tokens (approx 720 chars) instead of 110 tokens (440 chars).

    f1_content = "A" * 160
    f2_content = "B" * 800

    files = {"f1": f1_content, "f2": f2_content}

    prompt = provider._build_prompt(test_result, test_source, files)

    assert f1_content in prompt  # F1 should be full
    assert "f2" in prompt

    # Extract F2 content from prompt
    import re

    match = re.search(r"f2:\n```python\n(B+)", prompt)
    assert match
    b_content = match.group(1)

    # Verify F2 got the extra budget.
    # We saw ~536 chars in practice (134 tokens).
    # Equal split (100 tokens) would be ~400 chars.
    # So > 480 proves optimization.
    assert len(b_content) > 480
    assert len(b_content) < 800  # Still truncated
