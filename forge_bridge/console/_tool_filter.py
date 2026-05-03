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


# PR19 / PR19.1 — deterministic lexical normalization map.
#
# Purpose: collapse equivalent surface forms (plurals, verb synonyms) to a
# single canonical token so the PR18 token-complete subset check fires on
# natural-language phrasings ("show flame libraries" → flame_list_libraries).
#
# CONTRACT — read before editing:
#   1. Dictionary lookup ONLY. No stemming, fuzzy matching, edit distance,
#      partial matching, embeddings, or similarity scoring.
#   2. SYMMETRIC APPLICATION. Every place that produces a token-set for
#      matching MUST funnel through `normalize_token`. The single chokepoint
#      is `_pr14_tokens` below — both message text and tool names go
#      through it, so canonicalization is guaranteed identical on both
#      sides of the subset check.
#   3. CANONICAL IDENTITY ENTRIES. Each canonical form is also a key
#      mapping to itself (e.g. "library" → "library"). Functionally these
#      are no-ops (`dict.get(k, k)` already does identity for unmapped
#      keys), but they document the closed canonical vocabulary
#      explicitly and act as a regression guard: if a future edit accidentally
#      changes the canonical target for, say, "libraries", the corresponding
#      identity row makes the asymmetry visible at a glance.
NORMALIZATION_MAP: dict[str, str] = {
    # Canonical identity (closed vocabulary — prevents asymmetry drift).
    "library": "library",
    "project": "project",
    "shot": "shot",
    "version": "version",
    "role": "role",
    "list": "list",
    # Plurals → singular.
    "libraries": "library",
    "projects": "project",
    "shots": "shot",
    "versions": "version",
    "roles": "role",
    # Verb normalization → canonical "list".
    "listing": "list",
    "show": "list",
    "get": "list",
    "fetch": "list",
}


def normalize_token(token: str) -> str:
    """Map a single lowercase token to its canonical form.

    Deterministic dict lookup; tokens not in the map pass through unchanged
    (so the closed canonical vocabulary above does not affect the long tail
    of tool-specific words like ``flame``, ``ping``, ``forge``, etc.).
    """
    return NORMALIZATION_MAP.get(token, token)


def _pr14_tokens(text: str) -> set[str]:
    """Tokenize ``text`` and apply ``normalize_token`` to every token.

    Single chokepoint — both message text and tool names are tokenized
    through this function so the canonicalization rules apply symmetrically
    on both sides of the PR18 subset check (PR19.1 invariant).
    """
    return {normalize_token(t) for t in _PR14_TOKEN_RE.findall(text.lower())}


def filter_tools_by_message(
    tools: list[Any],
    message: str,
    *,
    max_tools: int = PR14_MAX_TOOLS,
) -> list[Any]:
    """PR14 — narrow the tool list passed to the LLM by simple keyword match.

    Pre-filter only. No embeddings, no ranking, no scoring. A tool survives if:
      * its lowercase name occurs as a substring of the message (EXACT, PR17), OR
      * every token of its name appears in the message tokens (EXACT,
        token-complete, PR18 — covers ``"list flame libraries"`` →
        ``flame_list_libraries``), OR
      * any of its name's word-tokens (split on non-alphanumerics) appear in
        the message tokens (other match — picks up category matches like
        ``flame`` / ``forge`` and verb matches like ``ping``).

    PR19: tokens (both message and tool name) are passed through
    ``NORMALIZATION_MAP`` before any comparison. Plurals collapse to their
    singular form and a small fixed set of "list"-equivalent verbs
    (``show``/``get``/``fetch``/``listing``) collapse to ``list``. Strict dict
    lookup — no fuzzy/partial/stemming.

    If nothing matches, the full ``tools`` list is returned unchanged so we
    never lose capability.

    PR17: exact-name matches are NEVER dropped by the cap. They go to the
    front of the result (in original input order) and other token matches
    fill remaining slots. If exact matches alone exceed ``max_tools``, the
    return is exact matches only (truncated to the cap, still input order).
    Otherwise the cap behaves as before — first N in input order, no sort,
    no rank.
    """
    if not isinstance(message, str) or not message:
        return list(tools)
    msg_lower = message.lower()
    msg_tokens = _pr14_tokens(message)
    if not msg_tokens:
        return list(tools)

    # PR17: split into two buckets so exact matches survive the cap regardless
    # of where they sit in input order.
    # PR18: a tool is also "exact" if every token of its name appears in the
    # message tokens — bridges the natural-language ↔ underscore-form gap
    # ("list flame libraries" → flame_list_libraries) without changing rank
    # or score. Strict subset only — partial overlap stays in the other bucket.
    exact_matches: list[Any] = []
    other_matches: list[Any] = []
    for t in tools:
        name = (getattr(t, "name", "") or "").lower()
        if not name:
            continue
        if name in msg_lower:
            exact_matches.append(t)
            continue
        name_tokens = _pr14_tokens(name)
        if name_tokens and name_tokens.issubset(msg_tokens):
            exact_matches.append(t)
            continue
        if name_tokens & msg_tokens:
            other_matches.append(t)

    if not exact_matches and not other_matches:
        return list(tools)

    # Exact matches always survive — even if they alone exceed the cap.
    if len(exact_matches) >= max_tools:
        return exact_matches[:max_tools]
    remaining = max_tools - len(exact_matches)
    return exact_matches + other_matches[:remaining]


# ---------------------------------------------------------------------------
# PR21 — deterministic disambiguation for multi-tool matches
# ---------------------------------------------------------------------------
#
# After PR14/17/18 message-filtering returns the candidate set, PR21 attempts
# a second deterministic narrowing step BEFORE the LLM sees the list. The
# rules are intentionally narrow — no scoring, no fuzzy matching, no ML.
#
# Rule 1 — EXACT TOKEN COVERAGE. Keep only tools whose normalized name-tokens
# overlap the message-tokens by the maximum count among the candidates. If
# every candidate ties at the same overlap, all survive Rule 1.
#
# Rule 2 — DOMAIN PRIORITY. When the message contains BOTH tokens of a
# priority pair, prefer tools that contain the WINNER token over tools
# that contain only the LOSER token. The brief specifies one rule:
# ``version > project`` (versions are more specific than projects).
# Strict pairwise — no transitive chains, no scores.
#
# Stop conditions:
#   - max overlap is 0 → no signal, leave the candidate set untouched.
#   - input is already 0 or 1 tools → return as-is.
#   - rules cannot reduce to a single survivor → return the surviving set;
#     the chat handler then falls back to the LLM.
#
# This module is pure (no I/O, no asyncio, no MCP types beyond duck-typed
# `.name`). The chat handler is the single caller — see PR21 wiring in
# forge_bridge/console/handlers.py:chat_handler.

# Pairwise domain priorities. WINNER outranks LOSER when BOTH tokens are
# present in the message. Closed list — extending requires explicit spec.
_PR21_DOMAIN_PRIORITIES: tuple[tuple[str, str], ...] = (
    ("version", "project"),  # versions are more specific than projects
)


def deterministic_narrow(tools: list[Any], message: str) -> list[Any]:
    """PR21 — narrow a multi-tool match deterministically before LLM dispatch.

    Returns the (possibly reduced) candidate set. Callers should treat a
    return value of length 1 as a signal to force-execute via the PR20
    short-circuit; any other length means "still ambiguous, hand to LLM".

    See module-level PR21 comment block above for the rule contract.
    """
    if len(tools) <= 1:
        return list(tools)
    if not isinstance(message, str) or not message:
        return list(tools)

    msg_tokens = _pr14_tokens(message)
    if not msg_tokens:
        return list(tools)

    # Rule 1 — max token-overlap. Compute overlap counts up-front, then
    # keep only tools that hit the maximum.
    scored: list[tuple[Any, int]] = []
    for t in tools:
        name = (getattr(t, "name", "") or "").lower()
        if not name:
            scored.append((t, 0))
            continue
        name_tokens = _pr14_tokens(name)
        scored.append((t, len(name_tokens & msg_tokens)))

    max_overlap = max(c for _, c in scored)
    if max_overlap == 0:
        # No signal — every candidate is a fallback. Don't narrow.
        return list(tools)

    survivors = [t for t, c in scored if c == max_overlap]
    if len(survivors) <= 1:
        return survivors

    # Rule 2 — domain priority. For each pair where BOTH tokens are in the
    # message, drop survivors that have the LOSER token but not the WINNER.
    for winner, loser in _PR21_DOMAIN_PRIORITIES:
        if winner in msg_tokens and loser in msg_tokens:
            winners = [
                t for t in survivors
                if winner in _pr14_tokens(getattr(t, "name", "") or "")
            ]
            if winners:
                survivors = winners
                if len(survivors) == 1:
                    return survivors

    return survivors
