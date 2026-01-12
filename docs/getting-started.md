# Getting Started

## Installation

```bash
# Basic
pip install pytest-llm-report

# With uv
uv add pytest-llm-report
```

For LLM support:
```bash
# Ollama (local)
pip install pytest-llm-report[ollama]

# LiteLLM (cloud)
pip install pytest-llm-report[litellm]
```

## Prerequisites

You need `pytest-cov` with context tracking:

```bash
pip install pytest-cov
```

## Basic Usage

### 1. Configure coverage

Add to your `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=your_package",
    "--cov-context=test",
    "--cov-report=",
]
```

### 2. Generate a report

```bash
pytest --llm-report=report.html
```

### 3. View the report

Open `report.html` in a browser to see:
- Test summary (passed/failed/skipped)
- Per-test coverage (files and lines)
- Filter and search functionality
- Dark mode (automatic based on system preferences)

## Next Steps

- [Configuration](configuration.md) - All options
- [Coverage Setup](coverage.md) - Coverage contexts explained
- [LLM Providers](providers.md) - Add AI annotations
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
