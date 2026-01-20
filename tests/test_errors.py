from pytest_llm_report.errors import ReportWarning, WarningCode, make_warning


def test_warning_code_values():
    """Test that warning codes have correct values."""
    assert WarningCode.W001_NO_COVERAGE.value == "W001"
    assert WarningCode.W101_LLM_ENABLED.value == "W101"
    assert WarningCode.W201_OUTPUT_PATH_INVALID.value == "W201"
    assert WarningCode.W301_INVALID_CONFIG.value == "W301"
    assert WarningCode.W401_AGGREGATE_DIR_MISSING.value == "W401"


def test_warning_to_dict():
    """Test ReportWarning.to_dict() method."""
    w = ReportWarning(
        code=WarningCode.W001_NO_COVERAGE, message="No coverage", detail="some/path"
    )
    d = w.to_dict()
    assert d == {"code": "W001", "message": "No coverage", "detail": "some/path"}

    w_no_detail = ReportWarning(
        code=WarningCode.W101_LLM_ENABLED, message="LLM enabled"
    )
    assert w_no_detail.to_dict() == {"code": "W101", "message": "LLM enabled"}


def test_make_warning():
    """Test the make_warning factory function."""
    w = make_warning(WarningCode.W001_NO_COVERAGE, detail="test-detail")
    assert w.code == WarningCode.W001_NO_COVERAGE
    assert "No .coverage file found" in w.message
    assert w.detail == "test-detail"

    w_unknown = make_warning("NON_EXISTENT_CODE")
    assert w_unknown.message == "Unknown warning."
