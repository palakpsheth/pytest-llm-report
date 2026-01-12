# LLM Data Handling

This document describes how pytest-llm-report handles data sent to LLM providers.

## What Data is Sent

When LLM is enabled, the following may be sent:

1. **Test function source code**
2. **Covered file contents** (based on context mode)
3. **Test nodeid** (e.g., `tests/test_foo.py::test_bar`)

## What Data is NOT Sent

- Test output (stdout/stderr)
- Environment variables
- Credentials or secrets
- System information
- Coverage statistics

## Context Modes

### minimal
Only the test function source code.

### balanced
Test code + covered files (limited by `llm_context_bytes`).

### complete
Test code + all covered files (up to limits).

## Exclusions

By default, these patterns are excluded:
- `*secret*`, `*password*`, `*credential*`
- `*key*`, `*token*`, `*.env*`
- `*config/secrets*`, `*private*`

Add custom exclusions:
```toml
[tool.pytest_llm_report]
llm_context_exclude_globs = ["internal/*", "proprietary/*"]
```

## Caching

LLM responses are cached locally to:
- Reduce API calls and costs
- Speed up repeat runs
- Avoid re-sending unchanged tests

Cache is keyed by test nodeid + source hash.

## Provider-Specific Considerations

### Ollama
Data stays on your machine. No external network calls.

### LiteLLM (Cloud)
Data is sent to external providers. Consider:
- Provider data retention policies
- API usage logging
- Regional data residency

### Gemini (Cloud)
Data is sent to the Gemini API. Consider:
- Provider data retention policies
- API usage logging
- Regional data residency
