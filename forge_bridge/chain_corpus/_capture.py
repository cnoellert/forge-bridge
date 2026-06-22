"""Dormant chain compile/trace capture.

The capture is gated by ``FORGE_BRIDGE_CHAIN_CORPUS_CAPTURE`` and is designed
to be observational: every capture failure is swallowed, while the request's
normal execution result is left untouched.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import inspect
import json
import os
from pathlib import Path
from typing import Any

from forge_bridge.chain_corpus._schema import (
    SCHEMA_VERSION,
    validate_compile_record,
    validate_trace_record,
)

CAPTURE_ENV = "FORGE_BRIDGE_CHAIN_CORPUS_CAPTURE"
CAPTURE_DIR_ENV = "FORGE_BRIDGE_CHAIN_CORPUS_DIR"
DEFAULT_CAPTURE_DIR = Path.home() / ".forge-bridge" / "chain-corpus"


def capture_enabled() -> bool:
    """Return True when chain-corpus capture is explicitly enabled."""

    value = os.environ.get(CAPTURE_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def canonical_hash(value: Any) -> str:
    """Return the full sha256 of canonical JSON for ``value``."""

    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def variety_tags_for(
    chain_steps: list[str],
    *,
    regime: str,
    salvage_applied: bool,
) -> list[str]:
    """Derive replay-variety tags from facts already present in the chain."""

    tokens = " ".join(chain_steps).lower()
    tags: set[str] = {f"regime:{regime}"}
    if len(chain_steps) >= 3:
        tags.add("multi_step")
    if not chain_steps:
        tags.add("empty_degenerate")
    if salvage_applied:
        tags.add("bug_d_salvage")
    if regime == "clarification_needed":
        tags.add("clarification_reentry")
    if regime == "compiled_mutating_preview":
        tags.add("mutating_preview")

    token_tags = {
        "commit": "commit",
        "filter(": "filter",
        "foreach(": "foreach",
        "if(": "if_gate",
        "collect": "collect",
        "select": "select",
    }
    for needle, tag in token_tags.items():
        if needle in tokens:
            tags.add(tag)
    if {"filter", "foreach", "collect"}.issubset(tags):
        tags.add("op_mix_filter_foreach_collect")
    return sorted(tags)


class ChainTraceRecorder:
    """Per-request trace wrapper and collision accumulator."""

    def __init__(self, *, request_id: str, mcp: Any, enabled: bool) -> None:
        self.request_id = request_id
        self.enabled = enabled
        self._mcp = mcp
        self.mcp = _TracingMCP(mcp, self) if enabled else mcp
        self.records: list[dict[str, Any]] = []
        self._seen: dict[tuple[str, str], str] = {}
        self._collision = False

    @property
    def replayable(self) -> bool:
        return not self._collision

    @property
    def has_collision(self) -> bool:
        return self._collision

    def record_call(self, tool_name: str, arguments: Any, raw_result: Any) -> None:
        if not self.enabled:
            return
        try:
            result = _capture_result(raw_result)
            args_hash = canonical_hash(arguments or {})
            result_hash = canonical_hash(result)
            key = (tool_name, args_hash)
            prior = self._seen.get(key)
            if prior is not None and prior != result_hash:
                self._collision = True
            else:
                self._seen[key] = result_hash
            record = {
                "schema_version": SCHEMA_VERSION,
                "captured_at": _captured_at(),
                "request_id": self.request_id,
                "tool_name": tool_name,
                "args_hash": args_hash,
                "result_hash": result_hash,
                "result": result,
            }
            emit_trace_record(record)
            self.records.append(record)
        except Exception:
            return


class _TracingMCP:
    def __init__(self, mcp: Any, recorder: ChainTraceRecorder) -> None:
        self._mcp = mcp
        self._recorder = recorder

    def __getattr__(self, name: str) -> Any:
        return getattr(self._mcp, name)

    async def call_tool(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        result = self._mcp.call_tool(tool_name, *args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        arguments = _arguments_from_call(args, kwargs)
        self._recorder.record_call(tool_name, arguments, result)
        return result


def start_trace_capture(*, request_id: str, mcp: Any) -> ChainTraceRecorder:
    """Return the request trace recorder and possibly-wrapped MCP object."""

    return ChainTraceRecorder(
        request_id=request_id,
        mcp=mcp,
        enabled=capture_enabled(),
    )


def emit_compile_record(
    *,
    request_id: str,
    regime: str,
    chain_steps: list[str],
    salvage_applied: bool,
    salvage_reason: str | None,
    replayable: bool,
    source: str = "captured",
) -> None:
    """Persist one compile record if capture is enabled."""

    if not capture_enabled():
        return
    try:
        record = {
            "schema_version": SCHEMA_VERSION,
            "captured_at": _captured_at(),
            "request_id": request_id,
            "regime": regime,
            "chain_steps": list(chain_steps),
            "salvage_applied": salvage_applied,
            "salvage_reason": salvage_reason,
            "variety_tags": variety_tags_for(
                list(chain_steps),
                regime=regime,
                salvage_applied=salvage_applied,
            ),
            "source": source,
            "replayable": replayable,
        }
        _append_record("chain-compile", validate_compile_record(record))
    except Exception:
        return


def emit_trace_record(record: dict[str, Any]) -> None:
    """Persist one tool trace record if capture is enabled."""

    if not capture_enabled():
        return
    _append_record("chain-trace", validate_trace_record(record))


def _arguments_from_call(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    if args:
        return args[0]
    if "arguments" in kwargs:
        return kwargs["arguments"]
    if "params" in kwargs:
        return kwargs["params"]
    return {}


def _capture_result(raw_result: Any) -> Any:
    try:
        from forge_bridge.composition.boundary import _extract_payload

        return _json_safe(_extract_payload(raw_result))
    except Exception:
        return _json_safe(raw_result)


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, sort_keys=True)
        return value
    except (TypeError, ValueError):
        return repr(value)


def _append_record(prefix: str, record: dict[str, Any]) -> None:
    directory = _capture_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{prefix}-{_dt.date.today().isoformat()}.jsonl"
    if not path.exists():
        path.write_text(_header_line(prefix), encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _header_line(prefix: str) -> str:
    header = {
        "_header": True,
        "schema_version": SCHEMA_VERSION,
        "kind": prefix,
        "created_at": _captured_at(),
    }
    return json.dumps(header, sort_keys=True) + "\n"


def _capture_dir() -> Path:
    configured = os.environ.get(CAPTURE_DIR_ENV)
    return Path(configured).expanduser() if configured else DEFAULT_CAPTURE_DIR


def _captured_at() -> str:
    return _dt.datetime.now(tz=_dt.UTC).isoformat()
