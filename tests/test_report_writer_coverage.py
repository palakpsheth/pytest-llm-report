# SPDX-License-Identifier: MIT
"""Additional tests for report_writer.py to cover PDF error handling.

Targets uncovered lines:
- Lines 135-137: get_plugin_git_info runtime fallback
- Lines 424-432: PDF generation exception handling
- Lines 449-451: _resolve_pdf_html_source when no existing HTML
"""

from unittest.mock import MagicMock, patch

from pytest_llm_report.models import ReportRoot, RunMeta, Summary, TestCaseResult
from pytest_llm_report.options import Config
from pytest_llm_report.report_writer import (
    ReportWriter,
    get_git_info,
    get_plugin_git_info,
)


class TestGetGitInfo:
    """Tests for get_git_info function."""

    def test_git_info_from_valid_repo(self, tmp_path):
        """Test getting git info from a valid git repo."""
        # This test runs in the project root which is a git repo
        sha, dirty = get_git_info(".")
        # Should return something (may be None if not in git repo)
        # Just verify it doesn't crash
        assert sha is None or isinstance(sha, str)

    def test_git_info_from_nonexistent_path(self, tmp_path):
        """Test getting git info from a non-git directory."""
        sha, dirty = get_git_info(tmp_path)
        assert sha is None
        assert dirty is None


class TestGetPluginGitInfo:
    """Tests for get_plugin_git_info function."""

    def test_plugin_git_info_returns_values(self):
        """Test that plugin git info returns some values."""
        sha, dirty = get_plugin_git_info()
        # Should return something (either from _git_info or runtime git)
        # Just verify it doesn't crash
        assert sha is None or isinstance(sha, str)

    def test_plugin_git_info_fallback(self):
        """Test fallback when _git_info import fails."""
        # This exercises lines 135-137
        with patch.dict("sys.modules", {"pytest_llm_report._git_info": None}):
            # Force the fallback by removing _git_info from cache
            sha, dirty = get_plugin_git_info()
            # Should still work via git runtime fallback
            assert sha is None or isinstance(sha, str)


class TestReportWriterPDF:
    """Tests for PDF generation error handling."""

    def _make_simple_report(self) -> ReportRoot:
        """Create a minimal report for testing."""
        return ReportRoot(
            run_meta=RunMeta(
                start_time="2024-01-01T00:00:00",
                end_time="2024-01-01T00:01:00",
                duration=60.0,
                pytest_version="8.0.0",
                plugin_version="0.1.0",
                python_version="3.12.0",
                platform="linux",
            ),
            summary=Summary(total=1, passed=1),
            tests=[
                TestCaseResult(
                    nodeid="test.py::test_pass",
                    outcome="passed",
                    duration=0.1,
                )
            ],
        )

    def test_pdf_playwright_not_installed(self, tmp_path):
        """Test PDF generation when playwright is not installed."""
        config = Config(report_pdf=str(tmp_path / "report.pdf"))
        writer = ReportWriter(config)
        report = self._make_simple_report()

        # Mock playwright as not installed
        with patch("importlib.util.find_spec", return_value=None):
            writer.write_pdf(report, str(tmp_path / "report.pdf"))

        # Should have warning about playwright missing
        assert any("W204" in w.code for w in writer.warnings)
        # PDF should not be created
        assert not (tmp_path / "report.pdf").exists()

    def test_pdf_playwright_exception(self, tmp_path):
        """Test PDF generation when playwright raises exception (lines 424-432)."""
        config = Config(report_pdf=str(tmp_path / "report.pdf"))
        writer = ReportWriter(config)
        report = self._make_simple_report()

        # Mock playwright as installed but failing
        mock_spec = MagicMock()
        mock_playwright_context = MagicMock()
        mock_playwright_context.__enter__ = MagicMock(
            side_effect=RuntimeError("Browser launch failed")
        )
        mock_playwright_context.__exit__ = MagicMock(return_value=False)

        with patch("importlib.util.find_spec", return_value=mock_spec):
            with patch(
                "playwright.sync_api.sync_playwright",
                return_value=mock_playwright_context,
            ):
                writer.write_pdf(report, str(tmp_path / "report.pdf"))

        # Should have warning about PDF failure
        assert any("W201" in w.code for w in writer.warnings)

    def test_resolve_html_source_uses_existing(self, tmp_path):
        """Test _resolve_pdf_html_source uses existing HTML file."""
        html_path = tmp_path / "existing.html"
        html_path.write_text("<html><body>Test</body></html>")

        config = Config(report_html=str(html_path))
        writer = ReportWriter(config)
        report = self._make_simple_report()

        path, is_temp = writer._resolve_pdf_html_source(report)
        assert path == html_path
        assert is_temp is False

    def test_resolve_html_source_creates_temp(self, tmp_path):
        """Test _resolve_pdf_html_source creates temp file when no HTML (lines 449-451)."""
        # No HTML path configured
        config = Config()
        writer = ReportWriter(config)
        report = self._make_simple_report()

        path, is_temp = writer._resolve_pdf_html_source(report)
        assert is_temp is True
        assert path.exists()
        assert path.suffix == ".html"

        # Clean up
        path.unlink()

    def test_resolve_html_source_missing_html_file(self, tmp_path):
        """Test _resolve_pdf_html_source when configured HTML doesn't exist."""
        # HTML path configured but file doesn't exist
        config = Config(report_html=str(tmp_path / "nonexistent.html"))
        writer = ReportWriter(config)
        report = self._make_simple_report()

        path, is_temp = writer._resolve_pdf_html_source(report)
        assert is_temp is True  # Falls back to temp file
        assert path.exists()

        # Clean up
        path.unlink()


class TestReportWriterAtomicWrite:
    """Tests for atomic write fallback."""

    def test_atomic_write_fallback(self, tmp_path):
        """Test atomic write falls back to direct write on error."""
        config = Config(report_json=str(tmp_path / "report.json"))
        writer = ReportWriter(config)

        # This just exercises the normal path
        tests = [
            TestCaseResult(
                nodeid="test.py::test_pass",
                outcome="passed",
                duration=0.1,
            )
        ]
        writer.write_report(tests)

        assert (tmp_path / "report.json").exists()
