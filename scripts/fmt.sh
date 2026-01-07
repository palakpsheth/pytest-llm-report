#!/bin/bash
# Format code with ruff
set -e
uv run ruff format .
echo "Formatting complete."
