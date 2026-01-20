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


def test_failure_demo():
    """A test that intentionally fails to show error reporting."""
    assert add(1, 1) == 3


@pytest.mark.skip(reason="Demonstrating skipped test reporting")
def test_skip_demo():
    """A test that is skipped."""
    pytest.fail("Should be skipped")


@pytest.mark.xfail(reason="Demonstrating xfailed test reporting")
def test_xfail_demo():
    """A test that is expected to fail."""
    assert 1 / 0 == 1
