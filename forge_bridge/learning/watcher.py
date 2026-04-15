"""Asyncio watcher for synthesized MCP tools.

Polls a directory for .py files, hot-loads them via importlib,
and registers/deregisters via the MCP registry.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Default: ~/.forge-bridge/synthesized/
# Matches LEARN-02 location pattern for runtime data
SYNTHESIZED_DIR = Path.home() / ".forge-bridge" / "synthesized"

_POLL_INTERVAL = 5.0  # seconds


async def watch_synthesized_tools(
    mcp: "FastMCP",
    synthesized_dir: Path | None = None,
    poll_interval: float = _POLL_INTERVAL,
) -> None:
    """Asyncio polling loop: hot-load new/changed synthesized tools."""
    synth_dir = synthesized_dir or SYNTHESIZED_DIR
    seen: dict[str, str] = {}  # stem -> sha256

    while True:
        await asyncio.sleep(poll_interval)
        try:
            _scan_once(mcp, seen, synth_dir)
        except Exception:
            logger.exception("Error in synthesized tool watcher")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scan_once(
    mcp: "FastMCP",
    seen: dict[str, str],
    synthesized_dir: Path,
) -> None:
    """Single scan pass — detect new, changed, and deleted files."""
    if not synthesized_dir.exists():
        return

    current_stems: set[str] = set()
    for path in sorted(synthesized_dir.glob("*.py")):
        if path.stem.startswith("__"):
            continue
        stem = path.stem
        current_stems.add(stem)
        digest = _sha256(path)
        if seen.get(stem) == digest:
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
        from forge_bridge.mcp.registry import register_tool
        try:
            register_tool(mcp, fn, name=stem, source="synthesized")
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
