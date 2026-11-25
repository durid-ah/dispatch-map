//! radio-transcriber: local-file audio ingestion service.
//!
//! On startup the service resolves its configuration from the environment,
//! verifies access to the samples directory and the `ffmpeg` binary, and runs
//! the local audio file ingestion pipeline streaming PCM chunks over an MPSC
//! channel to an asynchronous consumer worker.

mod config;
mod file_ingest;

use std::path::Path;

use anyhow::{bail, Context, Result};
use tokio::process::Command;
use tokio::sync::{mpsc, watch};
use tracing::{info, warn};
use tracing_subscriber::EnvFilter;

use crate::config::Config;
use crate::file_ingest::{AudioChunk, FileAudioIngester, FileIngestConfig};

const CHANNEL_CAPACITY: usize = 32;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()))
        .init();

    let cfg = Config::from_env(|key| std::env::var(key).ok())?;
    info!(
        ingest_mode = %cfg.ingest_mode,
        audio_file_path = %cfg.audio_file_path.display(),
        sample_rate = cfg.sample_rate,
        chunk_duration_ms = cfg.chunk_duration_ms,
        simulate_realtime = cfg.simulate_realtime,
        samples_dir = %cfg.samples_dir.display(),
        "radio-transcriber starting"
    );

    let entries = verify_samples_dir(&cfg.samples_dir).await?;
    info!(
        samples_dir = %cfg.samples_dir.display(),
        count = entries.len(),
        files = ?entries,
        "samples directory is accessible"
    );

    let ffmpeg_version = verify_ffmpeg().await?;
    info!(version = %ffmpeg_version, "ffmpeg is available");

    let ingest_cfg = FileIngestConfig::from(&cfg);
    let ingester = FileAudioIngester::new(ingest_cfg);

    let (tx, rx) = mpsc::channel::<AudioChunk>(CHANNEL_CAPACITY);
    let (shutdown_tx, shutdown_rx) = watch::channel(false);

    let signal_handle = tokio::spawn(async move {
        shutdown_signal().await;
        info!("shutdown signal received; stopping ingestion pipeline");
        let _ = shutdown_tx.send(true);
    });

    let consumer_handle = tokio::spawn(run_consumer(rx, shutdown_rx));

    let ingest_result = ingester.run(tx).await;
    signal_handle.abort();

    let (chunks_consumed, bytes_consumed) = consumer_handle
        .await
        .context("audio consumer task panicked")?;

    let stats = ingest_result?;
    info!(
        chunks_sent = stats.chunks_sent,
        bytes_sent = stats.bytes_sent,
        chunks_consumed,
        bytes_consumed,
        stopped_early = stats.stopped_early,
        "radio-transcriber finished"
    );
    Ok(())
}

/// Pulls [`AudioChunk`] items from the MPSC channel until the sender finishes
/// or a shutdown signal is received. Dropping `rx` signals the ingester to
/// terminate its `ffmpeg` subprocess cleanly.
async fn run_consumer(
    mut rx: mpsc::Receiver<AudioChunk>,
    mut shutdown_rx: watch::Receiver<bool>,
) -> (u64, u64) {
    let mut chunks_consumed: u64 = 0;
    let mut bytes_consumed: u64 = 0;

    loop {
        tokio::select! {
            biased;
            changed = shutdown_rx.changed() => {
                if changed.is_err() || *shutdown_rx.borrow() {
                    info!(
                        chunks_consumed,
                        bytes_consumed,
                        "consumer stopping on shutdown signal"
                    );
                    break;
                }
            }
            maybe_chunk = rx.recv() => {
                match maybe_chunk {
                    Some(chunk) => {
                        chunks_consumed += 1;
                        bytes_consumed += chunk.pcm_bytes.len() as u64;
                        info!(
                            feed_id = %chunk.feed_id,
                            sequence = chunk.sequence,
                            bytes = chunk.pcm_bytes.len(),
                            sample_rate = chunk.sample_rate,
                            channels = chunk.channels,
                            "received PCM audio chunk"
                        );
                    }
                    None => {
                        info!(
                            chunks_consumed,
                            bytes_consumed,
                            "audio channel closed; consumer finished"
                        );
                        break;
                    }
                }
            }
        }
    }

    drop(rx);
    (chunks_consumed, bytes_consumed)
}

/// Ensure `dir` exists, is a directory, and is readable. Returns sorted entry names.
async fn verify_samples_dir(dir: &Path) -> Result<Vec<String>> {
    let meta = tokio::fs::metadata(dir)
        .await
        .with_context(|| format!("samples directory '{}' is not accessible", dir.display()))?;
    if !meta.is_dir() {
        bail!("samples path '{}' is not a directory", dir.display());
    }

    let mut reader = tokio::fs::read_dir(dir)
        .await
        .with_context(|| format!("failed to read samples directory '{}'", dir.display()))?;
    let mut names = Vec::new();
    while let Some(entry) = reader.next_entry().await? {
        names.push(entry.file_name().to_string_lossy().into_owned());
    }
    names.sort();
    Ok(names)
}

/// Run `ffmpeg -version` and return the first line of its output.
async fn verify_ffmpeg() -> Result<String> {
    let output = Command::new("ffmpeg")
        .arg("-version")
        .output()
        .await
        .context("failed to execute 'ffmpeg'; is it installed and on PATH?")?;
    if !output.status.success() {
        bail!("'ffmpeg -version' exited with status {}", output.status);
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    Ok(stdout.lines().next().unwrap_or_default().trim().to_string())
}

async fn shutdown_signal() {
    let ctrl_c = async {
        if let Err(err) = tokio::signal::ctrl_c().await {
            warn!(error = %err, "failed to listen for Ctrl+C");
            std::future::pending::<()>().await;
        }
    };

    #[cfg(unix)]
    let terminate = async {
        match tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate()) {
            Ok(mut sig) => {
                sig.recv().await;
            }
            Err(err) => {
                warn!(error = %err, "failed to listen for SIGTERM");
                std::future::pending::<()>().await;
            }
        }
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn temp_dir(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "radio-transcriber-test-{}-{}",
            name,
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[tokio::test]
    async fn verify_samples_dir_lists_entries() {
        let dir = temp_dir("list");
        std::fs::write(dir.join("b.wav"), b"").unwrap();
        std::fs::write(dir.join("a.mp3"), b"").unwrap();

        let entries = verify_samples_dir(&dir).await.unwrap();
        assert_eq!(entries, vec!["a.mp3".to_string(), "b.wav".to_string()]);

        std::fs::remove_dir_all(&dir).unwrap();
    }

    #[tokio::test]
    async fn verify_samples_dir_missing_errors() {
        let dir = std::env::temp_dir().join("radio-transcriber-test-definitely-missing");
        let _ = std::fs::remove_dir_all(&dir);
        let err = verify_samples_dir(&dir).await.unwrap_err();
        assert!(err.to_string().contains("not accessible"));
    }

    #[tokio::test]
    async fn verify_samples_dir_rejects_file() {
        let dir = temp_dir("file");
        let file = dir.join("not-a-dir.txt");
        std::fs::write(&file, b"").unwrap();

        let err = verify_samples_dir(&file).await.unwrap_err();
        assert!(err.to_string().contains("not a directory"));

        std::fs::remove_dir_all(&dir).unwrap();
    }
}
