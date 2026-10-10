# syntax=docker/dockerfile:1.9

# ------------------------------------------------------------------------------
# Base Python & uv configuration
# ------------------------------------------------------------------------------
FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/packages/db/src"

WORKDIR /app

# Copy workspace configuration and dependencies
COPY pyproject.toml uv.lock ./
COPY packages/db/ ./packages/db/
COPY packages/migrations/pyproject.toml ./packages/migrations/

# Install migration dependencies (alembic and database driver)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package migrations --frozen --no-dev --no-install-project

# Copy migration configuration and scripts
COPY packages/migrations/ ./packages/migrations/

WORKDIR /app/packages/migrations

CMD ["alembic", "upgrade", "head"]
