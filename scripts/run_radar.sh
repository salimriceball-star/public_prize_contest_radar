#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/vboxuser/public_prize_contest_radar"
if [ -f "$ROOT/.local/runtime.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.local/runtime.env"
  set +a
fi
export PYTHONPATH="$ROOT/src:$ROOT/.local/site-packages:${PYTHONPATH:-}"
python3 -m contest_radar.cli "$@"
