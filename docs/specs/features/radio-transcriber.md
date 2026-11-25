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
  - performance/radio-transcriber/src/file_ingest.rs
tests:
  - performance/radio-transcriber/src/config.rs
  - performance/radio-transcriber/src/file_ingest.rs
  - performance/radio-transcriber/src/main.rs
---

# Radio Transcriber Local Audio Ingestion

## 1. Overview

`radio-transcriber` is a Rust service and a member of the `performance/` Cargo workspace. It ingests pre-recorded dispatch radio audio (`.mp3`, `.wav`, `.m4a`, or any format supported by FFmpeg) from a local samples directory, spawns an asynchronous `ffmpeg` child process to decode and resample the stream into standardized 16-bit signed little-endian mono linear PCM (`s16le`, default `16,000 Hz`), and streams fixed-duration `AudioChunk` payloads (`100ms` / `3,200 bytes` by default) over a bounded `tokio::sync::mpsc` channel to an asynchronous consumer worker with optional real-time pacing.

## 2. Requirements & Behavior

- Startup and pipeline sequence in `src/main.rs`:
  1. Initializes `tracing_subscriber` with `RUST_LOG` (default `info`).
  2. Builds `Config` from environment variables and logs the resolved values (`INGEST_MODE`, `AUDIO_FILE_PATH`, `SAMPLE_RATE`, `CHUNK_DURATION_MS`, `SIMULATE_REALTIME`, `SAMPLES_DIR`).
  3. Runs `verify_samples_dir()`. It requires `SAMPLES_DIR` to exist, be a directory, and be readable, and logs sorted entry names. Any failure aborts startup with a non-zero exit.
  4. Runs `verify_ffmpeg()`, which executes `ffmpeg -version` and logs the first output line. A missing binary or non-zero exit aborts startup.
  5. Instantiates `FileAudioIngester` from `FileIngestConfig`, opens a bounded `mpsc::channel::<AudioChunk>(32)`, and spawns an asynchronous consumer worker task along with a `Ctrl+C` / `SIGTERM` signal watcher.
  6. Executes `FileAudioIngester::run(tx)` to stream PCM chunks to the consumer. On clean EOF, the consumer drains remaining buffered chunks, logs final totals, and the process exits `0`. On `Ctrl+C` / `SIGTERM`, the consumer drops `rx`, triggering immediate termination and reaping of `ffmpeg`, and the process exits `0`.
- Local file ingestion and PCM transcoding in `src/file_ingest.rs`:
  - Computes chunk size as `sample_rate * channels * 2 * chunk_duration_ms / 1_000` bytes (`3,200` bytes at `16,000 Hz`, 1 channel, `100ms`).
  - Checks that `file_path` exists and is a regular file before spawning `ffmpeg`.
  - Spawns `ffmpeg -nostdin -i <file_path> -ac <channels> -ar <sample_rate> -f s16le -loglevel error pipe:1` with `stdin` set to null, `stdout`/`stderr` piped, and `kill_on_drop(true)`.
  - Drains `stderr` concurrently in a background task so pipe buffers never stall `ffmpeg` while preserving diagnostic messages on failure.
  - Reads exact `chunk_byte_size()` slices from `stdout`; emits any trailing partial chunk (`0 < len < chunk_byte_size`) at EOF so tail audio is preserved.
  - When `simulate_realtime` is `true`, sleeps for the remaining chunk interval between emissions using `tokio::time::sleep` while listening for `tx.closed()` for immediate shutdown. When `false`, emits chunks at full batch speed.
  - Cleanly kills and reaps (`child.kill().await` + `child.wait().await`) the `ffmpeg` child process whenever the receiver channel closes early.
- Relative paths resolve against the process working directory:
  - `/app` in the container, so `samples/...` resolves to the mounted `/app/samples`.
  - `performance/radio-transcriber` with `./run-dev.sh transcriber`.

## 3. Interfaces & Contracts

- **Environment variables** (`src/config.rs`; empty values count as unset):

  | Variable | Default | Accepted values |
  |---|---|---|
  | `INGEST_MODE` | `file` | `file` (case-insensitive) |
  | `AUDIO_FILE_PATH` | `samples/sample_dispatch.mp3` | Any regular file path |
  | `SIMULATE_REALTIME` | `true` | `true/false/1/0/yes/no/on/off` |
  | `SAMPLE_RATE` | `16000` | Positive integer (`u32 > 0`) |
  | `CHUNK_DURATION_MS` | `100` | Positive integer (`u32 > 0`) |
  | `SAMPLES_DIR` | `samples` | Any directory path |
  | `RUST_LOG` | `info` | `tracing-subscriber` `EnvFilter` syntax |

- **Internal Rust Payload Contract** (`src/file_ingest.rs`):
  - `FileIngestConfig { file_path: PathBuf, sample_rate: u32, channels: u16, chunk_duration_ms: u32, simulate_realtime: bool }` (implements `Default` and `From<&Config>`).
  - `AudioChunk { feed_id: String, source_path: PathBuf, pcm_bytes: Vec<u8>, sample_rate: u32, channels: u16, sequence: u64 }`.
  - `IngestStats { chunks_sent: u64, bytes_sent: u64, stopped_early: bool }`.
  - `FileAudioIngester::new(config)`, `FileAudioIngester::chunk_byte_size(&self) -> usize`, and `FileAudioIngester::run(&self, tx: mpsc::Sender<AudioChunk>) -> Result<IngestStats>`.
- **Container**: `performance/radio-transcriber/Dockerfile` is built from the repository root.
  - Builder stage: `rust:1-slim-bookworm`, running `cargo build --release --locked -p radio-transcriber`.
  - Runtime stage: `debian:bookworm-slim` with `ffmpeg` and `ca-certificates`, `WORKDIR /app`, `CMD ["radio-transcriber"]`.
- **Docker Compose** (`docker-compose.yml`): the `radio-transcriber` service passes the variables above, mounts `./performance/radio-transcriber/samples:/app/samples:ro`, and uses `restart: "no"` so finite sample runs do not loop continuously after EOF.
- **Developer CLI**: `./run-dev.sh transcriber` (alias `radio-transcriber`) runs `cargo run` inside `performance/radio-transcriber`.
- **Database / API**: none. The service doesn't touch PostgreSQL or the FastAPI contracts (see [architecture.md](../architecture.md)).

## 4. Edge Cases & Failure Modes

| Scenario | System Behavior | Expected Outcome / UX |
|---|---|---|
| `INGEST_MODE` is not `file` | `Config::from_env` returns `unsupported INGEST_MODE` | Process exits non-zero with the error logged |
| `SIMULATE_REALTIME` is not a recognized boolean | `Config::from_env` returns `invalid SIMULATE_REALTIME` | Process exits non-zero |
| `SAMPLE_RATE` or `CHUNK_DURATION_MS` is `0` or non-numeric | `Config::from_env` returns an invalid value error | Process exits non-zero |
| Samples directory is missing, unreadable, or a file | `verify_samples_dir` fails | Process exits non-zero; fix the volume mount or `SAMPLES_DIR` |
| `ffmpeg` is not installed or not on `PATH` | `verify_ffmpeg` fails | Process exits non-zero; use the runtime image or install ffmpeg locally |
| `AUDIO_FILE_PATH` does not exist or is a directory | `FileAudioIngester::run` fails pre-flight metadata check before spawning `ffmpeg` | Process exits non-zero with a clear path error |
| Audio file is corrupted or unsupported by FFmpeg | `ffmpeg` exits non-zero; stderr is collected and returned in the error | Process exits non-zero with FFmpeg status and stderr diagnostics |
| Audio duration is not an exact multiple of `CHUNK_DURATION_MS` | Final trailing bytes (`0 < len < chunk_byte_size`) are emitted as the last `AudioChunk` before clean EOF | No tail audio is dropped; process exits `0` |
| Consumer channel closes early or `Ctrl+C`/`SIGTERM` is received | `tx.closed()` / `SendError` breaks the read/sleep loop; `ffmpeg` is killed and reaped via `child.kill()` + `child.wait()` | Clean shutdown with exit `0` and zero orphaned `ffmpeg` processes |

## 5. Verification

- **Automated Tests**:
  - `src/config.rs`: defaults, empty-value fallback, overrides, boolean parsing, invalid mode/boolean/`SAMPLE_RATE`/`CHUNK_DURATION_MS` rejection.
  - `src/file_ingest.rs`: default config, chunk byte size calculations (8kHz, 16kHz, 48kHz, mono/stereo, varying chunk durations), zero-value config rejection, missing-file and directory errors, 44.1kHz-stereo-to-16kHz-mono resampling & clean EOF detection, trailing partial chunk emission at EOF, `simulate_realtime` pacing timing, early receiver-close termination without hanging, and corrupted-file error reporting.
  - `src/main.rs`: samples directory listing, missing directory, and file-instead-of-directory errors.
  - Run `cargo test --manifest-path performance/radio-transcriber/Cargo.toml` and `cargo clippy --manifest-path performance/radio-transcriber/Cargo.toml --all-targets -- -D warnings`.
- **Manual Checks**:
  - Generate a local sample (e.g., `ffmpeg -f lavfi -i sine=frequency=440:duration=2 -q:a 2 performance/radio-transcriber/samples/sample_dispatch.mp3`) and run `SIMULATE_REALTIME=false ./run-dev.sh transcriber` and `SIMULATE_REALTIME=true ./run-dev.sh transcriber` to verify 3,200-byte chunk streaming, ~100ms real-time pacing, and clean EOF exit.
  - Interrupt a longer run with `Ctrl+C` and confirm no `ffmpeg` child process remains (`pgrep -fl ffmpeg`).
