# SPDX-License-Identifier: MIT
"""Tests for pytest_llm_report.util.time module."""

from datetime import UTC, datetime

from pytest_llm_report.util.time import format_duration, iso_format, utc_now


class TestUtcNow:
    """Tests for utc_now function."""

    def test_returns_datetime(self):
        """Returns a datetime object."""
        result = utc_now()
        assert isinstance(result, datetime)

    def test_has_utc_timezone(self):
        """Returns datetime with UTC timezone."""
        result = utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_is_current_time(self):
        """Returns current time (within tolerance)."""
        before = datetime.now(UTC)
        result = utc_now()
        after = datetime.now(UTC)
        assert before <= result <= after


class TestIsoFormat:
    """Tests for iso_format function."""

    def test_formats_datetime_with_utc(self):
        """Formats datetime with UTC timezone."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
        result = iso_format(dt)
        assert result == "2024-01-15T10:30:45+00:00"

    def test_formats_naive_datetime(self):
        """Formats naive datetime (no timezone)."""
        dt = datetime(2024, 6, 20, 14, 0, 0)
        result = iso_format(dt)
        assert result == "2024-06-20T14:00:00"

    def test_formats_with_microseconds(self):
        """Formats datetime with microseconds."""
        dt = datetime(2024, 3, 10, 8, 15, 30, 123456, tzinfo=UTC)
        result = iso_format(dt)
        assert "123456" in result


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_microseconds_format(self):
        """Formats sub-millisecond durations as microseconds."""
        result = format_duration(0.0005)  # 500 microseconds
        assert "μs" in result
        assert result == "500μs"

    def test_very_small_microseconds(self):
        """Formats very small durations as microseconds."""
        result = format_duration(0.000001)  # 1 microsecond
        assert result == "1μs"

    def test_milliseconds_format(self):
        """Formats sub-second durations as milliseconds."""
        result = format_duration(0.5)  # 500 milliseconds
        assert "ms" in result
        assert result == "500.0ms"

    def test_small_milliseconds(self):
        """Formats small millisecond durations."""
        result = format_duration(0.001)  # 1 millisecond
        assert result == "1.0ms"

    def test_seconds_format(self):
        """Formats seconds under a minute."""
        result = format_duration(5.5)
        assert "s" in result
        assert result == "5.50s"

    def test_one_second(self):
        """Formats exactly one second."""
        result = format_duration(1.0)
        assert result == "1.00s"

    def test_minutes_format(self):
        """Formats durations over a minute."""
        result = format_duration(90.5)  # 1 minute 30.5 seconds
        assert "m" in result
        assert result == "1m 30.5s"

    def test_multiple_minutes(self):
        """Formats multiple minutes."""
        result = format_duration(185.0)  # 3 minutes 5 seconds
        assert result == "3m 5.0s"

    def test_boundary_one_minute(self):
        """Formats exactly one minute."""
        result = format_duration(60.0)
        assert result == "1m 0.0s"
