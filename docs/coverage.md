# Coverage Configuration

This guide explains how to configure pytest-cov for use with pytest-llm-report.

## What is `--cov-context=test`?

The `--cov-context=test` flag tells pytest-cov to record **which test** covered each line of code. This is called "coverage contexts."

Without contexts, coverage data only tells you which lines were executed. With contexts, you know exactly which test exercised each line.

## Why is it Required?

pytest-llm-report uses coverage contexts to:
- Show which source files and lines each test covers
- Generate per-test coverage reports
- Help LLM understand what code the test exercises

## Configuring Your Repository

### Option 1: pyproject.toml (Recommended)

Add to your `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=your_package",       # Replace with your package name
    "--cov-context=test",       # Required for per-test coverage mapping
    "--cov-report=",            # Suppress default coverage report (optional)
]
```

### Option 2: pytest.ini

```ini
[pytest]
addopts =
    --cov=your_package
    --cov-context=test
    --cov-report=
```

### Option 3: setup.cfg

```ini
[tool:pytest]
addopts =
    --cov=your_package
    --cov-context=test
    --cov-report=
```

### Option 4: Command Line

```bash
pytest --cov=your_package --cov-context=test --llm-report=report.html
```

## Configuration Options

| Option | Description |
|--------|-------------|
| `--cov=PKG` | Package/directory to measure coverage for |
| `--cov-context=test` | Record context for each test |
| `--cov-report=` | Suppress default report (set empty) |
| `--cov-append` | Append to existing coverage data |

## Example: Multi-Package Project

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=src/package_a",
    "--cov=src/package_b",
    "--cov-context=test",
    "--llm-report=reports/test-report.html",
    "--llm-report-json=reports/test-report.json",
]
```

## Parallel/Distributed Testing

For `pytest-xdist` (parallel testing), coverage data is automatically combined:

```bash
pytest -n auto --cov=your_package --cov-context=test --llm-report=report.html
```

The plugin reads both `.coverage` and `.coverage.*` files.

## CI Integration

Example GitHub Actions workflow:

```yaml
- name: Run tests
  run: |
    pytest \
      --cov=your_package \
      --cov-context=test \
      --cov-report=xml \
      --llm-report=report.html \
      --llm-report-json=report.json

- name: Upload report
  uses: actions/upload-artifact@v4
  with:
    name: test-report
    path: |
      report.html
      report.json
```

## Troubleshooting

### "No coverage contexts found" warning

This means `--cov-context=test` was not set. Add it to your pytest configuration.

### "No .coverage file found" warning

Ensure you're running with `--cov=your_package`. The `.coverage` file must exist after the test run.

### Coverage data seems stale

Run `coverage erase` before your test run to clear old data:

```bash
coverage erase && pytest --cov=your_package --cov-context=test
```
