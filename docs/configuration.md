# Configuration Reference

Complete configuration reference for pytest-llm-report.

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| **Output Paths** |
| `--llm-report PATH` | HTML report output path | None |
| `--llm-report-json PATH` | JSON report output path | None |
| `--llm-pdf PATH` | PDF report output (requires Playwright) | None |
| `--llm-evidence-bundle PATH` | Evidence bundle zip output | None |
| `--llm-dependency-snapshot PATH` | Dependency snapshot output | None |
| **Core LLM Configuration** |
| `--llm-provider NAME` | LLM provider (ollama, litellm, gemini, none) | None |
| `--llm-model NAME` | LLM model name | None |
| `--llm-context-mode MODE` | Context mode (minimal, balanced, complete) | None |
| **Context Controls** |
| `--llm-context-bytes N` | Maximum bytes for context window | 32000 |
| `--llm-context-file-limit N` | Maximum number of files in context | 10 |
| **Execution Controls** |
| `--llm-max-tests N` | Maximum tests to annotate (0=unlimited) | 0 |
| `--llm-max-concurrency N` | Maximum concurrent LLM requests | 1 |
| `--llm-timeout-seconds N` | Timeout for LLM requests in seconds | 30 |
| `--llm-requests-per-minute N` | LLM request rate limit | 5 |
| `--llm-max-retries N` | Maximum retries for transient errors | 10 |
| **Behavior Controls** |
| `--llm-capture-failed` | Capture stdout/stderr for failed tests | **enabled** |
| `--llm-no-capture-failed` | Disable capturing failed test output | - |
| **Provider-Specific** |
| `--llm-ollama-host URL` | Ollama server URL | http://127.0.0.1:11434 |
| `--llm-litellm-api-base URL` | LiteLLM API base URL for proxy | None |
| `--llm-litellm-api-key KEY` | LiteLLM API key override | None |
| `--llm-litellm-token-refresh-command CMD` | Command to fetch fresh auth token | None |
| `--llm-litellm-token-refresh-interval N` | Token refresh interval in seconds | 3300 |
| `--llm-litellm-token-output-format FMT` | Token command output format (text, json) | text |
| `--llm-litellm-token-json-key KEY` | JSON key for token extraction | token |
| **Maintenance** |
| `--llm-cache-dir DIR` | Directory for LLM cache | .pytest_llm_cache |
| `--llm-cache-ttl N` | Cache TTL in seconds | 86400 |
| **Metadata** |
| `--llm-metadata-file PATH` | Path to custom metadata JSON/YAML file | None |
| `--llm-hmac-key-file PATH` | Path to HMAC key file for signatures | None |
| **Content Optimization** |
| `--llm-include-params` | Include test parameter values in context | disabled |
| `--llm-strip-docstrings` | Strip docstrings from context | **enabled** |
| `--llm-no-strip-docstrings` | Disable docstring stripping | - |
| **Token Optimization** |
| `--llm-prompt-tier TIER` | System prompt tier (minimal, standard, auto) | auto |
| `--llm-batch-parametrized` | Group parametrized tests for single annotation | enabled |
| `--llm-no-batch-parametrized` | Disable test batching | - |
| `--llm-context-compression MODE` | Context compression (none, lines) | lines |
| **Aggregation** |
| `--llm-aggregate-dir DIR` | Directory with reports to [aggregate](aggregation.md) | None |
| `--llm-aggregate-policy POLICY` | Aggregation policy (latest, merge, all) | latest |
| `--llm-aggregate-run-id ID` | Unique run ID | Auto-generated |
| `--llm-aggregate-group-id ID` | Group ID for related runs | None |
| `--llm-coverage-source PATH` | Path to .coverage file/dir to inject into report | None |

> **Tip**: Run `pytest --help` to see usage examples for each option.

## pyproject.toml Configuration

Configure the plugin in the `[tool.pytest_llm_report]` section of your `pyproject.toml`.

### General Settings

| Key | Description | Default |
|-----|-------------|---------|
| `provider` | LLM provider to use (`none`, `ollama`, `litellm`, `gemini`) | `"none"` |
| `model` | Model name to use (provider-dependent) | `""` |
| `ollama_host` | URL of the Ollama server | `"http://127.0.0.1:11434"` |
| `cache_dir` | Directory for caching LLM responses | `".pytest_llm_cache"` |
| `metadata_file` | Path to custom metadata file (JSON/YAML) | `None` |

### LiteLLM Settings

Settings specific to the `litellm` provider.

| Key | Description | Default |
|-----|-------------|---------|
| `litellm_api_base` | Custom API base URL (e.g., for proxies) | `None` |
| `litellm_api_key` | Static API key override | `None` |
| `litellm_token_refresh_command` | CLI command to fetch a fresh auth token | `None` |
| `litellm_token_refresh_interval` | Refresh interval in seconds (min 60) | `3300` (55 min) |
| `litellm_token_output_format` | Token command output format (`text` or `json`) | `"text"` |
| `litellm_token_json_key` | Key to extract token from if format is `json` | `"token"` |

### LLM Execution Control

| Key | Description | Default |
|-----|-------------|---------|
| `max_tests` | Maximum number of tests to annotate (0 = unlimited) | `0` |
| `max_concurrency` | Maximum concurrent LLM requests | `1` |
| `requests_per_minute` | Rate limit for LLM requests | `5` |
| `timeout_seconds` | Timeout for each LLM request | `30` |
| `max_retries` | Maximum retries for transient errors | `10` |
| `cache_ttl_seconds` | How long to cache responses | `86400` (24h) |
| `prompt_tier` | System prompt complexity (`minimal`, `standard`, `auto`) | `"auto"` |

### Context & Content

| Key | Description | Default |
|-----|-------------|---------|
| `context_mode` | Context level (`minimal`, `balanced`, `complete`) | `"minimal"` |
| `context_bytes` | Max bytes for context window (collection phase limit) | `32000` |
| `context_file_limit` | Max number of files in context | `10` |
| `context_include_globs` | List of file patterns to force include | `[]` |
| `context_exclude_globs` | List of file patterns to exclude | `["*.pyc", "__pycache__/*", ...]` |
| `include_param_values` | Include test parameter values in validation | `False` |
| `param_value_max_chars` | Max characters for parameter values | `100` |
| `strip_docstrings` | Strip docstrings from context (reduces tokens) | `True` |

> **Context Modes Explained:**
> - **`minimal`**: Only test source code, no additional files
> - **`balanced`** (default): Test source + covered files up to `context_bytes` limit (32KB)
> - **`complete`**: All covered files up to much higher internal limits (~10MB)
>
> **Water-Fill Algorithm:** After context collection, the LLM provider applies a "water-fill" algorithm that fairly distributes the model's actual token budget among files by satisfying smaller files first, maximizing context utilization.

### Token Optimization

| Key | Description | Default |
|-----|-------------|---------|
| `batch_parametrized_tests` | Group parametrized tests for single annotation | `true` |
| `batch_max_tests` | Maximum tests per batch | `5` |
| `context_compression` | Context compression mode (`none`, `lines`) | `"lines"` |
| `context_line_padding` | Lines of context around covered ranges | `2` |

### Report & Coverage

| Key | Description | Default |
|-----|-------------|---------|
| `omit_tests_from_coverage` | Exclude test files from coverage usage | `True` |
| `include_phase` | Test phases to include (`run`, `setup`, `teardown`, `all`) | `"run"` |
| `report_collect_only` | Generate report even for collect-only runs | `True` |
| `capture_failed_output` | Include stdout/stderr for failed tests | `True` |
| `capture_output_max_chars` | Max chars for captured output | `4000` |
| `include_pytest_invocation` | Include pytest CLI command in report | `True` |

### Example Configuration

```toml
[tool.pytest_llm_report]
# Provider
provider = "litellm"
model = "gpt-4o"
litellm_api_base = "https://proxy.example.com"

# Performance
max_concurrency = 4
requests_per_minute = 60

# Context
context_mode = "balanced"
context_exclude_globs = ["**/.env*", "**/secrets.py"]

# Report
capture_failed_output = true
```


## LLM Provider Settings

### Provider: none (default)

No LLM calls. Reports are generated without annotations.

### Provider: ollama

```toml
[tool.pytest_llm_report]
provider = "ollama"
model = "llama3.2"
```

Environment variables:
- `OLLAMA_HOST`: Ollama server URL (default: http://127.0.0.1:11434)

### Provider: litellm

```toml
[tool.pytest_llm_report]
provider = "litellm"
model = "gpt-4o-mini"
```

Environment variables depend on the model (e.g., `OPENAI_API_KEY`).

### Provider: gemini

```toml
[tool.pytest_llm_report]
provider = "gemini"
model = "gemini-1.5-flash-latest"
```

Environment variables:
- `GEMINI_API_TOKEN`: Gemini API key

Gemini automatically queries model metadata to apply RPM/TPM/RPD limits. The
`llm_report_requests_per_minute` value is treated as an upper bound if it is
lower than the model’s RPM limit.

## pytest Markers

```python
import pytest

# Opt out of LLM annotation
@pytest.mark.llm_opt_out
def test_skip_llm():
    pass

# Override context mode
@pytest.mark.llm_context("complete")
def test_with_full_context():
    pass

# Associate with requirements
@pytest.mark.requirement("REQ-001", "REQ-002")
def test_requirement():
    pass
```

## Context Modes

| Mode | Description |
|------|-------------|
| `minimal` | Test code only, no additional context |
| `balanced` | Test code + covered files (limited) |
| `complete` | Test code + all covered files up to limits |

## Hardware Optimization Tips

### Local CPU-Only Setup (e.g., Intel i7/i9, no GPU)

Running LLMs locally on CPU is computationally intensive. To maximize performance and avoid system instability:

1.  **Set Concurrency to 1**:
    ```toml
    llm_max_concurrency = 1
    ```
    Parallel requests on CPU often lead to resource contention (thrashing), making total execution *slower* than sequential processing.

2.  **Skip Rate Limits**:
    Ensure the provider is detected as local (the plugin does this automatically for `ollama`) to avoid artificial delays.

3.  **Model Selection**:
    Use smaller, quantized models like `llama3.2` (3B) or `qwen2.5:1.5b` for faster inference times.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OLLAMA_HOST` | Ollama server URL |
| `OPENAI_API_KEY` | OpenAI API key (for litellm) |
| `ANTHROPIC_API_KEY` | Anthropic API key (for litellm) |
| `GEMINI_API_TOKEN` | Gemini API key |
