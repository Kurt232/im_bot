FROM node:22-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code
ENV CC_IN_CONTAINER=1
WORKDIR /workspace
ENTRYPOINT ["/workspace/start.sh"]
