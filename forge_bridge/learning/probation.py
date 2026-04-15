"""Probation tracking for synthesized MCP tools.

Wraps synthesized tool callables to track success/failure per tool.
When failures cross a configurable threshold, the tool is quarantined:
its source file is moved to ~/.forge-bridge/quarantined/ and the MCP
registration is removed.
"""
from __future__ import annotations

import functools
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

SYNTH_DIR = Path.home() / ".forge-bridge" / "synthesized"
QUARANTINE_DIR = Path.home() / ".forge-bridge" / "quarantined"


class ProbationTracker:
    """Track success/failure of synthesized tools and quarantine on breach."""

    def __init__(
        self,
        failure_threshold: int | None = None,
        synth_dir: Path = SYNTH_DIR,
        quarantine_dir: Path = QUARANTINE_DIR,
    ) -> None:
        self._threshold = (
            failure_threshold
            if failure_threshold is not None
            else int(os.environ.get("FORGE_PROBATION_THRESHOLD", "3"))
        )
        self._successes: dict[str, int] = {}
        self._failures: dict[str, int] = {}
        self._synth_dir = synth_dir
        self._quarantine_dir = quarantine_dir

    def record_success(self, tool_name: str) -> None:
        """Increment success counter for *tool_name*."""
        self._successes[tool_name] = self._successes.get(tool_name, 0) + 1

    def record_failure(self, tool_name: str) -> bool:
        """Increment failure counter. Return True if threshold is breached."""
        self._failures[tool_name] = self._failures.get(tool_name, 0) + 1
        return self._failures[tool_name] >= self._threshold

    def wrap(self, fn: Callable, tool_name: str, mcp: "FastMCP") -> Callable:
        """Return an async wrapper that tracks success/failure and quarantines on breach."""

        @functools.wraps(fn)
        async def _wrapper(*args, **kwargs):
            try:
                result = await fn(*args, **kwargs)
            except Exception:
                should_quarantine = self.record_failure(tool_name)
                if should_quarantine:
                    self.quarantine(tool_name, mcp)
                raise
            self.record_success(tool_name)
            return result

        return _wrapper

    def quarantine(self, tool_name: str, mcp: "FastMCP") -> None:
        """Move tool source to quarantine dir and remove MCP registration."""
        src = self._synth_dir / f"{tool_name}.py"
        if src.exists():
            self._quarantine_dir.mkdir(parents=True, exist_ok=True)
            dest = self._quarantine_dir / f"{tool_name}.py"
            if dest.exists():
                # Avoid overwriting a previously quarantined file — add timestamp suffix
                ts = int(time.time())
                dest = self._quarantine_dir / f"{tool_name}_{ts}.py"
            src.rename(dest)
            logger.warning("Quarantined tool %s -> %s", tool_name, dest)
        else:
            logger.warning("Quarantine: source file not found for %s", tool_name)
        try:
            mcp.remove_tool(tool_name)
        except Exception:
            pass

    def get_stats(self, tool_name: str) -> dict[str, int]:
        """Return success/failure counts for *tool_name*."""
        return {
            "successes": self._successes.get(tool_name, 0),
            "failures": self._failures.get(tool_name, 0),
        }
