# Configuration Reference

Complete configuration reference for pytest-llm-report.

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--llm-report PATH` | HTML report output path | None |
| `--llm-report-json PATH` | JSON report output path | None |
| `--llm-pdf PATH` | PDF report output (requires Playwright) | None |
| `--llm-evidence-bundle PATH` | Evidence bundle zip output | None |
| `--llm-aggregate-dir DIR` | Directory with reports to aggregate | None |
| `--llm-aggregate-policy POLICY` | Aggregation policy: latest, merge, all | latest |
| `--llm-aggregate-run-id ID` | Unique run ID | Auto-generated |
| `--llm-aggregate-group-id ID` | Group ID for related runs | None |

## pyproject.toml Options

```toml
[tool.pytest.ini_options]
# Output defaults
llm_report_html = "reports/test-report.html"
llm_report_json = "reports/test-report.json"

# LLM provider (none, ollama, litellm)
llm_report_provider = "none"
llm_report_model = "llama3.2"
llm_report_context_mode = "minimal"
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
