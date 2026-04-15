"""Manifest for synthesized tool file-origin validation.

The synthesizer registers every file it creates in a JSON manifest at
~/.forge-bridge/synthesized/.manifest.json (filename -> sha256).
The watcher checks this manifest before loading any file, rejecting
files that are not in the manifest or whose hash does not match.

This prevents arbitrary code execution through files placed in the
synthesized directory by external actors.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default manifest location — co-located with synthesized tools.
MANIFEST_PATH = Path.home() / ".forge-bridge" / "synthesized" / ".manifest.json"


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_manifest(manifest_path: Path) -> dict[str, str]:
    """Read the manifest JSON file, returning an empty dict on any error."""
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text())
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not read manifest at %s", manifest_path)
        return {}


def _write_manifest(manifest_path: Path, data: dict[str, str]) -> None:
    """Write the manifest JSON file atomically (write + rename)."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(manifest_path)


def manifest_register(
    file_path: Path,
    manifest_path: Path = MANIFEST_PATH,
) -> None:
    """Register a synthesized file in the manifest.

    Called by the synthesizer after writing a new tool file.
    """
    data = _read_manifest(manifest_path)
    data[file_path.name] = _sha256_file(file_path)
    _write_manifest(manifest_path, data)


def manifest_verify(
    file_path: Path,
    manifest_path: Path = MANIFEST_PATH,
) -> bool:
    """Return True if the file is in the manifest and its hash matches.

    Called by the watcher before loading a synthesized tool.
    """
    data = _read_manifest(manifest_path)
    expected_hash = data.get(file_path.name)
    if expected_hash is None:
        return False
    actual_hash = _sha256_file(file_path)
    return actual_hash == expected_hash
