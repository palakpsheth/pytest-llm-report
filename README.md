# pytest-llm-report

[![CI](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/ci.yml/badge.svg)](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/ci.yml)
[![CodeQL](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/codeql.yml/badge.svg)](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/codeql.yml)
[![Snyk Security](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/snyk.yml/badge.svg)](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/snyk.yml)
[![Docs](https://img.shields.io/badge/docs-online-blue?logo=github)](https://palakpsheth.github.io/pytest-llm-report/)
[![codecov](https://codecov.io/gh/palakpsheth/pytest-llm-report/branch/main/graph/badge.svg)](https://codecov.io/gh/palakpsheth/pytest-llm-report)
[![PyPI version](https://badge.fury.io/py/pytest-llm-report.svg)](https://pypi.org/project/pytest-llm-report/)
[![Python Versions](https://img.shields.io/badge/python-3.11%7C3.12%7C3.13-blue?logo=python&logoColor=white)](https://pypi.org/project/pytest-llm-report/)
[![License](https://img.shields.io/github/license/palakpsheth/pytest-llm-report)](LICENSE)
[![Dependabot](https://img.shields.io/badge/dependabot-enabled-blue.svg?logo=dependabot)](https://github.com/palakpsheth/pytest-llm-report/blob/main/.github/dependabot.yml)
[![pytest plugin](https://img.shields.io/badge/pytest-plugin-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)

Human-friendly pytest test reports with optional LLM annotations.

## Features

- Test inventory with status (pass/fail/skip/xfail) and duration
- Per-test covered files and line ranges (using pytest-cov + coverage contexts)
- Per-file source coverage summary (covered/missed/percentage)
- Optional LLM-generated annotations:
  - **Scenario**: What the test verifies
  - **Why needed**: What regression/bug it prevents
  - **Key assertions**: Critical checks performed
  - **Smart Context**: Automatically fetches model context limits (Gemini, Ollama, LiteLLM) to maximize relevant code included in prompts without hitting token limits.
  - **Compact Context**: Automatically strips docstrings and optimizes whitespace to reduce token consumption (enabled by default).
  - **Token Usage Reporting**: Tracks and displays input, output, and total token usage for each annotation and the entire test run.
- HTML and JSON output formats
- Dark mode support (auto-detects system preference)
- Optional PDF generation
- **Detailed Versioning**: Reports include exact plugin and repository versions (plus Git SHA/dirty status) for reproducibility
- Aggregation across multiple test runs (see [Aggregation](https://palakpsheth.github.io/pytest-llm-report/aggregation/))

## Installation

```bash
pip install pytest-llm-report
```

Or with uv:
```bash
uv add pytest-llm-report
```

### Optional Dependencies

Install additional features as needed:

```bash
# Ollama provider
pip install pytest-llm-report[ollama]

# Gemini provider
pip install pytest-llm-report[gemini]

# LiteLLM provider (supports OpenAI, Anthropic, etc.)
pip install pytest-llm-report[litellm]

# PDF generation
pip install pytest-llm-report[pdf]

# All features
pip install pytest-llm-report[all]
```

With uv:
```bash
uv add "pytest-llm-report[ollama]"  # or gemini, litellm, pdf, all
```

## Quick Start

Run pytest with coverage contexts enabled:

```bash
pytest --cov=your_package --cov-context=test --llm-report=report.html
```

## Configuration

Configure via `pyproject.toml`:

```toml
[tool.pytest_llm_report]
provider = "none"  # "none", "ollama", "litellm", or "gemini"
report_json = "reports/pytest_llm_report.json"
```

## Documentation

📖 **Full documentation**: [palakpsheth.github.io/pytest-llm-report](https://palakpsheth.github.io/pytest-llm-report/)

## Requirements

- Python 3.11+
- pytest >= 7.0.0
- pytest-cov >= 4.0.0

## Contributing

Contributions are welcome! Please see:

- [Contributing Guide](CONTRIBUTING.md) - Development setup and guidelines
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines
- [Security Policy](SECURITY.md) - Reporting vulnerabilities
- [Changelog](CHANGELOG.md) - Version history

## License

MIT
