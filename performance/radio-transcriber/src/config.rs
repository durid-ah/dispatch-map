//! Environment-driven configuration for the radio transcriber service.

use std::fmt;
use std::path::PathBuf;
use std::str::FromStr;

use anyhow::{bail, Context, Result};

pub const DEFAULT_INGEST_MODE: &str = "file";
pub const DEFAULT_AUDIO_FILE_PATH: &str = "samples/sample_dispatch.mp3";
pub const DEFAULT_SIMULATE_REALTIME: bool = true;
pub const DEFAULT_SAMPLES_DIR: &str = "samples";
pub const DEFAULT_SAMPLE_RATE: u32 = 16_000;
pub const DEFAULT_CHANNELS: u16 = 1;
pub const DEFAULT_CHUNK_DURATION_MS: u32 = 100;

/// Source from which audio is ingested.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IngestMode {
    /// Pre-recorded local audio file (e.g. `.mp3`, `.wav`, `.m4a`).
    File,
}

impl FromStr for IngestMode {
    type Err = anyhow::Error;

    fn from_str(s: &str) -> Result<Self> {
        match s.trim().to_ascii_lowercase().as_str() {
            "file" => Ok(IngestMode::File),
            other => bail!("unsupported INGEST_MODE '{other}' (supported: file)"),
        }
    }
}

impl fmt::Display for IngestMode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            IngestMode::File => f.write_str("file"),
        }
    }
}

/// Runtime configuration resolved from environment variables.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Config {
    pub ingest_mode: IngestMode,
    pub audio_file_path: PathBuf,
    pub simulate_realtime: bool,
    pub samples_dir: PathBuf,
    pub sample_rate: u32,
    pub chunk_duration_ms: u32,
}

impl Config {
    /// Build a [`Config`] using `lookup` to resolve environment variables.
    ///
    /// Empty values are treated as unset.
    pub fn from_env<F>(lookup: F) -> Result<Self>
    where
        F: Fn(&str) -> Option<String>,
    {
        let get = |key: &str| lookup(key).filter(|v| !v.trim().is_empty());

        let ingest_mode = get("INGEST_MODE")
            .unwrap_or_else(|| DEFAULT_INGEST_MODE.to_string())
            .parse::<IngestMode>()?;

        let audio_file_path = PathBuf::from(
            get("AUDIO_FILE_PATH").unwrap_or_else(|| DEFAULT_AUDIO_FILE_PATH.to_string()),
        );

        let simulate_realtime = match get("SIMULATE_REALTIME") {
            Some(raw) => parse_bool(&raw).context("invalid SIMULATE_REALTIME")?,
            None => DEFAULT_SIMULATE_REALTIME,
        };

        let samples_dir =
            PathBuf::from(get("SAMPLES_DIR").unwrap_or_else(|| DEFAULT_SAMPLES_DIR.to_string()));

        let sample_rate = match get("SAMPLE_RATE") {
            Some(raw) => parse_positive_u32(&raw).context("invalid SAMPLE_RATE")?,
            None => DEFAULT_SAMPLE_RATE,
        };

        let chunk_duration_ms = match get("CHUNK_DURATION_MS") {
            Some(raw) => parse_positive_u32(&raw).context("invalid CHUNK_DURATION_MS")?,
            None => DEFAULT_CHUNK_DURATION_MS,
        };

        Ok(Config {
            ingest_mode,
            audio_file_path,
            simulate_realtime,
            samples_dir,
            sample_rate,
            chunk_duration_ms,
        })
    }
}

fn parse_bool(raw: &str) -> Result<bool> {
    match raw.trim().to_ascii_lowercase().as_str() {
        "true" | "1" | "yes" | "on" => Ok(true),
        "false" | "0" | "no" | "off" => Ok(false),
        other => bail!("expected a boolean (true/false/1/0/yes/no), got '{other}'"),
    }
}

fn parse_positive_u32(raw: &str) -> Result<u32> {
    let parsed = raw
        .trim()
        .parse::<u32>()
        .with_context(|| format!("expected a positive integer, got '{raw}'"))?;
    if parsed == 0 {
        bail!("expected a value greater than 0, got 0");
    }
    Ok(parsed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    fn env(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
        let map: HashMap<String, String> = pairs
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();
        move |k| map.get(k).cloned()
    }

    #[test]
    fn defaults_when_unset() {
        let cfg = Config::from_env(env(&[])).unwrap();
        assert_eq!(cfg.ingest_mode, IngestMode::File);
        assert_eq!(cfg.audio_file_path, PathBuf::from(DEFAULT_AUDIO_FILE_PATH));
        assert!(cfg.simulate_realtime);
        assert_eq!(cfg.samples_dir, PathBuf::from(DEFAULT_SAMPLES_DIR));
        assert_eq!(cfg.sample_rate, DEFAULT_SAMPLE_RATE);
        assert_eq!(cfg.chunk_duration_ms, DEFAULT_CHUNK_DURATION_MS);
    }

    #[test]
    fn empty_values_fall_back_to_defaults() {
        let cfg = Config::from_env(env(&[
            ("INGEST_MODE", ""),
            ("AUDIO_FILE_PATH", "  "),
            ("SAMPLE_RATE", ""),
            ("CHUNK_DURATION_MS", "  "),
        ]))
        .unwrap();
        assert_eq!(cfg.ingest_mode, IngestMode::File);
        assert_eq!(cfg.audio_file_path, PathBuf::from(DEFAULT_AUDIO_FILE_PATH));
        assert_eq!(cfg.sample_rate, DEFAULT_SAMPLE_RATE);
        assert_eq!(cfg.chunk_duration_ms, DEFAULT_CHUNK_DURATION_MS);
    }

    #[test]
    fn overrides_are_applied() {
        let cfg = Config::from_env(env(&[
            ("INGEST_MODE", "FILE"),
            ("AUDIO_FILE_PATH", "samples/other.wav"),
            ("SIMULATE_REALTIME", "false"),
            ("SAMPLES_DIR", "/app/samples"),
            ("SAMPLE_RATE", "8000"),
            ("CHUNK_DURATION_MS", "250"),
        ]))
        .unwrap();
        assert_eq!(cfg.ingest_mode, IngestMode::File);
        assert_eq!(cfg.audio_file_path, PathBuf::from("samples/other.wav"));
        assert!(!cfg.simulate_realtime);
        assert_eq!(cfg.samples_dir, PathBuf::from("/app/samples"));
        assert_eq!(cfg.sample_rate, 8_000);
        assert_eq!(cfg.chunk_duration_ms, 250);
    }

    #[test]
    fn parses_boolean_variants() {
        for (raw, expected) in [
            ("true", true),
            ("1", true),
            ("YES", true),
            ("on", true),
            ("false", false),
            ("0", false),
            ("No", false),
            ("off", false),
        ] {
            assert_eq!(parse_bool(raw).unwrap(), expected, "input {raw}");
        }
    }

    #[test]
    fn rejects_invalid_boolean() {
        let err = Config::from_env(env(&[("SIMULATE_REALTIME", "maybe")])).unwrap_err();
        assert!(format!("{err:#}").contains("SIMULATE_REALTIME"));
    }

    #[test]
    fn rejects_unsupported_ingest_mode() {
        let err = Config::from_env(env(&[("INGEST_MODE", "stream")])).unwrap_err();
        assert!(err.to_string().contains("unsupported INGEST_MODE"));
    }

    #[test]
    fn rejects_invalid_sample_rate() {
        for bad in ["0", "-16000", "fast"] {
            let err = Config::from_env(env(&[("SAMPLE_RATE", bad)])).unwrap_err();
            assert!(format!("{err:#}").contains("SAMPLE_RATE"), "input {bad}");
        }
    }

    #[test]
    fn rejects_invalid_chunk_duration() {
        for bad in ["0", "-50", "abc"] {
            let err = Config::from_env(env(&[("CHUNK_DURATION_MS", bad)])).unwrap_err();
            assert!(
                format!("{err:#}").contains("CHUNK_DURATION_MS"),
                "input {bad}"
            );
        }
    }
}
