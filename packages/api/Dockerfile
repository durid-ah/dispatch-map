# syntax=docker/dockerfile:1.9

# ------------------------------------------------------------------------------
# Stage 1: Build the React web frontend (Vite)
# ------------------------------------------------------------------------------
FROM node:22-alpine AS web-builder
WORKDIR /app/packages/web

COPY packages/web/package*.json ./
RUN npm ci

COPY packages/web/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Base Python & uv configuration
# ------------------------------------------------------------------------------
FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/packages/api:/app/packages/db/src"

WORKDIR /app

# ------------------------------------------------------------------------------
# Stage 3: Python dependencies builder
# ------------------------------------------------------------------------------
FROM base AS builder

# Copy workspace configuration and dependency manifests for layer caching
COPY pyproject.toml uv.lock ./
COPY packages/db/ ./packages/db/
COPY packages/api/pyproject.toml ./packages/api/

# Install API dependencies without API application source
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package api --frozen --no-dev --no-install-project

# Copy API package sources
COPY packages/api/ ./packages/api/

# Complete installation of api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package api --frozen --no-dev

# ------------------------------------------------------------------------------
# Stage 4: Production image (serves API and compiled React SPA on port 8000)
# ------------------------------------------------------------------------------
FROM python:3.14-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/packages/api:/app/packages/db/src"

WORKDIR /app

# Copy virtual environment and code from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/packages/db /app/packages/db
COPY --from=builder /app/packages/api /app/packages/api

# Copy compiled frontend SPA from web-builder
COPY --from=web-builder /app/packages/api/static/app /app/packages/api/static/app

EXPOSE 8000

CMD ["fastapi", "run", "packages/api/main.py", "--host", "0.0.0.0", "--port", "8000"]

# ------------------------------------------------------------------------------
# Stage 5: Development image (supports live-reloading and volume mounts)
# ------------------------------------------------------------------------------
FROM base AS development

COPY pyproject.toml uv.lock ./
COPY packages/db/ ./packages/db/
COPY packages/api/pyproject.toml ./packages/api/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package api --frozen

COPY packages/api/ ./packages/api/

EXPOSE 8000

CMD ["uv", "run", "fastapi", "dev", "packages/api/main.py", "--host", "0.0.0.0", "--port", "8000"]
