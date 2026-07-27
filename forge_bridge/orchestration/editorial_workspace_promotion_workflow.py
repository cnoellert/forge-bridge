"""forge-bridge #244 / Pipeline Phase 156 — workspace main-promotion workflow.

One durable product workflow over the stream-to-main promotion rails admitted
at v1.9.13. It exposes four async transitions — ``propose``, ``ratify_apply``,
``status``, ``replay`` — and returns exactly one closed, path-free
``bridge.editorial_workspace.promotion_workflow_receipt`` mapping for every
successful transition and every post-propose refusal. A failure before a
durable proposal exists raises ``EditorialWorkspacePromotionWorkflowError``,
which carries a stable ``.code``.

Boundary discipline (handoff §1): Bridge owns graph composition, the
AssentRecord lifecycle, ratification, verify-before-apply commit, durable
workflow state, serialization, status, and replay. Pipeline owns all three
operation contracts, path resolution, resource semantics, catalog semantics,
and fresh proof. The Shell names held authority by identity and fingerprint
only — never a graph, path, plan body, manifest, resolved plan, AssentRecord,
commit receipt, or promoted asset ID.

Composition (handoff §5). Bridge — not Pipeline — constructs the seven-node
graph::

    forge_promote_shot_resource_stream
      -> commit
      -> pipeline.shot_resource.stream_promotion.validate
      -> pipeline.shot_resource.stream_promotion.registration_plan
      -> commit
      -> pipeline.editorial_workspace.main_promotion.registration_plan
      -> commit

Three things are genuinely unlike the shipped #241/#242 siblings:

1. **ONE AssentRecord governs all THREE commits.** ``UnifiedDispatch`` carries a
   single ``assent_record`` and hands it to every commit node; ``CommitBoundary``
   reads it and never consumes it (``CommitNode.verify`` only asks whether
   ``status == "ratified"``). ``propose`` discovers only and never mutates.

2. **Replay is RESUMABLE, not observational.** In #241/#242 replay is a pure
   read. Here it forward-completes over the ORIGINAL proposal, graph, assent,
   and held manifests. That is only possible because each stage carries durable
   status, so replay can resume at the first incomplete stage instead of
   re-running a copy that already happened. It creates no new AssentRecord, no
   new proposal, and cannot widen roles, resource IDs, target main number, or
   actor. A partial failure therefore leaves the AssentRecord *ratified* — the
   operator's authority still governs the same graph; the work is incomplete,
   not withdrawn.

3. **``partial_failed`` is a real terminal disposition** (handoff §7). Version-
   only, Media-only, location, or lineage interruption yields ``partial_failed``
   with ``main_advanced=false`` and ``reconciliation_required=true``. Success
   separately proves physical copy, promoted-resource catalog registration, and
   immutable main Version/Media registration — three stage statuses and six
   manifest/commit fingerprints in one closed receipt.

Privacy (handoff §3/§9). ``promotion_plan``, ``promotion_callable_intent`` and
``workspace_main_promotion_plan`` are private backend-to-Bridge authority
carrying absolute paths. They are persisted for verification and replay but
never reach a receipt, a log line, or an error string. No path, plan body,
callable intent, manifest body, resolved plan, graph, journal, native result,
or exception detail may occur in a receipt.

ponytail: this module carries its own ``AssentGateway`` copy, matching the
precedent already set by #241 and #242 — ``workflow_core`` holds shared
*mechanism*, and an assent seam shared across three workflow contracts would
let one workflow's lifecycle silently govern another's.
"""

from __future__ import annotations

import uuid
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

PROPOSAL_KIND = "pipeline.editorial_workspace.promotion_workflow_proposal"
PROPOSAL_SCHEMA_VERSION = 1
RECEIPT_KIND = "bridge.editorial_workspace.promotion_workflow_receipt"
RECEIPT_SCHEMA_VERSION = 1

# Durable row discriminator inside the shared orch_workflow_record family
# (migration 0016 — no new migration is needed for a new kind).
WORKFLOW_KIND = "bridge.editorial_workspace.promotion_workflow"

PROMOTE_TOOL = "forge_promote_shot_resource_stream"
RESOURCE_REGISTER_TOOL = "forge_register_shot_resource_promotion"
MAIN_REGISTER_TOOL = "forge_register_editorial_workspace_main_promotion"

PROMOTION_CALLABLE_OPERATION_TYPE = (
    "pipeline.shot_resource.stream_promotion.callable"
)
VALIDATE_OPERATION = "pipeline.shot_resource.stream_promotion.validate"
RESOURCE_PLAN_OPERATION = (
    "pipeline.shot_resource.stream_promotion.registration_plan"
)
MAIN_PLAN_OPERATION = (
    "pipeline.editorial_workspace.main_promotion.registration_plan"
)
MAIN_PLAN_KIND = "pipeline.editorial_workspace.main_promotion_plan"

PROMOTE_STATE_OWNER = "peer_owned"

# --------------------------------------------------------------------------- #
# Stable, path-free refusal codes (handoff §11)
# --------------------------------------------------------------------------- #
REASON_PROPOSAL_INVALID = "promotion_workflow_proposal_invalid"
REASON_PROPOSAL_NOT_FOUND = "promotion_workflow_proposal_not_found"
REASON_PROPOSAL_CHANGED = "promotion_workflow_proposal_changed"
REASON_CALLABLE_UNAVAILABLE = "promotion_workflow_callable_unavailable"
REASON_MANIFEST_INVALID = "promotion_workflow_manifest_invalid"
REASON_MANIFEST_DRIFT = "promotion_workflow_manifest_drift"
REASON_ASSENT_INVALID = "promotion_workflow_assent_invalid"
REASON_RESOURCE_COPY_FAILED = "promotion_workflow_resource_copy_failed"
REASON_RESOURCE_REGISTRATION_FAILED = (
    "promotion_workflow_resource_registration_failed"
)
REASON_MAIN_REGISTRATION_FAILED = "promotion_workflow_main_registration_failed"
REASON_PARTIAL_RECONCILIATION_REQUIRED = (
    "promotion_workflow_partial_reconciliation_required"
)
REASON_STATUS_UNAVAILABLE = "promotion_workflow_status_unavailable"
REASON_REPLAY_UNAVAILABLE = "promotion_workflow_replay_unavailable"
REASON_REPLAY_DRIFT = "promotion_workflow_replay_drift"

# Handoff §9 offers no "refused" taxon, so — exactly as accepted on #242 — a
# post-propose refusal is "failed" (something was attempted and did not stand)
# or "unavailable" (the transition was never on offer). A refusal over a
# workflow that already carries partial work reports "partial_failed" instead;
# that override is computed from durable stage state, not from this table.
_REFUSAL_STATUS: dict[str, str] = {
    REASON_PROPOSAL_CHANGED: "failed",
    REASON_CALLABLE_UNAVAILABLE: "unavailable",
    REASON_MANIFEST_INVALID: "failed",
    REASON_MANIFEST_DRIFT: "failed",
    REASON_ASSENT_INVALID: "failed",
    REASON_RESOURCE_COPY_FAILED: "failed",
    REASON_RESOURCE_REGISTRATION_FAILED: "failed",
    REASON_MAIN_REGISTRATION_FAILED: "failed",
    REASON_PARTIAL_RECONCILIATION_REQUIRED: "partial_failed",
    REASON_STATUS_UNAVAILABLE: "unavailable",
    REASON_REPLAY_UNAVAILABLE: "unavailable",
    REASON_REPLAY_DRIFT: "failed",
}

_TRUSTED_STATUSES = frozenset({"proposed", "applied"})
_REVIEW_STATUSES = frozenset({"partial_failed", "unavailable"})

# --------------------------------------------------------------------------- #
# Closed field sets (handoff §3)
# --------------------------------------------------------------------------- #
_PROPOSAL_FIELDS = frozenset({
    "kind",
    "schema_version",
    "project_id",
    "requested_by",
    "promotion_preview_id",
    "promotion_preview_fingerprint",
    "promotion_authority_fingerprint",
    "publish_preview_id",
    "publish_preview_fingerprint",
    "source_version_id",
    "source_main_version_id",
    "target_main_version_number",
    "selected_roles",
    "published_resource_asset_ids",
    "promotion_plan_fingerprint",
    "promotion_callable_intent_fingerprint",
    "workspace_main_promotion_plan_fingerprint",
    "promotion_plan",
    "promotion_callable_intent",
    "workspace_main_promotion_plan",
    "fingerprint",
})
_PROPOSAL_TEXT_FIELDS = (
    "project_id",
    "requested_by",
    "promotion_preview_id",
    "publish_preview_id",
    "source_version_id",
    "source_main_version_id",
)
_PROPOSAL_SHA256_FIELDS = (
    "promotion_preview_fingerprint",
    "promotion_authority_fingerprint",
    "publish_preview_fingerprint",
    "promotion_plan_fingerprint",
    "promotion_callable_intent_fingerprint",
    "workspace_main_promotion_plan_fingerprint",
    "fingerprint",
)
_PROPOSAL_ID_LIST_FIELDS = ("selected_roles", "published_resource_asset_ids")
# Each nested private authority and the field carrying its own fingerprint.
_PROPOSAL_NESTED_FIELDS = (
    ("promotion_plan", "promotion_plan_fingerprint"),
    ("promotion_callable_intent", "promotion_callable_intent_fingerprint"),
    (
        "workspace_main_promotion_plan",
        "workspace_main_promotion_plan_fingerprint",
    ),
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

# Ordered receipt keys (handoff §9). ``fingerprint`` is canonical SHA-256 over
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
    "promotion_preview_id",
    "promotion_preview_fingerprint",
    "promotion_authority_fingerprint",
    "source_version_id",
    "source_main_version_id",
    "target_main_version_number",
    "selected_roles",
    "published_resource_asset_ids",
    "promoted_resource_asset_ids",
    "main_version_id",
    "main_media_id",
    "assent_record_id",
    "assent_status",
    "resource_copy_manifest_fingerprint",
    "resource_copy_commit_fingerprint",
    "resource_copy_status",
    "resource_registration_manifest_fingerprint",
    "resource_registration_commit_fingerprint",
    "resource_registration_status",
    "main_registration_manifest_fingerprint",
    "main_registration_commit_fingerprint",
    "main_registration_status",
    "dispatch_authorized",
    "applied",
    "replayed",
    "main_advanced",
    "reconciliation_required",
    "reason_code",
)
_RECEIPT_FINGERPRINT_EXCLUDES = frozenset({"kind", "schema_version"})

_ACTIONS = frozenset({"propose", "ratify_apply", "status", "replay"})
_STATUSES = frozenset({
    "proposed",
    "applied",
    "partial_failed",
    "failed",
    "unavailable",
})
# Handoff §8: the stage values are NOT interchangeable. Physical resource copy
# is "applied"; the two catalog stages are "registered".
_STAGE_STATUSES = frozenset({"not_started", "applied", "registered", "failed"})

# The three stages, in graph order: (durable key, complete value).
_STAGES: tuple[tuple[str, str], ...] = (
    ("resource_copy", "applied"),
    ("resource_registration", "registered"),
    ("main_registration", "registered"),
)


class EditorialWorkspacePromotionWorkflowError(Exception):
    """Raised only when a transition cannot ground a durable proposal (§11).

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


class _AssentUnavailable(Exception):
    """Internal: the AssentRecord could not be ratified or reloaded."""


# --------------------------------------------------------------------------- #
# Durable store
# --------------------------------------------------------------------------- #
class InMemoryEditorialWorkspacePromotionWorkflowStore(InMemoryWorkflowStore):
    """Process-local store — unit tests and stock installs without Postgres."""

    def __init__(self) -> None:
        super().__init__(authority_field="promotion_authority_fingerprint")


class SessionFactoryEditorialWorkspacePromotionWorkflowStore(
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
        authority_field="promotion_authority_fingerprint",
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

    async def get(self, graph_intent_id: str) -> Any:
        """Reload the record WITHOUT transitioning it — the replay rail."""
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

    async def get(self, graph_intent_id: str) -> Any:
        from forge_bridge.store.assent_record_repo import AssentRecordRepo

        async with self._session_factory() as session:
            record = await AssentRecordRepo(session).get_by_graph_intent_id(
                graph_intent_id
            )
        if record is None:
            raise _AssentUnavailable("no assent record for that graph intent")
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
    content-addressed on the held body, and only ``proposed`` ratifies. The row
    id is derived from that same content so a captured receipt fixture is
    reproducible; the Postgres gateway keeps its random uuid4.
    """

    def __init__(self) -> None:
        self._records: dict[str, Any] = {}
        self.ratify_calls: list[str] = []

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
            id=uuid.uuid5(uuid.NAMESPACE_URL, graph_intent_id),
            graph_intent_id=graph_intent_id,
            chain_steps=list(chain_steps),
            status="proposed",
            metadata=dict(metadata),
        )
        self._records[graph_intent_id] = record
        return record

    async def ratify(self, graph_intent_id: str, *, actor: str) -> Any:
        self.ratify_calls.append(graph_intent_id)
        record = self._records.get(graph_intent_id)
        if record is None:
            raise _AssentUnavailable("no assent record for that graph intent")
        if record.status != "proposed":
            raise _AssentUnavailable("assent record is not proposed")
        record.status = "ratified"
        record.decided_by = actor
        return record

    async def get(self, graph_intent_id: str) -> Any:
        record = self._records.get(graph_intent_id)
        if record is None:
            raise _AssentUnavailable("no assent record for that graph intent")
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


# --------------------------------------------------------------------------- #
# Graph composition (handoff §5)
# --------------------------------------------------------------------------- #
def promotion_discovery_arguments(
    callable_intent: Mapping[str, Any],
) -> dict[str, Any]:
    """The discovery node arguments: the retained intent plus mode=discover.

    Handoff §5: Bridge must not rebuild or widen the retained callable intent.
    """
    return {
        "params": callable_intent["params"],
        "bridge_asset_ids": callable_intent["bridge_asset_ids"],
        "idempotency_key": callable_intent["idempotency_key"],
        "project_id": callable_intent["project_id"],
        "requested_by": callable_intent["requested_by"],
        "mode": "discover",
    }


def main_registration_plan_arguments(
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    """Arguments for the new main registration-plan node (handoff §5)."""
    intent = proposal["promotion_callable_intent"]
    return {
        "workspace_main_promotion_plan": proposal[
            "workspace_main_promotion_plan"
        ],
        "idempotency_key": f"{intent['idempotency_key']}:main-registration-plan",
        "project_id": proposal["project_id"],
        "requested_by": proposal["requested_by"],
    }


def promotion_operator_sequence(
    proposal: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """The exact seven-node graph of handoff §5, composed by Bridge.

    The Shell never submits it. ``propose`` executes node 0 only; the six-node
    tail is the assent-gated remainder, executed (whole or resumed) by
    ``ratify_apply`` / ``replay``.
    """
    return [
        _promote_step(proposal),
        *promotion_commit_tail(proposal),
    ]


def promotion_commit_tail(
    proposal: Mapping[str, Any],
    *,
    held_resource_copy_manifest: Optional[Mapping[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Nodes 1..6: the assent-gated tail of the seven-node graph."""
    return [
        _commit_step("promotion", held=held_resource_copy_manifest),
        _validate_step(),
        _resource_plan_step(),
        _commit_step("registration"),
        _main_plan_step(proposal),
        _commit_step("main"),
    ]


def _promote_step(proposal: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "operator_id": PROMOTE_TOOL,
        "arguments": promotion_discovery_arguments(
            proposal["promotion_callable_intent"]
        ),
        "inputs": [],
        "output_artifact_id": "promotion:held",
        "output_artifact_type": "mutation_plan",
    }


def _validate_step(
    *, promotion_commit: Optional[Mapping[str, Any]] = None
) -> dict[str, Any]:
    step: dict[str, Any] = {
        "operator_id": VALIDATE_OPERATION,
        "arguments": {},
        "inputs": [],
        "output_artifact_id": "promotion:validation",
        "output_artifact_type": (
            "pipeline.shot_resource.stream_promotion_validation_result"
        ),
    }
    if promotion_commit is None:
        step["inputs"] = [_input("promotion:commit", "commit_result",
                                "promotion_commit")]
    else:
        # Resumed run: the durable projection of the ALREADY-committed copy
        # stage stands in for the upstream node, so the copy is never re-run.
        step["arguments"] = {"promotion_commit": dict(promotion_commit)}
    return step


def _resource_plan_step(
    *, promotion_commit: Optional[Mapping[str, Any]] = None
) -> dict[str, Any]:
    inputs = [
        _input(
            "promotion:validation",
            "pipeline.shot_resource.stream_promotion_validation_result",
            "promotion_validation",
        )
    ]
    step: dict[str, Any] = {
        "operator_id": RESOURCE_PLAN_OPERATION,
        "arguments": {},
        "inputs": inputs,
        "output_artifact_id": "registration:held",
        "output_artifact_type": "mutation_plan",
    }
    if promotion_commit is None:
        step["inputs"] = [
            _input("promotion:commit", "commit_result", "promotion_commit"),
            *inputs,
        ]
    else:
        step["arguments"] = {"promotion_commit": dict(promotion_commit)}
    return step


def _main_plan_step(
    proposal: Mapping[str, Any],
    *,
    registration_commit: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    arguments = main_registration_plan_arguments(proposal)
    step: dict[str, Any] = {
        "operator_id": MAIN_PLAN_OPERATION,
        "arguments": arguments,
        "inputs": [],
        "output_artifact_id": "main:held",
        "output_artifact_type": "mutation_plan",
    }
    if registration_commit is None:
        step["inputs"] = [
            _input(
                "registration:commit",
                "commit_result",
                "promotion_registration_commit",
            )
        ]
    else:
        arguments["promotion_registration_commit"] = dict(registration_commit)
    return step


def _commit_step(
    prefix: str, *, held: Optional[Mapping[str, Any]] = None
) -> dict[str, Any]:
    step: dict[str, Any] = {
        "operator_id": "commit",
        "arguments": {},
        "inputs": [_input(f"{prefix}:held", "mutation_plan", "held")],
        "output_artifact_id": f"{prefix}:commit",
        "output_artifact_type": "commit_result",
    }
    if held is not None:
        # The held manifest persisted at propose, replayed under ratified
        # assent — CommitBoundary re-verifies it against fresh host state.
        step["inputs"] = []
        step["held"] = dict(held)
    return step


def _input(artifact_id: str, artifact_type: str, role: str) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "metadata": {"role": role},
    }


# --------------------------------------------------------------------------- #
# The API
# --------------------------------------------------------------------------- #
DiscoverFn = Callable[[Sequence[Mapping[str, Any]]], Awaitable[Any]]
PreviewFn = Callable[..., Awaitable[dict[str, Any]]]
ExecuteFn = Callable[..., Awaitable[dict[str, Any]]]
SettleFn = Callable[..., Awaitable[None]]


class EditorialWorkspacePromotionWorkflowAPI:
    """Closed workspace main-promotion workflow over discover + assent + commit."""

    def __init__(
        self,
        *,
        store: WorkflowStore,
        discover_fn: DiscoverFn,
        preview_fn: PreviewFn,
        execute_fn: ExecuteFn,
        settle_fn: SettleFn,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        self._store = store
        self._discover_fn = discover_fn
        self._preview_fn = preview_fn
        self._execute_fn = execute_fn
        self._settle_fn = settle_fn
        self._clock = clock or utc_now_iso
        self._guard = ProposalTransitionGuard(store)

    # -- propose ----------------------------------------------------------- #
    async def propose(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        """Discover the physical promotion only. Never verifies or applies."""
        normalized = _validate_proposal(proposal)
        proposal_fingerprint = normalized["fingerprint"]
        proposal_id = workflow_identifier("epr_", proposal_fingerprint)
        workflow_id = workflow_identifier("eprf_", proposal_fingerprint)

        existing = await self._store.get_by_proposal_id(proposal_id)
        if existing is not None:
            # Exact duplicate: the ORIGINAL durable proposal receipt (§12.2).
            return _build_receipt("propose", existing, status="proposed")

        collision = await self._store.get_by_authority_fingerprint(
            normalized["promotion_authority_fingerprint"]
        )
        if collision is not None:
            # §12.3: the same authority under a different proposal fails closed.
            raise EditorialWorkspacePromotionWorkflowError(
                REASON_PROPOSAL_INVALID,
                "promotion authority is already bound to a different proposal",
            )

        composition = promotion_operator_sequence(normalized)
        try:
            held_manifest = await self._discover(composition[:1])
        except _DiscoveryUnavailable as exc:
            raise EditorialWorkspacePromotionWorkflowError(
                REASON_CALLABLE_UNAVAILABLE,
                "stream promotion callable did not answer",
            ) from exc
        except _DiscoveryDrift as exc:
            raise EditorialWorkspacePromotionWorkflowError(
                REASON_MANIFEST_INVALID,
                "stream promotion discovery was not trusted",
            ) from exc

        _verify_promotion_manifest(held_manifest, normalized)

        preview = await self._preview(
            held_manifest=held_manifest,
            chain_steps=_chain_steps(normalized),
            display="Phase 156 workspace main promotion",
        )

        now = self._clock()
        record: dict[str, Any] = {
            "kind": WORKFLOW_KIND,
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "workflow_id": workflow_id,
            "proposal_id": proposal_id,
            "proposal_fingerprint": proposal_fingerprint,
            # Private: retained for verification + replay, never projected.
            "proposal": normalized,
            "promotion_preview_id": normalized["promotion_preview_id"],
            "promotion_preview_fingerprint": normalized[
                "promotion_preview_fingerprint"
            ],
            "promotion_authority_fingerprint": normalized[
                "promotion_authority_fingerprint"
            ],
            "source_version_id": normalized["source_version_id"],
            "source_main_version_id": normalized["source_main_version_id"],
            "target_main_version_number": normalized[
                "target_main_version_number"
            ],
            "selected_roles": list(normalized["selected_roles"]),
            "published_resource_asset_ids": list(
                normalized["published_resource_asset_ids"]
            ),
            "promoted_resource_asset_ids": [],
            "main_version_id": None,
            "main_media_id": None,
            "graph_node_sequence": [
                str(step["operator_id"]) for step in composition
            ],
            "assent_graph_intent_id": preview["graph_intent_id"],
            "assent_record_id": preview["assent_record_id"],
            "assent_status": "proposed",
            # Stage 1 is the only manifest that exists at propose time; the
            # other two are derived from commit evidence during apply.
            "resource_copy_held_manifest": held_manifest,
            "resource_copy_manifest_fingerprint": canonical_fingerprint(
                held_manifest
            ),
            "resource_copy_commit_fingerprint": None,
            "resource_copy_commit_output": None,
            "resource_copy_status": "not_started",
            "resource_registration_manifest_fingerprint": None,
            "resource_registration_commit_fingerprint": None,
            "resource_registration_commit_output": None,
            "resource_registration_status": "not_started",
            "main_registration_manifest_fingerprint": None,
            "main_registration_commit_fingerprint": None,
            "main_registration_status": "not_started",
            "status": "proposed",
            "reason_code": None,
            "replayed": False,
            "created_at": now,
            "requested_by": normalized["requested_by"],
            "actors": {"propose": normalized["requested_by"]},
            "timestamps": {"propose": now},
        }
        try:
            stored = await self._store.create(record)
        except Exception as exc:  # noqa: BLE001 - durable persistence failure
            raise EditorialWorkspacePromotionWorkflowError(
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
            # per-process lock was lost (§12.16).
            if workflow["status"] == "applied":
                return _build_receipt(
                    "ratify_apply", workflow, status="applied"
                )
            if workflow["status"] == "partial_failed":
                # Forward completion is replay's job, never a second ratify.
                return _refuse(
                    "ratify_apply",
                    workflow,
                    REASON_PARTIAL_RECONCILIATION_REQUIRED,
                )
            if (
                workflow["status"] != "proposed"
                or workflow["assent_status"] != "proposed"
            ):
                return _refuse("ratify_apply", workflow, REASON_ASSENT_INVALID)
            return await self._transition(
                "ratify_apply",
                workflow,
                requested_by=requested_by,
                ratify=True,
            )

    # -- status ------------------------------------------------------------ #
    async def status(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
    ) -> dict[str, Any]:
        """Read durable Bridge workflow state.

        Performs no discovery, no assent transition, no commit, and no MCP
        apply (§8 / §12.14).
        """
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "status", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed
        return _build_receipt("status", workflow, status=workflow["status"])

    # -- replay ------------------------------------------------------------ #
    async def replay(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
        requested_by: str,
    ) -> dict[str, Any]:
        """Forward-complete the original graph idempotently (§7).

        Uses the original proposal, graph, AssentRecord, held manifests, and
        commit identities. Creates no new proposal and no new AssentRecord, and
        cannot widen roles, resource IDs, target main number, or actor.
        """
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "replay", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed

        async with self._guard.lock(proposal_id):
            workflow = await self._reload_or_raise(proposal_id)
            if workflow["status"] == "applied":
                # §12.13: replay of a completed graph performs NO mutation.
                return _build_receipt("replay", workflow, status="applied")
            if workflow["status"] not in {"partial_failed", "failed"}:
                # An unratified proposal has no authority to forward-complete.
                return _refuse("replay", workflow, REASON_REPLAY_UNAVAILABLE)
            return await self._transition(
                "replay", workflow, requested_by=requested_by, ratify=False
            )

    # -- internals --------------------------------------------------------- #
    async def _transition(
        self,
        action: str,
        workflow: Mapping[str, Any],
        *,
        requested_by: str,
        ratify: bool,
    ) -> dict[str, Any]:
        """Run the assent-gated tail from the first incomplete stage."""
        held = workflow.get("resource_copy_held_manifest")
        if not isinstance(held, Mapping) or canonical_fingerprint(
            dict(held)
        ) != workflow["resource_copy_manifest_fingerprint"]:
            return _refuse(
                action,
                workflow,
                REASON_MANIFEST_DRIFT if ratify else REASON_REPLAY_DRIFT,
            )

        sequence, stage_nodes = _tail_for(workflow, held_manifest=held)
        if not sequence:
            # Every stage is already complete; nothing left to forward-complete.
            return _build_receipt(action, workflow, status="applied")

        outcome = await self._execute_fn(
            graph_intent_id=workflow["assent_graph_intent_id"],
            requested_by=requested_by,
            operator_sequence=sequence,
            ratify=ratify,
        )
        if outcome.get("outcome") != "ratified":
            patch = _stamp(workflow, action, requested_by, self._clock())
            patch["assent_status"] = outcome.get("assent_status")
            reason = outcome.get("reason_code") or REASON_ASSENT_INVALID
            patch["reason_code"] = reason
            patch["status"] = _terminal_status(workflow, reason)
            stored = await self._store.update(workflow["proposal_id"], patch)
            return _refuse(action, stored, reason, status=patch["status"])

        patch = _stage_patch(workflow, outcome.get("results") or {}, stage_nodes)
        patch.update(_stamp(workflow, action, requested_by, self._clock()))
        if action == "replay" and patch["status"] == "applied":
            patch["replayed"] = True

        # The AssentRecord settles ONLY on a terminal disposition. A partial
        # failure leaves it ratified so replay can forward-complete under the
        # SAME authority without minting a new record (§7).
        if patch["status"] == "applied":
            patch["assent_status"] = "applied"
            await self._settle_fn(
                graph_intent_id=workflow["assent_graph_intent_id"],
                disposition="applied",
                result={"applied": True},
            )
        elif patch["status"] == "failed":
            patch["assent_status"] = "failed"
            await self._settle_fn(
                graph_intent_id=workflow["assent_graph_intent_id"],
                disposition="failed",
                result={"error": {"type": patch.get("commit_reason_code")}},
            )
        else:
            patch["assent_status"] = "ratified"
        patch.pop("commit_reason_code", None)

        stored = await self._store.update(workflow["proposal_id"], patch)
        if patch["status"] == "applied":
            return _build_receipt(action, stored, status="applied")
        return _refuse(
            action, stored, patch["reason_code"], status=patch["status"]
        )

    async def _discover(
        self, operator_sequence: Sequence[Mapping[str, Any]]
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
        if output.get("type") != "mutation_plan":
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
        except EditorialWorkspacePromotionWorkflowError:
            raise
        except Exception as exc:  # noqa: BLE001 - persistence failure
            raise EditorialWorkspacePromotionWorkflowError(
                REASON_MANIFEST_INVALID,
                "preview did not persist a durable mutation manifest",
            ) from exc

    async def _load_or_raise(self, proposal_id: str) -> dict[str, Any]:
        workflow = await self._store.get_by_proposal_id(proposal_id)
        if workflow is None:
            raise EditorialWorkspacePromotionWorkflowError(
                REASON_PROPOSAL_NOT_FOUND,
                "no workflow for the supplied proposal id",
            )
        return workflow

    async def _reload_or_raise(self, proposal_id: str) -> dict[str, Any]:
        workflow = await self._guard.reload(proposal_id)
        if workflow is None:
            raise EditorialWorkspacePromotionWorkflowError(
                REASON_PROPOSAL_NOT_FOUND, "workflow disappeared"
            )
        return workflow


# --------------------------------------------------------------------------- #
# Stage machine
# --------------------------------------------------------------------------- #
def _tail_for(
    workflow: Mapping[str, Any], *, held_manifest: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Build the resume sequence + the stage -> commit node id map.

    The resume cursor is the durable per-stage status: a stage that already
    completed is NEVER re-composed, so a replay cannot re-copy bytes or mint a
    second main Version identity. Upstream evidence a skipped stage would have
    produced is supplied from its persisted closed projection instead.
    """
    proposal = workflow["proposal"]
    copy_done = workflow["resource_copy_status"] == "applied"
    registration_done = (
        workflow["resource_registration_status"] == "registered"
    )
    main_done = workflow["main_registration_status"] == "registered"

    steps: list[dict[str, Any]] = []
    stage_nodes: dict[str, dict[str, Optional[str]]] = {}

    def add(step: dict[str, Any]) -> str:
        node_id = f"{step['operator_id']}#{len(steps)}"
        steps.append(step)
        return node_id

    if not copy_done:
        # Stage 1's held manifest is the one persisted at propose, so its
        # fingerprint is already durable; the node map records no plan node.
        commit_node = add(_commit_step("promotion", held=held_manifest))
        stage_nodes["resource_copy"] = {"commit": commit_node, "plan": None}
    if not registration_done:
        commit_projection = (
            None if not copy_done else workflow["resource_copy_commit_output"]
        )
        add(_validate_step(promotion_commit=commit_projection))
        plan_node = add(_resource_plan_step(promotion_commit=commit_projection))
        commit_node = add(_commit_step("registration"))
        stage_nodes["resource_registration"] = {
            "commit": commit_node,
            "plan": plan_node,
        }
    if not main_done:
        registration_projection = (
            None
            if not registration_done
            else workflow["resource_registration_commit_output"]
        )
        plan_node = add(
            _main_plan_step(
                proposal, registration_commit=registration_projection
            )
        )
        commit_node = add(_commit_step("main"))
        stage_nodes["main_registration"] = {
            "commit": commit_node,
            "plan": plan_node,
        }
    return steps, stage_nodes


def _stage_patch(
    workflow: Mapping[str, Any],
    results: Mapping[str, Any],
    stage_nodes: Mapping[str, Mapping[str, Optional[str]]],
) -> dict[str, Any]:
    """Read per-stage evidence out of one executed tail run."""
    patch: dict[str, Any] = {}
    reason: Optional[str] = None
    commit_reason: Optional[str] = None
    failed_stage_dispatched = False

    for stage, complete_value in _STAGES:
        nodes = stage_nodes.get(stage)
        if nodes is None:
            continue  # already complete and durably recorded
        result = results.get(nodes["commit"])
        evidence = _commit_evidence(result)
        if evidence is not None and not _stage_complete(stage, evidence):
            # The host applied but did not report a complete catalog snapshot
            # (Version-only, Media-only, location, or lineage interruption).
            # That is dispatched-and-incomplete, never "registered".
            patch[f"{stage}_status"] = "failed"
            failed_stage_dispatched = True
            if reason is None:
                reason = _stage_reason(stage, None)
                commit_reason = "CATALOG_INCOMPLETE"
            break
        if evidence is None:
            code = _reason_code_of(result)
            dispatched = _stage_dispatched(result)
            if dispatched:
                patch[f"{stage}_status"] = "failed"
                failed_stage_dispatched = True
            if reason is None:
                reason = _stage_reason(stage, code)
                commit_reason = code
            break
        patch[f"{stage}_status"] = complete_value
        plan_node = nodes["plan"]
        if plan_node is not None:
            # The manifest this commit verified IS the upstream plan node's
            # output — fingerprinted here, never projected into a receipt.
            patch[f"{stage}_manifest_fingerprint"] = canonical_fingerprint(
                _plan_output(results.get(plan_node))
            )
        patch[f"{stage}_commit_fingerprint"] = evidence["commit_fingerprint"]
        if stage in {"resource_copy", "resource_registration"}:
            patch[f"{stage}_commit_output"] = evidence["output"]
        if stage == "resource_registration":
            patch["promoted_resource_asset_ids"] = evidence["created_asset_ids"]
        if stage == "main_registration":
            patch["main_version_id"] = evidence["main_version_id"]
            patch["main_media_id"] = evidence["main_media_id"]

    merged = {**workflow, **patch}
    if all(
        merged[f"{stage}_status"] == complete for stage, complete in _STAGES
    ):
        # One promoted resource per selected role, or the "applied" claim is
        # unfounded and the workflow needs reconciliation rather than a receipt.
        promoted = merged.get("promoted_resource_asset_ids") or []
        if len(promoted) == len(merged["selected_roles"]):
            patch["status"] = "applied"
            patch["reason_code"] = None
            return patch
        patch["main_registration_status"] = "failed"
        patch["status"] = "partial_failed"
        patch["reason_code"] = REASON_MAIN_REGISTRATION_FAILED
        patch["commit_reason_code"] = "PROMOTED_RESOURCE_COUNT_MISMATCH"
        return patch

    started = any(
        merged[f"{stage}_status"] != "not_started" for stage, _ in _STAGES
    ) or failed_stage_dispatched
    patch["reason_code"] = (
        reason or REASON_PARTIAL_RECONCILIATION_REQUIRED
    )
    patch["commit_reason_code"] = commit_reason
    patch["status"] = "partial_failed" if started else "failed"
    return patch


def _commit_evidence(result: Any) -> Optional[dict[str, Any]]:
    """Closed, path-free evidence for one successfully applied commit node."""
    if getattr(result, "status", None) != "ok":
        return None
    output = getattr(result, "output", None)
    if not isinstance(output, Mapping) or output.get("applied") is not True:
        return None
    apply_result = output.get("apply_result")
    if not isinstance(apply_result, Mapping):
        return None
    return {
        "output": dict(output),
        "commit_fingerprint": canonical_fingerprint(dict(output)),
        "created_asset_ids": _created_asset_ids(apply_result),
        "main_version_id": _text_or_none(apply_result.get("main_version_id")),
        "main_media_id": _text_or_none(apply_result.get("main_media_id")),
        "catalog_registration_status": apply_result.get(
            "catalog_registration_status"
        ),
        "main_advanced": apply_result.get("main_advanced"),
    }


def _stage_complete(stage: str, evidence: Mapping[str, Any]) -> bool:
    """Does this applied commit actually PROVE its stage completed?

    Handoff §6: success requires three separate proofs. An applied commit is
    necessary but not sufficient — the catalog stages must also report their
    own completion, which is exactly where a Version-only / Media-only /
    location / lineage interruption shows up.
    """
    if stage == "resource_registration":
        return (
            evidence["catalog_registration_status"] == "registered"
            and bool(evidence["created_asset_ids"])
        )
    if stage == "main_registration":
        return (
            evidence["main_advanced"] is True
            and evidence["main_version_id"] is not None
            and evidence["main_media_id"] is not None
        )
    return True


def _plan_output(result: Any) -> dict[str, Any]:
    """The mutation manifest a plan node emitted, for its stage fingerprint."""
    output = getattr(result, "output", None)
    return dict(output) if isinstance(output, Mapping) else {}


def _created_asset_ids(apply_result: Mapping[str, Any]) -> list[str]:
    ids = apply_result.get("created_asset_ids")
    if not isinstance(ids, list):
        nested = apply_result.get("publish_register")
        ids = nested.get("created_asset_ids") if isinstance(nested, Mapping) else None
    if not isinstance(ids, list):
        return []
    return sorted({str(item) for item in ids if str(item).strip()})


def _text_or_none(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _reason_code_of(result: Any) -> Optional[str]:
    return getattr(result, "reason_code", None)


def _stage_dispatched(result: Any) -> bool:
    """Did this failed stage reach the host apply?

    ``ASSENT_INVALID`` / ``MUTATION_MANIFEST_INVALID`` /
    ``APPLY_COUNTERPART_NOT_DECLARED`` / ``VERIFICATION_FAILED`` all prove the
    commit never dispatched. ``PLAN_STATE_DRIFT`` is ambiguous in general, but
    ``CommitBoundary`` attaches ``drift_count`` only on the VERIFY-time path —
    so a drift carrying that counter also proves no dispatch.

    ponytail ceiling: Bridge reads only the structured code and that counter.
    It never parses the host message and never guesses a catalog state it did
    not read; anything else is reported as dispatched, which fails closed
    toward reconciliation.
    """
    code = _reason_code_of(result)
    if code in {
        None,
        "ASSENT_INVALID",
        "MUTATION_MANIFEST_INVALID",
        "APPLY_COUNTERPART_NOT_DECLARED",
        "VERIFICATION_FAILED",
    }:
        return False
    if code == "PLAN_STATE_DRIFT":
        output = getattr(result, "output", None)
        error = output.get("error") if isinstance(output, Mapping) else None
        if isinstance(error, Mapping) and "drift_count" in error:
            return False
    return True


def _stage_reason(stage: str, code: Optional[str]) -> str:
    if code == "ASSENT_INVALID":
        return REASON_ASSENT_INVALID
    return {
        "resource_copy": REASON_RESOURCE_COPY_FAILED,
        "resource_registration": REASON_RESOURCE_REGISTRATION_FAILED,
        "main_registration": REASON_MAIN_REGISTRATION_FAILED,
    }[stage]


def _terminal_status(workflow: Mapping[str, Any], reason: str) -> str:
    """A refusal over a workflow that already carries partial work stays partial."""
    if any(
        workflow[f"{stage}_status"] != "not_started" for stage, _ in _STAGES
    ):
        return "partial_failed"
    return _REFUSAL_STATUS.get(reason, "failed")


def _stamp(
    workflow: Mapping[str, Any], action: str, actor: str, now: str
) -> dict[str, Any]:
    return {
        "timestamps": {**workflow["timestamps"], action: now},
        "actors": {**workflow["actors"], action: actor},
    }


def _chain_steps(proposal: Mapping[str, Any]) -> list[str]:
    """Operator-legible chain text for the one AssentRecord over three commits."""
    target = int(proposal["target_main_version_number"])
    return [
        f"promote selected roles to main/v{target:03d}",
        "commit",
        "validate promoted shot resources",
        "plan promoted-resource catalog registration",
        "commit",
        "plan immutable workspace main registration",
        "commit",
    ]


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #
def make_editorial_workspace_promotion_workflow_api(
    *,
    session_factory: Any,
    mcp: Any,
    store: WorkflowStore | None = None,
    assent_gateway: AssentGateway | None = None,
    run_operation: Callable[..., Any] | None = None,
    discover_fn: DiscoverFn | None = None,
    preview_fn: PreviewFn | None = None,
    execute_fn: ExecuteFn | None = None,
    settle_fn: SettleFn | None = None,
    clock: Callable[[], str] | None = None,
) -> EditorialWorkspacePromotionWorkflowAPI:
    """Construct the workflow API.

    Pipeline calls this with ``session_factory`` + ``mcp`` only; the remaining
    keywords are test seams. ``run_operation`` defaults to the forge-core
    operation dispatcher, which is present exactly when Pipeline is installed —
    the same optional federation seam ``run_graph`` uses.
    """
    if store is None:
        if session_factory is None:
            raise ValueError(
                "session_factory is required when store is not supplied"
            )
        store = SessionFactoryEditorialWorkspacePromotionWorkflowStore(
            session_factory
        )
    if assent_gateway is None and (
        preview_fn is None or execute_fn is None or settle_fn is None
    ):
        assent_gateway = SessionFactoryAssentGateway(session_factory)
    if discover_fn is None:
        discover_fn = _default_discover_fn(mcp)
    if preview_fn is None:
        preview_fn = _default_preview_fn(assent_gateway)
    if execute_fn is None:
        execute_fn = _default_execute_fn(assent_gateway, mcp, run_operation)
    if settle_fn is None:
        settle_fn = _default_settle_fn(assent_gateway)
    return EditorialWorkspacePromotionWorkflowAPI(
        store=store,
        discover_fn=discover_fn,
        preview_fn=preview_fn,
        execute_fn=execute_fn,
        settle_fn=settle_fn,
        clock=clock,
    )


def _default_discover_fn(mcp: Any) -> DiscoverFn:
    """Run the discovery node through the admitted graph dispatch surface."""

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


def _default_execute_fn(
    assent_gateway: AssentGateway,
    mcp: Any,
    run_operation: Callable[..., Any] | None,
) -> ExecuteFn:
    async def execute_fn(
        *,
        graph_intent_id: str,
        requested_by: str,
        operator_sequence: Sequence[Mapping[str, Any]],
        ratify: bool,
    ) -> dict[str, Any]:
        from forge_bridge.composition.boundary import MCPToolBoundary
        from forge_bridge.composition.commit_boundary import CommitBoundary
        from forge_bridge.composition.compiler import compile_operator_sequence
        from forge_bridge.composition.dispatch import UnifiedDispatch
        from forge_bridge.composition.executor import GraphExecutor
        from forge_bridge.composition.operation_boundary import (
            OperationDispatchBoundary,
        )

        try:
            if ratify:
                record = await assent_gateway.ratify(
                    graph_intent_id, actor=requested_by
                )
            else:
                # Replay: the ORIGINAL record, reloaded and never re-ratified.
                record = await assent_gateway.get(graph_intent_id)
                if getattr(record, "status", None) != "ratified":
                    raise _AssentUnavailable("assent record is not ratified")
        except _AssentUnavailable:
            return {
                "outcome": "refused",
                "assent_status": None,
                "reason_code": REASON_ASSENT_INVALID,
                "results": {},
            }

        if held_manifest_from_record(record) is None:
            return {
                "outcome": "refused",
                "assent_status": getattr(record, "status", None),
                "reason_code": REASON_MANIFEST_INVALID,
                "results": {},
            }

        runner = run_operation
        if runner is None:
            from forge_bridge.orchestration.operation_runner import (
                OperationRunnerUnavailable,
                build_operation_runner,
            )

            try:
                runner = build_operation_runner()
            except OperationRunnerUnavailable:
                return {
                    "outcome": "refused",
                    "assent_status": getattr(record, "status", None),
                    "reason_code": REASON_CALLABLE_UNAVAILABLE,
                    "results": {},
                }

        # ONE assent record, carried into EVERY commit node of this run.
        dispatch = UnifiedDispatch(
            mcp_boundary=MCPToolBoundary(mcp=mcp),
            operation_boundary=OperationDispatchBoundary(run_operation=runner),
            commit_boundary=CommitBoundary(mcp=mcp),
            assent_record=record,
        )
        spec = compile_operator_sequence(list(operator_sequence))
        results = await GraphExecutor(dispatch.dispatch).run(spec)
        return {
            "outcome": "ratified",
            "assent_status": getattr(record, "status", None),
            "reason_code": None,
            "results": results,
        }

    return execute_fn


def _default_settle_fn(assent_gateway: AssentGateway) -> SettleFn:
    async def settle_fn(
        *,
        graph_intent_id: str,
        disposition: str,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        if disposition == "applied":
            await assent_gateway.mark_applied(
                graph_intent_id, result=dict(result or {})
            )
        elif disposition == "failed":
            await assent_gateway.mark_failed(
                graph_intent_id,
                reason="chain_aborted",
                # Only the structured code — never the host message, which can
                # carry absolute paths.
                result=dict(result or {}),
            )

    return settle_fn


# --------------------------------------------------------------------------- #
# Proposal validation (handoff §3)
# --------------------------------------------------------------------------- #
def _invalid(message: str) -> EditorialWorkspacePromotionWorkflowError:
    return EditorialWorkspacePromotionWorkflowError(
        REASON_PROPOSAL_INVALID, message
    )


def _validate_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on any unknown or missing field, and on every drift (§3)."""
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

    target = proposal["target_main_version_number"]
    if isinstance(target, bool) or not isinstance(target, int) or target <= 0:
        raise _invalid("target_main_version_number must be a positive integer")

    for field in _PROPOSAL_ID_LIST_FIELDS:
        values = proposal[field]
        if (
            not isinstance(values, list)
            or not values
            or any(
                not isinstance(item, str) or not item.strip()
                for item in values
            )
            or sorted(set(values)) != list(values)
        ):
            raise _invalid(f"{field} must be non-empty, unique, and sorted")

    normalized = {key: proposal[key] for key in _PROPOSAL_FIELDS}
    for field, fingerprint_field in _PROPOSAL_NESTED_FIELDS:
        body = normalized[field]
        if not isinstance(body, Mapping):
            raise _invalid(f"proposal field {field} must be a mapping")
        if canonical_fingerprint(dict(body)) != normalized[fingerprint_field]:
            raise _invalid(f"{field} differs from its fingerprint")

    body = {
        key: value
        for key, value in normalized.items()
        if key not in {"kind", "schema_version", "fingerprint"}
    }
    if canonical_fingerprint(body) != normalized["fingerprint"]:
        raise _invalid("proposal fingerprint mismatch")

    _validate_callable_intent(normalized)
    _validate_main_promotion_plan(normalized)
    return normalized


def _validate_callable_intent(proposal: Mapping[str, Any]) -> None:
    intent = proposal["promotion_callable_intent"]
    extra = set(intent.keys()) - _CALLABLE_INTENT_FIELDS
    if extra:
        raise _invalid(
            f"promotion_callable_intent has unknown fields: {sorted(extra)}"
        )
    missing = _CALLABLE_INTENT_FIELDS - set(intent.keys())
    if missing:
        raise _invalid(
            f"promotion_callable_intent is missing fields: {sorted(missing)}"
        )
    if intent["tool"] != PROMOTE_TOOL:
        raise _invalid("callable_intent tool is not the stream promotion")
    if intent["operation_type"] != PROMOTION_CALLABLE_OPERATION_TYPE:
        raise _invalid("callable_intent operation_type is not recognized")
    if intent["project_id"] != proposal["project_id"]:
        raise _invalid("callable_intent project differs from the proposal")
    if not isinstance(intent["params"], Mapping):
        raise _invalid("callable_intent params must be a mapping")
    idempotency_key = intent["idempotency_key"]
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise _invalid("callable_intent idempotency_key must be non-empty")
    if (
        not isinstance(intent["requested_by"], str)
        or not intent["requested_by"].strip()
    ):
        # NB: NOT required to equal the proposal actor. The retained intent is
        # frozen at preview compile time; the Shell names the ratifying actor.
        raise _invalid("callable_intent requested_by must be non-empty")

    bridge_asset_ids = intent["bridge_asset_ids"]
    if not isinstance(bridge_asset_ids, list):
        raise _invalid("callable_intent bridge_asset_ids must be a list")
    missing_assets = [
        asset_id
        for asset_id in proposal["published_resource_asset_ids"]
        if asset_id not in bridge_asset_ids
    ]
    if missing_assets:
        raise _invalid(
            "callable_intent does not carry every published resource"
        )


def _validate_main_promotion_plan(proposal: Mapping[str, Any]) -> None:
    """Cross-check the held main plan against the proposal's public identities.

    ponytail ceiling: the plan body is private Pipeline authority, pinned by its
    own fingerprint. Bridge checks its kind and, for the identity fields it
    ALREADY knows publicly, that any present value agrees. It does not require
    fields it does not own, and never inspects paths.
    """
    plan = proposal["workspace_main_promotion_plan"]
    if plan.get("kind") != MAIN_PLAN_KIND:
        raise _invalid("workspace_main_promotion_plan kind is not recognized")
    checks = (
        ("selected_roles", list(proposal["selected_roles"])),
        (
            "published_resource_asset_ids",
            list(proposal["published_resource_asset_ids"]),
        ),
        ("source_version_id", proposal["source_version_id"]),
        ("source_main_version_id", proposal["source_main_version_id"]),
        ("target_version_number", proposal["target_main_version_number"]),
    )
    for field, expected in checks:
        if field not in plan:
            continue
        value = plan[field]
        if isinstance(expected, list):
            value = sorted(set(value)) if isinstance(value, list) else value
        if value != expected:
            raise _invalid(
                f"workspace_main_promotion_plan {field} differs from the proposal"
            )
    if plan.get("target_stream") not in {None, "main"}:
        raise _invalid("workspace_main_promotion_plan does not target main")


# --------------------------------------------------------------------------- #
# Manifest verification (handoff §5)
# --------------------------------------------------------------------------- #
def _verify_promotion_manifest(
    payload: Mapping[str, Any], proposal: Mapping[str, Any]
) -> None:
    """Prove the discovered manifest IS this proposal's physical promotion."""
    from forge_bridge.composition.admission import (
        AdmissionRejected,
        admit_mutation_counterpart,
    )
    from forge_bridge.graph.mutation import (
        MutationManifest,
        MutationManifestError,
    )

    def fail(detail: str) -> EditorialWorkspacePromotionWorkflowError:
        return EditorialWorkspacePromotionWorkflowError(
            REASON_MANIFEST_INVALID, detail
        )

    try:
        manifest = MutationManifest.from_dict(dict(payload))
    except (MutationManifestError, KeyError, TypeError) as exc:
        raise fail("discovered manifest is structurally invalid") from exc

    if payload.get("trust_status") != "trusted":
        raise fail("discovered manifest is not trusted")
    if payload.get("originating_capability") != PROMOTE_TOOL:
        raise fail("discovered manifest has the wrong originating capability")
    if manifest.apply_counterpart.get("tool") != PROMOTE_TOOL:
        raise fail("discovered manifest has the wrong apply counterpart")
    try:
        counterpart = admit_mutation_counterpart(PROMOTE_TOOL)
    except AdmissionRejected as exc:
        raise fail("apply counterpart is not admitted") from exc
    if (
        counterpart.state_owner != PROMOTE_STATE_OWNER
        or not counterpart.verify_before_apply
        or not counterpart.assent_required
    ):
        raise fail("apply counterpart lacks the required commit authority")

    intent = proposal["promotion_callable_intent"]
    manifest_intent = payload.get("intent_parameters")
    if not isinstance(manifest_intent, Mapping):
        raise fail("discovered manifest carries no intent parameters")
    if manifest_intent.get("params") != dict(intent["params"]):
        raise fail("manifest intent parameters differ from the callable intent")
    if manifest_intent.get("idempotency_key") != intent["idempotency_key"]:
        raise fail("manifest idempotency key differs from the callable intent")

    records = payload.get("resolved_plan")
    if not isinstance(records, list) or not records:
        raise fail("promotion manifest carries no change record")
    identity = (
        records[0].get("identity") if isinstance(records[0], Mapping) else None
    )
    if not isinstance(identity, Mapping):
        raise fail("change record carries no identity")
    if identity.get("operation_type") != PROMOTION_CALLABLE_OPERATION_TYPE:
        raise fail("change record operation type is not recognized")


# --------------------------------------------------------------------------- #
# Receipts (handoff §9)
# --------------------------------------------------------------------------- #
def _trust_status(status: str) -> str:
    if status in _TRUSTED_STATUSES:
        return "trusted"
    if status in _REVIEW_STATUSES:
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
    stage_statuses = {
        f"{stage}_status": (
            "not_started" if proposed_view else workflow[f"{stage}_status"]
        )
        for stage, _complete in _STAGES
    }
    dispatch_authorized = any(
        value != "not_started" for value in stage_statuses.values()
    )

    receipt: dict[str, Any] = {
        "kind": RECEIPT_KIND,
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "action": action,
        "status": status,
        "trust_status": _trust_status(status),
        "workflow_id": workflow["workflow_id"],
        "proposal_id": workflow["proposal_id"],
        "proposal_fingerprint": workflow["proposal_fingerprint"],
        "promotion_preview_id": workflow["promotion_preview_id"],
        "promotion_preview_fingerprint": workflow[
            "promotion_preview_fingerprint"
        ],
        "promotion_authority_fingerprint": workflow[
            "promotion_authority_fingerprint"
        ],
        "source_version_id": workflow["source_version_id"],
        "source_main_version_id": workflow["source_main_version_id"],
        "target_main_version_number": workflow["target_main_version_number"],
        "selected_roles": sorted(set(workflow["selected_roles"])),
        "published_resource_asset_ids": sorted(
            set(workflow["published_resource_asset_ids"])
        ),
        "promoted_resource_asset_ids": (
            []
            if proposed_view
            else sorted(set(workflow.get("promoted_resource_asset_ids") or []))
        ),
        "main_version_id": None if proposed_view else workflow.get(
            "main_version_id"
        ),
        "main_media_id": None if proposed_view else workflow.get(
            "main_media_id"
        ),
        "assent_record_id": workflow["assent_record_id"],
        "assent_status": (
            "proposed" if proposed_view else workflow.get("assent_status")
        ),
        "resource_copy_manifest_fingerprint": workflow[
            "resource_copy_manifest_fingerprint"
        ],
        "resource_copy_commit_fingerprint": (
            None
            if proposed_view
            else workflow.get("resource_copy_commit_fingerprint")
        ),
        "resource_registration_manifest_fingerprint": (
            None
            if proposed_view
            else workflow.get("resource_registration_manifest_fingerprint")
        ),
        "resource_registration_commit_fingerprint": (
            None
            if proposed_view
            else workflow.get("resource_registration_commit_fingerprint")
        ),
        "main_registration_manifest_fingerprint": (
            None
            if proposed_view
            else workflow.get("main_registration_manifest_fingerprint")
        ),
        "main_registration_commit_fingerprint": (
            None
            if proposed_view
            else workflow.get("main_registration_commit_fingerprint")
        ),
        "dispatch_authorized": dispatch_authorized,
        "applied": applied,
        "replayed": action == "replay" and applied,
        "main_advanced": applied,
        "reconciliation_required": status == "partial_failed",
        "reason_code": (
            None
            if proposed_view
            else reason_code
            or (
                workflow.get("reason_code")
                if status in {"failed", "unavailable", "partial_failed"}
                else None
            )
        ),
        **stage_statuses,
    }

    ordered = finalize_receipt(
        receipt,
        _RECEIPT_KEYS,
        fingerprint_excludes=_RECEIPT_FINGERPRINT_EXCLUDES,
    )
    _assert_receipt_invariants(ordered)
    return ordered


def _assert_receipt_invariants(receipt: Mapping[str, Any]) -> None:
    """Fail closed on any §9 invariant a caller could otherwise leak."""
    status = receipt["status"]
    for field in (
        "resource_copy_status",
        "resource_registration_status",
        "main_registration_status",
    ):
        if receipt[field] not in _STAGE_STATUSES:
            raise ValueError(f"receipt {field} is unsupported")
    for field in (
        "selected_roles",
        "published_resource_asset_ids",
        "promoted_resource_asset_ids",
    ):
        values = receipt[field]
        if sorted(set(values)) != list(values):
            raise ValueError(f"receipt {field} must be unique and sorted")
    if not receipt["selected_roles"] or not receipt[
        "published_resource_asset_ids"
    ]:
        raise ValueError("receipt role and resource lists must be non-empty")
    # NB (contract divergence, surfaced not smoothed): Pipeline's shipped
    # receipt dataclass binds status "proposed" to action == "propose", so a
    # `status` poll on a still-proposed workflow is rejected there. This is the
    # SAME defect Pipeline already fixed for the #242 publish receipt
    # (1ce539a9) and did not fix here. Bridge answers truthfully; there is no
    # other honest status in the closed vocabulary. Tracked in the #244 PR body.
    if status == "proposed" and (
        receipt["dispatch_authorized"]
        or receipt["applied"]
        or receipt["replayed"]
        or receipt["main_advanced"]
        or receipt["reconciliation_required"]
        or receipt["promoted_resource_asset_ids"]
        or receipt["assent_status"] != "proposed"
        or receipt["resource_copy_manifest_fingerprint"] is None
        or any(
            receipt[f"{stage}_status"] != "not_started" for stage, _ in _STAGES
        )
    ):
        raise ValueError("proposed promotion receipt is contradictory")
    if status == "applied" and (
        not receipt["dispatch_authorized"]
        or not receipt["applied"]
        or not receipt["main_advanced"]
        or receipt["reconciliation_required"]
        or receipt["resource_copy_status"] != "applied"
        or receipt["resource_registration_status"] != "registered"
        or receipt["main_registration_status"] != "registered"
        or len(receipt["promoted_resource_asset_ids"])
        != len(receipt["selected_roles"])
        or receipt["main_version_id"] is None
        or receipt["main_media_id"] is None
        or any(
            receipt[field] is None
            for field in (
                "resource_copy_manifest_fingerprint",
                "resource_copy_commit_fingerprint",
                "resource_registration_manifest_fingerprint",
                "resource_registration_commit_fingerprint",
                "main_registration_manifest_fingerprint",
                "main_registration_commit_fingerprint",
            )
        )
    ):
        raise ValueError("applied promotion receipt lacks complete evidence")
    if status == "partial_failed" and (
        not receipt["dispatch_authorized"]
        or receipt["applied"]
        or receipt["main_advanced"]
        or not receipt["reconciliation_required"]
        or receipt["assent_record_id"] is None
        or receipt["assent_status"] is None
        or not receipt["reason_code"]
        or all(
            receipt[f"{stage}_status"] == "not_started" for stage, _ in _STAGES
        )
    ):
        raise ValueError("partial promotion receipt is contradictory")
    if receipt["replayed"] and (
        receipt["action"] != "replay" or status != "applied"
    ):
        raise ValueError("replayed promotion receipt is contradictory")


def _refuse(
    action: str,
    workflow: Mapping[str, Any],
    reason_code: str,
    *,
    status: Optional[str] = None,
) -> dict[str, Any]:
    return _build_receipt(
        action,
        workflow,
        status=status or _REFUSAL_STATUS.get(reason_code, "failed"),
        reason_code=reason_code,
    )


def _fingerprint_refusal(
    action: str,
    workflow: Mapping[str, Any],
    expected_proposal_fingerprint: str,
) -> Optional[dict[str, Any]]:
    if workflow["proposal_fingerprint"] != expected_proposal_fingerprint:
        return _refuse(
            action,
            workflow,
            REASON_PROPOSAL_CHANGED,
            status=_terminal_status(workflow, REASON_PROPOSAL_CHANGED),
        )
    return None


__all__ = [
    "AssentGateway",
    "EditorialWorkspacePromotionWorkflowAPI",
    "EditorialWorkspacePromotionWorkflowError",
    "InMemoryAssentGateway",
    "InMemoryEditorialWorkspacePromotionWorkflowStore",
    "MAIN_PLAN_OPERATION",
    "MAIN_REGISTER_TOOL",
    "PROMOTE_TOOL",
    "PROPOSAL_KIND",
    "RECEIPT_KIND",
    "RESOURCE_PLAN_OPERATION",
    "RESOURCE_REGISTER_TOOL",
    "SessionFactoryAssentGateway",
    "SessionFactoryEditorialWorkspacePromotionWorkflowStore",
    "VALIDATE_OPERATION",
    "WORKFLOW_KIND",
    "main_registration_plan_arguments",
    "make_editorial_workspace_promotion_workflow_api",
    "promotion_commit_tail",
    "promotion_discovery_arguments",
    "promotion_operator_sequence",
]
