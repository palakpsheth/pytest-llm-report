# SPDX-License-Identifier: MIT
from pathlib import Path

from pytest_llm_report.options import Config
from pytest_llm_report.report_writer import ReportWriter


def test_report_writer_metadata_skips():
    """Cover lines 135-137: metadata skips when reports disabled."""
    config = Config(report_html="r.html", report_pdf=None, report_evidence_bundle=None)
    writer = ReportWriter(config)
    # Correct signature: tests, exit_code, start_time, end_time, llm_info
    writer._build_run_meta([], 0, None, None)

    metadata = writer._build_run_meta([], 0, None, None).to_dict()
    assert "start_time" in metadata
    assert metadata.get("llm_model") is None


def test_report_writer_ensure_dir_creation():
    """Cover lines 474-479: directory creation warning."""
    import shutil

    tmp_dir = Path("tmp_test_dir")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    config = Config(report_html=str(tmp_dir / "r.html"))
    writer = ReportWriter(config)
    writer._ensure_dir(str(tmp_dir / "r.html"))

    assert tmp_dir.exists()
    assert any(w.code == "W202" for w in writer.warnings)
    shutil.rmtree(tmp_dir)
