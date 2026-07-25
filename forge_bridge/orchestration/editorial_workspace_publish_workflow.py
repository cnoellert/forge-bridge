"""forge-bridge #242 / Pipeline Phase 156 — workspace publish workflow API.

One durable product workflow over the shot-resource publish transaction rails
already admitted at v1.9.11. It exposes six async transitions — ``propose``,
``ratify_apply``, ``status``, ``replay``, ``propose_recovery``,
``ratify_recovery`` — and returns exactly one closed, path-free
``bridge.editorial_workspace.publish_workflow_receipt`` mapping for every
successful transition and every post-propose refusal. A failure before a
durable proposal exists raises ``EditorialWorkspacePublishWorkflowError``,
which carries a stable ``.code``.

Boundary discipline (handoff §1): Bridge owns graph composition, the
AssentRecord lifecycle, ratification, commit, durable workflow state, replay
observation, and recovery composition. Pipeline owns the workspace, task,
stream, saved Version, canonical path resolution, host transaction planning,
the transaction apply/status/abort tools, and catalog resource semantics. The
Shell names held authority only — it never submits a graph, callable body,
manifest, resolved plan, path, recovery token, or AssentRecord.

Composition (handoff §5). Bridge — not Pipeline — constructs::

    forge_publish_shot_resource_transaction -> commit

``propose`` executes the DISCOVERY node of that composition only (never verify,
never apply) and persists the held manifest on a proposed ``AssentRecord``.
``ratify_apply`` ratifies that record and replays the held manifest through the
existing verify-before-apply ``CommitBoundary`` — which is the same ``commit``
node, executed later under operator assent.

Recovery (handoff §7) is a SEPARATE governed mutation over::

    forge_inspect_shot_resource_publish_transaction   (read-only)
    forge_abort_shot_resource_publish_transaction -> commit

``propose_recovery`` inspects and then discovers; it aborts nothing. Its
manifest, AssentRecord, and commit fingerprints are persisted separately and
NEVER overwrite the forward proposal, callable, manifest, or commit
fingerprints.

Privacy (handoff §4/§8). ``callable_intent`` is private backend-to-Bridge data
carrying absolute paths. It is persisted for verification and replay but never
reaches a receipt, a log line, or an error string. No path, callable intent,
manifest body, resolved plan, graph, journal body, recovery plan, or native
result may occur in a receipt.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Optional

from forge_bridge.orchestration.workflow_core import (
    InMemoryWorkflowStore,
    ProposalTransitionGuard,
    SessionFactoryWorkflowStore,
    WorkflowStore,
    canonical_fingerprint,
    finalize_receipt,
    held_manifest_from_record,
    is_sha256,
    sanitize,
    utc_now_iso,
    workflow_identifier,
)

PROPOSAL_KIND = "pipeline.editorial_workspace.publish_workflow_proposal"
PROPOSAL_SCHEMA_VERSION = 1
RECEIPT_KIND = "bridge.editorial_workspace.publish_workflow_receipt"
RECEIPT_SCHEMA_VERSION = 1

# Durable row discriminator inside the shared orch_workflow_record family.
WORKFLOW_KIND = "bridge.editorial_workspace.publish_workflow"

PUBLISH_TOOL = "forge_publish_shot_resource_transaction"
INSPECT_TOOL = "forge_inspect_shot_resource_publish_transaction"
ABORT_TOOL = "forge_abort_shot_resource_publish_transaction"

CALLABLE_TOOL = PUBLISH_TOOL
CALLABLE_OPERATION_TYPE = "pipeline.shot_resource.publish_transaction.callable"
ABORT_OPERATION_TYPE = (
    "pipeline.shot_resource.publish_transaction.abort.callable"
)
PUBLISH_STATE_OWNER = "federated_transaction"
ABORT_STATE_OWNER = "peer_owned"

# --------------------------------------------------------------------------- #
# Stable, path-free refusal codes (handoff §10)
# --------------------------------------------------------------------------- #
REASON_PROPOSAL_INVALID = "publish_workflow_proposal_invalid"
REASON_PROPOSAL_NOT_FOUND = "publish_workflow_proposal_not_found"
REASON_PROPOSAL_CHANGED = "publish_workflow_proposal_changed"
REASON_CALLABLE_UNAVAILABLE = "publish_workflow_callable_unavailable"
REASON_MANIFEST_INVALID = "publish_workflow_manifest_invalid"
REASON_MANIFEST_DRIFT = "publish_workflow_manifest_drift"
REASON_ASSENT_INVALID = "publish_workflow_assent_invalid"
REASON_COMMIT_FAILED = "publish_workflow_commit_failed"
REASON_STATUS_UNAVAILABLE = "publish_workflow_status_unavailable"
REASON_REPLAY_UNAVAILABLE = "publish_workflow_replay_unavailable"
REASON_RECOVERY_UNAVAILABLE = "publish_workflow_recovery_unavailable"
REASON_RECOVERY_DRIFT = "publish_workflow_recovery_drift"
REASON_RECOVERY_FAILED = "publish_workflow_recovery_failed"

# Receipt statuses (handoff §8) — note there is NO "refused" taxon; a
# post-propose refusal is reported as "failed" (something was attempted and did
# not stand) or "unavailable" (the transition is not on offer at all).
_REFUSAL_STATUS: dict[str, str] = {
    REASON_PROPOSAL_CHANGED: "failed",
    REASON_CALLABLE_UNAVAILABLE: "unavailable",
    REASON_MANIFEST_INVALID: "failed",
    REASON_MANIFEST_DRIFT: "failed",
    REASON_ASSENT_INVALID: "failed",
    REASON_COMMIT_FAILED: "failed",
    REASON_STATUS_UNAVAILABLE: "unavailable",
    REASON_REPLAY_UNAVAILABLE: "unavailable",
    REASON_RECOVERY_UNAVAILABLE: "unavailable",
    REASON_RECOVERY_DRIFT: "failed",
    REASON_RECOVERY_FAILED: "failed",
}

_TRUSTED_STATUSES = frozenset(
    {"proposed", "applied", "recovery_proposed", "aborted"}
)

# --------------------------------------------------------------------------- #
# Closed field sets (handoff §4)
# --------------------------------------------------------------------------- #
_PROPOSAL_FIELDS = frozenset({
    "kind",
    "schema_version",
    "project_id",
    "requested_by",
    "publish_preview_id",
    "publish_preview_fingerprint",
    "transaction_batch_fingerprint",
    "callable_intent_fingerprint",
    "owner_id",
    "owner_type",
    "sequence_id",
    "task",
    "role",
    "stream",
    "source_version_id",
    "source_package_fingerprint",
    "selected_roles",
    "callable_intent",
    "fingerprint",
})
_PROPOSAL_TEXT_FIELDS = (
    "project_id",
    "requested_by",
    "publish_preview_id",
    "owner_id",
    "owner_type",
    "sequence_id",
    "task",
    "role",
    "stream",
    "source_version_id",
)
_PROPOSAL_SHA256_FIELDS = (
    "publish_preview_fingerprint",
    "transaction_batch_fingerprint",
    "callable_intent_fingerprint",
    "source_package_fingerprint",
    "fingerprint",
)
_CALLABLE_INTENT_FIELDS = frozenset({
    "tool",
    "operation_type",
    "params",
    "bridge_asset_ids",
    "idempotency_key",
    "project_id",
    "requested_by",
})

# Ordered receipt keys (handoff §8). ``fingerprint`` is canonical SHA-256 over
# every receipt field EXCEPT kind, schema_version, and fingerprint.
_RECEIPT_KEYS: tuple[str, ...] = (
    "kind",
    "schema_version",
    "action",
    "status",
    "trust_status",
    "workflow_id",
    "proposal_id",
    "proposal_fingerprint",
    "publish_preview_id",
    "publish_preview_fingerprint",
    "transaction_batch_fingerprint",
    "callable_intent_fingerprint",
    "transaction_id",
    "selected_roles",
    "published_asset_ids",
    "manifest_fingerprint",
    "assent_record_id",
    "assent_status",
    "commit_fingerprint",
    "transaction_status",
    "recovery_status",
    "recovery_manifest_fingerprint",
    "recovery_assent_record_id",
    "recovery_assent_status",
    "recovery_commit_fingerprint",
    "dispatch_authorized",
    "applied",
    "replayed",
    "reason_code",
)
_RECEIPT_FINGERPRINT_EXCLUDES = frozenset({"kind", "schema_version"})

_ACTIONS = frozenset({
    "propose",
    "ratify_apply",
    "status",
    "replay",
    "propose_recovery",
    "ratify_recovery",
})
_STATUSES = frozenset({
    "proposed",
    "applied",
    "failed",
    "unavailable",
    "recovery_proposed",
    "aborted",
})
_RECOVERY_STATUSES = frozenset({
    "not_required",
    "available",
    "review_required",
    "unavailable",
    "aborted",
})


class EditorialWorkspacePublishWorkflowError(Exception):
    """Raised only when a transition cannot ground a durable proposal (§10).

    Carries a stable, path-free ``code``; the Pipeline adapter reads ``.code``
    and never surfaces the message body.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = sanitize(message)
        super().__init__(f"{code}: {self.message}")


class _DiscoveryUnavailable(Exception):
    """Internal: the callable did not answer at all."""


class _DiscoveryDrift(Exception):
    """Internal: the callable answered, but not with the held authority."""


# --------------------------------------------------------------------------- #
# Durable store
# --------------------------------------------------------------------------- #
class InMemoryEditorialWorkspacePublishWorkflowStore(InMemoryWorkflowStore):
    """Process-local store — unit tests and stock installs without Postgres."""

    def __init__(self) -> None:
        super().__init__(authority_field="publish_preview_fingerprint")


class SessionFactoryEditorialWorkspacePublishWorkflowStore(
    SessionFactoryWorkflowStore
):
    """Durable store over ``OrchWorkflowRecordRepo`` (migration 0016)."""

    def __init__(self, session_factory: Any) -> None:
        super().__init__(session_factory, repo_factory=_workflow_repo)


def _workflow_repo(session: Any) -> Any:
    from forge_bridge.store.orch_workflow_record_repo import (
        OrchWorkflowRecordRepo,
    )

    return OrchWorkflowRecordRepo(
        session,
        kind=WORKFLOW_KIND,
        authority_field="publish_preview_fingerprint",
    )


# --------------------------------------------------------------------------- #
# AssentRecord gateway
# --------------------------------------------------------------------------- #
class AssentGateway:
    """Seam onto the AssentRecord lifecycle.

    Production binds it to ``AssentRecordRepo`` + a session factory; tests bind
    it to an in-memory implementation so the REAL ``CommitBoundary`` rails still
    run against a fake MCP.
    """

    async def propose(
        self, chain_steps: list[str], *, metadata: dict[str, Any]
    ) -> Any:
        raise NotImplementedError

    async def ratify(self, graph_intent_id: str, *, actor: str) -> Any:
        raise NotImplementedError

    async def mark_applied(
        self, graph_intent_id: str, *, result: dict[str, Any]
    ) -> None:
        raise NotImplementedError

    async def mark_failed(
        self,
        graph_intent_id: str,
        *,
        reason: str,
        result: Optional[dict[str, Any]],
    ) -> None:
        raise NotImplementedError


class SessionFactoryAssentGateway(AssentGateway):
    """Durable gateway: one session per transition, caller commits."""

    def __init__(self, session_factory: Any) -> None:
        if session_factory is None:
            raise ValueError("session_factory is required for the assent rail")
        self._session_factory = session_factory

    async def propose(
        self, chain_steps: list[str], *, metadata: dict[str, Any]
    ) -> Any:
        from forge_bridge.store.assent_record_repo import AssentRecordRepo

        async with self._session_factory() as session:
            record = await AssentRecordRepo(session).propose(
                list(chain_steps), metadata=dict(metadata)
            )
            await session.commit()
            return record

    async def ratify(self, graph_intent_id: str, *, actor: str) -> Any:
        from forge_bridge.store.assent_record_repo import (
            AssentRecordLifecycleError,
            AssentRecordNotFound,
            AssentRecordRepo,
        )

        async with self._session_factory() as session:
            try:
                record = await AssentRecordRepo(session).ratify(
                    graph_intent_id, actor=actor
                )
            except (AssentRecordNotFound, AssentRecordLifecycleError) as exc:
                raise _AssentUnavailable(str(exc)) from exc
            await session.commit()
            return record

    async def mark_applied(
        self, graph_intent_id: str, *, result: dict[str, Any]
    ) -> None:
        from forge_bridge.store.assent_record_repo import AssentRecordRepo

        async with self._session_factory() as session:
            await AssentRecordRepo(session).mark_applied(
                graph_intent_id, result=result
            )
            await session.commit()

    async def mark_failed(
        self,
        graph_intent_id: str,
        *,
        reason: str,
        result: Optional[dict[str, Any]],
    ) -> None:
        from forge_bridge.store.assent_record_repo import AssentRecordRepo

        async with self._session_factory() as session:
            await AssentRecordRepo(session).mark_failed(
                graph_intent_id, reason=reason, result=result
            )
            await session.commit()


class InMemoryAssentGateway(AssentGateway):
    """Process-local AssentRecord lifecycle for tests / no-Postgres installs.

    ponytail: enough of the state machine to keep the rail honest — propose is
    content-addressed on the held body, and only ``proposed`` ratifies.
    """

    def __init__(self) -> None:
        self._records: dict[str, Any] = {}

    async def propose(
        self, chain_steps: list[str], *, metadata: dict[str, Any]
    ) -> Any:
        from forge_bridge.core.assent import AssentRecord

        body = {"chain_steps": list(chain_steps), "metadata": dict(metadata)}
        graph_intent_id = canonical_fingerprint(body)[:12]
        existing = self._records.get(graph_intent_id)
        if existing is not None:
            return existing
        record = AssentRecord(
            graph_intent_id=graph_intent_id,
            chain_steps=list(chain_steps),
            status="proposed",
            metadata=dict(metadata),
        )
        self._records[graph_intent_id] = record
        return record

    async def ratify(self, graph_intent_id: str, *, actor: str) -> Any:
        record = self._records.get(graph_intent_id)
        if record is None:
            raise _AssentUnavailable("no assent record for that graph intent")
        if record.status != "proposed":
            raise _AssentUnavailable("assent record is not proposed")
        record.status = "ratified"
        record.decided_by = actor
        return record

    async def mark_applied(
        self, graph_intent_id: str, *, result: dict[str, Any]
    ) -> None:
        record = self._records[graph_intent_id]
        record.status = "applied"
        record.apply_result = result

    async def mark_failed(
        self,
        graph_intent_id: str,
        *,
        reason: str,
        result: Optional[dict[str, Any]],
    ) -> None:
        record = self._records[graph_intent_id]
        record.status = "failed"
        record.apply_failure_reason = reason


class _AssentUnavailable(Exception):
    """Internal: the AssentRecord could not be ratified."""


# --------------------------------------------------------------------------- #
# Graph composition (handoff §5 / §7)
# --------------------------------------------------------------------------- #
def publish_discovery_arguments(
    callable_intent: Mapping[str, Any],
) -> dict[str, Any]:
    """The discovery node arguments: the original intent plus mode=discover."""
    return {
        "params": callable_intent["params"],
        "bridge_asset_ids": callable_intent["bridge_asset_ids"],
        "idempotency_key": callable_intent["idempotency_key"],
        "project_id": callable_intent["project_id"],
        "requested_by": callable_intent["requested_by"],
        "mode": "discover",
    }


def publish_commit_operator_sequence(
    callable_intent: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """``forge_publish_shot_resource_transaction -> commit`` — composed by
    Bridge, never submitted by the Shell."""
    return [
        {
            "operator_id": PUBLISH_TOOL,
            "arguments": publish_discovery_arguments(callable_intent),
            "inputs": [],
            "output_artifact_id": "workspace-publish:held",
            "output_artifact_type": "mutation_plan",
        },
        _commit_step("workspace-publish"),
    ]


def abort_commit_operator_sequence(
    *, params: Mapping[str, Any], idempotency_key: str
) -> list[dict[str, Any]]:
    """``forge_abort_shot_resource_publish_transaction -> commit``."""
    return [
        {
            "operator_id": ABORT_TOOL,
            "arguments": {
                "params": dict(params),
                "idempotency_key": idempotency_key,
                "mode": "discover",
            },
            "inputs": [],
            "output_artifact_id": "workspace-publish-abort:held",
            "output_artifact_type": "mutation_plan",
        },
        _commit_step("workspace-publish-abort"),
    ]


def _inspect_operator_sequence(
    *, params: Mapping[str, Any], idempotency_key: str
) -> list[dict[str, Any]]:
    return [
        {
            "operator_id": INSPECT_TOOL,
            "arguments": {
                "params": dict(params),
                "idempotency_key": idempotency_key,
            },
            "inputs": [],
            "output_artifact_id": "workspace-publish:status",
            "output_artifact_type": "mcp_read_result",
        }
    ]


def _commit_step(prefix: str) -> dict[str, Any]:
    return {
        "operator_id": "commit",
        "arguments": {},
        "inputs": [
            {
                "artifact_id": f"{prefix}:held",
                "artifact_type": "mutation_plan",
                "metadata": {"role": "held"},
            }
        ],
        "output_artifact_id": f"{prefix}:commit",
        "output_artifact_type": "commit_result",
    }


# --------------------------------------------------------------------------- #
# The API
# --------------------------------------------------------------------------- #
DiscoverFn = Callable[[Sequence[Mapping[str, Any]]], Awaitable[Any]]
PreviewFn = Callable[..., Awaitable[dict[str, Any]]]
ApplyFn = Callable[..., Awaitable[dict[str, Any]]]


class EditorialWorkspacePublishWorkflowAPI:
    """Closed workspace-publish workflow over discover + assent + commit."""

    def __init__(
        self,
        *,
        store: WorkflowStore,
        discover_fn: DiscoverFn,
        preview_fn: PreviewFn,
        apply_fn: ApplyFn,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        self._store = store
        self._discover_fn = discover_fn
        self._preview_fn = preview_fn
        self._apply_fn = apply_fn
        self._clock = clock or utc_now_iso
        self._guard = ProposalTransitionGuard(store)

    # -- propose ----------------------------------------------------------- #
    async def propose(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        normalized = _validate_proposal(proposal)
        proposal_fingerprint = normalized["fingerprint"]
        proposal_id = workflow_identifier("epw_", proposal_fingerprint)
        workflow_id = workflow_identifier("epwf_", proposal_fingerprint)

        existing = await self._store.get_by_proposal_id(proposal_id)
        if existing is not None:
            # Exact duplicate: the ORIGINAL durable proposal receipt (§6).
            return _build_receipt("propose", existing, status="proposed")

        collision = await self._store.get_by_authority_fingerprint(
            normalized["publish_preview_fingerprint"]
        )
        if collision is not None:
            raise EditorialWorkspacePublishWorkflowError(
                REASON_PROPOSAL_INVALID,
                "publish authority is already bound to a different proposal",
            )

        callable_intent = normalized["callable_intent"]
        # Compose publish -> commit, then execute the DISCOVERY node only.
        # The commit node runs later, under ratified assent, as a held-manifest
        # replay (§5: propose must never call verify or apply).
        composition = publish_commit_operator_sequence(callable_intent)
        try:
            held_manifest = await self._discover(composition[:1])
        except _DiscoveryUnavailable as exc:
            raise EditorialWorkspacePublishWorkflowError(
                REASON_CALLABLE_UNAVAILABLE,
                "publish transaction callable did not answer",
            ) from exc
        except _DiscoveryDrift as exc:
            raise EditorialWorkspacePublishWorkflowError(
                REASON_MANIFEST_INVALID,
                "publish transaction discovery was not trusted",
            ) from exc

        evidence = _verify_publish_manifest(held_manifest, normalized)

        preview = await self._preview(
            held_manifest=held_manifest,
            chain_steps=[
                f"publish shot-resource transaction "
                f"{evidence['transaction_id']}",
                "commit",
            ],
            display="Phase 156 workspace publish",
        )

        now = self._clock()
        record = {
            "kind": WORKFLOW_KIND,
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "workflow_id": workflow_id,
            "proposal_id": proposal_id,
            "proposal_fingerprint": proposal_fingerprint,
            # Private: retained for verification + recovery derivation, never
            # projected into a receipt.
            "proposal": normalized,
            "publish_preview_id": normalized["publish_preview_id"],
            "publish_preview_fingerprint": normalized[
                "publish_preview_fingerprint"
            ],
            "transaction_batch_fingerprint": normalized[
                "transaction_batch_fingerprint"
            ],
            "callable_intent_fingerprint": normalized[
                "callable_intent_fingerprint"
            ],
            "transaction_id": evidence["transaction_id"],
            "transaction_canonical": evidence["canonical"],
            "selected_roles": list(normalized["selected_roles"]),
            "published_asset_ids": [],
            "forward_manifest_fingerprint": canonical_fingerprint(
                held_manifest
            ),
            "forward_held_manifest": held_manifest,
            "forward_graph_intent_id": preview["graph_intent_id"],
            "forward_assent_record_id": preview["assent_record_id"],
            "forward_assent_status": "proposed",
            "forward_commit_fingerprint": None,
            "transaction_status": "not_started",
            "recovery_status": "not_required",
            "recovery_manifest_fingerprint": None,
            "recovery_held_manifest": None,
            "recovery_graph_intent_id": None,
            "recovery_assent_record_id": None,
            "recovery_assent_status": None,
            "recovery_commit_fingerprint": None,
            "status": "proposed",
            "reason_code": None,
            "replay_observations": 0,
            "created_at": now,
            "requested_by": normalized["requested_by"],
            "actors": {"propose": normalized["requested_by"]},
            "timestamps": {"propose": now},
        }
        try:
            stored = await self._store.create(record)
        except Exception as exc:  # noqa: BLE001 - durable persistence failure
            raise EditorialWorkspacePublishWorkflowError(
                REASON_MANIFEST_INVALID,
                "workflow persistence failed after discovery",
            ) from exc
        return _build_receipt("propose", stored, status="proposed")

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

        async with self._guard.lock(proposal_id):
            workflow = await self._reload_or_raise(proposal_id)
            # Durable status guard: fails closed across processes even if the
            # per-process lock was lost.
            if workflow["status"] != "proposed":
                return _refuse("ratify_apply", workflow, REASON_ASSENT_INVALID)
            if workflow["forward_assent_status"] != "proposed":
                return _refuse("ratify_apply", workflow, REASON_ASSENT_INVALID)

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
                evidence = _applied_evidence(outcome)
                if evidence is None:
                    # Host said applied but returned no committed transaction
                    # evidence; an "applied" receipt would be unfounded.
                    patch.update(
                        _failure_patch(workflow, REASON_COMMIT_FAILED, None)
                    )
                    stored = await self._store.update(proposal_id, patch)
                    return _refuse(
                        "ratify_apply", stored, REASON_COMMIT_FAILED
                    )
                patch["status"] = "applied"
                patch["reason_code"] = None
                patch["transaction_status"] = "committed"
                patch["published_asset_ids"] = evidence["created_asset_ids"]
                patch["forward_commit_fingerprint"] = canonical_fingerprint(
                    outcome["commit_result"]
                )
                patch["recovery_status"] = "not_required"
                stored = await self._store.update(proposal_id, patch)
                return _build_receipt("ratify_apply", stored, status="applied")

            reason = outcome.get("reason_code") or REASON_COMMIT_FAILED
            patch.update(
                _failure_patch(
                    workflow, reason, outcome.get("commit_reason_code")
                )
            )
            stored = await self._store.update(proposal_id, patch)
            return _refuse("ratify_apply", stored, reason)

    # -- status ------------------------------------------------------------ #
    async def status(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
    ) -> dict[str, Any]:
        """Read durable Bridge workflow state. Never rediscovers or dispatches."""
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "status", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed
        return _build_receipt(
            "status", workflow, status=_status_action_status(workflow)
        )

    # -- replay ------------------------------------------------------------ #
    async def replay(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
        requested_by: str,
    ) -> dict[str, Any]:
        """Observe an already-committed idempotent forward transaction.

        Creates no AssentRecord, manifest, or commit and performs no MCP apply.
        """
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

        patch = {
            "replay_observations": int(workflow.get("replay_observations", 0))
            + 1,
            "timestamps": {**workflow["timestamps"], "replay": self._clock()},
            "actors": {**workflow["actors"], "replay": requested_by},
        }
        stored = await self._store.update(proposal_id, patch)
        return _build_receipt("replay", stored, status="applied")

    # -- propose_recovery -------------------------------------------------- #
    async def propose_recovery(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
        requested_by: str,
    ) -> dict[str, Any]:
        """Inspect, then discover an abort. Aborts nothing (§7)."""
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "propose_recovery", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed

        async with self._guard.lock(proposal_id):
            workflow = await self._reload_or_raise(proposal_id)
            if workflow["status"] == "recovery_proposed":
                # Idempotent: the held abort authority already exists.
                return _build_receipt(
                    "propose_recovery", workflow, status="recovery_proposed"
                )
            if workflow["status"] != "failed":
                # Recovery is allowed only over an uncommitted, failed forward
                # transaction (§7). proposed / applied / aborted never recover.
                return _refuse(
                    "propose_recovery", workflow, REASON_RECOVERY_UNAVAILABLE
                )

            params = _recovery_params(workflow)
            idempotency_key = _recovery_idempotency_key(workflow)
            try:
                status_payload = await self._discover(
                    _inspect_operator_sequence(
                        params=params,
                        idempotency_key=f"{idempotency_key}:status",
                    ),
                    expect_manifest=False,
                )
            except (_DiscoveryUnavailable, _DiscoveryDrift):
                return await self._recovery_refusal(
                    workflow,
                    REASON_STATUS_UNAVAILABLE,
                    recovery_status="unavailable",
                    requested_by=requested_by,
                )

            trusted = _trusted_recovery_status(status_payload, workflow)
            if not trusted:
                return await self._recovery_refusal(
                    workflow,
                    REASON_RECOVERY_UNAVAILABLE,
                    recovery_status="review_required",
                    requested_by=requested_by,
                )

            composition = abort_commit_operator_sequence(
                params=params, idempotency_key=f"{idempotency_key}:abort"
            )
            try:
                held_abort = await self._discover(composition[:1])
            except _DiscoveryUnavailable:
                return await self._recovery_refusal(
                    workflow,
                    REASON_RECOVERY_UNAVAILABLE,
                    recovery_status="review_required",
                    requested_by=requested_by,
                )
            except _DiscoveryDrift:
                return await self._recovery_refusal(
                    workflow,
                    REASON_RECOVERY_DRIFT,
                    recovery_status="review_required",
                    requested_by=requested_by,
                )

            try:
                _verify_abort_manifest(held_abort, workflow)
            except _DiscoveryDrift:
                return await self._recovery_refusal(
                    workflow,
                    REASON_RECOVERY_DRIFT,
                    recovery_status="review_required",
                    requested_by=requested_by,
                )

            preview = await self._preview(
                held_manifest=held_abort,
                chain_steps=[
                    f"abort shot-resource publish transaction "
                    f"{workflow['transaction_id']}",
                    "commit",
                ],
                display="Phase 156 workspace publish recovery",
            )
            now = self._clock()
            # A SECOND held manifest + a SECOND proposed AssentRecord. The
            # forward proposal / callable / manifest / commit fingerprints are
            # never touched here (§9).
            patch = {
                "status": "recovery_proposed",
                "reason_code": None,
                "recovery_status": "available",
                "recovery_manifest_fingerprint": canonical_fingerprint(
                    held_abort
                ),
                "recovery_held_manifest": held_abort,
                "recovery_graph_intent_id": preview["graph_intent_id"],
                "recovery_assent_record_id": preview["assent_record_id"],
                "recovery_assent_status": "proposed",
                "recovery_commit_fingerprint": None,
                "timestamps": {
                    **workflow["timestamps"],
                    "propose_recovery": now,
                },
                "actors": {
                    **workflow["actors"],
                    "propose_recovery": requested_by,
                },
            }
            stored = await self._store.update(proposal_id, patch)
            return _build_receipt(
                "propose_recovery", stored, status="recovery_proposed"
            )

    # -- ratify_recovery --------------------------------------------------- #
    async def ratify_recovery(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
        requested_by: str,
    ) -> dict[str, Any]:
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "ratify_recovery", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed

        async with self._guard.lock(proposal_id):
            workflow = await self._reload_or_raise(proposal_id)
            if workflow["status"] == "aborted":
                # Idempotent: a trusted abort already committed.
                return _build_receipt(
                    "ratify_recovery", workflow, status="aborted"
                )
            if workflow["status"] != "recovery_proposed":
                return _refuse(
                    "ratify_recovery", workflow, REASON_RECOVERY_UNAVAILABLE
                )
            if workflow.get("recovery_assent_status") != "proposed":
                return _refuse(
                    "ratify_recovery", workflow, REASON_ASSENT_INVALID
                )

            outcome = await self._apply_fn(
                graph_intent_id=workflow["recovery_graph_intent_id"],
                requested_by=requested_by,
            )
            now = self._clock()
            patch: dict[str, Any] = {
                "recovery_assent_status": outcome.get("assent_status"),
                "timestamps": {
                    **workflow["timestamps"],
                    "ratify_recovery": now,
                },
                "actors": {
                    **workflow["actors"],
                    "ratify_recovery": requested_by,
                },
            }
            if outcome["outcome"] == "applied":
                patch["status"] = "aborted"
                patch["reason_code"] = None
                patch["transaction_status"] = "aborted"
                patch["recovery_status"] = "aborted"
                patch["recovery_commit_fingerprint"] = canonical_fingerprint(
                    outcome["commit_result"]
                )
                stored = await self._store.update(proposal_id, patch)
                return _build_receipt(
                    "ratify_recovery", stored, status="aborted"
                )

            reason = (
                REASON_RECOVERY_DRIFT
                if outcome.get("commit_reason_code") == "PLAN_STATE_DRIFT"
                else REASON_RECOVERY_FAILED
            )
            patch["status"] = "failed"
            patch["reason_code"] = reason
            patch["recovery_status"] = "review_required"
            stored = await self._store.update(proposal_id, patch)
            return _refuse("ratify_recovery", stored, reason)

    # -- internals --------------------------------------------------------- #
    async def _recovery_refusal(
        self,
        workflow: Mapping[str, Any],
        reason_code: str,
        *,
        recovery_status: str,
        requested_by: str,
    ) -> dict[str, Any]:
        """Persist the honest recovery disposition, then refuse.

        The forward failure stands; only the recovery disposition moves.
        """
        patch = {
            "recovery_status": recovery_status,
            "reason_code": reason_code,
            "actors": {
                **workflow["actors"],
                "propose_recovery": requested_by,
            },
            "timestamps": {
                **workflow["timestamps"],
                "propose_recovery": self._clock(),
            },
        }
        stored = await self._store.update(workflow["proposal_id"], patch)
        return _refuse("propose_recovery", stored, reason_code)

    async def _discover(
        self,
        operator_sequence: Sequence[Mapping[str, Any]],
        *,
        expect_manifest: bool = True,
    ) -> dict[str, Any]:
        result = await self._discover_fn(operator_sequence)
        status = getattr(result, "status", None)
        output = getattr(result, "output", None)
        if status is None:
            # A raw payload seam (tests may inject one).
            output = result
            status = "ok" if isinstance(result, dict) else "error"
        if status != "ok" or not isinstance(output, dict):
            raise _DiscoveryDrift("discovery node did not return trusted output")
        if expect_manifest and output.get("type") != "mutation_plan":
            raise _DiscoveryDrift("discovery did not resolve a mutation plan")
        return output

    async def _preview(
        self,
        *,
        held_manifest: dict[str, Any],
        chain_steps: list[str],
        display: str,
    ) -> dict[str, Any]:
        try:
            return await self._preview_fn(
                held_manifest=held_manifest,
                chain_steps=chain_steps,
                display=display,
            )
        except EditorialWorkspacePublishWorkflowError:
            raise
        except Exception as exc:  # noqa: BLE001 - persistence failure
            raise EditorialWorkspacePublishWorkflowError(
                REASON_MANIFEST_INVALID,
                "preview did not persist a durable mutation manifest",
            ) from exc

    async def _load_or_raise(self, proposal_id: str) -> dict[str, Any]:
        workflow = await self._store.get_by_proposal_id(proposal_id)
        if workflow is None:
            raise EditorialWorkspacePublishWorkflowError(
                REASON_PROPOSAL_NOT_FOUND,
                "no workflow for the supplied proposal id",
            )
        return workflow

    async def _reload_or_raise(self, proposal_id: str) -> dict[str, Any]:
        workflow = await self._guard.reload(proposal_id)
        if workflow is None:
            raise EditorialWorkspacePublishWorkflowError(
                REASON_PROPOSAL_NOT_FOUND, "workflow disappeared"
            )
        return workflow


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #
def make_editorial_workspace_publish_workflow_api(
    *,
    session_factory: Any,
    mcp: Any,
    store: WorkflowStore | None = None,
    assent_gateway: AssentGateway | None = None,
    discover_fn: DiscoverFn | None = None,
    preview_fn: PreviewFn | None = None,
    apply_fn: ApplyFn | None = None,
    clock: Callable[[], str] | None = None,
) -> EditorialWorkspacePublishWorkflowAPI:
    """Construct the workflow API.

    Pipeline calls this with ``session_factory`` + ``mcp`` only; the remaining
    keywords are test seams.
    """
    if store is None:
        if session_factory is None:
            raise ValueError(
                "session_factory is required when store is not supplied"
            )
        store = SessionFactoryEditorialWorkspacePublishWorkflowStore(
            session_factory
        )
    if assent_gateway is None and (preview_fn is None or apply_fn is None):
        assent_gateway = SessionFactoryAssentGateway(session_factory)
    if discover_fn is None:
        discover_fn = _default_discover_fn(mcp)
    if preview_fn is None:
        preview_fn = _default_preview_fn(assent_gateway)
    if apply_fn is None:
        apply_fn = _default_apply_fn(assent_gateway, mcp)
    return EditorialWorkspacePublishWorkflowAPI(
        store=store,
        discover_fn=discover_fn,
        preview_fn=preview_fn,
        apply_fn=apply_fn,
        clock=clock,
    )


def _default_discover_fn(mcp: Any) -> DiscoverFn:
    """Run a read/discovery node through the admitted graph dispatch surface."""

    async def discover(operator_sequence: Sequence[Mapping[str, Any]]) -> Any:
        from forge_bridge.composition.boundary import MCPToolBoundary
        from forge_bridge.composition.compiler import compile_operator_sequence
        from forge_bridge.composition.dispatch import UnifiedDispatch
        from forge_bridge.composition.executor import GraphExecutor

        spec = compile_operator_sequence(list(operator_sequence))
        dispatch = UnifiedDispatch(mcp_boundary=MCPToolBoundary(mcp=mcp))
        try:
            results = await GraphExecutor(dispatch.dispatch).run(spec)
        except Exception as exc:  # noqa: BLE001 - transport boundary evidence
            raise _DiscoveryUnavailable("discovery dispatch failed") from exc
        return results[spec.nodes[0].node_id]

    return discover


def _default_preview_fn(assent_gateway: AssentGateway) -> PreviewFn:
    async def preview_fn(
        *,
        held_manifest: dict[str, Any],
        chain_steps: list[str],
        display: str,
    ) -> dict[str, Any]:
        from forge_bridge.orchestration.apply_editorial_delta import (
            GRAPH_REPLAY_METADATA_KEY,
            build_graph_replay_metadata,
        )

        graph_replay = build_graph_replay_metadata(
            held_manifest=held_manifest, display=display
        )
        record = await assent_gateway.propose(
            list(chain_steps),
            metadata={GRAPH_REPLAY_METADATA_KEY: graph_replay},
        )
        return {
            "graph_intent_id": record.graph_intent_id,
            "assent_record_id": str(record.id),
        }

    return preview_fn


def _default_apply_fn(assent_gateway: AssentGateway, mcp: Any) -> ApplyFn:
    async def apply_fn(
        *, graph_intent_id: str, requested_by: str
    ) -> dict[str, Any]:
        return await _ratify_and_commit(
            graph_intent_id=graph_intent_id,
            requested_by=requested_by,
            assent_gateway=assent_gateway,
            mcp=mcp,
        )

    return apply_fn


async def _ratify_and_commit(
    *,
    graph_intent_id: str,
    requested_by: str,
    assent_gateway: AssentGateway,
    mcp: Any,
) -> dict[str, Any]:
    """Ratify the proposed AssentRecord, then replay its held manifest through
    the existing verify-before-apply ``CommitBoundary``."""
    from forge_bridge.composition.commit_boundary import CommitBoundary
    from forge_bridge.composition.dispatch import UnifiedDispatch
    from forge_bridge.composition.executor import GraphExecutor
    from forge_bridge.orchestration.apply_editorial_delta import (
        graph_replay_commit_spec,
    )

    try:
        record = await assent_gateway.ratify(graph_intent_id, actor=requested_by)
    except _AssentUnavailable:
        return {
            "outcome": "refused",
            "assent_status": None,
            "reason_code": REASON_ASSENT_INVALID,
            "commit_reason_code": None,
            "commit_result": None,
        }

    held_manifest = held_manifest_from_record(record)
    if held_manifest is None:
        await assent_gateway.mark_failed(
            graph_intent_id, reason="assent_invalid", result=None
        )
        return {
            "outcome": "failed",
            "assent_status": "failed",
            "reason_code": REASON_MANIFEST_INVALID,
            "commit_reason_code": None,
            "commit_result": None,
        }

    dispatch = UnifiedDispatch(
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=record,
    )
    results = await GraphExecutor(dispatch.dispatch).run(
        graph_replay_commit_spec(held_manifest)
    )
    commit_result = results["commit"]
    if commit_result.status == "error":
        reason_code = getattr(commit_result, "reason_code", None)
        await assent_gateway.mark_failed(
            graph_intent_id,
            reason=_assent_failure_reason(reason_code),
            # Only the structured code — never the host message, which can
            # carry absolute paths.
            result={"error": {"type": reason_code}},
        )
        return {
            "outcome": "failed",
            "assent_status": "failed",
            "reason_code": _commit_refusal_reason(reason_code),
            "commit_reason_code": reason_code,
            "commit_result": None,
        }

    applied = commit_result.output
    await assent_gateway.mark_applied(graph_intent_id, result=applied)
    return {
        "outcome": "applied",
        "assent_status": "applied",
        "reason_code": None,
        "commit_reason_code": None,
        "commit_result": applied,
    }


def _assent_failure_reason(reason_code: Any) -> str:
    if reason_code == "PLAN_STATE_DRIFT":
        return "drift_invalid"
    if reason_code == "ASSENT_INVALID":
        return "assent_invalid"
    return "chain_aborted"


def _commit_refusal_reason(reason_code: Any) -> str:
    if reason_code == "PLAN_STATE_DRIFT":
        return REASON_MANIFEST_DRIFT
    if reason_code == "ASSENT_INVALID":
        return REASON_ASSENT_INVALID
    return REASON_COMMIT_FAILED


# --------------------------------------------------------------------------- #
# Proposal validation (handoff §4)
# --------------------------------------------------------------------------- #
def _invalid(message: str) -> EditorialWorkspacePublishWorkflowError:
    return EditorialWorkspacePublishWorkflowError(
        REASON_PROPOSAL_INVALID, message
    )


def _validate_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(proposal, Mapping):
        raise _invalid("proposal must be a mapping")
    extra = set(proposal.keys()) - _PROPOSAL_FIELDS
    if extra:
        raise _invalid(f"proposal has unknown fields: {sorted(extra)}")
    missing = _PROPOSAL_FIELDS - set(proposal.keys())
    if missing:
        raise _invalid(f"proposal is missing fields: {sorted(missing)}")
    if proposal["kind"] != PROPOSAL_KIND:
        raise _invalid("proposal kind is not recognized")
    if proposal["schema_version"] != PROPOSAL_SCHEMA_VERSION:
        raise _invalid("proposal schema_version is not supported")
    for field in _PROPOSAL_TEXT_FIELDS:
        value = proposal[field]
        if not isinstance(value, str) or not value.strip():
            raise _invalid(f"proposal field {field} must be a non-empty string")
    for field in _PROPOSAL_SHA256_FIELDS:
        if not is_sha256(proposal[field]):
            raise _invalid(f"proposal field {field} is not a sha256 hash")

    selected_roles = proposal["selected_roles"]
    if (
        not isinstance(selected_roles, list)
        or not selected_roles
        or any(
            not isinstance(role, str) or not role.strip()
            for role in selected_roles
        )
        or sorted(set(selected_roles)) != list(selected_roles)
    ):
        raise _invalid("selected_roles must be non-empty, unique, and sorted")

    normalized = {key: proposal[key] for key in _PROPOSAL_FIELDS}
    body = {
        key: value
        for key, value in normalized.items()
        if key not in {"kind", "schema_version", "fingerprint"}
    }
    if canonical_fingerprint(body) != normalized["fingerprint"]:
        raise _invalid("proposal fingerprint mismatch")

    _validate_callable_intent(normalized)
    return normalized


def _validate_callable_intent(proposal: Mapping[str, Any]) -> None:
    intent = proposal["callable_intent"]
    if not isinstance(intent, Mapping):
        raise _invalid("callable_intent must be a mapping")
    extra = set(intent.keys()) - _CALLABLE_INTENT_FIELDS
    if extra:
        raise _invalid(f"callable_intent has unknown fields: {sorted(extra)}")
    missing = _CALLABLE_INTENT_FIELDS - set(intent.keys())
    if missing:
        raise _invalid(f"callable_intent is missing fields: {sorted(missing)}")
    if intent["tool"] != CALLABLE_TOOL:
        raise _invalid("callable_intent tool is not the publish transaction")
    if intent["operation_type"] != CALLABLE_OPERATION_TYPE:
        raise _invalid("callable_intent operation_type is not recognized")
    if canonical_fingerprint(dict(intent)) != proposal[
        "callable_intent_fingerprint"
    ]:
        raise _invalid("callable_intent differs from its fingerprint")
    if intent["project_id"] != proposal["project_id"]:
        raise _invalid("callable_intent project differs from the proposal")

    bridge_asset_ids = intent["bridge_asset_ids"]
    if not isinstance(bridge_asset_ids, list):
        raise _invalid("callable_intent bridge_asset_ids must be a list")
    if proposal["source_version_id"] not in bridge_asset_ids:
        raise _invalid("source Version is not carried by the callable intent")

    idempotency_key = intent["idempotency_key"]
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise _invalid("callable_intent idempotency_key must be non-empty")

    params = intent["params"]
    if not isinstance(params, Mapping):
        raise _invalid("callable_intent params must be a mapping")
    selected_roles = list(proposal["selected_roles"])
    roles = params.get("roles")
    if not isinstance(roles, list) or sorted(roles) != selected_roles:
        raise _invalid("callable params roles differ from the selected roles")

    outputs = params.get("outputs")
    if not isinstance(outputs, list) or len(outputs) != len(selected_roles):
        raise _invalid("callable params outputs do not cover the selected roles")
    output_roles = []
    for output in outputs:
        if not isinstance(output, Mapping):
            raise _invalid("callable output must be a mapping")
        output_roles.append(output.get("role"))
        lineage = output.get("lineage_asset_ids")
        if (
            not isinstance(lineage, list)
            or proposal["source_version_id"] not in lineage
        ):
            raise _invalid("callable output does not retain the source Version")
    if sorted(str(role) for role in output_roles) != selected_roles:
        raise _invalid("callable output roles differ from the selected roles")


# --------------------------------------------------------------------------- #
# Manifest verification (handoff §5 / §7)
# --------------------------------------------------------------------------- #
def _verify_publish_manifest(
    payload: Mapping[str, Any], proposal: Mapping[str, Any]
) -> dict[str, Any]:
    """Prove the discovered manifest IS the proposal's transaction.

    Returns the grounded, path-free evidence the durable record needs.
    """
    from forge_bridge.composition.admission import (
        AdmissionRejected,
        admit_mutation_counterpart,
    )
    from forge_bridge.graph.mutation import (
        MutationManifest,
        MutationManifestError,
    )

    def fail(detail: str) -> EditorialWorkspacePublishWorkflowError:
        return EditorialWorkspacePublishWorkflowError(
            REASON_MANIFEST_INVALID, detail
        )

    try:
        manifest = MutationManifest.from_dict(dict(payload))
    except (MutationManifestError, KeyError, TypeError) as exc:
        raise fail("discovered manifest is structurally invalid") from exc

    if payload.get("ok") is not True:
        raise fail("discovered manifest is not ok")
    if payload.get("status") != "ready":
        raise fail("discovered manifest is not ready")
    if payload.get("trust_status") != "trusted":
        raise fail("discovered manifest is not trusted")
    if payload.get("mutation_safe") is not True:
        raise fail("discovered manifest is not mutation safe")
    if payload.get("state_owner") != PUBLISH_STATE_OWNER:
        raise fail("discovered manifest has the wrong state owner")
    if payload.get("originating_capability") != PUBLISH_TOOL:
        raise fail("discovered manifest has the wrong originating capability")
    if manifest.apply_counterpart.get("tool") != PUBLISH_TOOL:
        raise fail("discovered manifest has the wrong apply counterpart")
    try:
        counterpart = admit_mutation_counterpart(PUBLISH_TOOL)
    except AdmissionRejected as exc:
        raise fail("apply counterpart is not admitted") from exc
    if (
        counterpart.state_owner != PUBLISH_STATE_OWNER
        or not counterpart.verify_before_apply
        or not counterpart.assent_required
    ):
        raise fail("apply counterpart lacks the required commit authority")

    plan = payload.get("transaction_plan")
    if not isinstance(plan, Mapping):
        raise fail("discovered manifest carries no transaction plan")
    transaction_id = plan.get("transaction_id")
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        raise fail("transaction plan carries no transaction id")
    canonical = plan.get("canonical")
    if not isinstance(canonical, str) or not canonical.strip():
        raise fail("transaction plan carries no canonical root")

    selected_roles = list(proposal["selected_roles"])
    if sorted(plan.get("roles") or []) != selected_roles:
        raise fail("transaction plan roles differ from the selected roles")
    if "selected_roles" in plan and sorted(
        plan.get("selected_roles") or []
    ) != selected_roles:
        raise fail("transaction plan selection differs from the selected roles")
    if plan.get("stream") != proposal["stream"]:
        raise fail("transaction plan stream differs from the proposal")
    if plan.get("task") != proposal["task"]:
        raise fail("transaction plan task differs from the proposal")

    records = payload.get("resolved_plan")
    if not isinstance(records, list) or len(records) != 1:
        raise fail("transaction manifest must carry exactly one change record")
    identity = records[0].get("identity") if isinstance(
        records[0], Mapping
    ) else None
    if not isinstance(identity, Mapping):
        raise fail("change record carries no identity")
    if identity.get("operation_type") != CALLABLE_OPERATION_TYPE:
        raise fail("change record operation type is not recognized")
    if identity.get("transaction_id") != transaction_id:
        raise fail("change record transaction identity differs")
    if sorted(identity.get("roles") or []) != selected_roles:
        raise fail("change record roles differ from the selected roles")

    intent = proposal["callable_intent"]
    manifest_intent = payload.get("intent_parameters")
    if not isinstance(manifest_intent, Mapping):
        raise fail("discovered manifest carries no intent parameters")
    if manifest_intent.get("params") != dict(intent["params"]):
        raise fail("manifest intent parameters differ from the callable intent")
    if manifest_intent.get("idempotency_key") != intent["idempotency_key"]:
        raise fail("manifest idempotency key differs from the callable intent")
    if list(manifest_intent.get("bridge_asset_ids") or []) != list(
        intent["bridge_asset_ids"]
    ):
        raise fail("manifest source assets differ from the callable intent")
    if manifest_intent.get("project_id") != intent["project_id"]:
        raise fail("manifest project differs from the callable intent")
    if manifest_intent.get("requested_by") != intent["requested_by"]:
        raise fail("manifest actor differs from the callable intent")

    actions = plan.get("actions")
    if not isinstance(actions, list) or len(actions) != len(selected_roles):
        raise fail("transaction plan actions do not cover the selected roles")
    if sorted(
        str(action.get("role"))
        for action in actions
        if isinstance(action, Mapping)
    ) != selected_roles:
        raise fail("transaction plan action roles differ from the selection")
    for action in actions:
        lineage = action.get("lineage_asset_ids") if isinstance(
            action, Mapping
        ) else None
        if (
            not isinstance(lineage, list)
            or proposal["source_version_id"] not in lineage
        ):
            raise fail("transaction action does not retain the source Version")

    return {"transaction_id": transaction_id, "canonical": canonical}


def _verify_abort_manifest(
    payload: Mapping[str, Any], workflow: Mapping[str, Any]
) -> None:
    """Prove the discovered abort manifest IS this transaction's abort."""
    from forge_bridge.composition.admission import (
        AdmissionRejected,
        admit_mutation_counterpart,
    )
    from forge_bridge.graph.mutation import (
        MutationManifest,
        MutationManifestError,
    )

    try:
        manifest = MutationManifest.from_dict(dict(payload))
    except (MutationManifestError, KeyError, TypeError) as exc:
        raise _DiscoveryDrift("abort manifest is structurally invalid") from exc
    if payload.get("ok") is not True:
        raise _DiscoveryDrift("abort manifest is not ok")
    if payload.get("status") != "ready":
        raise _DiscoveryDrift("abort manifest is not ready")
    if payload.get("trust_status") != "trusted":
        raise _DiscoveryDrift("abort manifest is not trusted")
    if payload.get("mutation_safe") is not True:
        raise _DiscoveryDrift("abort manifest is not mutation safe")
    if payload.get("state_owner") != ABORT_STATE_OWNER:
        raise _DiscoveryDrift("abort manifest has the wrong state owner")
    if payload.get("originating_capability") != ABORT_TOOL:
        raise _DiscoveryDrift("abort manifest has the wrong capability")
    if manifest.apply_counterpart.get("tool") != ABORT_TOOL:
        raise _DiscoveryDrift("abort manifest has the wrong apply counterpart")
    try:
        counterpart = admit_mutation_counterpart(ABORT_TOOL)
    except AdmissionRejected as exc:
        raise _DiscoveryDrift("abort counterpart is not admitted") from exc
    if not counterpart.verify_before_apply or not counterpart.assent_required:
        raise _DiscoveryDrift("abort counterpart lacks commit authority")

    plan = payload.get("abort_plan")
    if not isinstance(plan, Mapping):
        raise _DiscoveryDrift("abort manifest carries no abort plan")
    if plan.get("transaction_id") != workflow["transaction_id"]:
        raise _DiscoveryDrift("abort plan targets a different transaction")
    if plan.get("ready_for_abort") is not True:
        raise _DiscoveryDrift("abort plan is not ready for abort")
    if plan.get("registration_started") is True:
        # Registration may have Bridge side effects — ownership is uncertain.
        raise _DiscoveryDrift("abort plan reports registration started")

    records = payload.get("resolved_plan")
    if not isinstance(records, list) or len(records) != 1:
        raise _DiscoveryDrift("abort manifest must carry one change record")
    identity = records[0].get("identity") if isinstance(
        records[0], Mapping
    ) else None
    if not isinstance(identity, Mapping):
        raise _DiscoveryDrift("abort change record carries no identity")
    if identity.get("operation_type") != ABORT_OPERATION_TYPE:
        raise _DiscoveryDrift("abort operation type is not recognized")
    if identity.get("transaction_id") != workflow["transaction_id"]:
        raise _DiscoveryDrift("abort change record transaction identity differs")


def _trusted_recovery_status(
    payload: Mapping[str, Any], workflow: Mapping[str, Any]
) -> bool:
    """Is this a trusted, recoverable, pre-registration failed transaction?"""
    if not isinstance(payload, Mapping):
        return False
    if payload.get("ok") is not True:
        return False
    if payload.get("read_only") is not True:
        return False
    if payload.get("transaction_id") != workflow["transaction_id"]:
        return False
    if payload.get("registration_started") is True:
        return False
    if int(payload.get("registered_count") or 0) > 0:
        return False
    return payload.get("abort_allowed") is True


def _recovery_params(workflow: Mapping[str, Any]) -> dict[str, Any]:
    """Private recovery parameters derived from the RETAINED forward manifest.

    The Shell supplies none of this (§7); ``canonical`` is an absolute path and
    never leaves Bridge.
    """
    return {
        "canonical": workflow["transaction_canonical"],
        "transaction_id": workflow["transaction_id"],
    }


def _recovery_idempotency_key(workflow: Mapping[str, Any]) -> str:
    return f"publish-workflow-recovery:{workflow['proposal_id']}"


# --------------------------------------------------------------------------- #
# Receipts (handoff §8)
# --------------------------------------------------------------------------- #
def _applied_evidence(
    outcome: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """Sorted unique created asset ids from a committed transaction apply."""
    commit_result = outcome.get("commit_result")
    if not isinstance(commit_result, Mapping):
        return None
    apply_result = commit_result.get("apply_result")
    if not isinstance(apply_result, Mapping):
        return None
    transaction_apply = apply_result.get("transaction_apply")
    if (
        not isinstance(transaction_apply, Mapping)
        or transaction_apply.get("status") != "committed"
    ):
        return None
    created = apply_result.get("created_asset_ids")
    if not isinstance(created, list) or not created:
        return None
    if any(not isinstance(item, str) or not item.strip() for item in created):
        return None
    return {"created_asset_ids": sorted(set(created))}


def _failure_patch(
    workflow: Mapping[str, Any],
    reason_code: str,
    commit_reason_code: Any,
) -> dict[str, Any]:
    """The honest transaction + recovery disposition after a failed apply.

    ponytail ceiling: ``ASSENT_INVALID`` is the only CommitBoundary code that
    proves nothing was dispatched. Every other failure is reported as a failed
    transaction needing ``review_required`` recovery — ``propose_recovery``
    then asks the Pipeline status tool, which is the authority on whether a
    journal exists. Bridge never guesses a journal state it did not read.
    """
    dispatched = commit_reason_code not in {"ASSENT_INVALID", None}
    return {
        "status": "failed",
        "reason_code": reason_code,
        "transaction_status": "failed" if dispatched else "not_started",
        "recovery_status": "review_required" if dispatched else "not_required",
    }


def _status_action_status(workflow: Mapping[str, Any]) -> str:
    durable = str(workflow["status"])
    if durable == "recovery_proposed":
        # The Pipeline receipt contract binds status "recovery_proposed" to
        # action "propose_recovery". A status poll therefore reports the real
        # forward outcome — the publish DID fail — while the recovery_* fields
        # carry the held abort authority.
        return "failed"
    return durable


def _trust_status(status: str) -> str:
    if status in _TRUSTED_STATUSES:
        return "trusted"
    if status == "unavailable":
        return "review_required"
    return "untrusted"


def _build_receipt(
    action: str,
    workflow: Mapping[str, Any],
    *,
    status: str,
    reason_code: Optional[str] = None,
) -> dict[str, Any]:
    if action not in _ACTIONS:
        raise ValueError(f"unsupported workflow action: {action!r}")
    if status not in _STATUSES:
        raise ValueError(f"unsupported workflow status: {status!r}")

    proposed_view = action == "propose"
    applied = status == "applied"
    replayed = action == "replay" and applied
    dispatch_authorized = status in {"applied", "aborted"}

    receipt: dict[str, Any] = {
        "kind": RECEIPT_KIND,
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "action": action,
        "status": status,
        "trust_status": _trust_status(status),
        "workflow_id": workflow["workflow_id"],
        "proposal_id": workflow["proposal_id"],
        "proposal_fingerprint": workflow["proposal_fingerprint"],
        "publish_preview_id": workflow["publish_preview_id"],
        "publish_preview_fingerprint": workflow["publish_preview_fingerprint"],
        "transaction_batch_fingerprint": workflow[
            "transaction_batch_fingerprint"
        ],
        "callable_intent_fingerprint": workflow["callable_intent_fingerprint"],
        "transaction_id": workflow["transaction_id"],
        "selected_roles": sorted(set(workflow["selected_roles"])),
        "manifest_fingerprint": workflow.get("forward_manifest_fingerprint"),
        "assent_record_id": workflow.get("forward_assent_record_id"),
        "dispatch_authorized": dispatch_authorized,
        "applied": applied,
        "replayed": replayed,
        "reason_code": reason_code or (
            workflow.get("reason_code") if status in {"failed", "unavailable"}
            else None
        ),
    }
    if proposed_view:
        # An exact duplicate propose returns the IMMUTABLE original receipt,
        # even after the durable workflow advances.
        receipt.update({
            "published_asset_ids": [],
            "assent_status": "proposed",
            "commit_fingerprint": None,
            "transaction_status": "not_started",
            "recovery_status": "not_required",
            "recovery_manifest_fingerprint": None,
            "recovery_assent_record_id": None,
            "recovery_assent_status": None,
            "recovery_commit_fingerprint": None,
            "reason_code": None,
        })
    else:
        receipt.update({
            "published_asset_ids": sorted(
                set(workflow.get("published_asset_ids") or [])
            ),
            "assent_status": workflow.get("forward_assent_status"),
            "commit_fingerprint": workflow.get("forward_commit_fingerprint"),
            "transaction_status": (
                workflow.get("transaction_status") or "not_started"
            ),
            "recovery_status": workflow.get("recovery_status")
            or "not_required",
            "recovery_manifest_fingerprint": workflow.get(
                "recovery_manifest_fingerprint"
            ),
            "recovery_assent_record_id": workflow.get(
                "recovery_assent_record_id"
            ),
            "recovery_assent_status": workflow.get("recovery_assent_status"),
            "recovery_commit_fingerprint": workflow.get(
                "recovery_commit_fingerprint"
            ),
        })

    ordered = finalize_receipt(
        receipt,
        _RECEIPT_KEYS,
        fingerprint_excludes=_RECEIPT_FINGERPRINT_EXCLUDES,
    )
    _assert_receipt_invariants(ordered)
    return ordered


def _assert_receipt_invariants(receipt: Mapping[str, Any]) -> None:
    """Fail closed on any §8 invariant a caller could otherwise leak."""
    status = receipt["status"]
    if receipt["recovery_status"] not in _RECOVERY_STATUSES:
        raise ValueError("receipt recovery_status is unsupported")
    for field in ("selected_roles", "published_asset_ids"):
        values = receipt[field]
        if sorted(set(values)) != list(values):
            raise ValueError(f"receipt {field} must be unique and sorted")
    if not receipt["selected_roles"]:
        raise ValueError("receipt selected_roles must be non-empty")
    # NB (contract divergence, surfaced not smoothed): handoff §8 binds the
    # "proposed" status only to "no dispatch, no applied resources,
    # transaction not_started" — it does NOT bind it to an action. Pipeline's
    # shipped receipt dataclass additionally requires action == "propose", so
    # a `status` poll on a still-proposed workflow is rejected there. Bridge
    # answers truthfully ("proposed"); there is no other honest status in the
    # closed vocabulary. Tracked in the #242 PR body.
    if status == "proposed" and (
        receipt["dispatch_authorized"]
        or receipt["applied"]
        or receipt["replayed"]
        or receipt["transaction_status"] != "not_started"
        or receipt["published_asset_ids"]
    ):
        raise ValueError("proposed receipt contains contradictory state")
    if status == "applied" and (
        not receipt["applied"]
        or receipt["transaction_status"] != "committed"
        or not receipt["published_asset_ids"]
        or receipt["commit_fingerprint"] is None
    ):
        raise ValueError("applied receipt lacks committed transaction evidence")
    if status == "recovery_proposed" and (
        receipt["action"] != "propose_recovery"
        or receipt["recovery_status"] != "available"
        or receipt["recovery_manifest_fingerprint"] is None
        or receipt["recovery_assent_record_id"] is None
        or receipt["recovery_assent_status"] != "proposed"
        or receipt["recovery_commit_fingerprint"] is not None
        or receipt["dispatch_authorized"]
    ):
        raise ValueError("recovery proposal lacks held abort authority")
    if status == "aborted" and (
        receipt["action"] not in {"ratify_recovery", "status"}
        or receipt["transaction_status"] != "aborted"
        or receipt["recovery_status"] != "aborted"
        or receipt["recovery_commit_fingerprint"] is None
        or not receipt["dispatch_authorized"]
    ):
        raise ValueError("aborted receipt lacks committed recovery evidence")
    if receipt["replayed"] and (
        receipt["action"] != "replay" or status != "applied"
    ):
        raise ValueError("replayed receipt is contradictory")


def _refuse(
    action: str, workflow: Mapping[str, Any], reason_code: str
) -> dict[str, Any]:
    return _build_receipt(
        action,
        workflow,
        status=_REFUSAL_STATUS.get(reason_code, "failed"),
        reason_code=reason_code,
    )


def _fingerprint_refusal(
    action: str,
    workflow: Mapping[str, Any],
    expected_proposal_fingerprint: str,
) -> Optional[dict[str, Any]]:
    if workflow["proposal_fingerprint"] != expected_proposal_fingerprint:
        return _refuse(action, workflow, REASON_PROPOSAL_CHANGED)
    return None


__all__ = [
    "ABORT_TOOL",
    "AssentGateway",
    "EditorialWorkspacePublishWorkflowAPI",
    "EditorialWorkspacePublishWorkflowError",
    "INSPECT_TOOL",
    "InMemoryAssentGateway",
    "InMemoryEditorialWorkspacePublishWorkflowStore",
    "PROPOSAL_KIND",
    "PUBLISH_TOOL",
    "RECEIPT_KIND",
    "SessionFactoryAssentGateway",
    "SessionFactoryEditorialWorkspacePublishWorkflowStore",
    "WORKFLOW_KIND",
    "abort_commit_operator_sequence",
    "make_editorial_workspace_publish_workflow_api",
    "publish_commit_operator_sequence",
    "publish_discovery_arguments",
]
