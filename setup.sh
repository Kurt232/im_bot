#!/bin/bash
# Set up the project: install Python dependencies via uv
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Create venv and install dependencies
uv venv
uv pip install -e .

echo "Setup complete. Activate with: source .venv/bin/activate"
