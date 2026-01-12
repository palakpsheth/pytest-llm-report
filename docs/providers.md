# LLM Providers

pytest-llm-report supports multiple LLM providers for generating test annotations.

## Provider: none (default)

No LLM calls. Reports contain test results and coverage only.

```toml
[tool.pytest_llm_report]
provider = "none"
```

## Provider: ollama

Local LLM using [Ollama](https://ollama.com/).

### Setup

1. Install Ollama
2. Pull a model: `ollama pull llama3.2`
3. Configure:

```toml
[tool.pytest_llm_report]
provider = "ollama"
model = "llama3.2"
ollama_host = "http://127.0.0.1:11434"
```

### Recommended models

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `llama3.2` | 2GB | Fast | Good |
| `qwen2.5-coder:7b` | 4GB | Medium | Better |
| `qwen2.5-coder:14b` | 8GB | Slow | Best |

## Provider: litellm

Cloud LLMs via [LiteLLM](https://github.com/BerriAI/litellm).

### Setup

1. Set API key:
   ```bash
   export OPENAI_API_KEY="sk-..."
   # or
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

2. Configure:
   ```toml
   [tool.pytest_llm_report]
   provider = "litellm"
   model = "gpt-4o-mini"
   ```

### Supported models

- OpenAI: `gpt-4o-mini`, `gpt-4o`
- Anthropic: `claude-3-haiku-20240307`, `claude-3-5-sonnet-20241022`
- Many more via LiteLLM

## Provider: gemini

Cloud LLMs via the Gemini API.

### Setup

1. Set API key:
   ```bash
   export GEMINI_API_TOKEN="..."
   ```

2. Configure:
   ```toml
   [tool.pytest_llm_report]
   provider = "gemini"
   model = "gemini-1.5-flash-latest"
   ```

### Supported models

- `gemini-2.5-flash`
- `gemini-2.5-pro`
- `gemini-2.0-flash-exp`
- `gemini-2.0-flash`
- `gemini-2.0-flash-001`
- `gemini-2.0-flash-exp-image-generation`
- `gemini-2.0-flash-lite-001`
- `gemini-2.0-flash-lite`
- `gemini-2.0-flash-lite-preview-02-05`
- `gemini-2.0-flash-lite-preview`
- `gemini-exp-1206`
- `gemini-2.5-flash-preview-tts`
- `gemini-2.5-pro-preview-tts`
- `gemini-flash-latest`
- `gemini-flash-lite-latest`
- `gemini-pro-latest`
- `gemini-2.5-flash-lite`
- `gemini-2.5-flash-image-preview`
- `gemini-2.5-flash-image`
- `gemini-2.5-flash-preview-09-2025`
- `gemini-2.5-flash-lite-preview-09-2025`
- `gemini-3-pro-preview`
- `gemini-3-flash-preview`
- `gemini-3-pro-image-preview`
- `nano-banana-pro-preview`
- `gemini-robotics-er-1.5-preview`
- `gemini-2.5-computer-use-preview-10-2025`
- `deep-research-pro-preview-12-2025`
- `gemma-3-1b-it`
- `gemma-3-4b-it`
- `gemma-3-12b-it`
- `gemma-3-27b-it`
- `gemma-3n-e4b-it`
- `gemma-3n-e2b-it`

### Rate limits

When Gemini is enabled, pytest-llm-report queries the Gemini model metadata to
retrieve the **requests-per-minute (RPM)**, **tokens-per-minute (TPM)**, and
**requests-per-day (RPD)** limits for the selected model. The plugin applies
those limits automatically:

- **RPM/TPM**: waits until the next request is within the limit.
- **RPD**: skips annotation once the daily cap is reached (no waiting).

### Model rotation

If you specify `model = "all"` or a comma-separated list of models, the plugin
will automatically rotate between available models to maximize request throughput:

```toml
[tool.pytest_llm_report]
provider = "gemini"
model = "gemini-2.5-flash,gemini-2.0-flash,gemini-1.5-flash"
```

When a model reaches its rate limit, the plugin switches to the next available
model. This is especially useful for exceeding free-tier daily limits by
distributing requests across multiple models.

### Model recovery

For long-running test sessions (e.g., CI jobs spanning multiple days), models
that hit their daily request limits will **automatically recover** after 24
hours. The plugin tracks when each model was exhausted and clears that state
once the daily limit window has passed.

Additionally, the available model list is **refreshed every 6 hours** to pick
up any new models that may have become available via the Gemini API.

## Caching

LLM responses are cached to reduce API calls:

```toml
[tool.pytest_llm_report]
cache_dir = ".pytest_llm_cache"
llm_cache_ttl_seconds = 86400  # 24 hours
```

Clear cache:
```bash
rm -rf .pytest_llm_cache
```
