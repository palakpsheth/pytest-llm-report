# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
