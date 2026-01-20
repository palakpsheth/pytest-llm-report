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
    batch_tests: list[TestCaseResult] | None = None
    prompt_override: str | None = None


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
    from pytest_llm_report.llm.batching import (
        BatchedRequest,
        build_batch_prompt,
        group_tests_for_batching,
    )

    eligible_tests = [test for test in tests if not test.llm_opt_out]
    # 0 means no limit - annotate all eligible tests
    if config.llm_max_tests > 0:
        limited_tests = eligible_tests[: config.llm_max_tests]
    else:
        limited_tests = eligible_tests

    # Create map for fast lookups
    node_map = {t.nodeid: t for t in limited_tests}
    assembler = ContextAssembler(config)

    def get_source_helper(nodeid: str) -> str:
        test_obj = node_map.get(nodeid)
        if test_obj:
            src, _ = assembler.assemble(test_obj, config.repo_root)
            return src
        return ""

    # Group tests for batching
    test_groups = group_tests_for_batching(limited_tests, config, get_source_helper)

    total = len(limited_tests)
    if total and progress:
        progress(f"pytest-llm-report: Starting LLM annotations for {total} test(s)")
        if len(test_groups) < len(limited_tests):
            progress(
                f"pytest-llm-report: Optimization - grouped into {len(test_groups)} LLM requests"
            )

    # Separate cached and uncached tasks
    uncached_tasks: list[_AnnotationTask] = []
    completed = 0

    for group in test_groups:
        if isinstance(group, BatchedRequest):
            # 1. Check if we need to run this batch
            # Ideally we check cache for each test. If any are missing, we run the batch.
            # (Optimization: We could re-batch only missing ones, but keeping it simple for now:
            # if any missing, run batch for all and update cache for all)

            # Use first test to get template source
            first_test = group.tests[0]
            template_source, context_files = assembler.assemble(
                first_test, config.repo_root
            )

            # Check cache
            needs_run = False
            for t in group.tests:
                # We use the template source hash for cache key of individual tests
                # to allow cache hits even if they were run individually before
                sh = hash_source(template_source)
                # Note: Technically parametrized variants might have slightly different source
                # if we included parameter values in source hash?
                # Currently hash_source uses the source code string.
                # Parametrized tests
                cached = cache.get(t.nodeid, sh)
                if cached:
                    t.llm_annotation = cached
                    if progress:
                        completed_for_msg = completed + 1
                        progress(
                            f"pytest-llm-report: LLM annotation {completed_for_msg}/{total} "
                            f"(cache): {t.nodeid}"
                        )
                    completed += 1
                else:
                    needs_run = True

            if needs_run:
                # Construct batch prompt
                # usage of context_files from first test is approximation but usually correct for parametrized
                batch_prompt = build_batch_prompt(
                    group,
                    template_source,
                    context_files,
                    max_tokens=provider.get_max_context_tokens(),
                )

                uncached_tasks.append(
                    _AnnotationTask(
                        test=first_test,  # Anchor test
                        test_source=template_source,
                        context_files=context_files,
                        source_hash=hash_source(template_source),
                        batch_tests=group.tests,
                        prompt_override=batch_prompt,
                    )
                )
            else:
                # All cached
                pass  # completed count is handled inside the loop now

        else:
            # Single Test Case
            test = group
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
    first_error: str | None = None
    failures = 0

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
        annotation = provider.annotate(
            task.test,
            task.test_source,
            task.context_files,
            prompt_override=task.prompt_override,
        )

        if task.batch_tests:
            for t in task.batch_tests:
                t.llm_annotation = annotation
                # Assuming all tests in batch share same source (template)
                cache.set(t.nodeid, task.source_hash, annotation)

            newly_annotated += len(task.batch_tests)
            completed += len(task.batch_tests) - 1  # +1 is done below
        else:
            task.test.llm_annotation = annotation
            cache.set(task.test.nodeid, task.source_hash, annotation)

        newly_annotated += 1 if not task.batch_tests else 0  # Managed above
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
        annotation = provider.annotate(
            task.test,
            task.test_source,
            task.context_files,
            prompt_override=task.prompt_override,
        )
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

            if task.batch_tests:
                for t in task.batch_tests:
                    t.llm_annotation = annotation
                    cache.set(t.nodeid, task.source_hash, annotation)

                newly_annotated += len(task.batch_tests)
                completed += len(task.batch_tests) - 1  # +1 is done below
            else:
                task.test.llm_annotation = annotation
                cache.set(task.test.nodeid, task.source_hash, annotation)

            newly_annotated += 1 if not task.batch_tests else 0  # Managed above
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
