#!/bin/bash
# Entry point: launch Claude Code for this project
# Each invocation creates a git worktree for isolation. Run multiple times for multiple workers.
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

# --- Path A: Inside container ---
if [ "${CC_IN_CONTAINER:-}" = "1" ]; then
    git config --global --add safe.directory /workspace

    CLAUDE_ARGS=(--dangerously-skip-permissions)
    [ -n "${MODEL:-}" ]  && CLAUDE_ARGS+=(--model "$MODEL")
    [ -n "${EFFORT:-}" ] && CLAUDE_ARGS+=(--effort "$EFFORT")

    if [ -n "$1" ]; then
        TIMEOUT=${TIMEOUT:-300}
        timeout "$TIMEOUT" claude "${CLAUDE_ARGS[@]}" -p "$1"
    else
        claude "${CLAUDE_ARGS[@]}"
    fi
    exit 0
fi

# --- Path B: Docker mode (host) ---
AUTH_DIR="$PROJECT_DIR/.docker-claude"
mkdir -p "$AUTH_DIR/config"
[ ! -f "$AUTH_DIR/claude.json" ] && echo '{}' > "$AUTH_DIR/claude.json"

# Create worktree for isolation
WORKER_ID="$(date +%s)-$$"
BRANCH="worker-${PROJECT_NAME}-${WORKER_ID}"
WORKER_DIR="$PROJECT_DIR/.worktrees/worker-${WORKER_ID}"

git worktree add -b "$BRANCH" "$WORKER_DIR" HEAD
echo "Worktree: $WORKER_DIR (branch: $BRANCH)"

# Run container with worktree mounted
export PROJECT_NAME
COMPOSE_PROJECT_DIR="$PROJECT_DIR" docker compose \
    -f "$PROJECT_DIR/compose.yml" \
    run --rm \
    -v "$(cd "$WORKER_DIR" && pwd):/workspace" \
    worker "$@"
