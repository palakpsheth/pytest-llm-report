# SPDX-License-Identifier: MIT
"""Example module to demonstrate source coverage in the report.

This module provides simple utilities that the example tests will exercise.
"""


def add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        Sum of a and b.
    """
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        Difference of a and b.
    """
    return a - b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        Product of a and b.
    """
    return a * b


def divide(a: int, b: int) -> float:
    """Divide two numbers.

    Args:
        a: Numerator.
        b: Denominator.

    Returns:
        Quotient of a divided by b.

    Raises:
        ValueError: If b is zero.
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def is_even(n: int) -> bool:
    """Check if a number is even.

    Args:
        n: Number to check.

    Returns:
        True if n is even, False otherwise.
    """
    return n % 2 == 0


def is_positive(n: int) -> bool:
    """Check if a number is positive.

    Args:
        n: Number to check.

    Returns:
        True if n is positive, False otherwise.
    """
    return n > 0


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Args:
        n: Which Fibonacci number to calculate (0-indexed).

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def factorial(n: int) -> int:
    """Calculate the factorial of a number.

    Args:
        n: Number to calculate factorial of.

    Returns:
        n! (n factorial).

    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return 1
    return n * factorial(n - 1)
