---
feature: radio-transcriber
title: Radio Transcriber Local Audio Ingestion
status: experimental
packages:
  - performance/radio-transcriber
source_files:
  - performance/Cargo.toml
  - performance/radio-transcriber/Cargo.toml
  - performance/radio-transcriber/Dockerfile
  - performance/radio-transcriber/src/main.rs
  - performance/radio-transcriber/src/config.rs
tests:
  - performance/radio-transcriber/src/config.rs
  - performance/radio-transcriber/src/main.rs
---

# Radio Transcriber Local Audio Ingestion

## 1. Overview

`radio-transcriber` is a Rust service and a member of the `performance/` Cargo workspace. It ingests pre-recorded dispatch radio audio (`.mp3`, `.wav`, `.m4a`) from a local samples directory, so development doesn't depend on paid APIs or live streams. In the current scaffold it resolves its configuration, checks that the samples directory is accessible and the `ffmpeg` binary is available (FFmpeg is the planned 16kHz PCM transcoder), and then runs until it gets a shutdown signal.

## 2. Requirements & Behavior

- Startup sequence in `src/main.rs`:
  1. Initializes `tracing_subscriber` with `RUST_LOG` (default `info`).
  2. Builds `Config` from environment variables and logs the resolved values.
  3. Runs `verify_samples_dir()`. It requires `SAMPLES_DIR` to exist, be a directory, and be readable, and it logs the sorted entry names. Any failure aborts startup with a non-zero exit.
  4. Runs `verify_ffmpeg()`, which executes `ffmpeg -version` and logs the first output line. A missing binary or a non-zero exit aborts startup.
  5. Logs `audio file found` if `AUDIO_FILE_PATH` exists, otherwise a warning. A missing audio file is **not** fatal.
  6. Waits for `Ctrl+C` / `SIGTERM`, then exits `0`.
- Relative paths resolve against the process working directory:
  - `/app` in the container, so `samples/...` resolves to the mounted `/app/samples`.
  - `performance/radio-transcriber` with `./run-dev.sh transcriber`.

## 3. Interfaces & Contracts

- **Environment variables** (`src/config.rs`; empty values count as unset):

  | Variable | Default | Accepted values |
  |---|---|---|
  | `INGEST_MODE` | `file` | `file` (case-insensitive) |
  | `AUDIO_FILE_PATH` | `samples/sample_dispatch.mp3` | Any path |
  | `SIMULATE_REALTIME` | `true` | `true/false/1/0/yes/no/on/off` |
  | `SAMPLES_DIR` | `samples` | Any directory path |
  | `RUST_LOG` | `info` | `tracing-subscriber` `EnvFilter` syntax |

- **Container**: `performance/radio-transcriber/Dockerfile` is built from the repository root.
  - Builder stage: `rust:1-slim-bookworm`, running `cargo build --release --locked -p radio-transcriber`.
  - Runtime stage: `debian:bookworm-slim` with `ffmpeg` and `ca-certificates`, `WORKDIR /app`, `CMD ["radio-transcriber"]`.
- **Docker Compose** (`docker-compose.yml`): the `radio-transcriber` service passes the variables above and mounts `./performance/radio-transcriber/samples:/app/samples:ro`.
- **Developer CLI**: `./run-dev.sh transcriber` (alias `radio-transcriber`) runs `cargo run` inside `performance/radio-transcriber`.
- **Database / API**: none. The service doesn't touch PostgreSQL or the FastAPI contracts (see [architecture.md](../architecture.md)).

## 4. Edge Cases & Failure Modes

| Scenario | System Behavior | Expected Outcome / UX |
|---|---|---|
| `INGEST_MODE` is not `file` | `Config::from_env` returns `unsupported INGEST_MODE` | Process exits non-zero with the error logged |
| `SIMULATE_REALTIME` is not a recognized boolean | `Config::from_env` returns `invalid SIMULATE_REALTIME` | Process exits non-zero |
| Samples directory is missing, unreadable, or a file | `verify_samples_dir` fails | Process exits non-zero; fix the volume mount or `SAMPLES_DIR` |
| `ffmpeg` is not installed or not on `PATH` | `verify_ffmpeg` fails | Process exits non-zero; use the runtime image or install ffmpeg locally |
| `AUDIO_FILE_PATH` does not exist | A warning is logged | Service stays up so fresh clones without committed audio still boot |

## 5. Verification

- **Automated Tests**:
  - `src/config.rs`: defaults, empty-value fallback, overrides, boolean parsing, invalid mode/boolean rejection.
  - `src/main.rs`: samples directory listing, missing directory, and file-instead-of-directory errors.
  - Run `cargo test --manifest-path performance/radio-transcriber/Cargo.toml` and `cargo check --manifest-path performance/radio-transcriber/Cargo.toml`.
- **Manual Checks**:
  - `docker compose build radio-transcriber`, then `docker compose run --rm radio-transcriber ffmpeg -version`.
  - `docker compose up radio-transcriber` logs the config, the `/app/samples` listing, the ffmpeg version, and `ready; waiting for shutdown signal`.
