# SPDX-License-Identifier: MIT
"""Configuration and CLI options for pytest-llm-report.

This module defines the Config dataclass and handles loading configuration
from CLI arguments and pyproject.toml.

Component Contract:
    Input: CLI args (via pytest_addoption), pyproject.toml [tool.pytest_llm_report]
    Output: Config dataclass with validated options
    Dependencies: None (pure configuration)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


@dataclass
class Config:
    """Configuration for pytest-llm-report.

    All components should accept this Config rather than reading global state.
    Defaults are safe and privacy-preserving (provider=none, minimal context).

    Attributes:
        # Output paths
        report_html: Path for HTML report output.
        report_json: Path for JSON report output.
        report_pdf: Optional path for PDF report output.
        report_evidence_bundle: Optional path for evidence bundle zip.
        report_dependency_snapshot: Optional path for dependency snapshot.

        # LLM provider settings
        provider: LLM provider name ("none", "ollama", "litellm", "gemini").
        model: Model name for LLM provider.
        ollama_host: Ollama server URL.

        # LLM context controls
        llm_context_mode: Context mode ("minimal", "balanced", "complete").
        llm_context_bytes: Maximum bytes for LLM context.
        llm_context_file_limit: Maximum files to include in context.
        llm_context_include_globs: Globs for files to include.
        llm_context_exclude_globs: Globs for files to exclude.

        # LLM parameter handling
        llm_include_param_values: Whether to include raw parameter values.
        llm_param_value_max_chars: Max chars for parameter values.

        # LLM execution controls
        llm_max_tests: Maximum tests to annotate.
        llm_max_concurrency: Maximum concurrent LLM requests.
        llm_requests_per_minute: Maximum LLM requests per minute.
        llm_timeout_seconds: Timeout for LLM requests.
        llm_max_retries: Maximum retries for LLM requests.
        llm_cache_ttl_seconds: Cache TTL in seconds.
        cache_dir: Directory for LLM cache.

        # Coverage settings
        omit_tests_from_coverage: Whether to omit test files from coverage.
        include_phase: Which phase to include (run, setup, teardown).

        # Report behavior
        report_collect_only: Generate report for collect-only runs.
        capture_failed_output: Capture stdout/stderr for failed tests.
        capture_output_max_chars: Max chars for captured output.

        # Invocation summary
        include_pytest_invocation: Include sanitized pytest invocation.
        invocation_redact_patterns: Patterns to redact from invocation.

        # Aggregation
        aggregate_dir: Directory containing reports to aggregate.
        aggregate_policy: Aggregation policy (latest, merge, all).
        aggregate_run_id: Run ID for this run.
        aggregate_group_id: Group ID for related runs.
        aggregate_include_history: Include prior runs in output.

        # Compliance
        metadata_file: Path to custom metadata JSON/YAML file.
        hmac_key_file: Path to HMAC key file for signatures.

        # Internal
        repo_root: Repository root path for relative paths.
    """

    # Output paths
    report_html: str | None = None
    report_json: str | None = None
    report_pdf: str | None = None
    report_evidence_bundle: str | None = None
    report_dependency_snapshot: str | None = None

    # LLM provider settings
    provider: str = "none"
    model: str = ""
    ollama_host: str = "http://127.0.0.1:11434"

    # LLM context controls
    llm_context_mode: str = "minimal"
    llm_context_bytes: int = 32000
    llm_context_file_limit: int = 10
    llm_context_include_globs: list[str] = field(default_factory=list)
    llm_context_exclude_globs: list[str] = field(
        default_factory=lambda: [
            "*.pyc",
            "__pycache__/*",
            ".git/*",
            ".env",
            ".env.*",
            "*.key",
            "*.pem",
            "*secret*",
            "*password*",
            "*credential*",
        ]
    )

    # LLM parameter handling
    llm_include_param_values: bool = False
    llm_param_value_max_chars: int = 100

    # LLM execution controls
    llm_max_tests: int = 0  # 0 = no limit (annotate all tests)
    llm_max_concurrency: int = 1
    llm_requests_per_minute: int = 5
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 10
    llm_cache_ttl_seconds: int = 86400  # 24 hours
    cache_dir: str = ".pytest_llm_cache"

    # Coverage settings
    omit_tests_from_coverage: bool = True
    include_phase: str = "run"
    llm_coverage_source: str | None = None

    # Report behavior
    report_collect_only: bool = True
    capture_failed_output: bool = False
    capture_output_max_chars: int = 4000

    # Invocation summary
    include_pytest_invocation: bool = True
    invocation_redact_patterns: list[str] = field(
        default_factory=lambda: [
            r"--password[=\s]\S+",
            r"--token[=\s]\S+",
            r"--api[_-]?key[=\s]\S+",
            r"--secret[=\s]\S+",
        ]
    )

    # Aggregation
    aggregate_dir: str | None = None
    aggregate_policy: str = "latest"
    aggregate_run_id: str | None = None
    aggregate_group_id: str | None = None
    aggregate_include_history: bool = False

    # Compliance
    metadata_file: str | None = None
    hmac_key_file: str | None = None

    # Internal
    repo_root: Path | None = None

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        # Validate provider
        valid_providers = ("none", "ollama", "litellm", "gemini")
        if self.provider not in valid_providers:
            errors.append(
                f"Invalid provider '{self.provider}'. Must be one of: {valid_providers}"
            )

        # Validate context mode
        valid_modes = ("minimal", "balanced", "complete")
        if self.llm_context_mode not in valid_modes:
            errors.append(
                f"Invalid llm_context_mode '{self.llm_context_mode}'. "
                f"Must be one of: {valid_modes}"
            )

        # Validate aggregation policy
        valid_policies = ("latest", "merge", "all")
        if self.aggregate_policy not in valid_policies:
            errors.append(
                f"Invalid aggregate_policy '{self.aggregate_policy}'. "
                f"Must be one of: {valid_policies}"
            )

        # Validate include_phase
        valid_phases = ("run", "setup", "teardown", "all")
        if self.include_phase not in valid_phases:
            errors.append(
                f"Invalid include_phase '{self.include_phase}'. "
                f"Must be one of: {valid_phases}"
            )

        # Validate numeric ranges
        if self.llm_context_bytes < 1000:
            errors.append("llm_context_bytes must be at least 1000")
        if self.llm_max_tests < 0:
            errors.append("llm_max_tests must be 0 (no limit) or positive")
        if self.llm_requests_per_minute < 1:
            errors.append("llm_requests_per_minute must be at least 1")
        if self.llm_timeout_seconds < 1:
            errors.append("llm_timeout_seconds must be at least 1")
        if self.llm_max_retries < 0:
            errors.append("llm_max_retries must be 0 or positive")

        return errors

    def is_llm_enabled(self) -> bool:
        """Check if LLM is enabled (provider is not 'none')."""
        return self.provider != "none"


def get_default_config() -> Config:
    """Get a Config instance with all defaults.

    Returns:
        Config instance with default values.
    """
    return Config()


def load_config(config: "pytest.Config") -> Config:
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
    if config.getini("llm_report_requests_per_minute") is not None:
        cfg.llm_requests_per_minute = config.getini("llm_report_requests_per_minute")
    if config.getini("llm_report_html"):
        cfg.report_html = config.getini("llm_report_html")
    if config.getini("llm_report_json"):
        cfg.report_json = config.getini("llm_report_json")
    if config.getini("llm_report_max_retries") is not None:
        try:
            cfg.llm_max_retries = int(config.getini("llm_report_max_retries"))
        except (ValueError, TypeError):
            pass

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
    if config.option.llm_requests_per_minute is not None:
        cfg.llm_requests_per_minute = config.option.llm_requests_per_minute
    if config.option.llm_max_retries is not None:
        cfg.llm_max_retries = config.option.llm_max_retries

    # Aggregation options
    if config.option.llm_aggregate_dir:
        cfg.aggregate_dir = config.option.llm_aggregate_dir
    if config.option.llm_aggregate_policy:
        cfg.aggregate_policy = config.option.llm_aggregate_policy
    if config.option.llm_aggregate_run_id:
        cfg.aggregate_run_id = config.option.llm_aggregate_run_id
    if config.option.llm_aggregate_group_id:
        cfg.aggregate_group_id = config.option.llm_aggregate_group_id
    if config.option.llm_coverage_source:
        cfg.llm_coverage_source = config.option.llm_coverage_source

    # Set repo root
    cfg.repo_root = config.rootpath

    return cfg
