# Privacy

pytest-llm-report is designed with privacy as a priority.

## Default Behavior

By default, **no data leaves your machine**:
- LLM provider is `"none"`
- All processing is local
- Reports are local files only

## When LLM is Enabled

If you enable an LLM provider:

| Provider | Data Destination |
|----------|-----------------|
| `none` | Nowhere (default) |
| `ollama` | Your local Ollama server |
| `litellm` | External cloud provider |
| `gemini` | External cloud provider |

## What's Sent to LLM

Only when explicitly enabled:
- Test function source code
- Covered file contents (based on context mode)
- Test nodeid

## What's Never Sent

- Environment variables
- Credentials or secrets
- System information
- Test output (stdout/stderr)

## Protecting Sensitive Code

### Opt-out specific tests

```python
@pytest.mark.llm_opt_out
def test_sensitive():
    pass
```

### Exclude files from context

```toml
[tool.pytest_llm_report]
llm_context_exclude_globs = [
    "*secret*",
    "*proprietary*",
    "internal/*",
]
```

### Use minimal context

```toml
[tool.pytest_llm_report]
llm_context_mode = "minimal"  # Only test code, no covered files
```

## Recommendations by Environment

| Environment | Recommended Provider |
|-------------|---------------------|
| Public CI | `none` |
| Private CI | `ollama` or `none` |
| Local dev | `ollama` |
| Open source | `none` |

See also: [policies/privacy.md](../policies/privacy.md)
