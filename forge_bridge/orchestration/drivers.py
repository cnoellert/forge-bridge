"""Generation driver protocol and registry (Phase 4B §6)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from forge_bridge.store.orch_entity_views import DBOrchGenerationArtifact


class DriverReregisteredWarning(UserWarning):
    """Emitted when register_driver overwrites an existing backend_id."""


@runtime_checkable
class GenerationDriverProtocol(Protocol):
    """Implemented by forge-generators per backend.

    Populated into the worker's driver registry via sibling registration
    (Step 8). For Step 7, register drivers directly via
    ``GenerationDriverRegistry.register_driver(driver)``.
    """

    backend_id: str

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


def resolve_backend_id(artifact: DBOrchGenerationArtifact) -> str | None:
    """Canonical backend_id from execution_provenance.backend_identity_triple."""
    execution_provenance = artifact.execution_provenance
    if not isinstance(execution_provenance, dict):
        return None
    triple = execution_provenance.get("backend_identity_triple")
    if not isinstance(triple, dict):
        return None
    surface = triple.get("surface")
    path = triple.get("path")
    if not surface or not path:
        return None
    return f"{surface}.{path}"


class GenerationDriverRegistry:
    """Maps backend_id -> driver.

    Populated directly in Step 7 tests; Step 8 registers sibling drivers.
    """

    def __init__(self) -> None:
        self._drivers: dict[str, GenerationDriverProtocol] = {}

    def register_driver(self, driver: GenerationDriverProtocol) -> None:
        backend_id = driver.backend_id
        if backend_id in self._drivers:
            warnings.warn(
                f"Overwriting existing driver for backend_id={backend_id!r}",
                DriverReregisteredWarning,
                stacklevel=2,
            )
        self._drivers[backend_id] = driver

    def get_driver(self, backend_id: str) -> GenerationDriverProtocol | None:
        return self._drivers.get(backend_id)

    def registered_backends(self) -> frozenset[str]:
        return frozenset(self._drivers)
