# SPDX-License-Identifier: MIT
"""Filesystem utilities.

Provides path normalization and file handling utilities.

Component Contract:
    Input: file paths
    Output: normalized paths, relative paths
"""

from __future__ import annotations

import os
from pathlib import Path


def normalize_path(path: str | Path) -> str:
    """Normalize a path for consistent comparison.

    - Converts to forward slashes
    - Removes trailing slashes
    - Handles case folding on Windows

    Args:
        path: Path to normalize.

    Returns:
        Normalized path string.
    """
    path_str = str(path)

    # Convert backslashes to forward slashes
    path_str = path_str.replace("\\", "/")

    # Remove trailing slash
    path_str = path_str.rstrip("/")

    # Case-fold on Windows
    if os.name == "nt":
        path_str = path_str.lower()

    return path_str


def make_relative(file_path: str | Path, base_path: str | Path | None = None) -> str:
    """Make a path relative to a base path.

    Args:
        file_path: Absolute or relative path.
        base_path: Base path to make relative to. If None, returns as-is.

    Returns:
        Relative path string.
    """
    if base_path is None:
        return normalize_path(file_path)

    try:
        file_path = Path(file_path).resolve()
        base_path = Path(base_path).resolve()

        # Try to make relative
        rel_path = file_path.relative_to(base_path)
        return normalize_path(rel_path)
    except ValueError:
        # Path is not relative to base
        return normalize_path(file_path)


def is_python_file(path: str | Path) -> bool:
    """Check if a path is a Python source file.

    Args:
        path: Path to check.

    Returns:
        True if the path ends with .py.
    """
    return str(path).endswith(".py")


def should_skip_path(
    path: str | Path,
    exclude_patterns: list[str] | None = None,
) -> bool:
    """Check if a path should be skipped.

    Always skips:
    - venv, .venv directories
    - site-packages directories
    - __pycache__ directories

    Args:
        path: Path to check.
        exclude_patterns: Additional patterns to exclude.

    Returns:
        True if the path should be skipped.
    """
    path_str = normalize_path(path)

    # Always skip these
    skip_dirs = [
        "venv/",
        ".venv/",
        "site-packages/",
        "__pycache__/",
        ".git/",
    ]

    for skip in skip_dirs:
        if skip in path_str or path_str.startswith(skip.rstrip("/")):
            return True

    # Check exclude patterns
    if exclude_patterns:
        import fnmatch

        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True

    return False
