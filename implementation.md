# pytest-llm-report Implementation Plan

This plan is optimized for small, fast agentic coding models. Each step includes extra context, file targets, acceptance criteria, and an agent prompt. Follow AGENTS.md as the single source of truth.

## Global constraints and standards
- Default provider must remain "none" (no LLM calls) and must never transmit secrets, tokens, private URLs, or PHI.
- Never include the entire repo in a single prompt. Even "complete" context is bounded by size caps and file filters.
- Use pytest plugin best practices: register via `pytest11`, use pytest hooks, keep IO in `pytest_sessionfinish`.
- Keep diffs small and reviewable; write tests in the same change.
- Coverage for the repo must stay above 90 percent.
- Use `uv` for all dev tasks (`uv run pytest`, `uv run ruff check .`, `uv run ruff format .`).
- Deterministic output: stable sorting, UTC timestamps, fixed schema_version, explicit warning list.
- Cross-platform paths: normalize separators and casefold on Windows.
- Use only ASCII in new files unless the file already uses Unicode.
- First-class support and testing must target Python 3.11, 3.12, and 3.13.

## Regulatory context (CAP/CLIA/FDA, NGS assay verification)
- Reports can be used in formal verification packages, so provenance, reproducibility, and traceability must be explicit.
- Output must be deterministic and tamper-evident where possible (hashes, optional signatures).
- Reports must support mapping tests to requirement IDs and versioned artifacts.
- Avoid inclusion of PHI or customer data by default. Allow user-provided metadata with explicit opt-in.
- Provide a manifest of generated artifacts with hashes for audit trails.

## Edge cases and scenarios to cover (must add tests)
- Missing `.coverage` or missing `--cov-context=test` (no contexts).
- Coverage only in setup/teardown or test fails before run.
- xdist or parallel runs producing `.coverage.*` files.
- Collect-only runs and runs with zero collected tests.
- Deselected tests and keyword selection (`-k`, `-m`) affecting totals.
- Rerun/flaky outcomes from `pytest-rerunfailures`.
- Interrupted runs (KeyboardInterrupt), maxfail early stop, and non-zero exit codes.
- Collection errors (syntax/import errors during collection).
- Parameterized tests, long nodeids, and nodeids with special characters.
- Parameter values are sensitive or very large; raw values are opt-in only and must be redacted and truncated.
- Windows path separators and case-insensitive paths.
- Non-Python files or compiled extensions in coverage data.
- Non-UTF8 source files in prompts or report rendering.
- Invalid or unwritable output paths (missing dirs, read-only).
- Coverage data timing (read after pytest-cov finalizes output).
- Very large test suites (performance and UI usability).
- Large repos (skip venv, site-packages, and avoid symlink traversal outside repo root).
- LLM provider failures, timeouts, or rate limits.
- LLM context truncation due to size budget.
- HTML and JSON escaping for unusual characters.
- Secrets accidentally appearing in logs or report metadata.
- Evidence bundle output path errors or partial bundle generation.
- Captured stdout/stderr too large or contains sensitive data (must be opt-in and truncated).
- Aggregation across multiple runs: mismatched schema versions, missing or duplicate run IDs, partial runs, and mixed aggregation policies.
- Coverage append with multiple runs: stale `.coverage` data, missing contexts from earlier runs, and inconsistent run groups.

---

## Step 0: Component boundaries and integration contracts

**Objective**: Define clean component boundaries so agentic AI can implement modules in isolation without breaking integration.

**Context**:
- Keep modules small, pure where possible, and connected through explicit dataclass inputs and outputs.
- All components should accept a typed config object rather than reading env or CLI directly.
- Keep warnings centralized with codes and include them in report metadata.
- Define explicit contracts between components so agents can implement in parallel:
  - options -> Config
  - collector -> list[TestCaseResult]
  - coverage_map -> dict[nodeid, list[CoverageEntry]]
  - prompts/context -> PromptPayload + ContextSummary
  - llm provider -> LlmAnnotation
  - render -> HTML string
  - report_writer -> JSON + HTML + artifact manifest
- Use pytest `config.rootpath` (or a configured repo root) as the canonical base for relative paths and traversal bounds.

**Agent work split (parallelizable components)**:
| Component | Owner role | Inputs | Outputs | Dependencies |
| --- | --- | --- | --- | --- |
| options + config | Agent A | CLI args, `pyproject.toml` | Config dataclass | none |
| collector | Agent B | pytest hooks, Config | list[TestCaseResult] | Config |
| coverage_map | Agent C | `.coverage` files, Config | dict[nodeid, list[CoverageEntry]] | Config |
| prompts/context | Agent D | tests, Config, repo files | PromptPayload + ContextSummary | Config, util.fs |
| llm providers + cache | Agent E | PromptPayload, Config | LlmAnnotation | cache, prompts |
| report_writer | Agent F | results, coverage, LLM | JSON + HTML + artifact manifest | models, render |
| render/templates | Agent G | ReportRoot | HTML string | templates, static |
| docs/examples | Agent H | feature matrix | docs + examples | schema, options |

**Handoff checklist (per component)**:
- options + config: Config defaults match plan, validation tests added, new CLI options documented.
- collector: unit tests cover outcomes, parametrization, and setup/teardown; output fields match schema.
- coverage_map: tests cover missing coverage, xdist combine, and path normalization; omissions and warnings are deterministic.
- prompts/context: tests cover all context modes, truncation, file filters, and parameter id inclusion.
- llm providers + cache: tests cover cache keys, missing auth, and error handling without secrets logging.
- report_writer: JSON schema version and artifact manifest included; deterministic ordering; warnings surfaced.
- render/templates: golden fixtures updated intentionally; HTML escaping verified.
- docs/examples: config reference complete, citations added, examples runnable.

**Files to touch**:
- `src/pytest_llm_report/models.py`
- `src/pytest_llm_report/options.py`
- `src/pytest_llm_report/errors.py`
- `tests/test_models.py`

**Acceptance criteria**:
- A Config dataclass is defined with all options and defaults.
- Each component has a clear function or class interface and accepts Config explicitly.
- Warning codes are defined in one place and referenced by components.

**Agent prompt**:
"Define a Config dataclass in `options.py` and ensure all components accept it rather than reading global state. Add or update `errors.py` to centralize warning codes. Document component contracts in `models.py` docstrings and add a unit test verifying defaults and option types."

---

## Step 1: Define report schema and run metadata

**Objective**: Establish stable, versioned data models and JSON schema that can be used in regulatory submissions.

**Context**:
- Stable JSON is required for automated review and evidence packaging.
- Include run metadata: start/end time (UTC), duration, pytest version, plugin version, OS, Python, git commit SHA, dirty flag, tool config hash.
- Include a warning list and an artifact manifest (output file paths + hashes).
- Provide a JSON schema file for the report to aid validation in compliance workflows.
- Include parameterization fields in the schema (e.g., `param_id`, optional `param_summary`).
- Include run status fields: pytest exit code, interrupted flag, collect-only flag, collected count, selected count, deselected count, and rerun count.
- Include per-test rerun fields (attempt count and final outcome when rerunfailures is used).
- Include collection error summaries and early-stop indicators in the schema.
- Include sanitized pytest invocation and config summary fields in run metadata.
- Include per-test LLM controls in the schema (llm_opt_out flag, llm_context_override when provided).
- Include optional captured output fields for failed tests (stdout/stderr, truncated).
  - Field names: `pytest_invocation` (sanitized args list) and `pytest_config_summary` (sanitized ini options).
  - Per-test fields: `llm_opt_out`, `llm_context_override`, `captured_stdout`, `captured_stderr`.
- Include aggregation metadata: `run_id`, `run_group_id`, `is_aggregated`, `aggregation_policy`, `run_count`, and `source_reports` (path + sha256).

**Files to touch**:
- `src/pytest_llm_report/models.py`
- `src/pytest_llm_report/__about__.py`
- `src/pytest_llm_report/errors.py`
- `docs/report-format.md`
- `schemas/report.schema.json`
- `tests/test_models.py`

**Acceptance criteria**:
- Models are type-hinted dataclasses.
- JSON serialization is deterministic (sorted keys, stable field ordering).
- Schema version is embedded in output and used in tests.
- A JSON schema file exists and matches the output fields documented in `docs/report-format.md`.
- Parameterization fields are present in the schema and JSON output for parametrized tests.
- Run status fields are present in the schema and output, with deterministic defaults.
- Per-test rerun fields are present and default to zero or null when not applicable.
- Collection error summaries are present when collection fails.
- Sanitized pytest invocation/config summary fields are present with redaction rules documented.
- LLM control fields are present and default to false or null.
- Captured output fields are present only when enabled and truncated deterministically.
- Aggregation fields are present and defaulted when aggregation is disabled.

**Agent prompt**:
"Read `AGENTS.md` and draft dataclasses in `src/pytest_llm_report/models.py` for report outputs. Include RunMeta, TestCaseResult, CoverageEntry, LlmAnnotation, ReportWarning, ArtifactEntry, and ReportRoot with `schema_version`. Keep serialization deterministic. Add a JSON schema file at `schemas/report.schema.json` and sync fields with `docs/report-format.md`. Add unit tests in `tests/test_models.py` verifying required fields and schema_version."

---

## Step 2: Plugin entry point and configuration skeleton

**Objective**: Wire the plugin into pytest and expose CLI/config options, including LLM context controls.

**Context**:
- Follow pytest plugin conventions: `pytest_addoption` and `pytest_configure`.
- Provide a `--llm-report` path and `--llm-report-json` path. Default JSON path should be near HTML path unless configured.
- Add LLM context controls: `llm_context_mode` (minimal, balanced, complete), `llm_context_bytes`, `llm_context_file_limit`, `llm_context_include_globs`, `llm_context_exclude_globs`.
- Add LLM parameter handling controls: `llm_include_param_values` (default false) and `llm_param_value_max_chars`.
- Add LLM execution controls: `llm_max_tests`, `llm_max_concurrency`, and `llm_timeout_seconds`.
- Add LLM cache controls: `llm_cache_ttl_seconds`.
- Add report controls for collect-only runs: `report_collect_only` (default true) to generate inventory-only output.
- Add optional dependency snapshot output path (off by default).
- Add optional evidence bundle output path to package JSON/HTML/PDF/manifest (off by default).
- Add output capture controls: `capture_failed_output` (default false) and `capture_output_max_chars`.
- Add sanitized pytest invocation/config summary toggle (default true) and redaction rules.
- Explicit option names:
  - CLI outputs: `--llm-report` (HTML), `--llm-report-json`, `--llm-pdf`, `--llm-evidence-bundle`, `--llm-dependency-snapshot`.
  - Config outputs: `report_html`, `report_json`, `report_pdf`, `report_evidence_bundle`, `report_dependency_snapshot`.
  - Output capture: `capture_failed_output`, `capture_output_max_chars`.
  - Invocation summary: `include_pytest_invocation`, `invocation_redact_patterns`.
  - Collect-only behavior: `report_collect_only`.
- Add aggregation controls:
  - CLI: `--llm-aggregate-dir`, `--llm-aggregate-policy`, `--llm-aggregate-run-id`, `--llm-aggregate-group-id`.
  - Config: `aggregate_dir`, `aggregate_policy`, `aggregate_run_id`, `aggregate_group_id`, `aggregate_include_history`.
- "Complete" is a maximum safe mode and still must not send the entire repo; it must respect size caps and file filters.
- For cloud providers, prefer API keys from environment variables or config files, not CLI flags, to avoid accidental logging.
- Ensure the report generation runs only on the controller process under xdist to avoid duplicates.

**Files to touch**:
- `src/pytest_llm_report/plugin.py`
- `src/pytest_llm_report/options.py`
- `pyproject.toml`
- `tests/test_options.py`

**Acceptance criteria**:
- `pytest --help` shows the new options.
- Config can be provided via `[tool.pytest_llm_report]`.
- Defaults: provider=none, context_mode=minimal, conservative size caps.
- Invalid values produce clear errors and do not run.
- `requires-python` and classifiers declare support for Python 3.11, 3.12, and 3.13.
- Under xdist, only the controller writes reports; workers skip report generation.
- LLM execution and cache controls are validated and documented.
- Collect-only mode produces an inventory report when enabled.
- Evidence bundle output is validated and can be disabled independently.
- Aggregation options are validated; invalid policies or missing aggregate_dir produce clear errors.

**Agent prompt**:
"Add pytest plugin entry point in `pyproject.toml` under `pytest11`. Implement `pytest_addoption` and config parsing in `options.py`. Add LLM context options, parameter-value controls, execution limits, cache TTL, and LLM marker options with validation. Add options for collect-only report generation, optional dependency snapshot output, evidence bundle output, output capture for failed tests, and sanitized pytest invocation summary. Keep defaults provider=none and context_mode=minimal. Add tests in `tests/test_options.py` for CLI vs pyproject precedence and invalid values. Ensure `requires-python` and classifiers include 3.11, 3.12, 3.13. Add a guard to skip report generation on xdist workers."

---

## Step 3: Collector for test outcomes and durations

**Objective**: Capture per-test results (pass/fail/skip/xfail), duration, and error info, including setup and teardown failures.

**Context**:
- Use `pytest_runtest_logreport` for outcomes and durations.
- Track nodeid and parameterized tests precisely; do not collapse ids.
- Capture parameter ids (`callspec.id`) for parameterized tests and include them in the test record.
- Do not collect raw parameter values by default to avoid sensitive data exposure.
- Record errors in a short, deterministic form (first line + short traceback if needed) and include phase (setup/run/teardown).
- If raw parameter values are enabled, store only a redacted and truncated summary in the report (no full values).
- Track collected and deselected counts via collection hooks and record selection filters.
- Detect rerun outcomes from `pytest-rerunfailures` (outcome `rerun`) and record attempts.
- Support collect-only mode by recording inventory without run-phase results.
- Capture collection errors (from `pytest_collectreport`) and include short summaries.
- Capture per-test LLM markers: `llm_opt_out` and `llm_context` override.
- Marker names: `@pytest.mark.llm_opt_out` and `@pytest.mark.llm_context("minimal" | "balanced" | "complete")`.
- Optionally capture stdout/stderr for failed tests only, truncated and redacted.

**Files to touch**:
- `src/pytest_llm_report/collector.py`
- `tests/test_collector.py`
- `tests/test_smoke_pytester.py`

**Acceptance criteria**:
- Handles skipped/xfail/xpass correctly.
- Captures setup/teardown failures without crashing.
- Works with parameterized tests and xdist.
- Parameter ids are recorded and included in JSON output.
- Parameter summaries, when enabled, are redacted and truncated deterministically.
- Collected and deselected counts are recorded and surfaced in run metadata.
- Rerun attempts are recorded when rerunfailures is present.
- Collect-only mode produces inventory entries with a clear status.
- Collection errors are captured and included in the report.
- LLM marker settings are captured per test when present.
- Failed-test output capture is opt-in and truncated deterministically.

**Agent prompt**:
"Implement a collector class to capture nodeid, outcome, duration, error summary, and phase using pytest hooks. Ensure correct handling of skip/xfail/xpass and setup or teardown failures. Record parameter ids (callspec.id) without raw values by default, and add an optional redacted/truncated parameter summary when enabled. Track collected and deselected counts during collection. Detect rerun outcomes and record attempts when rerunfailures is present. Support collect-only mode by producing inventory entries. Capture collection errors via `pytest_collectreport` and include short summaries. Capture per-test LLM markers (opt-out and context override) and optional failed-test stdout/stderr with truncation. Add unit tests in `tests/test_collector.py` and a pytester integration test for mixed outcomes, parametrization, collection errors, output capture, and collect-only."

---

## Step 4: Coverage data ingestion and context mapping

**Objective**: Read coverage data and map test contexts to file and line ranges.

**Context**:
- Must use `pytest-cov` contexts (`--cov-context=test`).
- Prefer the run-phase context (`nodeid|run`) and ignore setup/teardown by default.
- Combine `.coverage.*` files if running under xdist or parallel mode.
- Normalize paths across platforms (Windows separators, case-insensitive comparisons).
- Skip missing files or non-Python entries gracefully.
- Read coverage data only after pytest-cov finalizes output (use correct hook ordering).
- Prefer repo-relative paths in coverage output to avoid leaking absolute paths.

**Files to touch**:
- `src/pytest_llm_report/coverage_map.py`
- `src/pytest_llm_report/util/ranges.py`
- `src/pytest_llm_report/util/fs.py`
- `tests/test_coverage_map.py`
- `tests/test_ranges.py`

**Acceptance criteria**:
- Missing coverage data does not crash the run.
- Omits test files by default when configured.
- Line ranges are compacted (e.g., 1-3, 5).
- Path normalization is deterministic across platforms.
- Coverage paths are reported relative to the repo root when possible.

**Agent prompt**:
"Implement coverage context mapping in `coverage_map.py` using coverage.py APIs. Combine `.coverage.*` data when present. Parse contexts like `nodeid|run` and ignore setup/teardown unless configured. Add range compression helpers in `util/ranges.py`, path normalization in `util/fs.py`, and unit tests for range compaction and context mapping."

---

## Step 5: Report assembly and JSON writer

**Objective**: Combine collected results and coverage into a stable JSON report and write to disk safely.

**Context**:
- Output must be deterministic and include a schema version.
- Include summary metrics (counts, total duration) and warning list.
- Include run metadata: tool versions, platform, git SHA, config hash.
- Include run status metadata: pytest exit code, interrupted flag, collect-only flag, collected/selected/deselected counts, rerun counts.
- Handle invalid output paths and unwritable locations gracefully, without failing the pytest run.
- When no tests are collected or run, emit a warning and produce a valid empty report.
- Include collection error summaries and early-stop indicators in the report metadata.
- Write reports atomically to avoid partial outputs on crash.
- Include sanitized pytest invocation and config summary (redacted) in run metadata.
- If evidence bundle output is configured, package JSON/HTML/PDF/manifest into a zip with hashes.
- If aggregation is enabled, read prior run reports from aggregate_dir, merge results per policy, and emit aggregated JSON/HTML.

**Files to touch**:
- `src/pytest_llm_report/report_writer.py`
- `src/pytest_llm_report/util/hashing.py`
- `tests/test_report_writer.py`

**Acceptance criteria**:
- JSON report includes run metadata, warnings, and summary.
- A sha256 hash of the JSON is computed and stored for tamper-evidence.
- Output directories are created when possible; errors are surfaced in warnings.
- Test rows are ordered deterministically (by nodeid, then phase if needed).
- Run status metadata and selection counts are present and correct.
- Collect-only runs produce inventory-only JSON without run-phase duration.
- Collection errors appear in JSON and warnings when present.
- Reports are written atomically (temp file then rename) where possible.
- Evidence bundle is produced when enabled and includes a manifest with hashes.
- Aggregated report includes run_count, source_reports, and policy info.

**Agent prompt**:
"Implement JSON report assembly in `report_writer.py` that merges collector and coverage data into `ReportRoot`. Add run metadata (UTC timestamps, pytest version, plugin version, OS, Python), run status fields (exit code, interrupted, collect-only, collected/selected/deselected counts, rerun counts), sanitized pytest invocation/config summary, and warnings list. Compute and include a sha256 hash of the JSON payload. Ensure output paths are created if missing and write failures become warnings. Sort test rows deterministically by nodeid. If evidence bundle output is configured, package JSON/HTML/PDF/manifest into a zip. If aggregation is enabled, read prior run JSON reports from `aggregate_dir` and merge per `aggregate_policy`, then emit aggregated JSON/HTML with source report hashes. Write tests to confirm deterministic output, collect-only behavior, aggregation, evidence bundle generation, and error handling."

---

## Step 6: HTML rendering pipeline

**Objective**: Render the HTML report from the JSON model using Jinja2 templates.

**Context**:
- Keep HTML simple, accessible, and deterministic.
- Provide collapsible per-test coverage lists and a summary table.
- Escape nodeids and messages to avoid HTML or JS issues.
- Add UI behavior that scales for large suites (collapse by default or simple paging).
- Display run status metadata (exit code, collect-only flag, deselected counts, rerun counts) in the summary.
- Display collection errors or warnings prominently when present.
- Display captured stdout/stderr for failed tests when enabled (collapsed by default).
- When aggregation is enabled, show run_count, policy, and source report list in the summary.

**Files to touch**:
- `src/pytest_llm_report/render.py`
- `src/pytest_llm_report/templates/*.j2`
- `src/pytest_llm_report/static/*`
- `tests/test_render.py`
- `tests/fixtures/golden/*`

**Acceptance criteria**:
- HTML renders without JS errors in a basic browser.
- Golden files pass for minimal report.
- Special characters in nodeids render safely.
- Large suites render without extreme performance issues (basic lazy collapse).
- Summary section shows collected/selected/deselected counts and run status.
- Collection errors are visible in HTML when present.
- Captured output is visible only when enabled and is truncated in UI.
- Aggregation summary is visible when enabled.

**Agent prompt**:
"Build `render.py` to render HTML via Jinja2 using templates under `templates/`. Output should include summary table with nodeid, status, duration, coverage list, run status metadata (exit code, collect-only flag, deselected counts, rerun counts), and collection errors. Add support for showing captured stdout/stderr for failed tests when enabled. Add JS for simple filters and default collapsing for large suites. Update golden HTML fixtures and tests in `tests/test_render.py`."

---

## Step 7: LLM provider interface (optional, default noop)

**Objective**: Define provider interface and a noop provider, preserving privacy defaults.

**Context**:
- Provider default must be \"none\".
- LLM must be opt-in; prompts should include only test code and minimal referenced snippets.
- Enabling a real provider should emit a warning about data handling.

**Files to touch**:
- `src/pytest_llm_report/llm/base.py`
- `src/pytest_llm_report/llm/noop.py`
- `src/pytest_llm_report/llm/schemas.py`
- `src/pytest_llm_report/prompts.py`
- `tests/test_llm_contract.py`

**Acceptance criteria**:
- No LLM calls occur when provider=none.
- Response schema is validated and normalized.
- Warning is logged when provider is not none.

**Agent prompt**:
"Create a provider interface and noop implementation that returns empty annotations. Define a strict JSON schema with `scenario`, `why_needed`, `key_assertions`, and optional `confidence`. Add tests that validate schema normalization and ensure noop returns deterministic empty fields. Emit a warning when a non-none provider is configured."

---

## Step 8: LLM context assembly and context modes

**Objective**: Build deterministic context assembly with user-configurable modes while honoring privacy guardrails.

**Context**:
- Provide `llm_context_mode` options: minimal, balanced, complete.
- Always include test identifier metadata in the prompt: nodeid, test file path, test name, and any test docstring.
- Always include parameter ids for parametrized tests; include raw parameter values only when explicitly enabled and redacted.
- Minimal: test code only (function/class body, docstring, local comments) plus identifier metadata.
- Balanced: minimal + first-party imports referenced by the test, with small docstrings and signatures.
- Complete: maximum safe context within the repo, still bounded by size and file limits, and never the entire repo in one prompt.
- Apply file allowlist and denylist; skip binary and large files; redact obvious secrets (env vars, tokens) by regex.
- Record context summary per test: mode, included files, byte count, and truncation flag.
- Do not traverse symlinks outside the repo root and skip `venv`, `.venv`, and `site-packages` by default.
- Handle non-UTF8 files by skipping or replacing with a warning and do not crash.
- Respect per-test LLM opt-out and context override markers.

**Files to touch**:
- `src/pytest_llm_report/prompts.py`
- `src/pytest_llm_report/util/fs.py`
- `src/pytest_llm_report/util/hashing.py`
- `tests/test_prompts.py`

**Acceptance criteria**:
- Context selection is deterministic and respects `llm_context_bytes` and `llm_context_file_limit`.
- The prompt always includes test identifier metadata (nodeid, file path, test name, docstring when present).
- Parameter ids are included in prompts; raw parameter values are excluded by default and, if enabled, truncated and redacted.
- "Complete" never includes the entire repo and always respects the filters.
- Truncation is recorded and emitted as a warning.
- Included file list is present in JSON for auditability.
- Symlink traversal is bounded to repo root and non-UTF8 files are handled with warnings.
- File paths in prompts and context summaries are repo-relative where possible.
- Per-test opt-out skips LLM calls and context override takes precedence over global mode.

**Agent prompt**:
"Implement context assembly in `prompts.py` with modes minimal, balanced, and complete. Always include test identifier metadata in the prompt (nodeid, file path, test name, docstring when present) and parameter ids for parametrized tests. Add size and file limits, include and exclude globs, and skip binary or oversized files. Add a simple redaction pass for obvious secrets. Support optional inclusion of raw parameter values with truncation and redaction. Bound symlink traversal to repo root and skip venv and site-packages by default. Handle non-UTF8 files with warnings. Respect per-test opt-out and context override markers. Record context summary (mode, file list, total bytes, truncated flag) in the report data. Add tests in `tests/test_prompts.py` for mode behavior, truncation, filtering, identifier inclusion, and parameter handling."

---

## Step 9: LLM caching and provider implementations

**Objective**: Implement caching and optional providers (Ollama, LiteLLM).

**Context**:
- Cache key must include provider, model, prompt template version, context hash, and file hashes.
- Handle rate limits and error conditions gracefully; annotate errors in report.
- Never fail the pytest run due to LLM errors.
- Read API keys or tokens from environment variables or provider-specific config only; never print secrets.
- Enforce `llm_max_tests`, `llm_max_concurrency`, and `llm_timeout_seconds` to control cost and runtime.
- Support cache TTL (`llm_cache_ttl_seconds`) and ignore stale cache entries.

**Files to touch**:
- `src/pytest_llm_report/cache.py`
- `src/pytest_llm_report/llm/ollama.py`
- `src/pytest_llm_report/llm/litellm_provider.py`
- `tests/test_cache.py`

**Acceptance criteria**:
- Cache hit/miss behavior is deterministic.
- Provider errors do not fail the pytest run; they degrade gracefully.
- Context hash changes invalidate cached LLM results.
- Missing or invalid auth produces a clear warning and empty annotations.
- LLM execution limits are enforced and reflected in warnings when exceeded.
- Cache TTL is applied deterministically.

**Agent prompt**:
"Implement a simple file cache under `.pytest_llm_cache` with deterministic keys. Add Ollama and LiteLLM providers behind the base interface. Failures should produce warnings and empty annotations, not crash. Include context hash in the cache key. Read auth only from env or config and ensure secrets are not logged. Enforce LLM execution limits (max tests, concurrency, timeout) and cache TTL. Add unit tests for cache behavior, TTL handling, limit enforcement, and provider error handling, including missing auth."

---

## Step 10: Optional PDF output via Playwright

**Objective**: Support PDF generation when `--llm-pdf` is specified.

**Context**:
- Playwright should be optional. If missing, emit a helpful error.
- PDF should be generated from HTML with a consistent page size (e.g., A4).

**Files to touch**:
- `src/pytest_llm_report/report_writer.py`
- `scripts/build_report_pdf.py`
- `tests/test_report_writer.py`

**Acceptance criteria**:
- PDF generation is skipped unless explicitly requested.
- Missing Playwright dependency produces a clear error and a warning entry.

**Agent prompt**:
"Add optional PDF generation in `report_writer.py` triggered by `--llm-pdf`. Use Playwright if available and emit a clear error if not installed. Add tests that exercise the code path with a stub or skip when Playwright is missing."

---

## Step 11: Compliance metadata and traceability

**Objective**: Provide audit-friendly metadata and requirements traceability.

**Context**:
- Regulatory submissions often require mapping tests to requirement IDs and documenting software versions.
- Provide a user-configurable metadata file (JSON or YAML) that merges into report metadata.
- Support a requirement marker (e.g., `@pytest.mark.requirement("REQ-123")`) and allow multiple IDs per test.
- Register markers for LLM control (`llm_opt_out`, `llm_context`) to avoid warnings.

**Files to touch**:
- `src/pytest_llm_report/options.py`
- `src/pytest_llm_report/report_writer.py`
- `src/pytest_llm_report/util/fs.py`
- `tests/test_report_writer.py`
- `docs/report-format.md`

**Acceptance criteria**:
- Report includes optional `requirements` mapping and custom metadata.
- Metadata merge is deterministic and namespaced.
- Requirement markers are collected and recorded per test.
- Marker is registered in pytest to avoid unknown-marker warnings.
- LLM control markers (`llm_opt_out`, `llm_context`) are registered and documented.

**Agent prompt**:
"Add support for optional metadata injection from a JSON or YAML file. Merge into report metadata under a namespace (e.g., `custom_metadata`). Add a requirements mapping field at test-level via a marker, allow multiple IDs, and update docs to describe these fields. Register requirement and LLM control markers in pytest to avoid warnings."

---

## Step 12: Tamper-evidence and provenance

**Objective**: Add hashes and provenance details to support audit trails.

**Context**:
- Provide SHA256 hashes for report files and include tool configuration hash.
- Capture git SHA and a dirty flag if the repo is not clean.
- Optional signature should use standard library HMAC to avoid heavy dependencies.
- If dependency snapshot output is enabled, write a deterministic list of installed distributions (sorted) and include its hash in the artifact manifest.
- If evidence bundle is enabled, include the bundle hash in the artifact manifest.

**Files to touch**:
- `src/pytest_llm_report/util/hashing.py`
- `src/pytest_llm_report/report_writer.py`
- `tests/test_report_writer.py`

**Acceptance criteria**:
- JSON includes `sha256` for itself and for the HTML output (if generated).
- Run metadata includes git SHA and dirty flag when available.
- Optional HMAC signature is included when a key is configured.
- Dependency snapshot output is optional, deterministic, and hashed when enabled.
- Evidence bundle hash is recorded when bundle output is enabled.

**Agent prompt**:
"Compute and embed SHA256 hashes for JSON and HTML outputs in the report metadata. Gather git SHA and dirty flag with a safe fallback if git is unavailable. Add optional HMAC signature using a user-provided key file and store signature info in the report. If dependency snapshot output is configured, write a deterministic package list and include its hash in the artifact manifest. Add tests for hash, snapshot, and signature determinism."

---

## Step 13: Resilience for missing or partial coverage

**Objective**: Ensure graceful degradation when coverage is missing or contexts are not enabled.

**Context**:
- Users may run without `--cov-context=test` or without coverage at all.
- Report should still generate with a clear warning and empty coverage lists.
- If coverage is only in setup/teardown, note it and skip by default.

**Files to touch**:
- `src/pytest_llm_report/coverage_map.py`
- `src/pytest_llm_report/errors.py`
- `tests/test_coverage_map.py`

**Acceptance criteria**:
- Report generation never fails due to missing `.coverage` files.
- Warning is emitted once with actionable guidance.

**Agent prompt**:
"Add explicit handling for missing coverage contexts. If coverage is missing or contexts are not enabled, return empty coverage for tests and log a single warning. Add tests that simulate missing `.coverage` and ensure a report still writes."

---

## Step 14: Pytester integration tests and golden files

**Objective**: Lock down end-to-end behavior in real pytest runs.

**Context**:
- Use `pytester` to run a sample project with pytest-cov and plugin enabled.
- Validate that HTML and JSON are generated and match golden files.
- Cover edge cases like setup failures, xfail, and special characters in nodeids.
- Add scenarios for collect-only runs, deselected tests, rerun outcomes, zero collected tests, and collection errors.
- Add scenarios for LLM opt-out markers, context override markers, and failed-test output capture.
- Add scenarios for aggregation across two runs with coverage append enabled.

**Files to touch**:
- `tests/test_smoke_pytester.py`
- `tests/fixtures/sample_project/*`
- `tests/fixtures/golden/*`

**Acceptance criteria**:
- Integration tests run in CI and verify output files are present.
- Golden files only change when output intentionally changes.
- Collect-only, deselection, rerun, zero-test, and collection-error scenarios are covered with stable outputs.
- Marker behavior and output capture are covered with stable outputs.
- Aggregation scenario produces a stable aggregated JSON and HTML report.

**Agent prompt**:
"Add or update pytester tests to run a sample project that generates HTML and JSON reports. Compare outputs to golden fixtures. Ensure the tests cover run-phase contexts, omit tests from coverage by default, include at least one test with special characters in the nodeid, and add scenarios for collect-only, deselected tests, rerun outcomes, zero collected tests, collection errors, LLM opt-out and context override markers, failed-test output capture, and aggregation across two runs with coverage append."

---

## Step 15: Documentation and examples for compliance usage

**Objective**: Provide clear guidance for using reports in CAP/CLIA/FDA submissions.

**Context**:
- Include a section on verification package usage, traceability, and metadata injection.
- Emphasize privacy defaults and LLM opt-in.
- Document LLM context modes and the fact that "complete" is bounded and never the entire repo.
- Document supported Python versions (3.11, 3.12, 3.13) and test matrix expectations.
- Document parameterized test handling: ids are included, raw parameter values are opt-in with redaction and truncation.
- Provide first-class, comprehensive docs with citation links for all configuration options, inputs, outputs, and usage scenarios.
- Include detailed LLM setup instructions, including subscription steps and API authentication for each provider.
- Document collect-only inventory reports, deselected counts, rerun outcomes, dependency snapshot artifacts, and run status fields (exit code, interrupted).
- Document collection errors and early-stop behavior, including how they appear in JSON and HTML.
- Document LLM cost controls (max tests, concurrency, timeouts) and cache TTL behavior.
- Document LLM opt-out and context override markers, evidence bundle packaging, sanitized pytest invocation summary, and failed-test output capture.
- Document aggregation workflows for multiple runs with coverage append, including policies and source report handling.

**Files to touch**:
- `docs/report-format.md`
- `docs/privacy.md`
- `docs/coverage.md`
- `docs/configuration.md`
- `docs/providers.md`
- `docs/getting-started.md`
- `docs/troubleshooting.md`
- `README.md`
- `examples/minimal/*`

**Acceptance criteria**:
- Docs explain how to include requirement IDs and metadata.
- Example shows `--cov-context=test` and report outputs.
- Context modes are documented with size and privacy constraints.
- Supported Python versions are documented in docs and README.
- Config reference includes every option with default, type, and example, plus citations to upstream docs (pytest, pytest-cov, coverage.py, LLM providers).
- Inputs and outputs are documented (JSON schema fields, HTML sections, PDF optional) with citation links where applicable.
- Usage scenarios include minimal, local LLM, cloud LLM, CI artifacts, and compliance package packaging.
- LLM setup docs cover subscription, API key configuration, and auth env vars, with provider-specific citations.
- Collect-only, rerun, deselection, and dependency snapshot behaviors are documented with examples.
- Collection errors and early-stop behavior are documented with examples.
- LLM marker behavior, evidence bundle packaging, and output capture are documented with examples.
- Aggregation workflow is documented with examples and CLI/config snippets.

**Documentation deliverables checklist**:
- Config reference: every option with default, type, and example; cite pytest and pytest-cov for required flags.
- Inputs: coverage requirements, contexts, supported file types; cite coverage.py context docs.
- Outputs: JSON schema fields, HTML sections, PDF optional; include example snippets and cite relevant upstream tools.
- Usage scenarios: minimal, local LLM, cloud LLM, CI artifacts, compliance package packaging.
- LLM setup: provider-specific subscription steps, API authentication, env vars, and regional settings where applicable.
- Parameterization: explain ids vs raw values, privacy defaults, and recommendations for `ids=`.
- Supported versions: Python 3.11-3.13 and pytest/pytest-cov minimums.
- Run status metadata, collect-only, rerun outcomes, and dependency snapshot options.
- LLM markers, evidence bundle packaging, sanitized invocation summary, and output capture.
- Aggregation options and policies.

**Citation source list (embed as links in docs)**:
- pytest docs: https://docs.pytest.org/en/stable/
- pytest plugin writing: https://docs.pytest.org/en/stable/how-to/writing_plugins.html
- pytest configuration: https://docs.pytest.org/en/stable/reference/customize.html
- pytest-cov docs: https://pytest-cov.readthedocs.io/en/latest/
- pytest-xdist docs: https://pytest-xdist.readthedocs.io/en/latest/
- pytest-rerunfailures docs: https://pytest-rerunfailures.readthedocs.io/en/latest/
- coverage.py contexts: https://coverage.readthedocs.io/en/latest/contexts.html
- coverage.py config: https://coverage.readthedocs.io/en/latest/config.html
- Jinja2 templates: https://jinja.palletsprojects.com/
- Playwright Python: https://playwright.dev/python/
- uv docs: https://docs.astral.sh/uv/
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- LiteLLM docs: https://docs.litellm.ai/
- LiteLLM providers/auth: https://docs.litellm.ai/docs/providers

**Agent prompt**:
"Update docs to include compliance-focused usage guidance. Add or update an example project that uses coverage contexts, sets provider=none, and injects metadata. Document LLM context modes and safety boundaries, LLM opt-out and context override markers, evidence bundle packaging, sanitized pytest invocation summary, failed-test output capture, and aggregation workflows for coverage-append runs. Add a supported Python versions section (3.11, 3.12, 3.13). Add a parameterization section that explains ids vs raw values and privacy defaults. Create a comprehensive config reference with defaults and examples, and cite upstream docs for pytest, pytest-cov, coverage.py, and each LLM provider. Add usage scenarios (minimal, local LLM, cloud LLM, CI artifacts, compliance packaging, aggregation across runs). Include detailed LLM setup instructions with subscription steps and API authentication (env vars), with citations. Keep the docs concise and avoid new dependencies."

---

## Step 16: CI and release checks

**Objective**: Ensure quality gates are enforced.

**Context**:
- CI should run lint, tests, and coverage >= 90 percent.
- Use `uv` for reproducible builds.
- Test matrix must include Python 3.11, 3.12, and 3.13 for plugin support.
- CI should build and smoke-import the package across the Python matrix.
- Release workflow should build artifacts with the same Python matrix before publishing.

**Files to touch**:
- `.github/workflows/ci.yml`
- `pyproject.toml`

**Acceptance criteria**:
- CI fails if coverage is below 90 percent.
- Build includes templates and static assets.
- CI runs tests on Python 3.11, 3.12, and 3.13.
- Build includes JSON schema files under `schemas/`.
- CI builds and smoke-imports the package on 3.11, 3.12, and 3.13.
- Release workflow builds artifacts for 3.11, 3.12, and 3.13 prior to publish.

**Agent prompt**:
"Review CI workflow to ensure lint + tests + coverage threshold. Confirm templates, static assets, and `schemas/` are included in packaging. Add or update CI steps to use `uv`, test Python 3.11, 3.12, and 3.13, and build/smoke-import the package on each version. Ensure the release workflow builds artifacts on the same matrix before publishing."

---

## Step 17: Security and privacy posture review

**Objective**: Verify default settings and documentation protect sensitive data.

**Context**:
- CAP/CLIA/FDA submissions often involve sensitive systems; avoid sending data to LLM by default.
- Provide a clear warning if LLM is enabled.
- Ensure context filters exclude `.env`, secrets, and common credentials files by default.
- Redact or avoid logging any config values that might contain secrets or tokens.

**Files to touch**:
- `docs/privacy.md`
- `src/pytest_llm_report/options.py`
- `src/pytest_llm_report/llm/*`

**Acceptance criteria**:
- Provider default remains "none".
- Enabling LLM requires explicit configuration and logs a warning.
- Context filters exclude common secret files by default.
- Logs and report metadata do not include secrets or API keys.

**Agent prompt**:
"Confirm provider defaults to none and add a warning when non-none providers are enabled. Add default context exclude globs for secret files. Ensure secrets are not logged or included in metadata. Update privacy docs to explicitly state what data is sent (test code only, minimal snippets by default) and what is never sent."

---

## Step 18: Integration gate and contract verification

**Objective**: Validate that component contracts and schema remain compatible as the system evolves.

**Context**:
- Add a small integration test that exercises the full pipeline without LLM and verifies required output fields.
- Add contract tests that validate Config defaults, schema compatibility, and report writer output alignment.
- The integration gate should be fast and run in CI.
- Include run status metadata fields and selection counts in contract checks.

**Files to touch**:
- `tests/test_integration_gate.py`
- `tests/test_models.py`
- `tests/test_options.py`

**Acceptance criteria**:
- Integration test passes with no LLM enabled and produces both JSON and HTML outputs.
- Contract tests confirm Config defaults and schema fields match report output.
- Tests are deterministic and fast.
- Contract tests verify run status fields, selection counts, and dependency snapshot configuration defaults.
- Contract tests cover collection error fields and early-stop indicators.

**Agent prompt**:
"Add a lightweight integration gate test that runs the report pipeline without LLM and asserts required JSON fields and HTML output. Add contract tests verifying Config defaults and schema compatibility. Keep tests fast and deterministic."

---

## Suggested testing commands
- `uv run pytest -q tests/test_coverage_map.py::test_context_mapping`
- `uv run pytest -q tests/test_smoke_pytester.py::test_minimal`
- `uv run pytest -q tests/test_prompts.py`
- `uv run pytest --cov=pytest_llm_report --cov-report=term-missing`
- `uv run ruff check .`
- `uv run ruff format .`

## Exit criteria for the full implementation
- HTML and JSON reports generated deterministically.
- Coverage contexts correctly mapped to test nodeids.
- LLM features are fully opt-in, cached, and context-controlled.
- Report includes run metadata, hashes, artifact manifest, and traceability hooks.
- Test suite passes with coverage > 90 percent.
