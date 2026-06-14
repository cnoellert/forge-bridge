"""Generation driver protocol and registry (Phase 4B §6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from forge_bridge.orchestration.errors import (
    DuplicateGenerationDriverError,
    GenerationDriverBackendIdMismatchError,
    GenerationDriverRegistrationError,
    MissingGenerationDriverBackendIdError,
)
from forge_bridge.store.orch_entity_views import DBOrchGenerationArtifact

if TYPE_CHECKING:
    from forge_bridge.orchestration.dispatcher import InvocationEnvelope


class DriverReregisteredWarning(UserWarning):
    """Legacy warning class retained for import compatibility."""


@runtime_checkable
class GenerationDriverProtocol(Protocol):
    """Implemented by forge-generators per backend.

    Populated into the worker's driver registry via sibling registration
    (Step 8). For Step 7, register drivers directly via
    ``GenerationDriverRegistry.register_driver(driver)``.
    """

    backend_id: str
    backend_identity_triple: dict[str, Any]

    async def submit(
        self,
        invocation: "InvocationEnvelope",
    ) -> "DriverSubmitResult":
        """Submit a generation invocation and return the backend request handle."""

    async def poll(
        self,
        artifact: DBOrchGenerationArtifact,
    ) -> DriverPollResult:
        """Poll the backend for this artifact's current state."""


@dataclass
class DriverPollResult:
    next_state: str
    polling_event: dict
    terminal_provenance: dict | None = None
    partial_fidelity_report: dict | None = None


@dataclass
class DriverSubmitResult:
    request_id: str
    submitted_at: datetime
    raw_response_summary: dict


def backend_id_from_identity_triple(triple: dict[str, Any]) -> str | None:
    """Composite bridge backend id from a backend_identity_triple."""
    surface = triple.get("surface")
    path = triple.get("path")
    if not surface or not path:
        return None
    return f"{surface}.{path}"


def resolve_backend_id(artifact: DBOrchGenerationArtifact) -> str | None:
    """Canonical backend_id from execution_provenance.backend_identity_triple."""
    execution_provenance = artifact.execution_provenance
    if not isinstance(execution_provenance, dict):
        return None
    triple = execution_provenance.get("backend_identity_triple")
    if not isinstance(triple, dict):
        return None
    return backend_id_from_identity_triple(triple)


class GenerationDriverRegistry:
    """Maps backend_id -> driver.

    Populated directly in Step 7 tests; Step 8 registers sibling drivers.
    """

    def __init__(self) -> None:
        self._drivers: dict[str, GenerationDriverProtocol] = {}

    def register_driver(self, driver: GenerationDriverProtocol) -> None:
        # Bridge keys generation drivers by the same composite id the planner
        # emits and the poller reverse-resolves from artifact provenance:
        # backend_identity_triple -> "surface.path". A legacy backend_id-only
        # driver can still register, but a present identity triple is canonical
        # and any divergence is rejected loudly at registration time.
        triple = getattr(driver, "backend_identity_triple", None)
        triple_present = isinstance(triple, dict) and bool(triple)
        triple_backend_id = (
            backend_id_from_identity_triple(triple)
            if isinstance(triple, dict)
            else None
        )
        driver_backend_id = getattr(driver, "backend_id", None)

        if triple_present and triple_backend_id is None:
            raise GenerationDriverRegistrationError(
                "backend_identity_triple must include surface and path"
            )
        if triple_backend_id is not None:
            if driver_backend_id and driver_backend_id != triple_backend_id:
                raise GenerationDriverBackendIdMismatchError(
                    triple_backend_id, str(driver_backend_id)
                )
            backend_id = triple_backend_id
        elif driver_backend_id:
            backend_id = str(driver_backend_id)
        else:
            raise MissingGenerationDriverBackendIdError()

        if backend_id in self._drivers:
            raise DuplicateGenerationDriverError(backend_id)
        self._drivers[backend_id] = driver

    def get_driver(self, backend_id: str) -> GenerationDriverProtocol | None:
        return self._drivers.get(backend_id)

    def registered_backends(self) -> frozenset[str]:
        return frozenset(self._drivers)
