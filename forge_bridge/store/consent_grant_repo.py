"""ConsentGrant repository — the fitted-model consent latch (#161).

Composes the generic ContentAddressedRepo base for content-hash identity +
idempotent insert + immutability discipline on the terms body, AND composes
EventRepo for atomic audit-event emission on every state transition. This is
the GenerationGrantRepo *lineage* (immutable-terms + mutable state-machine),
copied deliberately — but with the CAS/consume path REMOVED. Consent is a
durable latch, not a single-use spend: a person ratifies once, the asset is
bound later at fit, and the terminal is withdrawal (which propagates to asset
revocation), never a consume-flip.

State machine:
    (None)   -> proposed    (via propose())
    proposed -> ratified    (via ratify() — pure state transition)
    proposed -> withdrawn   (via withdraw())
    ratified -> withdrawn   (via withdraw())
    Terminals: withdrawn.

    ``bind_asset`` is NOT a status transition — it stamps the mutable
    ``fitted_model_asset_id`` onto a ratified grant when the model is fit,
    emitting a ``consent_grant.bound`` audit event.

WITHDRAWAL PROPAGATES TO REVOCATION (load-bearing SAFETY):
    ``withdraw`` transitions the grant to withdrawn AND, in the SAME session,
    calls ``revoke_asset`` on the bound fitted-model asset (if any) so
    grant-withdrawn and asset-revoked commit atomically. This is the consent
    ship-blocker for DFL fit: a withdrawn consent must immediately refuse
    inference (via the #160 ``_check_model_not_revoked`` gate). If the grant is
    unbound (no asset yet), there is nothing to revoke — the state just flips.
    Re-withdrawing an already-withdrawn grant is an idempotent no-op (no
    re-transition, no double-revoke).

    There is deliberately NO ``consume_atomic`` / CAS here — consent is not a
    spend, so double-spend is not a failure mode. Withdrawal is a one-way latch.

Immutability composition:
    The CAR base's update() / delete() remain raising — the terms body +
    content_hash are immutable post-insert. State transitions update
    DBEntity.status + DBEntity.attributes in place; the terms body keys
    (owner_of_likeness, allowed_shot_scopes, forbidden_uses, valid_from,
    valid_until, nonce) are never in attribute_updates. ``fitted_model_asset_id``
    is mutable state (bound at fit), NOT a terms-body key.

Atomicity guarantee:
    Status update, audit-event append, and the withdrawal→revocation propagation
    share the same AsyncSession. They either all commit or all rollback; callers
    own transaction boundaries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.core.consent_grant import ConsentGrant
from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.models import DBEntity
from forge_bridge.store.repo import EventRepo, revoke_asset


class ConsentGrantLifecycleError(Exception):
    """Raised when a ConsentGrant transition is not permitted."""

    def __init__(
        self,
        from_status: Optional[str],
        to_status: str,
        record_id: uuid.UUID,
        grant_id: Optional[str] = None,
    ):
        self.from_status = from_status
        self.to_status = to_status
        self.record_id = record_id
        self.grant_id = grant_id
        super().__init__(
            f"Illegal transition from {from_status!r} to {to_status!r} "
            f"for consent_grant {record_id}"
            + (f" (grant_id={grant_id})" if grant_id else "")
        )


class ConsentGrantNotFound(Exception):
    """Raised when no ConsentGrant resolves for a grant_id."""

    def __init__(self, grant_id: str):
        self.grant_id = grant_id
        super().__init__(f"ConsentGrant not found for grant_id={grant_id!r}")


class ConsentGrantBindingError(Exception):
    """Raised when a bind_asset request is rejected.

    Cases: the grant is not ratified (or already withdrawn), or it is already
    bound to a DIFFERENT asset than the one requested.
    """

    def __init__(self, grant_id: str, message: str, *, current_status: Optional[str] = None):
        self.grant_id = grant_id
        self.current_status = current_status
        super().__init__(message)


class ConsentGrantRepo(ContentAddressedRepo[ConsentGrant]):
    """Persist ConsentGrant rows and enforce the consent-latch state machine.

    The SOLE sanctioned write path for consent_grant rows. Direct
    ``session.add(DBEntity(entity_type='consent_grant', ...))`` is prohibited
    (mirror of assent.py:40) — it bypasses audit emission, content-hash
    idempotency, and the atomic withdrawal→revocation propagation that makes a
    withdrawn consent refuse inference.
    """

    __entity_type__ = "consent_grant"
    __model__ = ConsentGrant

    _ALLOWED_TRANSITIONS: frozenset[tuple[Optional[str], str]] = frozenset({
        (None, "proposed"),
        ("proposed", "ratified"),
        ("proposed", "withdrawn"),
        ("ratified", "withdrawn"),
    })

    _TRANSITION_EVENTS: dict[tuple[Optional[str], str], str] = {
        (None, "proposed"): "consent_grant.proposed",
        ("proposed", "ratified"): "consent_grant.ratified",
        ("proposed", "withdrawn"): "consent_grant.withdrawn",
        ("ratified", "withdrawn"): "consent_grant.withdrawn",
    }

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self._events = EventRepo(session)

    @classmethod
    def _default_status(cls, body: dict[str, Any]) -> str:
        _ = body
        return "proposed"

    async def propose(
        self,
        *,
        owner_of_likeness: str,
        allowed_shot_scopes: Optional[list[str]] = None,
        forbidden_uses: Optional[list[str]] = None,
        valid_from: Optional[datetime | str] = None,
        valid_until: Optional[datetime | str] = None,
        nonce: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ConsentGrant:
        """Mint a proposed consent grant. Reversible — no binding, no revoke.

        ``nonce`` defaults to a fresh uuid so every mint is content-unique; two
        identical-terms grants therefore never collapse onto one row (and can
        never resurrect a withdrawn grant). ``fitted_model_asset_id`` is NOT in
        the terms body — it is mutable state bound later via ``bind_asset`` (the
        grant is ratified for a person before the model exists).
        """
        scopes = list(allowed_shot_scopes) if allowed_shot_scopes is not None else ["this_clip_only"]
        forbidden = list(forbidden_uses or [])
        body: dict[str, Any] = {
            "owner_of_likeness": owner_of_likeness,
            "allowed_shot_scopes": scopes,
            "forbidden_uses": forbidden,
            "valid_from": _iso_or_none(valid_from),
            "valid_until": _iso_or_none(valid_until),
            "nonce": nonce or uuid.uuid4().hex,
        }
        if metadata is not None:
            body["metadata"] = dict(metadata)
        content_hash = self._canonical_hash(body)
        existing = await self.get_by_content_hash(content_hash)
        if existing is not None:
            return existing

        record = await self.insert_if_absent(body, project_id=project_id)
        db_entity = await self.session.get(DBEntity, record.id)
        if db_entity is None:
            raise ConsentGrantNotFound(content_hash[:12])
        db_entity.name = f"consent_grant:{content_hash[:12]}"

        await self._append_event(
            record_id=record.id,
            old_status=None,
            new_status="proposed",
            actor="bridge",
            grant_id=content_hash[:12],
            project_id=project_id,
            extra_payload={
                "owner_of_likeness": owner_of_likeness,
                "allowed_shot_scopes": scopes,
                "requires_ratification": True,
            },
        )
        return ConsentGrant.from_entity(db_entity)

    async def ratify(self, grant_id: str, actor: str) -> ConsentGrant:
        """Advance proposed -> ratified and record operator/policy assent.

        A pure state transition: consent is granted for a person here; the
        fitted-model asset is bound later (bind_asset), once the model exists.
        """
        decided_at = datetime.now(timezone.utc)
        return await self._transition(
            grant_id=grant_id,
            new_status="ratified",
            actor=actor,
            attribute_updates={
                "decided_by": actor,
                "decided_at": decided_at.isoformat(),
            },
            event_payload={
                "decided_by": actor,
                "decided_at": decided_at.isoformat(),
            },
        )

    async def bind_asset(
        self,
        grant_id: str,
        asset_id: uuid.UUID | str,
        *,
        actor: str = "operator",
    ) -> ConsentGrant:
        """Bind the fitted-model asset to a ratified grant (the fit-time stamp).

        ``fitted_model_asset_id`` is mutable state — the grant was ratified for a
        person before the model existed; fit binds the trained asset id here. NOT
        a status transition. Emits ``consent_grant.bound``.

        Rules:
          - only on a ``ratified`` grant (reject if proposed / withdrawn);
          - idempotent for the SAME asset (no-op, no duplicate event);
          - reject binding a DIFFERENT asset when already bound.
        """
        # Validate the asset_id is a well-formed UUID up front and normalize it.
        # A malformed id must be rejected HERE (house-style error), never bound:
        # withdraw() later coerces the bound id via uuid.UUID(...) and a raw
        # ValueError there aborts the withdraw + rolls the grant back to ratified,
        # stranding it permanently un-withdrawable (fail-closed but stuck).
        try:
            asset_id_uuid = uuid.UUID(str(asset_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ConsentGrantBindingError(
                grant_id,
                f"cannot bind consent_grant {grant_id} to malformed asset_id "
                f"{asset_id!r}: not a valid UUID",
            ) from exc
        asset_id_str = str(asset_id_uuid)
        grant = await self.get_by_grant_id(grant_id)
        if grant is None:
            raise ConsentGrantNotFound(grant_id)

        db_entity = await self.session.get(DBEntity, grant.id)
        if db_entity is None:
            raise ConsentGrantNotFound(grant_id)

        if db_entity.status != "ratified":
            raise ConsentGrantBindingError(
                grant_id,
                f"cannot bind asset to consent_grant {grant_id} in status "
                f"{db_entity.status!r}; a grant must be ratified to bind",
                current_status=db_entity.status,
            )

        # Assert the fitted-model asset row actually exists (and is an asset).
        # bind_asset runs at fit-time AFTER the asset is created, so it MUST exist
        # at bind — asserting it does not break the "ratified before asset exists"
        # flow (ratify precedes fit; bind follows asset creation). Binding a
        # nonexistent / non-asset id would strand the grant the same way a
        # malformed id does: withdraw()'s revoke_asset raises on the missing row.
        asset_entity = await self.session.get(DBEntity, asset_id_uuid)
        if asset_entity is None or asset_entity.entity_type != "asset":
            raise ConsentGrantBindingError(
                grant_id,
                f"cannot bind consent_grant {grant_id} to asset {asset_id_str}: "
                f"no such asset entity",
                current_status=db_entity.status,
            )

        attrs = dict(db_entity.attributes or {})
        already = attrs.get("fitted_model_asset_id")
        if already is not None:
            if already == asset_id_str:
                # Idempotent same-asset bind — no-op, no duplicate event.
                return ConsentGrant.from_entity(db_entity)
            raise ConsentGrantBindingError(
                grant_id,
                f"consent_grant {grant_id} is already bound to asset {already!r}; "
                f"refusing to rebind to {asset_id_str!r}",
                current_status=db_entity.status,
            )

        attrs["fitted_model_asset_id"] = asset_id_str
        db_entity.attributes = attrs  # reassign so the JSONB mutation is detected

        await self._events.append(
            event_type="consent_grant.bound",
            payload={
                "grant_id": grant_id,
                "fitted_model_asset_id": asset_id_str,
                "actor": actor,
                "operation": "consent_grant",
                "bound_at": datetime.now(timezone.utc).isoformat(),
            },
            client_name=actor,
            project_id=db_entity.project_id,
            entity_id=db_entity.id,
        )
        return ConsentGrant.from_entity(db_entity)

    async def withdraw(
        self,
        grant_id: str,
        *,
        reason: str = "consent_withdrawn",
        actor: str = "operator",
    ) -> ConsentGrant:
        """Withdraw consent — the load-bearing safety path (#161).

        Transitions proposed|ratified -> withdrawn, stamps ``withdrawn_at``, and
        emits ``consent_grant.withdrawn``. THEN, in the SAME session, if the grant
        is bound to a fitted-model asset, calls ``revoke_asset`` so the grant is
        withdrawn AND the asset revoked atomically (they commit or roll back
        together). A withdrawn consent therefore immediately refuses inference via
        the #160 ``_check_model_not_revoked`` gate.

        Idempotent: re-withdrawing an already-withdrawn grant is a no-op — no
        re-transition, no second event, no double-revoke.
        """
        grant = await self.get_by_grant_id(grant_id)
        if grant is None:
            raise ConsentGrantNotFound(grant_id)

        db_entity = await self.session.get(DBEntity, grant.id)
        if db_entity is None:
            raise ConsentGrantNotFound(grant_id)

        # Idempotent no-op: already withdrawn → return as-is, no double-revoke.
        if db_entity.status == "withdrawn":
            return ConsentGrant.from_entity(db_entity)

        withdrawn_at = datetime.now(timezone.utc)
        # inline authority-boundary: transition flips durable consent to withdrawn.
        updated = await self._transition(
            grant_id=grant_id,
            new_status="withdrawn",
            actor=actor,
            attribute_updates={
                "withdrawn_at": withdrawn_at.isoformat(),
                "withdrawal_reason": reason,
            },
            event_payload={
                "actor": actor,
                "reason": reason,
                "withdrawn_at": withdrawn_at.isoformat(),
            },
        )

        # Propagate to asset revocation IN THE SAME SESSION so withdrawal and
        # revocation are atomic (#160 revoke_asset). Unbound grant → nothing to
        # revoke, just the state flip above.
        asset_id_str = updated.fitted_model_asset_id
        if asset_id_str:
            await revoke_asset(
                self.session,
                uuid.UUID(str(asset_id_str)),  # authority-class arg: the bound model
                reason=reason,
                actor=actor,
            )
        return updated

    async def get_by_grant_id(self, grant_id: str) -> Optional[ConsentGrant]:
        """Lookup by 12-char grant_id prefix (content_hash prefix)."""
        result = await self.session.execute(
            select(DBEntity)
            .where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.content_hash.like(f"{grant_id}%"),
            )
            .order_by(DBEntity.created_at.desc())
            .limit(1)
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return ConsentGrant.from_entity(entity)

    async def list_grants(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConsentGrant], int]:
        """List grants optionally filtered by status."""
        filters = [DBEntity.entity_type == self.__entity_type__]
        if status is not None:
            filters.append(DBEntity.status == status)
        total = (
            await self.session.execute(
                select(func.count()).select_from(DBEntity).where(*filters)
            )
        ).scalar_one()
        result = await self.session.execute(
            select(DBEntity)
            .where(*filters)
            .order_by(DBEntity.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [ConsentGrant.from_entity(r) for r in result.scalars()], total

    async def _transition(
        self,
        grant_id: str,
        new_status: str,
        actor: str,
        attribute_updates: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> ConsentGrant:
        grant = await self.get_by_grant_id(grant_id)
        if grant is None:
            raise ConsentGrantNotFound(grant_id)

        db_entity = await self.session.get(DBEntity, grant.id)
        if db_entity is None:
            raise ConsentGrantNotFound(grant_id)
        old_status = db_entity.status
        if (old_status, new_status) not in self._ALLOWED_TRANSITIONS:
            raise ConsentGrantLifecycleError(
                old_status, new_status, db_entity.id, grant_id,
            )

        db_entity.status = new_status
        attrs = dict(db_entity.attributes or {})
        attrs.update(attribute_updates)
        db_entity.attributes = attrs

        await self._append_event(
            record_id=db_entity.id,
            old_status=old_status,
            new_status=new_status,
            actor=actor,
            grant_id=grant_id,
            project_id=db_entity.project_id,
            extra_payload=event_payload,
        )
        return ConsentGrant.from_entity(db_entity)

    async def _append_event(
        self,
        record_id: uuid.UUID,
        old_status: Optional[str],
        new_status: str,
        actor: str,
        grant_id: str,
        project_id: Optional[uuid.UUID],
        extra_payload: dict[str, Any],
    ) -> None:
        event_type = self._TRANSITION_EVENTS.get(
            (old_status, new_status), "consent_grant.withdrawn",
        )
        payload = {
            "old_status": old_status,
            "new_status": new_status,
            "actor": actor,
            "operation": "consent_grant",
            "transition_at": datetime.now(timezone.utc).isoformat(),
            "grant_id": grant_id,
        }
        payload.update(extra_payload)
        await self._events.append(
            event_type=event_type,
            payload=payload,
            client_name=actor,
            project_id=project_id,
            entity_id=record_id,
        )


def _iso_or_none(value: Optional[datetime | str]) -> Optional[str]:
    """Coerce a datetime | ISO-str | None to an ISO-8601 string | None for the
    content-hashed terms body (must be JSON-serializable and canonical)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


__all__ = [
    "ConsentGrantRepo",
    "ConsentGrantLifecycleError",
    "ConsentGrantNotFound",
    "ConsentGrantBindingError",
]
