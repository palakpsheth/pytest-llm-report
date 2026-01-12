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
        llm_timeout_seconds: Timeout for LLM requests.
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
    llm_max_tests: int = 100
    llm_max_concurrency: int = 4
    llm_timeout_seconds: int = 30
    llm_cache_ttl_seconds: int = 86400  # 24 hours
    cache_dir: str = ".pytest_llm_cache"

    # Coverage settings
    omit_tests_from_coverage: bool = True
    include_phase: str = "run"

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
        if self.llm_max_tests < 1:
            errors.append("llm_max_tests must be at least 1")
        if self.llm_timeout_seconds < 1:
            errors.append("llm_timeout_seconds must be at least 1")

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
