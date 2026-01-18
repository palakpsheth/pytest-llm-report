# SPDX-License-Identifier: MIT
"""Additional tests for models.py to increase coverage.

Targets uncovered lines in:
- TestCaseResult.to_dict: param_summary, captured_stdout/stderr, requirements
- Summary.to_dict: coverage_total_percent
- ReportRoot.to_dict: artifacts, source_coverage, custom_metadata, sha256, hmac_signature
"""

from pytest_llm_report.models import (
    ArtifactEntry,
    CollectionError,
    CoverageEntry,
    LlmAnnotation,
    ReportRoot,
    ReportWarning,
    SourceCoverageEntry,
    Summary,
    TestCaseResult,
)


class TestTestCaseResultToDict:
    """Tests for TestCaseResult.to_dict() edge cases."""

    def test_to_dict_with_param_summary(self):
        """Test to_dict includes param_summary when set."""
        test = TestCaseResult(
            nodeid="test.py::test_foo[param1]",
            outcome="passed",
            param_id="param1",
            param_summary="x=1, y=2",
        )
        result = test.to_dict()
        assert result["param_summary"] == "x=1, y=2"

    def test_to_dict_with_captured_stdout(self):
        """Test to_dict includes captured_stdout when set."""
        test = TestCaseResult(
            nodeid="test.py::test_foo",
            outcome="failed",
            captured_stdout="Debug output here",
        )
        result = test.to_dict()
        assert result["captured_stdout"] == "Debug output here"

    def test_to_dict_with_captured_stderr(self):
        """Test to_dict includes captured_stderr when set."""
        test = TestCaseResult(
            nodeid="test.py::test_foo",
            outcome="failed",
            captured_stderr="Error output here",
        )
        result = test.to_dict()
        assert result["captured_stderr"] == "Error output here"

    def test_to_dict_with_requirements(self):
        """Test to_dict includes requirements when set."""
        test = TestCaseResult(
            nodeid="test.py::test_foo",
            outcome="passed",
            requirements=["REQ-001", "REQ-002"],
        )
        result = test.to_dict()
        assert result["requirements"] == ["REQ-001", "REQ-002"]

    def test_to_dict_with_all_optional_fields(self):
        """Test to_dict includes all optional fields when set."""
        test = TestCaseResult(
            nodeid="test.py::test_foo[a-b-c]",
            outcome="failed",
            param_id="a-b-c",
            param_summary="a=1, b=2, c=3",
            captured_stdout="stdout content",
            captured_stderr="stderr content",
            requirements=["REQ-100"],
            error_message="AssertionError",
            llm_opt_out=True,
            llm_context_override="complete",
            coverage=[
                CoverageEntry(file_path="src/mod.py", line_ranges="1-10", line_count=10)
            ],
            llm_annotation=LlmAnnotation(
                scenario="Tests foo", why_needed="Prevents bar"
            ),
        )
        result = test.to_dict()

        assert result["param_id"] == "a-b-c"
        assert result["param_summary"] == "a=1, b=2, c=3"
        assert result["captured_stdout"] == "stdout content"
        assert result["captured_stderr"] == "stderr content"
        assert result["requirements"] == ["REQ-100"]
        assert result["llm_opt_out"] is True
        assert result["llm_context_override"] == "complete"
        assert len(result["coverage"]) == 1
        assert result["llm_annotation"]["scenario"] == "Tests foo"


class TestSummaryToDict:
    """Tests for Summary.to_dict() edge cases."""

    def test_to_dict_with_coverage_total_percent(self):
        """Test to_dict includes coverage_total_percent when set."""
        summary = Summary(
            total=10,
            passed=8,
            failed=1,
            skipped=1,
            coverage_total_percent=85.5,
        )
        result = summary.to_dict()
        assert result["coverage_total_percent"] == 85.5

    def test_to_dict_without_coverage_total_percent(self):
        """Test to_dict excludes coverage_total_percent when None."""
        summary = Summary(
            total=10,
            passed=10,
        )
        result = summary.to_dict()
        assert "coverage_total_percent" not in result


class TestReportRootToDict:
    """Tests for ReportRoot.to_dict() edge cases."""

    def test_to_dict_with_artifacts(self):
        """Test to_dict includes artifacts when set."""
        report = ReportRoot(
            artifacts=[
                ArtifactEntry(path="report.html", sha256="abc123", size_bytes=1024),
                ArtifactEntry(path="report.json", sha256="def456", size_bytes=2048),
            ]
        )
        result = report.to_dict()
        assert len(result["artifacts"]) == 2
        assert result["artifacts"][0]["path"] == "report.html"

    def test_to_dict_with_source_coverage(self):
        """Test to_dict includes source_coverage when set."""
        report = ReportRoot(
            source_coverage=[
                SourceCoverageEntry(
                    file_path="src/mod.py",
                    statements=100,
                    missed=10,
                    covered=90,
                    coverage_percent=90.0,
                    covered_ranges="1-90",
                    missed_ranges="91-100",
                )
            ]
        )
        result = report.to_dict()
        assert len(result["source_coverage"]) == 1
        assert result["source_coverage"][0]["file_path"] == "src/mod.py"

    def test_to_dict_with_custom_metadata(self):
        """Test to_dict includes custom_metadata when set."""
        report = ReportRoot(
            custom_metadata={
                "project": "myproject",
                "environment": "staging",
                "build_number": 123,
            }
        )
        result = report.to_dict()
        assert result["custom_metadata"]["project"] == "myproject"
        assert result["custom_metadata"]["environment"] == "staging"
        assert result["custom_metadata"]["build_number"] == 123

    def test_to_dict_with_sha256(self):
        """Test to_dict includes sha256 when set."""
        report = ReportRoot(sha256="abcdef1234567890")
        result = report.to_dict()
        assert result["sha256"] == "abcdef1234567890"

    def test_to_dict_with_hmac_signature(self):
        """Test to_dict includes hmac_signature when set."""
        report = ReportRoot(hmac_signature="signature123")
        result = report.to_dict()
        assert result["hmac_signature"] == "signature123"

    def test_to_dict_with_collection_errors(self):
        """Test to_dict includes collection_errors when set."""
        report = ReportRoot(
            collection_errors=[
                CollectionError(nodeid="broken_test.py", message="SyntaxError"),
            ]
        )
        result = report.to_dict()
        assert len(result["collection_errors"]) == 1
        assert result["collection_errors"][0]["nodeid"] == "broken_test.py"

    def test_to_dict_with_warnings(self):
        """Test to_dict includes warnings when set."""
        report = ReportRoot(
            warnings=[
                ReportWarning(code="W001", message="No coverage data"),
            ]
        )
        result = report.to_dict()
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["code"] == "W001"

    def test_to_dict_with_all_optional_fields(self):
        """Test to_dict includes all optional fields together."""
        report = ReportRoot(
            artifacts=[ArtifactEntry(path="a.html", sha256="aaa", size_bytes=100)],
            source_coverage=[
                SourceCoverageEntry(
                    file_path="src/x.py",
                    statements=50,
                    missed=5,
                    covered=45,
                    coverage_percent=90.0,
                    covered_ranges="1-45",
                    missed_ranges="46-50",
                )
            ],
            custom_metadata={"key": "value"},
            sha256="sha256hash",
            hmac_signature="hmachash",
            collection_errors=[CollectionError(nodeid="err.py", message="Error")],
            warnings=[ReportWarning(code="W002", message="Warning")],
        )
        result = report.to_dict()

        assert "artifacts" in result
        assert "source_coverage" in result
        assert "custom_metadata" in result
        assert "sha256" in result
        assert "hmac_signature" in result
        assert "collection_errors" in result
        assert "warnings" in result
