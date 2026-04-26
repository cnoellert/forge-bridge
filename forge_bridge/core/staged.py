"""StagedOperation application class for forge-bridge Phase 13 (FB-A).

This module defines the ``StagedOperation`` entity — a ``staged_operation``
vocabulary extension that represents a human-in-the-loop operation proposal
awaiting approval before execution.  It is intentionally minimal: forge-bridge
is the **bookkeeper** that persists the proposed operation, its approval state,
and the realized result; it does NOT execute the operation.

The state machine (``proposed → approved → executed / rejected / failed``) is
enforced by ``forge_bridge.store.staged_operations.StagedOpRepo`` (Plan 03).
This class carries no state-machine logic.

``to_dict()`` is the **single source of truth** for the shape that FB-B's MCP
tools and HTTP routes will return verbatim (STAGED-06 zero-divergence anchor).
Any consumer that serializes a ``StagedOperation`` must call ``to_dict()`` —
never hand-roll the shape.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from forge_bridge.core.entities import BridgeEntity


class StagedOperation(BridgeEntity):
    """A human-in-the-loop operation proposal awaiting approval and execution.

    forge-bridge is the bookkeeper — it persists the proposed operation,
    its approval state, and the realized result. It does NOT execute the
    operation. The proposer (projekt-forge v1.5, future Maya/editorial
    endpoints) subscribes to ``staged.approved`` events via the existing
    event bus and executes against its own domain.

    Lifecycle (enforced by StagedOpRepo, NOT by this class):
        proposed → approved → executed
        proposed → rejected
        approved → failed

    IMPORTANT: Do not construct StagedOperation rows directly via
    ``session.add(DBEntity(entity_type='staged_operation', ...))`` — the
    StagedOpRepo state machine is the only sanctioned write path.
    Direct construction bypasses the audit-trail event emission required
    by STAGED-03.
    """

    def __init__(
        self,
        operation: str,
        proposer: str,
        parameters: dict[str, Any],
        status: str = "proposed",
        result: Optional[dict[str, Any]] = None,
        approver: Optional[str] = None,
        executor: Optional[str] = None,
        approved_at: Optional[datetime] = None,
        executed_at: Optional[datetime] = None,
        id: Optional[uuid.UUID | str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(id=id, created_at=created_at, metadata=metadata)
        self.operation:   str                      = operation
        self.proposer:    str                      = proposer
        self.parameters:  dict[str, Any]           = parameters
        self.status:      str                      = status
        self.result:      Optional[dict[str, Any]] = result
        self.approver:    Optional[str]            = approver
        self.executor:    Optional[str]            = executor
        self.approved_at: Optional[datetime]       = approved_at
        self.executed_at: Optional[datetime]       = executed_at

    # ── CRITICAL: override entity_type ─────────────────────────────────────
    # BridgeEntity returns cls.__name__.lower() == "stagedoperation",
    # which does NOT match the discriminator string "staged_operation"
    # used everywhere else (ENTITY_TYPES frozenset, ck_entities_type CHECK,
    # EntityRepo.save at repo.py:254). Without this override the save
    # path silently writes the wrong discriminator.
    # See PATTERNS.md Critical Pre-Planning Finding #3.
    @property
    def entity_type(self) -> str:
        return "staged_operation"

    def to_dict(self) -> dict:
        """Return the FB-B contract shape — the zero-divergence anchor (STAGED-06).

        Shape (16 keys total):
            From super().to_dict():   id, entity_type, created_at, metadata,
                                      locations, relationships
            Added by this method:     operation, proposer, parameters, result,
                                      status, approver, executor,
                                      approved_at, executed_at
        """
        d = super().to_dict()
        d.update({
            "operation":   self.operation,
            "proposer":    self.proposer,
            "parameters":  self.parameters,
            "result":      self.result,
            "status":      self.status,
            "approver":    self.approver,
            "executor":    self.executor,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        })
        return d

    def __repr__(self) -> str:
        return (
            f"StagedOperation(op={self.operation!r}, "
            f"status={self.status!r}, id={self.id!s:.8}...)"
        )
