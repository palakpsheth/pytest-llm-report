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

# Run with accurate coverage
uv run coverage run -m pytest -o "addopts=" -p no:pytest-cov
uv run coverage report
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

      - name: Install Ollama
        if: github.ref == 'refs/heads/main' && matrix.python-version == '3.12'
        run: curl -fsSL https://ollama.com/install.sh | sh

      - name: Start Ollama
        if: github.ref == 'refs/heads/main' && matrix.python-version == '3.12'
        run: ollama serve &

      - name: Pull LLM Model
        if: github.ref == 'refs/heads/main' && matrix.python-version == '3.12'
        run: |
          sleep 5
          ollama pull llama3.2:1b

      - name: Run tests
        id: pytest
        continue-on-error: true
        run: |
          set +e  # Disable immediate exit on error so we can capture exit codes
          mkdir -p reports
          html_report="reports/pytest_llm_report-py${{ matrix.python-version }}.html"
          json_report="reports/pytest_llm_report-py${{ matrix.python-version }}.json"
          pdf_report="reports/pytest_llm_report-py${{ matrix.python-version }}.pdf"
          llm_provider="none"
          llm_args=()
          if [ "${{ matrix.python-version }}" = "3.12" ] && [ "${{ github.ref }}" = "refs/heads/main" ]; then
            llm_provider="ollama"
            llm_args+=(
              --llm-model=llama3.2:1b
              --llm-context-mode=minimal
            )
          fi
          uv run pytest tests \
            -o "addopts=--cov=src/pytest_llm_report --cov-branch --cov-context=test --cov-report=" \
            --llm-provider="${llm_provider}" \
            --llm-report="${html_report}" \
            --llm-report-json="${json_report}" \
            --llm-pdf="${pdf_report}" \
            --llm-aggregate-run-id="${{ github.run_id }}-py${{ matrix.python-version }}" \
            "${llm_args[@]}"
          test_exit_code=$?

          uv run coverage xml
          uv run coverage report
          cov_exit_code=$?

          if [ $test_exit_code -ne 0 ]; then
            exit_code=$test_exit_code
          elif [ $cov_exit_code -ne 0 ]; then
             exit_code=$cov_exit_code
          else
             exit_code=0
          fi

          echo "exit_code=${exit_code}" >> "${GITHUB_OUTPUT}"
          exit 0

      - name: Upload coverage
        uses: codecov/codecov-action@v5
        if: matrix.python-version == '3.12'
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          disable_search: true
          fail_ci_if_error: false

      - name: Prepare coverage artifact
        if: matrix.python-version == '3.12'
        run: cp .coverage reports/coverage.py3.12

      - name: Upload report artifact
        if: matrix.python-version == '3.12'
        uses: actions/upload-artifact@v6
        with:
          name: report-py${{ matrix.python-version }}
          path: |
            reports/pytest_llm_report-py${{ matrix.python-version }}.json
            reports/pytest_llm_report-py${{ matrix.python-version }}.pdf
            reports/coverage.py${{ matrix.python-version }}
          retention-days: 7

      - name: Fail if tests failed
        if: steps.pytest.outputs.exit_code != '0'
        run: exit 1

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Install dependencies
        run: uv sync

      - name: Lint
        run: uv run ruff check .

      - name: Format check
        run: uv run ruff format --check .

  # Aggregate reports and deploy to GitHub Pages (main branch only)
  # This job builds both docs AND test reports to avoid overwriting each other
  report:
    needs: test
    runs-on: ubuntu-latest
    # Run on main push OR pull request
    if: always() && ((github.ref == 'refs/heads/main' && github.event_name == 'push') || github.event_name == 'pull_request')
    permissions:
      contents: write  # Required to push to gh-pages branch
      pull-requests: write # Required to post comments

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Install dependencies
        run: uv sync

      - name: Build docs
        run: uv tool run --from mkdocs-material --with mkdocs-git-revision-date-localized-plugin mkdocs build

      - name: Download all report artifacts
        uses: actions/download-artifact@v7
        with:
          pattern: report-py*
          path: collected-reports/
          merge-multiple: true

      - name: Debug - List collected reports
        run: ls -R collected-reports/

      - name: Generate aggregated report
        run: |
          mkdir -p site/reports
          uv run pytest --collect-only -q \
            --llm-aggregate-dir=collected-reports/ \
            --llm-aggregate-policy=merge \
            --llm-report=site/reports/index.html \
            --llm-report-json=site/reports/latest.json \
            --llm-coverage-source=collected-reports/coverage.py3.12

      - name: Copy latest PDF report
        run: |
          mkdir -p site/reports
          if [ -f "collected-reports/pytest_llm_report-py3.12.pdf" ]; then
            cp "collected-reports/pytest_llm_report-py3.12.pdf" "site/reports/latest.pdf"
          fi

      - name: Deploy to GitHub Pages
        uses: JamesIves/github-pages-deploy-action@v4
        with:
          branch: gh-pages
          folder: site
          # Clean only if main, but exclude PR folders
          clean: ${{ github.ref == 'refs/heads/main' }}
          clean-exclude: |
            pr-*
          # Target folder: root for main (empty = root), 'pr-{id}' for PRs
          target-folder: ${{ github.event_name == 'pull_request' && format('pr-{0}', github.event.number) || '' }}

      - name: Post Report Link to PR
        uses: actions/github-script@v8
        if: github.event_name == 'pull_request'
        with:
          script: |
            const prNumber = context.issue.number;
            const repo = context.repo.owner + "/" + context.repo.repo;
            const baseUrl = `https://${context.repo.owner}.github.io/${context.repo.repo}/pr-${prNumber}`;
            const reportUrl = `${baseUrl}/reports/`;

            const body = `<!-- pytest-llm-report-link -->
            ## 📊 Test Report & Docs Ready

            Preview the documentation and test results for this PR:

            * 📘 **[Documentation Preview](${baseUrl}/)**
            * result **[Interactive Test Report](${reportUrl})**
            `;

            // Find existing comment
            const { data: comments } = await github.rest.issues.listComments({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: prNumber,
            });

            const botComment = comments.find(c => c.body.includes('<!-- pytest-llm-report-link -->'));

            if (botComment) {
              await github.rest.issues.updateComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                comment_id: botComment.id,
                body: body
              });
            } else {
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: prNumber,
                body: body
              });
            }

  publish:
    needs: [test, lint]
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    permissions:
      id-token: write

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7

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
