# SPDX-License-Identifier: MIT
"""Tests for prompts module."""

from pytest_llm_report.models import CoverageEntry, TestCaseResult
from pytest_llm_report.options import Config
from pytest_llm_report.prompts import ContextAssembler


class TestContextAssembler:
    """Tests for ContextAssembler."""

    def test_create_assembler(self):
        """Should create with config."""
        config = Config()
        assembler = ContextAssembler(config)
        assert assembler.config is config

    def test_minimal_mode_returns_empty_context(self, tmp_path):
        """Minimal mode should return empty context files."""
        config = Config(llm_context_mode="minimal", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        # Create a test file
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("def test_foo(): pass")

        test = TestCaseResult(nodeid="test_foo.py::test_foo", outcome="passed")
        source, context = assembler.assemble(test, tmp_path)

        assert context == {}  # Minimal mode has no context

    def test_balanced_mode_includes_coverage(self, tmp_path):
        """Balanced mode should include covered files."""
        # Create source file
        src_file = tmp_path / "src" / "module.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("def hello(): return 'world'")

        config = Config(llm_context_mode="balanced", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_foo.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(file_path="src/module.py", line_ranges="1", line_count=1)
            ],
        )
        source, context = assembler.assemble(test, tmp_path)

        assert "src/module.py" in context
        assert "hello" in context["src/module.py"]

    def test_context_override_from_marker(self, tmp_path):
        """Should use context override from test marker."""
        config = Config(llm_context_mode="minimal", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_foo.py::test_foo",
            outcome="passed",
            llm_context_override="balanced",
            coverage=[],
        )
        # With override to balanced but no coverage, still returns empty
        source, context = assembler.assemble(test, tmp_path)
        assert context == {}


class TestContextAssemblerExcludes:
    """Tests for context exclusion."""

    def test_excludes_secret_files(self, tmp_path):
        """Should exclude files matching secret patterns."""
        # Create a secret file
        secret_file = tmp_path / "config_secret.py"
        secret_file.write_text("API_KEY = 'xxx'")

        config = Config(llm_context_mode="balanced", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_foo.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(
                    file_path="config_secret.py", line_ranges="1", line_count=1
                )
            ],
        )
        source, context = assembler.assemble(test, tmp_path)

        # Should be excluded due to "*secret*" pattern
        assert "config_secret.py" not in context


class TestContextAssemblerComplete:
    """Tests for complete context mode."""

    def test_complete_mode_includes_coverage(self, tmp_path):
        """Complete mode should include all covered files."""
        # Create source files
        src_file = tmp_path / "src" / "module.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("def hello(): return 'world'")

        other_file = tmp_path / "src" / "utils.py"
        other_file.write_text("def helper(): return 42")

        config = Config(llm_context_mode="complete", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_foo.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(file_path="src/module.py", line_ranges="1", line_count=1),
                CoverageEntry(file_path="src/utils.py", line_ranges="1", line_count=1),
            ],
        )
        source, context = assembler.assemble(test, tmp_path)

        assert "src/module.py" in context
        assert "src/utils.py" in context


class TestContextAssemblerSource:
    """Tests for test source extraction."""

    def test_get_test_source_simple(self, tmp_path):
        """Should extract source for a simple test function."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text('''
def test_simple():
    """Simple test docstring."""
    x = 1
    assert x == 1
''')

        config = Config(llm_context_mode="minimal", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(nodeid="test_example.py::test_simple", outcome="passed")
        source, context = assembler.assemble(test, tmp_path)

        assert "def test_simple" in source
        assert "assert x == 1" in source

    def test_get_test_source_class_method(self, tmp_path):
        """Should extract source for a class method test."""
        test_file = tmp_path / "test_class.py"
        test_file.write_text('''
class TestClass:
    def test_method(self):
        """Method test."""
        assert True
''')

        config = Config(llm_context_mode="minimal", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_class.py::TestClass::test_method", outcome="passed"
        )
        source, context = assembler.assemble(test, tmp_path)

        assert "def test_method" in source
        assert "assert True" in source

    def test_get_test_source_parametrized(self, tmp_path):
        """Should extract source for parametrized test, stripping param suffix."""
        test_file = tmp_path / "test_param.py"
        test_file.write_text('''
def test_param(x):
    """Parametrized test."""
    assert x > 0
''')

        config = Config(llm_context_mode="minimal", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(nodeid="test_param.py::test_param[1]", outcome="passed")
        source, context = assembler.assemble(test, tmp_path)

        assert "def test_param" in source
        assert "assert x > 0" in source

    def test_get_test_source_nonexistent_file(self, tmp_path):
        """Should return empty for nonexistent file."""
        config = Config(llm_context_mode="minimal", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(nodeid="nonexistent.py::test_foo", outcome="passed")
        source, context = assembler.assemble(test, tmp_path)

        assert source == ""

    def test_get_test_source_empty_nodeid(self, tmp_path):
        """Should return empty for empty nodeid."""
        config = Config(llm_context_mode="minimal", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(nodeid="", outcome="passed")
        source, context = assembler.assemble(test, tmp_path)

        assert source == ""


class TestContextAssemblerLimits:
    """Tests for context size limits."""

    def test_context_truncated_at_max_bytes(self, tmp_path):
        """Should truncate context at max_bytes limit."""
        # Create a large source file
        src_file = tmp_path / "large.py"
        large_content = "x = 1\n" * 10000  # ~60KB
        src_file.write_text(large_content)

        config = Config(
            llm_context_mode="balanced",
            llm_context_bytes=1000,  # Only allow 1KB
            repo_root=tmp_path,
        )
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_foo.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(file_path="large.py", line_ranges="1", line_count=1)
            ],
        )
        source, context = assembler.assemble(test, tmp_path)

        # Should be truncated
        assert "large.py" in context
        assert len(context["large.py"]) <= 1050  # Allow some margin for truncation msg
        assert "truncated" in context["large.py"]

    def test_context_limited_by_file_count(self, tmp_path):
        """Should limit context by file count."""
        # Create multiple source files
        for i in range(15):
            src_file = tmp_path / f"module_{i}.py"
            src_file.write_text(f"var_{i} = {i}")

        config = Config(
            llm_context_mode="balanced",
            llm_context_file_limit=5,  # Only allow 5 files
            repo_root=tmp_path,
        )
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_foo.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(file_path=f"module_{i}.py", line_ranges="1", line_count=1)
                for i in range(15)
            ],
        )
        source, context = assembler.assemble(test, tmp_path)

        # Should only have 5 files
        assert len(context) <= 5

    def test_context_skips_nonexistent_files(self, tmp_path):
        """Should skip coverage entries for nonexistent files."""
        # Create one file, leave another missing
        src_file = tmp_path / "exists.py"
        src_file.write_text("exists = True")

        config = Config(llm_context_mode="balanced", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(
            nodeid="test_foo.py::test_foo",
            outcome="passed",
            coverage=[
                CoverageEntry(file_path="exists.py", line_ranges="1", line_count=1),
                CoverageEntry(file_path="missing.py", line_ranges="1", line_count=1),
            ],
        )
        source, context = assembler.assemble(test, tmp_path)

        assert "exists.py" in context
        assert "missing.py" not in context


class TestContextAssemblerRepoRoot:
    """Tests for repo_root handling."""

    def test_uses_config_repo_root(self, tmp_path):
        """Should use repo_root from config if not provided."""
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("def test_foo(): pass")

        config = Config(llm_context_mode="minimal", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test = TestCaseResult(nodeid="test_foo.py::test_foo", outcome="passed")
        source, context = assembler.assemble(test)  # No repo_root arg

        assert "def test_foo" in source

    def test_uses_cwd_if_no_repo_root(self, tmp_path, monkeypatch):
        """Should use cwd if no repo_root in config or arg."""
        test_file = tmp_path / "test_bar.py"
        test_file.write_text("def test_bar(): pass")

        # Change to tmp_path
        monkeypatch.chdir(tmp_path)

        config = Config(llm_context_mode="minimal", repo_root=None)
        assembler = ContextAssembler(config)

        test = TestCaseResult(nodeid="test_bar.py::test_bar", outcome="passed")
        source, context = assembler.assemble(test)  # No repo_root arg

        assert "def test_bar" in source
