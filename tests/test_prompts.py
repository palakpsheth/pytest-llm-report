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
