#!/usr/bin/env bash
set -euo pipefail

# Wrapper to sync command files across providers
# Usage: scripts/sync-commands.sh <provider> [--dry-run]
#   provider: claude, gemini, or cursor

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
CONFIG_PATH="$ROOT_DIR/commands_sync.config.yaml"
SCRIPT_PATH="$ROOT_DIR/scripts/sync_commands.py"

if [[ $# -lt 1 ]]; then
	echo "Error: provider argument required" >&2
	echo "Usage: $0 <provider> [--dry-run]" >&2
	echo "  provider: claude, gemini, or cursor" >&2
	exit 1
fi

PROVIDER="$1"
shift

# Validate provider
if [[ "$PROVIDER" != "claude" && "$PROVIDER" != "gemini" && "$PROVIDER" != "cursor" ]]; then
	echo "Error: invalid provider '$PROVIDER'" >&2
	echo "Valid providers: claude, gemini, cursor" >&2
	exit 1
fi

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
	python3 "$SCRIPT_PATH" "$cmd" "$PROVIDER" --config "$CONFIG_PATH" $DRY_RUN
done