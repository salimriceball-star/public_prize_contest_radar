#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/vboxuser/public_prize_contest_radar"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
TOP="${CONTEST_RADAR_TOP:-10}"
MIN_SCORE="${CONTEST_RADAR_MIN_SCORE:-40}"
NOTIFY="${CONTEST_RADAR_NOTIFY:-1}"
NEW_ONLY="${CONTEST_RADAR_NEW_ONLY:-1}"
SAVE_OUTPUT="${CONTEST_RADAR_SAVE_OUTPUT:-daily-contest-update-${STAMP}.txt}"
DB_PATH="${CONTEST_RADAR_DB:-}"

ARGS=(run-once --top "$TOP" --public-only --min-score "$MIN_SCORE" --save-output "$SAVE_OUTPUT")
if [ -n "$DB_PATH" ]; then
  ARGS+=(--db "$DB_PATH")
fi
if [ "$NEW_ONLY" != "0" ]; then
  ARGS+=(--new-only)
fi
if [ "$NOTIFY" != "0" ]; then
  ARGS+=(--notify)
fi

exec "$ROOT/scripts/run_radar.sh" "${ARGS[@]}"
