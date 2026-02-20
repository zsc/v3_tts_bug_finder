# TTS Bug Finder (CLI demo)

This repo implements the core pipeline described in `AGENTS.md` as a **command-line** demo first:
`text → TTS → ASR → alignment/metrics → scoring → dedupe → SQLite`.

## Quickstart

Run with dummy adapters (offline):

```bash
python -m tts_bug_finder run --budget 300 --concurrency 8
python -m tts_bug_finder export --out artifacts/exports/accepted.jsonl
python -m tts_bug_finder report --db artifacts/bugs.sqlite --out artifacts/report.html --status accepted --bundle-audio
```

On macOS you can try system `say` (TTS) if available:

```bash
python -m tts_bug_finder run --tts macos_say --asr dummy --budget 100
```

Real chain (macOS `say` → `whisper` CLI):

```bash
python -m tts_bug_finder run --tts macos_say --asr whisper_cli --budget 120 --budget-accepted 20 --concurrency 2
python -m tts_bug_finder report --db artifacts/bugs.sqlite --out artifacts/report.html --status accepted --bundle-audio
```

Long-run script (macOS `say` → `whisper` + `kimi` judging):

```bash
chmod +x scripts/long_run_macos_whisper.sh
./scripts/long_run_macos_whisper.sh
```

Notes:
- `--kimi` uses the external `kimi` CLI to (1) filter out semantic-equivalent cases and (2) judge novelty vs previously accepted patterns.
- `--t2s` attempts Traditional→Simplified normalization via `opencc` if installed. If not installed, it safely falls back to no conversion.

## Artifacts

Outputs go to:

```
artifacts/
  audio/
  bugs.sqlite
  exports/
  logs/
```
