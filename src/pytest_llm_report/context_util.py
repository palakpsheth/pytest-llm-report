# SPDX-License-Identifier: MIT
"""Context optimization utilities for pytest-llm-report.

This module provides utilities for compressing source code context
to reduce token consumption while preserving logical structure.

Component Contract:
    Input: Source code strings
    Output: Optimized source code strings
    Dependencies: tokenize, io
"""

import io
import re
import tokenize


def strip_docstrings(source: str) -> str:
    """Remove Python docstrings from source code using tokenizer.

    Args:
        source: Python source code.

    Returns:
        Source code with docstrings removed.
    """
    try:
        # standard tokenize expects bytes
        tokens = list(tokenize.tokenize(io.BytesIO(source.encode("utf-8")).readline))
    except tokenize.TokenError:
        return source

    out_tokens = []

    for i, token in enumerate(tokens):
        if token.type == tokenize.STRING:
            # Backtrack to find significant token
            j = i - 1
            while j >= 0:
                t_type = tokens[j].type
                if t_type in (
                    tokenize.NL,
                    tokenize.COMMENT,
                    tokenize.NEWLINE,
                    tokenize.INDENT,
                ):
                    j -= 1
                    continue
                break

            is_doc = False
            if j < 0:  # Start of stream
                is_doc = True
            else:
                prev = tokens[j]
                if prev.type == tokenize.ENCODING:
                    is_doc = True
                elif prev.type == tokenize.OP and prev.string == ":":
                    is_doc = True

            if is_doc:
                continue  # Skip the docstring

        out_tokens.append(token)

    result = tokenize.untokenize(out_tokens)
    if isinstance(result, bytes):
        result = result.decode("utf-8")
    return result


def strip_comments(source: str) -> str:
    """Remove Python comments from source code using tokenizer.

    Args:
        source: Python source code.

    Returns:
        Source code with comments removed.
    """
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(source.encode("utf-8")).readline))
    except tokenize.TokenError:
        return source

    out_tokens = [t for t in tokens if t.type != tokenize.COMMENT]

    result = tokenize.untokenize(out_tokens)
    if isinstance(result, bytes):
        result = result.decode("utf-8")

    # Remove trailing whitespace from lines efficiently
    return "\n".join(line.rstrip() for line in result.splitlines())


def collapse_empty_lines(source: str) -> str:
    """Collapse multiple consecutive empty lines into one.

    Args:
        source: Source code.

    Returns:
        Source code with collapsed empty lines.
    """
    # Replace 3+ consecutive newlines with 2 newlines (preserves paragraph structure but compacts)
    # or just all multiple newlines to single blank line?
    # Original logic was 3+ -> 2.
    return re.sub(r"\n\n\n+", "\n\n", source)


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
