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
   model = "gemini-1.5-flash"
   ```

### Supported models

- `gemini-1.5-flash`
- `gemini-1.5-pro`

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
