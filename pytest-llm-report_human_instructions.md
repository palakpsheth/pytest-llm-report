# Development Plan Instructions

Use this file to coordinate a human + agent workflow for `pytest-llm-report_implementation.md`.

## Quick start
1. Read `AGENTS.md` and `pytest-llm-report_implementation.md`.
2. Pick one step only and send the prompt template below.
3. Require the handoff report and verify acceptance criteria before moving on.

## One-step workflow
- Choose the next step number and title.
- Send the prompt template.
- Review the response for changed files, tests, and acceptance checks.
- If anything is missing, ask for a focused fix before moving to the next step.

## Prompt templates
Initial prompt:
```
Implement STEP_X from `pytest-llm-report_implementation.md`.
Follow `AGENTS.md` exactly. Make the minimal change to satisfy the step.
Add or update tests and report the commands you ran.
Do not use network access. Do not include secrets or PHI.
At the end, provide: changed files, tests run, and how acceptance criteria are met.
```

Follow-up prompt:
```
Provide a handoff report using the template in `_dev_plan_instructions.md`.
If any acceptance criteria are not met, list what is missing.
```

## Required evidence (every step)
- Changed files
- Tests run (or explicitly skipped)
- Acceptance criteria check
- Open questions or risks

## Handoff report template
```
Step:
Summary:
Changed files:
Tests run:
Acceptance criteria check:
Open questions or risks:
```

## Step completion evidence (short checklist)

### Step 0
- Config defaults validated; warning codes centralized.
- Component contract docstrings present.
- Repo rootpath is the base for relative paths and traversal bounds.

### Step 1
- `schemas/report.schema.json` created and matches models.
- Schema version and run status fields present and tested.
- Per-test rerun fields, collection error fields, and sanitized invocation fields present.
- Schema includes `pytest_invocation` and `pytest_config_summary` field names.

### Step 2
- CLI/config options include LLM limits, cache TTL, evidence bundle, output capture, and sanitized invocation.
- Collect-only and dependency snapshot options present.
- xdist worker guard in place; Python 3.11-3.13 metadata set.
- Option names align with the plan (CLI `--llm-report`, `--llm-report-json`, `--llm-pdf`, `--llm-evidence-bundle`, `--llm-dependency-snapshot` and config `report_html`, `report_json`, `report_pdf`, `report_evidence_bundle`, `report_dependency_snapshot`).

### Step 3
- Outcomes, setup/teardown failures, and parametrization recorded.
- Collected/deselected counts, rerun attempts, and collection errors recorded.
- LLM markers and failed-test output capture (opt-in) handled.
- Marker names documented and registered (`llm_opt_out`, `llm_context`).

### Step 4
- Coverage mapping handles missing data, xdist combine, and path normalization.
- Coverage paths are repo-relative where possible.

### Step 5
- JSON includes schema_version, run status, warnings, and sanitized invocation summary.
- Deterministic ordering and atomic writes.
- Evidence bundle generated when enabled.

### Step 6
- HTML includes run status and collection errors.
- Captured output shown only when enabled and truncated.

### Step 7
- Noop provider and schema validation; warnings for non-none providers.

### Step 8
- Context modes implemented; per-test opt-out and override respected.
- Truncation warnings, repo-relative paths, non-UTF8 handling, symlink bounds.

### Step 9
- Cache keys include context hash; TTL enforced.
- LLM limits (max tests, concurrency, timeout) enforced.

### Step 10
- PDF output optional; missing Playwright handled with warning.

### Step 11
- Requirement and LLM markers registered and documented.
- Metadata merge is deterministic and namespaced.

### Step 12
- JSON/HTML hashes and optional HMAC signature.
- Dependency snapshot and evidence bundle hashes recorded when enabled.

### Step 13
- Missing coverage produces warnings, not failures.

### Step 14
- Pytester scenarios include collect-only, deselection, rerun, zero-test, collection errors.
- LLM marker behavior and output capture covered.

### Step 15
- Docs include full config reference with citations.
- Usage scenarios include compliance packaging, LLM setup, evidence bundle, output capture, and LLM markers.
- Docs list concrete CLI/config option names and marker names.

### Step 16
- CI tests and builds on Python 3.11, 3.12, 3.13.
- Release workflow builds artifacts on the same matrix before publish.

### Step 17
- LLM defaults remain none; secrets are not logged or stored.
- Default context excludes common secret files.

### Step 18
- Integration gate verifies Config defaults and schema compatibility.
- Run status fields and dependency snapshot defaults checked.
