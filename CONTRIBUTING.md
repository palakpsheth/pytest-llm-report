# Contributing to pytest-llm-report

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/pytest-llm-report.git
cd pytest-llm-report

# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=pytest_llm_report --cov-report=term-missing

# Format and lint
uv run ruff format .
uv run ruff check .
```

## Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=pytest_llm_report --cov-fail-under=90

# Specific test file
uv run pytest tests/test_models.py -v
```

## Coverage Policy

CI requires **90% test coverage**. We achieve this by:

1. **Unit testing** core modules (models, render, cache, hashing, ranges, fs)
2. **Excluding integration modules** that require external services or full pytest runs

### Excluded from Coverage

The following modules are **excluded from coverage measurement** in `pyproject.toml`:

| Module | Reason |
|--------|--------|
| `collector.py` | Requires pytest hooks (full test run) |
| `coverage_map.py` | Requires `.coverage` file from pytest-cov |
| `plugin.py` | Requires pytest hook integration |
| `options.py` | Dataclass field access doesn't register as covered |
| `prompts.py` | File I/O heavy context extraction |
| `llm/ollama.py` | Requires Ollama server |
| `llm/litellm_provider.py` | Requires LLM API keys |

### Why These Exclusions?

These modules require **external dependencies** that cannot be mocked effectively:

- **Pytest hooks** (`collector`, `coverage_map`, `plugin`): These run during pytest's lifecycle and are tested via integration tests, not unit tests.
- **LLM providers** (`ollama`, `litellm`): Require actual API connections or local servers.
- **Context assembly** (`prompts`): Heavy file I/O for reading source files.

### Adding Tests

When contributing:

1. **Add unit tests** for pure functions and classes
2. **Use mocks** for external dependencies where possible
3. **Integration tests** go in `tests/test_plugin_integration.py`

## Code Style

- Format with `ruff format`
- Lint with `ruff check`
- Type hints required for public APIs
- Docstrings required for modules and public functions

## Pull Request Process

1. Fork and create a feature branch
2. Add tests for new functionality
3. Ensure `uv run pytest --cov-fail-under=90` passes
4. Run `uv run ruff check . && uv run ruff format --check .`
5. Submit PR with clear description
