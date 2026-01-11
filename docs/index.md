# pytest-llm-report Documentation

Welcome to pytest-llm-report, a pytest plugin for generating human-friendly test reports with optional LLM annotations.

!!! tip "Live Test Report Available"
    View the latest test report for this project:

    [🧪 Interactive Test Report](reports/index.html){ .md-button .md-button--primary }


## Quick Start

Install the plugin:
```bash
pip install pytest-llm-report
```

Run tests with a report:
```bash
pytest --cov=my_pkg --cov-context=test --llm-report=report.html
```

## Features

- **HTML and JSON reports** with per-test coverage
- **LLM annotations** describing what each test verifies
- **Local or cloud LLM** support (Ollama, OpenAI, Anthropic)
- **Privacy-first** - LLM is disabled by default
- **CI/CD ready** - artifacts for pipelines
- **Aggregation** - Combine reports from multiple runs (see [Aggregation](aggregation.md))

## Documentation

- [Getting Started](getting-started.md)
- [Configuration](configuration.md)
- [LLM Providers](providers.md)
- [Coverage Setup](coverage.md)
- [Report Format](report-format.md)
- [Privacy](privacy.md)
- [Security](security.md)
- [Troubleshooting](troubleshooting.md)
- [Contributing](https://github.com/palakpsheth/pytest-llm-report/blob/main/CONTRIBUTING.md)
