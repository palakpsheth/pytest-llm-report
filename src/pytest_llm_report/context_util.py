# SPDX-License-Identifier: MIT
"""Context optimization utilities for pytest-llm-report.

This module provides utilities for compressing source code context
to reduce token consumption while preserving logical structure.

Component Contract:
    Input: Source code strings
    Output: Optimized source code strings
    Dependencies: None (pure text processing)
"""

import re


def strip_docstrings(source: str) -> str:
    """Remove Python docstrings from source code.

    Removes both triple-quoted docstrings while preserving
    the logical structure of the code.

    Args:
        source: Python source code.

    Returns:
        Source code with docstrings removed.
    """
    # Remove triple double-quoted docstrings
    triple_double = '"""'
    result = re.sub(
        re.escape(triple_double) + r".*?" + re.escape(triple_double),
        "",
        source,
        flags=re.DOTALL,
    )

    # Remove triple single-quoted docstrings
    triple_single = "'''"
    result = re.sub(
        re.escape(triple_single) + r".*?" + re.escape(triple_single),
        "",
        result,
        flags=re.DOTALL,
    )

    return result


def strip_comments(source: str) -> str:
    """Remove Python comments from source code.

    Removes # comments while preserving the code structure.
    Does not remove comments that are part of strings.

    Args:
        source: Python source code.

    Returns:
        Source code with comments removed.
    """
    lines = []
    for line in source.split("\n"):
        # Simple heuristic: remove everything after # if not in a string
        # This is not perfect but works for most cases
        if "#" in line:
            # Check if # is inside a string
            in_string = False
            quote_char = None
            result_chars = []

            for i, char in enumerate(line):
                if char in ('"', "'") and (i == 0 or line[i - 1] != "\\"):
                    if not in_string:
                        in_string = True
                        quote_char = char
                    elif char == quote_char:
                        in_string = False
                        quote_char = None

                if char == "#" and not in_string:
                    break
                result_chars.append(char)

            lines.append("".join(result_chars).rstrip())
        else:
            lines.append(line)

    return "\n".join(lines)


def collapse_empty_lines(source: str) -> str:
    """Collapse multiple consecutive empty lines into one.

    Args:
        source: Source code.

    Returns:
        Source code with collapsed empty lines.
    """
    # Replace 3+ consecutive newlines with 2 newlines
    result = re.sub(r"\n\n\n+", "\n\n", source)
    return result


def optimize_context(
    source: str, strip_docs: bool = True, strip_comms: bool = False
) -> str:
    """Apply all context optimizations to source code.

    Args:
        source: Python source code.
        strip_docs: Whether to strip docstrings.
        strip_comms: Whether to strip comments.

    Returns:
        Optimized source code.
    """
    result = source

    if strip_docs:
        result = strip_docstrings(result)

    if strip_comms:
        result = strip_comments(result)

    # Always collapse empty lines
    result = collapse_empty_lines(result)

    return result
