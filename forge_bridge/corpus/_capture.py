"""forge_bridge.corpus._capture — Layer 1 divergence corpus capture.

Capture is emitted after arbitration decisions are finalized and
must not structurally participate in the arbitration pipeline.

PR 3 carrier sentences (verbatim, load-bearing — see
``A.5.3.2-PR3-SPEC.md`` §0):

Phase-level architectural intent (from the framing):

  Preserve Layer 1 truthfulness while introducing persistence.

  Once persistence exists, future interpretation layers begin
  inheriting authority from it automatically. That is why PR 3 is
  dangerous: not because it writes data, but because it creates
  institutional memory.

Orthogonal truth surfaces — input-parameter discipline (§5):

  The registered tool set is deployment identity, not runtime
  topology. Candidate sets are topology-sensitive operational
  subsets and are therefore insufficient inputs for
  deployment-stable identity hashing.

  The builder receives all three as explicit inputs. The builder
  does not discover them.

Atomic-append discipline — persistence-layer architectural
property (§6.5):

  Corpus existence implies at least one truthful persisted
  capture.

  The architecture should not introduce corruption windows larger
  than the platform already imposes.

This module implements the runtime probe (env-var-gated) and the
test-fixture path that emits Layer 1 records per the A.5.3.2
instrument contract. The contract's structural invariants
(``A.5.3.2-INSTRUMENT-CONTRACT.md`` §2.2) are enforced here:

  - I-1: append-only writer; never mutates existing records.
  - I-2: records carry observations only; no outcome labels.
  - I-3: this module is imported by daemon code paths but only
         performs disk writes — no LLM calls, no comparator logic.

PR 3 makes three additional invariants operational:

  - I-5 (append-only executable). The writer opens files only with
        ``mode="a"``; no rewrite/mutation/update/merge/overwrite
        paths exist. See ``A.5.3.2-PR3-SPEC.md`` §7.
  - I-6 (failure-invisibility). Every persistence-failure mode is
        caught and logged at WARNING; no exception ever propagates
        from ``emit_divergence_capture``. Observation failure
        cannot become arbitration failure. See spec §8.
  - §6.5 (atomic-append at the line boundary). Each emission
        performs exactly one ``file.write(...)`` call. Header +
        first record are bundled into one call when creating a new
        file. The writer never attempts partial-record recovery,
        in-place repair, continuation writes, or seek-and-
        reconstruct. If a write fails, the record is considered
        lost. Recovery semantics belong outside Layer 1
        persistence.

See ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §3 for the canonical record
shape and ``A.5.3.2-GATE-1-SPEC.md`` §5 for the capture-invocation
contract this module implements.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, Optional

from forge_bridge.corpus._identity import (
    daemon_git_sha,
    narrower_version_hash,
    registered_tools_snapshot_hash,
)
from forge_bridge.corpus._schema import (
    SCHEMA_VERSION,
    validate_capture_record,
)
from forge_bridge.corpus._topology import snapshot_topology

logger = logging.getLogger(__name__)

# Per A.5.3.2-GATE-1-SPEC.md §6.
_ENV_VAR = "FORGE_BRIDGE_DIVERGENCE_CAPTURE"
_CORPUS_DIR_ENV_VAR = "FORGE_BRIDGE_CORPUS_DIR"
_TRUTHY = frozenset({"1", "true", "yes"})
_FALSY = frozenset({"", "0", "false", "no"})

# Module state for one-time WARNING per unique invalid env-var value.
#
# Process-local by design. The warning is a UX nicety — surface typo'd
# env values without log spam — not a correctness mechanism. The set
# is shared across all callers within the process; in the daemon
# (single-threaded asyncio) this is safe without a lock because
# ``divergence_capture_enabled`` does not ``await`` between the
# membership check and the ``add()``. It is NOT safe for multi-
# threaded use, but the daemon does not use threads in the
# arbitration path.
#
# Test isolation: tests that exercise the invalid-value warning
# behavior must request the ``clean_warning_state`` fixture from
# ``tests/corpus/conftest.py``. Without it, prior tests in the same
# pytest process leave the set populated and the "warns once per
# unique value" assertion becomes order-dependent.
_warned_invalid_values: set[str] = set()


def divergence_capture_enabled() -> bool:
    """True iff the env-var gate is set to a recognized truthy value.

    Read at call time (not cached) so daemon restart is the supported
    way to flip the gate. Invalid values are treated as disabled and
    log a one-time WARNING per unique invalid value seen — avoids
    silent enablement on typo'd values without spamming the log.

    See ``A.5.3.2-GATE-1-SPEC.md`` §6 for the accepted value list.
    """
    raw = os.environ.get(_ENV_VAR, "")
    norm = raw.strip().lower()

    if norm in _TRUTHY:
        return True
    if norm in _FALSY:
        return False

    if raw not in _warned_invalid_values:
        _warned_invalid_values.add(raw)
        logger.warning(
            "%s=%r is not a recognized truthy/falsy value; "
            "treating as disabled. Accepted truthy: %s. "
            "Accepted falsy: %s.",
            _ENV_VAR, raw,
            sorted(_TRUTHY),
            sorted(v for v in _FALSY if v),
        )
    return False


# ── Dispatch-provenance substrate (PR 7 §4.2.2 + §4.2.3) ───────────────────
#
# Inert at PR 7 Step 3 landing. The contextvar default is ``None``; the
# resolution path inside ``emit_divergence_capture`` (Step 5) treats
# ``None`` as the runtime default (persisted ``source="runtime"``,
# ``fixture_id`` absent). The substrate is activated by
# ``seed_dispatch_scope`` (Step 4) and consumed by the resolution path
# (Step 5). PR 8's seed driver interacts via ``seed_dispatch_scope``
# only; direct construction of ``_DispatchContext`` is structurally
# prohibited (private name + frozen instance).
#
# See ``A.5.3.2-PR7-SPEC.md`` §4.2.2–§4.2.3 for the binding contract.


@dataclass(frozen=True)
class _DispatchContext:
    """Dispatch-provenance payload carried via contextvar.

    Private (underscore prefix) and frozen. Constructed exclusively
    by ``seed_dispatch_scope`` (lands at Step 4); PR 8's seed driver
    interacts with the scope helper, never with this dataclass
    directly. Frozen to prevent accidental mutation across the yield
    point of the context manager.

    ``fixture_id`` is ``str``, not ``str | None``. The framing-time
    correction (PR 7 framing §3 + 2026-05-08 EVE passoff §3.3) is
    binding: making it optional broadens the contract for "future
    flexibility" prematurely. If a use case for an absent
    ``fixture_id`` appears, that becomes a framing decision.
    """

    source: Literal["runtime", "seed"]
    fixture_id: str


_dispatch_context: ContextVar[Optional[_DispatchContext]] = ContextVar(
    "forge_bridge.corpus._capture._dispatch_context",
    default=None,
)


@contextmanager
def seed_dispatch_scope(*, fixture_id: str) -> Iterator[None]:
    """Activate seed-dispatch provenance for the current scope.

    Within this context, capture emissions persist
    ``source="seed"`` and the supplied ``fixture_id`` regardless
    of the call-site ``source`` literal. Outside this context,
    the contextvar default (``None``) yields the runtime
    behavior unchanged.

    The context manager yields no public value. ``ContextVar``
    token handling is implementation-internal. If future
    nested-scope introspection becomes a concrete need, that is
    an explicit framing/spec expansion event — never
    accidentally-carried-forward latent API surface (see
    ``A.5.3.2-PR7-FRAMING.md`` §5.2 +
    ``A.5.3.2-PR7-SPEC.md`` §5.2).

    Args:
        fixture_id: REQUIRED keyword-only. The seed fixture
            identifier the dispatch is operating on. Stored in
            the contextvar payload and persisted on every
            observation emission that occurs while the scope is
            active. The ``*`` keyword-only marker matches the
            ``forge_bridge.corpus`` helper convention and
            prevents future contributors from adding positional
            arguments accidentally.

    Yields:
        ``None``. The caller drives the dispatch through the
        arbitration pipeline; this scope only sets provenance.
    """
    token = _dispatch_context.set(
        _DispatchContext(source="seed", fixture_id=fixture_id)
    )
    try:
        yield
    finally:
        _dispatch_context.reset(token)


# ── Builder ────────────────────────────────────────────────────────────────


def _now_iso_ms() -> str:
    """Current UTC time as ISO 8601 with millisecond precision and Z
    suffix. Format example: ``"2026-05-07T14:32:11.123Z"``.

    Per spec §12 decision 5: millisecond precision is sufficient for
    arbitration timing analytics; sub-millisecond precision is not
    operationally useful and would falsely suggest finer
    measurement than the underlying narrower latency provides.
    """
    now = datetime.now(tz=timezone.utc)
    iso = now.isoformat(timespec="milliseconds")
    return iso.replace("+00:00", "Z")


def _new_uuid() -> str:
    """Fresh uuid4 as string. Indirection exists so tests can inject
    deterministic uuids via ``_build_capture_record(new_uuid=...)``."""
    return str(uuid.uuid4())


def _tool_names(tools: list[Any]) -> list[str]:
    """Extract tool names from a list of tool objects, dicts, or
    strings. Used to convert candidate sets and narrower decision
    lists into the schema's required shape (lists of tool name
    strings) per contract §3.

    Production callers pass FastMCP ``Tool`` objects (with ``.name``
    attribute). Tests may pass raw strings or dicts; both are
    handled.
    """
    names: list[str] = []
    for t in tools:
        if isinstance(t, str):
            names.append(t)
            continue
        n = getattr(t, "name", None)
        if n is None and isinstance(t, dict):
            n = t.get("name")
        names.append(str(n) if n is not None else "")
    return names


def _build_capture_record(
    *,
    prompt: str,
    registered_tools: list[Any],
    candidate_set_post_reachability: list[Any],
    candidate_set_post_pr14: list[Any],
    narrower_decision: list[Any],
    pr20_condition_met: bool,
    collapse_occurred: bool,
    ambiguity_state: str,
    narrower_latency_ms: float,
    source: str,
    record_kind: str,
    now: Callable[[], str] | None = None,
    new_uuid: Callable[[], str] | None = None,
) -> dict:
    """Build a Layer 1 record dict per
    ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §3. Pure function — no I/O,
    no exceptions caught (any failure surfaces to the writer's
    failure-invisibility wrapper).

    ``registered_tools`` is a separate parameter from the candidate
    sets per ``A.5.3.2-PR3-SPEC.md`` §5 (orthogonal-truth-surfaces
    framing): registered tools fingerprint deployment identity;
    candidate sets fingerprint runtime topology; arbitration
    inputs/outputs fingerprint decision truth. Recombining them
    would conflate identity drift with topology drift in the
    resulting hash.

    ``now`` and ``new_uuid`` are test-injection seams. Production
    callers do not provide them (the defaults are ``_now_iso_ms``
    and ``_new_uuid``). Tests pass deterministic substitutes when
    full record-content assertions matter.

    The builder is exposed for testing only; production code must
    not import ``_build_capture_record`` directly. The leading
    underscore is the binding contract.
    """
    _now = now or _now_iso_ms
    _uuid = new_uuid or _new_uuid

    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": _uuid(),
        "captured_at": _now(),
        "record_kind": record_kind,
        "source": source,
        "prompt": prompt,
        "candidate_set": {
            "post_reachability": _tool_names(candidate_set_post_reachability),
            "post_pr14_filter": _tool_names(candidate_set_post_pr14),
        },
        "topology": snapshot_topology(),
        "identity": {
            "narrower_version_hash": narrower_version_hash(),
            "registered_tools_snapshot_hash": (
                registered_tools_snapshot_hash(registered_tools)
            ),
            "daemon_git_sha": daemon_git_sha(),
        },
        "narrower": {
            "decision": _tool_names(narrower_decision),
            "pr20_condition_met": pr20_condition_met,
            "collapse_occurred": collapse_occurred,
            "ambiguity_state": ambiguity_state,
            "latency_ms": narrower_latency_ms,
        },
    }


# ── Writer ─────────────────────────────────────────────────────────────────


def _resolve_corpus_dir() -> Path:
    """Resolve the corpus directory path. ``FORGE_BRIDGE_CORPUS_DIR``
    overrides; the default is ``~/.forge-bridge/corpus/`` (per
    contract §7).

    Per spec §6.1: the env-var override is the single test-isolation
    surface. ``emit_divergence_capture`` does not take a path
    argument because the helper signature stays fire-and-forget per
    the framing's mechanical-dumbness constraint.
    """
    override = os.environ.get(_CORPUS_DIR_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".forge-bridge" / "corpus"


def _make_header(captured_at: str) -> dict:
    """Build the per-file header record. Format pinned by contract §7
    + spec §6.3."""
    return {
        "_header": True,
        "schema_version": SCHEMA_VERSION,
        "created_at": captured_at,
        "format": "forge-bridge-divergence-corpus-v1",
    }


def _serialize_line(record: dict) -> str:
    """Serialize a record to a single JSONL line. Compact separators,
    UTF-8 friendly (``ensure_ascii=False`` per spec §12 decision 6),
    terminated by ``\\n``."""
    return json.dumps(
        record, ensure_ascii=False, separators=(",", ":"),
    ) + "\n"


def _prompt_prefix_for_log(prompt: Any) -> str:
    """Truncated prompt prefix for WARNING messages.

    Contract §8.4 privacy posture: never log the full prompt. First
    32 characters max, ellipsis if truncated, empty string if the
    input is not a string (which itself is a logged failure mode).
    """
    if not isinstance(prompt, str):
        return ""
    if len(prompt) <= 32:
        return prompt
    return prompt[:32] + "..."


def emit_divergence_capture(
    *,
    prompt: str,
    registered_tools: list[Any],
    candidate_set_post_reachability: list[Any],
    candidate_set_post_pr14: list[Any],
    narrower_decision: list[Any],
    pr20_condition_met: bool,
    collapse_occurred: bool,
    ambiguity_state: str,
    narrower_latency_ms: float,
    source: str,
) -> None:
    """Fire-and-forget Layer 1 capture. Returns ``None``.

    Per ``A.5.3.2-PR3-SPEC.md`` §5.2, every step inside this
    function body is wrapped in a single ``try`` / ``except
    Exception`` block. Any exception — schema validation,
    filesystem error, encoding failure, lock contention, anything —
    is caught, logged at WARNING with structured detail (call site,
    failure mode, prompt prefix per contract §8.4 privacy posture),
    and swallowed. The function returns ``None`` regardless.
    Observation failure cannot become arbitration failure (I-6).

    Per spec §6.5, the file write is a single ``file.write(...)``
    call: header + first record bundled when creating a new file,
    record alone when appending to an existing file. The writer
    never attempts partial-record recovery, in-place repair,
    continuation writes, or seek-and-reconstruct. If a write fails,
    the record is considered lost.

    Per spec §5 (orthogonal truth surfaces), ``registered_tools``
    is a separate parameter from the candidate sets — it
    fingerprints deployment identity, distinct from runtime
    topology (candidate_set_post_reachability) and arbitration
    decision (narrower_decision et al). The parameters are
    deliberately separate because they fingerprint orthogonal
    truths. This is not redundancy. It is semantic boundary
    preservation.
    """
    try:
        record = _build_capture_record(
            prompt=prompt,
            registered_tools=registered_tools,
            candidate_set_post_reachability=candidate_set_post_reachability,
            candidate_set_post_pr14=candidate_set_post_pr14,
            narrower_decision=narrower_decision,
            pr20_condition_met=pr20_condition_met,
            collapse_occurred=collapse_occurred,
            ambiguity_state=ambiguity_state,
            narrower_latency_ms=narrower_latency_ms,
            source=source,
            # PR 7 Step 5 (post-§4.3 amendment): observation records are
            # what live arbitration emits. Step 6 introduces the
            # contextvar resolution path that may redirect ``source`` to
            # ``"seed"`` when a seed_dispatch_scope is active; the
            # ``record_kind`` discriminator stays ``"observation"`` for
            # all live arbitration emissions regardless of source value.
            # Expectation records are PR 8's domain
            # (``_persist_expectation_record`` lands at Step 8).
            record_kind="observation",
        )
        validate_capture_record(record)

        corpus_dir = _resolve_corpus_dir()
        corpus_dir.mkdir(parents=True, exist_ok=True)

        # File-per-UTC-day per contract §7. Date is taken from the
        # record's ``captured_at`` so multiple records emitted in the
        # same instant land in the same file deterministically.
        date_part = record["captured_at"][:10]  # "YYYY-MM-DD"
        path = corpus_dir / f"capture-{date_part}.jsonl"

        # §6.5: bundle header + first record into a single
        # file.write(...) call when the file is new or empty. The
        # bundling preserves the carrier invariant "Corpus existence
        # implies at least one truthful persisted capture." A
        # write(header) followed by write(record) two-step would
        # create the transient impossible state the bundling rule
        # exists to prevent.
        needs_header = not (path.exists() and path.stat().st_size > 0)

        record_line = _serialize_line(record)
        if needs_header:
            header_line = _serialize_line(_make_header(record["captured_at"]))
            payload = header_line + record_line
        else:
            payload = record_line

        # §6.5: exactly one file.write(...) per emission. The single
        # write is the atomic-append discipline made operational. No
        # split into JSON-emission + newline-emission. No split into
        # header-write + record-write. No buffering beyond what the
        # OS provides. Open → write → flush → close, every emission.
        with path.open("a", encoding="utf-8") as f:
            f.write(payload)
            f.flush()

    except Exception as exc:  # noqa: BLE001 — I-6 failure invisibility
        # I-6: observation failure cannot become arbitration failure.
        # Every failure mode (disk full, permission, partial write,
        # serialization, malformed runtime state, etc.) is caught
        # here and logged at WARNING. Nothing escapes.
        try:
            source_marker = source if isinstance(source, str) else "<invalid>"
            logger.warning(
                "capture write failed: source=%s, error=%s: %s, prompt_prefix=%r",
                source_marker,
                type(exc).__name__,
                exc,
                _prompt_prefix_for_log(prompt),
            )
        except Exception:  # noqa: BLE001 — even logging must not propagate
            # If even the WARNING log fails (e.g., logging subsystem
            # broken), we silently swallow. I-6 is binding: nothing
            # escapes from this function.
            pass

    return None
