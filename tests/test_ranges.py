# SPDX-License-Identifier: MIT
"""Tests for pytest_llm_report.util.ranges module."""

from pytest_llm_report.util.ranges import compress_ranges, expand_ranges


class TestCompressRanges:
    """Tests for compress_ranges function."""

    def test_empty_list(self):
        """Empty list should produce empty string."""
        assert compress_ranges([]) == ""

    def test_single_line(self):
        """Single line should not use range notation."""
        assert compress_ranges([5]) == "5"

    def test_consecutive_lines(self):
        """Consecutive lines should use range notation."""
        assert compress_ranges([1, 2, 3]) == "1-3"

    def test_non_consecutive_lines(self):
        """Non-consecutive lines should be comma-separated."""
        assert compress_ranges([1, 3, 5]) == "1, 3, 5"

    def test_mixed_ranges(self):
        """Mix of ranges and singles."""
        assert compress_ranges([1, 2, 3, 5, 10, 11, 12, 15]) == "1-3, 5, 10-12, 15"

    def test_unsorted_input(self):
        """Should handle unsorted input."""
        assert compress_ranges([5, 1, 3, 2]) == "1-3, 5"

    def test_duplicates(self):
        """Should handle duplicates."""
        assert compress_ranges([1, 2, 2, 3, 3, 3]) == "1-3"

    def test_two_consecutive(self):
        """Two consecutive lines should use range notation."""
        assert compress_ranges([1, 2]) == "1-2"


class TestExpandRanges:
    """Tests for expand_ranges function."""

    def test_empty_string(self):
        """Empty string should produce empty list."""
        assert expand_ranges("") == []

    def test_single_number(self):
        """Single number should produce single-element list."""
        assert expand_ranges("5") == [5]

    def test_range(self):
        """Range should expand to list."""
        assert expand_ranges("1-3") == [1, 2, 3]

    def test_mixed(self):
        """Mix of ranges and singles."""
        assert expand_ranges("1-3, 5, 10-12") == [1, 2, 3, 5, 10, 11, 12]

    def test_roundtrip(self):
        """compress_ranges and expand_ranges should be inverses."""
        original = [1, 2, 3, 5, 10, 11, 12, 15]
        compressed = compress_ranges(original)
        expanded = expand_ranges(compressed)
        assert expanded == original
