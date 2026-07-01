"""GenerationGrant application class — the generation spend-gate (#146).

Represents an operator's authorization to spend on ONE generation submit. The
grant is the finite-atomic authority a direct ``forge_generate_*`` tool (or the
planner door) must present at the ``driver.submit()`` chokepoint before any
paid backend is invoked.

Distinct authority class from ``AssentRecord``:
    - AssentRecord authorizes bridge's own re-execution of a persisted chain
      (a host mutation): terminal 1:1, carries ``chain_steps`` + apply result.
    - GenerationGrant authorizes an outbound *spend* against a peer backend:
      it carries NO chain_steps and NO apply result — the *runs* spend, not the
      grant. It is single-use, consumed atomically at submit.

Lifecycle (enforced by GenerationGrantRepo, NOT by this class):
    proposed  -> ratified  -> consumed          (the spend path)
    proposed  -> revoked   |  proposed -> failed
    ratified  -> revoked   |  ratified -> failed
    Terminals: consumed, revoked, failed.

The hashed terms body (immutable, content-addressed) carries:
    operator_id, backend_identity_triple, estimated_cost {currency, amount},
    nonce (a per-mint uuid), run_kind (the scope tag).
The ``nonce`` makes every mint unique so content-identity can never collapse a
fresh quote onto a revoked/consumed grant of identical cost. ``estimated_cost``
is peer-declared and stamped immutably — bridge never authors the dollar number.

``to_dict()`` is the single source of truth for the shape the CLI / HTTP / MCP
ratify surfaces return verbatim. Any consumer that serializes a GenerationGrant
must call ``to_dict()`` -- never hand-roll the shape (the assent.py discipline;
#140 cost-preview, #142 budget, and the Console projection all ride additively
on this dict).

``grant_id`` is the opaque 12-hex ``content_hash[:12]`` handle — per-mint-unique
by the nonce, and regex-identical to the assent graph_intent_id so the CLI /
endpoint validators are shared.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional, Self

from forge_bridge.core.entities import BridgeEntity


class GenerationGrant(BridgeEntity):
    """An operator's single-use authorization to spend on one generation submit.

    Constructing GenerationGrant rows directly via
    ``session.add(DBEntity(entity_type='generation_grant', ...))`` is prohibited
    -- GenerationGrantRepo is the only sanctioned write path. Direct construction
    bypasses the audit-trail event emission, the content-hash idempotency
    guarantee, and (critically) the atomic CAS consume that prevents
    double-spend.
    """

    def __init__(
        self,
        operator_id: str,
        backend_identity_triple: dict[str, Any],
        estimated_cost: dict[str, Any],
        run_kind: str,
        nonce: str,
        status: str = "proposed",
        grant_id: Optional[str] = None,
        decided_by: Optional[str] = None,
        decided_at: Optional[datetime] = None,
        consumed_at: Optional[datetime] = None,
        failure_reason: Optional[str] = None,
        id: Optional[uuid.UUID | str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(id=id, created_at=created_at, metadata=metadata)
        self.operator_id: str = operator_id
        self.backend_identity_triple: dict[str, Any] = dict(backend_identity_triple)
        self.estimated_cost: dict[str, Any] = dict(estimated_cost)
        self.run_kind: str = run_kind
        self.nonce: str = nonce
        self.status: str = status
        self.grant_id: Optional[str] = grant_id
        self.decided_by: Optional[str] = decided_by
        self.decided_at: Optional[datetime] = decided_at
        self.consumed_at: Optional[datetime] = consumed_at
        self.failure_reason: Optional[str] = failure_reason

    @property
    def entity_type(self) -> str:
        return "generation_grant"

    def to_dict(self) -> dict:
        """Return the canonical extensible shape all ratify surfaces return.

        Shape:
            From super().to_dict(): id, entity_type, created_at,
                                     metadata, locations, relationships
            Added by this method:   grant_id, operator_id,
                                     backend_identity_triple, estimated_cost,
                                     run_kind, nonce, status, decided_by,
                                     decided_at, consumed_at, failure_reason
        """
        d = super().to_dict()
        d.update({
            "grant_id": self.grant_id,
            "operator_id": self.operator_id,
            "backend_identity_triple": self.backend_identity_triple,
            "estimated_cost": self.estimated_cost,
            "run_kind": self.run_kind,
            "nonce": self.nonce,
            "status": self.status,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "consumed_at": self.consumed_at.isoformat() if self.consumed_at else None,
            "failure_reason": self.failure_reason,
        })
        return d

    @classmethod
    def from_entity(cls, entity) -> Self:
        """Reconstruct a GenerationGrant from a store DBEntity row."""
        from forge_bridge.store.models import DBEntity

        if not isinstance(entity, DBEntity):
            raise TypeError(f"Expected DBEntity, got {type(entity)!r}")
        if entity.entity_type != "generation_grant":
            raise ValueError(
                "GenerationGrant requires entity_type='generation_grant'; "
                f"got {entity.entity_type!r}"
            )

        attrs = entity.attributes or {}
        content_hash = entity.content_hash or ""
        return cls(
            operator_id=attrs.get("operator_id") or "",
            backend_identity_triple=dict(attrs.get("backend_identity_triple") or {}),
            estimated_cost=dict(attrs.get("estimated_cost") or {}),
            run_kind=attrs.get("run_kind") or "",
            nonce=attrs.get("nonce") or "",
            status=entity.status or attrs.get("status") or "proposed",
            grant_id=attrs.get("grant_id") or content_hash[:12],
            decided_by=attrs.get("decided_by"),
            decided_at=(
                datetime.fromisoformat(attrs["decided_at"])
                if attrs.get("decided_at") else None
            ),
            consumed_at=(
                datetime.fromisoformat(attrs["consumed_at"])
                if attrs.get("consumed_at") else None
            ),
            failure_reason=attrs.get("failure_reason"),
            id=entity.id,
            created_at=entity.created_at,
            metadata=dict(attrs.get("metadata") or {}),
        )

    def __repr__(self) -> str:
        return (
            f"GenerationGrant(grant_id={self.grant_id!r}, "
            f"status={self.status!r}, run_kind={self.run_kind!r}, "
            f"id={self.id!s:.8}...)"
        )


__all__ = ["GenerationGrant"]
