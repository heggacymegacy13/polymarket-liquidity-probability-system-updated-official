#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-.}"

echo "Starting Polymarket liquidity bot web dashboard..."
polymarket-bot web

