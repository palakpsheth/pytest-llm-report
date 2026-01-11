#!/bin/bash
# Development environment setup
set -e

echo "Setting up development environment..."

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Sync dependencies
echo "Installing dependencies..."
uv sync --all-extras

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
uv run pre-commit install

echo "Done! Run 'uv run pytest' to run tests."
