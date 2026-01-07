#!/bin/bash
# Build wheel and sdist
set -e
echo "Building package..."
uv build
echo "Build complete. Output in dist/"
ls -la dist/
