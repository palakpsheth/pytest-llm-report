# Deployment Instructions

This guide covers publishing pytest-llm-report to PyPI and setting up CI/CD.

## Prerequisites

- Python 3.11+
- uv (recommended) or pip
- PyPI account with API token

## Local Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/pytest-llm-report.git
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

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: uv sync --all-extras
      
      - name: Run tests
        run: |
          uv run pytest \
            --cov=pytest_llm_report \
            --cov-context=test \
            --cov-report=xml \
            --cov-fail-under=90
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  publish:
    needs: [test, lint]
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      
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
