"""Identity registry protocols and v0.1 in-memory implementations (Phase 4B §5)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class TrainedIdentityRecord:
    identity_id: uuid.UUID
    backend_id: str
    validity_window: tuple[datetime, datetime | None]
    reuse_constraints: dict


class PlatformUUIDRegistryProtocol(Protocol):
    async def lookup(
        self,
        content_sha256: str,
        backend_id: str,
    ) -> str | None:
        """Platform UUID if uploaded to backend; None otherwise."""


class InMemoryPlatformUUIDRegistry:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], str] = {}

    def register(
        self,
        *,
        content_sha256: str,
        backend_id: str,
        platform_uuid: str,
    ) -> None:
        self._entries[(content_sha256, backend_id)] = platform_uuid

    async def lookup(
        self,
        content_sha256: str,
        backend_id: str,
    ) -> str | None:
        return self._entries.get((content_sha256, backend_id))


class TrainedIdentityRegistryProtocol(Protocol):
    async def lookup(self, identity_id: uuid.UUID) -> TrainedIdentityRecord | None: ...

    async def is_valid_for_context(
        self,
        identity_id: uuid.UUID,
        *,
        shot_id: uuid.UUID,
        as_of: datetime,
    ) -> tuple[bool, str | None]: ...


class InMemoryTrainedIdentityRegistry:
    def __init__(self) -> None:
        self._records: dict[uuid.UUID, TrainedIdentityRecord] = {}

    def register(self, record: TrainedIdentityRecord) -> None:
        self._records[record.identity_id] = record

    async def lookup(self, identity_id: uuid.UUID) -> TrainedIdentityRecord | None:
        return self._records.get(identity_id)

    async def is_valid_for_context(
        self,
        identity_id: uuid.UUID,
        *,
        shot_id: uuid.UUID,
        as_of: datetime | None = None,
    ) -> tuple[bool, str | None]:
        record = self._records.get(identity_id)
        if record is None:
            return True, None

        as_of = as_of or datetime.now(timezone.utc)
        valid_from, valid_until = record.validity_window
        if as_of < valid_from:
            return False, "validity_expired"
        if valid_until is not None and as_of > valid_until:
            return False, "validity_expired"

        allowed_scopes = record.reuse_constraints.get("allowed_shot_scopes")
        if allowed_scopes is not None and str(shot_id) not in allowed_scopes:
            return False, "reuse_forbidden_for_scope"

        return True, None
