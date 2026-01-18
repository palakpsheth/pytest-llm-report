# SPDX-License-Identifier: MIT
"""Additional tests for prompts.py to increase coverage.

Targets uncovered lines:
- Line 80: Empty nodeid (no parts)
- Line 114: Breaking out of test function extraction loop
- Line 142: Max bytes limit reached
- Line 146: File doesn't exist in coverage
- Line 149: File matches exclude pattern
"""

from pytest_llm_report.models import CoverageEntry, TestCaseResult
from pytest_llm_report.options import Config
from pytest_llm_report.prompts import ContextAssembler


class TestContextAssemblerEdgeCases:
    """Tests for ContextAssembler edge cases."""

    def test_get_test_source_empty_nodeid(self, tmp_path):
        """Test _get_test_source with empty nodeid returns empty string."""
        config = Config(repo_root=tmp_path)
        assembler = ContextAssembler(config)

        # Empty string will have no parts after split
        result = assembler._get_test_source("", tmp_path)
        assert result == ""

    def test_get_test_source_file_not_exists(self, tmp_path):
        """Test _get_test_source with non-existent file."""
        config = Config(repo_root=tmp_path)
        assembler = ContextAssembler(config)

        result = assembler._get_test_source("nonexistent.py::test_foo", tmp_path)
        assert result == ""

    def test_get_test_source_with_class(self, tmp_path):
        """Test _get_test_source extracts function with proper indentation."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
class TestFoo:
    def test_bar(self):
        assert True
        assert 1 == 1

    def test_other(self):
        pass
""")
        config = Config(repo_root=tmp_path)
        assembler = ContextAssembler(config)

        result = assembler._get_test_source(
            "test_example.py::TestFoo::test_bar", tmp_path
        )
        assert "def test_bar" in result
        assert "assert True" in result
        assert "test_other" not in result

    def test_get_test_source_extraction_stops_at_next_def(self, tmp_path):
        """Test that source extraction stops at next function definition."""
        test_file = tmp_path / "test_stop.py"
        test_file.write_text("""def test_first():
    assert True

def test_second():
    assert False
""")
        config = Config(repo_root=tmp_path)
        assembler = ContextAssembler(config)

        result = assembler._get_test_source("test_stop.py::test_first", tmp_path)
        assert "def test_first" in result
        assert "test_second" not in result

    def test_balanced_context_max_bytes_limit(self, tmp_path):
        """Test that balanced context respects max bytes limit."""
        # Create a source file
        src_file = tmp_path / "large_module.py"
        src_file.write_text("x = 1\n" * 1000)  # ~6000 bytes

        config = Config(
            repo_root=tmp_path,
            llm_context_mode="balanced",
            llm_context_bytes=100,  # Very small limit
            llm_context_file_limit=10,
        )
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(
                    file_path="large_module.py", line_ranges="1-100", line_count=100
                )
            ],
        )

        context = assembler._get_balanced_context(test, tmp_path)

        # Content should be truncated
        assert (
            len(context.get("large_module.py", "")) <= 120
        )  # Some buffer for truncation message
        if "large_module.py" in context:
            assert "truncated" in context["large_module.py"]

    def test_balanced_context_file_not_exists(self, tmp_path):
        """Test balanced context skips non-existent files."""
        config = Config(
            repo_root=tmp_path,
            llm_context_mode="balanced",
        )
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(
                    file_path="nonexistent.py", line_ranges="1-10", line_count=10
                )
            ],
        )

        context = assembler._get_balanced_context(test, tmp_path)
        assert context == {}

    def test_balanced_context_excludes_patterns(self, tmp_path):
        """Test balanced context excludes files matching exclude patterns."""
        # Create a file that matches exclude pattern
        secret_file = tmp_path / "secret_config.py"
        secret_file.write_text("api_key = 'secret123'")

        config = Config(
            repo_root=tmp_path,
            llm_context_mode="balanced",
            llm_context_exclude_globs=["*secret*"],
        )
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(
                    file_path="secret_config.py", line_ranges="1", line_count=1
                )
            ],
        )

        context = assembler._get_balanced_context(test, tmp_path)
        assert context == {}

    def test_balanced_context_no_coverage(self, tmp_path):
        """Test balanced context with no coverage returns empty dict."""
        config = Config(repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test.py::test_foo",
            outcome="passed",
            coverage=[],
        )

        context = assembler._get_balanced_context(test, tmp_path)
        assert context == {}

    def test_balanced_context_reaches_max_bytes_before_file(self, tmp_path):
        """Test that loop exits when max bytes is reached before processing file."""
        # Create files
        file1 = tmp_path / "file1.py"
        file1.write_text("content1 = 1")
        file2 = tmp_path / "file2.py"
        file2.write_text("content2 = 2")

        config = Config(
            repo_root=tmp_path,
            llm_context_mode="balanced",
            llm_context_bytes=5,  # Very small - will hit limit after first file
            llm_context_file_limit=10,
        )
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(file_path="file1.py", line_ranges="1", line_count=1),
                CoverageEntry(file_path="file2.py", line_ranges="1", line_count=1),
            ],
        )

        context = assembler._get_balanced_context(test, tmp_path)

        # Should only have first file (truncated) or neither
        assert len(context) <= 1

    def test_complete_context_delegates_to_balanced(self, tmp_path):
        """Test that complete context uses same logic as balanced."""
        file1 = tmp_path / "module.py"
        file1.write_text("x = 1")

        config = Config(repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(file_path="module.py", line_ranges="1", line_count=1)
            ],
        )

        context = assembler._get_complete_context(test, tmp_path)
        assert "module.py" in context

    def test_assemble_minimal_mode(self, tmp_path):
        """Test assemble in minimal mode returns no context files."""
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("def test_foo():\n    pass")

        config = Config(
            repo_root=tmp_path,
            llm_context_mode="minimal",
        )
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_foo.py::test_foo",
            outcome="passed",
        )

        test_source, context_files = assembler.assemble(test, tmp_path)
        assert context_files == {}
        assert "def test_foo" in test_source

    def test_assemble_with_context_override(self, tmp_path):
        """Test assemble respects llm_context_override from test."""
        test_file = tmp_path / "test_bar.py"
        test_file.write_text("def test_bar():\n    pass")

        module_file = tmp_path / "module.py"
        module_file.write_text("y = 2")

        config = Config(
            repo_root=tmp_path,
            llm_context_mode="minimal",  # Default is minimal
        )
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_bar.py::test_bar",
            outcome="passed",
            llm_context_override="balanced",  # Override to balanced
            coverage=[
                CoverageEntry(file_path="module.py", line_ranges="1", line_count=1)
            ],
        )

        test_source, context_files = assembler.assemble(test, tmp_path)
        # Should use balanced mode due to override
        assert "module.py" in context_files
