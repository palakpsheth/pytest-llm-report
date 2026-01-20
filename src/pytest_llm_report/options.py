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

        # LiteLLM-specific settings
        litellm_api_base: Custom API base URL for LiteLLM proxy.
        litellm_api_key: Static API key override for LiteLLM.
        litellm_token_refresh_command: CLI command to get fresh token.
        litellm_token_refresh_interval: Seconds before token expires.
        litellm_token_output_format: How to parse token output ("text" or "json").
        litellm_token_json_key: JSON key for token when format is "json".

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

    # LiteLLM-specific settings
    litellm_api_base: str | None = None
    litellm_api_key: str | None = None
    litellm_token_refresh_command: str | None = None
    litellm_token_refresh_interval: int = 3300  # 55 minutes
    litellm_token_output_format: str = "text"  # "text" or "json"
    litellm_token_json_key: str = "token"

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
    prompt_tier: str = "auto"  # "minimal", "standard", "auto"

    # Token optimization settings
    batch_parametrized_tests: bool = True
    batch_max_tests: int = 5
    context_compression: str = "lines"  # "none", "lines"
    context_line_padding: int = 2

    # Coverage settings
    omit_tests_from_coverage: bool = True
    include_phase: str = "run"
    llm_coverage_source: str | None = None

    # Report behavior
    report_collect_only: bool = True
    capture_failed_output: bool = True  # Changed from False to True
    capture_output_max_chars: int = 4000
    llm_strip_docstrings: bool = True  # New: strip docstrings by default

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

        # Validate LiteLLM token output format
        valid_output_formats = ("text", "json")
        if self.litellm_token_output_format not in valid_output_formats:
            errors.append(
                f"Invalid litellm_token_output_format '{self.litellm_token_output_format}'. "
                f"Must be one of: {valid_output_formats}"
            )

        # Validate token refresh interval
        if self.litellm_token_refresh_interval < 60:
            errors.append("litellm_token_refresh_interval must be at least 60 seconds")

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

        # Validate prompt_tier
        valid_tiers = ("minimal", "standard", "auto")
        if self.prompt_tier not in valid_tiers:
            errors.append(
                f"Invalid prompt_tier '{self.prompt_tier}'. "
                f"Must be one of: {valid_tiers}"
            )

        # Validate token optimization settings
        valid_compression = ("none", "lines")
        if self.context_compression not in valid_compression:
            errors.append(
                f"Invalid context_compression '{self.context_compression}'. "
                f"Must be one of: {valid_compression}"
            )
        if self.batch_max_tests < 1:
            errors.append("batch_max_tests must be at least 1")
        if self.context_line_padding < 0:
            errors.append("context_line_padding must be 0 or positive")

        return errors

    def is_llm_enabled(self) -> bool:
        """Check if LLM features are enabled.

        Returns:
            True if provider is configured and not 'none'.
        """
        return self.provider.lower() != "none"


def get_default_config() -> Config:
    """Get a Config instance with all defaults.

    Returns:
        Config instance with default values.
    """
    return Config()


def load_config(config: "pytest.Config") -> Config:
    """Load Config from pytest options and pyproject.toml [tool.pytest_llm_report].

    CLI options take precedence over pyproject.toml options.

    Args:
        config: pytest configuration object.

    Returns:
        Populated Config instance.
    """
    # Start with defaults
    cfg = Config()

    # Load from pyproject.toml [tool.pytest_llm_report]
    try:
        import tomllib
    except ImportError:
        # Python < 3.11
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            tomllib = None  # type: ignore

    if tomllib:
        pyproject_path = config.rootpath / "pyproject.toml"
        if pyproject_path.exists():
            try:
                with open(pyproject_path, "rb") as f:
                    pyproject_data = tomllib.load(f)

                tool_config = pyproject_data.get("tool", {}).get(
                    "pytest_llm_report", {}
                )

                # Map configuration from [tool.pytest_llm_report] to Config
                if "provider" in tool_config:
                    cfg.provider = tool_config["provider"]
                if "model" in tool_config:
                    cfg.model = tool_config["model"]
                if "ollama_host" in tool_config:
                    cfg.ollama_host = tool_config["ollama_host"]

                # LiteLLM-specific settings
                if "litellm_api_base" in tool_config:
                    cfg.litellm_api_base = tool_config["litellm_api_base"]
                if "litellm_api_key" in tool_config:
                    cfg.litellm_api_key = tool_config["litellm_api_key"]
                if "litellm_token_refresh_command" in tool_config:
                    cfg.litellm_token_refresh_command = tool_config[
                        "litellm_token_refresh_command"
                    ]
                if "litellm_token_refresh_interval" in tool_config:
                    cfg.litellm_token_refresh_interval = tool_config[
                        "litellm_token_refresh_interval"
                    ]
                if "litellm_token_output_format" in tool_config:
                    cfg.litellm_token_output_format = tool_config[
                        "litellm_token_output_format"
                    ]
                if "litellm_token_json_key" in tool_config:
                    cfg.litellm_token_json_key = tool_config["litellm_token_json_key"]

                # LLM context controls
                if "context_mode" in tool_config:
                    cfg.llm_context_mode = tool_config["context_mode"]
                if "context_bytes" in tool_config:
                    cfg.llm_context_bytes = tool_config["context_bytes"]
                if "context_file_limit" in tool_config:
                    cfg.llm_context_file_limit = tool_config["context_file_limit"]
                if "context_include_globs" in tool_config:
                    cfg.llm_context_include_globs = tool_config["context_include_globs"]
                if "context_exclude_globs" in tool_config:
                    cfg.llm_context_exclude_globs = tool_config["context_exclude_globs"]

                # LLM parameter handling
                if "include_param_values" in tool_config:
                    cfg.llm_include_param_values = tool_config["include_param_values"]
                if "param_value_max_chars" in tool_config:
                    cfg.llm_param_value_max_chars = tool_config["param_value_max_chars"]

                # LLM execution controls
                if "max_tests" in tool_config:
                    cfg.llm_max_tests = tool_config["max_tests"]
                if "max_concurrency" in tool_config:
                    cfg.llm_max_concurrency = tool_config["max_concurrency"]
                if "requests_per_minute" in tool_config:
                    cfg.llm_requests_per_minute = tool_config["requests_per_minute"]
                if "timeout_seconds" in tool_config:
                    cfg.llm_timeout_seconds = tool_config["timeout_seconds"]
                if "max_retries" in tool_config:
                    cfg.llm_max_retries = tool_config["max_retries"]
                if "cache_ttl_seconds" in tool_config:
                    cfg.llm_cache_ttl_seconds = tool_config["cache_ttl_seconds"]
                if "cache_dir" in tool_config:
                    cfg.cache_dir = tool_config["cache_dir"]
                if "prompt_tier" in tool_config:
                    cfg.prompt_tier = tool_config["prompt_tier"]

                # Token optimization settings
                if "batch_parametrized_tests" in tool_config:
                    cfg.batch_parametrized_tests = tool_config[
                        "batch_parametrized_tests"
                    ]
                if "batch_max_tests" in tool_config:
                    cfg.batch_max_tests = tool_config["batch_max_tests"]
                if "context_compression" in tool_config:
                    cfg.context_compression = tool_config["context_compression"]
                if "context_line_padding" in tool_config:
                    cfg.context_line_padding = tool_config["context_line_padding"]

                # Coverage settings
                if "omit_tests_from_coverage" in tool_config:
                    cfg.omit_tests_from_coverage = tool_config[
                        "omit_tests_from_coverage"
                    ]
                if "include_phase" in tool_config:
                    cfg.include_phase = tool_config["include_phase"]

                # Report behavior
                if "report_collect_only" in tool_config:
                    cfg.report_collect_only = tool_config["report_collect_only"]
                if "capture_failed_output" in tool_config:
                    cfg.capture_failed_output = tool_config["capture_failed_output"]
                if "capture_output_max_chars" in tool_config:
                    cfg.capture_output_max_chars = tool_config[
                        "capture_output_max_chars"
                    ]

                # Invocation summary
                if "include_pytest_invocation" in tool_config:
                    cfg.include_pytest_invocation = tool_config[
                        "include_pytest_invocation"
                    ]
                if "invocation_redact_patterns" in tool_config:
                    cfg.invocation_redact_patterns = tool_config[
                        "invocation_redact_patterns"
                    ]

                # Aggregation (less likely to be in config, but support it)
                if "aggregate_policy" in tool_config:
                    cfg.aggregate_policy = tool_config["aggregate_policy"]
                if "aggregate_include_history" in tool_config:
                    cfg.aggregate_include_history = tool_config[
                        "aggregate_include_history"
                    ]

                # Compliance
                if "metadata_file" in tool_config:
                    cfg.metadata_file = tool_config["metadata_file"]
                if "hmac_key_file" in tool_config:
                    cfg.hmac_key_file = tool_config["hmac_key_file"]

            except Exception as e:
                # If pyproject.toml parsing fails, warn the user and continue with defaults
                import warnings

                warnings.warn(
                    f"Could not parse [tool.pytest_llm_report] from pyproject.toml: {e}",
                    UserWarning,
                    stacklevel=2,
                )

    # Override with CLI options (CLI commands take precedence over everything)
    if hasattr(config.option, "llm_provider") and config.option.llm_provider:
        cfg.provider = config.option.llm_provider

    if hasattr(config.option, "llm_model") and config.option.llm_model:
        cfg.model = config.option.llm_model

    if hasattr(config.option, "llm_context_mode") and config.option.llm_context_mode:
        cfg.llm_context_mode = config.option.llm_context_mode

    # Token optimization CLI overrides
    if hasattr(config.option, "llm_prompt_tier") and config.option.llm_prompt_tier:
        cfg.prompt_tier = config.option.llm_prompt_tier
    if hasattr(config.option, "llm_batch_parametrized"):
        if config.option.llm_batch_parametrized is not None:
            cfg.batch_parametrized_tests = config.option.llm_batch_parametrized
    if (
        hasattr(config.option, "llm_context_compression")
        and config.option.llm_context_compression
    ):
        cfg.context_compression = config.option.llm_context_compression

    # Standard overrides (legacy and existing)
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

    # Context controls
    if (
        hasattr(config.option, "llm_context_bytes")
        and config.option.llm_context_bytes is not None
    ):
        cfg.llm_context_bytes = config.option.llm_context_bytes
    if (
        hasattr(config.option, "llm_context_file_limit")
        and config.option.llm_context_file_limit is not None
    ):
        cfg.llm_context_file_limit = config.option.llm_context_file_limit

    # Execution controls
    if (
        hasattr(config.option, "llm_max_tests")
        and config.option.llm_max_tests is not None
    ):
        cfg.llm_max_tests = config.option.llm_max_tests
    if (
        hasattr(config.option, "llm_max_concurrency")
        and config.option.llm_max_concurrency is not None
    ):
        cfg.llm_max_concurrency = config.option.llm_max_concurrency
    if (
        hasattr(config.option, "llm_timeout_seconds")
        and config.option.llm_timeout_seconds is not None
    ):
        cfg.llm_timeout_seconds = config.option.llm_timeout_seconds

    # Behavior controls
    if (
        hasattr(config.option, "llm_capture_failed")
        and config.option.llm_capture_failed is not None
    ):
        cfg.capture_failed_output = config.option.llm_capture_failed

    # Provider-specific options
    if hasattr(config.option, "llm_ollama_host") and config.option.llm_ollama_host:
        cfg.ollama_host = config.option.llm_ollama_host
    if (
        hasattr(config.option, "llm_litellm_api_base")
        and config.option.llm_litellm_api_base
    ):
        cfg.litellm_api_base = config.option.llm_litellm_api_base
    if (
        hasattr(config.option, "llm_litellm_api_key")
        and config.option.llm_litellm_api_key
    ):
        cfg.litellm_api_key = config.option.llm_litellm_api_key
    if (
        hasattr(config.option, "llm_litellm_token_refresh_command")
        and config.option.llm_litellm_token_refresh_command
    ):
        cfg.litellm_token_refresh_command = (
            config.option.llm_litellm_token_refresh_command
        )
    if (
        hasattr(config.option, "llm_litellm_token_refresh_interval")
        and config.option.llm_litellm_token_refresh_interval is not None
    ):
        cfg.litellm_token_refresh_interval = (
            config.option.llm_litellm_token_refresh_interval
        )
    if (
        hasattr(config.option, "llm_litellm_token_output_format")
        and config.option.llm_litellm_token_output_format
    ):
        cfg.litellm_token_output_format = config.option.llm_litellm_token_output_format
    if (
        hasattr(config.option, "llm_litellm_token_json_key")
        and config.option.llm_litellm_token_json_key
    ):
        cfg.litellm_token_json_key = config.option.llm_litellm_token_json_key

    # Maintenance options
    if hasattr(config.option, "llm_cache_dir") and config.option.llm_cache_dir:
        cfg.cache_dir = config.option.llm_cache_dir
    if (
        hasattr(config.option, "llm_cache_ttl")
        and config.option.llm_cache_ttl is not None
    ):
        cfg.llm_cache_ttl_seconds = config.option.llm_cache_ttl

    # Metadata options
    if hasattr(config.option, "llm_metadata_file") and config.option.llm_metadata_file:
        cfg.metadata_file = config.option.llm_metadata_file
    if hasattr(config.option, "llm_hmac_key_file") and config.option.llm_hmac_key_file:
        cfg.hmac_key_file = config.option.llm_hmac_key_file

    # Content optimization options
    if (
        hasattr(config.option, "llm_include_params")
        and config.option.llm_include_params is not None
    ):
        cfg.llm_include_param_values = config.option.llm_include_params
    if (
        hasattr(config.option, "llm_strip_docstrings")
        and config.option.llm_strip_docstrings is not None
    ):
        cfg.llm_strip_docstrings = config.option.llm_strip_docstrings

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
