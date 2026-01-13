#!/bin/bash
# Run tests with coverage
set -e
uv run pytest \
    --cov=pytest_llm_report \
    --cov=src/pytest_llm_report \
    --cov-context=test \
    --cov-report=term-missing \
    "$@"
