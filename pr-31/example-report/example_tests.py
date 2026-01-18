# SPDX-License-Identifier: MIT
"""Example tests demonstrating various test statuses for the example report.

This file is used to generate the example report with a variety of test outcomes.
"""

import pytest


# Passed tests
class TestCalculator:
    """Tests for a simple calculator."""

    def test_addition(self):
        """Test that addition works correctly."""
        assert 2 + 2 == 4

    def test_subtraction(self):
        """Test that subtraction works correctly."""
        assert 10 - 3 == 7

    def test_multiplication(self):
        """Test that multiplication works correctly."""
        assert 6 * 7 == 42


class TestStringOperations:
    """Tests for string operations."""

    def test_concatenation(self):
        """Test string concatenation."""
        assert "hello" + " " + "world" == "hello world"

    def test_upper(self):
        """Test string upper case conversion."""
        assert "hello".upper() == "HELLO"


# Failed test
class TestFailures:
    """Tests that intentionally fail for demonstration."""

    def test_expected_failure_demo(self):
        """This test fails to demonstrate failure reporting."""
        assert 1 == 2, "Intentional failure for demo purposes"


# Skipped tests
class TestSkipped:
    """Tests that are skipped."""

    @pytest.mark.skip(reason="Not implemented yet")
    def test_not_implemented(self):
        """This feature is not implemented yet."""
        pass

    @pytest.mark.skipif(True, reason="Skipped on all platforms for demo")
    def test_platform_specific(self):
        """Platform-specific test that is skipped."""
        pass


# XFail tests
class TestExpectedFailures:
    """Tests that are expected to fail."""

    @pytest.mark.xfail(reason="Known bug in external library")
    def test_known_bug(self):
        """Test that fails due to a known bug."""
        raise AssertionError("Known bug")

    @pytest.mark.xfail(reason="Expected to fail but passes - XPASS")
    def test_xpass_demo(self):
        """Test marked as xfail that actually passes (xpassed)."""
        assert True


# Error test
class TestErrors:
    """Tests that raise errors during execution."""

    def test_with_error(self):
        """Test that raises an error."""
        raise RuntimeError("Intentional error for demo")


# Parameterized tests
class TestParameterized:
    """Parameterized tests demonstrating different inputs."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (1, 1, 2),
            (2, 3, 5),
            (10, 20, 30),
        ],
    )
    def test_add_numbers(self, a, b, expected):
        """Test addition with various inputs."""
        assert a + b == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("hello", 5),
            ("world", 5),
            ("python", 6),
        ],
    )
    def test_string_length(self, value, expected):
        """Test string length calculation."""
        assert len(value) == expected
