"""
forge-bridge Phase 13 (FB-A) — StagedOperation state-machine repository.

This module ships the behaviour half of the staged_operation entity: the only
sanctioned construction path (``propose``), the four legal lifecycle transitions
(``approve`` / ``reject`` / ``execute`` / ``fail``), and the audit-event emission
that is the load-bearing property of STAGED-03.

State machine (D-10):
    (None)    → proposed
    proposed  → approved | rejected
    approved  → executed | failed
    Terminals: rejected, executed, failed.  Any other transition raises
    StagedOpLifecycleError immediately.

Atomicity guarantee (security_threat_model "audit-trail tamper / dropped events"):
    The entity status update and the DBEvent append share the SAME AsyncSession
    that was passed to StagedOpRepo at construction time.  They either both
    commit or both roll back — there is no window where the status advances
    without an audit record.  The repo NEVER calls
    ``await self.session.commit()`` — transaction boundaries are owned by the
    caller (test fixture or server request handler), matching the conventions
    of EntityRepo and EventRepo.

Composition (PATTERNS.md Finding #8):
    StagedOpRepo composes EventRepo(session) and uses its ``append`` coroutine
    for every audit event.  Direct ``session.add(DBEvent(...))`` is NEVER used
    inside this module — that bypass route must stay sealed.

Exports:
    StagedOpRepo          — state-machine repo, the only sanctioned write path
    StagedOpLifecycleError — exception raised on illegal / idempotent transitions
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.core.staged import StagedOperation
from forge_bridge.store.models import DBEntity
from forge_bridge.store.repo import EventRepo


# ─────────────────────────────────────────────────────────────────────────────
# Exception
# ─────────────────────────────────────────────────────────────────────────────

class StagedOpLifecycleError(Exception):
    """Raised when a staged-operation transition is not permitted by the state machine.

    Carries the attempted transition for callers that want to introspect rather
    than parse the message string.  FB-B (Phase 14) catches this and translates
    to user-facing error envelopes (HTTP 409 Conflict, MCP error result).

    Per PATTERNS.md Critical Pre-Planning Finding #5 / #7:
        Subclass ``Exception`` directly — NOT ``RegistryError``.  The
        staged-ops domain is unrelated to the registry; coupling to a
        registry-specific base class would be a false abstraction.

    Per D-09 (CONTEXT.md):
        NOT exported from ``forge_bridge.__all__`` (internal error class;
        FB-B's API layer translates to user-facing envelopes).
        IS exported from ``forge_bridge.store.__init__`` so FB-B can import
        with ``from forge_bridge.store import StagedOpLifecycleError``.
    """

    def __init__(
        self,
        from_status: str | None,
        to_status: str,
        op_id: uuid.UUID,
    ):
        self.from_status = from_status
        self.to_status   = to_status
        self.op_id       = op_id
        super().__init__(
            f"Illegal transition from {from_status!r} to {to_status!r} "
            f"for staged_operation {op_id}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Repository
# ─────────────────────────────────────────────────────────────────────────────

class StagedOpRepo:
    """Persist staged operations and enforce the proposed → approved → executed
    state machine.  Every transition appends a DBEvent for full audit replay
    (STAGED-03).  The repo composes EventRepo so events are never written via
    direct ``session.add(DBEvent(...))`` — see PATTERNS.md Finding #8.

    Atomicity (security_threat_model): status update and event append share
    the AsyncSession passed in at construction; either both commit or both
    rollback.  This is the load-bearing property that prevents tamper-evident
    audit gaps.

    All writers (FB-B MCP tools, FB-B HTTP routes, future projekt-forge
    integration) MUST go through this repo per D-08 — direct
    ``session.add(DBEntity(entity_type='staged_operation', ...))`` bypasses
    the state machine and emits no events.

    None of the public methods call ``await self.session.commit()`` — the
    caller (test fixture / request handler) owns transaction boundaries,
    matching the ``EntityRepo`` and ``EventRepo`` conventions.
    """

    # State machine — D-10.  Single source of truth; frozenset gives O(1) legality check.
    _ALLOWED_TRANSITIONS: frozenset[tuple[str | None, str]] = frozenset({
        (None,        "proposed"),
        ("proposed",  "approved"),
        ("proposed",  "rejected"),
        ("approved",  "executed"),
        ("approved",  "failed"),
    })

    # Map (old_status, new_status) → event_type string.  Per D-06.
    _TRANSITION_EVENTS: dict[tuple[str | None, str], str] = {
        (None,        "proposed"): "staged.proposed",
        ("proposed",  "approved"): "staged.approved",
        ("proposed",  "rejected"): "staged.rejected",
        ("approved",  "executed"): "staged.executed",
        ("approved",  "failed"):   "staged.failed",
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self._events = EventRepo(session)   # compose — do NOT bypass with session.add(DBEvent)

    # ── Public API ────────────────────────────────────────────────────────────

    async def propose(
        self,
        operation: str,
        proposer: str,
        parameters: dict[str, Any],
        project_id: uuid.UUID | None = None,
    ) -> StagedOperation:
        """Mint a new staged_operation.  The ONLY sanctioned construction path.

        Inserts a DBEntity row with ``entity_type='staged_operation'`` and
        ``status='proposed'``, then appends a ``staged.proposed`` audit event
        on the same session.  The caller owns the commit.

        Per D-03: the ``name`` column carries the ``operation`` string so that
        ``WHERE entity_type='staged_operation' AND name='flame.publish_sequence'``
        uses the ``ix_entities_type_name`` index without a JSONB scan.
        """
        op = StagedOperation(
            operation=operation,
            proposer=proposer,
            parameters=parameters,
            status="proposed",
        )
        # Insert directly — we control the discriminator, name, and attributes.
        db_entity = DBEntity(
            id=op.id,
            entity_type="staged_operation",
            project_id=project_id,
            name=operation,          # D-03: index-friendly name column
            status="proposed",
            attributes=self._serialize(op),
        )
        self.session.add(db_entity)
        # Audit: emit staged.proposed with old_status=None
        await self._append_event(
            op_id=op.id, old_status=None, new_status="proposed",
            actor=proposer, operation=operation, project_id=project_id,
        )
        return op

    async def get(self, op_id: uuid.UUID) -> StagedOperation | None:
        """Return the StagedOperation with the given UUID, or None if absent."""
        db_entity = await self.session.get(DBEntity, op_id)
        if db_entity is None or db_entity.entity_type != "staged_operation":
            return None
        return self._to_staged_operation(db_entity)

    async def list(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        project_id: uuid.UUID | None = None,
    ) -> tuple[list[StagedOperation], int]:
        """Return (records, total_before_pagination) for FB-B's staged_list handler.

        D-01 default ordering: created_at DESC. Pagination clamp lives in the handler.
        Filters compose via SQL AND. `total` reflects filtered set count BEFORE pagination.

        T-14-01-01 (Tampering): uses SQLAlchemy parameterized queries — never f-string
        into SQL. Analog: EntityRepo.list_by_type (repo.py:295).
        """
        base_filter = (DBEntity.entity_type == "staged_operation",)
        if status is not None:
            base_filter += (DBEntity.status == status,)
        if project_id is not None:
            base_filter += (DBEntity.project_id == project_id,)

        count_stmt = select(func.count()).select_from(DBEntity).where(*base_filter)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(DBEntity)
            .where(*base_filter)
            .order_by(DBEntity.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        records = [self._to_staged_operation(db) for db in result.scalars().all()]
        return records, total

    async def approve(self, op_id: uuid.UUID, approver: str) -> StagedOperation:
        """Advance proposed → approved and record the approver identity.

        Raises StagedOpLifecycleError if the operation is not in 'proposed'
        status (including idempotent re-approval per D-10).
        """
        return await self._transition(
            op_id, new_status="approved", actor=approver,
            attribute_updates={
                "approver":    approver,
                "approved_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def reject(self, op_id: uuid.UUID, actor: str) -> StagedOperation:
        """Advance proposed → rejected.

        There is no 'rejector' field in D-02; the actor is captured only in
        the DBEvent (payload.actor + client_name per D-07).  The repo accepts
        any non-empty actor string per D-11/D-12; caller is responsible for
        providing the correct identity.  No validation in v1.4.

        Raises StagedOpLifecycleError if the operation is not in 'proposed'
        status (including idempotent re-rejection per D-10).
        """
        return await self._transition(
            op_id, new_status="rejected", actor=actor,
            # No attribute updates — there is no 'rejector' field in D-02.
            attribute_updates=None,
        )

    async def execute(
        self,
        op_id: uuid.UUID,
        executor: str,
        result: dict[str, Any],
    ) -> StagedOperation:
        """Mark approved → executed and record the success result payload (D-14).

        ``result`` is the caller-supplied success payload — passed verbatim
        into ``attributes.result``.  Sanitization is a v1.5+ concern per
        CONTEXT.md <deferred>.

        Raises StagedOpLifecycleError if the operation is not in 'approved'
        status.
        """
        return await self._transition(
            op_id, new_status="executed", actor=executor,
            attribute_updates={
                "executor":    executor,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "result":      result,
            },
        )

    async def fail(
        self,
        op_id: uuid.UUID,
        executor: str,
        result: dict[str, Any],
    ) -> StagedOperation:
        """Mark approved → failed with the failure result payload (D-13).

        ``result`` is the caller-supplied failure payload — passed verbatim
        into ``attributes.result``.  Sensitive detail sanitization is a
        v1.5+ concern (LLMTOOL-06's ``_sanitize_tool_result()`` is for the
        LLM-loop boundary, not storage).

        Raises StagedOpLifecycleError if the operation is not in 'approved'
        status.
        """
        return await self._transition(
            op_id, new_status="failed", actor=executor,
            attribute_updates={
                "executor":    executor,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "result":      result,
            },
        )

    # ── Internal — enforces D-08, D-10, D-22 ─────────────────────────────────

    async def _transition(
        self,
        op_id: uuid.UUID,
        new_status: str,
        actor: str,
        attribute_updates: dict[str, Any] | None,
    ) -> StagedOperation:
        """Core state-machine transition.

        1. Fetch the DBEntity row (lock in caller's session).
        2. Verify the (old_status, new_status) pair is in _ALLOWED_TRANSITIONS.
           Raises StagedOpLifecycleError for any illegal or idempotent transition.
        3. Mutate ``db_entity.status`` and apply ``attribute_updates`` via
           read-modify-write of the JSONB dict.  The ``parameters`` key is NEVER
           in ``attribute_updates`` for any of the four public methods — preserving
           the STAGED-04 SQL-only-diff property (D-22).
        4. Append the audit event on the SAME session (atomicity invariant).
        5. Return the reconstructed StagedOperation.

        Does NOT call ``await self.session.commit()`` — caller owns the
        transaction boundary.
        """
        db_entity = await self.session.get(DBEntity, op_id)
        if db_entity is None or db_entity.entity_type != "staged_operation":
            # UUID doesn't resolve to a staged_op — distinct from illegal-transition.
            # FB-B handlers (Plan 14-03 + 14-04) map `from_status is None` → HTTP 404
            # `staged_op_not_found`. Sentinel string "(missing)" was the WR-01 bug; the
            # None discriminator is now load-bearing for the FB-B 404/409 split.
            raise StagedOpLifecycleError(
                from_status=None, to_status=new_status, op_id=op_id,
            )
        old_status = db_entity.status
        if (old_status, new_status) not in self._ALLOWED_TRANSITIONS:
            raise StagedOpLifecycleError(
                from_status=old_status, to_status=new_status, op_id=op_id,
            )

        # Mutate status on the existing row — do NOT delete-and-reinsert.
        db_entity.status = new_status
        if attribute_updates:
            # Read-modify-write: start from the existing attributes dict so
            # that the ``parameters`` key (and any other keys we don't own
            # in this transition) are preserved verbatim.  CRITICAL per D-22:
            # ``parameters`` is NEVER in ``attribute_updates`` for any public
            # method — verify by reading approve/reject/execute/fail above.
            attrs = dict(db_entity.attributes or {})
            for k, v in attribute_updates.items():
                attrs[k] = v
            db_entity.attributes = attrs

        # Audit: emit the transition event on the SAME session.
        await self._append_event(
            op_id=op_id, old_status=old_status, new_status=new_status,
            actor=actor,
            operation=db_entity.attributes.get("operation", db_entity.name),
            project_id=db_entity.project_id,
        )

        return self._to_staged_operation(db_entity)

    async def _append_event(
        self,
        op_id: uuid.UUID,
        old_status: str | None,
        new_status: str,
        actor: str,
        operation: str,
        project_id: uuid.UUID | None,
    ) -> None:
        """Append a transition audit event via the composed EventRepo.

        The payload shape is defined by D-07:
            old_status   — None for the initial 'proposed' event
            new_status   — the status after transition
            actor        — free-string identity of the transitioning party
            operation    — denormalized for search without join
            transition_at — ISO-8601 UTC timestamp

        client_name carries the actor too (D-07 intentional duplication) so
        existing event tooling that reads client_name works without payload
        inspection.
        """
        event_type = self._TRANSITION_EVENTS[(old_status, new_status)]
        payload = {
            "old_status":    old_status,
            "new_status":    new_status,
            "actor":         actor,
            "operation":     operation,
            "transition_at": datetime.now(timezone.utc).isoformat(),
        }
        # Use composed EventRepo — NEVER session.add(DBEvent(...)) directly.
        await self._events.append(
            event_type=event_type,
            payload=payload,
            client_name=actor,
            project_id=project_id,
            entity_id=op_id,
        )

    # ── Serialization (D-02 shape) ────────────────────────────────────────────

    @staticmethod
    def _serialize(op: StagedOperation) -> dict[str, Any]:
        """Return the JSONB attributes shape for a staged_operation per D-02.

        This shape is the single canonical representation written to the
        ``attributes`` JSONB column.  It is mirrored by
        ``EntityRepo._attrs_to_dict``'s ``staged_operation`` branch (Task 2):
        both methods must produce identical shapes.

        Fields (8 typed keys, matching D-02):
            operation   — name of the proposed operation (e.g. 'flame.publish_sequence')
            proposer    — free-string identity of the proposing party
            parameters  — immutable after propose (D-22 SQL-only-diff anchor)
            result      — None until executed/failed; then the result payload
            approver    — None until approved
            executor    — None until executed or failed
            approved_at — None until approved; ISO-8601 when set
            executed_at — None until executed or failed; ISO-8601 when set
        """
        return {
            "operation":   op.operation,
            "proposer":    op.proposer,
            "parameters":  op.parameters,
            "result":      op.result,
            "approver":    op.approver,
            "executor":    op.executor,
            "approved_at": op.approved_at.isoformat() if op.approved_at else None,
            "executed_at": op.executed_at.isoformat() if op.executed_at else None,
        }

    @staticmethod
    def _to_staged_operation(db: DBEntity) -> StagedOperation:
        """Reconstruct a StagedOperation from a DBEntity row.

        Uses the ``BridgeEntity.__init__`` deserialization idiom established by
        the Version pattern at ``repo.py:424-431`` (PATTERNS.md "BridgeEntity.__init__
        deserialization"): allocate via ``__new__``, init the base with an empty
        metadata dict, then assign all typed fields directly.

        This method is mirrored by ``EntityRepo._to_core``'s
        ``staged_operation`` branch (Task 2) — both must produce identical
        StagedOperation instances.
        """
        from forge_bridge.core.entities import BridgeEntity
        a = db.attributes or {}
        op = StagedOperation.__new__(StagedOperation)
        BridgeEntity.__init__(op, id=db.id, created_at=db.created_at, metadata={})
        op.operation   = a.get("operation", db.name or "")
        op.proposer    = a.get("proposer", "")
        op.parameters  = a.get("parameters", {})
        op.result      = a.get("result")
        op.status      = db.status or "proposed"
        op.approver    = a.get("approver")
        op.executor    = a.get("executor")
        op.approved_at = (
            datetime.fromisoformat(a["approved_at"]) if a.get("approved_at") else None
        )
        op.executed_at = (
            datetime.fromisoformat(a["executed_at"]) if a.get("executed_at") else None
        )
        return op
