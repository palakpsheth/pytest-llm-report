# SPDX-License-Identifier: MIT
"""Additional tests for util/fs.py to increase coverage.

Targets uncovered lines:
- Line 40: Windows case folding (hard to test on Linux)
- Lines 65-67: Path is not relative to base (ValueError)
"""

from pathlib import Path

from pytest_llm_report.util.fs import (
    is_python_file,
    make_relative,
    normalize_path,
    should_skip_path,
)


class TestMakeRelative:
    """Tests for make_relative function edge cases."""

    def test_make_relative_path_not_under_base(self, tmp_path):
        """Test make_relative when path is not relative to base."""
        # Create two unrelated paths
        path1 = tmp_path / "project1" / "file.py"
        path1.parent.mkdir(parents=True, exist_ok=True)
        path1.touch()

        path2 = tmp_path / "project2"
        path2.mkdir(parents=True, exist_ok=True)

        # path1 is not relative to path2
        result = make_relative(str(path1), str(path2))

        # Should return normalized absolute path since relative_to will fail
        assert "project1" in result
        assert "file.py" in result

    def test_make_relative_with_none_base(self):
        """Test make_relative with None base returns normalized path."""
        result = make_relative("path/to/file.py", None)
        assert result == "path/to/file.py"

    def test_make_relative_success(self, tmp_path):
        """Test make_relative with valid relative path."""
        file_path = tmp_path / "subdir" / "file.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        result = make_relative(str(file_path), str(tmp_path))
        assert result == "subdir/file.py"


class TestNormalizePath:
    """Tests for normalize_path function."""

    def test_normalize_path_backslashes(self):
        """Test that backslashes are converted to forward slashes."""
        result = normalize_path("path\\to\\file.py")
        assert result == "path/to/file.py"

    def test_normalize_path_trailing_slash(self):
        """Test that trailing slashes are removed."""
        result = normalize_path("path/to/dir/")
        assert result == "path/to/dir"

    def test_normalize_path_path_object(self):
        """Test normalization with Path object input."""
        result = normalize_path(Path("path/to/file.py"))
        assert result == "path/to/file.py"


class TestShouldSkipPath:
    """Tests for should_skip_path function."""

    def test_should_skip_venv(self):
        """Test that venv directories are skipped."""
        assert should_skip_path("venv/lib/python3.12/site.py") is True
        assert should_skip_path(".venv/lib/python3.12/site.py") is True

    def test_should_skip_site_packages(self):
        """Test that site-packages directories are skipped."""
        assert should_skip_path("/usr/lib/python3.12/site-packages/pkg/mod.py") is True

    def test_should_skip_pycache(self):
        """Test that __pycache__ directories are skipped."""
        assert should_skip_path("src/__pycache__/module.cpython-312.pyc") is True

    def test_should_skip_git(self):
        """Test that .git directories are skipped."""
        assert should_skip_path(".git/hooks/pre-commit") is True

    def test_should_skip_with_exclude_patterns(self):
        """Test that custom exclude patterns work."""
        assert should_skip_path("src/secret.py", exclude_patterns=["*secret*"]) is True
        assert should_skip_path("src/module.py", exclude_patterns=["*secret*"]) is False

    def test_should_not_skip_regular_path(self):
        """Test that regular paths are not skipped."""
        assert should_skip_path("src/module.py") is False
        assert should_skip_path("tests/test_foo.py") is False

    def test_should_skip_path_starting_with_skip_dir(self):
        """Test paths that start with a skip directory name."""
        assert should_skip_path("venv") is True
        assert should_skip_path(".venv") is True


class TestIsPythonFile:
    """Tests for is_python_file function."""

    def test_is_python_file_true(self):
        """Test that .py files return True."""
        assert is_python_file("module.py") is True
        assert is_python_file("path/to/module.py") is True
        assert is_python_file(Path("module.py")) is True

    def test_is_python_file_false(self):
        """Test that non-.py files return False."""
        assert is_python_file("module.txt") is False
        assert is_python_file("module.pyc") is False
        assert is_python_file("module") is False
