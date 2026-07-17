"""ConsentGrant application class — the fitted-model consent latch (#161).

Represents a real person's authorization that their likeness may be fitted into
a model and replayed at infer. It is the consent-enforcement counterpart to the
GenerationGrant spend-gate (#146): where a GenerationGrant authorizes an
outbound *spend* (single-use, consumed atomically at submit), a ConsentGrant is
a durable *latch* — ratified once for a person, bound later to the fitted-model
asset that person's likeness trained, and re-verified at every infer. Its
terminal is withdrawal, and withdrawal propagates to asset revocation so a
withdrawn consent immediately refuses inference (#160 gate).

Distinct authority class from both AssentRecord and GenerationGrant:
    - AssentRecord authorizes bridge's own re-execution of a persisted chain
      (a host mutation): terminal 1:1, carries ``chain_steps`` + apply result.
    - GenerationGrant authorizes an outbound spend: single-use, CAS-consumed.
    - ConsentGrant authorizes fitting+replay of a likeness: a durable latch,
      NOT a single-use spend — there is no CAS/consume. It is bound to an ASSET
      (not to a call — ADR-002 D-D), verified at infer, and withdrawn to revoke.

Lifecycle (enforced by ConsentGrantRepo, NOT by this class):
    proposed  -> ratified  -> withdrawn      (the consent path)
    proposed  -> withdrawn
    Terminals: withdrawn.
    (A separate ``bind_asset`` step stamps the mutable ``fitted_model_asset_id``
    onto a ratified grant when the model is fit — it is NOT a status change.)

Immutable, content-hashed terms body (the person's grant of consent):
    owner_of_likeness, allowed_shot_scopes, forbidden_uses, valid_from,
    valid_until, nonce (a per-mint uuid).
The grant is ratified for a person BEFORE the fitted model exists, so
``fitted_model_asset_id`` is MUTABLE STATE bound later at fit — putting it in
the terms body would change the content hash and break immutability. The
``nonce`` makes every mint content-unique so a fresh grant can never collapse
onto a withdrawn one of identical terms.

Withdrawal is bridge's hard gate; expiry is NOT — ``valid_until`` is stored and
returned so downstream generators can verify the validity window at infer, but
bridge builds no expiry sweep. Only withdrawal (→ revoke) refuses at the gate.

``to_dict()`` is the single source of truth for the shape the CLI / HTTP / MCP
surfaces return. ``bound_asset_id`` is the canonical external name for the
fitted-model asset UUID. It must not be confused with forge-generators'
``ConsentGrant.identity_id``, which is a trained-identity handle such as
``dfl-marilyn``. The legacy bridge ``identity_id`` alias remains for one
compatibility cycle but has exactly the same UUID semantics as
``bound_asset_id``; consumers must migrate to the unambiguous name.

``grant_id`` is the opaque 12-hex ``content_hash[:12]`` handle — per-mint-unique
by the nonce, and regex-identical to the assent graph_intent_id so the CLI /
endpoint validators are shared.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional, Self

from forge_bridge.core.entities import BridgeEntity


def _coerce_dt(value: Any) -> Optional[datetime]:
    """Normalize a datetime | ISO-8601 str | None to a datetime | None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


class ConsentGrant(BridgeEntity):
    """A person's asset-bound authorization to fit and replay their likeness.

    Constructing ConsentGrant rows directly via
    ``session.add(DBEntity(entity_type='consent_grant', ...))`` is prohibited --
    ConsentGrantRepo is the only sanctioned write path. Direct construction
    bypasses the audit-trail event emission, the content-hash idempotency
    guarantee, and (critically) the atomic withdrawal→revocation propagation.
    """

    def __init__(
        self,
        owner_of_likeness: str,
        allowed_shot_scopes: Optional[list[str]] = None,
        forbidden_uses: Optional[list[str]] = None,
        valid_from: Optional[datetime | str] = None,
        valid_until: Optional[datetime | str] = None,
        nonce: str = "",
        status: str = "proposed",
        grant_id: Optional[str] = None,
        decided_by: Optional[str] = None,
        decided_at: Optional[datetime] = None,
        withdrawn_at: Optional[datetime] = None,
        fitted_model_asset_id: Optional[str] = None,
        revocation_handle: Optional[str] = None,
        id: Optional[uuid.UUID | str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(id=id, created_at=created_at, metadata=metadata)
        self.owner_of_likeness: str = owner_of_likeness
        self.allowed_shot_scopes: list[str] = list(
            allowed_shot_scopes if allowed_shot_scopes is not None else ["this_clip_only"]
        )
        self.forbidden_uses: list[str] = list(forbidden_uses or [])
        self.valid_from: Optional[datetime] = _coerce_dt(valid_from)
        self.valid_until: Optional[datetime] = _coerce_dt(valid_until)
        self.nonce: str = nonce
        self.status: str = status
        self.grant_id: Optional[str] = grant_id
        self.decided_by: Optional[str] = decided_by
        self.decided_at: Optional[datetime] = decided_at
        self.withdrawn_at: Optional[datetime] = withdrawn_at
        self.fitted_model_asset_id: Optional[str] = fitted_model_asset_id
        self.revocation_handle: Optional[str] = revocation_handle

    @property
    def entity_type(self) -> str:
        return "consent_grant"

    @property
    def revoked(self) -> bool:
        """Derived: a withdrawn consent reads as revoked (generators-compatible)."""
        return self.status == "withdrawn"

    def to_dict(self) -> dict:
        """Return the canonical extensible shape all consent surfaces return.

        Shape:
            From super().to_dict(): id, entity_type, created_at,
                                     metadata, locations, relationships
            Added by this method:   grant_id, bound_asset_id,
                                     identity_id (deprecated UUID alias),
                                     owner_of_likeness, allowed_shot_scopes,
                                     forbidden_uses, valid_from, valid_until,
                                     revoked (derived from status),
                                     revocation_handle, status,
                                     fitted_model_asset_id, nonce, decided_by,
                                     decided_at, withdrawn_at

        ``bound_asset_id`` is the canonical wire name. ``identity_id`` is a
        deprecated bridge compatibility alias for the same asset UUID; it is
        NOT forge-generators' trained-identity handle.
        """
        d = super().to_dict()
        d.update({
            "grant_id": self.grant_id,
            "bound_asset_id": self.fitted_model_asset_id,
            # Deprecated compatibility alias. Remove after one release cycle.
            "identity_id": self.fitted_model_asset_id,
            "owner_of_likeness": self.owner_of_likeness,
            "allowed_shot_scopes": list(self.allowed_shot_scopes),
            "forbidden_uses": list(self.forbidden_uses),
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "revoked": self.revoked,
            "revocation_handle": self.revocation_handle,
            "status": self.status,
            # Bridge-side mutable state (superset of the generators shape).
            "fitted_model_asset_id": self.fitted_model_asset_id,
            "nonce": self.nonce,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
        })
        return d

    @classmethod
    def from_entity(cls, entity) -> Self:
        """Reconstruct a ConsentGrant from a store DBEntity row."""
        from forge_bridge.store.models import DBEntity

        if not isinstance(entity, DBEntity):
            raise TypeError(f"Expected DBEntity, got {type(entity)!r}")
        if entity.entity_type != "consent_grant":
            raise ValueError(
                "ConsentGrant requires entity_type='consent_grant'; "
                f"got {entity.entity_type!r}"
            )

        attrs = entity.attributes or {}
        content_hash = entity.content_hash or ""
        return cls(
            owner_of_likeness=attrs.get("owner_of_likeness") or "",
            allowed_shot_scopes=list(attrs.get("allowed_shot_scopes") or []),
            forbidden_uses=list(attrs.get("forbidden_uses") or []),
            valid_from=attrs.get("valid_from"),
            valid_until=attrs.get("valid_until"),
            nonce=attrs.get("nonce") or "",
            status=entity.status or attrs.get("status") or "proposed",
            grant_id=attrs.get("grant_id") or content_hash[:12],
            decided_by=attrs.get("decided_by"),
            decided_at=_coerce_dt(attrs.get("decided_at")),
            withdrawn_at=_coerce_dt(attrs.get("withdrawn_at")),
            fitted_model_asset_id=attrs.get("fitted_model_asset_id"),
            revocation_handle=attrs.get("revocation_handle"),
            id=entity.id,
            created_at=entity.created_at,
            metadata=dict(attrs.get("metadata") or {}),
        )

    def __repr__(self) -> str:
        return (
            f"ConsentGrant(grant_id={self.grant_id!r}, "
            f"status={self.status!r}, "
            f"fitted_model_asset_id={self.fitted_model_asset_id!r}, "
            f"id={self.id!s:.8}...)"
        )


__all__ = ["ConsentGrant"]
