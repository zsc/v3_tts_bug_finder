#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARTIFACTS_DIR="${ARTIFACTS_DIR:-artifacts_live}"
DB_PATH="${DB_PATH:-$ARTIFACTS_DIR/bugs.sqlite}"
REPORT_PATH="${REPORT_PATH:-$ARTIFACTS_DIR/report.html}"

CONCURRENCY="${CONCURRENCY:-2}"
TIME_LIMIT_SEC="${TIME_LIMIT_SEC:-1800}"        # 30 min per cycle
BUDGET_TOTAL="${BUDGET_TOTAL:-1000000}"         # large; usually time limit triggers first
BUDGET_ACCEPTED="${BUDGET_ACCEPTED:-1000000}"   # large; usually time limit triggers first
MAX_DEPTH="${MAX_DEPTH:-3}"
SLEEP_SEC="${SLEEP_SEC:-5}"

KIMI_TIMEOUT_SEC="${KIMI_TIMEOUT_SEC:-60}"
KIMI_MAX_PATTERNS="${KIMI_MAX_PATTERNS:-120}"

mkdir -p "$ARTIFACTS_DIR"

echo "Starting long-run..."
echo "  ARTIFACTS_DIR=$ARTIFACTS_DIR"
echo "  DB_PATH=$DB_PATH"
echo "  REPORT_PATH=$REPORT_PATH"
echo "  TIME_LIMIT_SEC=$TIME_LIMIT_SEC"
echo "  CONCURRENCY=$CONCURRENCY"

while true; do
  SEED="$(date +%s)"
  echo "Cycle seed=$SEED start=$(date)"

  PYTHONUNBUFFERED=1 python -m tts_bug_finder run \
    --db "$DB_PATH" \
    --artifacts "$ARTIFACTS_DIR" \
    --tts macos_say \
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
    --random-seed "$SEED"

  python -m tts_bug_finder report \
    --db "$DB_PATH" \
    --out "$REPORT_PATH" \
    --status accepted \
    --bundle-audio

  echo "Cycle done=$(date). Sleeping ${SLEEP_SEC}s..."
  sleep "$SLEEP_SEC"
done

