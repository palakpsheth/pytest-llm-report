from pytest_llm_report.models import CoverageEntry, TestCaseResult
from pytest_llm_report.options import Config
from pytest_llm_report.prompts import ContextAssembler


class TestContextAssembler:
    def test_assemble_minimal_context(self, tmp_path):
        config = Config(llm_context_mode="minimal", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test_file = tmp_path / "test_a.py"
        test_file.write_text("def test_1():\n    assert True\n")

        test_result = TestCaseResult(nodeid="test_a.py::test_1", outcome="passed")

        source, context = assembler.assemble(test_result)
        assert "test_1" in source
        assert context == {}

    def test_assemble_balanced_context(self, tmp_path):
        config = Config(llm_context_mode="balanced", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test_file = tmp_path / "test_a.py"
        test_file.write_text("def test_1():\n    pass\n")

        dep_file = tmp_path / "utils.py"
        dep_file.write_text("def util():\n    return 1\n")

        test_result = TestCaseResult(
            nodeid="test_a.py::test_1",
            outcome="passed",
            coverage=[
                CoverageEntry(file_path="utils.py", line_ranges="1-2", line_count=2)
            ],
        )

        source, context = assembler.assemble(test_result)
        assert "utils.py" in context
        assert "def util()" in context["utils.py"]

    def test_assemble_complete_context(self, tmp_path):
        config = Config(llm_context_mode="complete", repo_root=tmp_path)
        assembler = ContextAssembler(config)

        test_file = tmp_path / "test_a.py"
        test_file.write_text("def test_1():\n    pass\n")

        test_result = TestCaseResult(nodeid="test_a.py::test_1", outcome="passed")

        source, context = assembler.assemble(test_result)
        assert "test_1" in source

    def test_get_test_source_edge_cases(self, tmp_path):
        config = Config(repo_root=tmp_path)
        assembler = ContextAssembler(config)

        # Non-existent file
        assert assembler._get_test_source("none.py::test", tmp_path) == ""

        # Nested test name with params
        test_file = tmp_path / "test_p.py"
        test_file.write_text("def test_param(x):\n    assert x\n")
        source = assembler._get_test_source("test_p.py::test_param[1]", tmp_path)
        assert "def test_param" in source

    def test_should_exclude(self):
        config = Config(llm_context_exclude_globs=["*.pyc", "secret/*"])
        assembler = ContextAssembler(config)

        assert assembler._should_exclude("test.pyc") is True
        assert assembler._should_exclude("secret/key.txt") is True
        assert assembler._should_exclude("public/readme.md") is False

    def test_balanced_context_limits(self, tmp_path):
        config = Config(
            llm_context_mode="balanced",
            repo_root=tmp_path,
            llm_context_bytes=20,
            llm_context_file_limit=1,
        )
        assembler = ContextAssembler(config)

        f1 = tmp_path / "f1.py"
        f1.write_text("Long content that exceeds 20 bytes")

        test_result = TestCaseResult(
            nodeid="t.py::t",
            outcome="passed",
            coverage=[CoverageEntry(file_path="f1.py", line_ranges="1", line_count=1)],
        )

        _, context = assembler.assemble(test_result)
        assert "f1.py" in context
        assert "... truncated" in context["f1.py"]
        assert len(context["f1.py"]) <= 40  # 20 bytes + truncation message

    def test_complete_context_limits_override(self, tmp_path):
        # Config has small limits
        config = Config(
            llm_context_mode="complete",
            repo_root=tmp_path,
            llm_context_bytes=20,  # Should be ignored in complete mode
            llm_context_file_limit=1,
        )
        assembler = ContextAssembler(config)

        f1 = tmp_path / "f1.py"
        content = "Long content that exceeds 20 bytes"
        f1.write_text(content)

        test_result = TestCaseResult(
            nodeid="t.py::t",
            outcome="passed",
            coverage=[CoverageEntry(file_path="f1.py", line_ranges="1", line_count=1)],
        )

        _, context = assembler.assemble(test_result)
        assert "f1.py" in context
        # Should NOT be truncated despite the 20 byte config limit
        assert context["f1.py"] == content
        assert "truncated" not in context["f1.py"]
