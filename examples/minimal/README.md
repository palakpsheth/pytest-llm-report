# Minimal Example

This example shows pytest-llm-report with no LLM provider (default), generating HTML and JSON reports.

## Setup

```bash
cd examples/minimal
uv sync
```

## Run

```bash
uv run pytest
```

Reports will be generated at:
- `reports/pytest_llm_report.html`
- `reports/pytest_llm_report.json`

## What it demonstrates

- Basic plugin usage
- Per-test coverage mapping
- HTML report with filtering
- JSON report with schema
