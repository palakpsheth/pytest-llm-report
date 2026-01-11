# SPDX-License-Identifier: MIT
"""Additional tests for options to increase coverage."""

from pathlib import Path

from pytest_llm_report.options import Config


class TestConfigAnnotations:
    """Test Config with different field combinations."""

    def test_all_output_paths(self):
        """Config with all output paths."""
        config = Config(
            report_html="report.html",
            report_json="report.json",
            report_pdf="report.pdf",
            report_evidence_bundle="bundle.zip",
            report_dependency_snapshot="deps.json",
        )
        assert config.report_html == "report.html"
        assert config.report_json == "report.json"
        assert config.report_pdf == "report.pdf"

    def test_llm_settings(self):
        """Config with LLM settings."""
        config = Config(
            provider="ollama",
            model="llama3.2",
            ollama_host="http://localhost:11434",
            llm_context_mode="balanced",
            llm_context_bytes=64000,
            llm_context_file_limit=20,
        )
        assert config.provider == "ollama"
        assert config.model == "llama3.2"
        assert config.llm_context_bytes == 64000

    def test_aggregation_settings(self):
        """Config with aggregation settings."""
        config = Config(
            aggregate_dir="/reports",
            aggregate_policy="merge",
            aggregate_run_id="run-123",
            aggregate_group_id="group-456",
            aggregate_include_history=True,
        )
        assert config.aggregate_dir == "/reports"
        assert config.aggregate_policy == "merge"
        assert config.aggregate_include_history is True

    def test_repo_root_path(self):
        """Config with repo root."""
        config = Config(repo_root=Path("/project"))
        assert config.repo_root == Path("/project")

    def test_include_globs(self):
        """Config with include globs."""
        config = Config(
            llm_context_include_globs=["*.py", "*.pyi"],
        )
        assert "*.py" in config.llm_context_include_globs

    def test_custom_exclude_globs(self):
        """Config with custom exclude globs."""
        config = Config(
            llm_context_exclude_globs=["*.pyc", "*.log"],
        )
        assert "*.pyc" in config.llm_context_exclude_globs

    def test_llm_param_settings(self):
        """Config with LLM param settings."""
        config = Config(
            llm_include_param_values=True,
            llm_param_value_max_chars=200,
        )
        assert config.llm_include_param_values is True
        assert config.llm_param_value_max_chars == 200

    def test_llm_execution_settings(self):
        """Config with LLM execution settings."""
        config = Config(
            llm_max_tests=50,
            llm_max_concurrency=8,
            llm_timeout_seconds=60,
            llm_cache_ttl_seconds=3600,
            cache_dir=".cache",
        )
        assert config.llm_max_tests == 50
        assert config.llm_max_concurrency == 8

    def test_coverage_settings(self):
        """Config with coverage settings."""
        config = Config(
            omit_tests_from_coverage=False,
            include_phase="all",
        )
        assert config.omit_tests_from_coverage is False
        assert config.include_phase == "all"

    def test_capture_settings(self):
        """Config with capture settings."""
        config = Config(
            capture_failed_output=True,
            capture_output_max_chars=8000,
        )
        assert config.capture_failed_output is True

    def test_invocation_settings(self):
        """Config with invocation settings."""
        config = Config(
            include_pytest_invocation=False,
            invocation_redact_patterns=[r"--api-key=\S+"],
        )
        assert config.include_pytest_invocation is False

    def test_compliance_settings(self):
        """Config with compliance settings."""
        config = Config(
            metadata_file="metadata.json",
            hmac_key_file="key.txt",
        )
        assert config.metadata_file == "metadata.json"
        assert config.hmac_key_file == "key.txt"

    def test_valid_phase_values(self):
        """All valid include_phase values should pass validation."""
        for phase in ("run", "setup", "teardown", "all"):
            config = Config(include_phase=phase)
            errors = config.validate()
            assert not any("include_phase" in e for e in errors)
