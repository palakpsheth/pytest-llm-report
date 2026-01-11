# AGENTS.md — Agent instructions for `pytest-llm-report`

This file is the single source of truth for how coding agents should work in this repository.

## Compatibility with Claude Code / other agents

- **Canonical instructions live in `AGENTS.md`** (this file).
- **Claude Code auto-loads `CLAUDE.md`** by default. If you use Claude Code, create a tiny `CLAUDE.md` that contains only:
  - `@AGENTS.md`
  This keeps one shared source of instructions while still working with Claude Code’s auto-context behavior.

> Keep this file concise and universally applicable. Prefer “progressive disclosure”: point to docs for details instead of stuffing everything here.

---

## Project goal (what we’re building)

A public **pytest plugin** that generates a **human-friendly test report** (HTML + JSON, optional PDF) containing:

- Test inventory + status (pass/fail/skip/xfail) + duration
- Per-test **covered files + line ranges** (using `pytest-cov` + coverage contexts)
- Optional **LLM-generated annotations** per test:
  - *Scenario*: what the test verifies in plain English
  - *Why needed*: what regression/bug it prevents
  - *Key assertions*: the critical checks performed

**Non-goals**
- Re-implement coverage collection (we rely on `pytest-cov`/coverage.py)
- Require a networked LLM by default (LLM is opt-in; local-first preferred)

---

## Guardrails (must-follow)

1. **Privacy + safety**
   - Default to `provider = "none"` (no LLM calls).
   - Never send secrets, tokens, private URLs, or customer data to any LLM provider.
   - When LLM is enabled, keep prompts minimal: only the test code + very small set of relevant production snippets.

2. **Minimize dependencies**
   - Prefer existing, mature libraries over new ones.
   - If adding a dependency, justify it in the PR and add coverage/tests.

3. **Deterministic tools first**
   - Use linters/formatters/typecheckers for style and correctness.
   - Do not ask the LLM to “be a linter” or to enforce formatting rules—run the tools.

4. **Small, reviewable changes**
   - Make incremental edits and keep diffs tight.
   - Update tests and docs with every behavior change.

---

## Repo map (where to change what)

- `src/pytest_llm_report/plugin.py`
  pytest plugin entry point + session orchestration (report generation trigger)

- `src/pytest_llm_report/options.py`
  CLI flags + config loading from `pyproject.toml` (`[tool.pytest_llm_report]`)

- `src/pytest_llm_report/collector.py`
  Collects per-test outcomes via pytest hooks (nodeid, outcome, duration, errors)

- `src/pytest_llm_report/coverage_map.py`
  Converts coverage contexts → per-test covered files/line ranges (core feature)

- `src/pytest_llm_report/llm/`
  Providers:
  - `noop.py` (default)
  - `ollama.py` (local)
  - `litellm_provider.py` (cloud via LiteLLM)
  - `schemas.py` (response schema normalization/validation)

- `src/pytest_llm_report/render.py` + `templates/` + `static/`
  HTML report rendering; keep templates simple and maintainable

- `tests/`
  Unit tests + `pytester` integration tests (must be kept green)

- `docs/` and `examples/`
  End-user documentation and runnable examples (prevent docs rot)

---

## Dev environment (use `uv`)

### Setup
```bash
uv sync
```

### Run tests
```bash
uv run pytest
```

### Run a single test quickly
```bash
uv run pytest -q tests/path/test_file.py::test_name
```

### Lint / format / typecheck (project standards)
(Exact tool choices come from `pyproject.toml`; keep commands here stable.)
```bash
uv run ruff check .
uv run ruff format .
# if used:
uv run mypy .
# or:
uv run pyright
```

### Build distributions
```bash
uv build
```

---


## Test-driven development (TDD) + coverage target (mandatory)

We follow **test-driven development** by default:

- For non-trivial changes, **write or update tests first** (or at minimum in the same commit) to capture expected behavior.
- Prefer **fast unit tests** for pure logic, and add **`pytester` integration tests** for plugin wiring / real pytest runs.
- Use **golden files** for report rendering stability; update them only when output changes are intentional.

### Coverage policy

- The repository’s **total test coverage must remain > 90%** at all times.
- If a change would reduce coverage, add tests to restore coverage before merging.
- Do not “game” coverage (e.g., excluding large modules without justification). Any exclusions must be:
  - minimal,
  - documented in `pyproject.toml` / `.coveragerc`,
  - justified in the PR description.

### Practical workflow

- Run locally:
  - `uv run pytest`
  - `uv run pytest --cov=pytest_llm_report --cov-report=term-missing`
- In CI, fail the build if coverage falls below 90% (e.g., via `--cov-fail-under=90`).


## How to work on tasks (agent workflow)

When asked to implement or modify behavior:

1. **Clarify intent** by reading:
   - relevant module(s) (see “Repo map”)
   - existing tests that cover the area
   - docs and examples that might need updates

2. **Propose a short plan** (3–7 bullets) before coding when the change is non-trivial.

3. **Implement with tests**
   - Add/adjust unit tests
   - Add/adjust `pytester` tests when behavior affects real pytest runs or report outputs
   - Update golden files only when output format changes intentionally

4. **Verify locally**
   - Run targeted tests first, then full suite
   - Ensure report artifacts are generated in integration tests

5. **Polish**
   - Keep output stable (avoid unnecessary HTML/JSON churn)
   - Update docs/examples for user-facing changes

---

## Coverage mapping requirements (core feature)

- We rely on `pytest-cov` with **coverage contexts**:
  - users run with `--cov-context=test`
  - plugin reads `.coverage` and maps contexts to tests
- Prefer using the **`run`** phase context (`nodeid|run`) rather than setup/teardown to reduce noise.
- Output should:
  - collapse line numbers into compact ranges (e.g., `12-18, 33, 40-41`)
  - omit test files by default (configurable)
  - be resilient when coverage data is missing or contexts aren’t enabled (degrade gracefully)

---

## LLM annotations (opt-in)

### Contract
LLM output must be parsed/validated into a stable schema (JSON). Keep it short:

- `scenario`: 1–3 sentences
- `why_needed`: 1–3 sentences
- `key_assertions`: 3–8 bullets
- `confidence`: optional (0–1)

### Caching
- Use a deterministic cache key:
  - provider + model + prompt template version + file hashes
- Cache lives in `.pytest_llm_cache/` by default (configurable).

### Prompt hygiene
- Never include entire repo context in a single prompt.
- Prefer:
  - the test body
  - docstring / comments for intent
  - minimal referenced production functions/classes (when easy to locate)
- If the agent can’t find enough info, it must say so explicitly rather than hallucinating.

---

## Report output requirements

- Always produce:
  - HTML report (`--llm-report=...`)
  - JSON report (configurable output path)
- Optional:
  - PDF (generated from HTML via Playwright; must be optional dependency)
- Summary table should include (at minimum):
  - nodeid
  - status
  - duration
  - covered files + line ranges (collapsible)
  - scenario/why/assertions when LLM enabled

---

## Publishing and releases (high-level)

- Use semantic versioning.
- Release checklist:
  1. Update `CHANGELOG.md`
  2. Ensure `uv run pytest` is green
  3. `uv build` produces wheel + sdist
  4. Tag `vX.Y.Z` to trigger automated publishing (if configured)

---

## “If you’re stuck”

- Prefer reading the relevant code + tests rather than guessing.
- If behavior involves pytest internals, add a `pytester` test to lock it down.
- If output format is unclear, implement the simplest version, then iterate with golden tests.
