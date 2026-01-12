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
| `--llm-aggregate-dir DIR` | Directory with reports to [aggregate](aggregation.md) | None |
| `--llm-aggregate-policy POLICY` | Aggregation policy: latest, merge, all | latest |
| `--llm-aggregate-run-id ID` | Unique run ID | Auto-generated |
| `--llm-aggregate-group-id ID` | Group ID for related runs | None |

> **Tip**: Run `pytest --help` to see usage examples for each option.

## pyproject.toml Options

```toml
[tool.pytest.ini_options]
# Output defaults
llm_report_html = "reports/test-report.html"
llm_report_json = "reports/test-report.json"

# LLM provider (none, ollama, litellm, gemini)
llm_report_provider = "none"
llm_report_model = "llama3.2"
llm_report_context_mode = "minimal"
llm_report_requests_per_minute = 5
```

## LLM Provider Settings

### Provider: none (default)

No LLM calls. Reports are generated without annotations.

### Provider: ollama

```toml
llm_report_provider = "ollama"
llm_report_model = "llama3.2"
```

Environment variables:
- `OLLAMA_HOST`: Ollama server URL (default: http://127.0.0.1:11434)

### Provider: litellm

```toml
llm_report_provider = "litellm"
llm_report_model = "gpt-4o-mini"
```

Environment variables depend on the model (e.g., `OPENAI_API_KEY`).

### Provider: gemini

```toml
llm_report_provider = "gemini"
llm_report_model = "gemini-1.5-flash-latest"
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

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OLLAMA_HOST` | Ollama server URL |
| `OPENAI_API_KEY` | OpenAI API key (for litellm) |
| `ANTHROPIC_API_KEY` | Anthropic API key (for litellm) |
| `GEMINI_API_TOKEN` | Gemini API key |
