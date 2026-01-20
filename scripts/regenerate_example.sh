#!/bin/bash
set -e

# Ensure we are in project root
cd "$(dirname "$0")/.."

# 1. Build git info (for correct metadata)
python3 scripts/build_git_info.py

# 2. Run example tests with Ollama
# We use the config from examples/with-ollama/pyproject.toml but override output path
# We also ensure source files are importable by adding examples/with-ollama to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/examples/with-ollama

echo "Running example tests..."
uv run pytest -c examples/with-ollama/pyproject.toml \
    examples/with-ollama/tests \
    -o "llm_report_model=llama3.2" \
    -o "llm_report_context_mode=complete" \
    --llm-report=docs/example-report/index.html \
    --llm-report-json=docs/example-report/report.json \
    --ignore=tests || true  # Allow pytest to fail (expected for demo reports with intentional failures)

# 3. Generate PDF
echo "Generating PDF..."
uv run python3 scripts/build_report_pdf.py docs/example-report/index.html docs/example-report/example_report.pdf

echo "Done! Check docs/example-report/"
