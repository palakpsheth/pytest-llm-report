# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Dark mode support for HTML reports (auto-detects system preference via `prefers-color-scheme`)
- CLI help text now includes usage examples for `--llm-report`, `--llm-report-json`, and `--llm-pdf`
- Concurrent LLM annotation support via `llm_max_concurrency` (default: 4 for cloud, 2 for local recommended)
- Performance optimization for local providers (e.g., Ollama) to skip artificial rate limits
- `llm_max_tests` now defaults to 0 (no limit) instead of 100
- New `--llm-coverage-source` CLI option to inject external coverage data (e.g., from `coverage run`) into reports
- HTML report now expands all test details by default for better visibility


### Changed

- Improved LLM response parsing to handle JSON wrapped in markdown code fences (` ```json ... ``` `)

## [0.2.0] - 2026-01-18

### Added

- **New LiteLLM Provider**: Support for LiteLLM as an LLM provider (`--llm-provider litellm`).
- **Table of Contents**: Added a Table of Contents to the HTML report for better navigation.
- **Grouped Tests**: HTML report now groups tests by file.

### Changed

- **[BREAKING] Standardized Configuration**: Renamed configuration properties in `pyproject.toml` and `pytest.ini` to remove the redundant `llm_` prefix.
    - `llm_provider` -> `provider`
    - `llm_model` -> `model`
    - `llm_context_mode` -> `context_mode`
    - `llm_timeout_seconds` -> `timeout_seconds`
    - `llm_max_tests` -> `max_tests`
    - `llm_omit_tests_from_coverage` -> `omit_tests_from_coverage`
    - `llm_include_phase` -> `include_phase`
    - `llm_max_concurrency` -> `max_concurrency`

## [0.1.1] - 2026-01-14

### Fixed

- Fix broken documentation links in README.
- Fix PyPI badge.

## [0.1.0] - 2026-01-07

### Added

- Initial release of pytest-llm-report
- Core pytest plugin with `pytest11` entry point
- CLI options: `--llm-report`, `--llm-report-json`, `--llm-pdf`
- Configuration via `pyproject.toml` and `pytest.ini`
- Per-test coverage mapping using `--cov-context=test`
- JSON report with schema validation (`schemas/report.schema.json`)
- HTML report with embedded CSS
- LLM providers: `none` (default), `ollama`, `litellm`
- LLM response caching (file-based, TTL-enabled)
- Context modes: `minimal`, `balanced`, `complete`
- Aggregation support for multi-run reports
- Tamper-evidence with SHA256 hashes and optional HMAC
- Git SHA and dirty flag in report metadata
- Atomic file writes for safe output
- pytest markers: `@pytest.mark.llm_opt_out`, `@pytest.mark.llm_context()`, `@pytest.mark.requirement()`
- CI workflow with Python 3.11-3.13 matrix
- 90%+ test coverage

### Security

- Default provider is `"none"` - no data sent to LLM unless explicitly enabled
- Secret file patterns excluded from LLM context by default
- Command-line redaction patterns for sensitive arguments

[Unreleased]: https://github.com/palakpsheth/pytest-llm-report/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/palakpsheth/pytest-llm-report/releases/tag/v0.1.0
