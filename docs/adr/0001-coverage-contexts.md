# ADR 0001: Coverage Contexts

## Status
Accepted

## Context

pytest-llm-report needs to know which test covered which lines of code. This enables per-test coverage reporting and provides context for LLM annotation.

## Decision

We require users to run with `--cov-context=test` which instructs coverage.py to record the test nodeid for each covered line.

## Consequences

### Positive
- Precise per-test coverage data
- Works with pytest-cov out of the box
- No custom instrumentation needed

### Negative
- Requires user to add `--cov-context=test` flag
- Slightly increases coverage data size
- Some older coverage.py versions may not support it fully

## Alternatives Considered

1. **Custom pytest hook** - Would require reimplementing coverage
2. **Post-processing coverage data** - Less accurate, timing issues
3. **AST analysis** - Complex, doesn't capture runtime behavior
