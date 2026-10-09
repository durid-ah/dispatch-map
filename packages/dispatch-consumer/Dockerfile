# syntax=docker/dockerfile:1.9

# ------------------------------------------------------------------------------
# Stage 1: Base Python & uv configuration
# ------------------------------------------------------------------------------
FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/packages/dispatch-consumer:/app/packages/db/src"

WORKDIR /app

# ------------------------------------------------------------------------------
# Stage 2: Python dependencies builder
# ------------------------------------------------------------------------------
FROM base AS builder

# Copy workspace configuration and dependency manifests for layer caching
COPY pyproject.toml uv.lock ./
COPY packages/db/ ./packages/db/
COPY packages/dispatch-consumer/pyproject.toml ./packages/dispatch-consumer/

# Install consumer dependencies without consumer application source
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package dispatch-consumer --frozen --no-dev --no-install-project

# Copy consumer package source
COPY packages/dispatch-consumer/ ./packages/dispatch-consumer/

# Complete installation of dispatch-consumer
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package dispatch-consumer --frozen --no-dev

# ------------------------------------------------------------------------------
# Stage 3: Production image (runs consumer worker)
# ------------------------------------------------------------------------------
FROM python:3.14-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/packages/dispatch-consumer:/app/packages/db/src"

WORKDIR /app

# Copy virtual environment and code from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/packages/db /app/packages/db
COPY --from=builder /app/packages/dispatch-consumer /app/packages/dispatch-consumer

WORKDIR /app/packages/dispatch-consumer

CMD ["python", "main.py"]

# ------------------------------------------------------------------------------
# Stage 4: Development image (supports volume mounts and hot-reloading)
# ------------------------------------------------------------------------------
FROM base AS development

COPY pyproject.toml uv.lock ./
COPY packages/db/ ./packages/db/
COPY packages/dispatch-consumer/pyproject.toml ./packages/dispatch-consumer/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package dispatch-consumer --frozen

COPY packages/dispatch-consumer/ ./packages/dispatch-consumer/

WORKDIR /app/packages/dispatch-consumer

CMD ["uv", "run", "--directory", "/app/packages/dispatch-consumer", "python", "main.py"]
