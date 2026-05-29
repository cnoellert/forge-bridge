"""AssentRecord application class for forge-bridge Phase A.2 (v1.7).

Represents an operator's authority-attached decision on a bridge-compiled
graph-intent. Bridge IS the executor here (unlike StagedOperation where bridge
is the bookkeeper); the assent record authorizes bridge's own execution of the
persisted chain.

The state machine (``proposed -> ratified -> applied | failed``) is enforced by
``forge_bridge.store.assent_record_repo.AssentRecordRepo``. This class carries
no state-machine logic.

``to_dict()`` is the single source of truth for the shape that the CLI and the
chat surface return verbatim. Any consumer that serializes an AssentRecord must
call ``to_dict()`` -- never hand-roll the shape.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from forge_bridge.core.entities import BridgeEntity


class AssentRecord(BridgeEntity):
    """An operator's authority-attached decision on a graph-intent.

    Constitutive identity per R-A2.0(a): bridge persists what it compiled, the
    operator decides whether bridge proceeds, bridge executes. Distinct from
    StagedOperation (where bridge is bookkeeper for consumer-proposed,
    consumer-executed operations).

    Lifecycle (enforced by AssentRecordRepo, NOT by this class):
        proposed  -> ratified  -> applied
        proposed  -> ratified  -> failed
        (no rejected state -- non-ratification is implicit by absence of
         ratify action; drift-invalidate happens at apply time)

    Constructing AssentRecord rows directly via
    ``session.add(DBEntity(entity_type='assent_record', ...))`` is prohibited
    -- AssentRecordRepo is the only sanctioned write path. Direct construction
    bypasses the audit-trail event emission and the content-hash idempotency
    guarantee.
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
        self.graph_intent_id: str = graph_intent_id
        self.chain_steps: list[str] = chain_steps
        self.status: str = status
        self.decided_by: Optional[str] = decided_by
        self.decided_at: Optional[datetime] = decided_at
        self.applied_at: Optional[datetime] = applied_at
        self.apply_result: Optional[dict[str, Any]] = apply_result
        self.apply_failure_reason: Optional[str] = apply_failure_reason

    @property
    def entity_type(self) -> str:
        return "assent_record"

    def to_dict(self) -> dict:
        """Return the shape that CLI + chat surfaces return verbatim.

        Shape (14 keys total):
            From super().to_dict(): id, entity_type, created_at,
                                     metadata, locations, relationships
            Added by this method:   graph_intent_id, chain_steps, status,
                                     decided_by, decided_at, applied_at,
                                     apply_result, apply_failure_reason
        """
        d = super().to_dict()
        d.update({
            "graph_intent_id": self.graph_intent_id,
            "chain_steps": self.chain_steps,
            "status": self.status,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "apply_result": self.apply_result,
            "apply_failure_reason": self.apply_failure_reason,
        })
        return d

    def __repr__(self) -> str:
        return (
            f"AssentRecord(graph_intent_id={self.graph_intent_id!r}, "
            f"status={self.status!r}, id={self.id!s:.8}...)"
        )
