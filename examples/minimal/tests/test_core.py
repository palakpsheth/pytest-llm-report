"""Tests for core module."""

import pytest
from example_pkg.core import add, divide, multiply, subtract


class TestAdd:
    """Tests for add function."""

    def test_positive_numbers(self):
        """Add positive numbers."""
        assert add(2, 3) == 5

    def test_negative_numbers(self):
        """Add negative numbers."""
        assert add(-1, -1) == -2

    def test_zero(self):
        """Add zero."""
        assert add(0, 5) == 5


class TestSubtract:
    """Tests for subtract function."""

    def test_positive_result(self):
        """Subtract with positive result."""
        assert subtract(5, 3) == 2

    def test_negative_result(self):
        """Subtract with negative result."""
        assert subtract(3, 5) == -2


class TestMultiply:
    """Tests for multiply function."""

    def test_positive_numbers(self):
        """Multiply positive numbers."""
        assert multiply(3, 4) == 12

    def test_by_zero(self):
        """Multiply by zero."""
        assert multiply(5, 0) == 0


class TestDivide:
    """Tests for divide function."""

    def test_exact_division(self):
        """Exact division."""
        assert divide(10, 2) == 5.0

    def test_float_result(self):
        """Division with float result."""
        assert divide(7, 2) == 3.5

    def test_divide_by_zero(self):
        """Division by zero raises error."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(5, 0)
