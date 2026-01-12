# Privacy Policy

## Data Collection

pytest-llm-report collects the following data during test runs:

1. **Test results** - Pass/fail status, duration, error messages
2. **Coverage data** - Files and lines executed by each test
3. **Test code** - Only when LLM provider is enabled

## Data Storage

All data is stored locally:
- Reports in user-specified paths
- LLM cache in `cache_dir` (default: `.pytest_llm_cache`)

No data is sent to any remote server by default.

## LLM Provider Data Handling

When an LLM provider is enabled:

### Provider: none (default)
No data leaves your machine.

### Provider: ollama
Data is sent to your local Ollama server only.

### Provider: litellm
Data is sent to the configured cloud provider (OpenAI, Anthropic, etc.).
Review their privacy policies:
- [OpenAI Privacy](https://openai.com/policies/privacy-policy)
- [Anthropic Privacy](https://www.anthropic.com/privacy)

### Provider: gemini
Data is sent to the Gemini API (Google).
Review Google's privacy policy:
- [Google Privacy](https://policies.google.com/privacy)

## User Controls

- `provider = "none"` - Disable all LLM features
- `@pytest.mark.llm_opt_out` - Opt out specific tests
- `llm_context_exclude_globs` - Exclude sensitive files
- `invocation_redact_patterns` - Redact CLI arguments

## Data Retention

- Reports: User controls retention
- LLM cache: Expires per `llm_cache_ttl_seconds` (default: 24 hours)
- No telemetry or analytics

## Contact

For privacy questions, open an issue or contact privacy@example.com.
