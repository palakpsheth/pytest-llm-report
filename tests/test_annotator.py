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
