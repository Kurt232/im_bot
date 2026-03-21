#!/bin/bash
# Entry point for the email bot.
# Usage:
#   ./start-bot.sh            — run directly (requires venv with dependencies)
#   ./start-bot.sh --docker   — run via docker compose
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Load .env if present
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . .env
    set +a
fi

# Validate required environment variables
required_vars=(IMAP_HOST EMAIL_USER EMAIL_PASSWORD)

missing=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        missing+=("$var")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo "Error: missing required environment variables: ${missing[*]}" >&2
    echo "Set them in .env or export before running." >&2
    exit 1
fi

# Docker mode
if [ "${1:-}" = "--docker" ]; then
    exec docker compose -f "$PROJECT_DIR/compose.yml" up bot
fi

# Direct mode — run Python module
exec python -m im_bot_email
