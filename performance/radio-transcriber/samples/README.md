# Radio Transcriber Samples

Put pre-recorded dispatch radio audio here for local ingestion.

- Supported formats: `.mp3`, `.wav`, `.m4a` (anything FFmpeg can decode).
- Default file: `sample_dispatch.mp3`. Point `AUDIO_FILE_PATH` at a different file to change it.
- Docker Compose mounts this folder read-only at `/app/samples`.
- Audio files are git-ignored, so don't commit recordings. Only this README and `.gitkeep` are tracked.
