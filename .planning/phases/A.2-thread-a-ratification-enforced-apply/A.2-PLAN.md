---
milestone: v1.7
thread: A
phase: A.2
phase_name: Ratification + enforced apply — assent as substrate state
status: phase-plan
drafted: 2026-05-28
revised:
  - 2026-05-28 (v3 — Stage 1b cycle 2 polish pass absorbed. Three net-new polish catches all surgical, none structural. M-new1 (DT archaeology-grade): modified-files heading count drift "9 files" → actual 10 entries; inline recount "15 new + 9 modified = 24" → "15 new + 10 modified = 25"; sibling absorption pass per [[feedback-sibling-check-before-fix-scope]] — v2 absorbed M4 new-files heading but left modified-files heading uncorrected. M-new2 (DT archaeology-grade): L11 helper docstring naming drift — said "Mirrors 0005's helper at content_addressed_repo migration" but content_addressed_repo.py is a class file, not a migration; corrected to "Mirrors the helper at 0005_phase4b_entity_types.py:62-64 (last migration to touch ck_entities_type)" with verbatim site reference. M-new3 (DT polish, same failure-shape family as F1/F2): D5 acceptance bullets 4 + 5 framed `run_chain_steps(steps=[..., "commit"], assent_record=None)` as "regime-3 preview-only path under A.1's pre-A.2 semantics — preserved unchanged" but under A.1 regime-3 SHORT-CIRCUITS at run_compile_branch before reaching run_chain_steps; no A.1 caller exercises this combination. v3 rewords as defensive default for kwarg surface with explicit "no A.1 caller exercises this combination" note; A.2's apply path passes assent_record explicitly via _run_apply_branch. Methodology candidate WIDENED: writing-room substrate-recall failure modes span shape (F1 dataclass fields), convention (F2 helper pattern), AND flow (M-new3 regime path). Three distinct surface manifestations, one root cause (memory-shaped recall vs file-shaped grounding), one Stage 1b discipline (substrate-shape grounding sweep). Per [[feedback-failure-shape-stability-as-disposition-evidence]]: disposition stability across all three instances is load-bearing evidence — promotion-grade candidate for A.2-CLOSE. Catch trajectory across cycles: v1→v2 = 9 (2 framing + 7 polish, structural); v2→v3 = 3 (0 framing + 3 polish, surgical). Healthy convergence; comparable to discuss-stage 10→2→0 trajectory. Per Creative cycle-2 frame: "Stage 1a discovers architecture. Stage 1b reattaches the architecture to the actual codebase. Different jobs, different failure signatures." Cycle 3 expected to be sign-off territory unless something genuinely new surfaces.)
  - 2026-05-28 (v2 — Stage 1b cycle 1 absorbed. Framing-grade catches (F1 + F2) + 7 polish-grade catches (M1..M7) all landed. F1 (DT BLOCKER): L5 + D4 invented CommitVerification shape that contradicts shipped dataclass + production caller + tests. v2 rewrites L5 against the verified shape (matched / drift_count / first_drift_index + new assent_valid + assent_record fields) and re-grounds the verify() body description against the shipped element-by-element drift algorithm; CommitError gains ASSENT_INVALID code constant + optional graph_intent_id kwarg; production caller at _step.py:798-808 ADOPTS the new assent_valid branch (moved from NOT-modified to modified). F2 (DT BLOCKER): L11 + D3 migration constraint string contained 3 fictional entity_types (orchestration_*_ledger are TABLE names from 0006/0007/0008, NOT entity_type discriminators). v2 rewrites L11 using the _entity_type_check helper pattern from migration 0005; pre-A.2 baseline is 20 entity_types (verified against 0005's _ALL_ENTITY_TYPES tuple); A.2 extends 20 → 21 by adding 'assent_record'; zero fictional siblings. F1 cascade: AssentRecord propagation through run_chain_steps → step executor → verify call requires _engine.py + _step.py modifications; new D5 ships the consumer adoption (substrate-before-consumer preserved: D4 = primitive, D5 = first consumer); D5..D9 from v1 renumbered to D6..D10. Polish: M1 _build_preview → build_preview_from_steps (actual name at _chat_compile.py:73); M2 L9(a) example shows async with session_factory + await session.commit() lifecycle; M3 regime-3 line count corrected 131-133 → 131-137; M4 file manifest heading "10 files" → "13 files"; M5 absorbed as F1 cascade; M6 subsumed by F1; M7 entity_type lookup error envelope plan-pick: silent fall-through to assent_record_not_found (CLI regex prevents UUID confusion; daemon-side entity_type='assent_record' scoping prevents cross-substrate confusion). Methodology candidate per [[feedback-failure-shape-stability-as-disposition-evidence]]: Stage 1b's substrate-shape grounding discipline as load-bearing scope-anchor for code-handoff specs — 2nd within-arc instance after A.1 C2. Self-referential failure mode caught: writing-room had [[feedback-ground-specs-in-actual-files]] + [[feedback-fixture-shape-mirrors-production]] in memory and still drafted L5+L11 from shape-shaped recall. Carry to A.2-CLOSE methodology synthesis.)
type: phase-plan
derives_from:
  - .planning/phases/A.2-thread-a-ratification-enforced-apply/A.2-DISCUSS-QUESTIONS.md
  - .planning/phases/A.2-thread-a-ratification-enforced-apply/A.2-FRAMING.md
governing_rulings: R-A2.0 (parallel substrate) + R-A2.1 (content-hash identity) + R-A2.2 (CAR-pattern table) + R-A2.3 (no expiration, drift-invalidates) + R-A2.4 (event: apply_complete) + R-A2.5 (CommitNode.verify optional assent kwarg) + R-A2.6 (fbridge ratify top-level) + R-A2.7 (store-and-replay) + R-A2.8 (decided_by placeholder)
artifact_role: code-handoff — implementation hands off against this spec after Stage 1b verification clears
review_state: writing-room-v3-stage-1b-cycle-2-absorbed-pending-stage-1b-cycle-3
---

# A.2 — Ratification + enforced apply

> **What this artifact is.** The code-handoff phase plan for A.2,
> the second phase in v1.7 Thread A. Locks the `AssentRecord`
> substrate, the `AssentRecordRepo` CAR-extension, the
> `ck_entities_type` migration, the `CommitNode.verify()` signature
> extension, the regime-3 chat-handler modification, the
> `fbridge ratify` CLI surface, the new chat-side terminal SSE taxon
> `event: apply_complete`, the assent-audit-event taxa, the test
> plan, and the file change manifest. Implementation hands off
> against this spec after Stage 1b verification clears (DT seat).
>
> **What this artifact is not.** Not implementation. Not a partial
> draft to be filled during execution. The contracts below are the
> spec; deviation requires a spec amendment, not implementation-time
> discretion.

## Scope

A.2 ships the ratification + enforced-apply surface of Thread A's
NL → compile → canonical graph → execution substrate → host arc.
A.1 stratified the chat path through compile-and-preview but left
the authority-transition gate stubbed. A.2 closes the loop by
making **assent a substrate record** attached to graph-intent
identity, with the CLI as the operator ratify surface and the
existing `run_chain_steps` post-compile executor enforcing assent
at the commit-node step.

Specifically:

- A new `AssentRecord` core dataclass in
  `forge_bridge/core/assent.py` — sibling to `StagedOperation`
  carrying graph-intent identity + chain-step body + ratification
  metadata.
- A new `assent_record` entity_type substrate, persisted via a new
  `AssentRecordRepo(ContentAddressedRepo)` subclass at
  `forge_bridge/store/assent_record_repo.py` — reuses the shipped
  generic CAR base; extends with state-machine transition methods
  per the audit-event integration pattern `StagedOpRepo` already
  ships.
- A new Alembic migration `0009_assent_record.py` extending the
  `ck_entities_type` CHECK constraint to include `'assent_record'`
  (analog to `0003_staged_operation.py`).
- An extension to `forge_bridge/graph/commit.py` —
  `CommitNode.verify(held, fresh, assent=None) -> CommitVerification`
  with optional `assent` kwarg; `CommitVerification` dataclass gains
  `assent_valid: bool` + `assent_record: AssentRecord | None`
  fields.
- Modification of `forge_bridge/console/_chat_compile.py` regime-3
  branch — graph-intent-id allocation (12-char content-hash prefix),
  `AssentRecord` creation at `state=proposed`, threading of
  `graph_intent_id` into the L4 preview shape.
- Modification of `forge_bridge/console/handlers.py` chat handler —
  new chat dispatch surface for `apply <graph_intent_id>` command;
  store-and-replay path that invokes `run_chain_steps` against the
  persisted chain; new SSE terminal taxon `event: apply_complete`.
- A new `fbridge ratify <graph_intent_id>` CLI subcommand at
  `forge_bridge/cli/main.py` — top-level (matches existing
  `chat`/`exec`/`run`/`flame-exec` pattern); atomic ratify+apply by
  default; writes assent via `AssentRecordRepo` and invokes the
  shared store-and-replay substrate; exit codes locked at L8.
- Four new audit-event types emitted by `AssentRecordRepo`:
  `assent.proposed` / `assent.ratified` / `assent.applied` /
  `assent.failed`. Distinct from `staged.*` per R-A2.0(a)
  parallel-substrate semantics.

Per the discuss artifact: A.2 is **ratification + enforced apply**.
A.1 shipped the compile + preview surface; A.3 is hardening —
surfaced once A.2 lands. The authority transition closes
end-to-end with A.2.

Per `[[feedback-substrate-not-producer]]`: A.2 adds substrate
primitives (AssentRecord, AssentRecordRepo, CommitNode.verify
extension) and operator surfaces (fbridge ratify CLI + chat apply
command) on top. The `staged_operation` substrate is preserved
unchanged — A.2 ships `assent_record` as a parallel substrate, not
as an extension of `staged_operation` (per R-A2.0(a)). The two
substrates coexist with distinct constitutive identities (bridge
as bookkeeper for staged_operation; bridge as executor for
assent_record).

## Substrate inventory (grounded; do not duplicate)

Verified 2026-05-28 against current `main` (`37e7dcb`):

- **`ContentAddressedRepo` base class** —
  `forge_bridge/store/content_addressed_repo.py:32-127`. Generic
  base; `__entity_type__` + `__model__` ClassVars set per subclass;
  `_canonical_hash(body)` static method uses
  `json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False)`
  followed by sha256 hex digest; `insert_if_absent(body)` idempotent
  by content; `get_by_content_hash` + `get_by_id` reads;
  `update()` / `delete()` raise `ImmutableArtifactError` (CAR
  immutability discipline). **A.2 extends with a subclass.**
- **`ImmutableArtifactError`** —
  `forge_bridge/store/content_addressed_repo.py:18`. Raised by
  CAR's `update()` / `delete()`. **A.2 does NOT raise this;
  AssentRecordRepo does not override the inherited update/delete
  (state-machine transitions mutate `DBEntity.status` + ratification
  metadata directly, leaving `content_hash` + `attributes.body`
  immutable).**
- **`DBEntity`** — `forge_bridge/store/models.py:270` (table
  `entities`). Discriminator `entity_type` with `ck_entities_type`
  CHECK constraint (current values include `'staged_operation'`,
  orch_* values added in migration 0005). JSONB `attributes` column;
  nullable `content_hash` column. **A.2 extends the CHECK to
  include `'assent_record'` via migration 0009.**
- **`StagedOpRepo`** — `forge_bridge/store/staged_operations.py:91-462`.
  Composes `EventRepo(session)` for audit-event emission on a
  shared session (atomicity invariant); `_transition` method
  enforces `_ALLOWED_TRANSITIONS` frozenset; emits transition events
  via `_append_event`. **Pattern reference for AssentRecordRepo's
  state-machine transition shape.**
- **`EventRepo`** —
  `forge_bridge/store/repo.py` (`append` method). Used by
  `StagedOpRepo` for audit emission. **AssentRecordRepo composes
  the same way.**
- **Migration head** —
  `forge_bridge/store/migrations/versions/0008_phase4b_orchestration_compromise_ledger.py`.
  **A.2's migration revises as `0009_assent_record.py` with
  `down_revision = "0008"`.**
- **`CommitVerification` dataclass** —
  `forge_bridge/graph/commit.py:91`. Existing fields: `is_valid:
  bool`, `held_hash: str`, `fresh_hash: str`, `mismatch_reason:
  Optional[str]`. **A.2 adds `assent_valid: bool` (default True
  for drift-only callers) + `assent_record: Optional[AssentRecord]`
  (default None).**
- **`CommitNode`** — `forge_bridge/graph/commit.py:98`.
  `verify(self, held: MutationManifest, fresh: MutationManifest)`
  at `:106`. **A.2 extends signature: adds optional `assent:
  Optional[AssentRecord] = None` kwarg.**
- **`CommitNode.verify` call sites** — 5 total per A.2 framing
  grounding (1 production at `console/_step.py:799` + 4 tests at
  `tests/graph/test_commit.py:257/268/279/303`). **A.1's
  drift-only invocation shape is backward-compatible under R-A2.5's
  optional kwarg lean.**
- **`run_chain_steps`** — `forge_bridge/console/_engine.py:14`.
  Signature `run_chain_steps(*, steps: list[str], tools: list,
  mcp, request_id, client_ip, started) -> dict`. Sequential,
  abort-on-first-error. **A.2's store-and-replay path invokes this
  unchanged — graph-intent comes from the stored `AssentRecord.body`
  rather than freshly-compiled output, but the executor is the
  same.**
- **`CompileBranchOutcome`** —
  `forge_bridge/console/_chat_compile.py:18`. A.1's 4-regime enum
  (`compiled_non_mutating` / `compiled_mutating_preview` /
  `compile_error` / `chain_aborted`). **A.2 extends the
  `compiled_mutating_preview` regime data payload — the outcome
  now also carries `graph_intent_id: str` and `assent_record_id:
  uuid.UUID` for the regime-3 preview-emit path.**
- **`run_compile_branch`** —
  `forge_bridge/console/_chat_compile.py:98-160`. The regime
  dispatcher. **A.2 modifies the `regime="compiled_mutating_preview"`
  branch only — allocates graph_intent_id, creates AssentRecord
  via repo, threads both into the outcome. Other regimes
  unchanged.**
- **L4 preview shape** —
  `{kind, steps[...], summary{total_steps, mutating_steps, requires_ratification}}`
  per A.1 L4. **A.2 adds a top-level `graph_intent_id` field to
  the preview shape; rest preserved verbatim.**
- **Chat-side SSE terminal taxa (A.1's 5)** — `compile_complete` /
  `chain_complete` / `preview_emitted` / `chain_aborted` /
  `compile_error`. Emission sites enumerated at
  `handlers.py:1098` (SSE preview_emitted), `:1119`
  (SSE chain_complete), `:1788` (JSON preview_emitted), `:1810`
  (JSON chain_complete). **A.2 adds a 6th terminal taxon
  `event: apply_complete` for the chat-driven apply path; emit
  sites are inside the new apply-dispatch branch added to
  `handlers.py` per D6.**
- **`fbridge` CLI Typer hierarchy** —
  `forge_bridge/cli/main.py`. Top-level subcommands: `doctor`,
  `actions`, `chat`, `exec`, `run`, `flame-exec`, `up`, `down`,
  `status` + subgroups `console`, `mcp`, `flame`, `graph`. **A.2
  adds `fbridge ratify <graph_intent_id>` as a NEW top-level
  subcommand sibling to the existing top-level set.**
- **Exit-code convention (locked)** — `fbridge flame-exec`
  pattern: 0=ok, 1=failure (Flame-side error), 2=transport (daemon
  unreachable). **A.2's `fbridge ratify` adopts this verbatim with
  failure-class specialization: 1 covers assent failures (unknown
  graph_intent_id, already-ratified, already-applied, write
  failure, drift_invalid, chain_aborted); 2 covers daemon
  transport.**
- **`staged_operation` substrate** —
  `forge_bridge/core/staged.py` + `forge_bridge/store/staged_operations.py`.
  Bridge-as-bookkeeper invariant per `staged.py:5-7`. **A.2 does
  NOT modify this substrate. R-A2.0(a) parallel-substrate ruling
  is enforced by surface separation — the four
  `forge_*_staged` MCP tools and `forge_bridge.store.staged_operations`
  remain unchanged; `assent_record` substrate is additive.**
- **`forge_*_staged` MCP tools** —
  `forge_bridge/mcp/tools.py:152-266` (the four impl functions).
  **Unchanged by A.2. Stage 2 grep verifies no resurrection of
  bridge-side propose for `staged_operation` (preserves the
  consumer-driven propose invariant).**

The substrate is ready. A.2 adds the assent_record substrate
primitive + the CommitNode.verify extension + the operator ratify
surfaces (CLI + chat apply command) on top.

## Locks

Locks are the load-bearing contract anchors Stage 1b verifies. Any
deviation from these requires a spec amendment, not
implementation-time discretion.

### L1 — `AssentRecord` dataclass shape

**`AssentRecord` is a new `BridgeEntity` subclass at
`forge_bridge/core/assent.py`. The exact field shape below is the
contract. Sibling to `StagedOperation` in pattern; distinct in
constitutive identity per R-A2.0(a).**

```python
"""AssentRecord application class for forge-bridge Phase A.2 (v1.7).

Represents an operator's authority-attached decision on a
bridge-compiled graph-intent. Bridge IS the executor here (unlike
StagedOperation where bridge is the bookkeeper); the assent record
authorizes bridge's own execution of the persisted chain.

The state machine (``proposed → ratified → applied | failed``) is
enforced by ``forge_bridge.store.assent_record_repo.AssentRecordRepo``.
This class carries no state-machine logic.

``to_dict()`` is the single source of truth for the shape that the
CLI and the chat surface return verbatim. Any consumer that
serializes an AssentRecord must call ``to_dict()`` — never
hand-roll the shape.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from forge_bridge.core.entities import BridgeEntity


class AssentRecord(BridgeEntity):
    """An operator's authority-attached decision on a graph-intent.

    Constitutive identity per R-A2.0(a): bridge persists what it
    compiled, the operator decides whether bridge proceeds, bridge
    executes. Distinct from StagedOperation (where bridge is
    bookkeeper for consumer-proposed, consumer-executed
    operations).

    Lifecycle (enforced by AssentRecordRepo, NOT by this class):
        proposed  → ratified  → applied
        proposed  → ratified  → failed
        (no rejected state — non-ratification is implicit by absence
         of ratify action; drift-invalidate happens at apply time)

    Constructing AssentRecord rows directly via
    ``session.add(DBEntity(entity_type='assent_record', ...))`` is
    prohibited — AssentRecordRepo is the only sanctioned write
    path. Direct construction bypasses the audit-trail event
    emission and the content-hash idempotency guarantee.
    """

    def __init__(
        self,
        graph_intent_id: str,
        chain_steps: list[str],
        status: str = "proposed",
        decided_by: Optional[str] = None,
        decided_at: Optional[datetime] = None,
        applied_at: Optional[datetime] = None,
        apply_result: Optional[dict[str, Any]] = None,
        apply_failure_reason: Optional[str] = None,
        id: Optional[uuid.UUID | str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(id=id, created_at=created_at, metadata=metadata)
        self.graph_intent_id:      str                      = graph_intent_id
        self.chain_steps:          list[str]                = chain_steps
        self.status:               str                      = status
        self.decided_by:           Optional[str]            = decided_by
        self.decided_at:           Optional[datetime]       = decided_at
        self.applied_at:           Optional[datetime]       = applied_at
        self.apply_result:         Optional[dict[str, Any]] = apply_result
        self.apply_failure_reason: Optional[str]            = apply_failure_reason

    @property
    def entity_type(self) -> str:
        return "assent_record"

    def to_dict(self) -> dict:
        """Return the shape that CLI + chat surfaces return verbatim.

        Shape (14 keys total):
            From super().to_dict(): id, entity_type, created_at,
                                     metadata, locations, relationships
            Added by this method:   graph_intent_id, chain_steps,
                                     status, decided_by, decided_at,
                                     applied_at, apply_result,
                                     apply_failure_reason
        """
        d = super().to_dict()
        d.update({
            "graph_intent_id":      self.graph_intent_id,
            "chain_steps":          self.chain_steps,
            "status":               self.status,
            "decided_by":           self.decided_by,
            "decided_at":           self.decided_at.isoformat() if self.decided_at else None,
            "applied_at":           self.applied_at.isoformat() if self.applied_at else None,
            "apply_result":         self.apply_result,
            "apply_failure_reason": self.apply_failure_reason,
        })
        return d

    def __repr__(self) -> str:
        return (
            f"AssentRecord(graph_intent_id={self.graph_intent_id!r}, "
            f"status={self.status!r}, id={self.id!s:.8}...)"
        )
```

**Anti-scope:** `AssentRecord` is NOT exported via
`forge_bridge.__all__`. The assent family is internal to
`forge_bridge.core` + `forge_bridge.store`; chat handlers / CLI
import directly from `forge_bridge.core.assent`. Preserves the
19-symbol public surface invariant (carried unchanged across
v1.4.x → v1.6 → v1.7).

**Decision-record vs apply-record split per Creative C9
(discuss):** graph-intent identity is content-addressed; the
`graph_intent_id` field is the 12-char prefix of the content-hash.
Ratification-event identity is OPEN per discuss-stage ruling — A.2
binds decision metadata into the AssentRecord directly (single-row
shape) but does not foreclose future event-addressed
ratification history. Plan-locks the single-row shape for A.2; the
two-lifetimes concern (per R-A2.1+R-A2.2 discuss "Two lifetimes
within the record") is addressed by leaving `apply_result` /
`apply_failure_reason` mutable on the same row at terminal
transition while `chain_steps` + `graph_intent_id` remain
immutable.

### L2 — `AssentRecordRepo` shape

**`AssentRecordRepo(ContentAddressedRepo)` at
`forge_bridge/store/assent_record_repo.py`. Subclass of the shipped
generic CAR base; extends with state-machine transition methods
modeled on `StagedOpRepo`.**

```python
"""forge-bridge Phase A.2 — AssentRecord repository.

Composes the generic ContentAddressedRepo base for content-hash
identity + idempotent insert + immutability discipline on the
graph-intent body, AND composes EventRepo for atomic audit-event
emission on every state transition.

State machine (L1):
    (None)     → proposed   (via propose())
    proposed   → ratified   (via ratify())
    ratified   → applied    (via mark_applied())
    ratified   → failed     (via mark_failed())
    Terminals: applied, failed. Any other transition raises
    AssentRecordLifecycleError.

Immutability composition (per R-A2.1+R-A2.2 discuss "Two lifetimes
within the record"):
    The CAR base's update() / delete() remain raising — the
    chain_steps body + content_hash are IMMUTABLE post-insert.
    State-machine transitions update DBEntity.status +
    DBEntity.attributes (ratification + apply metadata) directly
    on the same row via _transition; chain_steps is NEVER in
    attribute_updates.

Atomicity guarantee (mirrors StagedOpRepo): status update and
audit-event append share the SAME AsyncSession that the repo was
constructed with. They either both commit or both rollback — no
window where status advances without an audit record.

Composition (PATTERNS.md Finding #8): AssentRecordRepo composes
EventRepo(session); direct session.add(DBEvent(...)) is NEVER used
inside this module.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.core.assent import AssentRecord
from forge_bridge.store.content_addressed_repo import (
    ContentAddressedRepo,
    ImmutableArtifactError,
)
from forge_bridge.store.models import DBEntity
from forge_bridge.store.repo import EventRepo


class AssentRecordLifecycleError(Exception):
    """Raised when an AssentRecord transition is not permitted by
    the state machine. Carries the attempted transition for
    callers."""

    def __init__(
        self,
        from_status: Optional[str],
        to_status: str,
        record_id: uuid.UUID,
        graph_intent_id: Optional[str] = None,
    ):
        self.from_status     = from_status
        self.to_status       = to_status
        self.record_id       = record_id
        self.graph_intent_id = graph_intent_id
        super().__init__(
            f"Illegal transition from {from_status!r} to {to_status!r} "
            f"for assent_record {record_id}"
            + (f" (graph_intent_id={graph_intent_id})"
               if graph_intent_id else "")
        )


class AssentRecordRepo(ContentAddressedRepo[AssentRecord]):
    """Persist AssentRecord rows and enforce the
    proposed → ratified → applied | failed state machine.

    Per R-A2.1+R-A2.2 joint:
      - content_hash computed by CAR base over canonical-JSON of
        body. Body shape: {"chain_steps": list[str]}.
      - insert_if_absent (inherited) idempotent by content — same
        graph-intent → same content_hash → same row.

    Per R-A2.0(a): bridge IS the executor here. Distinct from
    StagedOpRepo's bridge-as-bookkeeper invariant.
    """

    __entity_type__ = "assent_record"
    __model__ = AssentRecord

    _ALLOWED_TRANSITIONS: frozenset[tuple[Optional[str], str]] = frozenset({
        (None,       "proposed"),
        ("proposed", "ratified"),
        ("ratified", "applied"),
        ("ratified", "failed"),
    })

    _TRANSITION_EVENTS: dict[tuple[Optional[str], str], str] = {
        (None,       "proposed"): "assent.proposed",
        ("proposed", "ratified"): "assent.ratified",
        ("ratified", "applied"): "assent.applied",
        ("ratified", "failed"):  "assent.failed",
    }

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self._events = EventRepo(session)

    # ── Public state-machine methods ────────────────────────────

    async def propose(
        self,
        chain_steps: list[str],
        project_id: Optional[uuid.UUID] = None,
    ) -> AssentRecord:
        """Create an AssentRecord at state=proposed (or return the
        existing row if its content_hash is already present —
        idempotent per CAR base's insert_if_absent).

        Emits an assent.proposed audit event ONLY on first insertion
        (not on idempotent return). Caller owns the commit.
        """
        # ... [body uses self.insert_if_absent + emits event if
        # newly inserted; sets graph_intent_id from content_hash[:12]] ...

    async def ratify(
        self,
        graph_intent_id: str,
        actor: str,
    ) -> AssentRecord:
        """Advance proposed → ratified. Records decided_by + decided_at.

        Raises AssentRecordLifecycleError if not in 'proposed' state.
        Raises AssentRecordNotFound if graph_intent_id resolves to
        no row.
        """
        # ... [transition body] ...

    async def mark_applied(
        self,
        graph_intent_id: str,
        result: dict[str, Any],
    ) -> AssentRecord:
        """Advance ratified → applied. Records applied_at +
        apply_result. Raises AssentRecordLifecycleError on illegal
        transition."""
        # ... [transition body] ...

    async def mark_failed(
        self,
        graph_intent_id: str,
        reason: str,
        result: Optional[dict[str, Any]] = None,
    ) -> AssentRecord:
        """Advance ratified → failed. Records applied_at +
        apply_failure_reason. Reason is one of:
        "drift_invalid" / "chain_aborted" / "assent_invalid"."""
        # ... [transition body] ...

    async def get_by_graph_intent_id(
        self,
        graph_intent_id: str,
    ) -> Optional[AssentRecord]:
        """Lookup by 12-char prefix of content_hash. Returns the
        latest row if multiple match (collision-tolerant)."""
        # ... [select * where attributes->>'graph_intent_id' = ...] ...

    async def list_pending(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AssentRecord], int]:
        """List records optionally filtered by status."""
        # ... [select with filters; ordering by created_at desc] ...
```

**Body-shape lock for `insert_if_absent`:** the body passed to CAR
base is exactly `{"chain_steps": list[str]}` — single key. This
ensures content_hash is computed ONLY over the graph-intent
content, not over ratification metadata. Ratification metadata
lives in `attributes.decided_by` / `attributes.decided_at` etc.,
mutated via `_transition` and NOT part of the content-hash.

**`AssentRecordNotFound` exception** — raised by `ratify` /
`mark_applied` / `mark_failed` when the `graph_intent_id` lookup
returns None. Sibling to `AssentRecordLifecycleError`; subclass of
`Exception` directly (NOT `RegistryError`, per PATTERNS.md Critical
Pre-Planning Finding #5/#7 lineage).

### L3 — Content-hash identity over canonical-JSON of chain_steps

**`graph_intent_id` is the **first 12 characters** of sha256-hex
computed over canonical JSON of `{"chain_steps": list[str]}`,
where canonical JSON is `json.dumps(body, sort_keys=True,
separators=(',', ':'), ensure_ascii=False)`.**

The CAR base's `_canonical_hash` produces the full 64-char hex;
A.2 takes the 12-char prefix for the public-facing identifier.
This matches the existing `ContentAddressedRepo` convention at
`content_addressed_repo.py:94` where the `name` column is
`f"{entity_type}:{content_hash[:12]}"` — A.2 follows the same
12-char prefix discipline per FC-A2.3 / R-A2.1 carve-out 2.

**Collision risk:** 12 hex chars = 48 bits. Birthday-bound
collision probability negligible for A.2's substrate density
(individual operator workstation, expected single-digit-thousands
of records over a project lifetime). Plan does NOT add
collision-handling fallback for A.2; future-phase concern if
substrate density grows beyond that.

**Anti-pattern:** truncating to fewer than 12 chars (paste-friction
gain too small; collision risk grows materially below 8 chars). The
12-char prefix is the locked shape.

**Identity-scope discipline per Creative C9 (discuss):** the
12-char `graph_intent_id` identifies the graph-intent. The
`AssentRecord.id` (UUID) identifies the ratification-event row.
These are distinct identifiers in the model. The
`graph_intent_id` is also exposed in the
`name` column (`f"assent_record:{graph_intent_id}"`) for
DB-side grep-ability + index reuse.

### L4 — Graph-intent-id wire shape

**`graph_intent_id` appears on the wire as a 12-char lowercase
hex string. The CLI positional argument accepts the same form. No
typed wrapper; no longer-prefix; no shorter prefix.**

Wire shape locations:

- **L4 preview JSON envelope** (A.1's preview shape) — adds a new
  top-level field `graph_intent_id: str` (the 12-char prefix).
  Position: alongside `kind`, before `steps`. Other A.1 fields
  preserved verbatim.
- **L4 preview SSE event** — `event: graph_intent_preview` data
  payload extends to include the `graph_intent_id` field at the
  same position.
- **`fbridge ratify <graph_intent_id>`** — positional argument;
  validated against `^[a-f0-9]{12}$` regex.
- **Chat-side apply trigger** — operator types `apply
  <graph_intent_id>` as a chat message; chat handler parses with
  the same 12-char hex regex.
- **`event: apply_complete` SSE data payload** — includes the
  `graph_intent_id` field so consumers can correlate the apply
  result to a prior preview.
- **`assent.*` audit-event payloads** — include the
  `graph_intent_id` field for cross-substrate query without join.

**Operator-UAT note** per FC-A2.3: 12-char hex is paste-friendly
in terminal contexts (selects cleanly with double-click on most
terminals; fits in one shell argument; no line-wrapping).

### L5 — `CommitNode.verify()` signature extension + `CommitVerification` field additions + `CommitError` taxon

**`CommitNode.verify(self, held, fresh, assent=None) ->
CommitVerification`. The optional `assent` kwarg is the extension;
absence preserves A.1's drift-only behavior verbatim.
`CommitVerification` dataclass gains two new fields with safe
defaults. `CommitError` gains an `ASSENT_INVALID` code constant +
optional `graph_intent_id` kwarg.**

**Shipped shape (verified 2026-05-28 against
`forge_bridge/graph/commit.py:90-130`):**

```python
@dataclass(frozen=True)
class CommitVerification:
    matched: bool
    drift_count: int = 0
    first_drift_index: int | None = None
```

Three fields. NOT `is_valid` / `held_hash` / `fresh_hash` /
`mismatch_reason`. The shipped verify() body iterates
`held.resolved_plan` vs `fresh.resolved_plan` element-by-element
counting drift items — NOT a canonical-hash comparison.

**A.2-extended shape:**

```python
# forge_bridge/graph/commit.py

@dataclass(frozen=True)
class CommitVerification:
    # Fields (existing — preserved verbatim):
    matched: bool
    drift_count: int = 0
    first_drift_index: int | None = None
    # Fields (added by A.2 — default values preserve backward compat):
    assent_valid: bool = True
    assent_record: Optional["AssentRecord"] = None


class CommitNode:
    def verify(
        self,
        held: MutationManifest,
        fresh: MutationManifest,
        assent: Optional["AssentRecord"] = None,
    ) -> CommitVerification:
        """Verify both drift validity and (optionally) assent validity.

        Drift check (existing behavior, preserved verbatim from A.1):
        iterates held.resolved_plan vs fresh.resolved_plan
        element-by-element and counts drift items; sets
        matched=(drift_count == 0). Source-line preserved at
        commit.py:106-130.

        Assent check (A.2 extension):
          - If assent is None: assent_valid defaults True;
            assent_record is None. Drift-only callers see no
            behavioral change. This is the backward-compatible path
            the 4 test call sites already use.
          - If assent is not None: validates
            assent.status == "ratified". Sets assent_valid=False
            iff status is any value other than "ratified".

        Aggregate result:
          - matched signals drift validity (existing semantic)
          - assent_valid signals assent validity (new semantic)
          - NO aggregate boolean is folded — consumers read both
            signals separately. Drift abort and assent abort have
            distinct CommitError codes (PLAN_STATE_DRIFT vs
            ASSENT_INVALID); folding into a single bool would
            require checking which side failed anyway.

        Per R-A2.5 + extend-the-primitive law: authority lives
        INSIDE the primitive. The caller does NOT branch on
        `if ratified: verify(held, fresh) else something`; the
        caller passes the optional assent and reads two distinct
        validity signals from the returned CommitVerification.
        """
        held_plan = held.resolved_plan
        fresh_plan = fresh.resolved_plan
        max_len = max(len(held_plan), len(fresh_plan))
        drift_count = 0
        first_drift_index: int | None = None

        for index in range(max_len):
            held_item = held_plan[index] if index < len(held_plan) else None
            fresh_item = fresh_plan[index] if index < len(fresh_plan) else None
            if held_item == fresh_item:
                continue
            drift_count += 1
            if first_drift_index is None:
                first_drift_index = index

        matched = drift_count == 0
        assent_valid = (
            True if assent is None
            else assent.status == "ratified"
        )

        return CommitVerification(
            matched=matched,
            drift_count=drift_count,
            first_drift_index=first_drift_index,
            assent_valid=assent_valid,
            assent_record=assent,
        )
```

**CommitError ASSENT_INVALID extension** (shipped CommitError at
`commit.py:27-64` adds a 4th code constant + optional
`graph_intent_id` kwarg; `to_error()` surfaces graph_intent_id
when code is ASSENT_INVALID):

```python
class CommitError(ValueError):
    """Raised when commit verification cannot proceed.

    Code constants (existing — preserved verbatim by A.2):
        MUTATION_MANIFEST_INVALID       = "MUTATION_MANIFEST_INVALID"
        APPLY_COUNTERPART_NOT_DECLARED  = "APPLY_COUNTERPART_NOT_DECLARED"
        PLAN_STATE_DRIFT                = "PLAN_STATE_DRIFT"

    Code constants (added by A.2):
        ASSENT_INVALID                  = "ASSENT_INVALID"
    """
    MUTATION_MANIFEST_INVALID      = "MUTATION_MANIFEST_INVALID"
    APPLY_COUNTERPART_NOT_DECLARED = "APPLY_COUNTERPART_NOT_DECLARED"
    PLAN_STATE_DRIFT               = "PLAN_STATE_DRIFT"
    ASSENT_INVALID                 = "ASSENT_INVALID"

    def __init__(
        self,
        code: str,
        message: str,
        *,
        step_index: int | str | None = None,
        step_text: str | None = None,
        drift_count: int | None = None,
        first_drift_index: int | None = None,
        # Added by A.2:
        graph_intent_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.step_index = step_index
        self.step_text = step_text
        self.drift_count = drift_count
        self.first_drift_index = first_drift_index
        self.graph_intent_id = graph_intent_id  # A.2 extension

    def to_error(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "type": self.code,
            "message": self.message,
        }
        if self.step_index is not None:
            error["step_index"] = self.step_index
        if self.step_text is not None:
            error["step"] = self.step_text
        if self.code == self.PLAN_STATE_DRIFT:
            error["drift_count"] = int(self.drift_count or 0)
            error["first_drift_index"] = int(self.first_drift_index or 0)
        if self.code == self.ASSENT_INVALID and self.graph_intent_id:
            error["graph_intent_id"] = self.graph_intent_id
        return error
```

**Per R-A2.5 cascade discipline:** the type of the `assent` kwarg
is `Optional[AssentRecord]` (the concrete A.2 type). Under
R-A2.0(a) parallel-substrate ruling, this is the appropriate type.
Plan locks the type; discuss artifact's R-A2.5 distinguished
law-independence from type-dependence on R-A2.0, and the room
ruled R-A2.0(a).

**5 call sites — migration mechanics:**

| Site | A.2 disposition |
|---|---|
| `console/_step.py:799` (production) | Production sole caller. Extends to call `CommitNode().verify(manifest, fresh, assent=assent_record)` when the chain context carries an AssentRecord (apply path); falls back to `assent=None` (omit kwarg) otherwise (preview-only path). Adds a new error-return branch after the existing `if not verification.matched` drift branch: `if not verification.assent_valid: return CommitError(ASSENT_INVALID, ..., graph_intent_id=assent_record.graph_intent_id).to_error()`. Detail in D5. |
| `tests/graph/test_commit.py:259/268/279/303` (4 test sites — verified line numbers) | Drift-only invocations preserved unchanged (use default `assent=None`); existing assertions on `verification.matched` / `verification.drift_count` continue to hold because the new fields have safe defaults. New tests added per D9 covering assent-passing path. |

**Field-naming discipline (Stage 1b F1 absorption):** the existing
fields (`matched`, `drift_count`, `first_drift_index`) are NOT
renamed. The new fields (`assent_valid`, `assent_record`) are
additive. Plan v1 invented `is_valid`/`held_hash`/`fresh_hash`/
`mismatch_reason` shapes from substrate-shape recall; v2 honors
the shipped names exactly.

### L6 — `assent_record` audit-event taxa

**Four event types emitted by `AssentRecordRepo._append_event`,
distinct from the `staged.*` family per R-A2.0(a). Names below
are the locked wire shape.**

| Event type | Fires when | Payload keys (in addition to D-07 standard) |
|---|---|---|
| `assent.proposed` | New AssentRecord inserted (not on idempotent return) | `graph_intent_id`, `chain_step_count`, `requires_ratification` |
| `assent.ratified` | proposed → ratified via `ratify()` | `graph_intent_id`, `decided_by`, `decided_at` |
| `assent.applied` | ratified → applied via `mark_applied()` | `graph_intent_id`, `applied_at`, `result_summary` |
| `assent.failed` | ratified → failed via `mark_failed()` | `graph_intent_id`, `applied_at`, `failure_reason` |

**Standard payload keys (per D-07 / EventRepo convention):**
`old_status`, `new_status`, `actor`, `operation`,
`transition_at`. The `operation` field carries the literal string
`"assent_record"` for cross-substrate audit queries.

**`client_name` field:** carries the `actor` per the D-07
intentional duplication convention (same shape `StagedOpRepo`
uses).

**Anti-scope:** A.2 does NOT add an `assent.rejected` event. The
state machine has no `rejected` state (per L2). Non-ratification
is the implicit default (operator just doesn't run
`fbridge ratify`); there is no explicit rejection verb. Future
phases may add explicit rejection if operator UAT surfaces a need.

**Forward-looking caveat per FC-A2.7:** the audit-event story is
symmetric to `staged.*` in shape, distinct in naming, and
substrate-isolated by entity_type. Consumers subscribing to
`assent.*` are A.2-aware; consumers subscribing to `staged.*` see
no contamination from A.2 surfaces.

### L7 — Chat-side terminal SSE taxon `event: apply_complete`

**A.1 shipped 5 chat-side terminal taxa. A.2 adds a 6th:
`event: apply_complete`. The data payload shape below is the wire
contract.**

```
event: apply_complete
data: {
  "kind":            "apply_complete",
  "graph_intent_id": str,                # 12-char prefix
  "chain":           {<run_chain_steps output dict>},
  "stop_reason":     "apply_complete",
  "chat_regime":     "ratified_apply",
  "transport":       "sse",
}
```

**Emission site:** new dispatch branch in
`console/handlers.py:_chat_sse_response` that fires when the chat
prompt matches the `apply <graph_intent_id>` grammar (regex
`^apply\s+([a-f0-9]{12})\s*$` after L9's parse).

**Symmetric JSON-path envelope** (for the non-SSE chat path):
`chat_handler` JSON response gains an `apply_complete` top-level
key when the apply path fires. Mirrors A.1's preview-shape JSON +
SSE symmetry (L4).

**Failure-side taxa for the chat apply path** (per carve-out 4):

| Failure | SSE taxon | JSON envelope field |
|---|---|---|
| Unknown `graph_intent_id` | `event: error` (transport-error analog) | `error: {code: "assent_record_not_found", graph_intent_id: ...}` |
| AssentRecord in wrong state (e.g., already applied) | `event: error` | `error: {code: "assent_illegal_state", current_status: ...}` |
| Drift-invalidate at commit-node verify | `event: chain_aborted` (existing taxon) | `error: {code: "drift_invalid", graph_intent_id: ...}` |
| Chain step aborted mid-apply | `event: chain_aborted` (existing taxon) | unchanged from A.1's chain_aborted envelope |

The chain_aborted family is reused (no new taxon) per
`[[feedback-explicitly-unbound-vs-implicitly-rejected]]`: the
existing taxon already represents "chain failed during execution"
— adding `apply_chain_aborted` would duplicate semantics. Stage
1b verifies this reuse is honest (no semantic blur).

### L8 — `fbridge ratify` CLI surface

**New top-level Typer subcommand at `forge_bridge/cli/main.py`,
sibling to `chat` / `exec` / `run` / `flame-exec`. Signature
below is the contract.**

```python
@app.command("ratify")
def ratify_cmd(
    graph_intent_id: str = typer.Argument(
        ...,
        help="12-char graph-intent identifier from a prior chat preview",
    ),
    actor: str = typer.Option(
        "local",
        "--actor",
        help="Caller identity (free string; future SEED-AUTH integration point)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON result instead of Rich-rendered table",
    ),
) -> None:
    """Ratify a previously-emitted graph-intent and apply it.

    Atomic operation: writes the assent record (proposed → ratified
    transition), then invokes the shared store-and-replay substrate
    to execute the persisted chain (ratified → applied | failed
    transition). Result returned to stdout.

    Exit codes:
      0  apply succeeded (assent.applied event emitted)
      1  apply failed (any class — see envelope for code)
      2  daemon unreachable (transport error)
    """
```

**Failure-class enumeration for exit code 1** (per carve-out 6):

| Failure code | Cause | Envelope shape |
|---|---|---|
| `assent_record_not_found` | graph_intent_id resolves to no row | `{error: {code: ..., graph_intent_id: ...}}` |
| `assent_illegal_state` | record exists but already applied/failed | `{error: {code: ..., current_status: ..., graph_intent_id: ...}}` |
| `assent_write_failure` | DB write failure during ratify | `{error: {code: ..., reason: <str>}}` |
| `drift_invalid` | drift check failed at commit-node verify | `{error: {code: ..., graph_intent_id: ..., held_hash: ..., fresh_hash: ...}}` |
| `chain_aborted` | chain step aborted during apply | `{error: {code: ..., step_index: ..., step_text: ...}}` |

**Daemon transport (exit code 2):**

| Failure | Envelope shape |
|---|---|
| Daemon unreachable | `{error: {code: "daemon_unreachable", url: <str>, reason: <str>}}` |

**`--json` short-circuit (P-01 stdout purity):** when `--json` is
passed, the command emits ONLY the JSON envelope to stdout. Rich
rendering is suppressed. Matches the existing pattern across
other `fbridge` subcommands.

**Daemon dispatch:** the CLI sends `POST :9996/api/v1/ratify`
with body `{"graph_intent_id": str, "actor": str}`. The daemon
performs the ratify + apply atomically and returns the result
envelope. The endpoint is new; specified in L9 below.

**Cross-substrate UUID/ID confusion at the lookup boundary**
(per Stage 1b M7 plan-pick — R-A2.0(a) parallel-substrate
discipline). The CLI surface accepts a 12-char hex
`graph_intent_id`, NOT a UUID. Operator confusion (passing a
staged_operation UUID to `fbridge ratify`, or an assent_record
graph_intent_id to `forge_approve_staged`) is prevented at TWO
layers:

1. **CLI-side regex validation** — `^[a-f0-9]{12}$` rejects any
   input that is not 12 lowercase hex characters before daemon
   dispatch. UUID format (8-4-4-4-12 hex with dashes, 36 chars
   total) fails this regex; operator gets a CLI-side validation
   error.
2. **Daemon-side entity_type scoping** — `AssentRecordRepo.get_by_graph_intent_id`
   queries are scoped to `entity_type='assent_record'`. A
   12-char prefix matching a non-assent_record row would not
   resolve in this scope; returns None.

Combined effect: a 12-char hex string that happens to match the
prefix of a non-assent_record row's content_hash (low-probability
but not impossible at 48-bit prefix density) is treated as
`assent_record_not_found` — silent fall-through to that error
code rather than a distinguished `wrong_substrate_id` envelope.
Plan-pick rationale: the two-layer validation makes confusion
operationally unreachable in practice; a 4th error code for an
operationally-unreachable case would dilute the failure-class
table without operator benefit.

**Symmetric protection for `forge_approve_staged`:** the MCP
tool's `ApproveStagedInput.id` is validated as a UUID (per
`tools.py:198`); a 12-char graph_intent_id fails UUID parsing
and returns `bad_request`. The two substrates' approval surfaces
cannot cross-confuse at the wire-shape layer.

### L9 — Regime-3 modification + chat apply dispatch + ratify HTTP endpoint

**Three modifications to `console/handlers.py` + one to
`console/_chat_compile.py`. The exact disposition is the contract.**

**(a) `_chat_compile.py:run_compile_branch` — regime-3 branch
modification.**

When the branch reaches the `regime="compiled_mutating_preview"`
return path (currently at `_chat_compile.py:131-137` — 8 lines
including the multi-line `CompileBranchOutcome(...)` constructor),
the modification creates an AssentRecord via the repo and threads
the resulting `graph_intent_id` into both the preview shape and
the outcome dataclass.

**Session lifecycle** (per Stage 1b M2 absorption — matches the
closure pattern at `tools.py:209-235`):

```python
# In _chat_compile.py — replaces the existing regime-3 return at
# :131-137 with the AssentRecord-creating variant.
async with session_factory() as session:
    assent_repo = AssentRecordRepo(session)
    record = await assent_repo.propose(chain_steps=steps)
    await session.commit()  # caller owns commit per repo convention

# record.graph_intent_id is the 12-char prefix (per L3 + L4)
graph_intent_id = record.graph_intent_id

return CompileBranchOutcome(
    regime="compiled_mutating_preview",
    steps=steps,
    preview=build_preview_from_steps(steps, graph_intent_id),
    chain_body=None,
    compile_error=None,
    graph_intent_id=graph_intent_id,
    assent_record_id=record.id,
)
```

**`build_preview_from_steps` signature extension** (per Stage 1b
M1 absorption — verified actual name at `_chat_compile.py:73`):
the function shipped at A.1 has signature
`build_preview_from_steps(steps: list[str]) -> dict`. A.2 extends
to `build_preview_from_steps(steps: list[str],
graph_intent_id: Optional[str] = None) -> dict`. When
`graph_intent_id` is not None, the returned dict gains a
top-level `"graph_intent_id"` field (positioned alongside `kind`,
before `steps`, per L4 wire shape). When None, the existing 3-key
dict shape is preserved verbatim (preview shape unchanged for
non-mutating-preview emit paths — currently none in production
post-A.1, but the backward-compat default is conservative).

**Extension to `CompileBranchOutcome` dataclass:** two new fields
`graph_intent_id: Optional[str] = None` (None for non-mutating
regimes) and `assent_record_id: Optional[uuid.UUID] = None`
(None for non-mutating regimes). Default None preserves A.1
backward compat for the 5-field constructor calls in other
regimes.

**Session-passing for `run_compile_branch`:** the function
signature extends with a `session_factory` parameter (matching
the closure pattern `_approve_staged_impl` uses at
`tools.py:209-216`). The chat handler injects the daemon's
session factory. Tests inject mock factories. The `async with` +
`await session.commit()` discipline above is per the repo
convention — AssentRecordRepo (like StagedOpRepo) does NOT call
commit internally; caller owns transaction boundaries.

**(b) `handlers.py` chat apply dispatch grammar.**

Before A.1's existing regime-3/regime-2 dispatch, add a check:
if `chat_prompt.strip()` matches `^apply\s+([a-f0-9]{12})\s*$`,
route to the apply dispatch branch instead of compile.

```python
# In chat_handler (JSON path) and _chat_sse_response (SSE path):
_APPLY_GRAMMAR = re.compile(r"^apply\s+([a-f0-9]{12})\s*$")
_apply_match = _APPLY_GRAMMAR.match(chat_prompt.strip())
if _apply_match:
    graph_intent_id = _apply_match.group(1)
    return await _run_apply_branch(
        graph_intent_id=graph_intent_id,
        session_factory=session_factory,
        request_id=request_id,
        client_ip=client_ip,
        started=started,
        transport=("sse" if accept_sse else "json"),
    )
# ... else: existing macros / -> chain / compile dispatch ...
```

**`_run_apply_branch` is a new helper** in `_chat_compile.py`
sibling to `run_compile_branch`. It:

1. Resolves `graph_intent_id` via
   `AssentRecordRepo.get_by_graph_intent_id`. Not found →
   `event: error` taxon with code `assent_record_not_found`.
2. Validates record.status == "ratified". Wrong state →
   `event: error` taxon with code `assent_illegal_state`.
3. Invokes `run_chain_steps(steps=record.chain_steps, ...)`. The
   steps come from STORAGE, not from a fresh compile (R-A2.7
   store-and-replay).
4. On chain success: calls `assent_repo.mark_applied(...)`; emits
   `event: apply_complete`.
5. On chain failure: calls `assent_repo.mark_failed(...,
   reason="chain_aborted")`; emits `event: chain_aborted`.

**(c) New HTTP endpoint `POST /api/v1/ratify`** at
`console/handlers.py`. Signature:

```python
@router.post("/api/v1/ratify")
async def ratify_endpoint(request: Request) -> JSONResponse:
    """Atomic ratify + apply for fbridge ratify CLI.

    Body: {"graph_intent_id": str, "actor": str}

    Internally:
      1. AssentRecordRepo.ratify(graph_intent_id, actor=actor)
         (proposed → ratified)
      2. _run_apply_branch(graph_intent_id, ...) (ratified →
         applied | failed)
      3. Return the unified result envelope (apply result or error).
    """
```

The endpoint reuses `_run_apply_branch` from (b) for the apply
half — single substrate for both ratify+apply (CLI) and apply
alone (chat). The CLI path skips the chat-grammar dispatch entirely;
the chat path skips the ratify half (just apply).

**Rate-limit + body-validation discipline:** the new endpoint
inherits the existing rate-limit pattern from `chat_handler`
(IP-keyed) AND adds body-validation (graph_intent_id regex,
actor non-empty). Sub-questions are Stage 1b ammo, not L9-level.

### L10 — Apply flow: store-and-replay

**The chain executed at apply time IS the chain stored in
`AssentRecord.chain_steps` at propose time. NO recompile happens
between assent and apply.**

```python
# Inside _run_apply_branch (and reused by the ratify endpoint):
record = await assent_repo.get_by_graph_intent_id(graph_intent_id)
# ... validation ...

chain_result = await run_chain_steps(
    steps=record.chain_steps,  # ← from storage, not from re-compile
    tools=tools,
    mcp=mcp,
    request_id=request_id,
    client_ip=client_ip,
    started=started,
)
```

**Per R-A2.7 constitutional position:** the inferential authority
is bounded at compile time. The operator decides on the
ratified graph-intent; the apply runs the EXACT chain the operator
saw in the preview. No second LLM call. No re-compile sampling
noise. The authority chain is unbroken.

**Drift-invalidation at commit-node step (per R-A2.3 + L5):** when
`run_chain_steps` reaches the commit-node step, it invokes
`CommitNode.verify(held=manifest, fresh=manifest, assent=record)`.
The drift check compares the manifest's hash; the assent check
validates `record.status == "ratified"`. Drift-invalid OR
assent-invalid → CommitVerification.is_valid=False; `run_chain_steps`
aborts the chain and returns the abort envelope.

**Anti-scope:** A.2 does NOT add a re-compile fallback path. The
sync-apply common-case assumption is the design center per Thesis;
async-tolerant operator workflows (operator walks away, returns
hours later) fall outside A.2's scope per discuss-stage ruling.

### L11 — Migration `0009_assent_record.py`

**Alembic migration extending `ck_entities_type` CHECK from 20 →
21 entity_types by adding `'assent_record'`. Reuses the
`_entity_type_check(types)` helper pattern established at
`0005_phase4b_entity_types.py:62-64`. Analog mechanic to
`0003_staged_operation.py`; helper convention follows 0005 (the
last migration to touch `ck_entities_type`).**

**Substrate-grounding (verified 2026-05-28 against
`0005_phase4b_entity_types.py:31-59`):** the pre-A.2 baseline is
exactly 20 entity_types — `_ALL_ENTITY_TYPES =
tuple(sorted(_PRE_ORCH_ENTITY_TYPES + _ORCH_ENTITY_TYPES))` from
0005. Migrations 0006/0007/0008 create new tables
(`orchestration_lifecycle_state`,
`orchestration_promotion_ledger`,
`orchestration_compromise_ledger`) but do NOT modify
`ck_entities_type`. The orchestration_*_ledger names are TABLE
names, NOT entity_type discriminator values. Verified by reading
`0008_phase4b_orchestration_compromise_ledger.py` (creates a
standalone table; no `op.drop_constraint("ck_entities_type", ...)`
nor `op.create_check_constraint("ck_entities_type", ...)` call).

A.2's migration 0009 therefore extends from the 0005-locked
20-tuple to a 21-tuple by adding `'assent_record'`. Re-sorted
alphabetically.

```python
"""Assent record entity type — Phase A.2.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-28

Changes:
  entities
    - Extend ck_entities_type CHECK from 20 → 21 entity_types by
      adding 'assent_record' (alphabetically between 'asset' and
      'layer' in the sorted output).

Notes:
  EVENT_TYPES additions for assent.proposed/ratified/applied/failed
  are Python-side only — the events table has no CHECK constraint
  on event_type (verified against 0001_initial_schema.py).

  No data backfill — assent_record is a new entity type with zero
  existing rows.

  Helper pattern reused from 0005_phase4b_entity_types.py:62-64.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


# Pre-A.2 baseline — verified against 0005's _ALL_ENTITY_TYPES tuple.
# Migrations 0006/0007/0008 create standalone tables; ck_entities_type
# unchanged since 0005.
_PRE_A2_ENTITY_TYPES = (
    # 8 pre-orch (from 0003_staged_operation.py via 0005 inheritance):
    "asset",
    "layer",
    "media",
    "sequence",
    "shot",
    "stack",
    "staged_operation",
    "version",
    # 12 orch_* (from 0005_phase4b_entity_types.py):
    "orch_audit_report",
    "orch_capability_snapshot",
    "orch_execution_plan",
    "orch_generation_artifact",
    "orch_inputs_catalog",
    "orch_locked_intent",
    "orch_partial_fidelity_snapshot",
    "orch_pipeline_run",
    "orch_provenance_manifest",
    "orch_rule_snapshot",
    "orch_spec_convergence_trace",
    "orch_validation_report",
)

# A.2 adds 1 entity_type. Sorted form is canonical.
_POST_A2_ENTITY_TYPES = tuple(
    sorted(_PRE_A2_ENTITY_TYPES + ("assent_record",))
)


def _entity_type_check(types: tuple[str, ...]) -> str:
    """Mirrors the helper at 0005_phase4b_entity_types.py:62-64
    (last migration to touch ck_entities_type)."""
    quoted = ", ".join(f"'{t}'" for t in types)
    return f"entity_type IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_POST_A2_ENTITY_TYPES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_A2_ENTITY_TYPES),
    )
```

**Count discipline:** the `len(_PRE_A2_ENTITY_TYPES)` MUST be 20
(8 + 12); `len(_POST_A2_ENTITY_TYPES)` MUST be 21. Stage 1b
verifies these counts mechanically before sign-off. The
constraint string from `_entity_type_check(_POST_A2_ENTITY_TYPES)`
contains exactly 21 single-quoted identifiers separated by `, `.

**Verification harness for D3** (per Stage 1b F2 absorption):
the D3 acceptance test asserts the post-upgrade constraint
contains exactly 21 quoted entity_types AND includes
`'assent_record'`. The pre-upgrade / post-downgrade constraint
contains exactly 20 quoted entity_types AND does NOT include
`'assent_record'`. Mechanical count check closes the
substrate-grounding gap that surfaced in Stage 1b cycle 1.

**Per `[[feedback-brief-examples-as-behavioral-reference-shapes]]`
(Stage 1b F2 absorption):** the `_entity_type_check` helper from
0005 is the battle-tested topology; v2 honors that convention
rather than hand-writing the constraint string. Plan v1's literal
multi-line string drift was convention-reconstruction-from-recall;
v2 corrects to the helper-reuse pattern the migration lineage
already established.

### L12 — `decided_by` placeholder field

**`AssentRecord.decided_by` is a free-string field, populated by
`AssentRecordRepo.ratify(actor=...)`. Pre-auth default value
written by the CLI: literal string `"local"`. The `--actor` CLI
flag overrides for operators who distinguish workstations
informally.**

```python
# In ratify_cmd:
actor: str = typer.Option(
    "local",
    "--actor",
    help="Caller identity (free string; future SEED-AUTH "
         "integration point)",
),
```

**Per R-A2.8 + `[[feedback-explicitly-unbound-vs-implicitly-rejected]]`:**
the field is the explicit-deferral surface. SEED-AUTH-V1.5 (future
auth landing) will populate from authenticated identity; A.2
maintains the field shape so migration is just population, not
schema change.

**Validation:** non-empty after strip. Whitespace-only rejected at
CLI Typer layer (matches `forge_approve_staged` ApproveStagedInput
validator pattern at `tools.py:120-125`).

**Audit-event payload:** `decided_by` mirrored into
`assent.ratified` event payload (per L6); also mirrored into
`client_name` per D-07 intentional duplication convention.

### Minor locks

**MOL-1. `forge_bridge.__all__` unchanged.** A.2 ships substrate
+ extensions; nothing exported. Public surface stays at 19
symbols (carried unchanged across v1.4.x → v1.6 → v1.7 → A.1 →
A.2).

**MOL-2. `pyproject.toml` version stays at `1.4.1`.** A.2 is
patch-equivalent within the v1.7 milestone arc per CLAUDE.md
convention.

**MOL-3. No new external libraries.** All substrate built on shipped
infrastructure (CAR base, EventRepo, run_chain_steps, Typer,
existing test fixtures). Migration uses SQLAlchemy + Alembic
already in dependencies.

**MOL-4. `ContentAddressedRepo` docstring scope broadens** (per
FC-A2.2a writing-room lean → plan-lock option (i)). A.2's D2 amends
the module docstring at
`forge_bridge/store/content_addressed_repo.py:1` from "Phase 4B
orch_* semantic artifacts" to acknowledge the broader
content-addressed substrate pattern:

```python
"""Content-addressed repository base for immutable substrate
artifacts.

Used by:
  - forge_bridge/store/orch_*.py (Phase 4B orchestration
    artifacts)
  - forge_bridge/store/assent_record_repo.py (Phase A.2
    operator-decision substrate)
  - future content-addressed substrate may compose this base
"""
```

The class docstring at `:32-45` similarly broadens — replaces
"orch_*" specificity with substrate-pattern generality. Per FC-A2.2a:
addresses the docstring/implementation scope-mismatch archaeology
trap proactively.

**MOL-5. K=2 termination semantics preserved unchanged** (per
FC-A2.8). A.2 modifies regime-3 (preview emit + apply flow) and
adds the chat apply dispatch grammar. The K=2 canonical-recurrence
termination trigger lives in `complete_with_tools`
(router.py:639-662), which is the legacy-agentic substrate
primitive A.1 left in place for non-chat callers. A.2 does NOT
touch that surface. Coexistence architecture preserved.

**MOL-6. Chat handler regime-2 path unchanged.** A.2 modifies the
regime-3 branch and adds the apply-grammar dispatch; the regime-2
path (`compiled_non_mutating` chain via `chain_complete`) is
untouched. Stage 1b verifies regime-2 wire shape unchanged at
both `handlers.py:1119` (SSE) and `:1810` (JSON).

**MOL-7. `_format_sse_event` helper reused verbatim** for the new
`event: apply_complete` emission. No new SSE formatter primitive.

**MOL-8. Audit-event atomicity invariant** — `AssentRecordRepo`
status updates and event appends share the SAME AsyncSession
passed in at construction. Repo NEVER calls
`await self.session.commit()`. Mirrors `StagedOpRepo`'s atomicity
invariant per the same load-bearing reason (tamper-evident audit
gaps closed by atomicity).

**MOL-9. AssentRecord.from_dict / mirror-pattern.** Per
`StagedOperation` precedent at `staged_operations.py:432-462`
(`_to_staged_operation`), `AssentRecordRepo` ships an internal
`_to_assent_record(db: DBEntity) -> AssentRecord` static method.
Allocation via `__new__` + `BridgeEntity.__init__(metadata={})`
+ field assignment. Matches the Version pattern PATTERNS.md
documents.

**MOL-10. CLI `--json` short-circuits Rich (P-01 stdout purity).**
`fbridge ratify --json` emits ONLY the JSON envelope; Rich
rendering suppressed. Same pattern as `fbridge doctor --json`,
`fbridge graph list --json`, etc.

## Deliverables

Spec order matches expected commit sequence. Implementation hands
off in this order; commits land in roughly D1..D10 cadence per
`[[feedback-substrate-before-consumer-landing]]` — substrate
primitives land FIRST + are tested on their own commits before
consumer wiring rides.

### D1 — `AssentRecord` core dataclass

**File:** `forge_bridge/core/assent.py` (new)

**Substrate-first landing per
`[[feedback-substrate-before-consumer-landing]]`.** The primitive
lands and is tested on its own commit; repo + consumers ride
later.

**Changes:**

1. New module `forge_bridge/core/assent.py`. Exports `AssentRecord`
   (BridgeEntity subclass per L1 contract).
2. Override `entity_type` property to return literal
   `"assent_record"` (per the critical-pattern at
   `staged.py:82-84`).
3. Implement `to_dict()` per L1 14-key shape.
4. Implement `__repr__` per L1 shape.

**Acceptance:**

- `AssentRecord(graph_intent_id="abc123", chain_steps=["list shots", "commit"])`
  constructs with status="proposed" by default; other fields
  default None.
- `record.entity_type == "assent_record"` (NOT "assentrecord" —
  verifies the override).
- `record.to_dict()` returns a dict with exactly 14 keys
  (6 inherited + 8 added per L1).
- `to_dict()` serializes `decided_at` / `applied_at` via
  `.isoformat()` when not None; emits `None` when None.
- Importing `AssentRecord` from `forge_bridge.core.assent` works;
  importing from `forge_bridge` itself does NOT (verifying
  `__all__` discipline per MOL-1).

### D2 — `AssentRecordRepo` + CAR docstring broadening

**File:** `forge_bridge/store/assent_record_repo.py` (new) +
`forge_bridge/store/content_addressed_repo.py` (modified)

**Changes:**

1. New module `forge_bridge/store/assent_record_repo.py`. Exports
   `AssentRecordRepo`, `AssentRecordLifecycleError`, and
   `AssentRecordNotFound`. Implementation per L2.
2. Set `__entity_type__ = "assent_record"` and
   `__model__ = AssentRecord` ClassVars.
3. State machine + transition methods per L2 (`propose`,
   `ratify`, `mark_applied`, `mark_failed`).
4. Audit-event emission per L6 — composed `EventRepo`, shared
   session, `_TRANSITION_EVENTS` map.
5. Lookup methods: `get_by_graph_intent_id` (12-char prefix
   resolution), `list_pending` (status filter + pagination).
6. `_to_assent_record(db)` static mirror per MOL-9.
7. **Modify `content_addressed_repo.py:1-45`** — module docstring
   + class docstring broadened per MOL-4 / FC-A2.2a. Implementation
   bodies unchanged.

**Acceptance:**

- `await repo.propose(chain_steps=["list shots", "commit"])`
  returns AssentRecord with content_hash computed (12-char prefix
  = `record.graph_intent_id`), status="proposed".
- Calling `propose` twice with the same `chain_steps` returns the
  SAME row (CAR base's idempotent insert_if_absent); audit event
  emitted ONLY on first call.
- `await repo.ratify(graph_intent_id, actor="local")` transitions
  proposed → ratified; sets `decided_by="local"` + `decided_at` to
  current UTC; emits `assent.ratified` event on shared session.
- Calling `ratify` on a record already in "ratified" state raises
  `AssentRecordLifecycleError(from_status="ratified", to_status="ratified")`.
- Calling `ratify` on a graph_intent_id with no matching row
  raises `AssentRecordNotFound`.
- `mark_applied` transitions ratified → applied; sets
  `applied_at` + `apply_result`; emits `assent.applied` event.
- `mark_failed` transitions ratified → failed; sets `applied_at` +
  `apply_failure_reason`; emits `assent.failed` event; allows
  `reason` ∈ {"drift_invalid", "chain_aborted", "assent_invalid"}.
- `repo.update(...)` raises `ImmutableArtifactError` (CAR base
  unchanged — chain_steps body is immutable).
- `repo.delete(...)` raises `ImmutableArtifactError`.
- `await repo.get_by_graph_intent_id("nonexistent")` returns
  None.
- Audit events are on the SAME session — verified by querying
  events table within the same transaction before commit.
- `content_addressed_repo.py` module docstring at `:1` includes
  "assent_record_repo.py" in the Used-by list; class docstring
  generalized per MOL-4.

### D3 — Alembic migration `0009_assent_record.py`

**File:** `forge_bridge/store/migrations/versions/0009_assent_record.py`
(new)

**Changes:**

1. New revision `0009` per L11. `down_revision = "0008"`.
2. Upgrade: extend `ck_entities_type` CHECK to include
   `'assent_record'` (alphabetically between `'asset'` and
   `'layer'`).
3. Downgrade: revert to the pre-0009 constraint shape (preserving
   the post-0008 set).

**Acceptance:**

- `alembic upgrade head` from a `0008`-head DB applies cleanly;
  the constraint includes `assent_record`.
- `alembic downgrade -1` from `0009` reverts cleanly; the
  constraint excludes `assent_record`.
- Inserting a row with `entity_type='assent_record'` post-upgrade
  succeeds; same insert pre-upgrade (or post-downgrade) raises
  CHECK constraint violation.
- The constraint string is identical to L11 contract; verified
  by reading the constraint via `pg_constraint` after upgrade.

### D4 — `CommitNode.verify()` extension + `CommitVerification` fields + `CommitError` ASSENT_INVALID taxon

**File:** `forge_bridge/graph/commit.py` (modified)

**Substrate extension landing per
`[[feedback-substrate-before-consumer-landing]]`.** The verify
primitive lands and is tested on its own commit; consumer
adoption (`_engine.py` + `_step.py`) rides D5.

**Changes:**

1. Extend `CommitVerification` dataclass (`commit.py:90-94`) —
   add `assent_valid: bool = True` + `assent_record:
   Optional[AssentRecord] = None` fields per L5. Existing fields
   (`matched`, `drift_count`, `first_drift_index`) preserved
   verbatim.
2. Extend `CommitNode.verify()` signature (`commit.py:106`) — add
   `assent: Optional[AssentRecord] = None` kwarg per L5.
3. Implement assent-check body per L5: validates
   `assent.status == "ratified"` (only when `assent is not None`);
   constructs `CommitVerification` with both `matched` and
   `assent_valid` signals separate (no aggregate fold per L5
   plan-pick). Drift body preserved verbatim (element-by-element
   resolved_plan iteration).
4. Extend `CommitError` class (`commit.py:27-64`) — add
   `ASSENT_INVALID = "ASSENT_INVALID"` class constant; extend
   `__init__` with optional `graph_intent_id: str | None = None`
   kwarg; extend `to_error()` to surface `graph_intent_id` when
   `code == ASSENT_INVALID`.
5. Import `AssentRecord` from `forge_bridge.core.assent` (lazy
   import inside the verify body to avoid circular import — the
   class reference in the type annotation uses the string
   forward-reference form `Optional["AssentRecord"]`).

**Acceptance:**

- `node.verify(held, fresh)` (no assent kwarg) returns
  `CommitVerification(matched=<drift result>, drift_count=<n>,
  first_drift_index=<i>, assent_valid=True, assent_record=None)`
  — backward-compatible with the 4 existing test call sites.
- `node.verify(held, fresh, assent=record)` where
  `record.status="ratified"` returns
  `assent_valid=True, assent_record=record`. The drift body
  produces the same `matched`/`drift_count`/`first_drift_index`
  as the no-assent invocation.
- `node.verify(held, fresh, assent=record)` where
  `record.status="proposed"` returns
  `assent_valid=False, assent_record=record`. `matched` /
  `drift_count` unchanged from the no-assent invocation (drift
  and assent are independent signals; assent failure does NOT
  modify `matched`).
- `node.verify(held, fresh_mismatched, assent=record_ratified)`
  returns `matched=False, drift_count>=1, assent_valid=True`
  (drift fails; assent passes — independent signals).
- `node.verify(held, fresh_mismatched, assent=record_proposed)`
  returns `matched=False, drift_count>=1, assent_valid=False`
  (both fail independently).
- `CommitError.ASSENT_INVALID == "ASSENT_INVALID"`.
- `CommitError("ASSENT_INVALID", "msg", graph_intent_id="abc123").to_error()`
  returns `{"type": "ASSENT_INVALID", "message": "msg",
  "graph_intent_id": "abc123"}`.
- `CommitError("PLAN_STATE_DRIFT", "msg", drift_count=2,
  first_drift_index=1).to_error()` returns the existing shape
  unchanged (verifies the new `graph_intent_id` field is
  conditional on `code == ASSENT_INVALID`).
- The 4 existing `tests/graph/test_commit.py:259/268/279/303`
  tests pass unchanged — they assert on
  `verification.matched` / `verification.drift_count` /
  `verification.first_drift_index`, all of which retain their
  shipped semantics; the new fields have safe defaults.

### D5 — `run_chain_steps` + `_step.py` adoption of AssentRecord propagation

**Files:** `forge_bridge/console/_engine.py` (modified) +
`forge_bridge/console/_step.py` (modified)

**Substrate-consumer landing — first adoption of D4's primitive
extension.** Per substrate-before-consumer discipline: D4 ships
the primitive on its own commit; D5 ships the consumer adoption
on its own commit. Substantive change but isolated to two
files.

**Changes:**

1. **Extend `_engine.py:run_chain_steps` signature** — add
   optional `assent_record: Optional[AssentRecord] = None`
   parameter (kwarg-only per the existing signature's `*` star).
   Default None preserves backward compat for the regime-2
   non-mutating chain path + any other callers.
2. **Propagate `assent_record` from `run_chain_steps` to the
   step executor** — pass it as a kwarg to the step-execution
   call. Specific propagation path: `run_chain_steps` loops over
   steps; when it dispatches a step it currently passes
   `(step_text, manifest, ...)` to the step executor; A.2 also
   passes `assent_record` to the step executor when the step is
   a commit-step (`is_commit_step(step_text)` is True).
3. **Extend `_step.py` step executor** — accept the new
   `assent_record` kwarg; pass it into the
   `CommitNode().verify(...)` call site at line 799 (becomes
   `CommitNode().verify(manifest, fresh, assent=assent_record)`).
4. **Extend `_step.py:798-808` branch logic** — after the
   existing `if not verification.matched:` drift-error branch,
   add a sibling `if not verification.assent_valid:` branch
   returning a CommitError envelope with ASSENT_INVALID code +
   `graph_intent_id=assent_record.graph_intent_id`:
   ```python
   verification = CommitNode().verify(manifest, fresh, assent=assent_record)
   if not verification.matched:
       return {"error": CommitError(
           CommitError.PLAN_STATE_DRIFT,
           "Mutation plan no longer matches current state.",
           step_index=step_index,
           step_text=step_text,
           drift_count=verification.drift_count,
           first_drift_index=verification.first_drift_index,
       ).to_error()}
   if assent_record is not None and not verification.assent_valid:
       return {"error": CommitError(
           CommitError.ASSENT_INVALID,
           "AssentRecord is not in ratified state.",
           step_index=step_index,
           step_text=step_text,
           graph_intent_id=assent_record.graph_intent_id,
       ).to_error()}
   ```
   The assent-check branch fires ONLY when `assent_record is not
   None` (preserves preview-only path semantics unchanged).

**Acceptance:**

- `run_chain_steps(steps=[...], tools=..., mcp=..., ..., assent_record=None)`
  preserves A.1 behavior verbatim (regime-2 non-mutating path).
- `run_chain_steps(steps=[..., "commit"], ..., assent_record=record_ratified)`
  reaches the commit-step + verify call; verify succeeds; chain
  proceeds to apply.
- `run_chain_steps(steps=[..., "commit"], ..., assent_record=record_proposed)`
  reaches the commit-step + verify call; assent_valid=False;
  chain aborts with error envelope code=ASSENT_INVALID +
  graph_intent_id populated.
- `run_chain_steps(steps=[..., "commit"], ..., assent_record=None)`
  reaches the commit-step + verify call WITH no assent; verify
  produces `assent_valid=True` (safe default for the kwarg);
  chain proceeds. **(Defensive default for the kwarg surface.
  No A.1 caller exercises this combination — A.1's regime-3
  short-circuits at `run_compile_branch` (`_chat_compile.py:130-137`)
  BEFORE reaching `run_chain_steps`; A.2's apply path passes
  `assent_record` explicitly via `_run_apply_branch`. Tests
  exercise this case directly for kwarg-default coverage.)**
- Existing `tests/console/test_chat_handler.py` +
  `tests/console/test_pr30_chain.py` etc. pass unchanged
  (regime-2 chain path doesn't touch the new kwarg; regime-3
  preview path doesn't reach `run_chain_steps` at all under
  both A.1 and A.2).
- `_step.py:798-808` source-line for the existing drift branch
  remains structurally at the same position; the new
  assent-check branch is appended below it.

### D6 — Regime-3 modification in `_chat_compile.py`

**File:** `forge_bridge/console/_chat_compile.py` (modified)

**Changes:**

1. Extend `CompileBranchOutcome` dataclass (`_chat_compile.py:18`)
   — add `graph_intent_id: Optional[str] = None` +
   `assent_record_id: Optional[uuid.UUID] = None` fields per L9(a).
   Default None preserves backward compat for non-mutating regimes.
2. Modify `run_compile_branch` signature to accept a
   `session_factory` parameter (matches
   `_approve_staged_impl`'s pattern at `tools.py:209-216`).
3. Modify the `regime="compiled_mutating_preview"` branch (around
   `_chat_compile.py:131-133`) per L9(a) body — invoke
   `AssentRecordRepo.propose`, populate `graph_intent_id` +
   `assent_record_id` on the outcome.
4. Extend `_build_preview` (or its equivalent — verify against
   actual A.1 module structure) to accept + thread the
   `graph_intent_id` into the preview dict per L4 wire-shape.

**Acceptance:**

- A regime-3 invocation (graph contains commit-node) returns a
  `CompileBranchOutcome` with `regime="compiled_mutating_preview"`,
  `graph_intent_id` populated (12-char hex), `assent_record_id`
  populated (UUID), and `preview` populated with the L4 shape
  extended with `graph_intent_id`.
- A regime-2 invocation (no commit-node) returns an outcome with
  `graph_intent_id=None` and `assent_record_id=None`.
- Same regime-3 prompt invoked twice produces the SAME
  `graph_intent_id` (CAR idempotency; both invocations resolve
  to the same AssentRecord row).
- The session injected via `session_factory` is closed cleanly
  after the propose call (caller owns the session lifecycle).

### D7 — Chat apply dispatch + `event: apply_complete` + ratify HTTP endpoint

**File:** `forge_bridge/console/handlers.py` (modified) +
`forge_bridge/console/_chat_compile.py` (extended)

**Changes:**

1. Add the `_APPLY_GRAMMAR` regex constant per L9(b) at module
   top of `handlers.py` (or `_chat_compile.py` if better-located).
2. Add the apply-dispatch check in BOTH chat paths:
   - `chat_handler` (JSON path) — check prompt against
     `_APPLY_GRAMMAR` before macro / `->` chain / compile dispatch.
   - `_chat_sse_response` (SSE path) — same check, same position
     in dispatch chain.
3. New `_run_apply_branch(...)` helper in `_chat_compile.py` per
   L9(b) body — resolves graph_intent_id, validates status,
   invokes `run_chain_steps` against `record.chain_steps`,
   transitions `assent_record` via `mark_applied` /
   `mark_failed`, emits the appropriate SSE taxa.
4. New `event: apply_complete` SSE emission per L7 wire shape.
5. New JSON path `apply_complete` envelope field per L7.
6. Failure-side taxa per L7 — `event: error` for record-not-found
   / illegal-state; `event: chain_aborted` (existing) for
   drift-invalid / chain-step abort.
7. New `POST /api/v1/ratify` endpoint per L9(c) — body validation
   + ratify + apply atomic dispatch + result envelope.

**Acceptance:**

- Chat prompt `"apply 4bd83c2f1abc"` (matching grammar) routes
  through `_run_apply_branch`; if record exists + ratified, runs
  the stored chain via `run_chain_steps`; emits
  `event: apply_complete` on SSE / populates `apply_complete`
  envelope on JSON.
- Chat prompt `"apply nonexistent12"` (matching grammar but no
  record) returns `event: error` (SSE) / `error` envelope (JSON)
  with code `assent_record_not_found`.
- Chat prompt `"apply 4bd83c2f1abc"` where record is in
  `proposed` state returns `event: error` / `error` envelope
  with code `assent_illegal_state`.
- Chat prompt `"apply  ABC123XYZ12"` (invalid grammar — uppercase
  hex) does NOT match `_APPLY_GRAMMAR`; falls through to existing
  dispatch (likely macros or `compile` path).
- `POST /api/v1/ratify` with body `{"graph_intent_id":
  "4bd83c2f1abc", "actor": "local"}` against a proposed record
  ratifies + applies atomically; returns 200 + apply envelope.
- `POST /api/v1/ratify` against an unknown graph_intent_id returns
  HTTP 404 + envelope `{error: {code: "assent_record_not_found", ...}}`.
- `POST /api/v1/ratify` against an already-applied record returns
  HTTP 409 + envelope `{error: {code: "assent_illegal_state",
  current_status: "applied"}}`.
- `POST /api/v1/ratify` with body missing `graph_intent_id`
  returns HTTP 400 + structured validation error.
- A.1's 5 chat-side terminal taxa fire unchanged in their existing
  paths (regime-2 chain_complete; regime-3 preview_emitted;
  compile_error; chain_aborted; compile_complete).
- Stage 2 grep table: `event: apply_complete` appears ONLY in
  `handlers.py` (or `_chat_compile.py`); not in any other module.
- Stage 2 grep table: `_APPLY_GRAMMAR` regex appears in EXACTLY
  ONE module (the dispatch home — `_chat_compile.py` recommended).

### D8 — `fbridge ratify` CLI subcommand

**File:** `forge_bridge/cli/main.py` (modified)

**Changes:**

1. Add `@app.command("ratify")` subcommand per L8 signature.
2. Body: validate `graph_intent_id` against `^[a-f0-9]{12}$`
   regex; reject whitespace-only `actor`; construct request body;
   send `POST {daemon_url}/api/v1/ratify`.
3. Handle response: emit Rich table (default) or JSON envelope
   (`--json`); set exit code per L8 failure classes.
4. Handle daemon transport errors per L8 exit code 2.
5. **No state-machine logic in CLI** — the CLI is a thin shell
   over the daemon's `/api/v1/ratify` endpoint.

**Acceptance:**

- `fbridge ratify 4bd83c2f1abc` against a proposed record:
  exit code 0; emits the apply result.
- `fbridge ratify 4bd83c2f1abc` against an unknown id:
  exit code 1; envelope code `assent_record_not_found`.
- `fbridge ratify 4bd83c2f1abc` against an already-applied
  record: exit code 1; envelope code `assent_illegal_state`.
- `fbridge ratify INVALID_FORMAT` (not 12-char hex): exit code 1;
  CLI-side validation error envelope (before daemon dispatch).
- `fbridge ratify 4bd83c2f1abc --actor jdoe` populates
  `decided_by="jdoe"` in the resulting AssentRecord.
- `fbridge ratify 4bd83c2f1abc --actor "  "` (whitespace-only):
  exit code 1; CLI-side validation error.
- `fbridge ratify 4bd83c2f1abc --json` emits ONLY the JSON
  envelope to stdout (Rich rendering suppressed).
- `fbridge ratify 4bd83c2f1abc` with daemon down: exit code 2;
  envelope code `daemon_unreachable`.
- `fbridge ratify --help` shows the locked help text per L8.

### D9 — Tests

**Files:**

- `tests/core/test_assent.py` (new)
- `tests/store/test_assent_record_repo.py` (new)
- `tests/store/test_migration_0009.py` (new)
- `tests/graph/test_commit_assent.py` (new) — extends existing
  `tests/graph/test_commit.py` coverage with assent-passing
  cases
- `tests/console/test_chat_apply_dispatch.py` (new)
- `tests/console/test_ratify_endpoint.py` (new)
- `tests/cli/test_ratify_cmd.py` (new)
- `tests/integration/test_a2_ratify_apply_flow.py` (new) —
  end-to-end happy path

**Coverage targets:**

- D1 acceptance criteria — all in `test_assent.py`.
- D2 acceptance criteria — all in `test_assent_record_repo.py`.
- D3 acceptance criteria — all in `test_migration_0009.py`
  (uses Alembic test helpers).
- D4 acceptance criteria — assent-extending tests in
  `test_commit_assent.py`; existing `tests/graph/test_commit.py`
  unchanged.
- D5 acceptance — `_engine.py` + `_step.py` adoption in
  `test_engine_assent_propagation.py` +
  `tests/console/test_step_assent_branch.py`.
- D6+D7+D8 acceptance — split across `test_chat_apply_dispatch.py`
  (chat path), `test_ratify_endpoint.py` (HTTP endpoint),
  `test_ratify_cmd.py` (CLI surface).
- End-to-end happy path — `test_a2_ratify_apply_flow.py` covers
  the full propose → ratify → applied flow against a real
  test DB, with mocked LLM compile returning a deterministic
  graph-intent.

**Per `[[feedback-mock-three-tier]]`:** mock the LLM (stub
shape — compile_intent returns canned chain_steps); mock the
session_factory in unit tests (contract-enforcer for repo
acceptance); use a real test DB in integration tests
(runtime-environment for migration + end-to-end). Each tier
matched to what the test must constrain.

### D10 — Docs + Phase close cursor

**Files:**

- `docs/CHAT.md` (modified) — add the apply-dispatch grammar +
  `event: apply_complete` terminal taxon to the existing chat-regimes
  reference. Cross-link to AssentRecord substrate.
- `docs/RATIFICATION.md` (new) — operator-facing reference for
  `fbridge ratify` + the propose → ratify → apply flow + the
  4 audit-event taxa + the failure-class envelope shapes.
- `docs/VOCABULARY.md` (modified) — add `assent_record` /
  `graph_intent_id` / `ratification` to the canonical vocabulary
  per project convention.
- `CLAUDE.md` (modified) — update the "Current State" section
  to reflect A.2 closure + describe the assent_record substrate
  briefly + mention the `fbridge ratify` CLI alongside other
  daily-launch surfaces.
- `.planning/phases/A.2-thread-a-ratification-enforced-apply/A.2-CLOSE.md`
  (new) — phase close cursor per A.1 precedent.

**Acceptance:**

- `docs/RATIFICATION.md` covers: the propose → ratify → apply
  flow; the `fbridge ratify <graph_intent_id>` CLI invocation;
  exit codes; the chat-side `apply <graph_intent_id>` grammar;
  the 4 `assent.*` audit events; the constitutive distinction
  from `staged_operation` (one-paragraph note).
- `docs/CHAT.md` extends the L4 preview shape doc with the
  `graph_intent_id` field; adds `event: apply_complete` to the
  terminal-taxa table; documents the apply-dispatch grammar.
- `docs/VOCABULARY.md` entry for `assent_record` aligns with the
  canonical-vocabulary template (entity definition + traits +
  relationships note).
- `CLAUDE.md` "Current State" section reflects A.2 shipped.
- A.2-CLOSE.md captures: methodology candidates from cycle
  archaeology; deferred items; surface inventory of what
  shipped + what's open; cross-link to discuss + plan.

## Test plan

Acceptance gate for A.2 implementation:

1. All tests in D9 pass.
2. Existing chat test suite passes unchanged
   (`tests/console/test_chat_handler.py`,
   `tests/console/test_chat_handler_sse.py`,
   `tests/console/test_pr30_chain.py`,
   `tests/console/test_pr33_macros.py`,
   `tests/console/test_pr40_exec.py`,
   plus A.1's chat-compile suite).
3. `tests/llm/test_complete_with_tools.py` passes unchanged —
   the legacy-agentic executor is untouched (MOL-5).
4. `tests/graph/test_commit.py` (A.1's drift-only tests) passes
   unchanged — the optional `assent` kwarg preserves backward
   compat.
5. Existing `tests/store/test_staged_operations*.py` passes
   unchanged — `staged_operation` substrate untouched per
   R-A2.0(a).
6. PR22 mechanical compliance test (`tests/test_tool_contract_enforcement.py`)
   reports the same passing count — A.2 does NOT add MCP tools.
7. `fbridge doctor` passes unchanged (includes Console, MCP,
   Flame, State WS, postgres, graph_store rows).
8. Live smoke test: `fbridge chat "list shots"` produces a
   `chain_complete` response (regime-2 wet end-to-end; A.1
   regression check).
9. Live smoke test: `fbridge chat "rename shots in 30sec 21 with
   suffix _v002 -> commit"` produces a `preview_emitted`
   response with the preview dict + `graph_intent_id` populated.
10. Live smoke test: `fbridge ratify <graph_intent_id>`
    successfully ratifies + applies; exit code 0; result envelope
    matches L8 success shape.
11. Live smoke test: chat-driven apply path —
    `fbridge chat "apply <graph_intent_id>"` against a ratified
    record emits `event: apply_complete` (verified via SSE
    inspection) and applies the chain.
12. Live smoke test: chat-driven apply path against unknown id
    returns `event: error` with code `assent_record_not_found`.
13. Live smoke test: drift-invalidate path —
    ratify, then mutate the chain's substrate context, then
    apply — should fail with code `drift_invalid`.

## Doc plan

Acceptance gate for A.2 docs:

1. **Create `docs/RATIFICATION.md`** per D10 sections.
2. **Modify `docs/CHAT.md`** per D10 — add `graph_intent_id` to
   preview shape, `event: apply_complete` to terminal-taxa
   table, apply-dispatch grammar.
3. **Modify `docs/VOCABULARY.md`** per D10 — `assent_record` +
   `graph_intent_id` + `ratification` entries.
4. **Modify `CLAUDE.md`** per D10 — "Current State" reflects A.2
   shipped; brief substrate mention; `fbridge ratify` named
   alongside other CLI surfaces.

## File change manifest

**New files (15 files):**

- `forge_bridge/core/assent.py` — `AssentRecord` dataclass (D1)
- `forge_bridge/store/assent_record_repo.py` — repo + transition
  methods + lookups (D2)
- `forge_bridge/store/migrations/versions/0009_assent_record.py` —
  Alembic migration (D3)
- `tests/core/test_assent.py` (D9)
- `tests/store/test_assent_record_repo.py` (D9)
- `tests/store/test_migration_0009.py` (D9)
- `tests/graph/test_commit_assent.py` (D9)
- `tests/console/test_engine_assent_propagation.py` (D9 — new
  per F1 cascade)
- `tests/console/test_step_assent_branch.py` (D9 — new per F1
  cascade)
- `tests/console/test_chat_apply_dispatch.py` (D9)
- `tests/console/test_ratify_endpoint.py` (D9)
- `tests/cli/test_ratify_cmd.py` (D9)
- `tests/integration/test_a2_ratify_apply_flow.py` (D9)
- `docs/RATIFICATION.md` (D10)
- `.planning/phases/A.2-thread-a-ratification-enforced-apply/A.2-CLOSE.md` (D10)

**Modified files (10 files):**

- `forge_bridge/store/content_addressed_repo.py` — module + class
  docstrings broadened per MOL-4 / FC-A2.2a (D2); implementation
  unchanged.
- `forge_bridge/graph/commit.py` — `CommitVerification` gains
  `assent_valid` + `assent_record` fields; `CommitNode.verify`
  signature gains optional `assent` kwarg; assent-check body
  added; `CommitError` gains `ASSENT_INVALID` code constant +
  optional `graph_intent_id` kwarg + `to_error()` extension
  (D4).
- `forge_bridge/console/_engine.py` — `run_chain_steps` signature
  gains optional `assent_record` kwarg; propagates to step
  executor when current step is a commit-step. **Moved from
  NOT-modified (v1) to modified (v2) per Stage 1b F1 cascade.**
  (D5)
- `forge_bridge/console/_step.py` — step executor accepts
  `assent_record` kwarg; passes `assent=assent_record` into
  `CommitNode().verify(...)` at line 799; adds new
  `if not verification.assent_valid` branch after existing
  drift branch returning `CommitError(ASSENT_INVALID, ...,
  graph_intent_id=...)`. **Moved from NOT-modified (v1) to
  modified (v2) per Stage 1b F1 cascade.** (D5)
- `forge_bridge/console/_chat_compile.py` — `CompileBranchOutcome`
  extended with `graph_intent_id` + `assent_record_id` fields;
  `run_compile_branch` signature gains `session_factory`;
  regime-3 branch creates AssentRecord + populates new fields;
  `build_preview_from_steps` signature extended with optional
  `graph_intent_id` parameter; new `_run_apply_branch` helper
  (D6, D7).
- `forge_bridge/console/handlers.py` — apply-dispatch grammar
  check added to BOTH chat paths; `event: apply_complete`
  emission + JSON envelope field; new `POST /api/v1/ratify`
  endpoint (D7).
- `forge_bridge/cli/main.py` — `fbridge ratify` subcommand
  added (D8).
- `docs/CHAT.md` — preview shape + terminal-taxa + apply-grammar
  additions (D10).
- `docs/VOCABULARY.md` — `assent_record` / `graph_intent_id` /
  `ratification` entries (D10).
- `CLAUDE.md` — "Current State" reflects A.2 shipped (D10).

(Manifest re-count for v3 honesty: 15 new + 10 modified = 25
touched files. Includes the 2 new test files for D5 cascade
coverage + the 2 newly-modified files [_engine.py + _step.py]
that v1 incorrectly placed in NOT-modified. v2 absorbed M4 on
the new-files heading but left modified-files heading at "9";
v3 sweeps the sibling per
`[[feedback-sibling-check-before-fix-scope]]`.)

**Files NOT modified (load-bearing preservation; Stage 1b
verifies):**

- `forge_bridge/__init__.py` — public `__all__` unchanged at 19
  per MOL-1.
- `pyproject.toml` — no version bump per MOL-2.
- `forge_bridge/core/staged.py` — `StagedOperation` unchanged
  (R-A2.0(a) parallel substrate; bridge-as-bookkeeper invariant
  preserved verbatim).
- `forge_bridge/store/staged_operations.py` — `StagedOpRepo`
  unchanged (parallel substrate).
- `forge_bridge/mcp/tools.py` — four `forge_*_staged` tools
  unchanged (consumer-side propose pattern preserved).
- `forge_bridge/llm/router.py` — `compile_intent` /
  `complete_with_tools` / `CompileError` family / K=2 termination
  / `_in_tool_loop` ContextVar all unchanged. MOL-5 preserves
  the legacy-agentic substrate.
- `forge_bridge/llm/_adapters.py` — unchanged.
- `forge_bridge/graph/mutation.py` — `MutationManifest` etc.
  unchanged. A.2 does not construct or validate manifests
  outside the `commit.verify` path.
- `forge_bridge/console/_chain_parse.py` — PR30 unchanged.
- `forge_bridge/console/_param_extract.py` — PR28 unchanged.
- `forge_bridge/console/_tool_filter.py` — PR14 / PR21 unchanged.
- `forge_bridge/console/_macros.py` — unchanged.
- `forge_bridge/console/_rate_limit.py` — unchanged (new
  endpoint inherits the existing rate-limit pattern).

## Implementation guidance — coexistence + substrate-discipline watch

Per the framing: A.2 is **substrate addition + consumer
extension**, not substrate replacement. Two parallel substrates
coexist post-A.2 (`staged_operation` + `assent_record`); the
chat-handler's three regimes from A.1 remain (no 4th regime is
added — apply-dispatch is a SIDEBAND grammar check, not a regime
modification).

> **Per `[[feedback-substrate-coherence-revealed-retrospect]]`
> (FC-A2.1):** the two-substrates shape may converge under a
> future unified "authorized-operation" pattern. A.2 does NOT
> pre-answer that future motion. Future-phase pressure point;
> not an A.2 design choice.

### What to PRESERVE (substrate parallel-coexistence)

- **`staged_operation` substrate** — `forge_bridge/core/staged.py`,
  `forge_bridge/store/staged_operations.py`, four `forge_*_staged`
  MCP tools. Bridge-as-bookkeeper invariant intact. Consumer
  (projekt-forge in production) continues to propose via
  consumer-owned `forge_stage_*` tools; bridge approval surface
  unchanged.
- **`complete_with_tools` body in `router.py`** — legacy-agentic
  substrate. K=2 termination, terminal taxa, OrchestrationTerminationEnvelope.
  No production consumers post-A.1 (test consumers only); MOL-5
  preserves the substrate primitive.
- **A.1's compile + preview substrate** — `compile_intent`,
  `CompileError` family, `graph_contains_commit_node`,
  `_chat_compile.py` (regime enum + `run_compile_branch`).
  A.2 EXTENDS the regime-3 branch; does NOT replace or
  restructure.
- **A.1's 5 chat-side terminal taxa** — emission sites unchanged;
  failure-side preserved unchanged.
- **`ContentAddressedRepo` implementation** — generic base class.
  Only docstring broadens (MOL-4); body unchanged.

### What to EXTEND (additive surface)

- `CommitNode.verify()` signature — optional `assent` kwarg.
  Drift-only callers unchanged.
- `CommitVerification` dataclass — 2 new fields with safe defaults
  (`assent_valid`, `assent_record`). Existing 3 fields (`matched`,
  `drift_count`, `first_drift_index`) preserved verbatim.
- `CommitError` class — new `ASSENT_INVALID` code constant +
  optional `graph_intent_id` kwarg + `to_error()` extension. The
  3 existing code constants preserved verbatim.
- `run_chain_steps` signature (`_engine.py`) — optional
  `assent_record` kwarg; propagates to step executor for
  commit-step calls.
- `_step.py` step executor — optional `assent_record` kwarg;
  passes into `CommitNode().verify(...)` at line 799; new
  `if not verification.assent_valid` branch after existing drift
  branch.
- `CompileBranchOutcome` dataclass — 2 new fields with safe
  defaults.
- `run_compile_branch` signature — new `session_factory` parameter.
- `build_preview_from_steps` signature — optional `graph_intent_id`
  parameter.
- Preview wire shape (L4) — `graph_intent_id` field added.
- Chat-side SSE terminal taxa — 6th taxon `event: apply_complete`
  added.

### What to ADD (new substrate)

- `AssentRecord` dataclass + `AssentRecordRepo` repository +
  Alembic migration (D1, D2, D3).
- `_run_apply_branch` helper (D7).
- `_APPLY_GRAMMAR` regex + dispatch check (D7).
- `POST /api/v1/ratify` endpoint (D7).
- `fbridge ratify` CLI subcommand (D8).
- 4 `assent.*` audit-event types (L6 — Python-side strings; no
  DB CHECK constraint required).

### Stage 2 grep table (for the implementation-review pass)

| Identifier | Allowed locations post-A.2 | Forbidden locations |
|---|---|---|
| `AssentRecord` | `core/assent.py` (definition), `store/assent_record_repo.py`, `graph/commit.py` (kwarg type), test files, doc files | — |
| `AssentRecordRepo` | `store/assent_record_repo.py` (definition), `_chat_compile.py`, `handlers.py` (ratify endpoint), `cli/main.py` (via daemon), test files | — |
| `assent_record` (entity_type literal) | `store/assent_record_repo.py` (`__entity_type__`), `migrations/versions/0009_assent_record.py`, `models.py` (CHECK after migration), test files | other entity_type discriminator sites |
| `graph_intent_id` | `core/assent.py`, `store/assent_record_repo.py`, `_chat_compile.py`, `handlers.py`, `cli/main.py`, `docs/RATIFICATION.md`, `docs/CHAT.md`, test files | — |
| `_APPLY_GRAMMAR` | `_chat_compile.py` (definition + dispatch use) | other modules (verifies single-home discipline) |
| `_run_apply_branch` | `_chat_compile.py` (definition), `handlers.py` (caller), `tests/console/test_chat_apply_dispatch.py` | other modules |
| `event: apply_complete` | `handlers.py` (emission site) + `_chat_compile.py` (data construction); `docs/CHAT.md` (reference) | other modules |
| `assent.proposed` / `.ratified` / `.applied` / `.failed` | `store/assent_record_repo.py` (emission), test files, `docs/RATIFICATION.md` | other modules |
| `staged_operation` (entity_type) | preserved unchanged at original sites | A.2-introduced files (verifies parallel-substrate discipline; no cross-contamination) |
| `StagedOpRepo` | preserved at original site; imported only by existing consumers | A.2-introduced files (verifies parallel-substrate discipline) |
| `forge_*_staged` MCP tool names | `mcp/tools.py` (preserved unchanged) | A.2-introduced files |

**The discipline:** A.2's job is to add the assent_record
substrate + the apply-dispatch surface WITHOUT touching the
staged_operation substrate. Stage 1b verifies the grep table
mechanically — same precedent as A.1's grep-table closure.

## Dependencies and sequencing

- **Blocks:** A.3 (hardening) — A.3's scope depends on A.2's
  shape. Cannot start until A.2's ratify substrate + apply path
  are locked.
- **Blocked by:** Nothing. A.1's substrate is shipped + closed at
  commit `242b8e9`; A.2's discuss is ratified + committed at
  `37e7dcb`.
- **Parallel with:** Phase-4b parallel track (orch_* artifacts).
  Architecturally orthogonal — phase-4b is in
  `forge_bridge/store/orch_*.py`; A.2's only contact with
  phase-4b is the shared `ContentAddressedRepo` base class
  (which A.2 reuses without modifying). Per
  `[[feedback-substrate-coherence-revealed-retrospect]]`: any
  future evolution of the CAR pattern needs to be honest about
  both consumer surfaces.

**D-phase landing order (substrate-first):**

```
D1 (AssentRecord)
   ↓
D2 (AssentRecordRepo + CAR docstring) ─→ D3 (migration 0009)
   ↓                                       ↓
   ↓                                       ↓ (D3 must land BEFORE D7's
   ↓                                       ↓  POST /api/v1/ratify endpoint
   ↓                                       ↓  can hit the DB cleanly)
   ↓                                       ↓
D4 (CommitNode.verify + CommitVerification fields + CommitError ASSENT_INVALID)
   ↓                                       ↓
D5 (_engine.py + _step.py adoption — first consumer)
   ↓                                       ↓
D6 (regime-3 modification in _chat_compile.py)
   ↓                                       ↓
D7 (apply dispatch + ratify endpoint + apply_complete) ←┘
   ↓
D8 (fbridge ratify CLI)
   ↓
D9 (tests — written incrementally per D1..D8, finalized as a wave)
   ↓
D10 (docs + close cursor)
```

**Dependency edges:**

- D1 + D4 are independent substrate-level commits (no
  inter-dependencies beyond import edges). D2 depends on D1
  (AssentRecord type needed for `__model__` ClassVar). D3
  depends on D2 (migration deploys the entity_type the repo
  uses).
- D5 depends on D4 (consumes the new `assent` kwarg + the new
  `assent_valid` field + the `ASSENT_INVALID` code constant).
- D6 depends on D1, D2, D3, D5 (regime-3 creates AssentRecord
  rows via the propose path; migration must be applied; D5
  enables apply path to consume the assent record at commit-node
  verify).
- D7 depends on D5, D6 (apply path consumes the AssentRecord
  shape regime-3 produces; ratify endpoint reuses the apply
  branch).
- D8 depends on D7 (CLI is thin shell over the `/api/v1/ratify`
  endpoint).
- D9 tests are written alongside each Dn but the integration
  test waits for D8.
- D10 docs + close follow D8's completion.

## Stage 1b checklist

Items DT (or substitute reviewer) should verify before this spec
clears for implementation handoff:

- [ ] **Locks L1-L12 + MOL-1..MOL-10 are mutually consistent
  and exhaustive.** Any scope question that could surface during
  implementation has an answer in a Lock, a Minor Lock, or is
  explicitly out of scope.
- [ ] **L1 dataclass shape is sweep-complete.** 8 added fields
  per L1 contract; 14 keys in `to_dict()` total (6 inherited +
  8 added). Verified against `StagedOperation` analog (8 added
  fields = same count; sibling pattern).
- [ ] **L2 state machine matches L1.** 4 transitions in
  `_ALLOWED_TRANSITIONS`; 4 corresponding event types in
  `_TRANSITION_EVENTS`. Same cardinality.
- [ ] **L3 content-hash discipline is grounded against CAR base.**
  The 12-char prefix matches `content_addressed_repo.py:94`'s
  existing convention.
- [ ] **L4 wire shape preserves A.1's L4 preview shape exactly
  except for the new `graph_intent_id` field.** Stage 2 grep
  verifies the existing field set is intact.
- [ ] **L5 field-name discipline** (F1 absorption): existing
  `CommitVerification` field names (`matched`, `drift_count`,
  `first_drift_index`) preserved verbatim; new fields
  (`assent_valid`, `assent_record`) additive with safe defaults.
  Stage 2 grep verifies NO `is_valid` / `held_hash` / `fresh_hash`
  / `mismatch_reason` identifiers appear in A.2-modified code
  (these were v1 plan-invented shapes that contradicted shipped
  reality).
- [ ] **L5 signature extension is backward-compatible** with the
  5 existing call sites (1 production at `_step.py:799` + 4 tests
  at `test_commit.py:259/268/279/303`). All 5 should pass
  unchanged with the optional kwarg.
- [ ] **L5 CommitError ASSENT_INVALID extension** sweep: new code
  constant added; `__init__` `graph_intent_id` kwarg added;
  `to_error()` surfaces graph_intent_id when code is
  ASSENT_INVALID; existing 3 code constants
  (`MUTATION_MANIFEST_INVALID`, `APPLY_COUNTERPART_NOT_DECLARED`,
  `PLAN_STATE_DRIFT`) preserved verbatim.
- [ ] **D5 _engine.py + _step.py adoption is honest** — both
  files in modified-files manifest; assent_record propagation
  visible in both signatures; `if not verification.assent_valid`
  branch in `_step.py` appended below existing
  `if not verification.matched` branch; existing drift branch
  body unchanged.
- [ ] **L6 audit-event taxa are distinct from `staged.*`** —
  no overlap; consumers subscribed to one family see no
  contamination from the other.
- [ ] **L7 chat-side terminal taxa cardinality is correct.** A.1
  shipped 5; A.2 adds 1 = 6 total. Stage 2 grep verifies all 6
  names appear; no 7th.
- [ ] **L8 exit-code envelope is sweep-complete** for all named
  failure classes (carve-out 6).
- [ ] **L9(a/b/c) is internally consistent.** Regime-3 produces
  graph_intent_id; chat-apply-grammar consumes graph_intent_id;
  ratify endpoint consumes graph_intent_id. The shape flows
  unchanged across the three surfaces.
- [ ] **L10 store-and-replay invariant holds** — chain_steps fed
  to `run_chain_steps` come from `AssentRecord.body`, not from
  a fresh `compile_intent` call. NO LLM call between assent and
  apply.
- [ ] **L11 migration constraint shape is verified against
  migration 0005's `_ALL_ENTITY_TYPES` tuple** for upgrade-target
  consistency (20 → 21 entity_types) and downgrade-target
  consistency (21 → 20). Helper pattern `_entity_type_check(types)`
  reused per 0005 convention; not hand-written. Stage 2 verifies
  ZERO references to fictional `orchestration_compromise_ledger`
  / `orchestration_lifecycle_state` /
  `orchestration_promotion_ledger` as entity_type discriminator
  values in any A.2-introduced files (these are TABLE names from
  migrations 0006/0007/0008, not entity_type values; F2
  absorption).
- [ ] **L11 count discipline**:
  `len(_PRE_A2_ENTITY_TYPES) == 20`;
  `len(_POST_A2_ENTITY_TYPES) == 21`. Mechanical assertion in
  D3 test suite.
- [ ] **L12 decided_by field semantics align with future
  SEED-AUTH-V1.5** — placeholder shape, free-string, default
  "local"; not auth-validated in A.2.
- [ ] **MOL-1 `forge_bridge.__all__` discipline upheld.**
  No new exports.
- [ ] **MOL-4 CAR docstring broadening lands honestly.** The new
  docstring acknowledges both orch_* and assent_record usage
  symmetrically.
- [ ] **MOL-5 K=2 termination preservation verified.**
  `complete_with_tools` body unchanged; `_OrchestrationTerminated`
  signal class unchanged.
- [ ] **R-A2.0(a) parallel-substrate discipline verified by
  grep table** — no `staged_operation` mention in A.2-introduced
  files; no `StagedOpRepo` import in A.2 modules.
- [ ] **N1 runtime-vs-snapshot reconciliation honored** —
  AssentRecord stores a snapshot; runtime statelessness preserved
  in the chat handler (no multi-turn graph-intent inheritance).
- [ ] **C9 identity-scope discipline honored** — graph_intent_id
  is content-addressed; AssentRecord.id (UUID) is the row-event
  identifier. Distinct. Both surfaced separately.
- [ ] **C10 deliberate-dual-surface honored** — the cross-surface
  chat+CLI flow is the architecturally-correct shape per Q5;
  not an oversight.

## Status

**Phase plan v3 — Stage 1b cycle 2 polish pass absorbed; awaiting
Stage 1b cycle 3 verification.** Revised 2026-05-28 from v2 after
DT + Creative Stage 1b cycle 2 produced 0 framing-grade catches +
3 polish-grade catches (M-new1, M-new2, M-new3). Per DT catch
trajectory: v1 → v2 = 9 catches (2 framing + 7 polish, structural);
v2 → v3 = 3 catches (0 framing + 3 polish, surgical). Healthy
convergence; comparable to discuss-stage 10 → 2 → 0 trajectory.

**v2 → v3 absorption summary:**

| Catch | Class | Disposition |
|---|---|---|
| M-new1 | DT archaeology-grade | Modified-files heading "9 files" → "10 files"; inline recount "15 new + 9 modified = 24" → "15 new + 10 modified = 25". Sibling absorption pass per `[[feedback-sibling-check-before-fix-scope]]` — v2 absorbed M4 new-files heading but left modified-files heading uncorrected. |
| M-new2 | DT archaeology-grade | L11 helper docstring naming drift — `"Mirrors 0005's helper at content_addressed_repo migration"` → `"Mirrors the helper at 0005_phase4b_entity_types.py:62-64 (last migration to touch ck_entities_type)"`. Verbatim site reference closes the future-archaeology gap. |
| M-new3 | DT polish (substrate-recall family — flow variant) | D5 acceptance bullets 4 + 5 reworded — drops the incorrect "regime-3 preview-only path under A.1's pre-A.2 semantics — preserved unchanged" framing; reframes as defensive default for kwarg surface with explicit "no A.1 caller exercises this combination — regime-3 short-circuits at `run_compile_branch:130-137` before reaching `run_chain_steps`" note. |

**Methodology candidate WIDENED** (per cycle 2 cross-voice
synthesis): the substrate-shape grounding discipline that
catches the writing-room substrate-recall failure mode spans
THREE distinct surface manifestations:

| Variant | Instance | Failure | Catch |
|---|---|---|---|
| Shape (dataclass fields) | A.2 F1 | Invented `CommitVerification` fields | L5 rewrite against shipped 3-field shape |
| Convention (helper patterns) | A.2 F2 | Hand-wrote constraint string; abandoned helper | L11 rewrite using `_entity_type_check` per 0005 |
| Flow (regime-path naming) | A.2 M-new3 | Framed unreachable A.1 path as "preserved" | D5 acceptance reframed as defensive default |

All three resolve to the same root cause — drafting against
memory-shaped recall rather than file-shaped grounding — and
all three are caught by the same Stage 1b discipline.

Plus A.1 C2 (Stage 1b inaugural instance from A.1 cycle):
within-project arc evidence now spans 4 within-project instances
(A.1 C2 + A.2 F1 + A.2 F2 + A.2 M-new3) across 2 cycles. Per
`[[feedback-failure-shape-stability-as-disposition-evidence]]`:
disposition stability across all instances is the load-bearing
evidence — same failure signature, same root cause, same Stage
1b discipline catches it. Promotion-grade candidate for
A.2-CLOSE methodology synthesis.

**Creative cycle-2 frame** (carry to A.2-CLOSE): *"Stage 1a
discovers architecture. Stage 1b reattaches the architecture to
the actual codebase. Different jobs, different failure
signatures."* The discipline distinction matters — the same
writing-room produces both stages, but each operates against a
different verification surface (Stage 1a against architectural
coherence; Stage 1b against substrate reality). Naming the
distinction in the close cursor preserves it for future code-
handoff cycles.

**v1 → v2 absorption summary (preserved for archaeology):**

| Catch | Class | Disposition |
|---|---|---|
| F1 | DT framing-grade (BLOCKER) | L5 rewritten against shipped `CommitVerification` shape (matched / drift_count / first_drift_index + new assent_valid + assent_record); verify() body re-grounded against shipped drift algorithm; CommitError extended with ASSENT_INVALID + graph_intent_id; production caller at _step.py:798-808 ADOPTS new branch (moved from NOT-modified to modified). |
| F2 | DT framing-grade (BLOCKER) | L11 rewritten using `_entity_type_check` helper pattern from migration 0005; pre-A.2 baseline is 20 entity_types (verified); A.2 extends 20 → 21 by adding `'assent_record'`; zero fictional `orchestration_*_ledger` siblings. |
| F1 cascade | F1 fallout | New D5 ships `_engine.py` + `_step.py` adoption of AssentRecord propagation through `run_chain_steps` → step executor → verify call. Substrate-before-consumer ordering preserved. D5..D9 from v1 renumbered to D6..D10. |
| M1 | DT polish | `_build_preview` → `build_preview_from_steps` (actual name at `_chat_compile.py:73`). |
| M2 | DT polish | L9(a) example shows `async with session_factory()` + `await session.commit()` lifecycle. |
| M3 | DT polish | Regime-3 return line count corrected 131-133 → 131-137. |
| M4 | DT polish | File manifest heading "10 files" → "15 files" (matches inline-recount + adds 2 new test files for D5 cascade). |
| M5 | DT polish (F1 fallout) | `_step.py` + `_engine.py` moved from NOT-modified to modified. |
| M6 | Creative polish | Subsumed by F1 absorption (CommitVerification field additions carve-out lands cleanly under corrected shape). |
| M7 | DT polish | L8 plan-pick: silent fall-through to `assent_record_not_found` (CLI regex + daemon-side entity_type scoping prevent cross-substrate confusion; 4th error code not warranted). |

**Drafted 2026-05-28 against:**
- A.2-FRAMING.md v3.1 at `072948f`
- A.2-DISCUSS-QUESTIONS.md v3 at `37e7dcb` (room-converged +
  operator-ratified)
- Direct grounding reads of `forge_bridge/store/staged_operations.py`,
  `forge_bridge/store/content_addressed_repo.py`,
  `forge_bridge/core/staged.py`, `forge_bridge/graph/commit.py`,
  `forge_bridge/console/_chat_compile.py`,
  `forge_bridge/console/handlers.py` (regime emit sites),
  `forge_bridge/mcp/tools.py` (staged-ops impl section),
  `forge_bridge/cli/main.py` (Typer top-level structure)
- **v2 additional grounding reads** (per Stage 1b cycle 1
  absorption): full body of `forge_bridge/graph/commit.py`
  (CommitVerification + verify() body + CommitError shape),
  `forge_bridge/store/migrations/versions/0005_phase4b_entity_types.py`
  (helper pattern + entity_type tuples), `forge_bridge/console/_step.py:790-830`
  (verify call site + drift branch + error envelope).

**Next motion.** Stage 1b cycle 3 verification pass (DT seat)
against:
- The plan body (this artifact)
- Current main (`37e7dcb` — discuss commit; no new substrate
  commits between v1, v2, and v3)
- The v2 → v3 diff (verifying M-new1 + M-new2 + M-new3 absorbed)
- All 9 rulings + 8 forward-looking caveats + 10 discuss
  carve-outs absorbed cleanly

If green-clean: implementation hands off in D1..D10 order. If
revisions needed: v4 draft. Per DT cycle-2 close-frame
("v3 → cycle 3 is sign-off territory unless something genuinely
new surfaces") + Creative cycle-2 close-frame (*"It smells like
'did the plan remember every place reality touches the ruling?'
That's usually the neighborhood immediately before handoff."*):
v3 → cycle 3 is the convergence target. Catch trajectory
expected to be 0–1 archaeology-grade catches at most; anything
structural would mean the substrate-grounding sweep missed a
seam.

**Anti-scope binding.** Per
`[[feedback-anti-scope-discipline-under-pressure]]`: when
mid-implementation surface pressures appear (e.g., "should this
also handle the staged_operation case?" / "what if compile
produces drift?"), the implementer does NOT improvise. The two
substrates are parallel by construction; drift detection is at
commit-node verify; the policy boundary is sharply named via L5 +
L10. Per `[[feedback-orchestrator-control-flow-not-meaning]]`:
the apply path runs the EXACT chain the operator decided on; no
LLM substitution.

**Layering discipline observation** (carrying from discuss v3):
the framing owns laws + assumptions + question space; this plan
owns implementation contracts + acceptance criteria + file change
manifest. Stage 1b owns verification of the plan's completeness;
implementation hands off after verification clears. Late-stage
churn usually comes from layer leakage; tight layer boundaries in
this plan reduce that risk.
