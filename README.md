# pytest-llm-report

Human-friendly pytest test reports with optional LLM annotations.

## Features

- Test inventory with status (pass/fail/skip/xfail) and duration
- Per-test covered files and line ranges (using pytest-cov + coverage contexts)
- Optional LLM-generated annotations:
  - **Scenario**: What the test verifies
  - **Why needed**: What regression/bug it prevents
  - **Key assertions**: Critical checks performed
- HTML and JSON output formats
- Optional PDF generation
- Aggregation across multiple test runs

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
provider = "none"  # "none", "ollama", or "litellm"
report_json = "reports/pytest_llm_report.json"
```

## Requirements

- Python 3.11+
- pytest >= 7.0.0
- pytest-cov >= 4.0.0

## License

MIT
