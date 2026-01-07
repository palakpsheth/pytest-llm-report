# pytest-llm-report — Repo Blueprint, Usage, and Publishing Guide

This document consolidates everything we outlined:

1. The comprehensive repository tree
2. Explanations of file groups and their roles
3. Example end-user usage scenarios with **uv** and **pyproject.toml**
4. Public publishing steps (manual + automated via GitHub Actions)

> Note on naming: the standard Python packaging/config file is **`pyproject.toml`** (not `project.toml`).  
> In the examples below, configuration lives in `pyproject.toml`.

---

## 1) Comprehensive repository tree

```text
pytest-llm-report/
├─ .github/
│  ├─ workflows/
│  │  ├─ ci.yml
│  │  ├─ docs.yml
│  │  ├─ release.yml
│  │  ├─ provenance.yml
│  │  ├─ codeql.yml
│  │  ├─ snyk.yml
│  │  ├─ dependency-review.yml
│  │  ├─ ossf-scorecard.yml
│  │  ├─ trivy.yml
│  │  ├─ pip-audit.yml
│  │  └─ secret-scan.yml
│  ├─ codeql/
│  │  ├─ codeql-config.yml
│  │  └─ queries/
│  │     ├─ README.md
│  │     └─ python/
│  │        └─ custom-query.ql
│  ├─ ISSUE_TEMPLATE/
│  │  ├─ bug_report.yml
│  │  ├─ feature_request.yml
│  │  └─ security_report.md
│  ├─ dependabot.yml
│  ├─ PULL_REQUEST_TEMPLATE.md
│  ├─ FUNDING.yml
│  └─ SECURITY.md
├─ docs/
│  ├─ index.md
│  ├─ getting-started.md
│  ├─ configuration.md
│  ├─ providers.md
│  ├─ coverage.md
│  ├─ report-format.md
│  ├─ privacy.md
│  ├─ security.md
│  ├─ troubleshooting.md
│  ├─ adr/
│  │  ├─ 0001-coverage-contexts.md
│  │  ├─ 0002-llm-providers.md
│  │  └─ 0003-report-formats.md
│  └─ assets/
│     ├─ screenshots/
│     │  ├─ report-summary.png
│     │  └─ report-details.png
│     └─ diagrams/
│        └─ architecture.svg
├─ examples/
│  ├─ minimal/
│  │  ├─ pyproject.toml
│  │  ├─ pytest.ini
│  │  ├─ .coveragerc
│  │  ├─ src/example_pkg/
│  │  │  ├─ __init__.py
│  │  │  └─ core.py
│  │  └─ tests/
│  │     ├─ test_core.py
│  │     └─ conftest.py
│  ├─ with-ollama/
│  │  ├─ README.md
│  │  ├─ pyproject.toml
│  │  ├─ pytest.ini
│  │  └─ .coveragerc
│  └─ with-litellm/
│     ├─ README.md
│     ├─ pyproject.toml
│     ├─ pytest.ini
│     └─ .coveragerc
├─ src/
│  └─ pytest_llm_report/
│     ├─ __init__.py
│     ├─ __about__.py
│     ├─ plugin.py
│     ├─ options.py
│     ├─ collector.py
│     ├─ coverage_map.py
│     ├─ report_writer.py
│     ├─ render.py
│     ├─ models.py
│     ├─ cache.py
│     ├─ prompts.py
│     ├─ errors.py
│     ├─ util/
│     │  ├─ __init__.py
│     │  ├─ fs.py
│     │  ├─ hashing.py
│     │  ├─ ranges.py
│     │  └─ time.py
│     ├─ llm/
│     │  ├─ __init__.py
│     │  ├─ base.py
│     │  ├─ noop.py
│     │  ├─ ollama.py
│     │  ├─ litellm_provider.py
│     │  └─ schemas.py
│     ├─ templates/
│     │  ├─ report.html.j2
│     │  ├─ summary.html.j2
│     │  ├─ test_row.html.j2
│     │  └─ components/
│     │     ├─ filters.html.j2
│     │     ├─ badges.html.j2
│     │     └─ coverage_list.html.j2
│     └─ static/
│        ├─ report.css
│        ├─ report.js
│        └─ vendor/
│           └─ pico.min.css
├─ tests/
│  ├─ conftest.py
│  ├─ test_smoke_pytester.py
│  ├─ test_options.py
│  ├─ test_collector.py
│  ├─ test_coverage_map.py
│  ├─ test_render.py
│  ├─ test_report_writer.py
│  ├─ test_llm_contract.py
│  ├─ test_cache.py
│  ├─ test_ranges.py
│  └─ fixtures/
│     ├─ sample_project/
│     │  ├─ pyproject.toml
│     │  ├─ pytest.ini
│     │  ├─ .coveragerc
│     │  ├─ src/sample_pkg/
│     │  │  ├─ __init__.py
│     │  │  └─ core.py
│     │  └─ tests/
│     │     ├─ test_core.py
│     │     └─ conftest.py
│     └─ golden/
│        ├─ expected_report_minimal.html
│        └─ expected_report_minimal.json
├─ scripts/
│  ├─ dev.sh
│  ├─ fmt.sh
│  ├─ lint.sh
│  ├─ test.sh
│  ├─ build_wheel.sh
│  ├─ verify_local_ollama.py
│  ├─ build_report_pdf.py
│  └─ security/
│     ├─ run_snyk_local.sh
│     ├─ run_codeql_local.md
│     ├─ run_trivy_local.sh
│     ├─ run_pip_audit_local.sh
│     └─ policy_checks.sh
├─ policies/
│  ├─ threat-model.md
│  ├─ privacy.md
│  ├─ disclosures.md
│  ├─ llm-data-handling.md
│  └─ security-baseline.md
├─ .editorconfig
├─ .gitignore
├─ .gitattributes
├─ .pre-commit-config.yaml
├─ .snyk
├─ CHANGELOG.md
├─ CODE_OF_CONDUCT.md
├─ CONTRIBUTING.md
├─ LICENSE
├─ README.md
├─ SECURITY.md
├─ mkdocs.yml
├─ pyproject.toml
├─ uv.lock
└─ requirements-security.txt
```

---

## 2) Explanations of groups and file types

### A) The core value: how the plugin works

The plugin combines **pytest results** (test status/duration) with **per-test coverage mapping** (which files/lines each test executed), and optionally uses an **LLM** to write plain-English annotations:
- scenario (“what this test verifies”)
- why-needed (“what regression/bug it prevents”)
- key assertions (“the critical checks performed”)

To minimize repeated code, the design leans on:
- **pytest** for test discovery/execution and hook lifecycle
- **pytest-cov** for collecting coverage with **per-test contexts**
- **coverage.py** for reading `.coverage` data and mapping contexts → line numbers
- **Jinja2** + static assets for HTML rendering
- optional **Playwright** for HTML → PDF
- optional LLM providers (local **Ollama** or cloud via **LiteLLM**)

---

### B) `.github/` — automation and project health

#### `.github/workflows/`

- `ci.yml` — lint + unit tests + integration tests (pytester-based) on PRs/pushes  
- `docs.yml` — build docs (MkDocs) and optionally deploy (GitHub Pages)  
- `release.yml` — build wheel/sdist and publish to PyPI on tags  
- `provenance.yml` — optional supply-chain provenance/attestations  
- `codeql.yml` — CodeQL static analysis → SARIF in GitHub Security tab  
- `snyk.yml` — Snyk dependency scan and/or SAST (skip fork PRs if using secrets)  
- `dependency-review.yml` — GitHub dependency review action on PRs  
- `ossf-scorecard.yml` — OSSF Scorecard posture checks  
- `trivy.yml` — optional container/IaC scanning (remove if you don’t ship images)  
- `pip-audit.yml` — tokenless Python dependency vuln scan  
- `secret-scan.yml` — optional secret scanning (gitleaks/trufflehog style)

#### `.github/codeql/`
- `codeql-config.yml` ignores directories and enables custom queries.
- `queries/` holds optional custom CodeQL queries.

#### Other GitHub metadata
- `dependabot.yml` creates dependency update PRs.
- `PULL_REQUEST_TEMPLATE.md` guides contributors.
- `.github/SECURITY.md` enables security reporting UI.

---

### C) `docs/` — end-user docs + architecture decisions

- Setup and configuration guides: `getting-started.md`, `configuration.md`
- Deep dives: `coverage.md`, `providers.md`, `report-format.md`
- Trust docs: `privacy.md`, `security.md`
- ADRs in `docs/adr/` record key design decisions.

---

### D) `examples/` — copy/paste starter projects

- `minimal/`: no LLM, report only
- `with-ollama/`: local LLM annotations
- `with-litellm/`: cloud providers via LiteLLM

---

### E) `src/pytest_llm_report/` — plugin implementation

**Primary modules**
- `plugin.py`: registers hooks; orchestrates end-of-session report generation
- `options.py`: reads CLI + `pyproject.toml` (`[tool.pytest_llm_report]`)
- `collector.py`: collects per-test outcomes/durations/failures via pytest hooks
- `coverage_map.py`: reads `.coverage` and computes per-test touched files + line ranges
- `prompts.py`: prompt contract + response schema
- `llm/`: providers (noop / ollama / litellm) + schema normalization
- `cache.py`: LLM response cache (prompt-hash keyed)
- `render.py` + `templates/` + `static/`: HTML generation

**Supporting modules**
- `models.py`: dataclasses/types for report rows
- `errors.py`: structured errors
- `util/`: range compression, hashing, FS helpers, etc.

---

### F) `tests/` — test strategy

- Unit tests for helpers and rendering logic.
- `pytester` integration tests (`test_smoke_pytester.py`) that create and run a sample project.
- Golden files (`fixtures/golden/`) for stable rendering when LLM is disabled.

---

### G) `scripts/` — developer and local security helpers

Convenience scripts for contributors and maintainers, plus local security run scripts.

---

### H) `policies/` — LLM and security posture docs

Threat model, data handling, disclosures, and baseline security expectations.

---

### I) Root files

- `pyproject.toml`: package metadata, deps, pytest entrypoint, tool configs
- `uv.lock`: reproducible dev lockfile
- `.snyk`: Snyk ignore/policy file
- `README.md`, `LICENSE`, `CHANGELOG.md`: OSS standard docs

---

## 3) Example end-user usage scenarios (uv + pyproject.toml)

### Scenario 1 — No LLM: status + per-test line ranges (HTML)

**Install**
```bash
uv add --dev pytest pytest-cov pytest-llm-report
uv sync
```

**pyproject.toml**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
  "-ra",
  "--cov=my_pkg",
  "--cov-context=test",
  "--cov-report=",
  "--llm-report=reports/pytest_llm_report.html",
]

[tool.pytest_llm_report]
provider = "none"
report_json = "reports/pytest_llm_report.json"
max_files_per_test = 8
omit_tests_from_coverage = true
include_phase = "run"
```

**Run**
```bash
uv run pytest
```

---

### Scenario 2 — Local LLM (Ollama): scenario + why-needed + key assertions

**Install**
```bash
uv add --dev pytest pytest-cov pytest-llm-report
uv sync
```

**Pull model**
```bash
ollama pull qwen2.5-coder:14b
```

**pyproject.toml**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
  "-ra",
  "--cov=my_pkg",
  "--cov-context=test",
  "--cov-report=",
  "--llm-report=reports/pytest_llm_report.html",
]

[tool.pytest_llm_report]
provider = "ollama"
ollama_host = "http://127.0.0.1:11434"
model = "qwen2.5-coder:14b"
cache_dir = ".pytest_llm_cache"
max_files_per_test = 12
max_prompt_chars = 60000
include_phase = "run"
```

**Run**
```bash
uv run pytest
```

---

### Scenario 3 — HTML + PDF output for CI artifacts

**Install PDF deps**
```bash
uv add --dev playwright
uv sync
python -m playwright install chromium
```

**pyproject.toml**
```toml
[tool.pytest.ini_options]
addopts = [
  "--cov=my_pkg",
  "--cov-context=test",
  "--cov-report=",
  "--llm-report=artifacts/pytest_llm_report.html",
  "--llm-pdf=artifacts/pytest_llm_report.pdf",
]

[tool.pytest_llm_report]
provider = "none"
```

**Run**
```bash
uv run pytest
```

---

### Scenario 4 — “Describe one test” (optional CLI entry point)

If you ship a console script (e.g., `pytest-llm-report`):

```bash
uv run pytest-llm-report describe "tests/test_api.py::test_create_user_unauthorized"
```

---

## 4) Public publishing using uv (manual + automated)

### A) Preflight checklist

1. Complete metadata in `pyproject.toml` (name, version, license, readme, classifiers).
2. Ensure templates/static assets are included in the built wheel/sdist.
3. Register the pytest plugin entry point under `pytest11`.
4. Run local build + smoke import.

---

### B) Manual publishing with uv (token-based)

1. Create a PyPI account + enable 2FA.
2. Create a PyPI API token.
3. Build and publish:

```bash
uv build
uv publish --token "pypi-***"
```

**Recommended:** publish to TestPyPI first, validate, then publish to PyPI.

---

### C) Automated publishing (recommended): GitHub Actions + Trusted Publishing (OIDC)

This avoids storing a long-lived PyPI token in GitHub secrets.

**Steps**
1. Create/claim your PyPI project.
2. Configure a PyPI “Trusted Publisher” pointing to:
   - GitHub repo
   - workflow file (e.g., `.github/workflows/release.yml`)
   - optional environment name (e.g. `pypi`)
3. In `release.yml`, set:
   - `permissions: id-token: write`
   - build dists (e.g., `uv build`)
   - publish using OIDC-compatible action (common pattern) or your chosen tooling
4. Publish by pushing a semver tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

---

### D) Security scans (recommended for public repos)

Enable the workflows under `.github/workflows/`:
- CodeQL (static analysis → SARIF)
- Dependency Review
- pip-audit (tokenless vuln scan)
- Snyk (optional; typically skips fork PRs)

---

## Appendix: suggested `.coveragerc`

```ini
[run]
branch = True

[html]
show_contexts = True
```

---

Generated on: 2026-01-07
