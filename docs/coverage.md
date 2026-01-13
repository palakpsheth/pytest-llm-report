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

## Advanced: Accurate Module-Level Coverage

By default, `pytest-cov` starts measuring coverage after pytest has already loaded many of your project's modules. This can lead to "missing" coverage for top-level code like class definitions, constants, and global variables in those files.

If you need accurate coverage for these early imports (common for plugin development or critical library setup), use `coverage run -m pytest` instead:

```bash
# Erase old data
coverage erase

# Run with coverage wrapper
coverage run -m pytest -o "addopts=" -p no:pytest-cov

# View report
coverage report
```

The `-o "addopts=" -p no:pytest-cov` flags are recommended to prevent conflicts with your existing `pytest-cov` configuration.

## Parallel/Distributed Testing

For `pytest-xdist` (parallel testing), coverage data is automatically combined when using `pytest-cov`:

```bash
pytest -n auto --cov=your_package --cov-context=test --llm-report=report.html
```

When using `coverage run` with `xdist`, make sure to use `coverage combine` if running manually:

```bash
coverage run -p -m pytest -n auto ...
coverage combine
coverage report
```

The plugin reads both `.coverage` and `.coverage.*` files to generate the final report.

## CI Integration

Recommended CI command for full accuracy:

```yaml
- name: Run tests and collect coverage
  run: |
    coverage run -m pytest \
      -o "addopts=" \
      -p no:pytest-cov \
      --llm-report=report.html \
      --llm-report-json=report.json

- name: Generate coverage XML
  run: coverage xml
```

## Troubleshooting

### "No coverage contexts found" warning

This means `--cov-context=test` was not set. Add it to your pytest configuration.

### "No .coverage file found" warning

Ensure you're running with `--cov=your_package` or `coverage run`. The `.coverage` file must exist after the test run.

### Coverage data seems stale

Run `coverage erase` before your test run to clear old data, or use the `--cov-clear` flag if using `pytest-cov`.
