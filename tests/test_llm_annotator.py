# SPDX-License-Identifier: MIT
"""Tests for LLM annotation orchestration."""

from __future__ import annotations

from pytest_llm_report.llm.annotator import annotate_tests
from pytest_llm_report.models import LlmAnnotation, TestCaseResult
from pytest_llm_report.options import Config


class FakeProvider:
    """Fake LLM provider for testing."""

    def __init__(self, annotation: LlmAnnotation) -> None:
        self.annotation = annotation
        self.calls: list[str] = []

    def annotate(self, test, *_args, **_kwargs):  # noqa: ANN001 - test helper
        self.calls.append(test.nodeid)
        return self.annotation


def test_annotate_tests_uses_cache(monkeypatch, tmp_path):
    """Annotations should be cached between runs."""
    config = Config(provider="litellm", cache_dir=str(tmp_path))
    test = TestCaseResult(nodeid="tests/test_sample.py::test_case", outcome="passed")
    provider = FakeProvider(LlmAnnotation(scenario="cached"))

    monkeypatch.setattr(
        "pytest_llm_report.llm.annotator.get_provider", lambda _cfg: provider
    )

    annotate_tests([test], config)
    assert provider.calls == ["tests/test_sample.py::test_case"]
    assert test.llm_annotation is not None

    provider_next = FakeProvider(LlmAnnotation(scenario="should-not-call"))

    def _raise_if_called(*_args, **_kwargs):  # noqa: ANN001 - test helper
        raise AssertionError("provider should not be called when cached")

    provider_next.annotate = _raise_if_called
    monkeypatch.setattr(
        "pytest_llm_report.llm.annotator.get_provider", lambda _cfg: provider_next
    )

    test.llm_annotation = None
    annotate_tests([test], config)
    assert test.llm_annotation is not None
    assert test.llm_annotation.scenario == "cached"


def test_annotate_tests_respects_opt_out_and_limit(monkeypatch, tmp_path):
    """LLM annotations should skip opt-out tests and respect max tests."""
    config = Config(provider="litellm", cache_dir=str(tmp_path), llm_max_tests=1)
    tests = [
        TestCaseResult(nodeid="tests/test_a.py::test_a", outcome="passed"),
        TestCaseResult(
            nodeid="tests/test_b.py::test_b", outcome="passed", llm_opt_out=True
        ),
        TestCaseResult(nodeid="tests/test_c.py::test_c", outcome="passed"),
    ]
    provider = FakeProvider(LlmAnnotation(scenario="ok"))

    monkeypatch.setattr(
        "pytest_llm_report.llm.annotator.get_provider", lambda _cfg: provider
    )

    annotate_tests(tests, config)

    assert provider.calls == ["tests/test_a.py::test_a"]
    assert tests[0].llm_annotation is not None
    assert tests[1].llm_annotation is None
    assert tests[2].llm_annotation is None
