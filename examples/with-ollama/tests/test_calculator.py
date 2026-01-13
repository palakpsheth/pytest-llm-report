import pytest
from example_pkg.calculator import add, divide


def test_add_basic():
    """Verify simple addition."""
    assert add(1, 2) == 3


def test_add_negative():
    """Verify addition with negatives."""
    assert add(-1, -1) == -2


def test_divide_success():
    """Verify division works."""
    assert divide(10, 2) == 5


def test_divide_zero():
    """Verify division by zero raises error."""
    with pytest.raises(ValueError):
        divide(10, 0)
