#!/bin/bash
# Task runner — intended as TASK_COMMAND for the IM bot.
# Each task gets an isolated worktree in cc-workspace.
# After completion, changes are merged back to main and the worktree is cleaned up.
set -e

REPO_DIR="${CC_WORKSPACE:-/workspace/cc-workspace}"

git config --global --add safe.directory "$REPO_DIR" 2>/dev/null || true

# Read email content from stdin (must happen before cd)
TASK_INPUT=$(cat)

# Create worktree for this task
TASK_ID="$(date +%s)-$$"
BRANCH="task-${TASK_ID}"
TASK_DIR="${REPO_DIR}/.worktrees/task-${TASK_ID}"

git -C "$REPO_DIR" worktree add -b "$BRANCH" "$TASK_DIR" HEAD --quiet
git config --global --add safe.directory "$TASK_DIR" 2>/dev/null || true

cd "$TASK_DIR"

# Copy attachments into worktree and append to prompt
if [ -n "${ATTACHMENTS_DIR:-}" ] && [ -d "$ATTACHMENTS_DIR" ]; then
    ATT_FILES=$(ls -1 "$ATTACHMENTS_DIR" 2>/dev/null)
    if [ -n "$ATT_FILES" ]; then
        ATT_DEST="$TASK_DIR/_attachments"
        mkdir -p "$ATT_DEST"
        cp "$ATTACHMENTS_DIR"/* "$ATT_DEST/"
        TASK_INPUT="${TASK_INPUT}

[附件已保存到 _attachments/ 目录，请读取以下文件：]"
        for f in "$ATT_DEST"/*; do
            TASK_INPUT="${TASK_INPUT}
- _attachments/$(basename "$f")"
        done
    fi
fi

# Build claude args
CLAUDE_ARGS=(--dangerously-skip-permissions)
[ -n "${MODEL:-}" ]  && CLAUDE_ARGS+=(--model "$MODEL")
[ -n "${EFFORT:-}" ] && CLAUDE_ARGS+=(--effort "$EFFORT")

TIMEOUT=${TIMEOUT:-300}
RESULT=0
timeout "$TIMEOUT" claude "${CLAUDE_ARGS[@]}" -p "$TASK_INPUT" || RESULT=$?

# Merge changes back to main (with lock to prevent concurrent overwrites)
LOCK="$(git -C "$REPO_DIR" rev-parse --git-common-dir)/merge.lock"
while ! mkdir "$LOCK" 2>/dev/null; do sleep 1; done
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

if [ -n "$(git diff HEAD)" ] || [ -n "$(git diff --cached HEAD)" ]; then
    git add -A
    git commit -m "task: ${TASK_ID}" --allow-empty-message 2>/dev/null || true
fi

if [ "$(git rev-parse HEAD)" != "$(git -C "$REPO_DIR" rev-parse main)" ]; then
    git rebase main --quiet 2>/dev/null || git rebase --abort 2>/dev/null || true
    git -C "$REPO_DIR" branch -f main HEAD
fi

rmdir "$LOCK" 2>/dev/null
trap - EXIT

# Clean up worktree
cd "$REPO_DIR"
git worktree remove "$TASK_DIR" --force 2>/dev/null || true
git branch -D "$BRANCH" 2>/dev/null || true

exit $RESULT
