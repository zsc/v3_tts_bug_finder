#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARTIFACTS_DIR="${ARTIFACTS_DIR:-artifacts_live}"
DB_PATH="${DB_PATH:-$ARTIFACTS_DIR/bugs.sqlite}"
REPORT_PATH="${REPORT_PATH:-$ARTIFACTS_DIR/report.html}"

TTS_KIND="${TTS_KIND:-macos_say}"
SEED_TAGS="${SEED_TAGS:-}"
ONLY_HANZI="${ONLY_HANZI:-0}"

CONCURRENCY="${CONCURRENCY:-2}"
TIME_LIMIT_SEC="${TIME_LIMIT_SEC:-1800}"        # 30 min per cycle
BUDGET_TOTAL="${BUDGET_TOTAL:-1000000}"         # large; usually time limit triggers first
BUDGET_ACCEPTED="${BUDGET_ACCEPTED:-1000000}"   # large; usually time limit triggers first
MAX_DEPTH="${MAX_DEPTH:-3}"
SLEEP_SEC="${SLEEP_SEC:-5}"

MIN_PLAUSIBILITY="${MIN_PLAUSIBILITY:-0.7}"
MIN_CER="${MIN_CER:-0.35}"
MIN_WER="${MIN_WER:-0.40}"
MIN_CRITICAL="${MIN_CRITICAL:-0.8}"

KIMI_TIMEOUT_SEC="${KIMI_TIMEOUT_SEC:-60}"
KIMI_MAX_PATTERNS="${KIMI_MAX_PATTERNS:-120}"

mkdir -p "$ARTIFACTS_DIR"

echo "Starting long-run..."
echo "  ARTIFACTS_DIR=$ARTIFACTS_DIR"
echo "  DB_PATH=$DB_PATH"
echo "  REPORT_PATH=$REPORT_PATH"
echo "  TTS_KIND=$TTS_KIND"
echo "  SEED_TAGS=$SEED_TAGS"
echo "  ONLY_HANZI=$ONLY_HANZI"
echo "  TIME_LIMIT_SEC=$TIME_LIMIT_SEC"
echo "  CONCURRENCY=$CONCURRENCY"

while true; do
  SEED="$(date +%s)"
  echo "Cycle seed=$SEED start=$(date)"

  RUN_ARGS=( \
    --db "$DB_PATH" \
    --artifacts "$ARTIFACTS_DIR" \
    --tts "$TTS_KIND" \
    --asr whisper_cli \
    --concurrency "$CONCURRENCY" \
    --time-limit-sec "$TIME_LIMIT_SEC" \
    --budget "$BUDGET_TOTAL" \
    --budget-accepted "$BUDGET_ACCEPTED" \
    --max-depth "$MAX_DEPTH" \
    --t2s \
    --bootstrap-from-accepted \
    --persist-seen \
    --kimi \
    --kimi-timeout-sec "$KIMI_TIMEOUT_SEC" \
    --kimi-max-patterns "$KIMI_MAX_PATTERNS" \
    --random-seed "$SEED" \
    --min-plausibility "$MIN_PLAUSIBILITY" \
    --min-cer "$MIN_CER" \
    --min-wer "$MIN_WER" \
    --min-critical "$MIN_CRITICAL" \
  )

  if [[ -n "${SEED_TAGS}" ]]; then
    RUN_ARGS+=( --seed-tags "$SEED_TAGS" )
  fi
  ONLY_HANZI_LC="$(echo "${ONLY_HANZI}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${ONLY_HANZI}" == "1" || "${ONLY_HANZI_LC}" == "true" ]]; then
    RUN_ARGS+=( --only-hanzi )
  fi

  PYTHONUNBUFFERED=1 python -m tts_bug_finder run \
    "${RUN_ARGS[@]}"

  python -m tts_bug_finder report \
    --db "$DB_PATH" \
    --out "$REPORT_PATH" \
    --status accepted \
    --bundle-audio

  echo "Cycle done=$(date). Sleeping ${SLEEP_SEC}s..."
  sleep "$SLEEP_SEC"
done
