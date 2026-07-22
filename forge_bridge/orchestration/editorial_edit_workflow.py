"""forge-bridge #235 / Phase 149 — closed editorial-edit workflow API.

One durable product workflow over the exact-realization + AssentRecord + commit
machinery already present in #229-#231. It exposes five async transitions —
``propose``, ``ratify_apply``, ``status``, ``replay``, ``restore`` — and returns
exactly one closed, path-free ``bridge.editorial_edit_workflow_receipt`` mapping
for every successful transition and every post-propose refusal/failure. A
failure before a durable proposal exists raises ``EditorialEditWorkflowError``.

This is composition, not a second mutation rail. ``propose`` reuses
``discover_live_flame_realization`` +
``build_live_flame_realization_preview_spec`` +
``preview_editorial_delta_for_ratification`` (which persists a proposed
``AssentRecord`` with ``metadata.graph_replay.held_manifest``);
``ratify_apply``/``restore`` reuse ``AssentRecordRepo.ratify`` +
``graph_replay_commit_spec`` through the verify-before-apply
``CommitBoundary``. The Shell never submits a GraphSpec, executor, host method,
delta, manifest, or AssentRecord body.

Boundary discipline (handoff §2/§13): Bridge owns graph composition, assent,
commit, replay, and restore ORCHESTRATION. It does NOT own editorial semantics.
The exact editorial inverse-step derivation for ``restore`` is therefore an
INJECTED callable (``build_inverse_step_plan``); split restore is gated on a
Pipeline-owned version-fork counterpart (§10) and returns
``editorial_workflow_restore_unavailable`` until wired.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from forge_bridge.orchestration.apply_editorial_delta import (
    graph_replay_commit_spec,
    preview_editorial_delta_for_ratification,
)
from forge_bridge.orchestration.live_editorial_vertical import (
    LiveEditorialVerticalError,
    build_live_flame_realization_preview_spec,
    discover_live_flame_realization,
)

PROPOSAL_KIND = "pipeline.traffik.editorial_edit_bridge_proposal"
PROPOSAL_SCHEMA_VERSION = 1
RECEIPT_KIND = "bridge.editorial_edit_workflow_receipt"
RECEIPT_SCHEMA_VERSION = 1

_TRIM_OPERATIONS = frozenset({"trim_tail", "trim_head", "extend_edit"})
_SPLIT_OPERATIONS = frozenset({"split_at_playhead", "split_segment"})

# Stable, path-free refusal codes (handoff §9).
REASON_PROPOSAL_INVALID = "editorial_workflow_proposal_invalid"
REASON_PROPOSAL_NOT_FOUND = "editorial_workflow_proposal_not_found"
REASON_PROPOSAL_CHANGED = "editorial_workflow_proposal_changed"
REASON_STATE_INVALID = "editorial_workflow_state_invalid"
REASON_TRANSITION_INFLIGHT = "editorial_workflow_transition_inflight"
REASON_LIVE_STATE_DRIFT = "editorial_workflow_live_state_drift"
REASON_SEMANTIC_BLOCKED = "editorial_workflow_semantic_capability_blocked"
REASON_SEMANTIC_DRIFT = "editorial_workflow_semantic_capability_drift"
REASON_REALIZATION_BLOCKED = "editorial_workflow_realization_blocked"
REASON_REALIZATION_DRIFT = "editorial_workflow_realization_drift"
REASON_DELTA_DRIFT = "editorial_workflow_delta_drift"
REASON_MANIFEST_INVALID = "editorial_workflow_manifest_invalid"
REASON_ASSENT_INVALID = "editorial_workflow_assent_invalid"
REASON_COMMIT_FAILED = "editorial_workflow_commit_failed"
REASON_REPLAY_UNAVAILABLE = "editorial_workflow_replay_unavailable"
REASON_RESTORE_UNAVAILABLE = "editorial_workflow_restore_unavailable"
REASON_RESTORE_DRIFT = "editorial_workflow_restore_drift"
REASON_RESTORE_FAILED = "editorial_workflow_restore_failed"

# Closed proposal top-level field set (handoff §4). Unknown fields fail closed.
_PROPOSAL_FIELDS = frozenset({
    "kind",
    "schema_version",
    "preview_id",
    "project_id",
    "sequence_id",
    "sequence_name",
    "requested_by",
    "source_authority",
    "source_fingerprint",
    "preview_authority_fingerprint",
    "preview_fingerprint",
    "interaction_fingerprint",
    "source_state_fingerprint",
    "after_state_fingerprint",
    "step_plan",
    "step_plan_fingerprint",
    "delta_fingerprint",
    "semantic_capability_plan_fingerprint",
    "expected_geometry_fingerprint",
    "fingerprint",
})
_SHA256_FIELDS = frozenset({
    "source_fingerprint",
    "preview_authority_fingerprint",
    "preview_fingerprint",
    "interaction_fingerprint",
    "source_state_fingerprint",
    "after_state_fingerprint",
    "step_plan_fingerprint",
    "delta_fingerprint",
    "semantic_capability_plan_fingerprint",
    "expected_geometry_fingerprint",
    "fingerprint",
})

# Ordered receipt keys (handoff §5). The trailing ``fingerprint`` is computed
# over every preceding key.
_RECEIPT_KEYS: tuple[str, ...] = (
    "kind",
    "schema_version",
    "action",
    "status",
    "workflow_id",
    "proposal_id",
    "proposal_fingerprint",
    "preview_id",
    "preview_authority_fingerprint",
    "step_plan_fingerprint",
    "live_state_fingerprint",
    "semantic_capability_plan_fingerprint",
    "realization_plan_fingerprint",
    "delta_fingerprint",
    "manifest_fingerprint",
    "assent_record_id",
    "assent_status",
    "commit_fingerprint",
    "dispatch_authorized",
    "applied",
    "replayed",
    "restored",
    "reason_code",
)


class EditorialEditWorkflowError(Exception):
    """Raised only when propose cannot ground a durable proposal (§3/§5).

    Carries a stable ``code`` and a sanitized, path-free ``message``. The
    Pipeline adapter translates it into the Pipeline workflow error.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = _sanitize(message)
        super().__init__(f"{code}: {self.message}")


def canonical_fingerprint(value: Any) -> str:
    """sha256 over canonical JSON (handoff §4)."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Durable workflow store
# --------------------------------------------------------------------------- #
class EditorialEditWorkflowStore(Protocol):
    """Durable correlation store keyed by ``proposal_id`` (handoff §6)."""

    async def get_by_proposal_id(
        self, proposal_id: str
    ) -> Optional[dict[str, Any]]: ...

    async def get_by_preview_authority_fingerprint(
        self, fingerprint: str
    ) -> Optional[dict[str, Any]]: ...

    async def create(self, record: dict[str, Any]) -> dict[str, Any]: ...

    async def update(
        self, proposal_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]: ...


class InMemoryEditorialEditWorkflowStore:
    """Process-local store. NOT durable across restarts — for tests and for a
    stock install without Postgres. Production uses the session-factory store.

    ponytail: a plain dict; the DB store is the authority per handoff §6.
    """

    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}

    async def get_by_proposal_id(
        self, proposal_id: str
    ) -> Optional[dict[str, Any]]:
        row = self._rows.get(proposal_id)
        return dict(row) if row is not None else None

    async def get_by_preview_authority_fingerprint(
        self, fingerprint: str
    ) -> Optional[dict[str, Any]]:
        for row in self._rows.values():
            if row.get("preview_authority_fingerprint") == fingerprint:
                return dict(row)
        return None

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        proposal_id = str(record["proposal_id"])
        if proposal_id in self._rows:
            raise ValueError(f"workflow already exists: {proposal_id}")
        self._rows[proposal_id] = dict(record)
        return dict(record)

    async def update(
        self, proposal_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        row = self._rows[proposal_id]
        row.update(patch)
        return dict(row)


class SessionFactoryEditorialEditWorkflowStore:
    """Durable store backed by ``EditorialEditWorkflowRepo`` + a session factory.

    Opens and commits one session per operation, matching the repo's
    caller-owns-the-transaction contract.
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def get_by_proposal_id(
        self, proposal_id: str
    ) -> Optional[dict[str, Any]]:
        from forge_bridge.store.editorial_edit_workflow_repo import (
            EditorialEditWorkflowRepo,
        )

        async with self._session_factory() as session:
            return await EditorialEditWorkflowRepo(session).get_by_proposal_id(
                proposal_id
            )

    async def get_by_preview_authority_fingerprint(
        self, fingerprint: str
    ) -> Optional[dict[str, Any]]:
        from forge_bridge.store.editorial_edit_workflow_repo import (
            EditorialEditWorkflowRepo,
        )

        async with self._session_factory() as session:
            repo = EditorialEditWorkflowRepo(session)
            return await repo.get_by_preview_authority_fingerprint(fingerprint)

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        from forge_bridge.store.editorial_edit_workflow_repo import (
            EditorialEditWorkflowRepo,
        )

        async with self._session_factory() as session:
            created = await EditorialEditWorkflowRepo(session).create(record)
            await session.commit()
            return created

    async def update(
        self, proposal_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        from forge_bridge.store.editorial_edit_workflow_repo import (
            EditorialEditWorkflowRepo,
        )

        async with self._session_factory() as session:
            repo = EditorialEditWorkflowRepo(session)
            current = await repo.get_by_proposal_id(proposal_id)
            merged = dict(current or {})
            merged.update(patch)
            updated = await repo.update(proposal_id, merged)
            await session.commit()
            return updated


# --------------------------------------------------------------------------- #
# The API
# --------------------------------------------------------------------------- #
PreviewFn = Callable[..., Awaitable[dict[str, Any]]]
ApplyFn = Callable[..., Awaitable[dict[str, Any]]]
BuildInverseFn = Callable[..., Awaitable[Mapping[str, Any]]]


class EditorialEditWorkflowAPI:
    """Closed editorial-edit workflow over exact realization + assent + commit."""

    def __init__(
        self,
        *,
        run_operation: Callable[..., Any],
        preview_fn: PreviewFn,
        apply_fn: ApplyFn,
        store: EditorialEditWorkflowStore,
        build_inverse_step_plan: Optional[BuildInverseFn] = None,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        self._run_operation = run_operation
        self._preview_fn = preview_fn
        self._apply_fn = apply_fn
        self._store = store
        self._build_inverse = build_inverse_step_plan
        self._clock = clock or _utc_now_iso
        # ponytail: per-process async lock keyed by proposal_id serializes
        # ratify_apply/restore. Multi-worker deployments need a DB advisory
        # lock; the durable status guard below is the cross-process backstop.
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    # -- propose ----------------------------------------------------------- #
    async def propose(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        normalized = _validate_proposal(proposal)
        proposal_fingerprint = normalized["fingerprint"]
        proposal_id = _proposal_id(proposal_fingerprint)
        workflow_id = _workflow_id(proposal_fingerprint)

        existing = await self._store.get_by_proposal_id(proposal_id)
        if existing is not None:
            # Exact duplicate: return the original proposed receipt (§7.1.2).
            return _build_receipt("propose", existing)

        collision = await self._store.get_by_preview_authority_fingerprint(
            normalized["preview_authority_fingerprint"]
        )
        if collision is not None:
            raise EditorialEditWorkflowError(
                REASON_PROPOSAL_INVALID,
                "preview authority already bound to a different proposal",
            )

        discovery = await self._discover(normalized)
        realization = discovery["realization_discovery"]
        # Stale-preview fence (§7.1.4) and held-fingerprint fences (§7.1.5).
        _fence(
            discovery["live_state_fingerprint"]
            == normalized["source_state_fingerprint"],
            REASON_LIVE_STATE_DRIFT,
            "fresh live state does not match the held preview",
        )
        _fence(
            discovery["step_plan_fingerprint"]
            == normalized["step_plan_fingerprint"],
            REASON_SEMANTIC_DRIFT,
            "discovered step-plan fingerprint drifted",
        )
        _fence(
            discovery["semantic_discovery"]["capability_plan_fingerprint"]
            == normalized["semantic_capability_plan_fingerprint"],
            REASON_SEMANTIC_DRIFT,
            "discovered semantic capability plan drifted",
        )
        _fence(
            realization["delta_fingerprint"] == normalized["delta_fingerprint"],
            REASON_DELTA_DRIFT,
            "discovered delta fingerprint drifted",
        )

        preview = await self._preview(normalized, discovery)
        held_manifest = preview["manifest"]
        manifest_fingerprint = canonical_fingerprint(held_manifest)

        now = self._clock()
        record = {
            "kind": "bridge.editorial_edit_workflow",
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "workflow_id": workflow_id,
            "proposal_id": proposal_id,
            "proposal_fingerprint": proposal_fingerprint,
            "proposal": normalized,
            "preview_id": normalized["preview_id"],
            "preview_authority_fingerprint": normalized[
                "preview_authority_fingerprint"
            ],
            "step_plan_fingerprint": normalized["step_plan_fingerprint"],
            "semantic_capability_plan_fingerprint": normalized[
                "semantic_capability_plan_fingerprint"
            ],
            "delta_fingerprint": normalized["delta_fingerprint"],
            "live_state_fingerprint": discovery["live_state_fingerprint"],
            "realization_plan_fingerprint": realization[
                "realization_plan_fingerprint"
            ],
            "forward_graph_intent_id": preview["graph_intent_id"],
            "forward_assent_record_id": preview["assent_record_id"],
            "forward_assent_status": "proposed",
            "forward_manifest_fingerprint": manifest_fingerprint,
            "forward_commit_fingerprint": None,
            "status": "proposed",
            "reason_code": None,
            "replay_observations": 0,
            "restore": None,
            "created_at": now,
            "requested_by": normalized["requested_by"],
            "actors": {"propose": normalized["requested_by"]},
            "timestamps": {"propose": now},
        }
        try:
            stored = await self._store.create(record)
        except Exception as exc:  # noqa: BLE001 - durable persistence failure
            raise EditorialEditWorkflowError(
                REASON_MANIFEST_INVALID,
                "workflow persistence failed after preview",
            ) from exc
        return _build_receipt("propose", stored)

    # -- ratify_apply ------------------------------------------------------ #
    async def ratify_apply(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
        requested_by: str,
    ) -> dict[str, Any]:
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "ratify_apply", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed

        async with self._locks[proposal_id]:
            workflow = await self._store.get_by_proposal_id(proposal_id)
            if workflow is None:
                raise EditorialEditWorkflowError(
                    REASON_PROPOSAL_NOT_FOUND, "workflow disappeared"
                )
            if workflow["status"] != "proposed":
                return _refuse(
                    "ratify_apply", workflow, REASON_STATE_INVALID
                )
            if workflow["forward_assent_status"] != "proposed":
                return _refuse(
                    "ratify_apply", workflow, REASON_ASSENT_INVALID
                )

            outcome = await self._apply_fn(
                graph_intent_id=workflow["forward_graph_intent_id"],
                requested_by=requested_by,
            )
            now = self._clock()
            patch: dict[str, Any] = {
                "forward_assent_status": outcome.get("assent_status"),
                "timestamps": {**workflow["timestamps"], "ratify_apply": now},
                "actors": {**workflow["actors"], "ratify_apply": requested_by},
            }
            if outcome["outcome"] == "applied":
                patch["status"] = "applied"
                patch["reason_code"] = None
                patch["forward_commit_fingerprint"] = canonical_fingerprint(
                    outcome["commit_result"]
                )
                stored = await self._store.update(proposal_id, patch)
                return _build_receipt("ratify_apply", stored)

            reason = outcome.get("reason_code") or REASON_COMMIT_FAILED
            patch["status"] = "failed"
            patch["reason_code"] = reason
            stored = await self._store.update(proposal_id, patch)
            return _build_receipt(
                "ratify_apply", stored, action_status="failed"
            )

    # -- status ------------------------------------------------------------ #
    async def status(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
    ) -> dict[str, Any]:
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "status", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed
        return _build_receipt("status", workflow)

    # -- replay ------------------------------------------------------------ #
    async def replay(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
        requested_by: str,
    ) -> dict[str, Any]:
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "replay", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed
        if workflow["status"] != "applied" or not workflow.get(
            "forward_commit_fingerprint"
        ):
            return _refuse("replay", workflow, REASON_REPLAY_UNAVAILABLE)

        # No new assent/manifest/commit and no host dispatch (§7.4).
        patch = {
            "replay_observations": int(workflow.get("replay_observations", 0))
            + 1,
            "timestamps": {**workflow["timestamps"], "replay": self._clock()},
            "actors": {**workflow["actors"], "replay": requested_by},
        }
        stored = await self._store.update(proposal_id, patch)
        return _build_receipt("replay", stored)

    # -- restore ----------------------------------------------------------- #
    async def restore(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
        requested_by: str,
    ) -> dict[str, Any]:
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "restore", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed

        operation = _forward_operation(workflow)
        if operation in _SPLIT_OPERATIONS:
            # Split restore is gated on the Pipeline version-fork counterpart
            # (§10). Never perform an ungoverned cleanup.
            return _refuse("restore", workflow, REASON_RESTORE_UNAVAILABLE)
        if operation not in _TRIM_OPERATIONS:
            return _refuse("restore", workflow, REASON_RESTORE_UNAVAILABLE)
        if self._build_inverse is None:
            # Trim inverse derivation is editorial semantics — must be injected
            # by the semantic owner (§2/§13). Not wired => gated, never guessed.
            return _refuse("restore", workflow, REASON_RESTORE_UNAVAILABLE)

        async with self._locks[proposal_id]:
            workflow = await self._store.get_by_proposal_id(proposal_id)
            if workflow is None:
                raise EditorialEditWorkflowError(
                    REASON_PROPOSAL_NOT_FOUND, "workflow disappeared"
                )
            if workflow["status"] != "applied":
                # proposed / failed / already-restored never restore (§8).
                return _refuse("restore", workflow, REASON_RESTORE_UNAVAILABLE)

            try:
                inverse_plan = await _maybe_await(
                    self._build_inverse(
                        workflow=workflow, run_operation=self._run_operation
                    )
                )
            except LiveEditorialVerticalError:
                return _refuse("restore", workflow, REASON_RESTORE_DRIFT)

            try:
                inverse_discovery = await self._discover(
                    workflow["proposal"], step_plan=inverse_plan
                )
            except EditorialEditWorkflowError:
                # Fresh host no longer supports the exact inverse => drift (§7.5).
                return _refuse("restore", workflow, REASON_RESTORE_DRIFT)

            inverse_preview = await self._preview(
                workflow["proposal"],
                inverse_discovery,
                step_plan=inverse_plan,
                display="Phase 149 restore inverse",
            )
            inverse_realization = inverse_discovery["realization_discovery"]
            inverse_manifest_fp = canonical_fingerprint(
                inverse_preview["manifest"]
            )

            outcome = await self._apply_fn(
                graph_intent_id=inverse_preview["graph_intent_id"],
                requested_by=requested_by,
            )
            now = self._clock()
            restore_record = {
                "graph_intent_id": inverse_preview["graph_intent_id"],
                "assent_record_id": inverse_preview["assent_record_id"],
                "assent_status": outcome.get("assent_status"),
                "manifest_fingerprint": inverse_manifest_fp,
                "live_state_fingerprint": inverse_discovery[
                    "live_state_fingerprint"
                ],
                "realization_plan_fingerprint": inverse_realization[
                    "realization_plan_fingerprint"
                ],
                "delta_fingerprint": inverse_realization["delta_fingerprint"],
                "commit_fingerprint": None,
            }
            patch: dict[str, Any] = {
                "timestamps": {**workflow["timestamps"], "restore": now},
                "actors": {**workflow["actors"], "restore": requested_by},
            }
            if outcome["outcome"] == "applied":
                restore_record["commit_fingerprint"] = canonical_fingerprint(
                    outcome["commit_result"]
                )
                patch["status"] = "restored"
                patch["reason_code"] = None
                patch["restore"] = restore_record
                stored = await self._store.update(proposal_id, patch)
                return _build_receipt("restore", stored)

            patch["status"] = "applied"  # forward apply still stands
            patch["reason_code"] = REASON_RESTORE_FAILED
            patch["restore"] = restore_record
            stored = await self._store.update(proposal_id, patch)
            return _refuse("restore", stored, REASON_RESTORE_FAILED)

    # -- internals --------------------------------------------------------- #
    async def _discover(
        self,
        proposal: Mapping[str, Any],
        *,
        step_plan: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        plan = step_plan if step_plan is not None else proposal["step_plan"]
        try:
            return await discover_live_flame_realization(
                plan,
                sequence_name=proposal["sequence_name"],
                run_operation=self._run_operation,
                project_id=proposal.get("project_id"),
                requested_by=proposal.get("requested_by")
                or "forge_bridge.editorial_edit_workflow",
            )
        except LiveEditorialVerticalError as exc:
            raise EditorialEditWorkflowError(
                _discovery_reason(str(exc)), "exact realization not trusted"
            ) from exc

    async def _preview(
        self,
        proposal: Mapping[str, Any],
        discovery: Mapping[str, Any],
        *,
        step_plan: Optional[Mapping[str, Any]] = None,
        display: str = "Phase 149 editorial edit",
    ) -> dict[str, Any]:
        plan = step_plan if step_plan is not None else proposal["step_plan"]
        spec = build_live_flame_realization_preview_spec(
            sequence_name=proposal["sequence_name"],
            step_plan=plan,
            realization_discovery=discovery,
            project_id=proposal.get("project_id"),
        )
        try:
            return await self._preview_fn(spec=spec, display=display)
        except EditorialEditWorkflowError:
            raise
        except Exception as exc:  # noqa: BLE001 - preview/persist failure
            raise EditorialEditWorkflowError(
                REASON_MANIFEST_INVALID,
                "preview did not resolve a durable mutation manifest",
            ) from exc

    async def _load_or_raise(self, proposal_id: str) -> dict[str, Any]:
        workflow = await self._store.get_by_proposal_id(proposal_id)
        if workflow is None:
            # No grounded authority to place in a receipt => typed error (§5).
            raise EditorialEditWorkflowError(
                REASON_PROPOSAL_NOT_FOUND,
                "no workflow for the supplied proposal id",
            )
        return workflow


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #
def make_editorial_edit_workflow_api(
    *,
    run_operation: Callable[..., Any],
    session_factory: Any | None = None,
    mcp: Any | None = None,
    store: EditorialEditWorkflowStore | None = None,
    preview_fn: PreviewFn | None = None,
    apply_fn: ApplyFn | None = None,
    build_inverse_step_plan: BuildInverseFn | None = None,
    clock: Callable[[], str] | None = None,
) -> EditorialEditWorkflowAPI:
    """Construct the workflow API.

    Production wiring supplies ``run_operation`` (the Pipeline operation runner),
    ``session_factory`` (durable store + AssentRecord persistence), and ``mcp``
    (the commit rail). Tests inject ``store``/``preview_fn``/``apply_fn`` fakes.
    """
    if store is None:
        if session_factory is None:
            raise ValueError(
                "session_factory is required when store is not supplied"
            )
        store = SessionFactoryEditorialEditWorkflowStore(session_factory)
    if preview_fn is None:
        preview_fn = _default_preview_fn(session_factory, mcp)
    if apply_fn is None:
        apply_fn = _default_apply_fn(session_factory, mcp)
    return EditorialEditWorkflowAPI(
        run_operation=run_operation,
        preview_fn=preview_fn,
        apply_fn=apply_fn,
        store=store,
        build_inverse_step_plan=build_inverse_step_plan,
        clock=clock,
    )


def _default_preview_fn(session_factory: Any, mcp: Any) -> PreviewFn:
    if session_factory is None:
        raise ValueError("session_factory is required for the default preview_fn")

    async def preview_fn(*, spec: Any, display: str) -> dict[str, Any]:
        return await preview_editorial_delta_for_ratification(
            spec,
            session_factory=session_factory,
            mcp=mcp,
            display=display,
        )

    return preview_fn


def _default_apply_fn(session_factory: Any, mcp: Any) -> ApplyFn:
    if session_factory is None:
        raise ValueError("session_factory is required for the default apply_fn")

    async def apply_fn(
        *, graph_intent_id: str, requested_by: str
    ) -> dict[str, Any]:
        return await _ratify_and_commit_graph_replay(
            graph_intent_id=graph_intent_id,
            requested_by=requested_by,
            session_factory=session_factory,
            mcp=mcp,
        )

    return apply_fn


async def _ratify_and_commit_graph_replay(
    *,
    graph_intent_id: str,
    requested_by: str,
    session_factory: Any,
    mcp: Any,
) -> dict[str, Any]:
    """Orchestration-level ratify + verify-before-apply commit of a held manifest.

    A narrower extraction of ``console._chat_compile.run_apply_branch``'s
    graph-replay branch: ratify the proposed AssentRecord, replay the persisted
    held manifest through the ``CommitBoundary``, and finalize the lifecycle.
    """
    from forge_bridge.composition.commit_boundary import CommitBoundary
    from forge_bridge.composition.dispatch import UnifiedDispatch
    from forge_bridge.composition.executor import GraphExecutor
    from forge_bridge.store.assent_record_repo import (
        AssentRecordLifecycleError,
        AssentRecordNotFound,
        AssentRecordRepo,
    )

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        try:
            record = await repo.ratify(graph_intent_id, actor=requested_by)
        except (AssentRecordNotFound, AssentRecordLifecycleError):
            return {
                "outcome": "refused",
                "assent_status": None,
                "reason_code": REASON_ASSENT_INVALID,
                "commit_result": None,
            }

        held_manifest = _held_manifest_from_record(record)
        if held_manifest is None:
            await repo.mark_failed(
                graph_intent_id, reason="assent_invalid", result=None
            )
            await session.commit()
            return {
                "outcome": "failed",
                "assent_status": "failed",
                "reason_code": REASON_MANIFEST_INVALID,
                "commit_result": None,
            }

        graph = graph_replay_commit_spec(held_manifest)
        dispatch = UnifiedDispatch(
            commit_boundary=CommitBoundary(mcp=mcp),
            assent_record=record,
        )
        results = await GraphExecutor(dispatch.dispatch).run(graph)
        commit_result = results["commit"]
        if commit_result.status == "error":
            reason = _apply_failure_reason(commit_result)
            await repo.mark_failed(
                graph_intent_id,
                reason=_assent_failure_reason(commit_result),
                result={"error": _commit_error(commit_result)},
            )
            await session.commit()
            return {
                "outcome": "failed",
                "assent_status": "failed",
                "reason_code": reason,
                "commit_result": _commit_error(commit_result),
            }

        applied = commit_result.output
        await repo.mark_applied(graph_intent_id, result=applied)
        await session.commit()
        return {
            "outcome": "applied",
            "assent_status": "applied",
            "reason_code": None,
            "commit_result": applied,
        }


# --------------------------------------------------------------------------- #
# Validation, receipts, helpers
# --------------------------------------------------------------------------- #
def _validate_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(proposal, Mapping):
        raise EditorialEditWorkflowError(
            REASON_PROPOSAL_INVALID, "proposal must be a mapping"
        )
    extra = set(proposal.keys()) - _PROPOSAL_FIELDS
    if extra:
        raise EditorialEditWorkflowError(
            REASON_PROPOSAL_INVALID,
            f"proposal has unknown fields: {sorted(extra)}",
        )
    missing = _PROPOSAL_FIELDS - set(proposal.keys())
    if missing:
        raise EditorialEditWorkflowError(
            REASON_PROPOSAL_INVALID,
            f"proposal is missing fields: {sorted(missing)}",
        )
    if proposal["kind"] != PROPOSAL_KIND:
        raise EditorialEditWorkflowError(
            REASON_PROPOSAL_INVALID, "proposal kind is not recognized"
        )
    if proposal["schema_version"] != PROPOSAL_SCHEMA_VERSION:
        raise EditorialEditWorkflowError(
            REASON_PROPOSAL_INVALID, "proposal schema_version is not supported"
        )
    for field in _SHA256_FIELDS:
        if not _is_sha256(proposal[field]):
            raise EditorialEditWorkflowError(
                REASON_PROPOSAL_INVALID,
                f"proposal field {field} is not a sha256 hash",
            )

    normalized = {key: proposal[key] for key in _PROPOSAL_FIELDS}
    # Recompute the closed proposal fingerprint (§4): sha256 over every
    # preceding proposal field.
    body = {
        key: value
        for key, value in normalized.items()
        if key != "fingerprint"
    }
    if canonical_fingerprint(body) != normalized["fingerprint"]:
        raise EditorialEditWorkflowError(
            REASON_PROPOSAL_INVALID, "proposal fingerprint mismatch"
        )
    if canonical_fingerprint(normalized["step_plan"]) != normalized[
        "step_plan_fingerprint"
    ]:
        raise EditorialEditWorkflowError(
            REASON_PROPOSAL_INVALID, "step_plan fingerprint mismatch"
        )
    steps = normalized["step_plan"].get("steps") if isinstance(
        normalized["step_plan"], Mapping
    ) else None
    if not isinstance(steps, list) or len(steps) != 1:
        raise EditorialEditWorkflowError(
            REASON_PROPOSAL_INVALID, "proposal step_plan must contain one step"
        )
    return normalized


def _build_receipt(
    action: str,
    workflow: Mapping[str, Any],
    *,
    action_status: Optional[str] = None,
) -> dict[str, Any]:
    status = action_status or _receipt_status(action, workflow)
    restore = workflow.get("restore") or {}
    is_restore_terminal = status == "restored"

    # Immutable forward proposal authority.
    receipt: dict[str, Any] = {
        "kind": RECEIPT_KIND,
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "action": action,
        "status": status,
        "workflow_id": workflow["workflow_id"],
        "proposal_id": workflow["proposal_id"],
        "proposal_fingerprint": workflow["proposal_fingerprint"],
        "preview_id": workflow["preview_id"],
        "preview_authority_fingerprint": workflow[
            "preview_authority_fingerprint"
        ],
        "step_plan_fingerprint": workflow["step_plan_fingerprint"],
        "semantic_capability_plan_fingerprint": workflow[
            "semantic_capability_plan_fingerprint"
        ],
        "delta_fingerprint": workflow["delta_fingerprint"],
    }

    if is_restore_terminal:
        # Inverse identities describe the separately governed restore (§5).
        receipt["live_state_fingerprint"] = restore.get("live_state_fingerprint")
        receipt["realization_plan_fingerprint"] = restore.get(
            "realization_plan_fingerprint"
        )
        receipt["manifest_fingerprint"] = restore.get("manifest_fingerprint")
        receipt["assent_record_id"] = restore.get("assent_record_id")
        receipt["assent_status"] = restore.get("assent_status")
        receipt["commit_fingerprint"] = restore.get("commit_fingerprint")
    else:
        receipt["live_state_fingerprint"] = workflow["live_state_fingerprint"]
        receipt["realization_plan_fingerprint"] = workflow[
            "realization_plan_fingerprint"
        ]
        receipt["manifest_fingerprint"] = workflow[
            "forward_manifest_fingerprint"
        ]
        receipt["assent_record_id"] = workflow["forward_assent_record_id"]
        receipt["assent_status"] = workflow["forward_assent_status"]
        receipt["commit_fingerprint"] = workflow["forward_commit_fingerprint"]

    flags = _receipt_flags(status)
    receipt.update(flags)
    receipt["reason_code"] = (
        workflow.get("reason_code") if status in {"refused", "failed"} else None
    )

    ordered = {key: receipt[key] for key in _RECEIPT_KEYS}
    ordered["fingerprint"] = canonical_fingerprint(ordered)
    return ordered


def _receipt_status(action: str, workflow: Mapping[str, Any]) -> str:
    if action == "propose":
        return "proposed"
    if action == "replay":
        return "replayed"
    # status action mirrors the durable terminal.
    return str(workflow["status"])


def _receipt_flags(status: str) -> dict[str, Any]:
    applied = status == "applied"
    replayed = status == "replayed"
    restored = status == "restored"
    dispatch_authorized = status in {"applied", "replayed", "restored"}
    return {
        "dispatch_authorized": dispatch_authorized,
        "applied": applied,
        "replayed": replayed,
        "restored": restored,
    }


def _refuse(
    action: str, workflow: Mapping[str, Any], reason_code: str
) -> dict[str, Any]:
    refused = dict(workflow)
    refused["reason_code"] = reason_code
    return _build_receipt(action, refused, action_status="refused")


def _fingerprint_refusal(
    action: str,
    workflow: Mapping[str, Any],
    expected_proposal_fingerprint: str,
) -> Optional[dict[str, Any]]:
    if workflow["proposal_fingerprint"] != expected_proposal_fingerprint:
        return _refuse(action, workflow, REASON_PROPOSAL_CHANGED)
    return None


def _forward_operation(workflow: Mapping[str, Any]) -> Optional[str]:
    step_plan = workflow.get("proposal", {}).get("step_plan", {})
    steps = step_plan.get("steps") if isinstance(step_plan, Mapping) else None
    if isinstance(steps, list) and steps and isinstance(steps[0], Mapping):
        return steps[0].get("operation")
    return None


def _held_manifest_from_record(record: Any) -> Optional[dict[str, Any]]:
    metadata = getattr(record, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    replay = metadata.get("graph_replay")
    if not isinstance(replay, dict):
        return None
    held = replay.get("held_manifest")
    return held if isinstance(held, dict) else None


def _apply_failure_reason(commit_result: Any) -> str:
    reason_code = getattr(commit_result, "reason_code", None)
    if reason_code in {"PLAN_STATE_DRIFT", "VERIFICATION_FAILED"}:
        return REASON_COMMIT_FAILED
    if reason_code == "ASSENT_INVALID":
        return REASON_ASSENT_INVALID
    return REASON_COMMIT_FAILED


def _assent_failure_reason(commit_result: Any) -> str:
    reason_code = getattr(commit_result, "reason_code", None)
    if reason_code == "PLAN_STATE_DRIFT":
        return "drift_invalid"
    if reason_code == "ASSENT_INVALID":
        return "assent_invalid"
    return "chain_aborted"


def _commit_error(commit_result: Any) -> dict[str, Any]:
    output = getattr(commit_result, "output", None)
    error = output.get("error") if isinstance(output, dict) else None
    return {
        "type": getattr(commit_result, "reason_code", None),
        "detail": error if isinstance(error, dict) else None,
    }


def _discovery_reason(message: str) -> str:
    lowered = message.casefold()
    if "semantic" in lowered:
        return REASON_SEMANTIC_BLOCKED
    return REASON_REALIZATION_BLOCKED


def _fence(condition: bool, reason_code: str, message: str) -> None:
    if not condition:
        raise EditorialEditWorkflowError(reason_code, message)


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _proposal_id(proposal_fingerprint: str) -> str:
    return f"eew_{proposal_fingerprint[:16]}"


def _workflow_id(proposal_fingerprint: str) -> str:
    return f"eewf_{proposal_fingerprint[:16]}"


def _sanitize(message: str) -> str:
    # Path-free: never leak filesystem paths in the typed error message.
    return " ".join(part for part in str(message).split() if "/" not in part)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


__all__ = [
    "EditorialEditWorkflowAPI",
    "EditorialEditWorkflowError",
    "EditorialEditWorkflowStore",
    "InMemoryEditorialEditWorkflowStore",
    "SessionFactoryEditorialEditWorkflowStore",
    "canonical_fingerprint",
    "make_editorial_edit_workflow_api",
    "PROPOSAL_KIND",
    "RECEIPT_KIND",
]
