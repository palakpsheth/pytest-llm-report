# Deployment Instructions

This guide covers publishing pytest-llm-report to PyPI and setting up CI/CD.

## Prerequisites

- Python 3.11+
- uv (recommended) or pip
- PyPI account with API token

## Local Development Setup

```bash
# Clone the repository
git clone https://github.com/palakpsheth/pytest-llm-report.git
cd pytest-llm-report

# Create virtual environment and install
uv sync

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=pytest_llm_report --cov-report=term-missing
```

## Building

```bash
# Build sdist and wheel
uv build

# Check the build
ls dist/
# pytest_llm_report-0.1.0.tar.gz
# pytest_llm_report-0.1.0-py3-none-any.whl
```

## Publishing to PyPI

### Option 1: Using uv (Recommended)

```bash
# Set PyPI token
export UV_PUBLISH_TOKEN="pypi-..."

# Publish
uv publish
```

### Option 2: Using twine

```bash
# Install twine
pip install twine

# Upload
twine upload dist/*
```

### Option 3: GitHub Actions (Automated)

The CI workflow automatically publishes on tagged releases.

```bash
# Tag a release
git tag v0.1.0
git push origin v0.1.0
```

## GitHub Actions CI/CD

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
  release:
    types: [published]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Install Playwright browsers
        run: uv run playwright install chromium

      # Ollama setup (Main branch only)
      - name: Install Ollama
        if: github.ref == 'refs/heads/main'
        run: curl -fsSL https://ollama.com/install.sh | sh

      - name: Start Ollama
        if: github.ref == 'refs/heads/main'
        run: ollama serve &

      - name: Pull LLM Model
        if: github.ref == 'refs/heads/main'
        run: |
          sleep 5
          ollama pull llama3.2:1b

      - name: Run tests
        id: pytest
        continue-on-error: true
        run: |
          mkdir -p reports
          json_report="reports/pytest_llm_report-py${{ matrix.python-version }}.json"
          pdf_report="reports/pytest_llm_report-py${{ matrix.python-version }}.pdf"
          llm_args=()

          # Use Ollama on main branch for Python 3.12
          if [ "${{ matrix.python-version }}" = "3.12" ] && [ "${{ github.ref }}" = "refs/heads/main" ]; then
             llm_args+=(
              -o llm_report_provider=ollama
              -o llm_report_model=llama3.2:1b
              -o llm_report_context_mode=minimal
            )
          fi

          uv run pytest \
            --cov=pytest_llm_report \
            --cov-context=test \
            --cov-report=xml \
            --cov-fail-under=90 \
            -o llm_report_context_mode=complete \
            --llm-report-json="${json_report}" \
            --llm-pdf="${pdf_report}" \
            "${llm_args[@]}"

          exit_code=$?
          echo "exit_code=${exit_code}" >> "${GITHUB_OUTPUT}"
          exit 0

      - name: Upload coverage
        uses: codecov/codecov-action@v5
        if: matrix.python-version == '3.12'
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          fail_ci_if_error: false

      - name: Upload report artifact
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: report-py${{ matrix.python-version }}
          path: |
            reports/pytest_llm_report-py${{ matrix.python-version }}.json
            reports/pytest_llm_report-py${{ matrix.python-version }}.pdf
          retention-days: 7

      - name: Fail if tests failed
        if: steps.pytest.outputs.exit_code != '0'
        run: exit 1

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  publish:
    needs: [test, lint]
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    permissions:
      id-token: write

    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
      - name: Build
        run: uv build
      - name: Publish to PyPI
        run: uv publish
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

## Version Management

Update version in `src/pytest_llm_report/__about__.py`:

```python
__version__ = "0.1.0"
```

## Release Checklist

1. [ ] Update version in `__about__.py`
2. [ ] Update CHANGELOG.md
3. [ ] Run full test suite: `uv run pytest`
4. [ ] Check lint: `uv run ruff check .`
5. [ ] Build: `uv build`
6. [ ] Test install: `pip install dist/*.whl`
7. [ ] Create git tag: `git tag v0.1.0`
8. [ ] Push tag: `git push origin v0.1.0`
9. [ ] Create GitHub release

## Verification

After publishing:

```bash
# Install from PyPI
pip install pytest-llm-report

# Verify installation
python -c "import pytest_llm_report; print(pytest_llm_report.__version__)"

# Test in a project
pytest --llm-report=report.html
```
