"""forge-bridge #261 / Pipeline Phase 160 — paired render + workfile promotion.

One durable product workflow that governs FOUR host/catalog mutations under a
single AssentRecord: the physical render/OpenClip copy, the promoted-resource
catalog registration, the promotion of the EXACT rendered-from workfile (a
Flame Batch package: ``.batch`` file plus extensionless sidecar directory are
one identity), and the lineage edge binding the promoted main render Version to
the promoted main workfile Version.

It exposes the same four async transitions as its #244 sibling — ``propose``,
``ratify_apply``, ``status``, ``replay`` — and returns exactly one closed,
path-free ``bridge.paired_promotion.workflow_receipt`` mapping for every
successful transition and every post-propose refusal. A failure before a
durable proposal exists raises ``PairedPromotionWorkflowError``, which carries
a stable ``.code``.

Boundary discipline: Bridge owns graph composition, the AssentRecord lifecycle,
ratification, verify-before-apply commit, durable workflow state, status, and
replay. Pipeline owns all four operation contracts, path resolution, catalog
semantics, package identity, next-main allocation, and fresh proof.

Composition. Bridge — not the Shell — constructs the nine-node graph::

    forge_promote_shot_resource_stream          (discover)
      -> commit
      -> pipeline.shot_resource.stream_promotion.validate
      -> pipeline.shot_resource.stream_promotion.registration_plan
      -> commit
      -> forge_promote_workfile_version         (discover)
      -> commit
      -> forge_bind_promoted_workfile_lineage   (discover)
      -> commit

What is genuinely unlike #244:

1. **The lineage node cannot be discovered at propose.** Pipeline's
   ``resolve_promoted_workfile_lineage_plan`` resolves and cross-checks all
   FOUR Version authorities, two of which (main render, main workfile) do not
   exist until stages 2 and 3 commit. So the assent-gated remainder is executed
   as TWO graph runs under the SAME ratified record: the pair run, then a
   lineage discovery Bridge verifies against the exact committed IDs, then the
   lineage commit run. Discovery is ``mutation_safe`` and reaches the executor
   surface; the commit is the only thing the assent gates.

2. **Bridge hands the lineage node the exact committed identities.** The four
   Version IDs are read from durable stage evidence — never reconstructed from
   labels, numbers, or paths — and a discovered lineage manifest that does not
   name exactly those four identities is refused BEFORE the commit dispatches.

3. **Four stages, four commit fingerprints, four stage statuses.** ``applied`` /
   ``main_advanced`` require all of resource copy, resource registration,
   workfile promotion, and lineage binding to be trusted. Any failure after an
   earlier commit stays ``partial_failed`` + ``reconciliation_required``, and
   the AssentRecord stays *ratified* so replay forward-completes under the same
   authority. A completed stage is never re-composed: the durable per-stage
   status is the resume cursor, and upstream evidence a skipped stage would
   have produced is supplied from its persisted closed projection.

Privacy. ``promotion_plan``, ``promotion_callable_intent`` and
``workfile_callable_intent`` are private backend-to-Bridge authority carrying
absolute paths. They are persisted for verification and replay but never reach
a receipt, a log line, or an error string. No path, plan body, callable intent,
manifest body, resolved plan, graph, native result, or exception detail may
occur in a receipt.

ponytail: this module carries its own ``AssentGateway`` copy, matching the
precedent set by #241/#242/#244 — ``workflow_core`` holds shared *mechanism*,
and an assent seam shared across workflow contracts would let one workflow's
lifecycle silently govern another's.
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

PROPOSAL_KIND = "pipeline.paired_promotion.workflow_proposal"
PROPOSAL_SCHEMA_VERSION = 1
RECEIPT_KIND = "bridge.paired_promotion.workflow_receipt"
RECEIPT_SCHEMA_VERSION = 1

# Durable row discriminator inside the shared orch_workflow_record family
# (migration 0016 — no new migration is needed for a new kind).
WORKFLOW_KIND = "bridge.paired_promotion.workflow"

PROMOTE_TOOL = "forge_promote_shot_resource_stream"
RESOURCE_REGISTER_TOOL = "forge_register_shot_resource_promotion"
WORKFILE_PROMOTE_TOOL = "forge_promote_workfile_version"
LINEAGE_BIND_TOOL = "forge_bind_promoted_workfile_lineage"

PROMOTION_CALLABLE_OPERATION_TYPE = (
    "pipeline.shot_resource.stream_promotion.callable"
)
# forge_core/workfile/callable_contract.py (Pipeline @ 6f0c7075)
WORKFILE_CALLABLE_OPERATION_TYPE = "pipeline.workfile.stream_promotion.callable"
LINEAGE_CALLABLE_OPERATION_TYPE = "pipeline.workfile.promoted_lineage.callable"

VALIDATE_OPERATION = "pipeline.shot_resource.stream_promotion.validate"
RESOURCE_PLAN_OPERATION = (
    "pipeline.shot_resource.stream_promotion.registration_plan"
)

PROMOTE_STATE_OWNER = "peer_owned"
# The workfile promotion copies a package on the peer's filesystem; the lineage
# binding only creates a Bridge relationship and rewrites Bridge metadata.
WORKFILE_STATE_OWNER = "peer_owned"
LINEAGE_STATE_OWNER = "bridge"

# --------------------------------------------------------------------------- #
# Stable, path-free refusal codes
# --------------------------------------------------------------------------- #
REASON_PROPOSAL_INVALID = "paired_promotion_workflow_proposal_invalid"
REASON_PROPOSAL_NOT_FOUND = "paired_promotion_workflow_proposal_not_found"
REASON_PROPOSAL_CHANGED = "paired_promotion_workflow_proposal_changed"
REASON_CALLABLE_UNAVAILABLE = "paired_promotion_workflow_callable_unavailable"
REASON_MANIFEST_INVALID = "paired_promotion_workflow_manifest_invalid"
REASON_MANIFEST_DRIFT = "paired_promotion_workflow_manifest_drift"
REASON_ASSENT_INVALID = "paired_promotion_workflow_assent_invalid"
REASON_RESOURCE_COPY_FAILED = "paired_promotion_workflow_resource_copy_failed"
REASON_RESOURCE_REGISTRATION_FAILED = (
    "paired_promotion_workflow_resource_registration_failed"
)
REASON_WORKFILE_PROMOTION_FAILED = (
    "paired_promotion_workflow_workfile_promotion_failed"
)
REASON_LINEAGE_BINDING_FAILED = (
    "paired_promotion_workflow_lineage_binding_failed"
)
REASON_PARTIAL_RECONCILIATION_REQUIRED = (
    "paired_promotion_workflow_partial_reconciliation_required"
)
REASON_REPLAY_UNAVAILABLE = "paired_promotion_workflow_replay_unavailable"
REASON_REPLAY_DRIFT = "paired_promotion_workflow_replay_drift"

# A post-propose refusal is "failed" (something was attempted and did not
# stand) or "unavailable" (the transition was never on offer). A refusal over a
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
    REASON_WORKFILE_PROMOTION_FAILED: "failed",
    REASON_LINEAGE_BINDING_FAILED: "failed",
    REASON_PARTIAL_RECONCILIATION_REQUIRED: "partial_failed",
    REASON_REPLAY_UNAVAILABLE: "unavailable",
    REASON_REPLAY_DRIFT: "failed",
}

_TRUSTED_STATUSES = frozenset({"proposed", "applied"})
_REVIEW_STATUSES = frozenset({"partial_failed", "unavailable"})

# --------------------------------------------------------------------------- #
# Closed field sets
# --------------------------------------------------------------------------- #
_PROPOSAL_FIELDS = frozenset({
    "kind",
    "schema_version",
    "project_id",
    "requested_by",
    "promotion_preview_id",
    "promotion_preview_fingerprint",
    "promotion_authority_fingerprint",
    "source_render_version_id",
    "source_render_media_id",
    "source_workfile_version_id",
    "selected_roles",
    "published_resource_asset_ids",
    "promotion_plan_fingerprint",
    "promotion_callable_intent_fingerprint",
    "workfile_callable_intent_fingerprint",
    "promotion_plan",
    "promotion_callable_intent",
    "workfile_callable_intent",
    "fingerprint",
})
_PROPOSAL_TEXT_FIELDS = (
    "project_id",
    "requested_by",
    "promotion_preview_id",
    "source_render_version_id",
    "source_render_media_id",
    "source_workfile_version_id",
)
_PROPOSAL_SHA256_FIELDS = (
    "promotion_preview_fingerprint",
    "promotion_authority_fingerprint",
    "promotion_plan_fingerprint",
    "promotion_callable_intent_fingerprint",
    "workfile_callable_intent_fingerprint",
    "fingerprint",
)
_PROPOSAL_ID_LIST_FIELDS = ("selected_roles", "published_resource_asset_ids")
# Each nested private authority and the field carrying its own fingerprint.
_PROPOSAL_NESTED_FIELDS = (
    ("promotion_plan", "promotion_plan_fingerprint"),
    ("promotion_callable_intent", "promotion_callable_intent_fingerprint"),
    ("workfile_callable_intent", "workfile_callable_intent_fingerprint"),
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

# Ordered receipt keys. ``fingerprint`` is canonical SHA-256 over every receipt
# field EXCEPT kind, schema_version, and fingerprint.
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
    "source_render_version_id",
    "source_render_media_id",
    "source_workfile_version_id",
    "selected_roles",
    "published_resource_asset_ids",
    "promoted_resource_asset_ids",
    "main_render_version_id",
    "main_render_media_id",
    "main_workfile_version_id",
    "main_workfile_media_id",
    "lineage_relationship_id",
    "assent_record_id",
    "assent_status",
    "resource_copy_manifest_fingerprint",
    "resource_copy_commit_fingerprint",
    "resource_copy_status",
    "resource_registration_manifest_fingerprint",
    "resource_registration_commit_fingerprint",
    "resource_registration_status",
    "workfile_promotion_manifest_fingerprint",
    "workfile_promotion_commit_fingerprint",
    "workfile_promotion_status",
    "lineage_binding_manifest_fingerprint",
    "lineage_binding_commit_fingerprint",
    "lineage_binding_status",
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
# The stage values are NOT interchangeable: the physical resource copy is
# "applied", catalog registration is "registered", the workfile package
# promotion is "promoted", and the lineage edge is "bound".
_STAGE_STATUSES = frozenset({
    "not_started",
    "applied",
    "registered",
    "promoted",
    "bound",
    "failed",
})

# The four stages, in graph order: (durable key, complete value).
_STAGES: tuple[tuple[str, str], ...] = (
    ("resource_copy", "applied"),
    ("resource_registration", "registered"),
    ("workfile_promotion", "promoted"),
    ("lineage_binding", "bound"),
)

_STAGE_REASONS: dict[str, str] = {
    "resource_copy": REASON_RESOURCE_COPY_FAILED,
    "resource_registration": REASON_RESOURCE_REGISTRATION_FAILED,
    "workfile_promotion": REASON_WORKFILE_PROMOTION_FAILED,
    "lineage_binding": REASON_LINEAGE_BINDING_FAILED,
}


class PairedPromotionWorkflowError(Exception):
    """Raised only when a transition cannot ground a durable proposal.

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
class InMemoryPairedPromotionWorkflowStore(InMemoryWorkflowStore):
    """Process-local store — unit tests and stock installs without Postgres."""

    def __init__(self) -> None:
        super().__init__(authority_field="promotion_authority_fingerprint")


class SessionFactoryPairedPromotionWorkflowStore(SessionFactoryWorkflowStore):
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
# Graph composition
# --------------------------------------------------------------------------- #
def callable_discovery_arguments(
    callable_intent: Mapping[str, Any],
) -> dict[str, Any]:
    """A discovery node's arguments: the retained intent plus mode=discover.

    Bridge must not rebuild or widen a retained callable intent.
    """
    return {
        "params": callable_intent["params"],
        "bridge_asset_ids": callable_intent["bridge_asset_ids"],
        "idempotency_key": callable_intent["idempotency_key"],
        "project_id": callable_intent["project_id"],
        "requested_by": callable_intent["requested_by"],
        "mode": "discover",
    }


def lineage_discovery_arguments(
    proposal: Mapping[str, Any],
    *,
    main_render_version_id: Optional[str],
    main_workfile_version_id: Optional[str],
) -> dict[str, Any]:
    """Arguments for the lineage discovery node.

    The four Version identities are the EXACT committed ones — two retained
    from the proposal, two read from durable commit evidence. Nothing here is
    reconstructed from a label, a version number, or a path.

    Param names are Pipeline's, from
    ``forge_core/workfile/promoted_lineage.py:137-144``.
    """
    intent = proposal["promotion_callable_intent"]
    params = {
        "source_render_version_id": proposal["source_render_version_id"],
        "main_render_version_id": main_render_version_id,
        "source_workfile_version_id": proposal["source_workfile_version_id"],
        "main_workfile_version_id": main_workfile_version_id,
    }
    return {
        "params": params,
        "bridge_asset_ids": sorted(
            {value for value in params.values() if isinstance(value, str)}
        ),
        "idempotency_key": (
            f"{intent['idempotency_key']}:promoted-workfile-lineage"
        ),
        "project_id": proposal["project_id"],
        "requested_by": proposal["requested_by"],
        "mode": "discover",
    }


def paired_promotion_operator_sequence(
    proposal: Mapping[str, Any],
    *,
    main_render_version_id: Optional[str] = None,
    main_workfile_version_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """The exact nine-node graph, composed by Bridge.

    The Shell never submits it. ``propose`` executes the two discovery nodes
    only; the commit-bearing remainder is the assent-gated tail, executed
    (whole or resumed) by ``ratify_apply`` / ``replay``. The lineage node's two
    main identities are unknown until stages 2 and 3 commit, which is exactly
    why the tail runs as two graph runs under one ratified record.
    """
    return [
        _discover_step(
            PROMOTE_TOOL,
            callable_discovery_arguments(proposal["promotion_callable_intent"]),
            "promotion:held",
        ),
        _commit_step("promotion"),
        _validate_step(),
        _resource_plan_step(),
        _commit_step("registration"),
        _discover_step(
            WORKFILE_PROMOTE_TOOL,
            callable_discovery_arguments(proposal["workfile_callable_intent"]),
            "workfile:held",
        ),
        _commit_step("workfile"),
        _discover_step(
            LINEAGE_BIND_TOOL,
            lineage_discovery_arguments(
                proposal,
                main_render_version_id=main_render_version_id,
                main_workfile_version_id=main_workfile_version_id,
            ),
            "lineage:held",
        ),
        _commit_step("lineage"),
    ]


def _discover_step(
    operator_id: str, arguments: Mapping[str, Any], output_artifact_id: str
) -> dict[str, Any]:
    return {
        "operator_id": operator_id,
        "arguments": dict(arguments),
        "inputs": [],
        "output_artifact_id": output_artifact_id,
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
        step["inputs"] = [
            _input("promotion:commit", "commit_result", "promotion_commit")
        ]
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
        # A manifest Bridge already discovered and verified, replayed under
        # ratified assent — CommitBoundary re-verifies it against fresh state.
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


class PairedPromotionWorkflowAPI:
    """Closed paired render + workfile promotion workflow."""

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
        """Discover both physical promotions only. Never verifies or applies."""
        normalized = _validate_proposal(proposal)
        proposal_fingerprint = normalized["fingerprint"]
        proposal_id = workflow_identifier("ppr_", proposal_fingerprint)
        workflow_id = workflow_identifier("pprf_", proposal_fingerprint)

        existing = await self._store.get_by_proposal_id(proposal_id)
        if existing is not None:
            # Exact duplicate: the ORIGINAL durable proposal receipt.
            return _build_receipt("propose", existing, status="proposed")

        collision = await self._store.get_by_authority_fingerprint(
            normalized["promotion_authority_fingerprint"]
        )
        if collision is not None:
            # The same authority under a different proposal fails closed.
            raise PairedPromotionWorkflowError(
                REASON_PROPOSAL_INVALID,
                "promotion authority is already bound to a different proposal",
            )

        composition = paired_promotion_operator_sequence(normalized)
        resource_manifest = await self._discover_or_raise(composition[0])
        _verify_promotion_manifest(resource_manifest, normalized)
        workfile_manifest = await self._discover_or_raise(composition[5])
        _verify_workfile_manifest(workfile_manifest, normalized)

        preview = await self._preview(
            held_manifest=resource_manifest,
            chain_steps=_chain_steps(),
            display="Phase 160 paired render and workfile promotion",
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
            "source_render_version_id": normalized["source_render_version_id"],
            "source_render_media_id": normalized["source_render_media_id"],
            "source_workfile_version_id": normalized[
                "source_workfile_version_id"
            ],
            "selected_roles": list(normalized["selected_roles"]),
            "published_resource_asset_ids": list(
                normalized["published_resource_asset_ids"]
            ),
            "promoted_resource_asset_ids": [],
            "main_render_version_id": None,
            "main_render_media_id": None,
            "main_workfile_version_id": None,
            "main_workfile_media_id": None,
            "lineage_relationship_id": None,
            "graph_node_sequence": [
                str(step["operator_id"]) for step in composition
            ],
            "assent_graph_intent_id": preview["graph_intent_id"],
            "assent_record_id": preview["assent_record_id"],
            "assent_status": "proposed",
            # Two manifests exist at propose time; the registration manifest is
            # derived from commit evidence and the lineage manifest cannot be
            # discovered until both main identities exist.
            "resource_copy_held_manifest": resource_manifest,
            "resource_copy_manifest_fingerprint": canonical_fingerprint(
                resource_manifest
            ),
            "resource_copy_commit_fingerprint": None,
            "resource_copy_commit_output": None,
            "resource_copy_status": "not_started",
            "resource_registration_manifest_fingerprint": None,
            "resource_registration_commit_fingerprint": None,
            "resource_registration_commit_output": None,
            "resource_registration_status": "not_started",
            "workfile_promotion_held_manifest": workfile_manifest,
            "workfile_promotion_manifest_fingerprint": canonical_fingerprint(
                workfile_manifest
            ),
            "workfile_promotion_commit_fingerprint": None,
            "workfile_promotion_status": "not_started",
            "lineage_binding_manifest_fingerprint": None,
            "lineage_binding_commit_fingerprint": None,
            "lineage_binding_status": "not_started",
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
            raise PairedPromotionWorkflowError(
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
        apply.
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
        """Forward-complete the original graph idempotently.

        Uses the original proposal, graph, AssentRecord, held manifests, and
        commit identities. Creates no new proposal and no new AssentRecord, and
        cannot widen roles, resource IDs, target identities, or actor.
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
                # Replay of a completed graph performs NO mutation.
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
        held = {}
        for stage, field in (
            ("resource_copy", "resource_copy_held_manifest"),
            ("workfile_promotion", "workfile_promotion_held_manifest"),
        ):
            body = workflow.get(field)
            if not isinstance(body, Mapping) or canonical_fingerprint(
                dict(body)
            ) != workflow[f"{stage}_manifest_fingerprint"]:
                return _refuse(
                    action,
                    workflow,
                    REASON_MANIFEST_DRIFT if ratify else REASON_REPLAY_DRIFT,
                )
            held[stage] = dict(body)

        state = dict(workflow)
        patch: dict[str, Any] = {}
        reason: Optional[str] = None
        commit_reason: Optional[str] = None
        ratified = False

        # The tail runs as separate graph runs under ONE ratification. The
        # resource stages are genuinely chained (each plan node consumes the
        # prior commit), but the workfile promotion and the lineage binding are
        # physically independent — so Bridge orders them conservatively rather
        # than letting an independent held commit apply after an upstream stage
        # already failed.
        for builder in (_resource_tail, _workfile_tail):
            if reason is not None:
                break
            sequence, stage_nodes = builder(state, held=held)
            if not sequence:
                continue
            outcome = await self._execute_fn(
                graph_intent_id=state["assent_graph_intent_id"],
                requested_by=requested_by,
                operator_sequence=sequence,
                ratify=ratify and not ratified,
            )
            if outcome.get("outcome") != "ratified":
                return await self._settle_refusal(
                    action,
                    state,
                    requested_by=requested_by,
                    assent_status=outcome.get("assent_status"),
                    reason=outcome.get("reason_code") or REASON_ASSENT_INVALID,
                )
            ratified = True
            stage_patch, reason, commit_reason = _apply_stage_results(
                outcome.get("results") or {}, stage_nodes
            )
            patch.update(stage_patch)
            state.update(stage_patch)

        if reason is None and state["lineage_binding_status"] != "bound":
            lineage_patch, reason, commit_reason = await self._bind_lineage(
                action,
                state,
                requested_by=requested_by,
                ratify=ratify and not ratified,
            )
            if lineage_patch is None:
                return await self._settle_refusal(
                    action,
                    state,
                    requested_by=requested_by,
                    assent_status=state.get("assent_status"),
                    reason=reason or REASON_ASSENT_INVALID,
                )
            patch.update(lineage_patch)
            state.update(lineage_patch)

        patch.update(_disposition(state, reason, commit_reason))
        patch.update(_stamp(workflow, action, requested_by, self._clock()))
        if action == "replay" and patch["status"] == "applied":
            patch["replayed"] = True

        # The AssentRecord settles ONLY on a terminal disposition. A partial
        # failure leaves it ratified so replay can forward-complete under the
        # SAME authority without minting a new record.
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

    async def _settle_refusal(
        self,
        action: str,
        state: Mapping[str, Any],
        *,
        requested_by: str,
        assent_status: Optional[str],
        reason: str,
    ) -> dict[str, Any]:
        """Record an assent-rail refusal without touching stage evidence."""
        patch = _stamp(state, action, requested_by, self._clock())
        patch["assent_status"] = assent_status
        patch["reason_code"] = reason
        patch["status"] = _terminal_status(state, reason)
        stored = await self._store.update(state["proposal_id"], patch)
        return _refuse(action, stored, reason, status=patch["status"])

    async def _bind_lineage(
        self,
        action: str,
        state: Mapping[str, Any],
        *,
        requested_by: str,
        ratify: bool,
    ) -> tuple[Optional[dict[str, Any]], Optional[str], Optional[str]]:
        """Discover, verify, and commit the lineage edge.

        Returns ``(patch, reason, commit_reason)``. ``patch is None`` means the
        assent rail itself refused and the caller must settle the refusal.
        """
        main_render = state.get("main_render_version_id")
        main_workfile = state.get("main_workfile_version_id")
        if not main_render or not main_workfile:
            # Both target Version identities must exist before the lineage node
            # is composed at all — never a reconstructed label or path.
            return {}, REASON_LINEAGE_BINDING_FAILED, "MAIN_IDENTITY_MISSING"

        step = _discover_step(
            LINEAGE_BIND_TOOL,
            lineage_discovery_arguments(
                state["proposal"],
                main_render_version_id=main_render,
                main_workfile_version_id=main_workfile,
            ),
            "lineage:held",
        )
        try:
            manifest = await self._discover([step])
        except _DiscoveryUnavailable:
            return {}, REASON_CALLABLE_UNAVAILABLE, "LINEAGE_UNAVAILABLE"
        except _DiscoveryDrift:
            return {}, REASON_MANIFEST_INVALID, "LINEAGE_DISCOVERY_UNTRUSTED"
        try:
            _verify_lineage_manifest(
                manifest,
                state["proposal"],
                main_render_version_id=main_render,
                main_workfile_version_id=main_workfile,
            )
        except PairedPromotionWorkflowError as exc:
            # Fail closed BEFORE the lineage commit dispatches.
            return {}, exc.code, "LINEAGE_MANIFEST_MISMATCH"

        patch: dict[str, Any] = {
            "lineage_binding_manifest_fingerprint": canonical_fingerprint(
                manifest
            )
        }
        outcome = await self._execute_fn(
            graph_intent_id=state["assent_graph_intent_id"],
            requested_by=requested_by,
            operator_sequence=[_commit_step("lineage", held=manifest)],
            ratify=ratify,
        )
        if outcome.get("outcome") != "ratified":
            return None, (
                outcome.get("reason_code") or REASON_ASSENT_INVALID
            ), None
        stage_patch, reason, commit_reason = _apply_stage_results(
            outcome.get("results") or {},
            {"lineage_binding": {"commit": "commit#0", "plan": None}},
        )
        patch.update(stage_patch)
        return patch, reason, commit_reason

    async def _discover_or_raise(
        self, step: Mapping[str, Any]
    ) -> dict[str, Any]:
        try:
            return await self._discover([step])
        except _DiscoveryUnavailable as exc:
            raise PairedPromotionWorkflowError(
                REASON_CALLABLE_UNAVAILABLE,
                "promotion callable did not answer",
            ) from exc
        except _DiscoveryDrift as exc:
            raise PairedPromotionWorkflowError(
                REASON_MANIFEST_INVALID,
                "promotion discovery was not trusted",
            ) from exc

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
        except PairedPromotionWorkflowError:
            raise
        except Exception as exc:  # noqa: BLE001 - persistence failure
            raise PairedPromotionWorkflowError(
                REASON_MANIFEST_INVALID,
                "preview did not persist a durable mutation manifest",
            ) from exc

    async def _load_or_raise(self, proposal_id: str) -> dict[str, Any]:
        workflow = await self._store.get_by_proposal_id(proposal_id)
        if workflow is None:
            raise PairedPromotionWorkflowError(
                REASON_PROPOSAL_NOT_FOUND,
                "no workflow for the supplied proposal id",
            )
        return workflow

    async def _reload_or_raise(self, proposal_id: str) -> dict[str, Any]:
        workflow = await self._guard.reload(proposal_id)
        if workflow is None:
            raise PairedPromotionWorkflowError(
                REASON_PROPOSAL_NOT_FOUND, "workflow disappeared"
            )
        return workflow


# --------------------------------------------------------------------------- #
# Stage machine
# --------------------------------------------------------------------------- #
def _resource_tail(
    workflow: Mapping[str, Any], *, held: Mapping[str, Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Optional[str]]]]:
    """Build the resume sequence for the two chained resource stages.

    The resume cursor is the durable per-stage status: a stage that already
    completed is NEVER re-composed, so a replay cannot re-copy bytes or mint a
    second catalog identity. Upstream evidence a skipped stage would have
    produced is supplied from its persisted closed projection instead.
    """
    copy_done = workflow["resource_copy_status"] == "applied"
    registration_done = (
        workflow["resource_registration_status"] == "registered"
    )

    steps: list[dict[str, Any]] = []
    stage_nodes: dict[str, dict[str, Optional[str]]] = {}

    def add(step: dict[str, Any]) -> str:
        node_id = f"{step['operator_id']}#{len(steps)}"
        steps.append(step)
        return node_id

    if not copy_done:
        # Stage 1's held manifest was persisted at propose, so its fingerprint
        # is already durable; the node map records no plan node.
        commit_node = add(_commit_step("promotion", held=held["resource_copy"]))
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
    return steps, stage_nodes


def _workfile_tail(
    workflow: Mapping[str, Any], *, held: Mapping[str, Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Optional[str]]]]:
    """The exact-workfile promotion commit, or nothing if already promoted.

    Its held manifest was discovered and fingerprinted at propose, so a resumed
    run re-verifies the SAME allocation rather than reallocating a main number.
    """
    if workflow["workfile_promotion_status"] == "promoted":
        return [], {}
    return (
        [_commit_step("workfile", held=held["workfile_promotion"])],
        {"workfile_promotion": {"commit": "commit#0", "plan": None}},
    )


def _apply_stage_results(
    results: Mapping[str, Any],
    stage_nodes: Mapping[str, Mapping[str, Optional[str]]],
) -> tuple[dict[str, Any], Optional[str], Optional[str]]:
    """Read per-stage evidence out of one executed graph run."""
    patch: dict[str, Any] = {}
    reason: Optional[str] = None
    commit_reason: Optional[str] = None

    for stage, complete_value in _STAGES:
        nodes = stage_nodes.get(stage)
        if nodes is None:
            continue  # not part of this run
        result = results.get(nodes["commit"])
        evidence = _commit_evidence(result)
        if evidence is not None and not _stage_complete(stage, evidence):
            # The host applied but did not report complete evidence for this
            # stage. That is dispatched-and-incomplete, never complete.
            patch[f"{stage}_status"] = "failed"
            reason = _STAGE_REASONS[stage]
            commit_reason = "STAGE_EVIDENCE_INCOMPLETE"
            break
        if evidence is None:
            code = _reason_code_of(result)
            if _stage_dispatched(result):
                patch[f"{stage}_status"] = "failed"
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
        patch.update(_stage_identities(stage, evidence))
    return patch, reason, commit_reason


def _stage_identities(
    stage: str, evidence: Mapping[str, Any]
) -> dict[str, Any]:
    """The exact committed identities a completed stage contributes."""
    apply_result = evidence["apply_result"]
    if stage == "resource_copy":
        return {"resource_copy_commit_output": evidence["output"]}
    if stage == "resource_registration":
        return {
            "resource_registration_commit_output": evidence["output"],
            "promoted_resource_asset_ids": _created_asset_ids(apply_result),
            "main_render_version_id": _one(_version_asset_ids(apply_result)),
            "main_render_media_id": _one(_media_asset_ids(apply_result)),
        }
    if stage == "workfile_promotion":
        promotion_apply = _mapping(apply_result.get("promotion_apply"))
        return {
            "main_workfile_version_id": _text_or_none(
                apply_result.get("target_version_id")
            ),
            # NB: Pipeline's WorkfileOp.promote_stream omits ``media_id`` on the
            # idempotent-replay branch (forge_core/workfile/ops.py:1259-1272 vs
            # :1437-1453), so the promoted workfile Media is best-effort.
            "main_workfile_media_id": _text_or_none(
                promotion_apply.get("media_id")
            ),
        }
    if stage == "lineage_binding":
        lineage_apply = _mapping(apply_result.get("lineage_apply"))
        return {
            "lineage_relationship_id": _text_or_none(
                lineage_apply.get("relationship_id")
            )
        }
    return {}


def _disposition(
    state: Mapping[str, Any],
    reason: Optional[str],
    commit_reason: Optional[str],
) -> dict[str, Any]:
    """Compute the terminal disposition from merged durable stage state."""
    patch: dict[str, Any] = {}
    complete = all(
        state[f"{stage}_status"] == value for stage, value in _STAGES
    )
    if complete and reason is None:
        # ``applied`` requires resource, workfile, AND lineage evidence — a
        # complete stage table alone never carries the claim.
        missing = [
            field
            for field in (
                "main_render_version_id",
                "main_render_media_id",
                "main_workfile_version_id",
                "lineage_relationship_id",
            )
            if not state.get(field)
        ]
        if not missing:
            patch["status"] = "applied"
            patch["reason_code"] = None
            return patch
        patch["lineage_binding_status"] = "failed"
        patch["status"] = "partial_failed"
        patch["reason_code"] = REASON_LINEAGE_BINDING_FAILED
        patch["commit_reason_code"] = "PROMOTED_IDENTITY_INCOMPLETE"
        return patch

    started = any(
        state[f"{stage}_status"] != "not_started" for stage, _ in _STAGES
    )
    patch["reason_code"] = reason or REASON_PARTIAL_RECONCILIATION_REQUIRED
    patch["commit_reason_code"] = commit_reason
    patch["status"] = "partial_failed" if started else "failed"
    return patch


def _commit_evidence(result: Any) -> Optional[dict[str, Any]]:
    """Closed evidence for one successfully applied commit node."""
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
        "apply_result": dict(apply_result),
    }


def _stage_complete(stage: str, evidence: Mapping[str, Any]) -> bool:
    """Does this applied commit actually PROVE its stage completed?

    An applied commit is necessary but not sufficient: each stage must also
    report its own completion, which is exactly where a catalog, package, or
    lineage interruption shows up.
    """
    apply_result = evidence["apply_result"]
    if stage == "resource_registration":
        # ponytail ceiling: the paired graph binds ONE main render Version to
        # ONE main workfile Version, so exactly one registered Version and one
        # registered Media is the contract. Anything else is ambiguous and
        # fails closed toward reconciliation rather than guessing which
        # identity the lineage node should receive.
        return (
            apply_result.get("catalog_registration_status") == "registered"
            and len(_version_asset_ids(apply_result)) == 1
            and len(_media_asset_ids(apply_result)) == 1
            and bool(_created_asset_ids(apply_result))
        )
    if stage == "workfile_promotion":
        promotion_apply = apply_result.get("promotion_apply")
        return (
            apply_result.get("ok") is True
            and _text_or_none(apply_result.get("target_version_id")) is not None
            and isinstance(promotion_apply, Mapping)
            and promotion_apply.get("status") == "promoted"
            and promotion_apply.get("trust_status") == "trusted"
        )
    if stage == "lineage_binding":
        lineage_apply = apply_result.get("lineage_apply")
        return (
            apply_result.get("ok") is True
            and isinstance(lineage_apply, Mapping)
            and lineage_apply.get("status") == "bound"
            and lineage_apply.get("trust_status") == "trusted"
            and _text_or_none(lineage_apply.get("relationship_id")) is not None
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
        ids = (
            nested.get("created_asset_ids")
            if isinstance(nested, Mapping)
            else None
        )
    if not isinstance(ids, list):
        return []
    return sorted({str(item) for item in ids if str(item).strip()})


def _version_asset_ids(apply_result: Mapping[str, Any]) -> list[str]:
    """The registered Version identities.

    Derived from Pipeline's ``publish_register`` payload
    (``forge_core/operations/shot_resource_publish_registration_plan.py``
    :334-341), which is the only place the registration result separates
    Versions from Media.
    """
    return _id_list(_mapping(apply_result.get("publish_register")), "version")


def _media_asset_ids(apply_result: Mapping[str, Any]) -> list[str]:
    return _id_list(_mapping(apply_result.get("publish_register")), "media")


def _id_list(register: Mapping[str, Any], kind: str) -> list[str]:
    values = register.get(f"{kind}_asset_ids")
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if str(item).strip()]


def _one(values: Sequence[str]) -> Optional[str]:
    return values[0] if len(values) == 1 else None


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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
    return _STAGE_REASONS[stage]


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


def _chain_steps() -> list[str]:
    """Operator-legible chain text for the ONE AssentRecord over four commits."""
    return [
        "promote the selected artist render and OpenClip to main",
        "commit",
        "validate promoted shot resources",
        "plan promoted-resource catalog registration",
        "commit",
        "promote the exact rendered-from workfile to main",
        "commit",
        "bind the promoted main render to the promoted main workfile",
        "commit",
    ]


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #
def make_paired_promotion_workflow_api(
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
) -> PairedPromotionWorkflowAPI:
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
        store = SessionFactoryPairedPromotionWorkflowStore(session_factory)
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
    return PairedPromotionWorkflowAPI(
        store=store,
        discover_fn=discover_fn,
        preview_fn=preview_fn,
        execute_fn=execute_fn,
        settle_fn=settle_fn,
        clock=clock,
    )


def _default_discover_fn(mcp: Any) -> DiscoverFn:
    """Run a discovery node through the admitted graph dispatch surface."""

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
                # The ORIGINAL record, reloaded and never re-ratified. Both the
                # replay rail and the second run of one ratify_apply take this
                # path, so the four commits share ONE ratification.
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
# Proposal validation
# --------------------------------------------------------------------------- #
def _invalid(message: str) -> PairedPromotionWorkflowError:
    return PairedPromotionWorkflowError(REASON_PROPOSAL_INVALID, message)


def _validate_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on any unknown or missing field, and on every drift."""
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
    if proposal["source_render_version_id"] == (
        proposal["source_workfile_version_id"]
    ):
        raise _invalid("render and workfile sources must be distinct Versions")

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

    _validate_callable_intent(
        normalized,
        "promotion_callable_intent",
        tool=PROMOTE_TOOL,
        operation_type=PROMOTION_CALLABLE_OPERATION_TYPE,
    )
    _validate_callable_intent(
        normalized,
        "workfile_callable_intent",
        tool=WORKFILE_PROMOTE_TOOL,
        operation_type=WORKFILE_CALLABLE_OPERATION_TYPE,
    )
    _validate_resource_intent(normalized)
    _validate_workfile_intent(normalized)
    return normalized


def _validate_callable_intent(
    proposal: Mapping[str, Any],
    field: str,
    *,
    tool: str,
    operation_type: str,
) -> None:
    intent = proposal[field]
    extra = set(intent.keys()) - _CALLABLE_INTENT_FIELDS
    if extra:
        raise _invalid(f"{field} has unknown fields: {sorted(extra)}")
    missing = _CALLABLE_INTENT_FIELDS - set(intent.keys())
    if missing:
        raise _invalid(f"{field} is missing fields: {sorted(missing)}")
    if intent["tool"] != tool:
        raise _invalid(f"{field} tool is not the expected callable")
    if intent["operation_type"] != operation_type:
        raise _invalid(f"{field} operation_type is not recognized")
    if intent["project_id"] != proposal["project_id"]:
        raise _invalid(f"{field} project differs from the proposal")
    if not isinstance(intent["params"], Mapping):
        raise _invalid(f"{field} params must be a mapping")
    idempotency_key = intent["idempotency_key"]
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise _invalid(f"{field} idempotency_key must be non-empty")
    if (
        not isinstance(intent["requested_by"], str)
        or not intent["requested_by"].strip()
    ):
        # NB: NOT required to equal the proposal actor. The retained intent is
        # frozen at preview compile time; the Shell names the ratifying actor.
        raise _invalid(f"{field} requested_by must be non-empty")
    if not isinstance(intent["bridge_asset_ids"], list):
        raise _invalid(f"{field} bridge_asset_ids must be a list")


def _validate_resource_intent(proposal: Mapping[str, Any]) -> None:
    intent = proposal["promotion_callable_intent"]
    missing_assets = [
        asset_id
        for asset_id in proposal["published_resource_asset_ids"]
        if asset_id not in intent["bridge_asset_ids"]
    ]
    if missing_assets:
        raise _invalid(
            "promotion_callable_intent does not carry every published resource"
        )


def _validate_workfile_intent(proposal: Mapping[str, Any]) -> None:
    """Cross-check the retained workfile intent against the public identities.

    ponytail ceiling: the intent body is private Pipeline authority pinned by
    its own fingerprint. Bridge checks only the fields it already owns
    publicly — the exact source Version and the main target stream — which are
    the two params Pipeline's resolver treats as authority
    (``forge_core/workfile/callable_promotion.py``:158-161, :205).
    """
    params = proposal["workfile_callable_intent"]["params"]
    if params.get("source_version_id") != proposal["source_workfile_version_id"]:
        raise _invalid(
            "workfile_callable_intent does not name the selected workfile"
        )
    if params.get("target_stream") not in {None, "main"}:
        raise _invalid("workfile_callable_intent does not target main")


# --------------------------------------------------------------------------- #
# Manifest verification
# --------------------------------------------------------------------------- #
def _manifest_failure(detail: str) -> PairedPromotionWorkflowError:
    return PairedPromotionWorkflowError(REASON_MANIFEST_INVALID, detail)


def _verify_manifest_envelope(
    payload: Mapping[str, Any],
    *,
    tool: str,
    state_owner: str,
) -> Any:
    """Structural + admission proof shared by all three discovered manifests."""
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
        raise _manifest_failure(
            "discovered manifest is structurally invalid"
        ) from exc

    if payload.get("trust_status") != "trusted":
        raise _manifest_failure("discovered manifest is not trusted")
    if payload.get("originating_capability") != tool:
        raise _manifest_failure(
            "discovered manifest has the wrong originating capability"
        )
    if manifest.apply_counterpart.get("tool") != tool:
        raise _manifest_failure(
            "discovered manifest has the wrong apply counterpart"
        )
    try:
        counterpart = admit_mutation_counterpart(tool)
    except AdmissionRejected as exc:
        raise _manifest_failure("apply counterpart is not admitted") from exc
    if (
        counterpart.state_owner != state_owner
        or not counterpart.verify_before_apply
        or not counterpart.assent_required
    ):
        raise _manifest_failure(
            "apply counterpart lacks the required commit authority"
        )
    return manifest


def _manifest_identity(
    payload: Mapping[str, Any], *, operation_type: str
) -> dict[str, Any]:
    records = payload.get("resolved_plan")
    if not isinstance(records, list) or len(records) != 1:
        raise _manifest_failure("manifest does not carry one change record")
    identity = (
        records[0].get("identity") if isinstance(records[0], Mapping) else None
    )
    if not isinstance(identity, Mapping):
        raise _manifest_failure("change record carries no identity")
    if identity.get("operation_type") != operation_type:
        raise _manifest_failure("change record operation type is not recognized")
    return dict(identity)


def _verify_intent_parameters(
    payload: Mapping[str, Any], intent: Mapping[str, Any]
) -> None:
    manifest_intent = payload.get("intent_parameters")
    if not isinstance(manifest_intent, Mapping):
        raise _manifest_failure("discovered manifest carries no intent parameters")
    if manifest_intent.get("params") != dict(intent["params"]):
        raise _manifest_failure(
            "manifest intent parameters differ from the callable intent"
        )
    if manifest_intent.get("idempotency_key") != intent["idempotency_key"]:
        raise _manifest_failure(
            "manifest idempotency key differs from the callable intent"
        )


def _verify_promotion_manifest(
    payload: Mapping[str, Any], proposal: Mapping[str, Any]
) -> None:
    """Prove the discovered manifest IS this proposal's physical promotion."""
    _verify_manifest_envelope(
        payload, tool=PROMOTE_TOOL, state_owner=PROMOTE_STATE_OWNER
    )
    _verify_intent_parameters(payload, proposal["promotion_callable_intent"])
    _manifest_identity(
        payload, operation_type=PROMOTION_CALLABLE_OPERATION_TYPE
    )


def _verify_workfile_manifest(
    payload: Mapping[str, Any], proposal: Mapping[str, Any]
) -> None:
    """Prove the discovered plan promotes the EXACT rendered-from workfile.

    The identity keys are Pipeline's, from
    ``forge_core/bridge/registry.py``:975-991.
    """
    _verify_manifest_envelope(
        payload, tool=WORKFILE_PROMOTE_TOOL, state_owner=WORKFILE_STATE_OWNER
    )
    _verify_intent_parameters(payload, proposal["workfile_callable_intent"])
    identity = _manifest_identity(
        payload, operation_type=WORKFILE_CALLABLE_OPERATION_TYPE
    )
    if identity.get("source_version_id") != proposal[
        "source_workfile_version_id"
    ]:
        raise _manifest_failure(
            "workfile plan does not promote the selected source Version"
        )
    if identity.get("target_stream") != "main":
        raise _manifest_failure("workfile plan does not target main")
    if identity.get("project_id") not in {None, proposal["project_id"]}:
        raise _manifest_failure("workfile plan belongs to another project")


def _verify_lineage_manifest(
    payload: Mapping[str, Any],
    proposal: Mapping[str, Any],
    *,
    main_render_version_id: str,
    main_workfile_version_id: str,
) -> None:
    """Prove the lineage plan binds exactly the four committed identities.

    This is the check the whole two-run split exists to make: the discovered
    plan is refused BEFORE the commit node dispatches unless it names the exact
    committed main Version IDs and the exact retained artist Version IDs.

    The identity keys are Pipeline's, from
    ``forge_core/bridge/registry.py``:1137-1150.
    """
    _verify_manifest_envelope(
        payload, tool=LINEAGE_BIND_TOOL, state_owner=LINEAGE_STATE_OWNER
    )
    identity = _manifest_identity(
        payload, operation_type=LINEAGE_CALLABLE_OPERATION_TYPE
    )
    expected = {
        "project_id": proposal["project_id"],
        "source_render_version_id": proposal["source_render_version_id"],
        "main_render_version_id": main_render_version_id,
        "source_workfile_version_id": proposal["source_workfile_version_id"],
        "main_workfile_version_id": main_workfile_version_id,
    }
    for field, value in expected.items():
        if identity.get(field) != value:
            raise _manifest_failure(
                f"lineage plan {field} is not the committed identity"
            )
    if not is_sha256(identity.get("authority_fingerprint")):
        raise _manifest_failure("lineage plan carries no authority fingerprint")


# --------------------------------------------------------------------------- #
# Receipts
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

    def durable(field: str) -> Any:
        return None if proposed_view else workflow.get(field)

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
        "source_render_version_id": workflow["source_render_version_id"],
        "source_render_media_id": workflow["source_render_media_id"],
        "source_workfile_version_id": workflow["source_workfile_version_id"],
        "selected_roles": sorted(set(workflow["selected_roles"])),
        "published_resource_asset_ids": sorted(
            set(workflow["published_resource_asset_ids"])
        ),
        "promoted_resource_asset_ids": (
            []
            if proposed_view
            else sorted(set(workflow.get("promoted_resource_asset_ids") or []))
        ),
        "main_render_version_id": durable("main_render_version_id"),
        "main_render_media_id": durable("main_render_media_id"),
        "main_workfile_version_id": durable("main_workfile_version_id"),
        "main_workfile_media_id": durable("main_workfile_media_id"),
        "lineage_relationship_id": durable("lineage_relationship_id"),
        "assent_record_id": workflow["assent_record_id"],
        "assent_status": (
            "proposed" if proposed_view else workflow.get("assent_status")
        ),
        "resource_copy_manifest_fingerprint": workflow[
            "resource_copy_manifest_fingerprint"
        ],
        "resource_copy_commit_fingerprint": durable(
            "resource_copy_commit_fingerprint"
        ),
        "resource_registration_manifest_fingerprint": durable(
            "resource_registration_manifest_fingerprint"
        ),
        "resource_registration_commit_fingerprint": durable(
            "resource_registration_commit_fingerprint"
        ),
        "workfile_promotion_manifest_fingerprint": workflow[
            "workfile_promotion_manifest_fingerprint"
        ],
        "workfile_promotion_commit_fingerprint": durable(
            "workfile_promotion_commit_fingerprint"
        ),
        "lineage_binding_manifest_fingerprint": durable(
            "lineage_binding_manifest_fingerprint"
        ),
        "lineage_binding_commit_fingerprint": durable(
            "lineage_binding_commit_fingerprint"
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
    """Fail closed on any invariant a caller could otherwise leak."""
    status = receipt["status"]
    for stage, _complete in _STAGES:
        if receipt[f"{stage}_status"] not in _STAGE_STATUSES:
            raise ValueError(f"receipt {stage}_status is unsupported")
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
    if status == "proposed" and (
        receipt["dispatch_authorized"]
        or receipt["applied"]
        or receipt["replayed"]
        or receipt["main_advanced"]
        or receipt["reconciliation_required"]
        or receipt["promoted_resource_asset_ids"]
        or receipt["assent_status"] != "proposed"
        or receipt["resource_copy_manifest_fingerprint"] is None
        or receipt["workfile_promotion_manifest_fingerprint"] is None
        or any(
            receipt[f"{stage}_status"] != "not_started" for stage, _ in _STAGES
        )
    ):
        raise ValueError("proposed paired promotion receipt is contradictory")
    if status == "applied" and (
        not receipt["dispatch_authorized"]
        or not receipt["applied"]
        or not receipt["main_advanced"]
        or receipt["reconciliation_required"]
        or any(
            receipt[f"{stage}_status"] != complete
            for stage, complete in _STAGES
        )
        or receipt["main_render_version_id"] is None
        or receipt["main_render_media_id"] is None
        or receipt["main_workfile_version_id"] is None
        or receipt["lineage_relationship_id"] is None
        or not receipt["promoted_resource_asset_ids"]
        or any(
            receipt[field] is None
            for field in (
                "resource_copy_manifest_fingerprint",
                "resource_copy_commit_fingerprint",
                "resource_registration_manifest_fingerprint",
                "resource_registration_commit_fingerprint",
                "workfile_promotion_manifest_fingerprint",
                "workfile_promotion_commit_fingerprint",
                "lineage_binding_manifest_fingerprint",
                "lineage_binding_commit_fingerprint",
            )
        )
    ):
        raise ValueError("applied paired promotion receipt lacks evidence")
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
        raise ValueError("partial paired promotion receipt is contradictory")
    if receipt["replayed"] and (
        receipt["action"] != "replay" or status != "applied"
    ):
        raise ValueError("replayed paired promotion receipt is contradictory")


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
    "InMemoryAssentGateway",
    "InMemoryPairedPromotionWorkflowStore",
    "LINEAGE_BIND_TOOL",
    "LINEAGE_CALLABLE_OPERATION_TYPE",
    "PROMOTE_TOOL",
    "PROPOSAL_KIND",
    "PairedPromotionWorkflowAPI",
    "PairedPromotionWorkflowError",
    "RECEIPT_KIND",
    "RESOURCE_PLAN_OPERATION",
    "RESOURCE_REGISTER_TOOL",
    "SessionFactoryAssentGateway",
    "SessionFactoryPairedPromotionWorkflowStore",
    "VALIDATE_OPERATION",
    "WORKFILE_CALLABLE_OPERATION_TYPE",
    "WORKFILE_PROMOTE_TOOL",
    "WORKFLOW_KIND",
    "callable_discovery_arguments",
    "lineage_discovery_arguments",
    "make_paired_promotion_workflow_api",
    "paired_promotion_operator_sequence",
]
