---
name: tts-bug-finder-polyphone
description: Run Chinese polyphone/古文-focused TTS→ASR fuzzing in this repo and generate a single-file HTML report (macOS say or Qwen3-TTS 0.6B → whisper).
metadata:
  short-description: Polyphone fuzz + HTML report
---

# TTS Bug Finder (polyphone / 古文)

Use this when you want **Chinese-only** inputs (no digits/Latin) that stress **多音字/古文** and you want a **single HTML** that shows:
WAV (playable) + GT text + ASR text side-by-side.

## One round (recommended flags)

macOS `say` → `whisper`:

```bash
PYTHONUNBUFFERED=1 python -m tts_bug_finder run \
  --db artifacts_polyphone_say/bugs.sqlite \
  --artifacts artifacts_polyphone_say \
  --tts macos_say \
  --asr whisper_cli \
  --concurrency 2 \
  --time-limit-sec 300 \
  --budget 1000000 \
  --budget-accepted 1000000 \
  --max-depth 4 \
  --t2s \
  --seed-tags polyphone,guwen \
  --only-hanzi \
  --min-cer 0.25 \
  --bootstrap-from-accepted \
  --persist-seen \
  --kimi

python -m tts_bug_finder report \
  --db artifacts_polyphone_say/bugs.sqlite \
  --out artifacts_polyphone_say/report.html \
  --status accepted \
  --bundle-audio
```

Qwen3-TTS 0.6B (`--tts qwen3_tts`) → `whisper` (slower; keep `--concurrency 1`):

```bash
PYTHONUNBUFFERED=1 python -m tts_bug_finder run \
  --db artifacts_polyphone_qwen3/bugs.sqlite \
  --artifacts artifacts_polyphone_qwen3 \
  --tts qwen3_tts \
  --asr whisper_cli \
  --concurrency 1 \
  --time-limit-sec 420 \
  --budget 1000000 \
  --budget-accepted 1000000 \
  --max-depth 3 \
  --t2s \
  --seed-tags polyphone,guwen \
  --only-hanzi \
  --min-cer 0.25 \
  --bootstrap-from-accepted \
  --persist-seen \
  --kimi

python -m tts_bug_finder report \
  --db artifacts_polyphone_qwen3/bugs.sqlite \
  --out artifacts_polyphone_qwen3/report.html \
  --status accepted \
  --bundle-audio
```

Merge both into one HTML:

```bash
python -m tts_bug_finder report \
  --db artifacts_polyphone_say/bugs.sqlite artifacts_polyphone_qwen3/bugs.sqlite \
  --out artifacts_polyphone/report.html \
  --status accepted \
  --bundle-audio
```

## Long run

This repo includes a loop script that runs `run` then regenerates the HTML report every cycle:

```bash
chmod +x scripts/long_run_macos_whisper.sh
TTS_KIND=macos_say SEED_TAGS=polyphone,guwen ONLY_HANZI=1 MIN_CER=0.25 ./scripts/long_run_macos_whisper.sh
```

Switch to Qwen3-TTS:

```bash
TTS_KIND=qwen3_tts CONCURRENCY=1 SEED_TAGS=polyphone,guwen ONLY_HANZI=1 MIN_CER=0.25 ./scripts/long_run_macos_whisper.sh
```

## Knobs / gotchas

- `--seed-tags polyphone,guwen`: restrict initial queue to those seed tags (e.g. only古文：`--seed-tags guwen`).
- `--only-hanzi`: filters out any queue text containing digits or Latin letters (helps isolate “纯汉字” cases).
- `--min-cer`: polyphone cases can be subtle; lower this (e.g. `0.25`) and rely on `--kimi` semantic check to reject “没变意思”的样本。
- `--t2s`: normalizes Traditional→Simplified (requires `opencc-python-reimplemented`; included in `pyproject.toml`).
- `qwen3_tts` deps: `torch`, `soundfile`, `qwen_tts` must be importable in the current Python env.
- `QWEN3_TTS_*` env vars:
  - `QWEN3_TTS_DEVICE` (`auto|mps|cuda|cpu`)
  - `QWEN3_TTS_SPEAKER` (default `Vivian`)
  - `QWEN3_TTS_MODEL` (default `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`)

