#!/bin/bash
# Lint code with ruff
set -e
uv run ruff check "$@" .
