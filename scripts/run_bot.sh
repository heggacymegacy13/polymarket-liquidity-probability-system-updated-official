#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-.}"

CONFIG_DIR="${1:-./config}"

echo "Starting Polymarket liquidity bot (config_dir=${CONFIG_DIR})..."
polymarket-bot run-all --config-dir "${CONFIG_DIR}"

