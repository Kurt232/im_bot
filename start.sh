#!/bin/bash
# Entry point: launch Claude Code for this project
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

NUM_WORKERS=${NUM_WORKERS:-1}

# --- Path A: Inside container ---
if [ "${CC_IN_CONTAINER:-}" = "1" ]; then
    git config --global --add safe.directory /workspace
    if [ -n "$1" ]; then
        claude --dangerously-skip-permissions -p "$1"
    else
        claude --dangerously-skip-permissions
    fi
    exit 0
fi

# --- Path B: Docker mode (host) ---
if [ "${DOCKER:-}" = "1" ]; then
    # Find Dockerfile: project dir first, then config/ (for root project)
    if [ -f "$PROJECT_DIR/Dockerfile" ]; then
        DOCKERFILE="$PROJECT_DIR/Dockerfile"
    elif [ -f "$PROJECT_DIR/config/Dockerfile.template" ]; then
        DOCKERFILE="$PROJECT_DIR/config/Dockerfile.template"
    else
        echo "Error: No Dockerfile found (checked ./Dockerfile and ./config/Dockerfile.template)"
        exit 1
    fi

    IMAGE_NAME="cc-${PROJECT_NAME}-docker"

    echo "Building image $IMAGE_NAME from $DOCKERFILE..."
    docker build -t "$IMAGE_NAME" -f "$DOCKERFILE" "$(dirname "$DOCKERFILE")"

    # API key: env var > .env file
    DOCKER_ENV_ARGS=()
    if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
        DOCKER_ENV_ARGS+=(-e ANTHROPIC_API_KEY)
    elif [ -f "$PROJECT_DIR/.env" ]; then
        DOCKER_ENV_ARGS+=(--env-file "$PROJECT_DIR/.env")
    fi

    if [ "$NUM_WORKERS" -eq 1 ]; then
        CONTAINER_NAME="cc-${PROJECT_NAME}-docker"
        docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

        if [ -n "$1" ]; then
            docker run --rm \
                -v "$PROJECT_DIR:/workspace" \
                "${DOCKER_ENV_ARGS[@]}" \
                --name "$CONTAINER_NAME" \
                "$IMAGE_NAME" \
                "$1"
        else
            docker run -it --rm \
                -v "$PROJECT_DIR:/workspace" \
                "${DOCKER_ENV_ARGS[@]}" \
                --name "$CONTAINER_NAME" \
                "$IMAGE_NAME"
        fi
    else
        # Multi-worker: host creates worktrees, each worker gets its own container
        for i in $(seq 1 "$NUM_WORKERS"); do
            WORKER_DIR="$PROJECT_DIR/../claude-worker-${PROJECT_NAME}-$i"
            BRANCH="worker-${PROJECT_NAME}-$i"
            CONTAINER_NAME="cc-${PROJECT_NAME}-docker-$i"

            if [ ! -d "$WORKER_DIR" ]; then
                git worktree add -b "$BRANCH" "$WORKER_DIR" HEAD
                echo "Created worktree: $WORKER_DIR (branch: $BRANCH)"
            fi

            docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

            docker run -d --rm \
                -v "$(cd "$WORKER_DIR" && pwd):/workspace" \
                "${DOCKER_ENV_ARGS[@]}" \
                --name "$CONTAINER_NAME" \
                "$IMAGE_NAME" \
                "Read CLAUDE.md. Pick one unchecked task from tasks.md, complete it, update PROGRESS.md, commit, and exit."

            echo "Worker $i started (container: $CONTAINER_NAME)"
        done

        echo ""
        echo "=== $NUM_WORKERS Docker workers running for $PROJECT_NAME ==="
        echo "  docker ps                                   — list containers"
        echo "  docker logs -f cc-${PROJECT_NAME}-docker-1  — view worker 1"
    fi
    exit 0
fi

# --- Path C: Original behavior (no Docker) ---
if [ "$NUM_WORKERS" -eq 1 ]; then
    if [ -n "$1" ]; then
        claude -p "$1"
    else
        claude
    fi
else
    mkdir -p "$HOME/claude-logs"

    for i in $(seq 1 "$NUM_WORKERS"); do
        WORKER_DIR="$PROJECT_DIR/../claude-worker-${PROJECT_NAME}-$i"
        BRANCH="worker-${PROJECT_NAME}-$i"

        if [ ! -d "$WORKER_DIR" ]; then
            git worktree add -b "$BRANCH" "$WORKER_DIR" HEAD
            echo "Created worktree: $WORKER_DIR (branch: $BRANCH)"
        fi

        tmux kill-session -t "cc-${PROJECT_NAME}-$i" 2>/dev/null || true

        tmux new-session -d -s "cc-${PROJECT_NAME}-$i" bash -c "
            cd $WORKER_DIR
            while true; do
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] Worker $i starting...\"
                claude -p 'Read CLAUDE.md. Pick one unchecked task from tasks.md, complete it, update PROGRESS.md, commit, and exit.' \
                    2>&1 | tee -a $HOME/claude-logs/${PROJECT_NAME}-worker-$i.log
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] Worker $i done. Sleeping 15s...\"
                sleep 15
            done
        "
        echo "Worker $i started (tmux: cc-${PROJECT_NAME}-$i)"
    done

    echo ""
    echo "=== $NUM_WORKERS workers running for $PROJECT_NAME ==="
    echo "  tmux ls                              — list sessions"
    echo "  tmux attach -t cc-${PROJECT_NAME}-1  — view worker 1"
fi
