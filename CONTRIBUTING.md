# Contributing to pytest-llm-report

Thank you for your interest in contributing!

For full documentation, see: [palakpsheth.github.io/pytest-llm-report](https://palakpsheth.github.io/pytest-llm-report/)

## Development Setup

```bash
# Clone the repository
git clone https://github.com/palakpsheth/pytest-llm-report.git
cd pytest-llm-report

# Install with all development dependencies (includes all LLM providers)
uv sync

# Or install manually with all extras
uv pip install -e ".[dev]"

# Install Playwright browsers (required for PDF tests)
uv run playwright install chromium

# Run tests
uv run pytest

# Run tests with coverage (accurate for plugin imports)
uv run coverage run --branch -m pytest -o "addopts=" -p no:pytest-cov
uv run coverage report
```

### What Gets Installed

The `dev` optional dependency group includes:
- **All LLM providers**: httpx (for Ollama/Gemini), litellm
- **PDF generation**: playwright
- **Development tools**: ruff, mypy, pytest-xdist
- **Coverage tools**: coverage, pytest-cov

This ensures `uv sync` installs everything needed to run all tests.

## Running Tests

```bash
# All tests
uv run pytest

# With accurate coverage (Recommended)
uv run coverage run --branch -m pytest -o "addopts=" -p no:pytest-cov
uv run coverage report

# With pytest-cov (Faster, but may miss early plugin imports)
uv run pytest --cov=pytest_llm_report --cov-branch

# Specific test file
uv run pytest tests/test_models.py -v
```

## Coverage Policy

CI requires **90% test coverage**. We achieve this by testing core logic and supporting provider edge cases.

### Module Coverage Status

Most modules in the core plugin now have high coverage. We use `coverage run -m pytest` to ensure that module-level code (like class definitions and plugin registration) is correctly measured.

| Module | Status | Note |
|--------|--------|------|
| `collector.py` | ✅ Covered | Tested via `tests/test_collector_maximal.py` |
| `coverage_map.py` | ✅ Covered | Tested via integration and unit tests |
| `plugin.py` | ✅ Covered | Tested via `tests/test_plugin_maximal.py` |
| `options.py` | ✅ Covered | Tested via `tests/test_options_maximal.py` |
| `prompts.py` | ✅ Covered | Tested via `tests/test_prompts.py` |
| `llm/ollama.py` | ✅ Covered | Tested via provider mocks |
| `llm/gemini.py` | ✅ Covered | Tested via provider mocks |

### Adding Tests

When contributing:

1. **Add unit tests** for pure functions and classes
2. **Use mocks** for external dependencies (e.g., `unittest.mock` for HTTP calls)
3. **Integration tests** go in `tests/test_smoke_pytester.py` or similar
4. **Use maximal test files** (e.g., `tests/test_plugin_maximal.py`) for comprehensive coverage of complex modules

## Code Style

- Format with `ruff format`
- Lint with `ruff check`
- Type hints required for public APIs
- Docstrings required for modules and public functions

## Pull Request Process

1. Fork and create a feature branch
2. Add tests for new functionality
3. Ensure `uv run coverage run --branch -m pytest -o "addopts=" -p no:pytest-cov && uv run coverage report` passes
4. Run `uv run ruff check . && uv run ruff format --check .`
5. Submit PR with clear description
