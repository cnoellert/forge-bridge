"""Execution logging with AST normalization, JSONL persistence, and promotion counters.

Every bridge execution (when callback active) appends a JSONL record to
~/.forge-bridge/executions.jsonl. Replaying the JSONL on startup rebuilds
promotion counters without re-triggering synthesis.
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LOG_PATH = Path.home() / ".forge-bridge" / "executions.jsonl"


class _LiteralStripper(ast.NodeTransformer):
    """Strip string and numeric literals from AST so variants produce the same hash."""

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:
        if isinstance(node.value, str):
            return ast.Constant(value="STR")
        if isinstance(node.value, (int, float)):
            return ast.Constant(value=0)
        return node


def normalize_and_hash(code: str) -> tuple[str, str]:
    """Normalize Python code via AST (stripping literals) and return (normalized, sha256_hex).

    On SyntaxError, falls back to hashing the dedented/stripped raw code.
    """
    cleaned = textwrap.dedent(code).strip()
    try:
        tree = ast.parse(cleaned)
        tree = _LiteralStripper().visit(tree)
        normalized = ast.unparse(tree)
    except SyntaxError:
        normalized = cleaned

    h = hashlib.sha256(normalized.encode()).hexdigest()
    return normalized, h


class ExecutionLog:
    """Append-only JSONL execution log with AST normalization and promotion counters.

    Args:
        log_path: Path to the JSONL file. Defaults to ~/.forge-bridge/executions.jsonl.
        threshold: Number of identical (normalized) executions before promotion signal.
                   Overridden by FORGE_PROMOTION_THRESHOLD env var if set.
    """

    def __init__(self, log_path: Path = LOG_PATH, threshold: int = 3) -> None:
        self._path = log_path
        self._threshold = int(os.environ.get("FORGE_PROMOTION_THRESHOLD", threshold))
        self._counters: dict[str, int] = {}
        self._promoted: set[str] = set()
        self._code_by_hash: dict[str, str] = {}
        self._intent_by_hash: dict[str, Optional[str]] = {}
        self._replay()

    def _replay(self) -> None:
        """Replay existing JSONL to rebuild in-memory state."""
        if not self._path.exists():
            return
        try:
            with open(self._path, "r") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed JSONL line")
                        continue

                    code_hash = rec.get("code_hash")
                    if code_hash is None:
                        continue

                    # Promotion-only record
                    if rec.get("promoted") is True and "raw_code" not in rec:
                        self._promoted.add(code_hash)
                        continue

                    # Normal execution record
                    if "raw_code" in rec:
                        self._counters[code_hash] = self._counters.get(code_hash, 0) + 1
                        self._code_by_hash[code_hash] = rec["raw_code"]
                        self._intent_by_hash[code_hash] = rec.get("intent")
                        if rec.get("promoted") is True:
                            self._promoted.add(code_hash)
        except OSError:
            logger.warning("Could not read execution log at %s", self._path)

    def record(self, code: str, intent: Optional[str] = None) -> bool:
        """Record an execution. Returns True exactly once when promotion threshold is crossed.

        Args:
            code: The raw Python code that was executed.
            intent: Optional intent string for synthesis prompt enrichment.

        Returns:
            True if this execution crosses the promotion threshold (and not already promoted).
        """
        normalized, h = normalize_and_hash(code)
        self._code_by_hash[h] = code
        self._intent_by_hash[h] = intent
        self._counters[h] = self._counters.get(h, 0) + 1

        rec = {
            "code_hash": h,
            "raw_code": code,
            "intent": intent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "promoted": False,
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as fp:
            fp.write(json.dumps(rec) + "\n")
            fp.flush()

        if self._counters[h] >= self._threshold and h not in self._promoted:
            return True
        return False

    def mark_promoted(self, code_hash: str) -> None:
        """Mark a code hash as promoted, preventing future promotion signals."""
        self._promoted.add(code_hash)
        rec = {
            "code_hash": code_hash,
            "promoted": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as fp:
            fp.write(json.dumps(rec) + "\n")
            fp.flush()

    def get_code(self, code_hash: str) -> Optional[str]:
        """Return the raw code for a given hash, or None."""
        return self._code_by_hash.get(code_hash)

    def get_intent(self, code_hash: str) -> Optional[str]:
        """Return the intent string for a given hash, or None."""
        return self._intent_by_hash.get(code_hash)

    def get_count(self, code_hash: str) -> int:
        """Return the execution count for a given hash."""
        return self._counters.get(code_hash, 0)
