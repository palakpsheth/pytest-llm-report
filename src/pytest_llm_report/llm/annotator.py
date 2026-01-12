# SPDX-License-Identifier: MIT
"""LLM annotation orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from pytest_llm_report.cache import LlmCache, hash_source
from pytest_llm_report.llm.base import get_provider
from pytest_llm_report.models import TestCaseResult
from pytest_llm_report.prompts import ContextAssembler

if TYPE_CHECKING:
    from pytest_llm_report.options import Config


def annotate_tests(tests: Iterable[TestCaseResult], config: Config) -> None:
    """Annotate test cases in-place when LLM is enabled.

    Args:
        tests: Test cases to annotate.
        config: Plugin configuration.
    """
    if not config.is_llm_enabled():
        return

    provider = get_provider(config)
    cache = LlmCache(config)
    assembler = ContextAssembler(config)

    annotated = 0
    failures = 0
    for test in tests:
        if annotated >= config.llm_max_tests:
            break
        if test.llm_opt_out:
            continue

        test_source, context_files = assembler.assemble(test, config.repo_root)
        source_hash = hash_source(test_source)
        cached = cache.get(test.nodeid, source_hash)
        if cached:
            test.llm_annotation = cached
            annotated += 1
            continue

        annotation = provider.annotate(test, test_source, context_files)
        test.llm_annotation = annotation
        cache.set(test.nodeid, source_hash, annotation)
        annotated += 1
        if annotation.error:
            failures += 1

    if annotated:
        provider_name = config.provider
        print(
            "pytest-llm-report: Annotated "
            f"{annotated} test(s) via {provider_name} "
            f"({failures} error(s))."
        )
