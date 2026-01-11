"""Sample package."""

__version__ = "0.1.0"


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def divide(a: int, b: int) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
