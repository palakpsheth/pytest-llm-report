# SPDX-License-Identifier: MIT
"""Centralized warning and error codes for pytest-llm-report.

All warning codes are defined here to ensure consistency across components.
Each warning code should have a unique identifier and actionable message.
"""

from dataclasses import dataclass
from enum import Enum


class WarningCode(str, Enum):
    """Warning codes for report generation.

    Naming convention: W{category}{number}
    Categories:
      - 0xx: Coverage-related
      - 1xx: LLM-related
      - 2xx: Output/IO-related
      - 3xx: Config-related
      - 4xx: Aggregation-related
    """

    # Coverage warnings (0xx)
    W001_NO_COVERAGE = "W001"
    W002_NO_CONTEXTS = "W002"
    W003_COVERAGE_TIMING = "W003"
    W004_MISSING_SOURCE = "W004"

    # LLM warnings (1xx)
    W101_LLM_ENABLED = "W101"
    W102_LLM_TIMEOUT = "W102"
    W103_LLM_RATE_LIMIT = "W103"
    W104_LLM_AUTH_MISSING = "W104"
    W105_LLM_MAX_TESTS_EXCEEDED = "W105"
    W106_LLM_CONTEXT_TRUNCATED = "W106"

    # Output/IO warnings (2xx)
    W201_OUTPUT_PATH_INVALID = "W201"
    W202_OUTPUT_DIR_CREATED = "W202"
    W203_ATOMIC_WRITE_FAILED = "W203"
    W204_PDF_PLAYWRIGHT_MISSING = "W204"

    # Config warnings (3xx)
    W301_INVALID_CONFIG = "W301"
    W302_DEPRECATED_OPTION = "W302"

    # Aggregation warnings (4xx)
    W401_AGGREGATE_DIR_MISSING = "W401"
    W402_SCHEMA_VERSION_MISMATCH = "W402"
    W403_DUPLICATE_RUN_ID = "W403"


@dataclass(frozen=True)
class ReportWarning:
    """A warning captured during report generation.

    Attributes:
        code: The warning code enum value.
        message: Human-readable description of the warning.
        detail: Optional additional context (e.g., file path, nodeid).
    """

    code: WarningCode | str
    message: str
    detail: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        code_val = (
            self.code.value if isinstance(self.code, WarningCode) else str(self.code)
        )
        result = {
            "code": code_val,
            "message": self.message,
        }
        if self.detail:
            result["detail"] = self.detail
        return result


# Predefined warning messages for common cases
WARNING_MESSAGES = {
    WarningCode.W001_NO_COVERAGE: (
        "No .coverage file found. Run pytest with --cov to enable coverage collection."
    ),
    WarningCode.W002_NO_CONTEXTS: (
        "Coverage contexts not enabled. Run pytest with --cov-context=test for per-test coverage mapping."
    ),
    WarningCode.W003_COVERAGE_TIMING: (
        "Coverage data may be stale. Ensure pytest-cov finalizes before reading."
    ),
    WarningCode.W004_MISSING_SOURCE: (
        "Source file referenced in coverage data not found."
    ),
    WarningCode.W101_LLM_ENABLED: (
        "LLM provider enabled. Test code will be sent to the configured provider."
    ),
    WarningCode.W102_LLM_TIMEOUT: ("LLM request timed out."),
    WarningCode.W103_LLM_RATE_LIMIT: (
        "LLM rate limit reached. Some annotations may be missing."
    ),
    WarningCode.W104_LLM_AUTH_MISSING: (
        "LLM authentication not configured. Check environment variables or config."
    ),
    WarningCode.W105_LLM_MAX_TESTS_EXCEEDED: (
        "Maximum number of tests for LLM annotation exceeded."
    ),
    WarningCode.W106_LLM_CONTEXT_TRUNCATED: (
        "LLM context was truncated to fit size limits."
    ),
    WarningCode.W201_OUTPUT_PATH_INVALID: ("Output path is invalid or unwritable."),
    WarningCode.W202_OUTPUT_DIR_CREATED: ("Output directory was created."),
    WarningCode.W203_ATOMIC_WRITE_FAILED: (
        "Atomic write failed; fell back to direct write."
    ),
    WarningCode.W204_PDF_PLAYWRIGHT_MISSING: (
        "Playwright not installed. PDF generation requires: pip install playwright && playwright install"
    ),
    WarningCode.W301_INVALID_CONFIG: ("Invalid configuration value."),
    WarningCode.W302_DEPRECATED_OPTION: ("Deprecated configuration option used."),
    WarningCode.W401_AGGREGATE_DIR_MISSING: (
        "Aggregate directory does not exist or is empty."
    ),
    WarningCode.W402_SCHEMA_VERSION_MISMATCH: (
        "Schema version mismatch in aggregated reports."
    ),
    WarningCode.W403_DUPLICATE_RUN_ID: ("Duplicate run_id found in aggregation."),
}


def make_warning(code: WarningCode, detail: str | None = None) -> ReportWarning:
    """Create a warning with the standard message for the given code.

    Args:
        code: The warning code.
        detail: Optional additional context.

    Returns:
        A ReportWarning instance with the standard message.
    """
    return ReportWarning(
        code=code,
        message=WARNING_MESSAGES.get(code, "Unknown warning."),
        detail=detail,
    )
