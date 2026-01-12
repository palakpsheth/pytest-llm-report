# pytest-llm-report

[![CI](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/ci.yml/badge.svg)](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/ci.yml)
[![Docs](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/docs.yml/badge.svg)](https://github.com/palakpsheth/pytest-llm-report/actions/workflows/docs.yml)
[![codecov](https://codecov.io/gh/palakpsheth/pytest-llm-report/branch/main/graph/badge.svg)](https://codecov.io/gh/palakpsheth/pytest-llm-report)
[![PyPI](https://img.shields.io/pypi/v/pytest-llm-report)](https://pypi.org/project/pytest-llm-report/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pytest-llm-report)](https://pypi.org/project/pytest-llm-report/)
[![License](https://img.shields.io/pypi/l/pytest-llm-report)](LICENSE)
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
- HTML and JSON output formats
- Dark mode support (auto-detects system preference)
- Optional PDF generation
- Aggregation across multiple test runs (see [Aggregation](docs/aggregation.md))

## Installation

```bash
pip install pytest-llm-report
```

Or with uv:
```bash
uv add pytest-llm-report
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
