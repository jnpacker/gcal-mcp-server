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

# Derive command names from the YAML config and loop through them
readarray -t COMMANDS < <(python3 - "$CONFIG_PATH" <<'PY'
import sys, yaml, pathlib
data = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
for entry in data.get("commands", []):
	name = entry.get("name")
	if name:
		print(name)
PY
)

for cmd in "${COMMANDS[@]}"; do
	python3 "$SCRIPT_PATH" "$cmd" --config "$CONFIG_PATH" $DRY_RUN
done