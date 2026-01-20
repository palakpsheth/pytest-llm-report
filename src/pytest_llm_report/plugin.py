# SPDX-License-Identifier: MIT
"""Pytest plugin entry point for pytest-llm-report.

This module is registered via the pytest11 entry point and provides
the hooks for integrating with pytest.

Component Contract:
    Input: pytest hooks and configuration
    Output: Report generation at session end
    Dependencies: options, collector, coverage_map, render, report_writer
"""

from __future__ import annotations

import warnings
from collections.abc import Generator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from pytest import StashKey

from pytest_llm_report.options import Config

if TYPE_CHECKING:
    from pytest_llm_report.collector import TestCollector

# Stash keys for storing plugin state (official pytest API)
_config_key: StashKey[Config] = StashKey()
_enabled_key: StashKey[bool] = StashKey()
_collector_key: StashKey[TestCollector] = StashKey()
_start_time_key: StashKey[datetime] = StashKey()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options for pytest-llm-report.

    Args:
        parser: pytest argument parser.
    """
    group = parser.getgroup("llm-report", "LLM-enhanced test reports")

    # Output paths
    group.addoption(
        "--llm-report",
        dest="llm_report_html",
        default=None,
        help="Path for HTML report output. Example: --llm-report=reports/tests.html",
    )
    group.addoption(
        "--llm-report-json",
        dest="llm_report_json",
        default=None,
        help="Path for JSON report output. Example: --llm-report-json=reports/tests.json",
    )
    group.addoption(
        "--llm-pdf",
        dest="llm_report_pdf",
        default=None,
        help="Path for PDF report (requires playwright). Example: --llm-pdf=reports/tests.pdf",
    )
    group.addoption(
        "--llm-evidence-bundle",
        dest="llm_evidence_bundle",
        default=None,
        help="Path for evidence bundle zip output",
    )
    group.addoption(
        "--llm-dependency-snapshot",
        dest="llm_dependency_snapshot",
        default=None,
        help="Path for dependency snapshot output",
    )
    group.addoption(
        "--llm-requests-per-minute",
        dest="llm_requests_per_minute",
        type=int,
        default=None,
        help="Maximum LLM requests per minute (default: 5)",
    )
    group.addoption(
        "--llm-max-retries",
        dest="llm_max_retries",
        type=int,
        default=None,
        help="Maximum LLM retries for transient errors (default: 10)",
    )

    # Aggregation options
    group.addoption(
        "--llm-aggregate-dir",
        dest="llm_aggregate_dir",
        default=None,
        help="Directory containing reports to aggregate",
    )
    group.addoption(
        "--llm-aggregate-policy",
        dest="llm_aggregate_policy",
        default=None,
        help="Aggregation policy: latest, merge, or all",
    )
    group.addoption(
        "--llm-aggregate-run-id",
        dest="llm_aggregate_run_id",
        default=None,
        help="Unique run ID for this test run",
    )
    group.addoption(
        "--llm-aggregate-group-id",
        dest="llm_aggregate_group_id",
        default=None,
        help="Group ID for related runs",
    )
    group.addoption(
        "--llm-coverage-source",
        dest="llm_coverage_source",
        default=None,
        help="Path to .coverage file or directory for aggregation enhancement",
    )

    # Core LLM configuration (CLI overrides)
    group.addoption(
        "--llm-provider",
        dest="llm_provider",
        default=None,
        help="LLM provider name (e.g. ollama, litellm)",
    )
    group.addoption(
        "--llm-model",
        dest="llm_model",
        default=None,
        help="LLM model name",
    )
    group.addoption(
        "--llm-context-mode",
        dest="llm_context_mode",
        default=None,
        help="LLM context mode (minimal, balanced, complete)",
    )

    # Token optimization options
    group.addoption(
        "--llm-prompt-tier",
        dest="llm_prompt_tier",
        default=None,
        help="Prompt tier for system prompts (minimal, standard, auto). Default: auto",
    )
    group.addoption(
        "--llm-batch-parametrized",
        dest="llm_batch_parametrized",
        action="store_true",
        default=None,
        help="Group parametrized tests for single LLM annotation (default: enabled)",
    )
    group.addoption(
        "--llm-no-batch-parametrized",
        dest="llm_batch_parametrized",
        action="store_false",
        help="Disable batching of parametrized tests",
    )
    group.addoption(
        "--llm-context-compression",
        dest="llm_context_compression",
        default=None,
        help="Context compression mode (none, lines). Default: lines",
    )

    # Context controls
    group.addoption(
        "--llm-context-bytes",
        dest="llm_context_bytes",
        type=int,
        default=None,
        help="Maximum bytes for context window (default: 32000)",
    )
    group.addoption(
        "--llm-context-file-limit",
        dest="llm_context_file_limit",
        type=int,
        default=None,
        help="Maximum number of files in context (default: 10)",
    )

    # Execution controls
    group.addoption(
        "--llm-max-tests",
        dest="llm_max_tests",
        type=int,
        default=None,
        help="Maximum tests to annotate, 0=unlimited (default: 0)",
    )
    group.addoption(
        "--llm-max-concurrency",
        dest="llm_max_concurrency",
        type=int,
        default=None,
        help="Maximum concurrent LLM requests (default: 1)",
    )
    group.addoption(
        "--llm-timeout-seconds",
        dest="llm_timeout_seconds",
        type=int,
        default=None,
        help="Timeout for LLM requests in seconds (default: 30)",
    )

    # Behavior controls
    group.addoption(
        "--llm-capture-failed",
        dest="llm_capture_failed",
        action="store_true",
        default=None,
        help="Capture stdout/stderr for failed tests (default: enabled)",
    )
    group.addoption(
        "--llm-no-capture-failed",
        dest="llm_capture_failed",
        action="store_false",
        help="Disable capturing failed test output",
    )

    # Provider-specific options
    group.addoption(
        "--llm-ollama-host",
        dest="llm_ollama_host",
        default=None,
        help="Ollama server URL (default: http://127.0.0.1:11434)",
    )
    group.addoption(
        "--llm-litellm-api-base",
        dest="llm_litellm_api_base",
        default=None,
        help="LiteLLM API base URL for proxy",
    )
    group.addoption(
        "--llm-litellm-api-key",
        dest="llm_litellm_api_key",
        default=None,
        help="LiteLLM API key override",
    )
    group.addoption(
        "--llm-litellm-token-refresh-command",
        dest="llm_litellm_token_refresh_command",
        default=None,
        help="Command to fetch fresh auth token",
    )
    group.addoption(
        "--llm-litellm-token-refresh-interval",
        dest="llm_litellm_token_refresh_interval",
        type=int,
        default=None,
        help="Token refresh interval in seconds (default: 3300)",
    )
    group.addoption(
        "--llm-litellm-token-output-format",
        dest="llm_litellm_token_output_format",
        default=None,
        help="Token command output format: text or json (default: text)",
    )
    group.addoption(
        "--llm-litellm-token-json-key",
        dest="llm_litellm_token_json_key",
        default=None,
        help="JSON key for token extraction (default: token)",
    )

    # Maintenance options
    group.addoption(
        "--llm-cache-dir",
        dest="llm_cache_dir",
        default=None,
        help="Directory for LLM cache (default: .pytest_llm_cache)",
    )
    group.addoption(
        "--llm-cache-ttl",
        dest="llm_cache_ttl",
        type=int,
        default=None,
        help="Cache TTL in seconds (default: 86400)",
    )

    # Metadata options
    group.addoption(
        "--llm-metadata-file",
        dest="llm_metadata_file",
        default=None,
        help="Path to custom metadata JSON/YAML file",
    )
    group.addoption(
        "--llm-hmac-key-file",
        dest="llm_hmac_key_file",
        default=None,
        help="Path to HMAC key file for signatures",
    )

    # Content optimization options
    group.addoption(
        "--llm-include-params",
        dest="llm_include_params",
        action="store_true",
        default=None,
        help="Include test parameter values in context",
    )
    group.addoption(
        "--llm-strip-docstrings",
        dest="llm_strip_docstrings",
        action="store_true",
        default=None,
        help="Strip docstrings from context (default: enabled)",
    )
    group.addoption(
        "--llm-no-strip-docstrings",
        dest="llm_strip_docstrings",
        action="store_false",
        help="Disable docstring stripping",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure the plugin.

    This hook runs early in pytest startup.

    Args:
        config: pytest configuration object.
    """
    # Register markers to avoid warnings
    config.addinivalue_line(
        "markers",
        "llm_opt_out: Opt out of LLM annotation for this test",
    )
    config.addinivalue_line(
        "markers",
        "llm_context(mode): Override LLM context mode (minimal, balanced, complete)",
    )
    config.addinivalue_line(
        "markers",
        "requirement(*ids): Associate test with requirement IDs",
    )

    # Check if we're a worker on xdist - if so, don't set up report generation
    if hasattr(config, "workerinput"):
        return

    # Load configuration
    cfg = Config.load(config) if hasattr(Config, "load") else None
    if not cfg:
        # Fallback if I messed up the import in my thought process, but better to import explicitly
        from pytest_llm_report.options import load_config

        cfg = load_config(config)

    # Validate configuration
    errors = cfg.validate()
    if errors:
        raise pytest.UsageError(
            "pytest-llm-report configuration errors:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    # Warn when LLM is enabled
    if cfg.is_llm_enabled():
        warnings.warn(
            f"pytest-llm-report: LLM provider '{cfg.provider}' is enabled. "
            "Test code will be sent to the configured provider.",
            UserWarning,
            stacklevel=1,
        )

    # Store config and enable flag using stash (official pytest API)
    config.stash[_config_key] = cfg
    config.stash[_enabled_key] = bool(
        cfg.report_html or cfg.report_json or cfg.report_pdf
    )


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, exitstatus: int, config: pytest.Config
) -> None:
    """Generate the report at end of session using pytest's terminal summary hook.

    This function previously used the ``pytest_sessionfinish`` hook, but was moved
    to ``pytest_terminal_summary`` because:

    * ``pytest_terminal_summary`` runs after the built-in terminal reporting is
      complete and has direct access to the ``terminalreporter`` instance, which
      is the natural integration point for session-level reporting.
    * It avoids ordering and interaction issues that can occur with
      ``pytest_sessionfinish`` when other plugins also use that hook or modify
      session state during teardown.
    * It provides a more stable point in the lifecycle for generating the final
      LLM report once all tests have been collected, executed, and reported.
    Args:
        terminalreporter: pytest terminal reporter.
        exitstatus: pytest exit status code.
        config: pytest configuration.
    """
    # Skip report generation on workers (xdist)
    if hasattr(config, "workerinput"):
        return

    # Skip if report not enabled
    if not config.stash.get(_enabled_key, False):
        return

    # Get config (already validated)
    cfg: Config = config.stash[_config_key]

    # Handle aggregation if configured
    if cfg.aggregate_dir:
        from pytest_llm_report.aggregation import Aggregator

        aggregator = Aggregator(cfg)
        report = aggregator.aggregate()

        # If aggregation was successful, write it and return
        if report:
            from pytest_llm_report.report_writer import ReportWriter

            writer = ReportWriter(cfg)

            if cfg.report_json:
                writer.write_json(report, cfg.report_json)
            if cfg.report_html:
                writer.write_html(report, cfg.report_html)
            return

    # Get collector if it was set up
    collector = config.stash.get(_collector_key, None)
    if collector is None:
        # Collector wasn't set up, create one with empty results
        from pytest_llm_report.collector import TestCollector

        collector = TestCollector(cfg)

    # Get results
    tests = collector.get_results()
    collection_errors = collector.get_collection_errors()

    # Get start/end times from config (stored early) or use now
    start_time = config.stash.get(_start_time_key, None) or datetime.now(UTC)
    end_time = datetime.now(UTC)

    from pytest_llm_report.coverage_map import CoverageMapper
    from pytest_llm_report.report_writer import ReportWriter

    # Collect coverage data if available
    coverage = None
    coverage_percent = None
    source_coverage = []
    try:
        mapper = CoverageMapper(cfg)
        # Load from disk (pytest-cov should have saved it by now)
        coverage = mapper.map_coverage()

        # Calculate total coverage percentage
        try:
            from pathlib import Path

            from coverage import Coverage

            # Use the .coverage file in cwd (or repo root)
            cov_file = Path.cwd() / ".coverage"
            if cov_file.exists():
                cov = Coverage(data_file=str(cov_file))
                cov.load()

                import io

                out = io.StringIO()
                coverage_pct = cov.report(file=out)
                coverage_percent = round(coverage_pct, 2)
                source_coverage = mapper.map_source_coverage(cov)
                # Note: coverage_percent is from cov.report() above for consistency
                # with coverage command line. source_coverage is for display only.
        except (ImportError, OSError, ValueError) as e:
            warnings.warn(
                f"Failed to compute coverage percentage from .coverage file: {e}",
                stacklevel=2,
            )
    except Exception as e:
        warnings.warn(f"Failed to map coverage: {e}", stacklevel=2)

    # Attach coverage to tests for downstream processing
    if coverage:
        for test in tests:
            if test.nodeid in coverage:
                test.coverage = coverage[test.nodeid]

    # Apply LLM annotations
    llm_info = None
    if cfg.is_llm_enabled():
        from pytest_llm_report.llm.annotator import annotate_tests
        from pytest_llm_report.llm.base import get_provider

        # Get provider to capture model info
        provider = get_provider(cfg)

        annotate_tests(tests, cfg, progress=terminalreporter.write_line)

        # Count annotations and errors
        annotations_count = 0
        annotations_errors = 0
        for test in tests:
            if test.llm_annotation:
                if test.llm_annotation.error:
                    annotations_errors += 1
                else:
                    annotations_count += 1

        # Calculate token usage totals
        total_input = 0
        total_output = 0
        total_combined = 0

        for test in tests:
            if test.llm_annotation and test.llm_annotation.token_usage:
                usage = test.llm_annotation.token_usage
                total_input += usage.prompt_tokens
                total_output += usage.completion_tokens
                total_combined += usage.total_tokens

        llm_info = {
            "provider": cfg.provider,
            "model": provider.get_model_name(),
            "context_mode": cfg.llm_context_mode,
            "annotations_count": annotations_count,
            "annotations_errors": annotations_errors,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_combined,
        }

    writer = ReportWriter(cfg)
    writer.write_report(
        tests=tests,
        coverage=coverage,
        coverage_percent=coverage_percent,
        source_coverage=source_coverage,
        collection_errors=collection_errors,
        exit_code=exitstatus,
        start_time=start_time,
        end_time=end_time,
        llm_info=llm_info,
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo
) -> Generator[None, Any, None]:
    """Wrapper around test report creation to capture config.

    Args:
        item: Test item.
        call: Call info.
    """
    outcome = yield
    report = outcome.get_result()

    # Skip if not enabled
    if not item.config.stash.get(_enabled_key, False):
        return

    # Get collector
    collector = item.config.stash.get(_collector_key, None)
    if collector:
        collector.handle_runtest_logreport(report, item)


def pytest_collectreport(report: pytest.CollectReport) -> None:
    """Handle collection reports to capture collection errors.

    Args:
        report: pytest collection report.
    """
    # Get config from report - need to access via fspath or session
    # This hook is called per-node, so we access stash via the session
    if hasattr(report, "session") and report.session is not None:
        config = report.session.config
    else:
        # Fallback: can't access config, skip
        return

    # Skip if not enabled
    if not config.stash.get(_enabled_key, False):
        return

    # Get collector
    collector = config.stash.get(_collector_key, None)
    if collector:
        collector.handle_collection_report(report)


def pytest_collection_finish(session: pytest.Session) -> None:
    """Handle collection finish.

    Args:
        session: pytest session.
    """
    # Skip if not enabled
    if not session.config.stash.get(_enabled_key, False):
        return

    # Get collector
    collector = session.config.stash.get(_collector_key, None)
    if collector:
        collector.handle_collection_finish(session.items)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Initialize collector at session start.

    Args:
        session: pytest session.
    """
    # Skip if not enabled
    if not session.config.stash.get(_enabled_key, False):
        return

    # Record start time
    session.config.stash[_start_time_key] = datetime.now(UTC)

    # Create collector
    from pytest_llm_report.collector import TestCollector

    cfg: Config = session.config.stash[_config_key]
    session.config.stash[_collector_key] = TestCollector(cfg)
