# SPDX-License-Identifier: MIT
from unittest.mock import MagicMock, patch

from pytest_llm_report.llm.annotator import (
    _annotate_sequential,
    _AnnotationTask,
    annotate_tests,
)
from pytest_llm_report.models import LlmAnnotation, TestCaseResult
from pytest_llm_report.options import Config


class TestAnnotatorAdvanced:
    """Tests for annotator gaps (progress, errors, rate limits)."""

    def test_annotate_tests_provider_unavailable(self, capsys):
        """Should print message and return when provider is not available."""
        config = Config(provider="ollama")
        tests = [TestCaseResult(nodeid="test_foo", outcome="passed")]

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = False

        with patch(
            "pytest_llm_report.llm.annotator.get_provider", return_value=mock_provider
        ):
            annotate_tests(tests, config)

        captured = capsys.readouterr()
        assert "not available. Skipping annotations" in captured.out

    def test_annotate_sequential_rate_limit_wait(self):
        """Should wait if rate limit interval has not elapsed."""
        config = Config(llm_requests_per_minute=60)  # 1 request/sec
        provider = MagicMock()
        provider.is_local.return_value = False
        provider.get_rate_limits.return_value = None
        provider.annotate.return_value = LlmAnnotation(scenario="done")

        cache = MagicMock()
        tasks = [
            _AnnotationTask(
                TestCaseResult(nodeid="t1", outcome="p"), "src", None, "h1"
            ),
            _AnnotationTask(
                TestCaseResult(nodeid="t2", outcome="p"), "src", None, "h2"
            ),
        ]

        with patch("pytest_llm_report.llm.annotator.time.sleep") as mock_sleep:
            with patch("pytest_llm_report.llm.annotator.time.monotonic") as mock_time:
                # Mock time moving slowly
                mock_time.side_effect = [100.0, 100.1, 100.2, 100.3, 100.4]

                _annotate_sequential(tasks, provider, cache, config, None, 2, 0, 0)

                # Should have slept because only 0.1s elapsed but interval is 1.0s
                assert mock_sleep.called

    def test_annotate_concurrent_with_progress_and_errors(self):
        """Should report progress and first error in concurrent mode."""
        from pytest_llm_report.llm.annotator import _annotate_concurrent

        config = Config(llm_max_concurrency=2)
        provider = MagicMock()
        # Mock annotate to return different results
        provider.annotate.side_effect = [
            LlmAnnotation(error="first error"),
            LlmAnnotation(scenario="success"),
        ]

        cache = MagicMock()
        tasks = [
            _AnnotationTask(
                TestCaseResult(nodeid="t1", outcome="p"), "src", None, "h1"
            ),
            _AnnotationTask(
                TestCaseResult(nodeid="t2", outcome="p"), "src", None, "h2"
            ),
        ]

        progress_msgs = []
        annotated, failures, first_error = _annotate_concurrent(
            tasks, provider, cache, config, progress_msgs.append, 2, 0, 0
        )

        assert annotated == 2
        assert failures == 1
        assert "first error" in first_error
        assert any("Processing 2 test(s)" in m for m in progress_msgs)
        assert any("LLM annotation progress" in m for m in progress_msgs)

    def test_annotate_tests_cached_progress(self):
        """Should report progress for cached tests."""
        config = Config(provider="ollama")
        test = TestCaseResult(nodeid="test_cached", outcome="passed")

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True

        mock_cache = MagicMock()
        mock_cache.get.return_value = LlmAnnotation(scenario="cached")

        progress_msgs = []
        with patch(
            "pytest_llm_report.llm.annotator.get_provider", return_value=mock_provider
        ):
            with patch(
                "pytest_llm_report.llm.annotator.LlmCache", return_value=mock_cache
            ):
                with patch(
                    "pytest_llm_report.llm.annotator.ContextAssembler"
                ) as mock_asm_cls:
                    mock_asm = MagicMock()
                    mock_asm.assemble.return_value = ("src", None)
                    mock_asm_cls.return_value = mock_asm

                    annotate_tests([test], config, progress=progress_msgs.append)

        assert any("(cached): test_cached" in m for m in progress_msgs)
