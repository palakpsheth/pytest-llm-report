# Configuration Reference

Complete configuration reference for pytest-llm-report.

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--llm-report PATH` | HTML report output path | None |
| `--llm-report-json PATH` | JSON report output path | None |
| `--llm-pdf PATH` | PDF report output (requires Playwright) | None |
| `--llm-evidence-bundle PATH` | Evidence bundle zip output | None |
| `--llm-requests-per-minute N` | LLM request rate limit (also used as a cap for Gemini auto limits) | 5 |
| `--llm-max-retries N` | Maximum retries for transient errors | 10 |
| `--llm-aggregate-dir DIR` | Directory with reports to [aggregate](aggregation.md) | None |
| `--llm-aggregate-policy POLICY` | Aggregation policy: latest, merge, all | latest |
| `--llm-aggregate-run-id ID` | Unique run ID | Auto-generated |
| `--llm-aggregate-group-id ID` | Group ID for related runs | None |
| `--llm-provider NAME` | Override LLM provider (ollama, litellm, gemini) | None |
| `--llm-model NAME` | Override LLM model name | None |
| `--llm-context-mode MODE` | Override context mode (minimal, balanced, complete) | None |
| `--llm-coverage-source PATH` | Path to .coverage file/dir to inject into report | None |

> **Tip**: Run `pytest --help` to see usage examples for each option.

## pyproject.toml Options

Configure defaults in `pyproject.toml`:

```toml
[tool.pytest_llm_report]
# LLM provider configuration
provider = "ollama"              # Options: none, ollama, litellm, gemini
model = "llama3.2"
context_mode = "minimal"     # Options: minimal, balanced, complete
requests_per_minute = 5

# Execution limits
max_tests = 50              # Limit number of tests to annotate (0 = no limit)
max_concurrency = 1         # Max concurrent LLM requests
max_retries = 10           # Max retries for transient errors

# Coverage settings
omit_tests_from_coverage = true
include_phase = "run"           # Options: run, setup, teardown, all
```

> [!TIP]
> Local providers (like `ollama`) skip rate limiting automatically, so you can safely increase `llm_max_concurrency` to speed up annotations.


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
