//! Local audio file ingestion and FFmpeg PCM transcoding engine.
//!
//! Spawns an asynchronous `ffmpeg` subprocess to decode and resample a local
//! audio file (`.mp3`, `.wav`, `.m4a`, etc.) into standardized 16-bit signed
//! little-endian linear PCM (`s16le`), streaming fixed-duration [`AudioChunk`]
//! payloads over a Tokio MPSC channel with optional real-time pacing.

use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::time::Duration;

use anyhow::{bail, Context, Result};
use tokio::io::{AsyncRead, AsyncReadExt};
use tokio::process::Command;
use tokio::sync::mpsc;
use tokio::time::{sleep, Instant};
use tracing::{debug, info};

use crate::config::{
    Config, DEFAULT_AUDIO_FILE_PATH, DEFAULT_CHANNELS, DEFAULT_CHUNK_DURATION_MS,
    DEFAULT_SAMPLE_RATE, DEFAULT_SIMULATE_REALTIME,
};

/// Bytes per PCM sample for 16-bit signed little-endian linear PCM (`s16le`).
pub const BYTES_PER_SAMPLE: usize = 2;

/// Configuration for [`FileAudioIngester`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileIngestConfig {
    pub file_path: PathBuf,
    pub sample_rate: u32,
    pub channels: u16,
    pub chunk_duration_ms: u32,
    pub simulate_realtime: bool,
}

impl Default for FileIngestConfig {
    fn default() -> Self {
        Self {
            file_path: PathBuf::from(DEFAULT_AUDIO_FILE_PATH),
            sample_rate: DEFAULT_SAMPLE_RATE,
            channels: DEFAULT_CHANNELS,
            chunk_duration_ms: DEFAULT_CHUNK_DURATION_MS,
            simulate_realtime: DEFAULT_SIMULATE_REALTIME,
        }
    }
}

impl From<&Config> for FileIngestConfig {
    fn from(cfg: &Config) -> Self {
        Self {
            file_path: cfg.audio_file_path.clone(),
            sample_rate: cfg.sample_rate,
            channels: DEFAULT_CHANNELS,
            chunk_duration_ms: cfg.chunk_duration_ms,
            simulate_realtime: cfg.simulate_realtime,
        }
    }
}

/// A discrete slice of decoded `s16le` PCM audio emitted by an ingester.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AudioChunk {
    pub feed_id: String,
    pub source_path: PathBuf,
    pub pcm_bytes: Vec<u8>,
    pub sample_rate: u32,
    pub channels: u16,
    pub sequence: u64,
}

/// Summary statistics returned when [`FileAudioIngester::run`] finishes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct IngestStats {
    pub chunks_sent: u64,
    pub bytes_sent: u64,
    pub stopped_early: bool,
}

/// Reads a local audio file, transcodes it to `s16le` PCM via `ffmpeg`, and
/// streams [`AudioChunk`] frames across an asynchronous MPSC channel.
#[derive(Debug, Clone)]
pub struct FileAudioIngester {
    config: FileIngestConfig,
}

impl FileAudioIngester {
    /// Create a new [`FileAudioIngester`] with the given configuration.
    pub fn new(config: FileIngestConfig) -> Self {
        Self { config }
    }

    /// Return the expected byte size of a full PCM chunk for the configured
    /// sample rate, channel count, and chunk duration (`s16le` = 2 bytes/sample).
    pub fn chunk_byte_size(&self) -> usize {
        let bytes = (self.config.sample_rate as u64)
            * (self.config.channels as u64)
            * (BYTES_PER_SAMPLE as u64)
            * (self.config.chunk_duration_ms as u64)
            / 1_000;
        bytes as usize
    }

    /// Decode and stream the configured audio file as PCM chunks into `tx`.
    ///
    /// - Validates configuration and verifies file existence before spawning `ffmpeg`.
    /// - Emits exact `chunk_byte_size()` chunks, plus any trailing partial chunk at EOF.
    /// - Sleeps between emissions when `simulate_realtime` is enabled.
    /// - Cleanly terminates and reaps `ffmpeg` if `tx` is closed early or on EOF.
    pub async fn run(&self, tx: mpsc::Sender<AudioChunk>) -> Result<IngestStats> {
        let chunk_size = self.validate_config()?;

        let meta = tokio::fs::metadata(&self.config.file_path)
            .await
            .with_context(|| {
                format!(
                    "audio file '{}' does not exist or is not accessible",
                    self.config.file_path.display()
                )
            })?;
        if !meta.is_file() {
            bail!(
                "audio path '{}' is not a regular file",
                self.config.file_path.display()
            );
        }

        let feed_id = derive_feed_id(&self.config.file_path);
        let chunk_duration = Duration::from_millis(self.config.chunk_duration_ms as u64);

        info!(
            feed_id = %feed_id,
            source_path = %self.config.file_path.display(),
            sample_rate = self.config.sample_rate,
            channels = self.config.channels,
            chunk_duration_ms = self.config.chunk_duration_ms,
            chunk_byte_size = chunk_size,
            simulate_realtime = self.config.simulate_realtime,
            "starting local file audio ingestion via ffmpeg"
        );

        let mut child = Command::new("ffmpeg")
            .arg("-nostdin")
            .arg("-i")
            .arg(&self.config.file_path)
            .arg("-ac")
            .arg(self.config.channels.to_string())
            .arg("-ar")
            .arg(self.config.sample_rate.to_string())
            .arg("-f")
            .arg("s16le")
            .arg("-loglevel")
            .arg("error")
            .arg("pipe:1")
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true)
            .spawn()
            .context("failed to spawn ffmpeg subprocess")?;

        let mut stdout = child
            .stdout
            .take()
            .context("failed to capture ffmpeg stdout pipe")?;

        let stderr_handle = child.stderr.take().map(|mut stderr| {
            tokio::spawn(async move {
                let mut buf = Vec::new();
                let _ = stderr.read_to_end(&mut buf).await;
                String::from_utf8_lossy(&buf).trim().to_string()
            })
        });

        let mut chunks_sent: u64 = 0;
        let mut bytes_sent: u64 = 0;
        let mut stopped_early = false;

        loop {
            let iter_start = Instant::now();

            let read_result = tokio::select! {
                biased;
                _ = tx.closed() => {
                    stopped_early = true;
                    break;
                }
                res = read_pcm_chunk(&mut stdout, chunk_size) => res,
            };

            let pcm_bytes = match read_result {
                Ok(buf) => buf,
                Err(err) => {
                    drop(stdout);
                    let _ = child.kill().await;
                    let _ = child.wait().await;
                    if let Some(handle) = stderr_handle {
                        handle.abort();
                    }
                    return Err(err).context("failed reading PCM bytes from ffmpeg stdout");
                }
            };

            if pcm_bytes.is_empty() {
                debug!(feed_id = %feed_id, "reached clean EOF on ffmpeg stdout");
                break;
            }

            let is_partial = pcm_bytes.len() < chunk_size;
            let len = pcm_bytes.len();
            let sequence = chunks_sent;

            let chunk = AudioChunk {
                feed_id: feed_id.clone(),
                source_path: self.config.file_path.clone(),
                pcm_bytes,
                sample_rate: self.config.sample_rate,
                channels: self.config.channels,
                sequence,
            };

            if tx.send(chunk).await.is_err() {
                stopped_early = true;
                break;
            }

            chunks_sent += 1;
            bytes_sent += len as u64;

            if is_partial {
                debug!(
                    feed_id = %feed_id,
                    trailing_bytes = len,
                    "emitted final partial PCM chunk at EOF"
                );
                break;
            }

            if self.config.simulate_realtime {
                let delay = chunk_duration.saturating_sub(iter_start.elapsed());
                if !delay.is_zero() {
                    tokio::select! {
                        biased;
                        _ = tx.closed() => {
                            stopped_early = true;
                            break;
                        }
                        _ = sleep(delay) => {}
                    }
                }
            }
        }

        drop(stdout);

        if stopped_early {
            info!(
                feed_id = %feed_id,
                chunks_sent,
                bytes_sent,
                "receiver channel closed; terminating ffmpeg child process"
            );
            let _ = child.kill().await;
            let _ = child.wait().await;
            if let Some(handle) = stderr_handle {
                handle.abort();
            }
            return Ok(IngestStats {
                chunks_sent,
                bytes_sent,
                stopped_early: true,
            });
        }

        let status = child
            .wait()
            .await
            .context("failed waiting for ffmpeg child process to exit")?;

        let stderr_text = match stderr_handle {
            Some(handle) => handle.await.unwrap_or_default(),
            None => String::new(),
        };

        if !status.success() {
            let detail = if stderr_text.is_empty() {
                "no stderr output".to_string()
            } else {
                stderr_text
            };
            bail!("ffmpeg exited with status {status}: {detail}");
        }

        info!(
            feed_id = %feed_id,
            chunks_sent,
            bytes_sent,
            "completed local file audio ingestion"
        );

        Ok(IngestStats {
            chunks_sent,
            bytes_sent,
            stopped_early: false,
        })
    }

    fn validate_config(&self) -> Result<usize> {
        if self.config.sample_rate == 0 {
            bail!("sample_rate must be greater than 0");
        }
        if self.config.channels == 0 {
            bail!("channels must be greater than 0");
        }
        if self.config.chunk_duration_ms == 0 {
            bail!("chunk_duration_ms must be greater than 0");
        }
        let chunk_size = self.chunk_byte_size();
        if chunk_size == 0 {
            bail!(
                "computed chunk_byte_size is 0 for sample_rate={}, channels={}, chunk_duration_ms={}",
                self.config.sample_rate,
                self.config.channels,
                self.config.chunk_duration_ms
            );
        }
        Ok(chunk_size)
    }
}

/// Derive a concise feed identifier from the source file path.
fn derive_feed_id(path: &Path) -> String {
    path.file_stem()
        .and_then(|s| s.to_str())
        .filter(|s| !s.is_empty())
        .map(ToOwned::to_owned)
        .unwrap_or_else(|| path.display().to_string())
}

/// Read up to `chunk_size` bytes from `reader`, looping until the buffer is full
/// or EOF (`0` bytes read) is reached.
///
/// - Empty `Vec` indicates clean EOF on a chunk boundary.
/// - `0 < len < chunk_size` indicates the final trailing chunk before EOF.
/// - `len == chunk_size` indicates a full chunk.
async fn read_pcm_chunk<R: AsyncRead + Unpin>(
    reader: &mut R,
    chunk_size: usize,
) -> std::io::Result<Vec<u8>> {
    let mut buf = vec![0u8; chunk_size];
    let mut filled = 0;

    while filled < chunk_size {
        let n = reader.read(&mut buf[filled..]).await?;
        if n == 0 {
            buf.truncate(filled);
            return Ok(buf);
        }
        filled += n;
    }

    Ok(buf)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};

    static TEST_COUNTER: AtomicU64 = AtomicU64::new(0);

    struct TempAudioFile {
        path: PathBuf,
    }

    impl TempAudioFile {
        fn new_path(label: &str, ext: &str) -> Self {
            let seq = TEST_COUNTER.fetch_add(1, Ordering::Relaxed);
            let path = std::env::temp_dir().join(format!(
                "radio-transcriber-ingest-{label}-{}-{seq}.{ext}",
                std::process::id()
            ));
            Self { path }
        }

        /// Write a valid PCM WAV file with a synthetic 440Hz sine wave.
        fn synthetic_wav(label: &str, sample_rate: u32, channels: u16, duration_ms: u32) -> Self {
            let file = Self::new_path(label, "wav");
            let total_frames = ((sample_rate as u64) * (duration_ms as u64) / 1_000) as usize;
            let bytes_per_sample: u16 = 2;
            let block_align = channels * bytes_per_sample;
            let byte_rate = sample_rate * (block_align as u32);
            let data_size = (total_frames * (block_align as usize)) as u32;
            let riff_chunk_size = 36 + data_size;

            let mut bytes = Vec::with_capacity(44 + data_size as usize);
            bytes.extend_from_slice(b"RIFF");
            bytes.extend_from_slice(&riff_chunk_size.to_le_bytes());
            bytes.extend_from_slice(b"WAVE");
            bytes.extend_from_slice(b"fmt ");
            bytes.extend_from_slice(&16u32.to_le_bytes()); // PCM fmt chunk size
            bytes.extend_from_slice(&1u16.to_le_bytes()); // AudioFormat = PCM
            bytes.extend_from_slice(&channels.to_le_bytes());
            bytes.extend_from_slice(&sample_rate.to_le_bytes());
            bytes.extend_from_slice(&byte_rate.to_le_bytes());
            bytes.extend_from_slice(&block_align.to_le_bytes());
            bytes.extend_from_slice(&(bytes_per_sample * 8).to_le_bytes());
            bytes.extend_from_slice(b"data");
            bytes.extend_from_slice(&data_size.to_le_bytes());

            let freq = 440.0_f64;
            for frame in 0..total_frames {
                let t = frame as f64 / sample_rate as f64;
                let sample = ((2.0 * std::f64::consts::PI * freq * t).sin() * 12_000.0) as i16;
                for _ in 0..channels {
                    bytes.extend_from_slice(&sample.to_le_bytes());
                }
            }

            std::fs::write(&file.path, bytes).expect("write synthetic wav");
            file
        }

        fn path(&self) -> &Path {
            &self.path
        }
    }

    impl Drop for TempAudioFile {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.path);
        }
    }

    #[test]
    fn default_config_and_chunk_size() {
        let cfg = FileIngestConfig::default();
        assert_eq!(cfg.file_path, PathBuf::from(DEFAULT_AUDIO_FILE_PATH));
        assert_eq!(cfg.sample_rate, 16_000);
        assert_eq!(cfg.channels, 1);
        assert_eq!(cfg.chunk_duration_ms, 100);
        assert!(cfg.simulate_realtime);

        let ingester = FileAudioIngester::new(cfg);
        assert_eq!(ingester.chunk_byte_size(), 3_200);
    }

    #[test]
    fn chunk_byte_size_calculations() {
        let cases = [
            // (sample_rate, channels, chunk_duration_ms, expected_bytes)
            (8_000, 1, 100, 1_600),
            (8_000, 1, 20, 320),
            (8_000, 2, 100, 3_200),
            (16_000, 1, 100, 3_200),
            (16_000, 1, 50, 1_600),
            (16_000, 1, 250, 8_000),
            (16_000, 2, 100, 6_400),
            (48_000, 1, 20, 1_920),
        ];

        for (sample_rate, channels, chunk_duration_ms, expected) in cases {
            let ingester = FileAudioIngester::new(FileIngestConfig {
                sample_rate,
                channels,
                chunk_duration_ms,
                ..FileIngestConfig::default()
            });
            assert_eq!(
                ingester.chunk_byte_size(),
                expected,
                "rate={sample_rate}, channels={channels}, duration_ms={chunk_duration_ms}"
            );
        }
    }

    #[tokio::test]
    async fn rejects_zero_config_values() {
        let (tx, _rx) = mpsc::channel(4);

        let bad_configs = [
            FileIngestConfig {
                sample_rate: 0,
                ..FileIngestConfig::default()
            },
            FileIngestConfig {
                channels: 0,
                ..FileIngestConfig::default()
            },
            FileIngestConfig {
                chunk_duration_ms: 0,
                ..FileIngestConfig::default()
            },
        ];

        for cfg in bad_configs {
            let ingester = FileAudioIngester::new(cfg);
            assert!(ingester.run(tx.clone()).await.is_err());
        }
    }

    #[tokio::test]
    async fn errors_when_audio_file_does_not_exist() {
        let missing = std::env::temp_dir().join(format!(
            "radio-transcriber-definitely-missing-{}.mp3",
            std::process::id()
        ));
        let _ = std::fs::remove_file(&missing);

        let ingester = FileAudioIngester::new(FileIngestConfig {
            file_path: missing,
            simulate_realtime: false,
            ..FileIngestConfig::default()
        });

        let (tx, mut rx) = mpsc::channel(8);
        let err = ingester.run(tx).await.unwrap_err();
        assert!(format!("{err:#}").contains("does not exist"));
        assert!(rx.recv().await.is_none());
    }

    #[tokio::test]
    async fn errors_when_audio_path_is_directory() {
        let dir = std::env::temp_dir().join(format!(
            "radio-transcriber-dir-check-{}",
            std::process::id()
        ));
        std::fs::create_dir_all(&dir).unwrap();

        let ingester = FileAudioIngester::new(FileIngestConfig {
            file_path: dir.clone(),
            simulate_realtime: false,
            ..FileIngestConfig::default()
        });

        let (tx, _rx) = mpsc::channel(8);
        let err = ingester.run(tx).await.unwrap_err();
        assert!(format!("{err:#}").contains("not a regular file"));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[tokio::test]
    async fn decodes_resamples_and_detects_clean_eof() {
        // 0.5s at 44.1kHz stereo -> resampled to 16kHz mono s16le = 16,000 bytes = 5 x 3,200B
        let sample = TempAudioFile::synthetic_wav("resample_eof", 44_100, 2, 500);

        let ingester = FileAudioIngester::new(FileIngestConfig {
            file_path: sample.path().to_path_buf(),
            sample_rate: 16_000,
            channels: 1,
            chunk_duration_ms: 100,
            simulate_realtime: false,
        });

        let (tx, mut rx) = mpsc::channel(16);
        let consumer = tokio::spawn(async move {
            let mut chunks = Vec::new();
            while let Some(chunk) = rx.recv().await {
                chunks.push(chunk);
            }
            chunks
        });

        let stats = ingester.run(tx).await.unwrap();
        let chunks = consumer.await.unwrap();

        assert!(!stats.stopped_early);
        assert_eq!(stats.chunks_sent, chunks.len() as u64);
        assert_eq!(chunks.len(), 5);
        assert_eq!(stats.bytes_sent, 16_000);

        for (idx, chunk) in chunks.iter().enumerate() {
            assert_eq!(chunk.sequence, idx as u64);
            assert_eq!(chunk.pcm_bytes.len(), 3_200);
            assert_eq!(chunk.sample_rate, 16_000);
            assert_eq!(chunk.channels, 1);
            assert_eq!(chunk.source_path, sample.path());
            assert!(chunk
                .feed_id
                .starts_with("radio-transcriber-ingest-resample_eof"));
        }
    }

    #[tokio::test]
    async fn emits_final_partial_chunk_on_non_aligned_eof() {
        // 0.35s at 16kHz mono = 11,200 bytes = 3 x 3,200B + 1 x 1,600B
        let sample = TempAudioFile::synthetic_wav("partial_eof", 16_000, 1, 350);

        let ingester = FileAudioIngester::new(FileIngestConfig {
            file_path: sample.path().to_path_buf(),
            sample_rate: 16_000,
            channels: 1,
            chunk_duration_ms: 100,
            simulate_realtime: false,
        });

        let (tx, mut rx) = mpsc::channel(16);
        let consumer = tokio::spawn(async move {
            let mut chunks = Vec::new();
            while let Some(chunk) = rx.recv().await {
                chunks.push(chunk);
            }
            chunks
        });

        let stats = ingester.run(tx).await.unwrap();
        let chunks = consumer.await.unwrap();

        assert!(!stats.stopped_early);
        assert_eq!(chunks.len(), 4);
        assert_eq!(chunks[0].pcm_bytes.len(), 3_200);
        assert_eq!(chunks[1].pcm_bytes.len(), 3_200);
        assert_eq!(chunks[2].pcm_bytes.len(), 3_200);
        assert_eq!(chunks[3].pcm_bytes.len(), 1_600);
        assert_eq!(stats.bytes_sent, 11_200);
    }

    #[tokio::test]
    async fn simulate_realtime_paces_chunk_emissions() {
        // 0.4s at 16kHz mono = 4 chunks of 100ms
        let sample = TempAudioFile::synthetic_wav("pacing", 16_000, 1, 400);

        let ingester = FileAudioIngester::new(FileIngestConfig {
            file_path: sample.path().to_path_buf(),
            sample_rate: 16_000,
            channels: 1,
            chunk_duration_ms: 100,
            simulate_realtime: true,
        });

        let (tx, mut rx) = mpsc::channel(16);
        let consumer = tokio::spawn(async move {
            let mut count = 0usize;
            while rx.recv().await.is_some() {
                count += 1;
            }
            count
        });

        let start = Instant::now();
        let stats = ingester.run(tx).await.unwrap();
        let elapsed = start.elapsed();
        let count = consumer.await.unwrap();

        assert_eq!(count, 4);
        assert_eq!(stats.chunks_sent, 4);
        assert!(
            elapsed >= Duration::from_millis(320),
            "expected realtime pacing >= 320ms for 400ms clip, got {elapsed:?}"
        );
    }

    #[tokio::test]
    async fn stops_cleanly_when_receiver_closes_early() {
        // 5.0s clip in realtime mode would take ~5s if not terminated early
        let sample = TempAudioFile::synthetic_wav("early_close", 16_000, 1, 5_000);

        let ingester = FileAudioIngester::new(FileIngestConfig {
            file_path: sample.path().to_path_buf(),
            sample_rate: 16_000,
            channels: 1,
            chunk_duration_ms: 100,
            simulate_realtime: true,
        });

        let (tx, mut rx) = mpsc::channel(4);
        let consumer = tokio::spawn(async move {
            let mut received = 0usize;
            while rx.recv().await.is_some() {
                received += 1;
                if received == 2 {
                    break;
                }
            }
            drop(rx);
            received
        });

        let start = Instant::now();
        let stats = ingester.run(tx).await.unwrap();
        let elapsed = start.elapsed();
        let received = consumer.await.unwrap();

        assert_eq!(received, 2);
        assert!(stats.stopped_early);
        assert!(
            elapsed < Duration::from_millis(1_500),
            "expected prompt shutdown when receiver closes, took {elapsed:?}"
        );
    }

    #[tokio::test]
    async fn errors_on_corrupted_audio_file() {
        let bad_file = TempAudioFile::new_path("corrupt", "mp3");
        std::fs::write(bad_file.path(), b"this is definitely not valid audio data").unwrap();

        let ingester = FileAudioIngester::new(FileIngestConfig {
            file_path: bad_file.path().to_path_buf(),
            sample_rate: 16_000,
            channels: 1,
            chunk_duration_ms: 100,
            simulate_realtime: false,
        });

        let (tx, _rx) = mpsc::channel(8);
        let err = ingester.run(tx).await.unwrap_err();
        assert!(
            format!("{err:#}").contains("ffmpeg exited with status"),
            "unexpected error: {err:#}"
        );
    }
}
