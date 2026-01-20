# SPDX-License-Identifier: MIT
"""Example tests demonstrating various test statuses for the example report.

This file is used to generate the example report with a variety of test outcomes,
source coverage, and LLM annotations.
"""

import pytest
from calculator import (
    add,
    divide,
    factorial,
    fibonacci,
    is_even,
    is_positive,
    multiply,
    subtract,
)


# Passed tests - Calculator operations
class TestCalculator:
    """Tests for basic calculator operations."""

    def test_addition(self):
        """Test that addition works correctly."""
        assert add(2, 2) == 4
        assert add(-1, 1) == 0
        assert add(0, 0) == 0

    def test_subtraction(self):
        """Test that subtraction works correctly."""
        assert subtract(10, 3) == 7
        assert subtract(5, 5) == 0
        assert subtract(0, 5) == -5

    def test_multiplication(self):
        """Test that multiplication works correctly."""
        assert multiply(6, 7) == 42
        assert multiply(-2, 3) == -6
        assert multiply(0, 100) == 0

    def test_division(self):
        """Test that division works correctly."""
        assert divide(10, 2) == 5.0
        assert divide(7, 2) == 3.5
        assert divide(0, 5) == 0.0

    def test_division_by_zero(self):
        """Test that division by zero raises an error."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)


class TestNumberProperties:
    """Tests for number property checks."""

    def test_is_even(self):
        """Test even number detection."""
        assert is_even(2) is True
        assert is_even(4) is True
        assert is_even(0) is True
        assert is_even(1) is False
        assert is_even(-3) is False

    def test_is_positive(self):
        """Test positive number detection."""
        assert is_positive(1) is True
        assert is_positive(100) is True
        assert is_positive(0) is False
        assert is_positive(-1) is False


class TestRecursiveFunctions:
    """Tests for recursive mathematical functions."""

    def test_fibonacci_base_cases(self):
        """Test Fibonacci base cases."""
        assert fibonacci(0) == 0
        assert fibonacci(1) == 1

    def test_fibonacci_sequence(self):
        """Test Fibonacci sequence values."""
        assert fibonacci(5) == 5
        assert fibonacci(10) == 55

    def test_fibonacci_negative_raises(self):
        """Test that negative input raises an error."""
        with pytest.raises(ValueError, match="n must be non-negative"):
            fibonacci(-1)

    def test_factorial_base_cases(self):
        """Test factorial base cases."""
        assert factorial(0) == 1
        assert factorial(1) == 1

    def test_factorial_values(self):
        """Test factorial values."""
        assert factorial(5) == 120
        assert factorial(10) == 3628800

    def test_factorial_negative_raises(self):
        """Test that negative input raises an error."""
        with pytest.raises(ValueError, match="n must be non-negative"):
            factorial(-1)


# Failed test - intentional failure for demo
class TestFailures:
    """Tests that intentionally fail for demonstration."""

    def test_expected_failure_demo(self):
        """This test fails to demonstrate failure reporting."""
        assert 1 == 2, "Intentional failure for demo purposes"


# Skipped tests
class TestSkipped:
    """Tests that are skipped."""

    @pytest.mark.skip(reason="Feature not implemented yet")
    def test_not_implemented(self):
        """This feature is not implemented yet."""
        pass

    @pytest.mark.skipif(True, reason="Skipped for demonstration")
    def test_conditionally_skipped(self):
        """Conditionally skipped test."""
        pass


# XFail tests
class TestExpectedFailures:
    """Tests that are expected to fail."""

    @pytest.mark.xfail(reason="Known bug in edge case handling")
    def test_known_bug(self):
        """Test that fails due to a known bug."""
        raise AssertionError("Known bug")

    @pytest.mark.xfail(reason="Expected to fail but actually passes")
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
            (-5, 5, 0),
        ],
    )
    def test_add_numbers(self, a, b, expected):
        """Test addition with various inputs."""
        assert add(a, b) == expected

    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, True),
            (1, False),
            (2, True),
            (100, True),
            (-4, True),
        ],
    )
    def test_is_even_parametrized(self, n, expected):
        """Test is_even with various inputs."""
        assert is_even(n) == expected
