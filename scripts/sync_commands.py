#!/usr/bin/env python3

import argparse
import hashlib
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
	import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
	print("Missing dependency: pyyaml. Install with: pip install pyyaml", file=sys.stderr)
	raise


@dataclass
class ProviderSpec:
	name: str
	path: Path
	header: str
	footer: str


@dataclass
class CommandSpec:
	name: str
	providers: Dict[str, 'ProviderSpec']


CONFIG_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "commands_sync.config.yaml"


def read_text(path: Path) -> str:
	return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, content: str) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(content, encoding="utf-8")


def get_body_from_provider_content(provider: str, content: str, header: str, footer: str) -> str:
	# Strip exact header prefix if present
	if header:
		if content.startswith(header):
			content = content[len(header):]
		else:
			# Allow a leading newline after header
			if content.startswith(header.rstrip("\n") + "\n"):
				content = content[len(header.rstrip("\n")) + 1:]
	# Strip footer suffix if present
	if footer:
		if content.endswith(footer):
			content = content[: -len(footer)]
		else:
			# Allow a trailing newline before footer
			if content.endswith("\n" + footer.lstrip("\n")):
				content = content[: -(len(footer.lstrip("\n")) + 1)]
	return content


def strip_known_wrappers(content: str, providers: Dict[str, 'ProviderSpec']) -> str:
	"""Remove any known provider-specific header/footer wrappers from content.

	This normalizes a file's contents down to just the prompt body, even if the
	body was previously contaminated with another provider's header/footer.
	"""
	normalized = content
	for pspec in providers.values():
		if not normalized:
			break
		normalized = get_body_from_provider_content(pspec.name, normalized, pspec.header, pspec.footer)
	return normalized


def assemble_provider_content(header: str, body: str, footer: str) -> str:
	return f"{header}{body}{footer}"


def file_signature(path: Path) -> Tuple[float, str]:
	if not path.exists():
		return 0.0, hashlib.sha256(b"").hexdigest()
	stat = path.stat()
	mtime = stat.st_mtime
	content = read_text(path)
	digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
	return mtime, digest


def load_config(path: Path) -> Tuple[Dict[str, 'CommandSpec'], str]:
	data = yaml.safe_load(path.read_text(encoding="utf-8"))
	commands: Dict[str, CommandSpec] = {}
	for entry in data.get("commands", []):
		name = entry["name"]
		providers: Dict[str, ProviderSpec] = {}
		for provider_name, spec in entry["files"].items():
			providers[provider_name] = ProviderSpec(
				name=provider_name,
				path=(path.parent / spec["path"]).resolve(),
				header=spec.get("header", ""),
				footer=spec.get("footer", ""),
			)
		commands[name] = CommandSpec(name=name, providers=providers)
	primary_provider = str(data.get("primary_provider", "auto"))
	return commands, primary_provider


class SyncError(Exception):
	pass


def detect_primary(spec: CommandSpec, primary_policy: str) -> str:
	if primary_policy and primary_policy != "auto":
		if primary_policy not in spec.providers:
			raise SyncError(f"Configured primary_provider '{primary_policy}' not found for command {spec.name}")
		return primary_policy
	# Auto: pick most recently modified existing file among providers
	candidate: Optional[Tuple[str, float]] = None
	for pname, pspec in spec.providers.items():
		if pspec.path.exists():
			mtime = pspec.path.stat().st_mtime
			if candidate is None or mtime > candidate[1]:
				candidate = (pname, mtime)
	if candidate is None:
		# none exists yet; default to claude as canonical
		return "claude"
	return candidate[0]


def sync_command(spec: CommandSpec, primary_policy: str, dry_run: bool = False) -> None:
	# Gather provider contents and metadata
	provider_contents: Dict[str, str] = {}
	provider_bodies: Dict[str, str] = {}
	mtimes: Dict[str, float] = {}

	for pname, pspec in spec.providers.items():
		content = read_text(pspec.path)
		provider_contents[pname] = content
		mtimes[pname] = pspec.path.stat().st_mtime if pspec.path.exists() else 0.0
		# Normalize by stripping any known provider wrappers to avoid cross-contamination
		provider_bodies[pname] = strip_known_wrappers(content, spec.providers)

	# Determine primary
	primary = detect_primary(spec, primary_policy)

	# Determine if any non-primary was edited since it was last synced from primary body
	primary_body = provider_bodies.get(primary, "")

	# If non-primary body differs from primary body and file is newer than primary, raise
	conflicting: Dict[str, Tuple[float, float]] = {}
	for pname in spec.providers.keys():
		if pname == primary:
			continue
		if provider_bodies.get(pname, "") and provider_bodies[pname] != primary_body:
			if mtimes[pname] > mtimes.get(primary, 0.0):
				conflicting[pname] = (mtimes[pname], mtimes.get(primary, 0.0))

	if conflicting:
		details = ", ".join(sorted(conflicting.keys()))
		raise SyncError(
			f"Sync conflict: {details} modified independently after primary '{primary}'. "
			f"Primary is '{primary}'. Revert others or set primary_provider in config."
		)

	# Propagate primary body to others
	for pname, pspec in spec.providers.items():
		desired = assemble_provider_content(pspec.header, primary_body, pspec.footer)
		if provider_contents.get(pname, "") != desired:
			if dry_run:
				print(f"[DRY-RUN] Would update {pspec.path}")
			else:
				write_text(pspec.path, desired)
				os.utime(pspec.path, (time.time(), time.time()))


def main() -> int:
	parser = argparse.ArgumentParser(description="Sync command prompt files across providers")
	parser.add_argument("command", help="Command core name, e.g. 'emails'")
	parser.add_argument("--config", default=str(CONFIG_DEFAULT_PATH), help="Path to config YAML")
	parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
	args = parser.parse_args()

	config_path = Path(args.config).resolve()
	if not config_path.exists():
		print(f"Config not found: {config_path}", file=sys.stderr)
		return 2

	commands, primary_policy = load_config(config_path)
	if args.command not in commands:
		print(f"Command '{args.command}' not defined in {config_path}", file=sys.stderr)
		return 2

	try:
		sync_command(commands[args.command], primary_policy, dry_run=args.dry_run)
	except SyncError as exc:
		print(str(exc), file=sys.stderr)
		return 1

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
