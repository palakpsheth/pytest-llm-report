# SPDX-License-Identifier: MIT
"""Tests for pytest_llm_report.report_writer module."""

from datetime import UTC, datetime
from pathlib import Path

from pytest_llm_report.__about__ import __version__
from pytest_llm_report.errors import WarningCode
from pytest_llm_report.models import CoverageEntry, SourceCoverageEntry, TestCaseResult
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

    def test_build_summary_all_outcomes(self):
        """Summary should count all outcome types."""
        config = Config()
        writer = ReportWriter(config)

        tests = [
            TestCaseResult(nodeid="1", outcome="passed"),
            TestCaseResult(nodeid="2", outcome="failed"),
            TestCaseResult(nodeid="3", outcome="skipped"),
            TestCaseResult(nodeid="4", outcome="xfailed"),
            TestCaseResult(nodeid="5", outcome="xpassed"),
            TestCaseResult(nodeid="6", outcome="error"),
        ]

        summary = writer._build_summary(tests)

        assert summary.total == 6
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.skipped == 1
        assert summary.xfailed == 1
        assert summary.xpassed == 1
        assert summary.error == 1

    def test_write_report_includes_coverage_percent(self):
        """Report should include total coverage percentage."""
        config = Config()
        writer = ReportWriter(config)

        report = writer.write_report([], coverage_percent=85.5)

        assert report.summary.coverage_total_percent == 85.5

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
        assert meta.plugin_version == __version__
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

    def test_write_report_includes_source_coverage(self):
        """Report should include source coverage summary."""
        config = Config()
        writer = ReportWriter(config)

        source_coverage = [
            SourceCoverageEntry(
                file_path="src/foo.py",
                statements=8,
                missed=1,
                covered=7,
                coverage_percent=87.5,
                covered_ranges="1-4, 6-7",
                missed_ranges="5",
            )
        ]

        report = writer.write_report([], source_coverage=source_coverage)

        assert len(report.source_coverage) == 1
        assert report.source_coverage[0].file_path == "src/foo.py"


class TestReportWriterWithFiles:
    """Tests for file writing functionality."""

    def test_write_json_creates_file(self, tmp_path):
        """Should create JSON file with hash."""
        json_path = str(tmp_path / "report.json")
        config = Config(report_json=json_path)
        writer = ReportWriter(config)

        tests = [TestCaseResult(nodeid="test1", outcome="passed")]
        writer.write_report(tests)

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
        assert "Skipped" in html
        assert "XFailed" in html
        assert "XPassed" in html
        assert "Errors" in html

    def test_write_html_includes_xfail_summary(self, tmp_path):
        """Should include xfail outcomes in the HTML summary."""
        html_path = str(tmp_path / "report.html")
        config = Config(report_html=html_path)
        writer = ReportWriter(config)

        tests = [
            TestCaseResult(nodeid="test_xfail", outcome="xfailed"),
            TestCaseResult(nodeid="test_xpass", outcome="xpassed"),
        ]
        writer.write_report(tests)

        html = (tmp_path / "report.html").read_text()
        assert "XFAILED" in html
        assert "XFailed" in html
        assert "XPASSED" in html
        assert "XPassed" in html

    def test_creates_directory_if_missing(self, tmp_path):
        """Should create output directory if it doesn't exist."""
        json_path = str(tmp_path / "subdir" / "report.json")
        config = Config(report_json=json_path)
        writer = ReportWriter(config)

        tests = [TestCaseResult(nodeid="test1", outcome="passed")]
        writer.write_report(tests)

        assert (tmp_path / "subdir" / "report.json").exists()

    def test_atomic_write_fallback(self, tmp_path):
        """Should fall back to direct write if atomic write fails."""
        from unittest.mock import patch

        json_path = str(tmp_path / "report.json")
        config = Config(report_json=json_path)
        writer = ReportWriter(config)

        # Mock os.replace to fail
        with patch("os.replace", side_effect=OSError("Cross-device link")):
            writer.write_report([])

        assert (tmp_path / "report.json").exists()
        assert any(w.code == "W203" for w in writer.warnings)

    def test_ensure_dir_failure(self, tmp_path):
        """Should capture warning if directory creation fails."""
        from unittest.mock import patch

        # Path that definitely doesn't exist
        json_path = str(tmp_path / "nonexistent" / "report.json")

        config = Config(report_json=json_path)
        writer = ReportWriter(config)

        # Mock mkdir to raise OSError
        with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            writer._ensure_dir(json_path)

        assert any(w.code == "W201" for w in writer.warnings)

    def test_git_info_failure(self):
        """Should handle git command failures gracefully."""
        from unittest.mock import patch

        from pytest_llm_report.report_writer import get_git_info

        with patch("subprocess.check_output", side_effect=Exception("Git not found")):
            sha, dirty = get_git_info()
            assert sha is None
            assert dirty is None

    def test_write_pdf_creates_file(self, tmp_path):
        """Should create PDF file when Playwright is available."""
        from unittest.mock import MagicMock, patch

        pdf_path = tmp_path / "report.pdf"
        config = Config(report_pdf=str(pdf_path))
        writer = ReportWriter(config)

        # Mock the playwright module and browser
        mock_page = MagicMock()
        mock_browser = MagicMock()

        mock_playwright_context = MagicMock()

        # Setup page.pdf to actually write the file
        def write_pdf(path, **kwargs):
            Path(path).write_bytes(b"%PDF-1.4\n%fake")

        mock_page.pdf = write_pdf

        # Setup the mock chain
        mock_browser.new_page.return_value = mock_page
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright_context.__enter__.return_value = mock_playwright_context
        mock_playwright_context.__exit__.return_value = False

        mock_sync_playwright = MagicMock(return_value=mock_playwright_context)

        # Mock both the module import and find_spec
        mock_module = MagicMock()
        mock_module.sync_playwright = mock_sync_playwright

        with patch.dict("sys.modules", {"playwright.sync_api": mock_module}):
            with patch("importlib.util.find_spec", return_value=MagicMock()):
                tests = [TestCaseResult(nodeid="test1", outcome="passed")]
                writer.write_report(tests)

        assert pdf_path.exists()
        assert any(artifact.path == str(pdf_path) for artifact in writer.artifacts)

    def test_write_pdf_missing_playwright_warns(self, tmp_path):
        """Should warn when Playwright is missing for PDF output."""
        from unittest.mock import patch

        pdf_path = tmp_path / "report.pdf"
        config = Config(report_pdf=str(pdf_path))
        writer = ReportWriter(config)

        # Mock importlib.util.find_spec to return None (module not found)
        with patch("importlib.util.find_spec", return_value=None):
            tests = [TestCaseResult(nodeid="test1", outcome="passed")]
            writer.write_report(tests)

        assert not pdf_path.exists()
        assert any(
            w.code == WarningCode.W204_PDF_PLAYWRIGHT_MISSING.value
            for w in writer.warnings
        )
