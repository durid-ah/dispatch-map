# syntax=docker/dockerfile:1.9
# Build from the repository root:
#   docker build -f performance/radio-transcriber/Dockerfile .

# ------------------------------------------------------------------------------
# Stage 1: Rust builder (release binary)
# ------------------------------------------------------------------------------
FROM rust:1-slim-bookworm AS builder

WORKDIR /app/performance

COPY performance/Cargo.toml performance/Cargo.lock ./
COPY performance/radio-transcriber/Cargo.toml ./radio-transcriber/Cargo.toml
COPY performance/radio-transcriber/src ./radio-transcriber/src

RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/performance/target \
    cargo build --release --locked -p radio-transcriber \
    && cp target/release/radio-transcriber /usr/local/bin/radio-transcriber

# ------------------------------------------------------------------------------
# Stage 2: Runtime image with FFmpeg
# ------------------------------------------------------------------------------
FROM debian:bookworm-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/bin/radio-transcriber /usr/local/bin/radio-transcriber

CMD ["radio-transcriber"]
