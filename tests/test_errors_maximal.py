# SPDX-License-Identifier: MIT
"""Tests for errors module."""

from pytest_llm_report.errors import (
    WARNING_MESSAGES,
    ReportWarning,
    WarningCode,
    make_warning,
)


class TestWarningDataClass:
    """Tests for Warning dataclass."""

    def test_warning_to_dict_with_detail(self):
        """Should serialize correct dictionary with detail."""
        w = ReportWarning(
            code=WarningCode.W001_NO_COVERAGE,
            message="No coverage",
            detail="Check setup",
        )
        data = w.to_dict()
        assert data == {
            "code": "W001",
            "message": "No coverage",
            "detail": "Check setup",
        }

    def test_warning_to_dict_no_detail(self):
        """Should serialize correct dictionary without detail."""
        w = ReportWarning(
            code=WarningCode.W001_NO_COVERAGE,
            message="No coverage",
        )
        data = w.to_dict()
        assert data == {
            "code": "W001",
            "message": "No coverage",
        }


class TestMakeWarning:
    """Tests for make_warning function."""

    def test_make_warning_known_code(self):
        """Should create warning with standard message."""
        w = make_warning(WarningCode.W101_LLM_ENABLED)
        assert w.code == WarningCode.W101_LLM_ENABLED
        assert w.message == WARNING_MESSAGES[WarningCode.W101_LLM_ENABLED]
        assert w.detail is None

    def test_make_warning_with_detail(self):
        """Should create warning with detail."""
        w = make_warning(WarningCode.W301_INVALID_CONFIG, detail="Bad value")
        assert w.code == WarningCode.W301_INVALID_CONFIG
        assert w.detail == "Bad value"

    def test_make_warning_unknown_code(self):
        """Should use fallback message for unknown code (if enum allowed it)."""
        # We can't easily pass a non-enum to the typed function,
        # but if we extend the enum or if the dict is missing a key:

        # Simulate missing message for a valid code
        missing_code = WarningCode.W001_NO_COVERAGE
        old_message = WARNING_MESSAGES.pop(missing_code)

        try:
            w = make_warning(missing_code)
            assert w.message == "Unknown warning."
        finally:
            # Restore
            WARNING_MESSAGES[missing_code] = old_message


class TestWarningCodes:
    """Tests for WarningCode enum."""

    def test_codes_are_strings(self):
        """Enum values should be strings."""
        for code in WarningCode:
            assert isinstance(code.value, str)
            assert code.value.startswith("W")
