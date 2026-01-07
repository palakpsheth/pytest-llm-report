# SPDX-License-Identifier: MIT
"""Time utilities."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Get current UTC time.

    Returns:
        Current datetime in UTC.
    """
    return datetime.now(UTC)


def iso_format(dt: datetime) -> str:
    """Format datetime as ISO 8601.

    Args:
        dt: Datetime to format.

    Returns:
        ISO formatted string.
    """
    return dt.isoformat()


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string like "1.23s" or "45.6ms".
    """
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.0f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
