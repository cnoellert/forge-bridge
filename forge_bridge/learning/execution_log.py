"""Execution logging with AST normalization, JSONL persistence, and promotion counters.

Every bridge execution (when callback active) appends a JSONL record to
~/.forge-bridge/executions.jsonl. Replaying the JSONL on startup rebuilds
promotion counters without re-triggering synthesis.
"""
from __future__ import annotations

import ast
import asyncio
import collections
import dataclasses
import fcntl
import hashlib
import inspect
import json
import logging
import os
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Optional, Union

logger = logging.getLogger(__name__)

LOG_PATH = Path.home() / ".forge-bridge" / "executions.jsonl"
_DEFAULT_MAX_SNAPSHOT = 10_000


# ---------------------------------------------------------------------------
# Storage callback contract (LRN-02)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionRecord:
    """Payload delivered to storage callbacks after every ExecutionLog.record() write.

    Mirrors the JSONL row written by ExecutionLog.record() — same field names,
    same types. NOT every JSONL row is an ExecutionRecord: ExecutionLog.mark_promoted()
    writes a separate partial row of shape {code_hash, promoted, timestamp} for
    promotion events. Readers that replay the JSONL must tolerate both row shapes.

    Frozen so consumer code cannot mutate state shared between the log write and
    the callback fire.
    """

    code_hash: str
    raw_code: str
    intent: Optional[str]
    timestamp: str
    promoted: bool


StorageCallback = Callable[[ExecutionRecord], Union[None, Awaitable[None]]]


def _log_callback_exception(task: "asyncio.Task") -> None:
    """done_callback for fire-and-forget async storage callbacks.

    Logs exceptions raised inside the async callback without surfacing them
    to the caller of ExecutionLog.record().
    """
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        return
    if exc is not None:
        logger.warning(
            "storage_callback raised — execution log unaffected",
            exc_info=(type(exc), exc, exc.__traceback__),
        )


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
        # Bounded in-memory snapshot deque (D-06).
        # Sized via FORGE_EXEC_SNAPSHOT_MAX env; default 10_000.
        # Replay (below) will re-fill the deque from JSONL, maxlen-truncating to newest.
        maxlen = int(os.environ.get("FORGE_EXEC_SNAPSHOT_MAX", _DEFAULT_MAX_SNAPSHOT))
        self._records: "collections.deque[ExecutionRecord]" = collections.deque(maxlen=maxlen)
        # Promotion-only JSONL rows (mark_promoted) populate this set; snapshot()
        # joins it against deque records to project promoted=True (D-09, P9-3).
        self._promoted_hashes: set[str] = set()
        self._replay()
        self._storage_callback: Optional[StorageCallback] = None
        self._storage_callback_is_async: bool = False

    def set_storage_callback(self, fn: Optional[StorageCallback]) -> None:
        """Register (or clear with None) a single best-effort storage callback.

        The JSONL log is source-of-truth; the callback is a best-effort mirror.
        A failing callback is logged at WARNING level and never disrupts the
        JSONL append.

        The callback may be sync (returns None) or async (returns Awaitable[None]).
        Dispatch mode is detected once here via inspect.iscoroutinefunction and
        cached — per-record dispatch does not re-inspect.

        An async callback requires record() to be called from a running event loop.
        When no loop is present at dispatch time, asyncio.ensure_future raises
        RuntimeError which is caught and logged as a warning.

        Args:
            fn: Callable taking an ExecutionRecord and returning None or an
                Awaitable[None]. Pass None to clear a previously-set callback.
        """
        if fn is None:
            self._storage_callback = None
            self._storage_callback_is_async = False
            return
        self._storage_callback = fn
        self._storage_callback_is_async = inspect.iscoroutinefunction(fn)

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
                        self._promoted_hashes.add(code_hash)  # D-09 for snapshot projection
                        continue

                    # Normal execution record
                    if "raw_code" in rec:
                        self._counters[code_hash] = self._counters.get(code_hash, 0) + 1
                        self._code_by_hash[code_hash] = rec["raw_code"]
                        self._intent_by_hash[code_hash] = rec.get("intent")
                        if rec.get("promoted") is True:
                            self._promoted.add(code_hash)
                            self._promoted_hashes.add(code_hash)  # D-09 projection
                        replayed = ExecutionRecord(
                            code_hash=code_hash,
                            raw_code=rec["raw_code"],
                            intent=rec.get("intent"),
                            timestamp=rec.get("timestamp", ""),
                            promoted=bool(rec.get("promoted", False)),
                        )
                        self._records.append(replayed)  # newest-wins via deque maxlen
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

        record = ExecutionRecord(
            code_hash=h,
            raw_code=code,
            intent=intent,
            timestamp=datetime.now(timezone.utc).isoformat(),
            promoted=False,
        )

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as fp:
            fcntl.flock(fp, fcntl.LOCK_EX)
            try:
                fp.write(json.dumps(asdict(record)) + "\n")
                fp.flush()
            finally:
                fcntl.flock(fp, fcntl.LOCK_UN)

        # Fire storage callback AFTER the JSONL flush completes (best-effort mirror).
        if self._storage_callback is not None:
            if self._storage_callback_is_async:
                try:
                    task = asyncio.ensure_future(self._storage_callback(record))
                    task.add_done_callback(_log_callback_exception)
                except RuntimeError:
                    logger.warning(
                        "storage_callback scheduled outside event loop — skipped"
                    )
            else:
                try:
                    self._storage_callback(record)
                except Exception:
                    logger.warning(
                        "storage_callback raised — execution log unaffected",
                        exc_info=True,
                    )

        # D-06: append to the snapshot deque AFTER JSONL flush + callback fire.
        # Ordering is the contract — the deque mirrors canonical write order.
        self._records.append(record)

        if self._counters[h] >= self._threshold and h not in self._promoted:
            return True
        return False

    def mark_promoted(self, code_hash: str) -> None:
        """Mark a code hash as promoted, preventing future promotion signals."""
        self._promoted.add(code_hash)
        self._promoted_hashes.add(code_hash)  # D-09: snapshot projection source
        rec = {
            "code_hash": code_hash,
            "promoted": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as fp:
            fcntl.flock(fp, fcntl.LOCK_EX)
            try:
                fp.write(json.dumps(rec) + "\n")
                fp.flush()
            finally:
                fcntl.flock(fp, fcntl.LOCK_UN)

    def get_code(self, code_hash: str) -> Optional[str]:
        """Return the raw code for a given hash, or None."""
        return self._code_by_hash.get(code_hash)

    def get_intent(self, code_hash: str) -> Optional[str]:
        """Return the intent string for a given hash, or None."""
        return self._intent_by_hash.get(code_hash)

    def get_count(self, code_hash: str) -> int:
        """Return the execution count for a given hash."""
        return self._counters.get(code_hash, 0)

    def snapshot(
        self,
        limit: int = 50,
        offset: int = 0,
        since: Optional[datetime] = None,
        promoted_only: bool = False,
        code_hash: Optional[str] = None,  # prefix match per D-03
    ) -> tuple[list[ExecutionRecord], int]:
        """Return (filtered_records, total_before_pagination) from the bounded deque.

        Reads deque only (D-07). Never touches JSONL — the deque is the hot-path
        query surface; disk is canonical for full history.

        Ordering: newest-first (reverse deque iteration). Default limit is 50,
        matches D-05; the handler clamps to 500 max BEFORE calling this method.

        Filters (all AND-combined):
          since: ISO8601-parsed timestamp; records older than this are dropped.
          promoted_only: include only records whose code_hash is in
                         self._promoted_hashes (D-09 projection — not the frozen
                         ExecutionRecord.promoted field, which may be stale).
          code_hash: prefix match (D-03) — rec.code_hash.startswith(code_hash).

        NOTE (W-01): the `tool` filter (e.g. `?tool=synth_*`) is DEFERRED to
        v1.4. Supporting it requires either a `ManifestService`-owned
        `code_hash`->name reverse map (with careful concurrency semantics while
        the watcher mutates the manifest) or an additive field on
        `ExecutionRecord`. Both changes are larger than D-12's "decide now"
        threshold. In v1.3 the /api/v1/execs route handler REJECTS `?tool=...`
        with a 400 `{"error": {"code": "not_implemented"}}` response — so
        `snapshot()` never sees the kwarg and does not need to accept it.

        Returns a fresh list so callers may iterate without worrying about deque
        mutation during iteration.
        """
        filtered: list[ExecutionRecord] = []
        for rec in reversed(self._records):  # newest-first
            if since is not None:
                try:
                    rec_ts = datetime.fromisoformat(rec.timestamp)
                except ValueError:
                    continue  # unparseable timestamp: skip, don't break (clock skew tolerance)
                if rec_ts < since:
                    continue
            if promoted_only and rec.code_hash not in self._promoted_hashes:
                continue
            if code_hash is not None and not rec.code_hash.startswith(code_hash):
                continue
            # D-09 projection: mirror current promoted state onto a frozen clone
            if rec.code_hash in self._promoted_hashes and not rec.promoted:
                rec = dataclasses.replace(rec, promoted=True)
            filtered.append(rec)

        total = len(filtered)
        page = filtered[offset : offset + limit]
        return page, total
