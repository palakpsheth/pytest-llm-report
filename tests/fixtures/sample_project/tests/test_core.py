"""Tests for sample package."""

import pytest
from sample_pkg import add, divide


def test_add_positive():
    assert add(2, 3) == 5


def test_add_zero():
    assert add(0, 5) == 5


def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(5, 0)
