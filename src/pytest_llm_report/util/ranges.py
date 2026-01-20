# SPDX-License-Identifier: MIT
"""Line range compression utilities.

Provides functions to compress lists of line numbers into compact
range strings like "1-3, 5, 10-15".

Component Contract:
    Input: list of integers (line numbers)
    Output: compact string representation
"""

from __future__ import annotations


def compress_ranges(lines: list[int]) -> str:
    """Compress a list of line numbers into a compact range string.

    Examples:
        [1, 2, 3, 5] -> "1-3, 5"
        [1, 3, 5] -> "1, 3, 5"
        [1, 2, 3, 4, 5] -> "1-5"

    Args:
        lines: List of line numbers (doesn't need to be sorted).

    Returns:
        Compact string representation of the ranges.
    """
    if not lines:
        return ""

    # Sort and deduplicate
    sorted_lines = sorted(set(lines))

    ranges = []
    start = sorted_lines[0]
    end = sorted_lines[0]

    for line in sorted_lines[1:]:
        if line == end + 1:
            # Extend current range
            end = line
        else:
            # Close current range and start new one
            ranges.append(_format_range(start, end))
            start = line
            end = line

    # Don't forget the last range
    ranges.append(_format_range(start, end))

    return ", ".join(ranges)


def _format_range(start: int, end: int) -> str:
    """Format a single range.

    Args:
        start: Start line number.
        end: End line number.

    Returns:
        Formatted range string.
    """
    if start == end:
        return str(start)
    return f"{start}-{end}"


def expand_ranges(range_str: str) -> list[int]:
    """Expand a compact range string back to a list of line numbers.

    This is the inverse of compress_ranges.

    Args:
        range_str: Compact range string (e.g., "1-3, 5").

    Returns:
        List of line numbers.
    """
    if not range_str:
        return []

    lines: list[int] = []
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = int(start_str)
            end = int(end_str)
            lines.extend(range(start, end + 1))
        else:
            lines.append(int(part))

    return sorted(lines)
