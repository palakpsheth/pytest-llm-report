# LiteLLM Example

This example shows pytest-llm-report with LiteLLM for cloud LLM providers (OpenAI, Anthropic, etc.).

## Prerequisites

Set your API key:
```bash
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Setup

```bash
cd examples/with-litellm
uv sync
```

## Run

```bash
uv run pytest
```

## Configuration

See `pyproject.toml` for LLM settings:

```toml
[tool.pytest_llm_report]
provider = "litellm"
model = "gpt-4o-mini"  # or "claude-3-haiku-20240307"
```

## Supported Models

LiteLLM supports 100+ models. Common options:
- `gpt-4o-mini` (OpenAI, fast and cheap)
- `gpt-4o` (OpenAI, most capable)
- `claude-3-haiku-20240307` (Anthropic, fast)
- `claude-3-5-sonnet-20241022` (Anthropic, balanced)

## What it demonstrates

- Cloud LLM annotation
- Multi-provider support via LiteLLM
- Caching to reduce API costs
