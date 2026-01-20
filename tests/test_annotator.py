# SPDX-License-Identifier: MIT
"""Tests for LLM annotation orchestration."""

from unittest.mock import MagicMock

import pytest

from pytest_llm_report.llm.annotator import annotate_tests
from pytest_llm_report.models import LlmAnnotation, TestCaseResult
from pytest_llm_report.options import Config


@pytest.fixture
def mock_provider(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock the LlmProvider."""
    provider = MagicMock()
    provider.is_available.return_value = True
    provider.is_local.return_value = False  # Default to remote
    provider.get_rate_limits.return_value = None
    provider.annotate.return_value = LlmAnnotation(
        scenario="test", why_needed="test", key_assertions=["test"]
    )

    # Mock the get_provider factory
    monkeypatch.setattr(
        "pytest_llm_report.llm.annotator.get_provider", lambda config: provider
    )
    return provider


@pytest.fixture
def mock_cache(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock the LlmCache."""
    cache = MagicMock()
    cache.get.return_value = None  # Always miss by default

    # Mock the LlmCache class
    monkeypatch.setattr(
        "pytest_llm_report.llm.annotator.LlmCache", lambda config: cache
    )
    return cache


@pytest.fixture
def mock_assembler(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock the ContextAssembler."""
    assembler = MagicMock()
    assembler.assemble.return_value = ("def test_foo(): pass", {})

    # Mock the ContextAssembler class
    monkeypatch.setattr(
        "pytest_llm_report.llm.annotator.ContextAssembler", lambda config: assembler
    )
    return assembler


class TestAnnotateTests:
    """Tests for annotate_tests function."""

    def test_skips_if_disabled(self):
        """Should do nothing if LLM is not enabled."""
        config = Config(provider="none")
        annotate_tests([], config)

    def test_skips_if_provider_unavailable(
        self, mock_provider: MagicMock, capsys: pytest.CaptureFixture
    ):
        """Should print message and return if provider is unavailable."""
        mock_provider.is_available.return_value = False
        config = Config(provider="ollama")

        annotate_tests([], config)

        captured = capsys.readouterr()
        assert "is not available" in captured.out

    def test_sequential_annotation(
        self, mock_provider: MagicMock, mock_cache: MagicMock, mock_assembler: MagicMock
    ):
        """Should annotate sequentially for remote providers."""
        config = Config(provider="gemini", model="gemini-pro")
        tests = [
            TestCaseResult(nodeid="test_1", outcome="passed"),
            TestCaseResult(nodeid="test_2", outcome="passed"),
        ]

        annotate_tests(tests, config)

        assert mock_provider.annotate.call_count == 2
        assert mock_cache.set.call_count == 2

        # Verify annotations were set on tests
        assert tests[0].llm_annotation is not None
        assert tests[1].llm_annotation is not None

    def test_concurrent_annotation(
        self, mock_provider: MagicMock, mock_cache: MagicMock, mock_assembler: MagicMock
    ):
        """Should annotate concurrently for local providers with concurrency > 1."""
        mock_provider.is_local.return_value = True
        config = Config(provider="ollama", model="llama2", llm_max_concurrency=2)
        tests = [
            TestCaseResult(nodeid="test_1", outcome="passed"),
            TestCaseResult(nodeid="test_2", outcome="passed"),
            TestCaseResult(nodeid="test_3", outcome="passed"),
        ]

        annotate_tests(tests, config)

        assert mock_provider.annotate.call_count == 3
        # In actual concurrent execution, order isn't guaranteed, but all should be called
        assert tests[0].llm_annotation is not None
        assert tests[1].llm_annotation is not None
        assert tests[2].llm_annotation is not None

    def test_cached_tests_are_skipped(
        self, mock_provider: MagicMock, mock_cache: MagicMock, mock_assembler: MagicMock
    ):
        """Should skip annotation for cached tests."""
        # Make first test hit cache
        cached_annotation = LlmAnnotation(
            scenario="cached", why_needed="cached", key_assertions=[]
        )
        mock_cache.get.side_effect = [cached_annotation, None]

        config = Config(provider="ollama")
        tests = [
            TestCaseResult(nodeid="test_cached", outcome="passed"),
            TestCaseResult(nodeid="test_uncached", outcome="passed"),
        ]

        annotate_tests(tests, config)

        # Assemble is called for both to check hash
        assert mock_assembler.assemble.call_count == 2
        # Cache check for both
        assert mock_cache.get.call_count == 2
        # Annotate only called for uncached one
        assert mock_provider.annotate.call_count == 1

        assert tests[0].llm_annotation == cached_annotation
        assert tests[1].llm_annotation is not None
        assert tests[1].llm_annotation.scenario == "test"  # From default mock

    def test_progress_reporting(
        self, mock_provider: MagicMock, mock_cache: MagicMock, mock_assembler: MagicMock
    ):
        """Should invoke progress callback."""
        config = Config(provider="ollama")
        tests = [TestCaseResult(nodeid="test_1", outcome="passed")]
        progress_mock = MagicMock()

        annotate_tests(tests, config, progress=progress_mock)

        assert progress_mock.call_count >= 2  # Start + Per-test

    def test_concurrent_annotation_handles_failures(
        self,
        mock_provider: MagicMock,
        mock_cache: MagicMock,
        mock_assembler: MagicMock,
        capsys: pytest.CaptureFixture,
    ):
        """Concurrent annotation should handle failures gracefully."""
        mock_provider.is_local.return_value = True
        mock_provider.annotate.side_effect = [
            LlmAnnotation(error="fail"),
            LlmAnnotation(scenario="success", why_needed="s", key_assertions=[]),
        ]

        config = Config(provider="ollama", llm_max_concurrency=2)
        tests = [
            TestCaseResult(nodeid="test_fail", outcome="passed"),
            TestCaseResult(nodeid="test_success", outcome="passed"),
        ]

        annotate_tests(tests, config)

        captured = capsys.readouterr()
        assert "1 error(s)" in captured.out
        assert "First error: fail" in captured.out

    def test_respects_opt_out_and_limit(
        self, mock_provider: MagicMock, mock_cache: MagicMock, mock_assembler: MagicMock
    ):
        """LLM annotations should skip opt-out tests and respect max tests."""
        config = Config(provider="ollama", llm_max_tests=1)
        tests = [
            TestCaseResult(nodeid="tests/test_a.py::test_a", outcome="passed"),
            TestCaseResult(
                nodeid="tests/test_b.py::test_b", outcome="passed", llm_opt_out=True
            ),
            TestCaseResult(nodeid="tests/test_c.py::test_c", outcome="passed"),
        ]

        annotate_tests(tests, config)

        assert mock_provider.annotate.call_count == 1
        assert tests[0].llm_annotation is not None
        assert tests[1].llm_annotation is None  # Opted out
        assert tests[2].llm_annotation is None  # Beyond limit

    def test_respects_rate_limit(
        self,
        mock_provider: MagicMock,
        mock_cache: MagicMock,
        mock_assembler: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """LLM annotations should respect the requests-per-minute rate limit."""
        from types import SimpleNamespace

        config = Config(
            provider="litellm",
            llm_requests_per_minute=60,
        )
        tests = [
            TestCaseResult(nodeid="tests/test_a.py::test_a", outcome="passed"),
            TestCaseResult(nodeid="tests/test_b.py::test_b", outcome="passed"),
        ]
        mock_provider.get_rate_limits.return_value = SimpleNamespace(
            requests_per_minute=30
        )
        sleep_calls: list[float] = []
        times = iter([0.0, 0.0, 2.0])

        monkeypatch.setattr(
            "pytest_llm_report.llm.annotator.time.monotonic", lambda: next(times)
        )
        monkeypatch.setattr(
            "pytest_llm_report.llm.annotator.time.sleep", sleep_calls.append
        )

        annotate_tests(tests, config)

        assert mock_provider.annotate.call_count == 2
        assert sleep_calls == [2.0]

    def test_reports_progress_messages(
        self,
        mock_provider: MagicMock,
        mock_cache: MagicMock,
        mock_assembler: MagicMock,
    ):
        """LLM annotation progress should be reported via callback."""
        config = Config(provider="litellm")
        test = TestCaseResult(
            nodeid="tests/test_progress.py::test_case", outcome="passed"
        )
        messages: list[str] = []

        annotate_tests([test], config, progress=messages.append)

        assert (
            messages[0] == "pytest-llm-report: Starting LLM annotations for 1 test(s)"
        )
        assert "LLM annotation 1/1" in messages[1]
        assert "tests/test_progress.py::test_case" in messages[1]

    def test_cached_progress_reporting(
        self,
        mock_provider: MagicMock,
        mock_cache: MagicMock,
        mock_assembler: MagicMock,
    ):
        """Should report progress for cached tests."""
        cached_annotation = LlmAnnotation(scenario="cached")
        mock_cache.get.return_value = cached_annotation

        config = Config(provider="ollama")
        test = TestCaseResult(nodeid="test_cached", outcome="passed")
        progress_msgs: list[str] = []

        annotate_tests([test], config, progress=progress_msgs.append)

        assert any("(cache): test_cached" in m for m in progress_msgs)

    def test_batch_optimization_message(
        self,
        mock_provider: MagicMock,
        mock_cache: MagicMock,
        mock_assembler: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Should report optimization message when tests are batched."""
        from pytest_llm_report.llm import batching

        # Create parametrized test to trigger batching
        config = Config(
            provider="ollama", batch_parametrized_tests=True, llm_max_concurrency=1
        )
        tests = [
            TestCaseResult(nodeid="tests/test_foo.py::test_x[a]", outcome="passed"),
            TestCaseResult(nodeid="tests/test_foo.py::test_x[b]", outcome="passed"),
        ]
        progress_msgs: list[str] = []

        # Mock batching to return a BatchedRequest
        mock_batch = batching.BatchedRequest(
            tests=tests,
            base_nodeid="tests/test_foo.py::test_x",
            source_hash="abc123",
        )

        monkeypatch.setattr(
            batching, "group_tests_for_batching", lambda tests, cfg, fn: [mock_batch]
        )
        monkeypatch.setattr(
            batching,
            "build_batch_prompt",
            lambda g, s, c, max_tokens=None: "batched prompt",
        )

        annotate_tests(tests, config, progress=progress_msgs.append)

        assert any("Optimization" in m and "grouped" in m for m in progress_msgs)

    def test_sequential_annotation_error_tracking(
        self,
        mock_provider: MagicMock,
        mock_cache: MagicMock,
        mock_assembler: MagicMock,
    ):
        """Should track first error in sequential annotation."""
        mock_provider.annotate.side_effect = [
            LlmAnnotation(scenario="ok", why_needed="test", key_assertions=[]),
            LlmAnnotation(error="First error"),
            LlmAnnotation(error="Second error"),
        ]

        config = Config(provider="ollama", llm_max_concurrency=1)
        tests = [
            TestCaseResult(nodeid="t1", outcome="passed"),
            TestCaseResult(nodeid="t2", outcome="passed"),
            TestCaseResult(nodeid="t3", outcome="passed"),
        ]

        annotate_tests(tests, config)

        # First test should have annotation
        assert tests[0].llm_annotation is not None
        assert tests[0].llm_annotation.scenario == "ok"
        # Others should have errors
        assert tests[1].llm_annotation is not None
        assert tests[1].llm_annotation.error == "First error"
        assert tests[2].llm_annotation is not None
        assert tests[2].llm_annotation.error == "Second error"
