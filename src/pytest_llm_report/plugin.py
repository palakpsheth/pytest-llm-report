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

import pytest

from pytest_llm_report.options import Config


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
        help="Path for HTML report output",
    )
    group.addoption(
        "--llm-report-json",
        dest="llm_report_json",
        default=None,
        help="Path for JSON report output",
    )
    group.addoption(
        "--llm-pdf",
        dest="llm_report_pdf",
        default=None,
        help="Path for PDF report output (requires playwright)",
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

    # Add ini-file options for pyproject.toml [tool.pytest_llm_report]
    parser.addini(
        "llm_report_provider",
        default="none",
        help="LLM provider: none, ollama, or litellm",
    )
    parser.addini(
        "llm_report_model",
        default="",
        help="Model name for LLM provider",
    )
    parser.addini(
        "llm_report_context_mode",
        default="minimal",
        help="LLM context mode: minimal, balanced, or complete",
    )
    parser.addini(
        "llm_report_html",
        default="",
        help="Default path for HTML report output",
    )
    parser.addini(
        "llm_report_json",
        default="",
        help="Default path for JSON report output",
    )


def _load_config_from_pytest(config: pytest.Config) -> Config:
    """Load Config from pytest options and ini file.

    CLI options take precedence over ini file options.

    Args:
        config: pytest configuration object.

    Returns:
        Populated Config instance.
    """
    # Start with defaults
    cfg = Config()

    # Load from ini (pyproject.toml [tool.pytest.ini_options])
    if config.getini("llm_report_provider"):
        cfg.provider = config.getini("llm_report_provider")
    if config.getini("llm_report_model"):
        cfg.model = config.getini("llm_report_model")
    if config.getini("llm_report_context_mode"):
        cfg.llm_context_mode = config.getini("llm_report_context_mode")
    if config.getini("llm_report_html"):
        cfg.report_html = config.getini("llm_report_html")
    if config.getini("llm_report_json"):
        cfg.report_json = config.getini("llm_report_json")

    # Override with CLI options
    if config.option.llm_report_html:
        cfg.report_html = config.option.llm_report_html
    if config.option.llm_report_json:
        cfg.report_json = config.option.llm_report_json
    if config.option.llm_report_pdf:
        cfg.report_pdf = config.option.llm_report_pdf
    if config.option.llm_evidence_bundle:
        cfg.report_evidence_bundle = config.option.llm_evidence_bundle
    if config.option.llm_dependency_snapshot:
        cfg.report_dependency_snapshot = config.option.llm_dependency_snapshot

    # Aggregation options
    if config.option.llm_aggregate_dir:
        cfg.aggregate_dir = config.option.llm_aggregate_dir
    if config.option.llm_aggregate_policy:
        cfg.aggregate_policy = config.option.llm_aggregate_policy
    if config.option.llm_aggregate_run_id:
        cfg.aggregate_run_id = config.option.llm_aggregate_run_id
    if config.option.llm_aggregate_group_id:
        cfg.aggregate_group_id = config.option.llm_aggregate_group_id

    # Set repo root
    cfg.repo_root = config.rootpath

    return cfg


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
    cfg = _load_config_from_pytest(config)

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

    # Store config and enable flag
    config._llm_report_config = cfg
    config._llm_report_enabled = bool(cfg.report_html or cfg.report_json)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Generate the report at session end.

    Args:
        session: pytest session.
        exitstatus: pytest exit status code.
    """
    # Skip report generation on workers (xdist)
    if hasattr(session.config, "workerinput"):
        return

    # Skip if report not enabled
    if not getattr(session.config, "_llm_report_enabled", False):
        return

    # Get config (already validated)
    cfg: Config = session.config._llm_report_config

    # Get collector if it was set up
    collector = getattr(session.config, "_llm_report_collector", None)
    if collector is None:
        # Collector wasn't set up, create one with empty results
        from pytest_llm_report.collector import TestCollector
        collector = TestCollector(cfg)

    # Get results
    tests = collector.get_results()
    collection_errors = collector.get_collection_errors()

    # Get start/end times from session
    from datetime import datetime, timezone
    start_time = getattr(session, "_llm_report_start_time", None) or datetime.now(timezone.utc)
    end_time = datetime.now(timezone.utc)

    # Write report
    from pytest_llm_report.report_writer import ReportWriter
    writer = ReportWriter(cfg)
    writer.write_report(
        tests=tests,
        collection_errors=collection_errors,
        exit_code=exitstatus,
        start_time=start_time,
        end_time=end_time,
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """Wrapper around test report creation to capture config.

    Args:
        item: Test item.
        call: Call info.
    """
    outcome = yield
    report = outcome.get_result()

    # Skip if not enabled
    if not getattr(item.config, "_llm_report_enabled", False):
        return

    # Get collector
    collector = getattr(item.config, "_llm_report_collector", None)
    if collector:
        collector.handle_runtest_logreport(report, item)


def pytest_collection_finish(session: pytest.Session) -> None:
    """Handle collection finish.

    Args:
        session: pytest session.
    """
    # Skip if not enabled
    if not getattr(session.config, "_llm_report_enabled", False):
        return

    # Get collector
    collector = getattr(session.config, "_llm_report_collector", None)
    if collector:
        collector.handle_collection_finish(session.items)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Initialize collector at session start.

    Args:
        session: pytest session.
    """
    # Skip if not enabled
    if not getattr(session.config, "_llm_report_enabled", False):
        return

    # Record start time
    from datetime import datetime, timezone
    session._llm_report_start_time = datetime.now(timezone.utc)

    # Create collector
    from pytest_llm_report.collector import TestCollector
    cfg: Config = session.config._llm_report_config
    session.config._llm_report_collector = TestCollector(cfg)
