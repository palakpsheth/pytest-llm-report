# SPDX-License-Identifier: MIT
"""Tests for pytest_llm_report.report_writer module."""

from datetime import UTC, datetime

from pytest_llm_report.models import CoverageEntry, TestCaseResult
from pytest_llm_report.options import Config
from pytest_llm_report.report_writer import ReportWriter, compute_sha256


class TestComputeSha256:
    """Tests for compute_sha256 function."""

    def test_empty_bytes(self):
        """Empty bytes should produce consistent hash."""
        hash1 = compute_sha256(b"")
        hash2 = compute_sha256(b"")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_different_content(self):
        """Different content should produce different hashes."""
        hash1 = compute_sha256(b"hello")
        hash2 = compute_sha256(b"world")
        assert hash1 != hash2


class TestReportWriter:
    """Tests for ReportWriter class."""

    def test_create_writer(self):
        """Writer should initialize with config."""
        config = Config()
        writer = ReportWriter(config)
        assert writer.config is config
        assert writer.warnings == []
        assert writer.artifacts == []

    def test_build_summary_counts(self):
        """Summary should count outcomes correctly."""
        config = Config()
        writer = ReportWriter(config)

        tests = [
            TestCaseResult(nodeid="test1", outcome="passed"),
            TestCaseResult(nodeid="test2", outcome="passed"),
            TestCaseResult(nodeid="test3", outcome="failed"),
            TestCaseResult(nodeid="test4", outcome="skipped"),
        ]

        summary = writer._build_summary(tests)

        assert summary.total == 4
        assert summary.passed == 2
        assert summary.failed == 1
        assert summary.skipped == 1

    def test_build_run_meta(self):
        """Run meta should include version info."""
        config = Config()
        writer = ReportWriter(config)

        tests = [TestCaseResult(nodeid="test1", outcome="passed")]
        start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 12, 1, 0, tzinfo=UTC)

        meta = writer._build_run_meta(
            tests, exit_code=0, start_time=start, end_time=end
        )

        assert meta.duration == 60.0
        assert meta.pytest_version  # Should have a value
        assert meta.plugin_version == "0.1.0"
        assert meta.python_version

    def test_write_report_assembles_tests(self):
        """Report should include all tests."""
        config = Config()  # No output paths, won't write files
        writer = ReportWriter(config)

        tests = [
            TestCaseResult(nodeid="test1", outcome="passed"),
            TestCaseResult(nodeid="test2", outcome="failed"),
        ]

        report = writer.write_report(tests)

        assert len(report.tests) == 2
        assert report.summary.total == 2

    def test_write_report_merges_coverage(self):
        """Report should merge coverage into tests."""
        config = Config()
        writer = ReportWriter(config)

        tests = [TestCaseResult(nodeid="test1", outcome="passed")]
        coverage = {
            "test1": [
                CoverageEntry(file_path="src/foo.py", line_ranges="1-5", line_count=5)
            ]
        }

        report = writer.write_report(tests, coverage=coverage)

        assert len(report.tests[0].coverage) == 1
        assert report.tests[0].coverage[0].file_path == "src/foo.py"


class TestReportWriterWithFiles:
    """Tests for file writing functionality."""

    def test_write_json_creates_file(self, tmp_path):
        """Should create JSON file with hash."""
        json_path = str(tmp_path / "report.json")
        config = Config(report_json=json_path)
        writer = ReportWriter(config)

        tests = [TestCaseResult(nodeid="test1", outcome="passed")]
        _report = writer.write_report(tests)

        # File should exist
        assert (tmp_path / "report.json").exists()

        # Should have artifact tracked
        assert len(writer.artifacts) >= 1

    def test_write_html_creates_file(self, tmp_path):
        """Should create HTML file."""
        html_path = str(tmp_path / "report.html")
        config = Config(report_html=html_path)
        writer = ReportWriter(config)

        tests = [
            TestCaseResult(nodeid="test1", outcome="passed"),
            TestCaseResult(
                nodeid="test2",
                outcome="failed",
                error_message="AssertionError",
            ),
        ]
        writer.write_report(tests)

        # File should exist
        assert (tmp_path / "report.html").exists()

        # Should contain expected content
        html = (tmp_path / "report.html").read_text()
        assert "test1" in html
        assert "test2" in html
        assert "PASSED" in html
        assert "FAILED" in html

    def test_creates_directory_if_missing(self, tmp_path):
        """Should create output directory if it doesn't exist."""
        json_path = str(tmp_path / "subdir" / "report.json")
        config = Config(report_json=json_path)
        writer = ReportWriter(config)

        tests = [TestCaseResult(nodeid="test1", outcome="passed")]
        writer.write_report(tests)

        assert (tmp_path / "subdir" / "report.json").exists()
