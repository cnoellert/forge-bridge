"""forge_bridge.console._tool_filter — backend-aware tool-list scoping for chat (D-01).

Phase 16.1 (FB-D gap closure). The chat handler invokes
`filter_tools_by_reachable_backends()` between `mcp.list_tools()` and
`complete_with_tools(tools=...)` to drop tools whose runtime backend
is unreachable on this host. Without this filter the LLM picks tools
that would hang at execution time (Bug C — 49-tool full-registry hang
on a bare deploy host with no Flame backend, see Phase 16 VERIFICATION.md).

BACKEND CLASSIFICATION (NOT prefix-based — see in-process exception list):

1. Flame HTTP bridge (:9999) — TCP-probed.
   Tools whose impl calls `forge_bridge.bridge.execute_*()`:
     - All `flame_*` tools (29 tools registered in mcp/registry.py)
     - Most `forge_*` tools (20 builtin tools that import from
       forge_bridge.tools.* — project, timeline, batch, publish, utility,
       switch_grade, reconform). They are name-prefixed `forge_` because
       they read pipeline state, but their RUNTIME backend is Flame.
   When :9999 is unreachable → these are dropped.

2. In-process forge_* tools — ALWAYS reachable.
   SEVEN tools registered from
   `forge_bridge/console/resources.py:register_console_resources`,
   backed by `console_read_api` / `session_factory` (local SQLAlchemy +
   ManifestService).  Hardcoded in `_IN_PROCESS_FORGE_TOOLS` below.
   KEEP IN SYNC with register_console_resources additions — Test 1
   (`test_in_process_tool_set_matches_resources_module`) is the
   regression guard.

3. synth_* tools — ALWAYS reachable (synthesizer runs in-process).

Cache: 5-second monotonic cache keyed by backend identity. Single asyncio.Lock
(async-native — the critical section awaits the probe). Single probe
per backend per cache window even under concurrent chat requests.

Security note (T-16.1-01): _BACKENDS is hardcoded to 127.0.0.1:9999.
Host/port are NOT user-controllable — no SSRF surface.

DoS mitigation (T-16.1-05): 5s monotonic-clock cache + asyncio.Lock serialization
→ at most 1 probe per 5s per backend regardless of request rate. Probe timeout
capped at 1.5s.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

# PR14 — message-based tool pre-filter: cap and tokenizer.
# Pre-filter only. No embeddings, no ranking, no scoring.
PR14_MAX_TOOLS = 8
_PR14_TOKEN_RE = re.compile(r"[a-z0-9]+")

# ---------------------------------------------------------------------------
# Per-tool routing classification (the planner audit — see plan 16.1-01)
# ---------------------------------------------------------------------------

# Tools that run IN-PROCESS in the forge-bridge process itself.
# KEEP IN SYNC with `forge_bridge/console/resources.py:register_console_resources`.
# Test `test_in_process_tool_set_matches_resources_module` enforces this.
# SEVEN names — verified 2026-04-27 against resources.py @mcp.tool registrations.
_IN_PROCESS_FORGE_TOOLS: frozenset[str] = frozenset({
    "forge_manifest_read",
    "forge_tools_read",
    "forge_list_staged",
    "forge_get_staged",
    "forge_approve_staged",
    "forge_reject_staged",
    "forge_staged_pending_read",
})

# Backends whose reachability is probed each chat request (cached 5s).
# (backend_label, host, port)
_BACKENDS: tuple[tuple[str, str, int], ...] = (
    ("flame_bridge", "127.0.0.1", 9999),
)

_PROBE_TIMEOUT_SEC: float = 1.5
_PROBE_CACHE_TTL_SEC: float = 5.0

# Module state — guarded by `_cache_lock`.
# backend_label -> (reachable: bool, expires_at_monotonic: float)
_cache: dict[str, tuple[bool, float]] = {}
_cache_lock = asyncio.Lock()


async def _probe_backend(host: str, port: int) -> bool:
    """TCP-connect probe — True iff something accepts a TCP handshake within timeout.

    Async-native (unlike `read_api._check_ws_server`'s blocking socket) because
    the chat handler's hot path cannot afford to block the event loop for 1.5s.
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=_PROBE_TIMEOUT_SEC,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001 — best-effort close, never propagate
            pass
        return True
    except (OSError, asyncio.TimeoutError) as exc:
        logger.debug(
            "tool_filter probe failed: %s:%d %s",
            host, port, type(exc).__name__,
        )
        return False
    except Exception as exc:  # noqa: BLE001 — never let the probe break chat
        logger.warning(
            "tool_filter probe unexpected: %s:%d %s",
            host, port, type(exc).__name__,
            exc_info=True,
        )
        return False


async def _get_backend_reachability() -> dict[str, bool]:
    """Return {backend_label: reachable_bool} for every probed backend, cached 5s."""
    now = time.monotonic()
    result: dict[str, bool] = {}
    async with _cache_lock:
        for label, host, port in _BACKENDS:
            cached = _cache.get(label)
            if cached is not None and now < cached[1]:
                result[label] = cached[0]
                continue
            ok = await _probe_backend(host, port)
            _cache[label] = (ok, now + _PROBE_CACHE_TTL_SEC)
            result[label] = ok
    return result


def _is_in_process_tool(name: str) -> bool:
    """True iff the tool runs in the bridge process and needs no remote backend."""
    if name.startswith("synth_"):
        return True
    if name in _IN_PROCESS_FORGE_TOOLS:
        return True
    return False


async def filter_tools_by_reachable_backends(tools: list[Any]) -> list[Any]:
    """Return the subset of `tools` whose runtime backend is reachable.

    `tools` is `list[mcp.types.Tool]` (Pydantic; has `.name: str`).
    In-process tools (`synth_*` + `_IN_PROCESS_FORGE_TOOLS`) always pass through.
    Everything else with `flame_` or `forge_` prefix requires the Flame bridge :9999.
    Unknown-prefix tools (defense-in-depth) are dropped — registry only allows
    the three known prefixes anyway.
    """
    reachability = await _get_backend_reachability()
    flame_ok = reachability.get("flame_bridge", False)
    survivors: list[Any] = []
    for t in tools:
        name = t.name
        if _is_in_process_tool(name):
            survivors.append(t)
            continue
        if name.startswith("flame_") or name.startswith("forge_"):
            if flame_ok:
                survivors.append(t)
            continue
        # Unknown prefix — drop. (Registry _validate_name should reject these
        # at registration time; this is belt-and-suspenders.)
        logger.debug("tool_filter dropping unknown-prefix tool: %s", name)
    return survivors


def _reset_for_tests() -> None:
    """Test affordance — clear the cache. Mirrors `_rate_limit._reset_for_tests`."""
    _cache.clear()


# ---------------------------------------------------------------------------
# PR14 — message-based tool pre-filter
# ---------------------------------------------------------------------------


def _pr14_tokens(text: str) -> set[str]:
    return set(_PR14_TOKEN_RE.findall(text.lower()))


def filter_tools_by_message(
    tools: list[Any],
    message: str,
    *,
    max_tools: int = PR14_MAX_TOOLS,
) -> list[Any]:
    """PR14 — narrow the tool list passed to the LLM by simple keyword match.

    Pre-filter only. No embeddings, no ranking, no scoring. A tool survives if:
      * its lowercase name occurs as a substring of the message, OR
      * any of its name's word-tokens (split on non-alphanumerics) appear in
        the message tokens — this picks up category matches like ``flame``
        or ``forge`` and verb matches like ``ping``.

    If nothing matches, the full ``tools`` list is returned unchanged so we
    never lose capability. When more than ``max_tools`` survive, the first N
    in input order are kept (no sort, no rank).
    """
    if not isinstance(message, str) or not message:
        return list(tools)
    msg_lower = message.lower()
    msg_tokens = _pr14_tokens(message)
    if not msg_tokens:
        return list(tools)

    selected: list[Any] = []
    for t in tools:
        name = (getattr(t, "name", "") or "").lower()
        if not name:
            continue
        if name in msg_lower:
            selected.append(t)
            continue
        if _pr14_tokens(name) & msg_tokens:
            selected.append(t)
            continue

    if not selected:
        return list(tools)
    return selected[:max_tools]
