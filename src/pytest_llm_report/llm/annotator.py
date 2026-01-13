# SPDX-License-Identifier: MIT
"""LLM annotation orchestration."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pytest_llm_report.cache import LlmCache, hash_source
from pytest_llm_report.llm.base import LlmProvider, get_provider
from pytest_llm_report.models import LlmAnnotation, TestCaseResult
from pytest_llm_report.prompts import ContextAssembler

if TYPE_CHECKING:
    from pytest_llm_report.options import Config


@dataclass
class _AnnotationTask:
    """Internal task for concurrent annotation."""

    test: TestCaseResult
    test_source: str
    context_files: dict[str, str] | None
    source_hash: str


def annotate_tests(
    tests: Iterable[TestCaseResult],
    config: Config,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Annotate test cases in-place when LLM is enabled.

    Supports concurrent processing when config.llm_max_concurrency > 1.

    Args:
        tests: Test cases to annotate.
        config: Plugin configuration.
        progress: Optional callback for progress reporting.
    """
    if not config.is_llm_enabled():
        return

    provider = get_provider(config)
    if not provider.is_available():
        print(
            "pytest-llm-report: LLM provider "
            f"'{config.provider}' is not available. Skipping annotations."
        )
        return

    cache = LlmCache(config)
    assembler = ContextAssembler(config)

    eligible_tests = [test for test in tests if not test.llm_opt_out]
    # 0 means no limit - annotate all eligible tests
    if config.llm_max_tests > 0:
        limited_tests = eligible_tests[: config.llm_max_tests]
    else:
        limited_tests = eligible_tests

    total = len(limited_tests)
    if total and progress:
        progress(f"pytest-llm-report: Starting LLM annotations for {total} test(s)")

    # Separate cached and uncached tests
    uncached_tasks: list[_AnnotationTask] = []
    completed = 0

    for test in limited_tests:
        test_source, context_files = assembler.assemble(test, config.repo_root)
        source_hash = hash_source(test_source)
        cached = cache.get(test.nodeid, source_hash)
        if cached:
            test.llm_annotation = cached
            completed += 1
            if progress:
                progress(
                    f"pytest-llm-report: LLM annotation {completed}/{total} "
                    f"(cache): {test.nodeid}"
                )
        else:
            uncached_tasks.append(
                _AnnotationTask(
                    test=test,
                    test_source=test_source,
                    context_files=context_files,
                    source_hash=source_hash,
                )
            )

    # Process uncached tests
    failures = 0
    first_error: str | None = None

    if uncached_tasks:
        # Use concurrent processing for local providers or when concurrency > 1
        use_concurrent = provider.is_local() and config.llm_max_concurrency > 1

        if use_concurrent:
            annotated_count, failures, first_error = _annotate_concurrent(
                uncached_tasks,
                provider,
                cache,
                config,
                progress,
                total,
                completed,
            )
        else:
            annotated_count, failures, first_error = _annotate_sequential(
                uncached_tasks,
                provider,
                cache,
                config,
                progress,
                total,
                completed,
            )
        # Sum up for final summary
        # we don't really need 'annotated' variable as we count failures separately
    else:
        annotated_count = 0

    total_annotated = completed + annotated_count
    if total_annotated:
        provider_name = config.provider
        message = (
            "pytest-llm-report: Annotated "
            f"{total_annotated} test(s) via {provider_name} "
            f"({completed} from cache, {annotated_count} new, {failures} error(s))."
        )
        if first_error:
            message = f"{message} First error: {first_error}"
        print(message)


def _annotate_sequential(
    tasks: list[_AnnotationTask],
    provider: LlmProvider,
    cache: LlmCache,
    config: Config,
    progress: Callable[[str], None] | None,
    total: int,
    completed: int,
) -> tuple[int, int, str | None]:
    """Process annotations sequentially with rate limiting.

    Args:
        tasks: List of annotation tasks.
        provider: LLM provider instance.
        cache: LLM cache instance.
        config: Plugin configuration.
        progress: Optional progress callback.
        total: Total number of tests.
        completed: Number of tests already completed (cached).

    Returns:
        Tuple of (newly_annotated_count, failure_count, first_error).
    """
    failures = 0
    first_error: str | None = None
    last_request_time: float | None = None
    newly_annotated = 0

    rate_limits = provider.get_rate_limits()
    requests_per_minute = (
        rate_limits.requests_per_minute
        if rate_limits and rate_limits.requests_per_minute
        else config.llm_requests_per_minute
    )
    request_interval = 60.0 / requests_per_minute

    for task in tasks:
        # Skip rate limiting for local providers
        if not provider.is_local() and last_request_time is not None:
            elapsed = time.monotonic() - last_request_time
            if elapsed < request_interval:
                time.sleep(request_interval - elapsed)

        last_request_time = time.monotonic()
        annotation = provider.annotate(task.test, task.test_source, task.context_files)
        task.test.llm_annotation = annotation
        cache.set(task.test.nodeid, task.source_hash, annotation)
        newly_annotated += 1
        completed += 1

        if progress:
            progress(
                f"pytest-llm-report: LLM annotation {completed}/{total} "
                f"({config.provider}): {task.test.nodeid}"
            )

        if annotation.error:
            failures += 1
            if first_error is None:
                first_error = annotation.error

    return newly_annotated, failures, first_error


def _annotate_concurrent(
    tasks: list[_AnnotationTask],
    provider: LlmProvider,
    cache: LlmCache,
    config: Config,
    progress: Callable[[str], None] | None,
    total: int,
    completed: int,
) -> tuple[int, int, str | None]:
    """Process annotations concurrently using ThreadPoolExecutor.

    Args:
        tasks: List of annotation tasks.
        provider: LLM provider instance.
        cache: LLM cache instance.
        config: Plugin configuration.
        progress: Optional progress callback.
        total: Total number of tests.
        completed: Number of tests already completed (cached).

    Returns:
        Tuple of (newly_annotated_count, failure_count, first_error).
    """
    failures = 0
    first_error: str | None = None
    max_workers = config.llm_max_concurrency
    newly_annotated = 0

    def _process_task(task: _AnnotationTask) -> tuple[_AnnotationTask, LlmAnnotation]:
        """Process a single annotation task."""
        annotation = provider.annotate(task.test, task.test_source, task.context_files)
        return task, annotation

    if progress:
        progress(
            f"pytest-llm-report: Processing {len(tasks)} test(s) "
            f"with {max_workers} concurrent workers"
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_task, task): task for task in tasks}

        for future in as_completed(futures):
            task, annotation = future.result()
            task.test.llm_annotation = annotation
            cache.set(task.test.nodeid, task.source_hash, annotation)
            newly_annotated += 1
            completed += 1

            if progress:
                progress(
                    f"pytest-llm-report: LLM annotation {completed}/{total} "
                    f"({config.provider}): {task.test.nodeid}"
                )

            if annotation.error:
                failures += 1
                if first_error is None:
                    first_error = annotation.error

    return newly_annotated, failures, first_error
