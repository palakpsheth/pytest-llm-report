# SPDX-License-Identifier: MIT
"""Tests for util/fs module."""

from pytest_llm_report.util.fs import (
    is_python_file,
    make_relative,
    normalize_path,
    should_skip_path,
)


class TestNormalizePath:
    """Tests for normalize_path."""

    def test_forward_slashes(self):
        """Should convert backslashes to forward slashes."""
        assert normalize_path("foo\\bar") == "foo/bar"

    def test_strips_trailing_slash(self):
        """Should strip trailing slashes."""
        assert normalize_path("foo/bar/") == "foo/bar"

    def test_already_normalized(self):
        """Should handle already-normalized paths."""
        assert normalize_path("foo/bar") == "foo/bar"


class TestMakeRelative:
    """Tests for make_relative."""

    def test_returns_normalized_with_no_base(self):
        """Should return normalized path when no base."""
        result = make_relative("foo/bar")
        assert result == "foo/bar"

    def test_makes_path_relative(self, tmp_path):
        """Should make absolute path relative."""
        file_path = tmp_path / "subdir" / "file.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        result = make_relative(file_path, tmp_path)
        assert result == "subdir/file.py"


class TestIsPythonFile:
    """Tests for is_python_file."""

    def test_python_file(self):
        """Should return True for .py files."""
        assert is_python_file("foo/bar.py") is True

    def test_non_python_file(self):
        """Should return False for non-.py files."""
        assert is_python_file("foo/bar.txt") is False
        assert is_python_file("foo/bar.pyc") is False


class TestShouldSkipPath:
    """Tests for should_skip_path."""

    def test_skips_venv(self):
        """Should skip venv directories."""
        assert should_skip_path("venv/lib/python/site.py") is True
        assert should_skip_path(".venv/lib/python/site.py") is True

    def test_skips_pycache(self):
        """Should skip __pycache__ directories."""
        assert should_skip_path("foo/__pycache__/bar.pyc") is True

    def test_skips_git(self):
        """Should skip .git directories."""
        assert should_skip_path(".git/objects/foo") is True

    def test_normal_path(self):
        """Should not skip normal paths."""
        assert should_skip_path("src/module.py") is False

    def test_custom_exclude_patterns(self):
        """Should skip paths matching custom patterns."""
        assert should_skip_path("tests/conftest.py", exclude_patterns=["test*"]) is True
        assert should_skip_path("src/module.py", exclude_patterns=["test*"]) is False
