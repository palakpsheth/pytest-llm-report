# Report Format

This document describes the JSON report format produced by pytest-llm-report.

## Schema Version

The current schema version is `1.0.0`. Check the `schema_version` field in any report output.

A JSON schema file is available at `schemas/report.schema.json`.

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Schema version (semver) |
| `run_meta` | object | yes | Run metadata |
| `summary` | object | yes | Summary statistics |
| `tests` | array | yes | Test results (sorted by nodeid) |
| `collection_errors` | array | no | Collection errors |
| `warnings` | array | no | Warnings during generation |
| `artifacts` | array | no | Generated artifact files |
| `source_coverage` | array | no | Per-file coverage summary |
| `custom_metadata` | object | no | User-provided metadata |
| `sha256` | string | no | SHA256 hash of this report |
| `hmac_signature` | string | no | Optional HMAC signature |

## Run Metadata (`run_meta`)

| Field | Type | Description |
|-------|------|-------------|
| `start_time` | string | UTC start time (ISO 8601) |
| `end_time` | string | UTC end time (ISO 8601) |
| `duration` | number | Duration in seconds |
| `pytest_version` | string | pytest version |
| `plugin_version` | string | pytest-llm-report version |
| `python_version` | string | Python version |
| `platform` | string | OS platform |
| `git_sha` | string | Git commit SHA (if available) |
| `git_dirty` | boolean | Uncommitted changes flag |
| `exit_code` | integer | pytest exit code |
| `interrupted` | boolean | Whether run was interrupted |
| `collect_only` | boolean | Collect-only run flag |
| `collected_count` | integer | Tests collected |
| `selected_count` | integer | Tests selected to run |
| `deselected_count` | integer | Tests deselected |
| `rerun_count` | integer | Total reruns |
| `pytest_invocation` | array | Sanitized command line args |
| `pytest_config_summary` | object | Sanitized ini options |

### Aggregation Fields

When aggregation is enabled (`--llm-aggregate-dir`):

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Unique identifier for this run |
| `run_group_id` | string | Group ID for related runs |
| `is_aggregated` | boolean | Whether this is aggregated |
| `aggregation_policy` | string | Policy: latest, merge, or all |
| `run_count` | integer | Number of runs aggregated |
| `source_reports` | array | Source report paths and hashes |

### LLM Traceability Fields

When LLM annotations are enabled:

| Field | Type | Description |
|-------|------|-------------|
| `llm_provider` | string | LLM provider (e.g., "ollama", "gemini") |
| `llm_model` | string | Model name/version (e.g., "llama3.2:1b") |
| `llm_context_mode` | string | Context mode (minimal, balanced, complete) |
| `llm_annotations_enabled` | boolean | Whether LLM annotations were enabled |
| `llm_annotations_count` | integer | Number of tests annotated |
| `llm_annotations_errors` | integer | Number of annotation errors |

## Summary Statistics (`summary`)

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total number of tests |
| `passed` | integer | Number of passed tests |
| `failed` | integer | Number of failed tests |
| `skipped` | integer | Number of skipped tests |
| `xfailed` | integer | Number of xfailed tests |
| `xpassed` | integer | Number of xpassed tests |
| `error` | integer | Number of tests with errors |
| `total_duration` | number | Total duration in seconds |
| `coverage_total_percent` | number | Total coverage percentage (if available) |

## Test Result Fields

Each test in the `tests` array has:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nodeid` | string | yes | Full pytest nodeid |
| `outcome` | string | yes | passed/failed/skipped/xfailed/xpassed/error |
| `duration` | number | yes | Duration in seconds |
| `phase` | string | yes | setup/call/teardown |
| `error_message` | string | no | Error message if failed |
| `param_id` | string | no | Parameter id for parameterized tests |
| `coverage` | array | no | Coverage entries |
| `llm_annotation` | object | no | LLM annotation |
| `llm_opt_out` | boolean | no | LLM annotation opt-out |
| `requirements` | array | no | Requirement IDs |

## Coverage Entry

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Repo-relative file path |
| `line_ranges` | string | Compact ranges (e.g., "1-3, 5") |
| `line_count` | integer | Total lines covered |

## Source Coverage Entry

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Repo-relative file path |
| `statements` | integer | Total statements |
| `missed` | integer | Missed statements |
| `covered` | integer | Covered statements |
| `coverage_percent` | number | Coverage percentage for the file |
| `covered_ranges` | string | Covered line ranges |
| `missed_ranges` | string | Missed line ranges |

## LLM Annotation

| Field | Type | Description |
|-------|------|-------------|
| `scenario` | string | What the test verifies |
| `why_needed` | string | What bug it prevents |
| `key_assertions` | array | Critical checks (3-8 bullets) |
| `confidence` | number | Confidence score (0-1), displayed as percentage in HTML |
| `error` | string | Error if LLM call failed |
| `context_summary` | object | Context used for annotation |
| `token_usage` | object | Token usage statistics (see below) |

### Token Usage

| Field | Type | Description |
|-------|------|-------------|
| `prompt_tokens` | integer | Number of tokens in the prompt |
| `completion_tokens` | integer | Number of tokens in the completion |
| `total_tokens` | integer | Total tokens used |
