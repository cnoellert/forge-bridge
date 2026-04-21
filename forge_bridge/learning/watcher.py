"""Asyncio watcher for synthesized MCP tools.

Polls a directory for .py files, hot-loads them via importlib,
and registers/deregisters via the MCP registry.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json as _json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from forge_bridge.learning.manifest import manifest_verify, MANIFEST_PATH
from forge_bridge.learning.sanitize import _sanitize_tag, apply_size_budget

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.learning.probation import ProbationTracker

logger = logging.getLogger(__name__)

# Default: ~/.forge-bridge/synthesized/
# Matches LEARN-02 location pattern for runtime data
SYNTHESIZED_DIR = Path.home() / ".forge-bridge" / "synthesized"

_POLL_INTERVAL = 5.0  # seconds


async def watch_synthesized_tools(
    mcp: "FastMCP",
    synthesized_dir: Path | None = None,
    poll_interval: float = _POLL_INTERVAL,
    tracker: "ProbationTracker | None" = None,
) -> None:
    """Asyncio polling loop: hot-load new/changed synthesized tools."""
    synth_dir = synthesized_dir or SYNTHESIZED_DIR
    seen: dict[str, str] = {}  # stem -> sha256

    while True:
        await asyncio.sleep(poll_interval)
        try:
            _scan_once(mcp, seen, synth_dir, tracker=tracker)
        except Exception:
            logger.exception("Error in synthesized tool watcher")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_sidecar(py_path: Path) -> dict | None:
    """Load the sidecar envelope for a synthesized tool.

    Prefers `<stem>.sidecar.json` (v1.2+), falls back to legacy `<stem>.tags.json`
    (v1.1) for a grace window. Applies `_sanitize_tag` to every consumer-supplied
    tag at the READ boundary (PROV-03 defense-in-depth), then `apply_size_budget`
    to enforce <= 16 tags and <= 4 KB `meta`. Always prepends the literal
    `"synthesized"` tag so clients can filter (TS-02.1).

    Returns:
        dict of shape `{"tags": [...], "meta": {...}}` on success, or None if
        no sidecar exists OR the sidecar is malformed (non-JSON, non-dict).
    """
    sidecar_path = py_path.with_suffix(".sidecar.json")
    legacy_path = py_path.with_suffix(".tags.json")

    raw: dict | None = None
    if sidecar_path.exists():
        try:
            loaded = _json.loads(sidecar_path.read_text())
        except _json.JSONDecodeError:
            logger.warning("malformed .sidecar.json for %s — skipping provenance", py_path.stem)
            return None
        if not isinstance(loaded, dict):
            logger.warning(
                ".sidecar.json for %s is not a JSON object — skipping provenance",
                py_path.stem,
            )
            return None
        raw = {
            "tags": loaded.get("tags") or [],
            "meta": loaded.get("meta") or {},
        }
    elif legacy_path.exists():
        try:
            loaded = _json.loads(legacy_path.read_text())
        except _json.JSONDecodeError:
            logger.warning("malformed .tags.json for %s — skipping provenance", py_path.stem)
            return None
        if not isinstance(loaded, dict):
            logger.warning(
                ".tags.json for %s is not a JSON object — skipping provenance",
                py_path.stem,
            )
            return None
        raw = {
            "tags": loaded.get("tags") or [],
            "meta": {},  # legacy shape has no meta block
        }
    else:
        return None

    # Sanitize each consumer tag; drop rejections silently (already logged by sanitize)
    sanitized_tags: list[str] = []
    for t in raw["tags"]:
        cleaned = _sanitize_tag(t)
        if cleaned is not None:
            sanitized_tags.append(cleaned)

    # Prepend the literal "synthesized" filter tag (TS-02.1 — unconditional)
    tags_out = ["synthesized"] + sanitized_tags

    payload = {"tags": tags_out, "meta": dict(raw["meta"])}
    return apply_size_budget(payload)


def _scan_once(
    mcp: "FastMCP",
    seen: dict[str, str],
    synthesized_dir: Path,
    tracker: "ProbationTracker | None" = None,
    manifest_path: Path = MANIFEST_PATH,
) -> None:
    """Single scan pass — detect new, changed, and deleted files."""
    if not synthesized_dir.exists():
        return

    from forge_bridge.mcp.registry import register_tool

    current_stems: set[str] = set()
    for path in sorted(synthesized_dir.glob("*.py")):
        if path.stem.startswith("__"):
            continue
        stem = path.stem
        current_stems.add(stem)
        digest = _sha256(path)
        if seen.get(stem) == digest:
            continue
        # Manifest check — reject files not registered by the synthesizer
        if not manifest_verify(path, manifest_path=manifest_path):
            logger.warning(f"Skipping {stem}: not in manifest or hash mismatch")
            continue
        # New or changed file — (re)load
        if stem in seen:
            try:
                mcp.remove_tool(stem)
            except Exception:
                pass
        fn = _load_fn(path, stem)
        if fn is None:
            continue
        if tracker is not None:
            fn = tracker.wrap(fn, stem, mcp)
        try:
            provenance = _read_sidecar(path)
            register_tool(mcp, fn, name=stem, source="synthesized", provenance=provenance)
            seen[stem] = digest
            logger.info(f"Registered synthesized tool: {stem}")
        except ValueError as e:
            logger.warning(f"Skipped {stem}: {e}")

    # Remove tools whose files disappeared
    for stem in list(seen):
        if stem not in current_stems:
            try:
                mcp.remove_tool(stem)
                logger.info(f"Removed synthesized tool: {stem}")
            except Exception:
                pass
            del seen[stem]


def _load_fn(path: Path, stem: str):
    """Load a Python file and return the callable named `stem`."""
    spec = importlib.util.spec_from_file_location(stem, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        logger.exception(f"Failed to load {path}")
        return None
    fn = getattr(module, stem, None)
    if not callable(fn):
        logger.warning(f"{path}: no callable named {stem!r}")
        return None
    return fn
