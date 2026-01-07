# ADR 0002: LLM Providers

## Status
Accepted

## Context

The plugin needs to support multiple LLM providers for test annotation while maintaining privacy and flexibility.

## Decision

Implement a provider abstraction with three providers:
1. `none` - No LLM (default)
2. `ollama` - Local LLM via Ollama
3. `litellm` - Cloud LLMs via LiteLLM library

## Consequences

### Positive
- Privacy by default (provider=none)
- Local option for sensitive code (Ollama)
- Broad cloud support via LiteLLM (100+ models)
- Clean abstraction for adding new providers

### Negative
- LiteLLM is a heavy dependency
- Ollama requires local setup
- Different providers have different quality/speed

## Alternatives Considered

1. **Direct API integration** - More work, less flexibility
2. **Single provider** - Limits user choice
3. **LangChain** - Too heavy, unnecessary complexity
