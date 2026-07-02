"""Bridge-local ``author_prompt`` GenerationDriver (#66 Slice 1, C1).

A minimal :class:`GenerationDriverProtocol` implementation backed by bridge's
existing local Ollama capability (``LLMRouter.acomplete``). It exists so the
manual author -> QC -> re-author loop (``forge_bridge.orchestration.manual_qc``)
is *self-contained on a stock install*: with zero federation siblings present,
``_select_author_backend`` still finds a local ``ollama-api`` author driver.

Shape (C1, synchronous author):

* ``submit`` extracts the author prompt (and any QC-correction note) from the
  invocation envelope, calls ``acomplete`` once (local Ollama, ``sensitive=True``
  — the free local model, no data egress), caches the authored text keyed by the
  synthetic ``request_id``, and returns a :class:`DriverSubmitResult`.
* ``poll`` returns a TERMINAL :class:`DriverPollResult` (``next_state="complete"``)
  carrying the cached text in ``terminal_provenance["text"]`` — the exact field
  ``manual_qc._artifact_text`` reads. Because ``acomplete`` is one-shot blocking,
  the FIRST poll is already terminal; there is no poll loop (C2 is deferred).

This is the adapter only. Grant mint/ratify/consume and the whole preview/pause
state machine stay in ``manual_qc`` / ``dispatcher`` — this driver is merely the
thing the shipped chokepoint consumes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from forge_bridge.orchestration.drivers import (
    DriverPollResult,
    DriverSubmitResult,
    backend_id_from_identity_triple,
)

if TYPE_CHECKING:
    from forge_bridge.llm.router import LLMRouter
    from forge_bridge.orchestration.dispatcher import InvocationEnvelope
    from forge_bridge.store.orch_entity_views import DBOrchGenerationArtifact

__all__ = ["OllamaAuthorDriver", "AUTHOR_SURFACE"]

# The surface token ``_select_author_backend`` matches on to find a local,
# no-egress author driver. Keep in lockstep with manual_qc's selection guard.
AUTHOR_SURFACE = "ollama-api"

_AUTHOR_SYSTEM_PROMPT = (
    "You are drafting short creative prompt text for a VFX shot. "
    "Respond with only the drafted text — no preamble, no quotes, no commentary."
)


class OllamaAuthorDriver:
    """Local-Ollama-backed ``author_prompt`` driver (implements the protocol).

    The backend identity triple's ``path``/``revision`` are the router's local
    model, so the composite ``backend_id`` (``ollama-api.<model>``) is stable and
    round-trips through the planner/poller the same way sibling drivers do.
    """

    def __init__(self, router: "LLMRouter" | None = None) -> None:
        if router is None:
            # Import lazily: constructing the router only reads env (clients are
            # lazy), so this stays cheap and keeps the [llm] extra off the import
            # path for callers who never build the default driver.
            from forge_bridge.llm.router import LLMRouter

            router = LLMRouter()
        self._router = router
        model = str(getattr(router, "local_model", "") or "local")
        self.backend_identity_triple: dict[str, Any] = {
            "surface": AUTHOR_SURFACE,
            "path": model,
            "revision": model,
        }
        self.backend_id: str = str(
            backend_id_from_identity_triple(self.backend_identity_triple)
        )
        self._text_by_request: dict[str, str] = {}

    async def submit(self, invocation: "InvocationEnvelope") -> DriverSubmitResult:
        prompt = _author_prompt(invocation)
        text = await self._router.acomplete(
            prompt,
            sensitive=True,  # local Ollama only — never egress the shot intent.
            system=_AUTHOR_SYSTEM_PROMPT,
        )
        request_id = uuid.uuid4().hex
        self._text_by_request[request_id] = text
        return DriverSubmitResult(
            request_id=request_id,
            submitted_at=datetime.now(timezone.utc),
            raw_response_summary={
                "surface": AUTHOR_SURFACE,
                "model": self.backend_identity_triple["path"],
                "text_length": len(text),
            },
        )

    async def poll(
        self, artifact: "DBOrchGenerationArtifact"
    ) -> DriverPollResult:
        provenance = artifact.execution_provenance
        request_id = (
            provenance.get("request_id") if isinstance(provenance, dict) else None
        )
        # First poll IS terminal: acomplete returned the full text at submit, so
        # there is nothing to wait for. Returning non-terminal here would pause
        # the run with NO authored text (a silent bug) — so this is always
        # complete + terminal_provenance carrying the text.
        text = self._text_by_request.get(str(request_id), "")
        return DriverPollResult(
            next_state="complete",
            polling_event={"raw_status": "complete", "request_id": request_id},
            terminal_provenance={"request_id": request_id, "text": text},
        )


def _author_prompt(invocation: "InvocationEnvelope") -> str:
    """Build the authoring prompt from the envelope's typed inputs.

    The structural input carries ``metadata.prompt`` (the base intent); a
    remediation attempt adds an editorial input carrying ``metadata.qc_correction``.
    """
    base = ""
    correction: str | None = None
    for ref in invocation.inputs:
        metadata = getattr(ref, "metadata", None) or {}
        if not base and isinstance(metadata.get("prompt"), str):
            base = metadata["prompt"]
        note = metadata.get("qc_correction")
        if isinstance(note, str) and note:
            correction = note

    lines = []
    if base:
        lines.append(f"Draft a single vivid one-line beat for: {base}")
    else:
        lines.append("Draft a single vivid one-line beat.")
    if correction:
        lines.append(f"Revise it to address this QC note: {correction}")
    return "\n".join(lines)
