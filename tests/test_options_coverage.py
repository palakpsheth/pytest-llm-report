# SPDX-License-Identifier: MIT
"""Additional tests for options.py to increase coverage.

Targets uncovered lines in:
- Pyproject.toml loading paths (lines 300-401)
- Config validation edge cases (lines 227, 234)
- LiteLLM-specific config options
"""

from unittest.mock import MagicMock

from pytest_llm_report.options import Config, load_config


class TestPyprojectLoadingCoverage:
    """Test pyproject.toml loading to cover untested config keys."""

    def _make_mock_config(self, tmp_path):
        """Create a mock pytest config for testing."""
        mock = MagicMock()
        # Set all CLI options to None by default
        for attr in [
            "llm_report_html",
            "llm_report_json",
            "llm_report_pdf",
            "llm_evidence_bundle",
            "llm_dependency_snapshot",
            "llm_requests_per_minute",
            "llm_aggregate_dir",
            "llm_aggregate_policy",
            "llm_aggregate_run_id",
            "llm_aggregate_group_id",
            "llm_coverage_source",
            "llm_max_retries",
            # Core CLI Flags
            "llm_provider",
            "llm_model",
            "llm_context_mode",
            # New CLI options from our changes
            "llm_context_bytes",
            "llm_context_file_limit",
            "llm_max_tests",
            "llm_max_concurrency",
            "llm_timeout_seconds",
            "llm_capture_failed",
            "llm_ollama_host",
            "llm_litellm_api_base",
            "llm_litellm_api_key",
            "llm_litellm_token_refresh_command",
            "llm_litellm_token_refresh_interval",
            "llm_litellm_token_output_format",
            "llm_litellm_token_json_key",
            "llm_cache_dir",
            "llm_cache_ttl",
            "llm_metadata_file",
            "llm_hmac_key_file",
            "llm_include_params",
            "llm_strip_docstrings",
            "llm_prompt_tier",
            "llm_batch_parametrized",
            "llm_context_compression",
        ]:
            setattr(mock.option, attr, None)
        mock.rootpath = tmp_path
        return mock

    def test_load_litellm_api_base(self, tmp_path):
        """Test loading litellm_api_base from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "litellm"
litellm_api_base = "https://api.example.com"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.litellm_api_base == "https://api.example.com"

    def test_load_litellm_api_key(self, tmp_path):
        """Test loading litellm_api_key from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "litellm"
litellm_api_key = "sk-test-key"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.litellm_api_key == "sk-test-key"

    def test_load_litellm_token_refresh_command(self, tmp_path):
        """Test loading litellm_token_refresh_command from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "litellm"
litellm_token_refresh_command = "gcloud auth print-access-token"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.litellm_token_refresh_command == "gcloud auth print-access-token"

    def test_load_litellm_token_refresh_interval(self, tmp_path):
        """Test loading litellm_token_refresh_interval from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "litellm"
litellm_token_refresh_interval = 1800
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.litellm_token_refresh_interval == 1800

    def test_load_litellm_token_output_format(self, tmp_path):
        """Test loading litellm_token_output_format from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "litellm"
litellm_token_output_format = "json"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.litellm_token_output_format == "json"

    def test_load_litellm_token_json_key(self, tmp_path):
        """Test loading litellm_token_json_key from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "litellm"
litellm_token_json_key = "access_token"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.litellm_token_json_key == "access_token"

    def test_load_context_bytes(self, tmp_path):
        """Test loading context_bytes from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
context_bytes = 64000
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_context_bytes == 64000

    def test_load_context_file_limit(self, tmp_path):
        """Test loading context_file_limit from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
context_file_limit = 25
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_context_file_limit == 25

    def test_load_context_include_globs(self, tmp_path):
        """Test loading context_include_globs from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
context_include_globs = ["*.py", "*.pyi"]
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_context_include_globs == ["*.py", "*.pyi"]

    def test_load_context_exclude_globs(self, tmp_path):
        """Test loading context_exclude_globs from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
context_exclude_globs = ["*.pyc", "*.log"]
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_context_exclude_globs == ["*.pyc", "*.log"]

    def test_load_include_param_values(self, tmp_path):
        """Test loading include_param_values from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
include_param_values = true
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_include_param_values is True

    def test_load_param_value_max_chars(self, tmp_path):
        """Test loading param_value_max_chars from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
param_value_max_chars = 250
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_param_value_max_chars == 250

    def test_load_max_concurrency(self, tmp_path):
        """Test loading max_concurrency from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
max_concurrency = 4
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_max_concurrency == 4

    def test_load_timeout_seconds(self, tmp_path):
        """Test loading timeout_seconds from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
timeout_seconds = 60
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_timeout_seconds == 60

    def test_load_cache_ttl_seconds(self, tmp_path):
        """Test loading cache_ttl_seconds from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
cache_ttl_seconds = 7200
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_cache_ttl_seconds == 7200

    def test_load_cache_dir(self, tmp_path):
        """Test loading cache_dir from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
cache_dir = ".my_cache"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.cache_dir == ".my_cache"

    def test_load_omit_tests_from_coverage(self, tmp_path):
        """Test loading omit_tests_from_coverage from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
omit_tests_from_coverage = false
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.omit_tests_from_coverage is False

    def test_load_include_phase(self, tmp_path):
        """Test loading include_phase from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
include_phase = "all"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.include_phase == "all"

    def test_load_report_collect_only(self, tmp_path):
        """Test loading report_collect_only from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
report_collect_only = false
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.report_collect_only is False

    def test_load_capture_failed_output(self, tmp_path):
        """Test loading capture_failed_output from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
capture_failed_output = true
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.capture_failed_output is True

    def test_load_capture_output_max_chars(self, tmp_path):
        """Test loading capture_output_max_chars from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
capture_output_max_chars = 8000
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.capture_output_max_chars == 8000

    def test_load_include_pytest_invocation(self, tmp_path):
        """Test loading include_pytest_invocation from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
include_pytest_invocation = false
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.include_pytest_invocation is False

    def test_load_invocation_redact_patterns(self, tmp_path):
        """Test loading invocation_redact_patterns from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
invocation_redact_patterns = ["--secret=\\\\S+"]
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.invocation_redact_patterns == ["--secret=\\S+"]

    def test_load_aggregate_include_history(self, tmp_path):
        """Test loading aggregate_include_history from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
aggregate_include_history = true
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.aggregate_include_history is True

    def test_load_metadata_file(self, tmp_path):
        """Test loading metadata_file from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
metadata_file = "custom_metadata.yaml"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.metadata_file == "custom_metadata.yaml"

    def test_load_hmac_key_file(self, tmp_path):
        """Test loading hmac_key_file from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
hmac_key_file = "signature.key"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.hmac_key_file == "signature.key"

    def test_load_ollama_host(self, tmp_path):
        """Test loading ollama_host from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "ollama"
ollama_host = "http://localhost:12345"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.ollama_host == "http://localhost:12345"

    def test_load_max_tests(self, tmp_path):
        """Test loading max_tests from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
max_tests = 100
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.llm_max_tests == 100

    def test_load_aggregate_policy_from_pyproject(self, tmp_path):
        """Test loading aggregate_policy from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
aggregate_policy = "all"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.aggregate_policy == "all"

    def test_load_malformed_pyproject(self, tmp_path):
        """Test handling of malformed pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("this is not valid TOML [[[")
        # Should not raise, should fallback to defaults
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.provider == "none"

    def test_load_all_config_keys_combined(self, tmp_path):
        """Test loading all config keys in a single pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
provider = "litellm"
model = "gpt-4"
ollama_host = "http://custom:11434"
litellm_api_base = "https://api.test.com"
litellm_api_key = "test-key"
litellm_token_refresh_command = "token-cmd"
litellm_token_refresh_interval = 3000
litellm_token_output_format = "json"
litellm_token_json_key = "tok"
context_mode = "complete"
context_bytes = 50000
context_file_limit = 15
context_include_globs = ["src/**/*.py"]
context_exclude_globs = ["test/**"]
include_param_values = true
param_value_max_chars = 150
max_tests = 50
max_concurrency = 2
requests_per_minute = 8
timeout_seconds = 45
max_retries = 5
cache_ttl_seconds = 3600
cache_dir = ".cache"
omit_tests_from_coverage = false
include_phase = "setup"
report_collect_only = false
capture_failed_output = true
capture_output_max_chars = 5000
include_pytest_invocation = false
invocation_redact_patterns = ["--pass=\\\\S+"]
aggregate_policy = "merge"
aggregate_include_history = true
metadata_file = "meta.json"
hmac_key_file = "key.pem"
""")
        cfg = load_config(self._make_mock_config(tmp_path))

        assert cfg.provider == "litellm"
        assert cfg.model == "gpt-4"
        assert cfg.ollama_host == "http://custom:11434"
        assert cfg.litellm_api_base == "https://api.test.com"
        assert cfg.litellm_api_key == "test-key"
        assert cfg.litellm_token_refresh_command == "token-cmd"
        assert cfg.litellm_token_refresh_interval == 3000
        assert cfg.litellm_token_output_format == "json"
        assert cfg.litellm_token_json_key == "tok"
        assert cfg.llm_context_mode == "complete"
        assert cfg.llm_context_bytes == 50000
        assert cfg.llm_context_file_limit == 15
        assert cfg.llm_context_include_globs == ["src/**/*.py"]
        assert cfg.llm_context_exclude_globs == ["test/**"]
        assert cfg.llm_include_param_values is True
        assert cfg.llm_param_value_max_chars == 150
        assert cfg.llm_max_tests == 50
        assert cfg.llm_max_concurrency == 2
        assert cfg.llm_requests_per_minute == 8
        assert cfg.llm_timeout_seconds == 45
        assert cfg.llm_max_retries == 5
        assert cfg.llm_cache_ttl_seconds == 3600
        assert cfg.cache_dir == ".cache"
        assert cfg.omit_tests_from_coverage is False
        assert cfg.include_phase == "setup"
        assert cfg.report_collect_only is False
        assert cfg.capture_failed_output is True
        assert cfg.capture_output_max_chars == 5000
        assert cfg.include_pytest_invocation is False
        assert cfg.aggregate_policy == "merge"
        assert cfg.aggregate_include_history is True
        assert cfg.metadata_file == "meta.json"
        assert cfg.hmac_key_file == "key.pem"


class TestConfigValidationCoverage:
    """Additional validation tests for uncovered paths."""

    def test_validate_invalid_token_output_format(self):
        """Test validation with invalid token output format."""
        cfg = Config(litellm_token_output_format="xml")
        errors = cfg.validate()
        assert any("litellm_token_output_format" in e for e in errors)

    def test_validate_token_refresh_interval_too_short(self):
        """Test validation when token refresh interval is too short."""
        cfg = Config(litellm_token_refresh_interval=30)
        errors = cfg.validate()
        assert any(
            "litellm_token_refresh_interval must be at least 60" in e for e in errors
        )

    def test_validate_valid_litellm_config(self):
        """Test validation passes with valid LiteLLM config."""
        cfg = Config(
            provider="litellm",
            litellm_token_output_format="text",
            litellm_token_refresh_interval=3600,
        )
        errors = cfg.validate()
        assert not errors


class TestCliOverrides:
    """Test CLI option overrides for coverage."""

    def _make_mock_config(self, tmp_path):
        """Create a mock pytest config for testing."""
        mock = MagicMock()
        for attr in [
            "llm_report_html",
            "llm_report_json",
            "llm_report_pdf",
            "llm_evidence_bundle",
            "llm_dependency_snapshot",
            "llm_requests_per_minute",
            "llm_aggregate_dir",
            "llm_aggregate_policy",
            "llm_aggregate_run_id",
            "llm_aggregate_group_id",
            "llm_coverage_source",
            "llm_max_retries",
        ]:
            setattr(mock.option, attr, None)
        mock.rootpath = tmp_path
        return mock

    def test_cli_report_json(self, tmp_path):
        """Test CLI override for report JSON."""
        mock = self._make_mock_config(tmp_path)
        mock.option.llm_report_json = "output.json"
        cfg = load_config(mock)
        assert cfg.report_json == "output.json"

    def test_cli_report_pdf(self, tmp_path):
        """Test CLI override for report PDF."""
        mock = self._make_mock_config(tmp_path)
        mock.option.llm_report_pdf = "output.pdf"
        cfg = load_config(mock)
        assert cfg.report_pdf == "output.pdf"

    def test_cli_evidence_bundle(self, tmp_path):
        """Test CLI override for evidence bundle."""
        mock = self._make_mock_config(tmp_path)
        mock.option.llm_evidence_bundle = "bundle.zip"
        cfg = load_config(mock)
        assert cfg.report_evidence_bundle == "bundle.zip"

    def test_cli_dependency_snapshot(self, tmp_path):
        """Test CLI override for dependency snapshot."""
        mock = self._make_mock_config(tmp_path)
        mock.option.llm_dependency_snapshot = "deps.json"
        cfg = load_config(mock)
        assert cfg.report_dependency_snapshot == "deps.json"


class TestValidationCoverageExtended:
    """Additional validation tests for uncovered branches."""

    def test_validate_invalid_prompt_tier(self):
        """Test validation with invalid prompt_tier."""
        cfg = Config(prompt_tier="extra_verbose")
        errors = cfg.validate()
        assert any("Invalid prompt_tier" in e for e in errors)

    def test_validate_invalid_context_compression(self):
        """Test validation with invalid context_compression."""
        cfg = Config(context_compression="gzip")
        errors = cfg.validate()
        assert any("Invalid context_compression" in e for e in errors)

    def test_validate_batch_max_tests_too_small(self):
        """Test validation with batch_max_tests < 1."""
        cfg = Config(batch_max_tests=0)
        errors = cfg.validate()
        assert any("batch_max_tests must be at least 1" in e for e in errors)

    def test_validate_context_line_padding_negative(self):
        """Test validation with negative context_line_padding."""
        cfg = Config(context_line_padding=-1)
        errors = cfg.validate()
        assert any("context_line_padding must be 0 or positive" in e for e in errors)


class TestPyprojectTokenOptimization:
    """Tests for token optimization config loading from pyproject.toml."""

    def _make_mock_config(self, tmp_path):
        """Create a mock pytest config for testing."""
        mock = MagicMock()
        for attr in [
            "llm_report_html",
            "llm_report_json",
            "llm_report_pdf",
            "llm_evidence_bundle",
            "llm_dependency_snapshot",
            "llm_requests_per_minute",
            "llm_aggregate_dir",
            "llm_aggregate_policy",
            "llm_aggregate_run_id",
            "llm_aggregate_group_id",
            "llm_coverage_source",
            "llm_max_retries",
            "llm_provider",
            "llm_model",
            "llm_context_mode",
            "llm_prompt_tier",
            "llm_batch_parametrized",
            "llm_context_compression",
        ]:
            setattr(mock.option, attr, None)
        mock.rootpath = tmp_path
        return mock

    def test_load_prompt_tier(self, tmp_path):
        """Test loading prompt_tier from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
prompt_tier = "minimal"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.prompt_tier == "minimal"

    def test_load_batch_parametrized_tests(self, tmp_path):
        """Test loading batch_parametrized_tests from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
batch_parametrized_tests = false
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.batch_parametrized_tests is False

    def test_load_batch_max_tests(self, tmp_path):
        """Test loading batch_max_tests from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
batch_max_tests = 10
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.batch_max_tests == 10

    def test_load_context_compression(self, tmp_path):
        """Test loading context_compression from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
context_compression = "none"
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.context_compression == "none"

    def test_load_context_line_padding(self, tmp_path):
        """Test loading context_line_padding from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[tool.pytest_llm_report]
context_line_padding = 5
""")
        cfg = load_config(self._make_mock_config(tmp_path))
        assert cfg.context_line_padding == 5
