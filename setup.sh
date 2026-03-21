#!/bin/bash
# Initialize project-specific files (run once after cloning from meta)
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

[ ! -f tasks.md ]    && touch tasks.md    && echo "Created tasks.md"
[ ! -f PROGRESS.md ] && touch PROGRESS.md && echo "Created PROGRESS.md"
[ ! -f README.md ]   && touch README.md   && echo "Created README.md"
[ ! -f .gitignore ]  && touch .gitignore  && echo "Created .gitignore"

echo "Setup complete."
