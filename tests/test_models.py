# SPDX-License-Identifier: MIT
"""Tests for models module."""

from pytest_llm_report.models import (
    SCHEMA_VERSION,
    ArtifactEntry,
    CollectionError,
    CoverageEntry,
    LlmAnnotation,
    ReportRoot,
    ReportWarning,
    RunMeta,
    SourceCoverageEntry,
    SourceReport,
    Summary,
    TestCaseResult,
)


class TestSchemaVersion:
    """Tests for schema version."""

    def test_schema_version_format(self):
        """Schema version should be semver format."""
        parts = SCHEMA_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_schema_version_in_report_root(self):
        """ReportRoot should include schema version."""
        report = ReportRoot()
        assert report.schema_version == SCHEMA_VERSION
        assert report.to_dict()["schema_version"] == SCHEMA_VERSION


class TestCoverageEntry:
    """Tests for CoverageEntry dataclass."""

    def test_to_dict(self):
        """CoverageEntry should serialize correctly."""
        entry = CoverageEntry(
            file_path="src/foo.py",
            line_ranges="1-3, 5, 10-15",
            line_count=10,
        )
        d = entry.to_dict()
        assert d["file_path"] == "src/foo.py"
        assert d["line_ranges"] == "1-3, 5, 10-15"
        assert d["line_count"] == 10


class TestSourceCoverageEntry:
    """Tests for SourceCoverageEntry dataclass."""

    def test_to_dict(self):
        """SourceCoverageEntry should serialize correctly."""
        entry = SourceCoverageEntry(
            file_path="src/foo.py",
            statements=12,
            missed=3,
            covered=9,
            coverage_percent=75.0,
            covered_ranges="1-5, 7-9",
            missed_ranges="6, 10-11",
        )
        data = entry.to_dict()
        assert data["file_path"] == "src/foo.py"
        assert data["statements"] == 12
        assert data["missed"] == 3
        assert data["covered"] == 9
        assert data["coverage_percent"] == 75.0
        assert data["covered_ranges"] == "1-5, 7-9"
        assert data["missed_ranges"] == "6, 10-11"


class TestLlmAnnotation:
    """Tests for LlmAnnotation dataclass."""

    def test_empty_annotation(self):
        """Empty annotation should have default values."""
        annotation = LlmAnnotation()
        assert annotation.scenario == ""
        assert annotation.why_needed == ""
        assert annotation.key_assertions == []
        assert annotation.confidence is None
        assert annotation.error is None

    def test_to_dict_minimal(self):
        """Minimal annotation should serialize with required fields."""
        annotation = LlmAnnotation()
        d = annotation.to_dict()
        assert "scenario" in d
        assert "why_needed" in d
        assert "key_assertions" in d
        assert "confidence" not in d  # Optional, not included when None

    def test_to_dict_with_all_fields(self):
        """Full annotation should include all fields."""
        annotation = LlmAnnotation(
            scenario="Tests user login",
            why_needed="Prevents auth bypass",
            key_assertions=["Assert 200 status", "Assert token present"],
            confidence=0.95,
            error=None,
            context_summary={"mode": "minimal", "bytes": 1000},
        )
        d = annotation.to_dict()
        assert d["scenario"] == "Tests user login"
        assert d["confidence"] == 0.95
        assert d["context_summary"]["mode"] == "minimal"


class TestTestCaseResult:
    """Tests for TestCaseResult dataclass."""

    def test_minimal_result(self):
        """Minimal result should have required fields."""
        result = TestCaseResult(nodeid="test_foo.py::test_bar", outcome="passed")
        d = result.to_dict()
        assert d["nodeid"] == "test_foo.py::test_bar"
        assert d["outcome"] == "passed"
        assert d["duration"] == 0.0
        assert d["phase"] == "call"

    def test_result_with_coverage(self):
        """Result with coverage should include coverage list."""
        result = TestCaseResult(
            nodeid="test_foo.py::test_bar",
            outcome="passed",
            coverage=[
                CoverageEntry(file_path="src/foo.py", line_ranges="1-5", line_count=5)
            ],
        )
        d = result.to_dict()
        assert len(d["coverage"]) == 1
        assert d["coverage"][0]["file_path"] == "src/foo.py"

    def test_result_with_llm_opt_out(self):
        """Result with LLM opt-out should include flag."""
        result = TestCaseResult(
            nodeid="test_foo.py::test_bar",
            outcome="passed",
            llm_opt_out=True,
        )
        d = result.to_dict()
        assert d["llm_opt_out"] is True

    def test_result_with_rerun(self):
        """Result with reruns should include rerun fields."""
        result = TestCaseResult(
            nodeid="test_foo.py::test_bar",
            outcome="passed",
            rerun_count=2,
            final_outcome="passed",
        )
        d = result.to_dict()
        assert d["rerun_count"] == 2
        assert d["final_outcome"] == "passed"

    def test_result_without_rerun_excludes_fields(self):
        """Result without reruns should exclude rerun fields."""
        result = TestCaseResult(
            nodeid="test_foo.py::test_bar",
            outcome="passed",
        )
        d = result.to_dict()
        assert "rerun_count" not in d
        assert "final_outcome" not in d


class TestRunMeta:
    """Tests for RunMeta dataclass."""

    def test_aggregation_fields_present(self):
        """RunMeta should have aggregation fields."""
        meta = RunMeta(
            run_id="run-123",
            run_group_id="group-456",
            is_aggregated=True,
            aggregation_policy="merge",
            run_count=3,
            source_reports=[
                SourceReport(path="report1.json", sha256="abc123", run_id="run-1"),
                SourceReport(path="report2.json", sha256="def456", run_id="run-2"),
            ],
        )
        d = meta.to_dict()
        assert d["run_id"] == "run-123"
        assert d["run_group_id"] == "group-456"
        assert d["is_aggregated"] is True
        assert d["aggregation_policy"] == "merge"
        assert d["run_count"] == 3
        assert len(d["source_reports"]) == 2

    def test_non_aggregated_excludes_source_reports(self):
        """Non-aggregated report should not include source_reports."""
        meta = RunMeta()
        d = meta.to_dict()
        assert "source_reports" not in d
        assert d["is_aggregated"] is False

    def test_run_status_fields(self):
        """RunMeta should include run status fields."""
        meta = RunMeta(
            exit_code=1,
            interrupted=True,
            collect_only=True,
            collected_count=10,
            selected_count=8,
            deselected_count=2,
        )
        d = meta.to_dict()
        assert d["exit_code"] == 1
        assert d["interrupted"] is True
        assert d["collect_only"] is True
        assert d["collected_count"] == 10
        assert d["selected_count"] == 8
        assert d["deselected_count"] == 2

    def test_run_meta_to_dict_full(self):
        """Test RunMeta to dict with all optional fields."""
        meta = RunMeta(
            pytest_version="7.4.0",
            plugin_version="0.1.0",
            python_version="3.11",
            platform="linux",
            # Legacy fields
            git_sha="abc1234",
            git_dirty=True,
            # New fields
            repo_version="1.0.0",
            repo_git_sha="abc1234",
            repo_git_dirty=True,
            plugin_git_sha="def5678",
            plugin_git_dirty=False,
            config_hash="def5678",
            pytest_invocation="pytest -v",
            pytest_config_summary="config_summary",
            run_id="run-1",
            run_group_id="group-1",
            is_aggregated=True,
            aggregation_policy="merge",
        )

        # Add dummy source report
        meta.source_reports = [SourceReport(path="p", sha256="abc", run_id="r1")]

        data = meta.to_dict()

        assert data["git_sha"] == "abc1234"
        assert data["git_dirty"] is True
        assert data["repo_version"] == "1.0.0"
        assert data["repo_git_sha"] == "abc1234"
        assert data["repo_git_dirty"] is True
        assert data["plugin_git_sha"] == "def5678"
        assert data["plugin_git_dirty"] is False
        assert data["config_hash"] == "def5678"
        assert len(data["source_reports"]) == 1

    def test_llm_traceability_fields(self):
        """Test LLM traceability fields are included when enabled."""
        meta = RunMeta(
            llm_provider="ollama",
            llm_model="llama3.2:1b",
            llm_context_mode="complete",
            llm_annotations_enabled=True,
            llm_annotations_count=10,
            llm_annotations_errors=2,
        )
        data = meta.to_dict()
        assert data["llm_annotations_enabled"] is True
        assert data["llm_provider"] == "ollama"
        assert data["llm_model"] == "llama3.2:1b"
        assert data["llm_context_mode"] == "complete"
        assert data["llm_annotations_count"] == 10
        assert data["llm_annotations_errors"] == 2

    def test_llm_fields_excluded_when_disabled(self):
        """Test LLM fields are excluded when annotations not enabled."""
        meta = RunMeta(llm_annotations_enabled=False)
        data = meta.to_dict()
        assert "llm_annotations_enabled" not in data
        assert "llm_provider" not in data
        assert "llm_model" not in data


class TestReportRoot:
    """Tests for ReportRoot dataclass."""

    def test_default_report(self):
        """Default report should have schema version and empty lists."""
        report = ReportRoot()
        d = report.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION
        assert d["tests"] == []
        assert "warnings" not in d  # Empty list excluded
        assert "collection_errors" not in d  # Empty list excluded

    def test_tests_sorted_by_nodeid(self):
        """Tests should be sorted by nodeid in output."""
        report = ReportRoot(
            tests=[
                TestCaseResult(nodeid="z_test.py::test_z", outcome="passed"),
                TestCaseResult(nodeid="a_test.py::test_a", outcome="passed"),
                TestCaseResult(nodeid="m_test.py::test_m", outcome="passed"),
            ]
        )
        d = report.to_dict()
        nodeids = [t["nodeid"] for t in d["tests"]]
        assert nodeids == [
            "a_test.py::test_a",
            "m_test.py::test_m",
            "z_test.py::test_z",
        ]

    def test_report_with_warnings(self):
        """Report with warnings should include them."""
        report = ReportRoot(
            warnings=[
                ReportWarning(code="W001", message="No coverage"),
            ]
        )
        d = report.to_dict()
        assert len(d["warnings"]) == 1
        assert d["warnings"][0]["code"] == "W001"

    def test_report_with_collection_errors(self):
        """Report with collection errors should include them."""
        report = ReportRoot(
            collection_errors=[
                CollectionError(nodeid="test_bad.py", message="SyntaxError"),
            ]
        )
        d = report.to_dict()
        assert len(d["collection_errors"]) == 1
        assert d["collection_errors"][0]["nodeid"] == "test_bad.py"


class TestCollectionError:
    """Tests for CollectionError dataclass."""

    def test_to_dict(self):
        """CollectionError should serialize correctly."""
        error = CollectionError(nodeid="test_bad.py", message="Import error")
        d = error.to_dict()
        assert d["nodeid"] == "test_bad.py"
        assert d["message"] == "Import error"


class TestReportWarning:
    """Tests for ReportWarning dataclass."""

    def test_to_dict_without_detail(self):
        """Warning without detail should exclude it."""
        warning = ReportWarning(code="W001", message="No coverage")
        d = warning.to_dict()
        assert d["code"] == "W001"
        assert d["message"] == "No coverage"
        assert "detail" not in d

    def test_to_dict_with_detail(self):
        """Warning with detail should include it."""
        warning = ReportWarning(
            code="W001", message="No coverage", detail="/path/to/file"
        )
        d = warning.to_dict()
        assert d["detail"] == "/path/to/file"


class TestArtifactEntry:
    """Tests for ArtifactEntry dataclass."""

    def test_to_dict(self):
        """ArtifactEntry should serialize correctly."""
        entry = ArtifactEntry(
            path="report.json",
            sha256="abc123",
            size_bytes=1024,
        )
        d = entry.to_dict()
        assert d["path"] == "report.json"
        assert d["sha256"] == "abc123"
        assert d["size_bytes"] == 1024


class TestSourceReport:
    """Tests for SourceReport dataclass."""

    def test_to_dict_minimal(self):
        """SourceReport should serialize without optional fields."""
        source = SourceReport(path="report.json", sha256="abc123")
        d = source.to_dict()
        assert d["path"] == "report.json"
        assert d["sha256"] == "abc123"
        assert "run_id" not in d

    def test_to_dict_with_run_id(self):
        """SourceReport with run_id should include it."""
        source = SourceReport(path="report.json", sha256="abc123", run_id="run-1")
        d = source.to_dict()
        assert d["run_id"] == "run-1"


class TestSummary:
    """Tests for Summary dataclass."""

    def test_to_dict(self):
        """Summary should serialize all fields."""
        summary = Summary(
            total=10,
            passed=7,
            failed=2,
            skipped=1,
            xfailed=0,
            xpassed=0,
            error=0,
            total_duration=5.5,
        )
        d = summary.to_dict()
        assert d["total"] == 10
        assert d["passed"] == 7
        assert d["failed"] == 2
        assert d["total_duration"] == 5.5
