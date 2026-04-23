#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/vboxuser/public_prize_contest_radar"
export PYTHONPATH="$ROOT/src"
python3 -m contest_radar.cli run-once --db "$ROOT/data/contest_radar.sqlite3" "$@"
