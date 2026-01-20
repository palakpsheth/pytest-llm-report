# SPDX-License-Identifier: MIT
"""Data models for pytest-llm-report.

This module defines the core dataclasses used throughout the plugin.
All models are designed for deterministic JSON serialization.

Component Contracts:
- options -> Config: CLI args and pyproject.toml -> Config dataclass
- collector -> list[TestCaseResult]: pytest hooks -> test outcomes
- coverage_map -> dict[nodeid, list[CoverageEntry]]: .coverage -> per-test coverage
- prompts/context -> PromptPayload + ContextSummary: test code -> LLM prompt
- llm provider -> LlmAnnotation: prompt -> structured annotation
- render -> HTML string: ReportRoot -> HTML
- report_writer -> JSON + HTML + manifest: all data -> output files
"""

from dataclasses import dataclass, field
from typing import Any, ClassVar

from pytest_llm_report.errors import ReportWarning

# Schema version for report format compatibility
SCHEMA_VERSION = "1.1.0"


@dataclass
class LlmTokenUsage:
    """Token usage statistics for an LLM call.

    Attributes:
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        total_tokens: Total tokens used.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class CoverageEntry:
    """A file and its covered line ranges for a single test.

    Attributes:
        file_path: Repo-relative path to the covered file.
        line_ranges: Compact line ranges (e.g., "1-3, 5, 10-15").
        line_count: Total number of lines covered.
    """

    file_path: str
    line_ranges: str
    line_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "line_ranges": self.line_ranges,
            "line_count": self.line_count,
        }


@dataclass
class SourceCoverageEntry:
    """Coverage summary for a source file.

    Attributes:
        file_path: Repo-relative path to the covered file.
        statements: Total number of statements.
        missed: Number of missed statements.
        covered: Number of covered statements.
        coverage_percent: Coverage percentage for the file.
        covered_ranges: Compact ranges of covered lines.
        missed_ranges: Compact ranges of missed lines.
    """

    file_path: str
    statements: int
    missed: int
    covered: int
    coverage_percent: float
    covered_ranges: str
    missed_ranges: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "statements": self.statements,
            "missed": self.missed,
            "covered": self.covered,
            "coverage_percent": self.coverage_percent,
            "covered_ranges": self.covered_ranges,
            "missed_ranges": self.missed_ranges,
        }


@dataclass
class LlmAnnotation:
    """LLM-generated annotation for a test.

    Attributes:
        scenario: What the test verifies (1-3 sentences).
        why_needed: What regression/bug it prevents (1-3 sentences).
        key_assertions: The critical checks performed (3-8 bullets).
        confidence: Optional confidence score (0.0-1.0).
        error: Error message if LLM call failed.
        context_summary: Summary of context used for this annotation.
    """

    scenario: str = ""
    why_needed: str = ""
    key_assertions: list[str] = field(default_factory=list)
    confidence: float | None = None
    error: str | None = None
    context_summary: dict[str, Any] | None = None
    token_usage: LlmTokenUsage | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "scenario": self.scenario,
            "why_needed": self.why_needed,
            "key_assertions": self.key_assertions,
        }
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.error is not None:
            result["error"] = self.error
        if self.context_summary is not None:
            result["context_summary"] = self.context_summary
        if self.token_usage is not None:
            result["token_usage"] = self.token_usage.to_dict()
        return result


@dataclass
class TestCaseResult:
    """Result of a single test case.

    Attributes:
        nodeid: Full pytest nodeid (e.g., "tests/test_foo.py::test_bar").
        outcome: Test outcome (passed, failed, skipped, xfailed, xpassed, error).
        duration: Test duration in seconds.
        phase: Phase where outcome occurred (setup, call, teardown).
        error_message: Short error message if failed.
        param_id: Parameter id for parameterized tests.
        param_summary: Optional redacted parameter summary.
        rerun_count: Number of reruns (pytest-rerunfailures).
        final_outcome: Final outcome after reruns.
        coverage: List of coverage entries for this test.
        llm_annotation: Optional LLM annotation.
        llm_opt_out: Whether LLM annotation was opted out via marker.
        llm_context_override: Context mode override from marker.
        captured_stdout: Captured stdout (opt-in, truncated).
        captured_stderr: Captured stderr (opt-in, truncated).
        requirements: List of requirement IDs from markers.
    """

    nodeid: str
    outcome: str
    duration: float = 0.0
    phase: str = "call"
    error_message: str | None = None
    param_id: str | None = None
    param_summary: str | None = None
    rerun_count: int = 0
    final_outcome: str | None = None
    coverage: list[CoverageEntry] = field(default_factory=list)
    llm_annotation: LlmAnnotation | None = None
    llm_opt_out: bool = False
    llm_context_override: str | None = None
    captured_stdout: str | None = None
    captured_stderr: str | None = None
    requirements: list[str] = field(default_factory=list)
    __test__: ClassVar[bool] = False

    @property
    def file_path(self) -> str:
        """Get the file path portion of the nodeid."""
        return self.nodeid.split("::")[0]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "nodeid": self.nodeid,
            "outcome": self.outcome,
            "duration": self.duration,
            "phase": self.phase,
            "file_path": self.file_path,
        }
        if self.error_message:
            result["error_message"] = self.error_message
        if self.param_id:
            result["param_id"] = self.param_id
        if self.param_summary:
            result["param_summary"] = self.param_summary
        if self.rerun_count > 0:
            result["rerun_count"] = self.rerun_count
            result["final_outcome"] = self.final_outcome
        if self.coverage:
            result["coverage"] = [c.to_dict() for c in self.coverage]
        if self.llm_annotation:
            result["llm_annotation"] = self.llm_annotation.to_dict()
        if self.llm_opt_out:
            result["llm_opt_out"] = True
        if self.llm_context_override:
            result["llm_context_override"] = self.llm_context_override
        if self.captured_stdout:
            result["captured_stdout"] = self.captured_stdout
        if self.captured_stderr:
            result["captured_stderr"] = self.captured_stderr
        if self.requirements:
            result["requirements"] = self.requirements
        return result


@dataclass
class CollectionError:
    """An error that occurred during test collection.

    Attributes:
        nodeid: Partial nodeid where collection failed.
        message: Short error message.
    """

    nodeid: str
    message: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "nodeid": self.nodeid,
            "message": self.message,
        }


@dataclass
class ArtifactEntry:
    """An artifact file generated by the report.

    Attributes:
        path: File path (relative to output dir).
        sha256: SHA256 hash of the file contents.
        size_bytes: File size in bytes.
    """

    path: str
    sha256: str
    size_bytes: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass
class SourceReport:
    """Reference to a source report used in aggregation.

    Attributes:
        path: Path to the source JSON report.
        sha256: SHA256 hash of the source report.
        run_id: Run ID from the source report.
    """

    path: str
    sha256: str
    run_id: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "path": self.path,
            "sha256": self.sha256,
        }
        if self.run_id:
            result["run_id"] = self.run_id
        return result


@dataclass
class RunMeta:
    """Metadata about the test run.

    Attributes:
        start_time: UTC start time (ISO 8601).
        end_time: UTC end time (ISO 8601).
        duration: Total duration in seconds.
        pytest_version: pytest version string.
        plugin_version: pytest-llm-report version string.
        python_version: Python version string.
        platform: OS platform string.
        git_sha: Git commit SHA (if available).
        git_dirty: Whether the working tree has uncommitted changes.
        config_hash: Hash of the tool configuration.
        pytest_invocation: Sanitized pytest command line args.
        pytest_config_summary: Sanitized pytest ini options.
        exit_code: pytest exit code.
        interrupted: Whether the run was interrupted.
        collect_only: Whether this was a collect-only run.
        collected_count: Number of tests collected.
        selected_count: Number of tests selected to run.
        deselected_count: Number of tests deselected.
        rerun_count: Total number of reruns.
        run_id: Unique identifier for this run.
        run_group_id: Optional group identifier for related runs.
        is_aggregated: Whether this is an aggregated report.
        aggregation_policy: Aggregation policy used.
        run_count: Number of runs aggregated.
        source_reports: List of source reports (for aggregated reports).
        llm_provider: LLM provider name (e.g., "ollama", "gemini").
        llm_model: LLM model name/version (e.g., "llama3.2:1b").
        llm_context_mode: LLM context mode (minimal, balanced, complete).
        llm_annotations_enabled: Whether LLM annotations were enabled.
        llm_annotations_count: Number of tests annotated.
        llm_annotations_errors: Number of annotation errors.
    """

    start_time: str = ""
    end_time: str = ""
    duration: float = 0.0
    pytest_version: str = ""
    plugin_version: str = ""
    python_version: str = ""
    platform: str = ""
    git_sha: str | None = None  # Deprecated in favor of repo_git_sha
    git_dirty: bool | None = None  # Deprecated in favor of repo_git_dirty
    repo_version: str | None = None
    repo_git_sha: str | None = None
    repo_git_dirty: bool | None = None
    plugin_git_sha: str | None = None
    plugin_git_dirty: bool | None = None
    config_hash: str | None = None
    pytest_invocation: list[str] | None = None
    pytest_config_summary: dict[str, str] | None = None
    exit_code: int = 0
    interrupted: bool = False
    collect_only: bool = False
    collected_count: int = 0
    selected_count: int = 0
    deselected_count: int = 0
    rerun_count: int = 0
    run_id: str | None = None
    run_group_id: str | None = None
    is_aggregated: bool = False
    aggregation_policy: str | None = None
    run_count: int = 1
    source_reports: list[SourceReport] = field(default_factory=list)
    # LLM traceability fields
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_context_mode: str | None = None
    llm_annotations_enabled: bool = False
    llm_annotations_count: int | None = None
    llm_annotations_errors: int | None = None
    llm_total_input_tokens: int | None = None
    llm_total_output_tokens: int | None = None
    llm_total_tokens: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "pytest_version": self.pytest_version,
            "plugin_version": self.plugin_version,
            "python_version": self.python_version,
            "platform": self.platform,
            "exit_code": self.exit_code,
            "interrupted": self.interrupted,
            "collect_only": self.collect_only,
            "collected_count": self.collected_count,
            "selected_count": self.selected_count,
            "deselected_count": self.deselected_count,
            "rerun_count": self.rerun_count,
            "is_aggregated": self.is_aggregated,
            "run_count": self.run_count,
        }
        if self.git_sha:
            result["git_sha"] = self.git_sha
            result["git_dirty"] = self.git_dirty
        if self.repo_version:
            result["repo_version"] = self.repo_version
        if self.repo_git_sha:
            result["repo_git_sha"] = self.repo_git_sha
            result["repo_git_dirty"] = self.repo_git_dirty
        if self.plugin_git_sha:
            result["plugin_git_sha"] = self.plugin_git_sha
            result["plugin_git_dirty"] = self.plugin_git_dirty
        if self.config_hash:
            result["config_hash"] = self.config_hash
        if self.pytest_invocation is not None:
            result["pytest_invocation"] = self.pytest_invocation
        if self.pytest_config_summary is not None:
            result["pytest_config_summary"] = self.pytest_config_summary
        if self.run_id:
            result["run_id"] = self.run_id
        if self.run_group_id:
            result["run_group_id"] = self.run_group_id
        if self.is_aggregated:
            result["aggregation_policy"] = self.aggregation_policy
            result["source_reports"] = [s.to_dict() for s in self.source_reports]
        # LLM traceability fields
        if self.llm_annotations_enabled:
            result["llm_annotations_enabled"] = True
            if self.llm_provider:
                result["llm_provider"] = self.llm_provider
            if self.llm_model:
                result["llm_model"] = self.llm_model
            if self.llm_context_mode:
                result["llm_context_mode"] = self.llm_context_mode
            if self.llm_annotations_count is not None:
                result["llm_annotations_count"] = self.llm_annotations_count
            if self.llm_annotations_errors is not None:
                result["llm_annotations_errors"] = self.llm_annotations_errors
            if self.llm_total_input_tokens is not None:
                result["llm_total_input_tokens"] = self.llm_total_input_tokens
            if self.llm_total_output_tokens is not None:
                result["llm_total_output_tokens"] = self.llm_total_output_tokens
            if self.llm_total_tokens is not None:
                result["llm_total_tokens"] = self.llm_total_tokens
        return result


@dataclass
class Summary:
    """Summary statistics for the test run.

    Attributes:
        total: Total number of tests.
        passed: Number of passed tests.
        failed: Number of failed tests.
        skipped: Number of skipped tests.
        xfailed: Number of xfailed tests.
        xpassed: Number of xpassed tests.
        error: Number of tests with errors.
        total_duration: Total duration in seconds.
    """

    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    xfailed: int = 0
    xpassed: int = 0
    error: int = 0
    total_duration: float = 0.0
    coverage_total_percent: float | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "xfailed": self.xfailed,
            "xpassed": self.xpassed,
            "error": self.error,
            "total_duration": self.total_duration,
        }
        if self.coverage_total_percent is not None:
            result["coverage_total_percent"] = self.coverage_total_percent
        return result


@dataclass
class ReportRoot:
    """Root data structure for the report.

    Attributes:
        schema_version: Version of the report schema.
        run_meta: Metadata about the test run.
        summary: Summary statistics.
        tests: List of test results.
        collection_errors: List of collection errors.
        warnings: List of warnings.
        artifacts: List of generated artifact files.
        source_coverage: Per-file coverage summary (if available).
        custom_metadata: Optional user-provided metadata.
        sha256: SHA256 hash of this report (computed after serialization).
        hmac_signature: Optional HMAC signature.
    """

    schema_version: str = SCHEMA_VERSION
    run_meta: RunMeta = field(default_factory=RunMeta)
    summary: Summary = field(default_factory=Summary)
    tests: list[TestCaseResult] = field(default_factory=list)
    collection_errors: list[CollectionError] = field(default_factory=list)
    warnings: list[ReportWarning] = field(default_factory=list)
    artifacts: list[ArtifactEntry] = field(default_factory=list)
    source_coverage: list[SourceCoverageEntry] = field(default_factory=list)
    custom_metadata: dict[str, Any] | None = None
    sha256: str | None = None
    hmac_signature: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for deterministic JSON serialization.

        Tests are sorted by nodeid for deterministic ordering.
        """
        # Sort tests by nodeid for deterministic output
        sorted_tests = sorted(self.tests, key=lambda t: t.nodeid)

        result = {
            "schema_version": self.schema_version,
            "run_meta": self.run_meta.to_dict(),
            "summary": self.summary.to_dict(),
            "tests": [t.to_dict() for t in sorted_tests],
        }
        if self.collection_errors:
            result["collection_errors"] = [e.to_dict() for e in self.collection_errors]
        if self.warnings:
            result["warnings"] = [w.to_dict() for w in self.warnings]
        if self.artifacts:
            result["artifacts"] = [a.to_dict() for a in self.artifacts]
        if self.source_coverage:
            result["source_coverage"] = [s.to_dict() for s in self.source_coverage]
        if self.custom_metadata:
            result["custom_metadata"] = self.custom_metadata
        if self.sha256:
            result["sha256"] = self.sha256
        if self.hmac_signature:
            result["hmac_signature"] = self.hmac_signature
        return result
