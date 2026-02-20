# TTS Bug Finder (CLI demo)

This repo implements the core pipeline described in `AGENTS.md` as a **command-line** demo first:
`text → TTS → ASR → alignment/metrics → scoring → dedupe → SQLite`.

## Quickstart

Run with dummy adapters (offline):

```bash
python -m tts_bug_finder run --budget 300 --concurrency 8
python -m tts_bug_finder export --out artifacts/exports/accepted.jsonl
```

On macOS you can try system `say` (TTS) if available:

```bash
python -m tts_bug_finder run --tts macos_say --asr dummy --budget 100
```

## Artifacts

Outputs go to:

```
artifacts/
  audio/
  bugs.sqlite
  exports/
  logs/
```

