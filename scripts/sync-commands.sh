#!/usr/bin/env bash
set -euo pipefail

# Wrapper to sync the 'emails' command files across providers
# Usage: scripts/sync-commands.sh [--dry-run]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CONFIG_PATH="$ROOT_DIR/commands_sync.config.yaml"
SCRIPT_PATH="$ROOT_DIR/scripts/sync_commands.py"

DRY_RUN=""
if [[ "${1-}" == "--dry-run" ]]; then
	DRY_RUN="--dry-run"
fi

python3 "$SCRIPT_PATH" events --config "$CONFIG_PATH" $DRY_RUN
python3 "$SCRIPT_PATH" focus --config "$CONFIG_PATH" $DRY_RUN
