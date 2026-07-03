"""M2 slice 5 — shadow parity instrumentation over live read chains.

The graph-native execution engine (``composition/`` + ``graph/``) has been
offline-proven for the entire M2 arc with **zero production callers**. This
module is its first live production caller, in **shadow** mode: legacy
``run_chain_steps`` stays authoritative and byte-identical, and the graph path
runs opportunistically alongside it on real read traffic, emitting one
interpretable parity-evidence record per run.

Design contract (see ``.planning/M2-SLICE-5-SHADOW.md``):

* **Shadow is instrumentation, not a wrapper feature.** Everything operational
  lives here — the ``FORGE_BRIDGE_SHADOW_COMPARE`` flag, the compile+compare
  orchestration, the time-box, the outcome taxonomy, the ``comparison_mode``
  stamp, error/timeout capture, and the JSONL sink. The wrapper's only job is
  to run the authoritative path and hand this module the already-computed
  legacy body plus the in-memory tool-call records.
* **Replay is the intended mode.** Legacy runs ONCE; every tool call it makes
  is recorded in-memory by a transparent MCP proxy. The graph path replays
  those captured results (keyed by a skew-robust call-identity) instead of
  re-hitting real tools. This isolates the variable under test to the graph
  runtime — "does ``GraphExecutor`` execute the same plan correctly?" —
  answering the milestone question. Double-exec (re-validating against the live
  world) is a different question and is the documented fallback only, taken
  ONLY if records cannot be cleanly exposed. Here they can, so this module runs
  replay and never falls back.
* **A shadow failure can never regress a read.** Every path swallows to a
  recorded outcome; the authoritative body is already returned by the wrapper
  before this module is reached.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import inspect
import json
import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge_bridge.composition.boundary import MCPToolBoundary
from forge_bridge.composition.chain_compiler import (
    ChainCompileError,
    compile_chain_steps,
)
from forge_bridge.composition.compare import (
    admitted_records_for,
    compare_strategy_for,
    normalize_chain_body,
    normalize_graph_results,
)
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor

logger = logging.getLogger(__name__)

SHADOW_ENV = "FORGE_BRIDGE_SHADOW_COMPARE"
SHADOW_DIR_ENV = "FORGE_BRIDGE_SHADOW_DIR"
DEFAULT_SHADOW_DIR = Path.home() / ".forge-bridge" / "chain-compare"

#: Inline time-box for the opportunistic shadow run. A read that exceeds this
#: budget lands a ``shadow_timeout`` outcome — it never blocks the response.
SHADOW_BUDGET_S = 3.0

SCHEMA_VERSION = 1

#: The comparison mode stamped on every record. Replay is the intended mode
#: for this slice; ``double_exec`` is the documented fallback (never taken here
#: because records are cleanly exposed) — kept in the taxonomy so evidence can
#: never silently mix modes.
COMPARISON_MODES = frozenset({"replay", "double_exec"})

#: Outcome taxonomy. ``replay_miss`` is its OWN category — a robustly-keyed miss
#: is #153 value→kwarg divergence evidence, but it is first a corpus/keying
#: limitation, so it is never auto-labelled ``divergence``. ``shadow_error`` and
#: ``shadow_timeout`` are recorded outcomes: a swallowed or timed-out run must
#: land in the sink as itself, never vanish.
OUTCOMES = frozenset(
    {"match", "divergence", "replay_miss", "shadow_error", "shadow_timeout"}
)


def shadow_enabled() -> bool:
    """Return True when shadow compare is explicitly enabled (mirror capture)."""

    return os.environ.get(SHADOW_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


# --------------------------------------------------------------------------- #
# In-memory record hand-off — a transparent proxy over the real MCP.          #
# --------------------------------------------------------------------------- #


class ShadowRecorder:
    """Transparent MCP proxy that records ``(tool, args, raw_result)`` per call.

    Wraps the real MCP object the legacy path already uses and delegates every
    attribute. ``call_tool`` records the raw return (the FastMCP envelope the
    graph boundary also decodes) so replay can hand back a byte-identical
    object. This is a pure observer: it never mutates the result and never
    changes authoritative behavior.
    """

    def __init__(self, mcp: Any) -> None:
        self._mcp = mcp
        self.records: list[tuple[str, Any, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._mcp, name)

    async def call_tool(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        result = self._mcp.call_tool(tool_name, *args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        self.records.append(
            (tool_name, _arguments_from_call(args, kwargs), result)
        )
        return result


def wrap_mcp_for_shadow(mcp: Any) -> ShadowRecorder:
    """Wrap ``mcp`` in a transparent recording proxy for the authoritative run."""

    return ShadowRecorder(mcp)


class ShadowReplayMiss(Exception):
    """Raised inside replay when a graph-requested call has no captured record."""

    def __init__(self, tool_name: str, key: Any) -> None:
        super().__init__(f"no captured record for {tool_name!r} (key={key!r})")
        self.tool_name = tool_name


class _ReplayMCP:
    """Serve captured legacy results to the graph dispatch by match-key.

    Deliberately exposes NO ``list_tools`` — the boundary then passes the
    graph-computed arguments straight through (no ``normalize_tool_args``
    re-shaping), so the match-key sees the graph's own argument shape. Records
    for the same key are served in capture order (FIFO) to preserve
    multi-call-per-tool ordering within a linear chain.
    """

    def __init__(self, records: list[tuple[str, Any, Any]]) -> None:
        self._buckets: dict[tuple[str, str], list[Any]] = {}
        for tool_name, arguments, raw in records:
            self._buckets.setdefault(_match_key(tool_name, arguments), []).append(raw)
        self.misses: list[str] = []

    async def call_tool(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        arguments = _arguments_from_call(args, kwargs)
        key = _match_key(tool_name, arguments)
        bucket = self._buckets.get(key)
        if not bucket:
            self.misses.append(tool_name)
            raise ShadowReplayMiss(tool_name, key)
        return bucket.pop(0)


# --------------------------------------------------------------------------- #
# The skew-robust call-identity match-key (grounding-pass Q2).                 #
# --------------------------------------------------------------------------- #


def _match_key(tool_name: str, arguments: Any) -> tuple[str, str]:
    """Call-identity key robust to BENIGN argument-shape skew.

    The key must match logically-identical calls despite normalization skew
    between how legacy assembles arguments (token/JSON parsing in ``_step.py``)
    and how the graph assembles them (static config + #153 edge-sourced kwarg
    merge), while still DISTINGUISHING a genuinely-different or missing kwarg
    value (that difference is the #153 evidence a ``replay_miss`` carries).

    Benign skews collapsed by ``_canonical_args``:
      * key ordering (canonical JSON sorts keys);
      * explicit ``None`` vs an omitted kwarg (``None`` values dropped);
      * scalar-type skew from parsing — ``"5"`` vs ``5``, ``"true"`` vs
        ``True`` (numeric/bool-looking strings coerced);
      * surrounding whitespace on string scalars.

    A different or missing VALUE survives normalization → different key →
    interpretable miss. That is what makes "a robustly-keyed miss is #153
    divergence evidence" hold.
    """

    payload = json.dumps(_canonical_args(arguments), sort_keys=True, separators=(",", ":"))
    return (tool_name, payload)


def _canonical_args(value: Any) -> Any:
    if isinstance(value, Mapping):
        canon: dict[str, Any] = {}
        for key, item in value.items():
            if item is None:
                continue
            canon[str(key)] = _canonical_args(item)
        return canon
    if isinstance(value, (list, tuple)):
        return [_canonical_args(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return _coerce_scalar(value)
    return value


def _coerce_scalar(value: str) -> Any:
    text = value.strip()
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered == "null":
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        # Non-numeric string: keep it, but trimmed — surrounding whitespace is
        # benign call-identity skew, a value difference is not.
        return text


def _arguments_from_call(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    # Legacy calls ``mcp.call_tool(tool_name, params)`` (positional); the graph
    # boundary calls ``mcp.call_tool(operator_id, arguments=...)`` (keyword).
    # Handle both so the recorder and the replay server key on the same shape.
    if args:
        return args[0]
    if "arguments" in kwargs:
        return kwargs["arguments"]
    if "params" in kwargs:
        return kwargs["params"]
    return {}


# --------------------------------------------------------------------------- #
# The compare orchestration — time-boxed, never-raising, single emit point.   #
# --------------------------------------------------------------------------- #


async def shadow_compare(
    *,
    steps: list[str],
    legacy_body: dict[str, Any],
    recorder: ShadowRecorder,
    request_id: str,
    client_ip: str,
) -> None:
    """Opportunistically compare the graph path against the legacy body.

    Owns the time-box and the taxonomy; emits exactly one record. Never raises
    — a timeout, a graph explosion, or an un-normalizable body all land as a
    recorded outcome so "no divergence logged" can never conflate "ran and
    matched" with "never finished".
    """

    try:
        record = await asyncio.wait_for(
            _build_compare_record(
                steps=steps,
                legacy_body=legacy_body,
                records=recorder.records,
                request_id=request_id,
                client_ip=client_ip,
            ),
            timeout=SHADOW_BUDGET_S,
        )
    except asyncio.TimeoutError:
        record = _base_record(
            request_id, client_ip, steps, outcome="shadow_timeout"
        )
    except Exception as exc:  # never let a shadow failure escape
        record = _base_record(
            request_id,
            client_ip,
            steps,
            outcome="shadow_error",
            detail=_safe_detail(exc),
        )
    _emit_record(record)


async def _build_compare_record(
    *,
    steps: list[str],
    legacy_body: dict[str, Any],
    records: list[tuple[str, Any, Any]],
    request_id: str,
    client_ip: str,
) -> dict[str, Any]:
    """Compile → replay → normalize → classify. Returns one record dict."""

    try:
        graph = compile_chain_steps(steps)
    except ChainCompileError as exc:
        # The compiler could not represent this chain in admitted graph IR.
        # That is a corpus/keying limitation (a compiler gap), NOT a graph
        # runtime divergence — record it as a replay_miss at the compile stage.
        return _base_record(
            request_id,
            client_ip,
            steps,
            outcome="replay_miss",
            detail=f"compile: {_safe_detail(exc)}",
            stage="compile",
        )

    replay = _ReplayMCP(records)
    dispatch = UnifiedDispatch(mcp_boundary=MCPToolBoundary(mcp=replay))
    terminal_node_id = graph.nodes[-1].node_id if graph.nodes else ""
    operator_strategy = _operator_strategy(graph)

    try:
        graph_results = await GraphExecutor(dispatch.dispatch).run(graph)
    except ShadowReplayMiss as exc:
        return _base_record(
            request_id,
            client_ip,
            steps,
            outcome="replay_miss",
            detail=_safe_detail(exc),
            stage="replay",
            operator_strategy=operator_strategy,
            replay_misses=list(replay.misses),
        )

    legacy_snapshot = normalize_chain_body(legacy_body, expected_steps=len(steps))
    graph_snapshot = normalize_graph_results(
        graph_results, terminal_node_id=terminal_node_id
    )
    outcome = "match" if legacy_snapshot == graph_snapshot else "divergence"
    record = _base_record(
        request_id,
        client_ip,
        steps,
        outcome=outcome,
        stage="compare",
        operator_strategy=operator_strategy,
        replay_misses=list(replay.misses),
    )
    if outcome == "divergence":
        record["legacy_status_vector"] = list(legacy_snapshot.status_vector)
        record["graph_status_vector"] = list(graph_snapshot.status_vector)
    return record


def _operator_strategy(graph: Any) -> str | None:
    """The operator-idempotency class (compare.py), distinct from comparison_mode.

    ``compare_strategy_for`` reports whether the admitted operators would permit
    a double-exec re-validation. Recorded as evidence metadata; the shadow run
    itself is always ``comparison_mode="replay"`` this slice.
    """

    try:
        return compare_strategy_for(admitted_records_for(graph))
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Record shape + the module's own JSONL sink.                                 #
# --------------------------------------------------------------------------- #


def _base_record(
    request_id: str,
    client_ip: str,
    steps: list[str],
    *,
    outcome: str,
    detail: str | None = None,
    stage: str | None = None,
    operator_strategy: str | None = None,
    replay_misses: list[str] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": _captured_at(),
        "request_id": request_id,
        "client_ip": client_ip,
        "comparison_mode": "replay",
        "outcome": outcome,
        "step_count": len(steps),
        "chain_steps": list(steps),
    }
    if stage is not None:
        record["stage"] = stage
    if operator_strategy is not None:
        record["operator_strategy"] = operator_strategy
    if replay_misses:
        record["replay_misses"] = replay_misses
    if detail is not None:
        record["detail"] = detail
    return record


def _emit_record(record: dict[str, Any]) -> None:
    """Append one record to the shadow sink. Swallows all IO failures."""

    try:
        directory = _shadow_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"shadow-compare-{_dt.date.today().isoformat()}.jsonl"
        if not path.exists():
            path.write_text(_header_line(), encoding="utf-8")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except Exception:
        logger.debug("shadow sink write failed", exc_info=True)


def _header_line() -> str:
    header = {
        "_header": True,
        "schema_version": SCHEMA_VERSION,
        "kind": "shadow-compare",
        "created_at": _captured_at(),
    }
    return json.dumps(header, sort_keys=True) + "\n"


def _shadow_dir() -> Path:
    configured = os.environ.get(SHADOW_DIR_ENV)
    return Path(configured).expanduser() if configured else DEFAULT_SHADOW_DIR


def _captured_at() -> str:
    return _dt.datetime.now(tz=_dt.UTC).isoformat()


def _safe_detail(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}"
    return text[:500]


__all__ = [
    "SHADOW_BUDGET_S",
    "SHADOW_ENV",
    "ShadowRecorder",
    "ShadowReplayMiss",
    "shadow_compare",
    "shadow_enabled",
    "wrap_mcp_for_shadow",
]
