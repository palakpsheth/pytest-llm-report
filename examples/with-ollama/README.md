# Ollama Example

This example shows pytest-llm-report with local Ollama LLM for generating test annotations.

## Prerequisites

1. Install [Ollama](https://ollama.com/)
2. Pull a model:
   ```bash
   ollama pull llama3.2
   ```

## Setup

```bash
cd examples/with-ollama
uv sync
```

## Run

```bash
# Start Ollama (if not running)
ollama serve &

# Run tests
uv run pytest
```

## Configuration

See `pyproject.toml` for LLM settings:

```toml
[tool.pytest_llm_report]
provider = "ollama"
model = "llama3.2"
ollama_host = "http://127.0.0.1:11434"
```

## What it demonstrates

- Local LLM annotation
- Per-test scenarios
- Why-needed explanations
- Key assertions extraction
