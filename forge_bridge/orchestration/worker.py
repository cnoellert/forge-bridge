"""Generation polling worker (Phase 4B §6)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import ClassVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from forge_bridge.orchestration.drivers import (
    GenerationDriverRegistry,
    resolve_backend_id,
)
from forge_bridge.store.orch_entity_views import DBOrchGenerationArtifact
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.repo import EventRepo

logger = logging.getLogger(__name__)


@dataclass
class PollPassResult:
    processed: int
    transitioned: int
    terminal: int
    errors: int
    no_driver: int


class GenerationPoller:
    """Polling worker for non-terminal generation artifacts.

    Knows artifacts, not runs. Per-artifact single-transaction discipline;
    never calls GraphEngine — terminal events are consumed by the engine later.
    """

    DEFAULT_POLL_INTERVAL_SECONDS: ClassVar[float] = 5.0

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        driver_registry: GenerationDriverRegistry,
        *,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> None:
        self._session_factory = session_factory
        self._driver_registry = driver_registry
        self._poll_interval_seconds = poll_interval_seconds

    async def poll_once(self) -> PollPassResult:
        async with self._session_factory() as session:
            repo = GenerationArtifactRepo(session)
            artifacts = await repo.find_non_terminal()

        result = PollPassResult(
            processed=0,
            transitioned=0,
            terminal=0,
            errors=0,
            no_driver=0,
        )

        for artifact in artifacts:
            outcome = await self._poll_artifact(artifact)
            result.processed += 1
            if outcome == "transitioned":
                result.transitioned += 1
            elif outcome == "terminal":
                result.transitioned += 1
                result.terminal += 1
            elif outcome == "error":
                result.errors += 1
            elif outcome == "no_driver":
                result.no_driver += 1

        if result.processed:
            logger.info(
                "Generation poll pass complete: processed=%d transitioned=%d "
                "terminal=%d errors=%d no_driver=%d",
                result.processed,
                result.transitioned,
                result.terminal,
                result.errors,
                result.no_driver,
            )

        return result

    async def run_forever(
        self,
        *,
        shutdown_event: asyncio.Event | None = None,
    ) -> None:
        while True:
            await self.poll_once()
            if shutdown_event is not None and shutdown_event.is_set():
                return
            await asyncio.sleep(self._poll_interval_seconds)

    async def _poll_artifact(self, artifact: DBOrchGenerationArtifact) -> str:
        async with self._session_factory() as session:
            repo = GenerationArtifactRepo(session)
            events = EventRepo(session)

            current = await repo.get_by_id(artifact.id)
            if current is None:
                logger.warning(
                    "Artifact %s disappeared before poll; skipping",
                    artifact.id,
                )
                return "skipped"

            backend_id = resolve_backend_id(current)
            if backend_id is None:
                backend_id = "unknown"

            driver = (
                self._driver_registry.get_driver(backend_id)
                if backend_id != "unknown"
                else None
            )
            if driver is None:
                await events.append(
                    "generation_artifact_no_driver",
                    {
                        "artifact_id": str(current.id),
                        "backend_id": backend_id,
                    },
                    entity_id=current.id,
                )
                await session.commit()
                logger.warning(
                    "No driver registered for artifact %s backend_id=%s",
                    current.id,
                    backend_id,
                )
                return "no_driver"

            try:
                poll_result = await driver.poll(current)
            except Exception as exc:
                await events.append(
                    "generation_artifact_polling_error",
                    {
                        "artifact_id": str(current.id),
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                    entity_id=current.id,
                )
                await session.commit()
                logger.warning(
                    "Polling error for artifact %s: %s",
                    current.id,
                    exc,
                )
                return "error"

            state_unchanged = poll_result.next_state == current.lifecycle_state
            has_terminal_payload = (
                poll_result.terminal_provenance is not None
                or poll_result.partial_fidelity_report is not None
            )

            artifact_id = current.id
            try:
                if state_unchanged and not has_terminal_payload:
                    await repo.transition(
                        current.id,
                        current.lifecycle_state,
                        polling_event=poll_result.polling_event,
                    )
                    await session.commit()
                    return "polled"

                await repo.transition(
                    current.id,
                    poll_result.next_state,
                    polling_event=poll_result.polling_event,
                    terminal_provenance=poll_result.terminal_provenance,
                    partial_fidelity_report=poll_result.partial_fidelity_report,
                )

                if poll_result.next_state in GenerationArtifactRepo.TERMINAL_STATES:
                    run_id = current.run_id
                    await events.append(
                        "generation_artifact_terminal",
                        {
                            "artifact_id": str(current.id),
                            "run_id": str(run_id) if run_id is not None else None,
                            "terminal_state": poll_result.next_state,
                            "terminal_provenance": poll_result.terminal_provenance,
                            "partial_fidelity_report": poll_result.partial_fidelity_report,
                        },
                        entity_id=current.id,
                    )

                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.warning(
                    "Transaction failed for artifact %s: %s",
                    artifact_id,
                    exc,
                )
                return "error"

            if poll_result.next_state in GenerationArtifactRepo.TERMINAL_STATES:
                return "terminal"
            return "transitioned"
