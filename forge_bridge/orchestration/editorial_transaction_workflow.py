"""forge-bridge #241 / Pipeline Phase 153 — editorial transaction workflow API.

One durable product workflow over an ordered MULTI-command editorial
transaction, standing BESIDE the v1.9.11 single-edit workflow rather than
replacing it. It exposes five async transitions — ``propose``,
``ratify_apply``, ``status``, ``replay``, ``restore`` — and returns exactly one
closed, path-free ``bridge.editorial_transaction_workflow_receipt`` mapping for
every successful transition and every post-propose refusal. A failure before a
durable proposal exists raises ``EditorialTransactionWorkflowError``, which
carries a stable ``.code``.

Why a second workflow (#241 "Why This Is A New Contract"): the v1.9.11 path
admits exactly one step. Calling it twice for a two-command transaction would
create two assents, two commits, an observable partial state, and the wrong
replay/restore semantics. **One-step proposals continue through the existing
v1.9.11 path unchanged** — this module refuses a one-command proposal on
cardinality and never routes it.

Boundary discipline: Bridge owns graph composition, the AssentRecord lifecycle,
ratification, commit, durable workflow state, replay observation, and restore
orchestration. Pipeline owns editorial semantics — the preview, the ordered
step plan, the semantic capability plan, the pure apply receipt, the
TimelineDeltas, the realization operator, the aggregate transaction callable,
the recovery token, and the restore counterpart. Bridge never authors, derives,
or reconstructs any of those.

Lifecycle (#241 "Requested Bridge Lifecycle"):

1. ``propose`` admits ONE strict transaction proposal (2-8 ordered commands).
2. It FRESHLY runs the ``flame.editorial.transaction_realization`` discovery
   and requires exact agreement with the proposal before any graph intent
   exists.
3. It discovers exactly ONE ``forge_apply_segment_temporal_transaction``
   mutation manifest.
4. It persists one graph intent, one proposed ``AssentRecord``, one held
   manifest.
5. ``ratify_apply`` ratifies and commits exactly once through the aggregate
   callable, via the existing verify-before-apply ``CommitBoundary``. One
   assent produces at most one dispatch.
6. On a successful commit it extracts the single host-generated recovery token
   from the apply result, validates its schema/sequence, and persists it
   BYTE-FOR-BYTE plus its canonical fingerprint. Bridge never reconstructs it.
7. ``replay`` is observation only: no new assent, manifest, commit, or host
   dispatch.
8. ``restore`` re-verifies the persisted token fingerprint, discovers a fresh
   ``forge_apply_segment_temporal_transaction_restore`` manifest, takes a
   SEPARATE assent, and commits through the same boundary.
9. The forward proposal, realization, manifest, assent, and commit fingerprints
   are never rewritten by restore.

--------------------------------------------------------------------------- #
THREE BRIDGE-SIDE CALLS the #241 handoff left open (Pipeline pins after Bridge
publishes; all three are authored here, deliberately, and are the contract):

**(a) The receipt is a closed, versioned field set.** #241's "Receipt
Requirements" is narrative. It is realized here as
``bridge.editorial_transaction_workflow_receipt`` schema 1 with the exact
``_RECEIPT_KEYS`` below — nothing more, nothing less, every transition. It
deliberately does NOT overload the one-step
``bridge.editorial_edit_workflow_receipt``. ``fingerprint`` is canonical
SHA-256 (sorted keys, compact separators) over every receipt field EXCEPT
``kind``, ``schema_version``, and ``fingerprint`` itself — the #242 §8
convention, not #235's fingerprint-over-everything. No path, step plan,
manifest body, resolved plan, recovery-token body, graph, or native result may
appear in a receipt; every value is a scalar or a list of scalars.

**(b) The refusal-code set is closed and path-free**, in #242's
``publish_workflow_*`` house style with a ``transaction_workflow_`` prefix. #241
names only ``restore_unavailable`` / ``restore_drift``; the full set is
``_REASON_CODES`` below. As in #242 there is NO ``refused`` status taxon: a
transition that was attempted and did not stand is ``failed``; a transition
that was never on offer is ``unavailable``.

**(c) ``replay_observations`` is INSIDE the fingerprinted field set.** A
receipt is therefore a per-ACTION value, not a stored workflow identity: two
receipts for the same workflow legitimately differ once a replay is observed.
**Consumers must not treat receipt equality as workflow identity** — the
durable identity is ``(proposal_id, proposal_fingerprint)``. The one exception
is the ``propose`` view, which is pinned to the IMMUTABLE original proposal
projection so an exact duplicate propose keeps returning byte-identical bytes
forever.

--------------------------------------------------------------------------- #
HOST SHAPES (reconciled against the released Pipeline Phase 153 operator and
MCP executor — these are read from Pipeline's own executable outputs, not
assumed):

- The MCP signature is ``sequence_name, entries, mode, resolved_plan``.
  ``entries`` come from the FRESH realization's ordered deltas, read from
  ``realization_plan.deltas`` (discover mode intentionally does not surface
  them as top-level routable output). One unwrap is required and is proven
  executably, not assumed: a realization delta is a TimelineDelta and the
  callable takes the flat segment CHANGE inside it — passing the deltas
  themselves is refused host-side with ``transaction_continuity_mismatch``.
  See ``transaction_entries``. The delta-set fingerprint is still computed
  over the TimelineDeltas. Bridge forwards; it never authors.
- Both manifests are the STANDARD five-key ``MutationManifest``: ``type``,
  ``intent_parameters``, ``resolved_plan``, ``originating_capability``,
  ``apply_counterpart``. There is no ``ok`` / ``status`` / ``trust_status`` /
  ``mutation_safe`` / ``state_owner`` envelope and no ``transaction_plan``
  block. ``MutationManifest.from_dict`` plus counterpart admission IS the
  authority fence.
- One aggregate callable does NOT mean one resolved record: schema 1 emits one
  ordered host record per command, carrying ordinary Flame segment identity.
  Aggregate membership is proven by the record payloads (``member_index``,
  ``transaction_member_count``, ``method``, ``object_id``), not by any
  synthetic operation type.
- The forward apply payload is top-level ``{ok, status: "applied",
  applied: <n>, results: [member, member], recovery: <token>}``; the recovery
  token sits BESIDE the member results, not inside ``results[0]``.
- The restore apply payload is top-level ``{ok, status: "restored",
  restored: <n>, results, baseline_state, baseline_mismatches: [],
  recovery_fingerprint}``. That echoed fingerprint must be the one Bridge
  persisted — a real identity fence, checked in ``_restore_evidence``.

Two evidence ceilings (surfaced, not smoothed):

1. **Compensation.** ``CommitBoundary`` discards the host apply payload on an
   error result, so when the host reports a hard native failure Bridge can
   prove only that the workflow stays unapplied — it reports
   ``transaction_status="unknown"`` rather than guessing a rollback it did not
   read. The released Pipeline path always takes this opaque route: a native
   compensated failure carries verified host evidence but also ``ok: false`` +
   ``error``. The legible branch (a successful envelope reporting
   ``status="compensated"``) is retained as the correct reading if Pipeline
   ever ships one. ``flame.editorial.transaction_compensation_plan`` is
   PREFLIGHT authority only and must never be used to infer that compensation
   actually ran. See ``_transaction_disposition`` / ``_failure_patch``.
2. **Terminal baseline.** The host verifies the exact SEGMENT baseline before
   returning restore success and reports it as ``baseline_state``, but there is
   no whole-``EditState`` readback, so nothing is comparable to the proposal's
   whole-state ``source_state_fingerprint``. ``terminal_baseline_verified`` is
   therefore honestly ``False`` on every restore today. See
   ``_terminal_baseline``.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Optional

from forge_bridge.orchestration.workflow_core import (
    InMemoryWorkflowStore,
    ProposalTransitionGuard,
    SessionFactoryWorkflowStore,
    WorkflowStore,
    canonical_fingerprint,
    extract_recovery_token,
    finalize_receipt,
    held_manifest_from_record,
    is_sha256,
    sanitize,
    utc_now_iso,
    workflow_identifier,
)

PROPOSAL_KIND = "pipeline.traffik.editorial_transaction_bridge_proposal"
PROPOSAL_SCHEMA_VERSION = 1
RECEIPT_KIND = "bridge.editorial_transaction_workflow_receipt"
RECEIPT_SCHEMA_VERSION = 1

# Durable row discriminator inside the shared orch_workflow_record family
# (migration 0016 — #241 needs no further migration).
WORKFLOW_KIND = "bridge.editorial_transaction_workflow"

TRANSACTION_TOOL = "forge_apply_segment_temporal_transaction"
TRANSACTION_RESTORE_TOOL = "forge_apply_segment_temporal_transaction_restore"
TRANSACTION_REALIZATION_OPERATION_TYPE = "flame.editorial.transaction_realization"
RECOVERY_TOKEN_KIND = "flame.editorial.temporal_transaction_recovery"
RECOVERY_TOKEN_SCHEMA_VERSION = 1

TRANSACTION_STATE_OWNER = "dcc_host"

# Cardinality bounds (#241 "Pipeline Deliverables": two through eight closed
# commands).
MIN_COMMANDS = 2
MAX_COMMANDS = 8

# Schema 1's admitted native command shapes. #241: "Schema 1's first admitted
# native shape is trim_head then trim_tail on one continuous segment."
# ponytail ceiling: an explicit tuple, not a grammar. A second admitted shape
# is one more tuple; a shape language is warranted only when Pipeline ships
# shapes that cannot be enumerated.
ADMITTED_COMMAND_SHAPES: frozenset[tuple[str, ...]] = frozenset({
    ("trim_head", "trim_tail"),
})

# --------------------------------------------------------------------------- #
# (b) Stable, path-free refusal codes — the closed set
# --------------------------------------------------------------------------- #
REASON_PROPOSAL_INVALID = "transaction_workflow_proposal_invalid"
REASON_PROPOSAL_NOT_FOUND = "transaction_workflow_proposal_not_found"
REASON_PROPOSAL_CHANGED = "transaction_workflow_proposal_changed"
REASON_CARDINALITY_INVALID = "transaction_workflow_cardinality_invalid"
REASON_COMMAND_ORDER_INVALID = "transaction_workflow_command_order_invalid"
REASON_CONTINUITY_INVALID = "transaction_workflow_continuity_invalid"
REASON_REALIZATION_UNAVAILABLE = "transaction_workflow_realization_unavailable"
REASON_REALIZATION_DRIFT = "transaction_workflow_realization_drift"
REASON_MANIFEST_UNAVAILABLE = "transaction_workflow_manifest_unavailable"
REASON_MANIFEST_INVALID = "transaction_workflow_manifest_invalid"
REASON_MANIFEST_DRIFT = "transaction_workflow_manifest_drift"
REASON_ASSENT_INVALID = "transaction_workflow_assent_invalid"
REASON_COMMIT_FAILED = "transaction_workflow_commit_failed"
REASON_COMMIT_COMPENSATED = "transaction_workflow_commit_compensated"
REASON_REPLAY_UNAVAILABLE = "transaction_workflow_replay_unavailable"
REASON_RESTORE_UNAVAILABLE = "transaction_workflow_restore_unavailable"
REASON_RESTORE_DRIFT = "transaction_workflow_restore_drift"
REASON_RESTORE_FAILED = "transaction_workflow_restore_failed"

_REASON_CODES: frozenset[str] = frozenset({
    REASON_PROPOSAL_INVALID,
    REASON_PROPOSAL_NOT_FOUND,
    REASON_PROPOSAL_CHANGED,
    REASON_CARDINALITY_INVALID,
    REASON_COMMAND_ORDER_INVALID,
    REASON_CONTINUITY_INVALID,
    REASON_REALIZATION_UNAVAILABLE,
    REASON_REALIZATION_DRIFT,
    REASON_MANIFEST_UNAVAILABLE,
    REASON_MANIFEST_INVALID,
    REASON_MANIFEST_DRIFT,
    REASON_ASSENT_INVALID,
    REASON_COMMIT_FAILED,
    REASON_COMMIT_COMPENSATED,
    REASON_REPLAY_UNAVAILABLE,
    REASON_RESTORE_UNAVAILABLE,
    REASON_RESTORE_DRIFT,
    REASON_RESTORE_FAILED,
})

# No "refused" taxon (#242 §10 convention): attempted-and-did-not-stand is
# "failed"; never-on-offer is "unavailable".
_REFUSAL_STATUS: dict[str, str] = {
    REASON_PROPOSAL_CHANGED: "failed",
    REASON_REALIZATION_UNAVAILABLE: "unavailable",
    REASON_REALIZATION_DRIFT: "failed",
    REASON_MANIFEST_UNAVAILABLE: "unavailable",
    REASON_MANIFEST_INVALID: "failed",
    REASON_MANIFEST_DRIFT: "failed",
    REASON_ASSENT_INVALID: "failed",
    REASON_COMMIT_FAILED: "failed",
    REASON_COMMIT_COMPENSATED: "failed",
    REASON_REPLAY_UNAVAILABLE: "unavailable",
    REASON_RESTORE_UNAVAILABLE: "unavailable",
    REASON_RESTORE_DRIFT: "failed",
    REASON_RESTORE_FAILED: "failed",
}

# --------------------------------------------------------------------------- #
# Closed proposal field set
# --------------------------------------------------------------------------- #
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
    "final_state_fingerprint",
    # Private: the exact ordered command plan. Retained for verification and
    # restore, never projected into a receipt.
    "step_plan",
    "step_plan_fingerprint",
    "semantic_capability_plan_fingerprint",
    "pure_apply_fingerprint",
    "delta_set_fingerprint",
    "realization_plan_fingerprint",
    "fingerprint",
})
_PROPOSAL_TEXT_FIELDS = (
    "preview_id",
    "sequence_id",
    "sequence_name",
    "requested_by",
    "source_authority",
)
_PROPOSAL_SHA256_FIELDS = (
    "source_fingerprint",
    "preview_authority_fingerprint",
    "preview_fingerprint",
    "interaction_fingerprint",
    "source_state_fingerprint",
    "final_state_fingerprint",
    "step_plan_fingerprint",
    "semantic_capability_plan_fingerprint",
    "pure_apply_fingerprint",
    "delta_set_fingerprint",
    "realization_plan_fingerprint",
    "fingerprint",
)
# The proposal fingerprint uses the SAME exclusion rule as the receipt, so one
# contract has one arithmetic (#235's include-everything rule stays #235's).
_NON_BODY_FIELDS = frozenset({"kind", "schema_version", "fingerprint"})

# --------------------------------------------------------------------------- #
# (a) Ordered, closed receipt field set
# --------------------------------------------------------------------------- #
_RECEIPT_KEYS: tuple[str, ...] = (
    "kind",
    "schema_version",
    "action",
    "status",
    "trust_status",
    "workflow_id",
    "proposal_id",
    "proposal_fingerprint",
    "preview_id",
    "preview_authority_fingerprint",
    "preview_fingerprint",
    "interaction_fingerprint",
    "source_fingerprint",
    "source_state_fingerprint",
    "final_state_fingerprint",
    "step_plan_fingerprint",
    "semantic_capability_plan_fingerprint",
    "pure_apply_fingerprint",
    "delta_set_fingerprint",
    "realization_plan_fingerprint",
    "command_count",
    "manifest_fingerprint",
    "assent_record_id",
    "assent_status",
    "commit_fingerprint",
    "transaction_status",
    "recovery_token_fingerprint",
    "restore_availability",
    "restore_manifest_fingerprint",
    "restore_assent_record_id",
    "restore_assent_status",
    "restore_commit_fingerprint",
    "terminal_baseline_fingerprint",
    "terminal_baseline_verified",
    "replay_observations",
    "dispatch_authorized",
    "applied",
    "replayed",
    "restored",
    "reason_code",
)
_RECEIPT_FINGERPRINT_EXCLUDES = frozenset({"kind", "schema_version"})

_ACTIONS = frozenset({"propose", "ratify_apply", "status", "replay", "restore"})
_STATUSES = frozenset({
    "proposed",
    "applied",
    "failed",
    "unavailable",
    "restored",
})
_TRANSACTION_STATUSES = frozenset({
    "not_started",
    "committed",
    "compensated",
    "failed",
    "unknown",
    "restored",
})
_RESTORE_AVAILABILITY = frozenset({
    "not_applicable",
    "available",
    "unavailable",
    "restored",
})
_TRUSTED_STATUSES = frozenset({"proposed", "applied", "restored"})


class EditorialTransactionWorkflowError(Exception):
    """Raised only when a transition cannot ground a durable proposal.

    Carries a stable, path-free ``code``; the Pipeline adapter reads ``.code``
    and never surfaces the message body.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = sanitize(message)
        super().__init__(f"{code}: {self.message}")


class _DiscoveryUnavailable(Exception):
    """Internal: the callable/operator did not answer at all."""


class _DiscoveryDrift(Exception):
    """Internal: it answered, but not with this proposal's held authority."""


class _AssentUnavailable(Exception):
    """Internal: the AssentRecord could not be ratified."""


# --------------------------------------------------------------------------- #
# Durable store
# --------------------------------------------------------------------------- #
class InMemoryEditorialTransactionWorkflowStore(InMemoryWorkflowStore):
    """Process-local store — unit tests and stock installs without Postgres."""

    def __init__(self) -> None:
        super().__init__(authority_field="preview_authority_fingerprint")


class SessionFactoryEditorialTransactionWorkflowStore(
    SessionFactoryWorkflowStore
):
    """Durable store over ``OrchWorkflowRecordRepo`` — reuses migration 0016's
    ``orch_workflow_record`` table under a new ``kind``; no new migration."""

    def __init__(self, session_factory: Any) -> None:
        super().__init__(session_factory, repo_factory=_workflow_repo)


def _workflow_repo(session: Any) -> Any:
    from forge_bridge.store.orch_workflow_record_repo import (
        OrchWorkflowRecordRepo,
    )

    return OrchWorkflowRecordRepo(
        session,
        kind=WORKFLOW_KIND,
        authority_field="preview_authority_fingerprint",
    )


# --------------------------------------------------------------------------- #
# AssentRecord gateway
# --------------------------------------------------------------------------- #
# ponytail ceiling: this seam mirrors #242's rather than importing it. The two
# contracts stay uncoupled by design (see workflow_core's module docstring —
# collapsing them would make one workflow's contract silently govern the
# other). Fold both onto workflow_core when a THIRD consumer appears, not
# before.
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


# --------------------------------------------------------------------------- #
# Discovery arguments (composed by Bridge, never submitted by the Shell)
# --------------------------------------------------------------------------- #
def realization_discovery_params(
    proposal: Mapping[str, Any], *, mode: str = "discover"
) -> dict[str, Any]:
    """Parameters for the fresh ``flame.editorial.transaction_realization`` run.

    INCOMPLETE BY CONSTRUCTION, and deliberately so. The operator additionally
    requires the full ``semantic_capability_plan`` and pure ``apply_result``
    BODIES; the public Bridge proposal carries only their fingerprints. That is
    why ``realize_fn`` is an injection point on the factory rather than a
    detail: production wiring supplies a store-backed callback that reads those
    private bodies from the verified held Pipeline preview. This builder is the
    test/default half of that seam.
    """
    return {
        "mode": mode,
        "step_plan": proposal["step_plan"],
        "sequence_name": proposal["sequence_name"],
        "held_step_plan_fingerprint": proposal["step_plan_fingerprint"],
        "held_semantic_capability_plan_fingerprint": proposal[
            "semantic_capability_plan_fingerprint"
        ],
        "held_apply_result_fingerprint": proposal["pure_apply_fingerprint"],
        "held_realization_plan_fingerprint": proposal[
            "realization_plan_fingerprint"
        ],
    }


def transaction_discovery_arguments(
    proposal: Mapping[str, Any], entries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Arguments for the ONE aggregate transaction manifest discovery.

    This is the public MCP signature of
    ``forge_apply_segment_temporal_transaction``
    (``forge_core/bridge/registry.py``): ``sequence_name``, ``entries``,
    ``mode``, ``resolved_plan``. ``entries`` are the freshly authorized
    realization deltas — Bridge forwards them, it never authors them.
    """
    return {
        "sequence_name": proposal["sequence_name"],
        "entries": [dict(entry) for entry in entries],
        "mode": "discover",
        "resolved_plan": None,
    }


def realization_deltas(realization: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The exact ordered TimelineDeltas held inside a fresh realization result.

    The realization operator intentionally does NOT expose them as top-level
    routable output until authorization, so they are read from
    ``realization_plan.deltas``. These are the objects the realization's own
    ``delta_set_fingerprint`` is computed over.
    """
    plan = realization.get("realization_plan")
    deltas = plan.get("deltas") if isinstance(plan, Mapping) else None
    if not isinstance(deltas, list) or not all(
        isinstance(delta, Mapping) for delta in deltas
    ):
        raise _invalid(
            "fresh realization carries no ordered deltas",
            REASON_REALIZATION_UNAVAILABLE,
        )
    return [dict(delta) for delta in deltas]


def transaction_entries(
    deltas: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """The flat segment CHANGES the transaction callable takes as ``entries``.

    Layering, proven executably against the released executor: a realization
    delta is a TimelineDelta (``{type, sequence_id, metadata, changes}``), while
    ``forge_apply_segment_temporal_transaction`` requires the flat segment
    change inside it (``{action, object_type, object_id, before, after,
    metadata}``). Passing the TimelineDeltas themselves is refused host-side
    with ``transaction_continuity_mismatch``. Schema 1 carries exactly one
    segment change per delta; anything else fails closed here rather than at
    the host.
    """
    entries: list[dict[str, Any]] = []
    for delta in deltas:
        changes = delta.get("changes")
        if not isinstance(changes, list) or len(changes) != 1:
            raise _invalid(
                "a realization delta does not carry exactly one change",
                REASON_REALIZATION_DRIFT,
            )
        change = changes[0]
        if (
            not isinstance(change, Mapping)
            or change.get("object_type") != "segment"
            or not change.get("object_id")
        ):
            raise _invalid(
                "a realization delta change is not a segment change",
                REASON_REALIZATION_DRIFT,
            )
        entries.append(dict(change))
    return entries


def restore_discovery_arguments(
    *, sequence_name: str, recovery: Mapping[str, Any]
) -> dict[str, Any]:
    """Arguments for the fresh restore-counterpart discovery.

    ``recovery`` is the persisted host token, handed back untouched.
    """
    return {
        "sequence_name": sequence_name,
        "recovery": dict(recovery),
        "mode": "discover",
        "resolved_plan": None,
    }


# --------------------------------------------------------------------------- #
# The API
# --------------------------------------------------------------------------- #
RealizeFn = Callable[..., Awaitable[Any]]
DiscoverFn = Callable[..., Awaitable[Any]]
PreviewFn = Callable[..., Awaitable[dict[str, Any]]]
ApplyFn = Callable[..., Awaitable[dict[str, Any]]]


class EditorialTransactionWorkflowAPI:
    """Closed multi-command editorial transaction workflow."""

    def __init__(
        self,
        *,
        store: WorkflowStore,
        realize_fn: RealizeFn,
        discover_fn: DiscoverFn,
        preview_fn: PreviewFn,
        apply_fn: ApplyFn,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        self._store = store
        self._realize_fn = realize_fn
        self._discover_fn = discover_fn
        self._preview_fn = preview_fn
        self._apply_fn = apply_fn
        self._clock = clock or utc_now_iso
        self._guard = ProposalTransitionGuard(store)

    # -- propose ----------------------------------------------------------- #
    async def propose(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        normalized = _validate_proposal(proposal)
        proposal_fingerprint = normalized["fingerprint"]
        proposal_id = workflow_identifier("etw_", proposal_fingerprint)
        workflow_id = workflow_identifier("etwf_", proposal_fingerprint)

        existing = await self._store.get_by_proposal_id(proposal_id)
        if existing is not None:
            # Exact duplicate: the IMMUTABLE original proposal receipt.
            return _build_receipt("propose", existing, status="proposed")

        collision = await self._store.get_by_authority_fingerprint(
            normalized["preview_authority_fingerprint"]
        )
        if collision is not None:
            # A CHANGED proposal under the same preview authority.
            raise EditorialTransactionWorkflowError(
                REASON_PROPOSAL_INVALID,
                "preview authority is already bound to a different proposal",
            )

        # 2. Fresh realization discovery BEFORE any graph intent exists.
        realization = await self._realize(normalized)

        # 3. Exactly ONE aggregate transaction mutation manifest, discovered
        #    from the freshly authorized deltas that realization just held.
        held_manifest = await self._discover_transaction(normalized, realization)

        # 4. One graph intent, one proposed AssentRecord, one held manifest.
        preview = await self._preview(
            held_manifest=held_manifest,
            chain_steps=[
                f"editorial transaction of "
                f"{_command_count(normalized)} ordered commands",
                "commit",
            ],
            display="Phase 153 editorial transaction",
        )

        now = self._clock()
        record = {
            "kind": WORKFLOW_KIND,
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "workflow_id": workflow_id,
            "proposal_id": proposal_id,
            "proposal_fingerprint": proposal_fingerprint,
            # Private: retained for verification + restore, never in a receipt.
            "proposal": normalized,
            "preview_id": normalized["preview_id"],
            "preview_authority_fingerprint": normalized[
                "preview_authority_fingerprint"
            ],
            "preview_fingerprint": normalized["preview_fingerprint"],
            "interaction_fingerprint": normalized["interaction_fingerprint"],
            "source_fingerprint": normalized["source_fingerprint"],
            "source_state_fingerprint": normalized["source_state_fingerprint"],
            "final_state_fingerprint": normalized["final_state_fingerprint"],
            "step_plan_fingerprint": normalized["step_plan_fingerprint"],
            "semantic_capability_plan_fingerprint": normalized[
                "semantic_capability_plan_fingerprint"
            ],
            "pure_apply_fingerprint": normalized["pure_apply_fingerprint"],
            "delta_set_fingerprint": normalized["delta_set_fingerprint"],
            "realization_plan_fingerprint": normalized[
                "realization_plan_fingerprint"
            ],
            "command_count": _command_count(normalized),
            "forward_manifest_fingerprint": canonical_fingerprint(
                held_manifest
            ),
            "forward_held_manifest": held_manifest,
            "forward_graph_intent_id": preview["graph_intent_id"],
            "forward_assent_record_id": preview["assent_record_id"],
            "forward_assent_status": "proposed",
            "forward_commit_fingerprint": None,
            "transaction_status": "not_started",
            "recovery_token": None,
            "recovery_token_fingerprint": None,
            "restore_availability": "not_applicable",
            "restore_manifest_fingerprint": None,
            "restore_graph_intent_id": None,
            "restore_assent_record_id": None,
            "restore_assent_status": None,
            "restore_commit_fingerprint": None,
            "terminal_baseline_fingerprint": None,
            "terminal_baseline_verified": False,
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
            raise EditorialTransactionWorkflowError(
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
            # Durable status guard: one assent produces at most ONE dispatch,
            # and it fails closed across processes even if the lock was lost.
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
                count = int(workflow["command_count"])
                disposition = _transaction_disposition(outcome, count)
                if disposition != "committed":
                    # The commit rail succeeded but the host reports the
                    # transaction did not stand. Never an "applied" receipt.
                    patch["status"] = "failed"
                    patch["transaction_status"] = disposition
                    patch["reason_code"] = (
                        REASON_COMMIT_COMPENSATED
                        if disposition == "compensated"
                        else REASON_COMMIT_FAILED
                    )
                    patch["restore_availability"] = "unavailable"
                    stored = await self._store.update(proposal_id, patch)
                    return _refuse(
                        "ratify_apply", stored, patch["reason_code"]
                    )

                patch["status"] = "applied"
                patch["reason_code"] = None
                patch["transaction_status"] = "committed"
                patch["forward_commit_fingerprint"] = canonical_fingerprint(
                    outcome["commit_result"]
                )
                # 6. Persist the host token BYTE-FOR-BYTE plus its canonical
                # fingerprint. A missing/invalid token never rewrites this
                # success — it only leaves restore unavailable.
                recovery = _extract_transaction_recovery(
                    outcome, workflow["proposal"].get("sequence_name"), count
                )
                if recovery is None:
                    patch["restore_availability"] = "unavailable"
                else:
                    patch["recovery_token"] = recovery
                    patch["recovery_token_fingerprint"] = (
                        canonical_fingerprint(recovery)
                    )
                    patch["restore_availability"] = "available"
                stored = await self._store.update(proposal_id, patch)
                return _build_receipt("ratify_apply", stored, status="applied")

            reason = outcome.get("reason_code") or REASON_COMMIT_FAILED
            patch.update(_failure_patch(reason, outcome))
            stored = await self._store.update(proposal_id, patch)
            return _refuse("ratify_apply", stored, reason)

    # -- status ------------------------------------------------------------ #
    async def status(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
    ) -> dict[str, Any]:
        """Read durable Bridge workflow state. Never rediscovers or dispatches.

        NB (learned from #242 correction 1): a status poll on an unratified
        workflow honestly reports ``proposed``. This contract deliberately does
        NOT bind the ``proposed`` status to the ``propose`` action.
        """
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "status", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed
        return _build_receipt(
            "status", workflow, status=str(workflow["status"])
        )

    # -- replay ------------------------------------------------------------ #
    async def replay(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
        requested_by: str,
    ) -> dict[str, Any]:
        """Observe an already-committed transaction. Observation ONLY.

        7. No new assent, manifest, commit, or host dispatch — the only durable
        effect is the incremented observation count.
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
            # Never before apply, and never after a restore has undone it.
            return _refuse("replay", workflow, REASON_REPLAY_UNAVAILABLE)

        patch = {
            "replay_observations": int(workflow.get("replay_observations", 0))
            + 1,
            "timestamps": {**workflow["timestamps"], "replay": self._clock()},
            "actors": {**workflow["actors"], "replay": requested_by},
        }
        stored = await self._store.update(proposal_id, patch)
        return _build_receipt(
            "replay", stored, status=str(stored["status"])
        )

    # -- restore ----------------------------------------------------------- #
    async def restore(
        self,
        *,
        proposal_id: str,
        expected_proposal_fingerprint: str,
        requested_by: str,
    ) -> dict[str, Any]:
        """8. Re-verify the token, discover fresh, take a SEPARATE assent."""
        workflow = await self._load_or_raise(proposal_id)
        changed = _fingerprint_refusal(
            "restore", workflow, expected_proposal_fingerprint
        )
        if changed is not None:
            return changed

        async with self._guard.lock(proposal_id):
            workflow = await self._reload_or_raise(proposal_id)
            if workflow["status"] == "restored":
                # Idempotent no-op: a trusted restore already committed.
                return _build_receipt("restore", workflow, status="restored")
            if workflow["status"] != "applied":
                return _refuse(
                    "restore", workflow, REASON_RESTORE_UNAVAILABLE
                )

            recovery = workflow.get("recovery_token")
            recovery_fingerprint = workflow.get("recovery_token_fingerprint")
            if not recovery or not recovery_fingerprint:
                # No trusted token captured at forward apply => fail closed.
                return _refuse(
                    "restore", workflow, REASON_RESTORE_UNAVAILABLE
                )
            if canonical_fingerprint(recovery) != recovery_fingerprint:
                # Persisted token tampered/altered => drift, never dispatch.
                return _refuse("restore", workflow, REASON_RESTORE_DRIFT)

            sequence_name = workflow["proposal"].get("sequence_name")
            command_count = int(workflow["command_count"])
            try:
                held_restore = await self._discover(
                    TRANSACTION_RESTORE_TOOL,
                    restore_discovery_arguments(
                        sequence_name=sequence_name, recovery=recovery
                    ),
                )
                _verify_restore_manifest(
                    held_restore,
                    sequence_name=sequence_name,
                    recovery=recovery,
                    command_count=command_count,
                )
            except _DiscoveryUnavailable:
                return _refuse(
                    "restore", workflow, REASON_RESTORE_UNAVAILABLE
                )
            except _DiscoveryDrift:
                return _refuse("restore", workflow, REASON_RESTORE_DRIFT)

            preview = await self._preview(
                held_manifest=held_restore,
                chain_steps=[
                    f"restore editorial transaction of "
                    f"{command_count} ordered commands",
                    "commit",
                ],
                display="Phase 153 editorial transaction restore",
            )
            outcome = await self._apply_fn(
                graph_intent_id=preview["graph_intent_id"],
                requested_by=requested_by,
            )
            now = self._clock()
            # A SECOND held manifest + a SECOND proposed AssentRecord. The
            # forward proposal / realization / manifest / assent / commit
            # fingerprints are never touched here.
            patch: dict[str, Any] = {
                "restore_manifest_fingerprint": canonical_fingerprint(
                    held_restore
                ),
                "restore_graph_intent_id": preview["graph_intent_id"],
                "restore_assent_record_id": preview["assent_record_id"],
                "restore_assent_status": outcome.get("assent_status"),
                "timestamps": {**workflow["timestamps"], "restore": now},
                "actors": {**workflow["actors"], "restore": requested_by},
            }
            evidence = (
                _restore_evidence(
                    outcome,
                    command_count=command_count,
                    token_fingerprint=recovery.get("fingerprint"),
                )
                if outcome["outcome"] == "applied"
                else None
            )
            if outcome["outcome"] != "applied" or evidence is None:
                # A failed restore — or one whose success evidence does not
                # bind THIS held token — leaves the durable status "applied".
                patch["status"] = "applied"
                patch["reason_code"] = (
                    REASON_RESTORE_FAILED
                    if outcome["outcome"] != "applied"
                    else REASON_RESTORE_DRIFT
                )
                patch["restore_availability"] = "available"
                stored = await self._store.update(proposal_id, patch)
                return _refuse("restore", stored, patch["reason_code"])

            baseline, whole_state = _terminal_baseline(outcome, evidence)
            patch["status"] = "restored"
            patch["reason_code"] = None
            patch["transaction_status"] = "restored"
            patch["restore_availability"] = "restored"
            patch["restore_commit_fingerprint"] = canonical_fingerprint(
                outcome["commit_result"]
            )
            # Durable operator evidence; the receipt stays closed at 41 fields.
            patch["restore_baseline_state"] = evidence["baseline_state"]
            patch["terminal_baseline_fingerprint"] = baseline
            patch["terminal_baseline_verified"] = bool(
                whole_state
                and baseline == workflow["source_state_fingerprint"]
            )
            stored = await self._store.update(proposal_id, patch)
            return _build_receipt("restore", stored, status="restored")

    # -- internals --------------------------------------------------------- #
    async def _realize(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        """Fresh realization discovery, required to agree EXACTLY (step 2)."""
        from forge_bridge.composition.admission import (
            AdmissionRejected,
            admit_operator,
        )

        try:
            admitted = admit_operator(TRANSACTION_REALIZATION_OPERATION_TYPE)
        except AdmissionRejected as exc:
            raise EditorialTransactionWorkflowError(
                REASON_REALIZATION_UNAVAILABLE,
                "transaction realization operator is not admitted",
            ) from exc
        if not admitted.no_state_mutation:
            raise EditorialTransactionWorkflowError(
                REASON_REALIZATION_UNAVAILABLE,
                "transaction realization operator is not declared read-only",
            )

        try:
            result = await _maybe_await(
                self._realize_fn(proposal=proposal, mode="discover")
            )
        except EditorialTransactionWorkflowError:
            raise
        except Exception as exc:  # noqa: BLE001 - transport boundary evidence
            raise EditorialTransactionWorkflowError(
                REASON_REALIZATION_UNAVAILABLE,
                "transaction realization discovery did not answer",
            ) from exc
        payload = _operation_data(result)
        if payload is None:
            raise EditorialTransactionWorkflowError(
                REASON_REALIZATION_UNAVAILABLE,
                "transaction realization discovery returned no data",
            )
        _verify_realization(payload, proposal)
        return payload

    async def _discover_transaction(
        self, proposal: Mapping[str, Any], realization: Mapping[str, Any]
    ) -> dict[str, Any]:
        deltas = realization_deltas(realization)
        entries = transaction_entries(deltas)
        try:
            payload = await self._discover(
                TRANSACTION_TOOL,
                transaction_discovery_arguments(proposal, entries),
            )
        except _DiscoveryUnavailable as exc:
            raise EditorialTransactionWorkflowError(
                REASON_MANIFEST_UNAVAILABLE,
                "transaction callable did not answer",
            ) from exc
        except _DiscoveryDrift as exc:
            raise EditorialTransactionWorkflowError(
                REASON_MANIFEST_INVALID,
                "transaction discovery was not trusted",
            ) from exc
        _verify_transaction_manifest(payload, proposal, deltas, entries)
        return payload

    async def _discover(
        self, tool: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        result = await self._discover_fn(tool=tool, arguments=dict(arguments))
        if not isinstance(result, dict):
            raise _DiscoveryDrift("discovery did not return a payload mapping")
        return result

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
        except EditorialTransactionWorkflowError:
            raise
        except Exception as exc:  # noqa: BLE001 - persistence failure
            raise EditorialTransactionWorkflowError(
                REASON_MANIFEST_INVALID,
                "preview did not persist a durable mutation manifest",
            ) from exc

    async def _load_or_raise(self, proposal_id: str) -> dict[str, Any]:
        workflow = await self._store.get_by_proposal_id(proposal_id)
        if workflow is None:
            raise EditorialTransactionWorkflowError(
                REASON_PROPOSAL_NOT_FOUND,
                "no workflow for the supplied proposal id",
            )
        return workflow

    async def _reload_or_raise(self, proposal_id: str) -> dict[str, Any]:
        workflow = await self._guard.reload(proposal_id)
        if workflow is None:
            raise EditorialTransactionWorkflowError(
                REASON_PROPOSAL_NOT_FOUND, "workflow disappeared"
            )
        return workflow


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #
def make_editorial_transaction_workflow_api(
    *,
    session_factory: Any,
    mcp: Any,
    run_operation: Callable[..., Any] | None = None,
    store: WorkflowStore | None = None,
    assent_gateway: AssentGateway | None = None,
    realize_fn: RealizeFn | None = None,
    discover_fn: DiscoverFn | None = None,
    preview_fn: PreviewFn | None = None,
    apply_fn: ApplyFn | None = None,
    clock: Callable[[], str] | None = None,
) -> EditorialTransactionWorkflowAPI:
    """Construct the workflow API.

    ``realize_fn`` is a PRODUCTION injection point, not just a test seam.
    ``FlameEditorialTransactionRealizationOperator`` requires the full
    ``semantic_capability_plan`` and pure ``apply_result`` bodies, which the
    public proposal does not carry (it carries their fingerprints), so
    production wiring supplies a store-backed callback that reads them from the
    verified held Pipeline preview and projects ``final_state_fingerprint`` and
    ``command_count`` onto the result. The default ``run_operation`` argument
    builder is sufficient only where those bodies are already reachable.
    """
    if store is None:
        if session_factory is None:
            raise ValueError(
                "session_factory is required when store is not supplied"
            )
        store = SessionFactoryEditorialTransactionWorkflowStore(
            session_factory
        )
    if assent_gateway is None and (preview_fn is None or apply_fn is None):
        assent_gateway = SessionFactoryAssentGateway(session_factory)
    if realize_fn is None:
        if run_operation is None:
            raise ValueError(
                "run_operation is required when realize_fn is not supplied"
            )
        realize_fn = _default_realize_fn(run_operation)
    if discover_fn is None:
        discover_fn = _default_discover_fn(mcp)
    if preview_fn is None:
        preview_fn = _default_preview_fn(assent_gateway)
    if apply_fn is None:
        apply_fn = _default_apply_fn(assent_gateway, mcp)
    return EditorialTransactionWorkflowAPI(
        store=store,
        realize_fn=realize_fn,
        discover_fn=discover_fn,
        preview_fn=preview_fn,
        apply_fn=apply_fn,
        clock=clock,
    )


def _default_realize_fn(run_operation: Callable[..., Any]) -> RealizeFn:
    async def realize(
        *, proposal: Mapping[str, Any], mode: str = "discover"
    ) -> Any:
        return await _maybe_await(
            run_operation(
                TRANSACTION_REALIZATION_OPERATION_TYPE,
                params=realization_discovery_params(proposal, mode=mode),
                idempotency_key=(
                    f"editorial-transaction-realization-{mode}:"
                    f"{proposal['step_plan_fingerprint']}"
                ),
                project_id=proposal.get("project_id"),
                requested_by=proposal.get("requested_by")
                or "forge_bridge.editorial_transaction_workflow",
            )
        )

    return realize


def _default_discover_fn(mcp: Any) -> DiscoverFn:
    """Discover a mutation manifest from an admitted commit-only counterpart.

    The counterparts are admitted for COMMIT, not for the executor surface
    (the shipped split-delta/split-restore precedent), so discovery is a direct
    tool call rather than a graph dispatch. The manifest it returns is what the
    real verify-before-apply ``CommitBoundary`` later replays.
    """

    async def discover(*, tool: str, arguments: dict[str, Any]) -> Any:
        from forge_bridge.composition.boundary import (
            _extract_payload,
            _maybe_list_tools,
        )

        if mcp is None:
            raise _DiscoveryUnavailable("no commit rail for discovery")
        try:
            available = await _maybe_list_tools(mcp)
        except Exception as exc:  # noqa: BLE001 - transport boundary evidence
            raise _DiscoveryDrift("tool discovery failed") from exc
        if available is not None and tool not in _tool_names(available):
            raise _DiscoveryUnavailable("counterpart is not declared")
        try:
            return _extract_payload(
                await mcp.call_tool(tool, arguments=dict(arguments))
            )
        except Exception as exc:  # noqa: BLE001 - transport boundary evidence
            raise _DiscoveryDrift("discovery call failed") from exc

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
# Proposal validation
# --------------------------------------------------------------------------- #
def _invalid(
    message: str, code: str = REASON_PROPOSAL_INVALID
) -> EditorialTransactionWorkflowError:
    return EditorialTransactionWorkflowError(code, message)


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

    normalized = {key: proposal[key] for key in _PROPOSAL_FIELDS}
    body = {
        key: value
        for key, value in normalized.items()
        if key not in _NON_BODY_FIELDS
    }
    if canonical_fingerprint(body) != normalized["fingerprint"]:
        raise _invalid("proposal fingerprint mismatch")
    if canonical_fingerprint(normalized["step_plan"]) != normalized[
        "step_plan_fingerprint"
    ]:
        raise _invalid("step_plan fingerprint mismatch")

    _validate_step_plan(normalized)
    return normalized


def _validate_step_plan(proposal: Mapping[str, Any]) -> None:
    """Cardinality, command order, and continuity each refuse distinctly."""
    step_plan = proposal["step_plan"]
    if not isinstance(step_plan, Mapping):
        raise _invalid("step_plan must be a mapping")
    steps = step_plan.get("steps")
    if not isinstance(steps, list):
        raise _invalid("step_plan must carry a list of steps")

    # -- cardinality ------------------------------------------------------- #
    if len(steps) < MIN_COMMANDS or len(steps) > MAX_COMMANDS:
        # A ONE-command proposal belongs to the v1.9.11 single-edit path and is
        # refused here rather than routed.
        raise _invalid(
            f"a transaction admits {MIN_COMMANDS}-{MAX_COMMANDS} ordered "
            f"commands, not {len(steps)}",
            REASON_CARDINALITY_INVALID,
        )
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            raise _invalid(f"step {index} must be a mapping")
        if not isinstance(step.get("operation"), str) or not step[
            "operation"
        ].strip():
            raise _invalid(f"step {index} carries no operation")
        if not isinstance(step.get("step_id"), str) or not step[
            "step_id"
        ].strip():
            raise _invalid(f"step {index} carries no step_id")
        if not isinstance(step.get("params"), Mapping):
            raise _invalid(f"step {index} carries no params mapping")

    # -- command order ----------------------------------------------------- #
    shape = tuple(str(step["operation"]) for step in steps)
    if shape not in ADMITTED_COMMAND_SHAPES:
        raise _invalid(
            "command order is not an admitted schema-1 native shape",
            REASON_COMMAND_ORDER_INVALID,
        )
    if len({step["step_id"] for step in steps}) != len(steps):
        raise _invalid(
            "ordered commands must carry distinct step ids",
            REASON_COMMAND_ORDER_INVALID,
        )

    # -- continuity -------------------------------------------------------- #
    # ponytail ceiling: continuity is proven by SEGMENT REFERENT identity —
    # every command names the same segment on the same sequence. Frame-range
    # continuity is editorial geometry and stays Pipeline's; Bridge proves the
    # referent, not the geometry.
    referents = {_segment_referent(step) for step in steps}
    if len(referents) != 1 or None in referents:
        raise _invalid(
            "ordered commands do not name one continuous segment",
            REASON_CONTINUITY_INVALID,
        )
    sequences = {
        step["params"].get("sequence_id")
        for step in steps
        if "sequence_id" in step["params"]
    }
    if len(sequences) > 1 or (
        sequences and proposal["sequence_id"] not in sequences
    ):
        raise _invalid(
            "ordered commands do not share the proposal sequence",
            REASON_CONTINUITY_INVALID,
        )


def _segment_referent(step: Mapping[str, Any]) -> Optional[str]:
    params = step.get("params") or {}
    for candidate in (params.get("segment_id"), step.get("node_id")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def _command_count(proposal: Mapping[str, Any]) -> int:
    return len(proposal["step_plan"]["steps"])


# --------------------------------------------------------------------------- #
# Realization + manifest verification
# --------------------------------------------------------------------------- #
_REALIZATION_REQUIRED = {
    "operation_type": TRANSACTION_REALIZATION_OPERATION_TYPE,
    "mode": "discover",
    "status": "ready",
    "trust_status": "trusted",
    "allowed": True,
    "dispatch_authorized": False,
    "drift": False,
    "read_only": True,
    "mutation_safe": True,
    "realization_authority": "forge_flame",
    "composition_owner": "bridge",
}
# Fresh realization key -> the proposal field it must equal EXACTLY.
_REALIZATION_AGREEMENT = {
    "step_plan_fingerprint": "step_plan_fingerprint",
    "semantic_capability_plan_fingerprint": (
        "semantic_capability_plan_fingerprint"
    ),
    "apply_result_fingerprint": "pure_apply_fingerprint",
    "delta_set_fingerprint": "delta_set_fingerprint",
    "realization_plan_fingerprint": "realization_plan_fingerprint",
    # PROJECTED by the injected realize_fn from the verified held preview —
    # the realization operator itself emits neither of these two keys.
    "final_state_fingerprint": "final_state_fingerprint",
}


def _verify_realization(
    payload: Mapping[str, Any], proposal: Mapping[str, Any]
) -> None:
    for key, expected in _REALIZATION_REQUIRED.items():
        if payload.get(key) != expected:
            raise _invalid(
                f"fresh realization is not trusted at {key}",
                REASON_REALIZATION_UNAVAILABLE,
            )
    for key, field in _REALIZATION_AGREEMENT.items():
        if payload.get(key) != proposal[field]:
            raise _invalid(
                f"fresh realization {key} drifted from the proposal",
                REASON_REALIZATION_DRIFT,
            )
    if payload.get("command_count") != _command_count(proposal):
        raise _invalid(
            "fresh realization command count drifted from the proposal",
            REASON_REALIZATION_DRIFT,
        )
    if "deltas" in payload:
        # discover mode holds the deltas inside realization_plan; it must never
        # surface them as top-level routable output.
        raise _invalid(
            "realization discover mode must not emit routable deltas",
            REASON_REALIZATION_UNAVAILABLE,
        )
    if len(realization_deltas(payload)) != _command_count(proposal):
        raise _invalid(
            "fresh realization does not hold one delta per command",
            REASON_REALIZATION_DRIFT,
        )


def _admitted_manifest(
    payload: Mapping[str, Any],
    tool: str,
    fail: Callable[[str], Exception],
) -> Any:
    """Check 1 — one structurally valid manifest + one admitted counterpart.

    The host manifest is the STANDARD five-key ``MutationManifest``
    (``type``, ``intent_parameters``, ``resolved_plan``,
    ``originating_capability``, ``apply_counterpart``). It carries no ``ok`` /
    ``status`` / ``trust_status`` / ``mutation_safe`` / ``state_owner`` /
    ``kind`` / ``schema_version`` envelope — ``MutationManifest.from_dict``
    plus counterpart admission IS the authority fence, matching the shipped
    mutation-manifest convention.
    """
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
        raise fail("discovered manifest is structurally invalid") from exc
    if payload.get("originating_capability") != tool:
        raise fail("discovered manifest has the wrong originating capability")
    if manifest.apply_counterpart.get("tool") != tool:
        raise fail("discovered manifest has the wrong apply counterpart")
    try:
        counterpart = admit_mutation_counterpart(tool)
    except AdmissionRejected as exc:
        raise fail("apply counterpart is not admitted") from exc
    if (
        counterpart.state_owner != TRANSACTION_STATE_OWNER
        or not counterpart.verify_before_apply
        or not counterpart.assent_required
    ):
        raise fail("apply counterpart lacks the required commit authority")
    return manifest


def _member_payloads(
    records: Any, count: int, fail: Callable[[str], Exception]
) -> list[dict[str, Any]]:
    """Check 5 — one host change record per transaction member, in order."""
    if not isinstance(records, list) or len(records) != count:
        raise fail("manifest resolved plan does not cover every member")
    payloads: list[dict[str, Any]] = []
    for record in records:
        payload = record.get("payload") if isinstance(record, Mapping) else None
        identity = (
            record.get("identity") if isinstance(record, Mapping) else None
        )
        if not isinstance(payload, Mapping) or not isinstance(identity, Mapping):
            raise fail("manifest change record is structurally invalid")
        payloads.append(dict(payload))
    return payloads


def _verify_transaction_manifest(
    payload: Mapping[str, Any],
    proposal: Mapping[str, Any],
    deltas: Sequence[Mapping[str, Any]],
    entries: Sequence[Mapping[str, Any]],
) -> None:
    """Prove the discovered manifest IS this proposal's ONE transaction.

    Pipeline's six checks. Aggregate membership is proven by the record
    PAYLOAD fields the host actually emits (``member_index``,
    ``transaction_member_count``, ``method``, ``object_id``), not by a
    synthetic operation type — one aggregate callable does not mean one
    resolved record.
    """

    def fail(detail: str) -> EditorialTransactionWorkflowError:
        return _invalid(detail, REASON_MANIFEST_INVALID)

    # 1. one manifest + one admitted apply counterpart
    manifest = _admitted_manifest(payload, TRANSACTION_TOOL, fail)

    # 2. exact intent sequence
    intent = manifest.intent_parameters
    if intent.get("sequence_name") != proposal["sequence_name"]:
        raise fail("manifest intent targets a different sequence")

    # 3. intent entries are EXACTLY the freshly authorized realization deltas
    held_entries = [dict(entry) for entry in entries]
    if intent.get("entries") != held_entries:
        raise _invalid(
            "manifest entries differ from the fresh realization deltas",
            REASON_MANIFEST_DRIFT,
        )

    # 4. those entries came from the proposal's held delta set. The
    #    delta-set fingerprint is computed over the TimelineDeltas (the
    #    realization's own arithmetic), not over the unwrapped entries.
    if canonical_fingerprint(
        [dict(delta) for delta in deltas]
    ) != proposal["delta_set_fingerprint"]:
        raise _invalid(
            "manifest entries drifted from the held delta set",
            REASON_MANIFEST_DRIFT,
        )

    # 5. one host change record per member
    count = _command_count(proposal)
    payloads = _member_payloads(payload.get("resolved_plan"), count, fail)

    # 6. ordered membership, matching member counts, proposal method order,
    #    and one continuous object identity
    if [member.get("member_index") for member in payloads] != list(range(count)):
        raise fail("manifest members are not ordered 0..n-1")
    if any(
        member.get("transaction_member_count") != count for member in payloads
    ):
        raise fail("manifest members disagree on the transaction member count")
    operations = [
        str(step["operation"]) for step in proposal["step_plan"]["steps"]
    ]
    if [member.get("method") for member in payloads] != operations:
        raise _invalid(
            "manifest member methods do not preserve the proposal order",
            REASON_MANIFEST_DRIFT,
        )
    object_ids = {member.get("object_id") for member in payloads}
    if len(object_ids) != 1 or not next(iter(object_ids)):
        raise _invalid(
            "manifest members do not name one continuous object",
            REASON_MANIFEST_DRIFT,
        )


def _verify_restore_manifest(
    payload: Mapping[str, Any],
    *,
    sequence_name: Optional[str],
    recovery: Mapping[str, Any],
    command_count: int,
) -> None:
    """Prove the fresh restore manifest replays THIS persisted token.

    Same standard five-key manifest shape as the forward rail. Its
    ``resolved_plan`` carries one member record per reverse step, with ordered
    ``member_index`` and REVERSED ``source_member_index``.
    """

    def fail(detail: str) -> Exception:
        return _DiscoveryDrift(detail)

    manifest = _admitted_manifest(payload, TRANSACTION_RESTORE_TOOL, fail)

    intent = manifest.intent_parameters
    if intent.get("sequence_name") != sequence_name:
        raise _DiscoveryDrift("restore manifest sequence mismatch")
    if intent.get("recovery") != dict(recovery):
        # Bridge hands the token back verbatim; anything else is drift.
        raise _DiscoveryDrift("restore manifest token mismatch")

    payloads = _member_payloads(
        payload.get("resolved_plan"), command_count, fail
    )
    if [member.get("member_index") for member in payloads] != list(
        range(command_count)
    ):
        raise _DiscoveryDrift("restore members are not ordered 0..n-1")
    if [member.get("source_member_index") for member in payloads] != list(
        reversed(range(command_count))
    ):
        raise _DiscoveryDrift("restore members do not reverse the forward order")
    if any(
        member.get("transaction_member_count") != command_count
        for member in payloads
    ):
        raise _DiscoveryDrift("restore members disagree on the member count")
    if any(
        member.get("recovery_fingerprint") != recovery.get("fingerprint")
        for member in payloads
    ):
        raise _DiscoveryDrift("restore members do not bind the held token")


# --------------------------------------------------------------------------- #
# Commit-outcome readers
# --------------------------------------------------------------------------- #
def _apply_result(outcome: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    commit_result = outcome.get("commit_result")
    if not isinstance(commit_result, Mapping):
        return None
    apply_result = commit_result.get("apply_result")
    return dict(apply_result) if isinstance(apply_result, Mapping) else None


def _transaction_disposition(
    outcome: Mapping[str, Any], command_count: int
) -> str:
    """What the HOST says happened to the transaction on a successful commit.

    The real successful forward payload is TOP-LEVEL
    ``{ok: true, status: "applied", applied: <n>, results: [...],
    recovery: <token>}`` — there is no ``transaction_apply`` wrapper. Host
    ``status="applied"`` with a full member count maps to workflow
    ``committed``.

    ponytail ceiling (evidence, not inference): Bridge reports only what the
    apply result carries. It cannot re-read the host, so it never certifies a
    rollback on its own authority — ``compensated`` here means "the host
    reported a compensated transaction", nothing stronger. A missing or
    unreadable disposition is ``unknown``, never a silent success.

    NB: the released Pipeline path does not currently reach the ``compensated``
    branch. A native compensated failure carries verified host evidence but
    ALSO ``ok: false`` + ``error``, so ``CommitBoundary`` classifies it as an
    apply failure and discards the body — see ``_failure_patch``. The branch is
    kept because it is the correct reading if Pipeline ever ships a successful
    terminal compensation envelope. ``flame.editorial.transaction_compensation_plan``
    is PREFLIGHT authority only and must never be used to infer that
    compensation actually ran.
    """
    apply_result = _apply_result(outcome)
    if apply_result is None or apply_result.get("ok") is not True:
        return "unknown"
    status = apply_result.get("status")
    if status == "applied":
        if apply_result.get("applied") != command_count:
            return "failed"
        return "committed"
    if status == "compensated":
        return "compensated"
    if status == "compensation_failed":
        return "failed"
    return "unknown"


def _failure_patch(
    reason_code: str, outcome: Mapping[str, Any]
) -> dict[str, Any]:
    """The honest transaction disposition after a FAILED commit.

    ponytail ceiling: ``ASSENT_INVALID`` is the only ``CommitBoundary`` code
    that proves nothing was dispatched. Every other failure discards the host
    apply payload at the boundary, so Bridge reports ``unknown`` rather than
    guessing whether the host compensated. Restore stays unavailable either
    way — there is no trusted recovery token.
    """
    commit_reason_code = outcome.get("commit_reason_code")
    dispatched = commit_reason_code not in {"ASSENT_INVALID", None}
    return {
        "status": "failed",
        "reason_code": reason_code,
        "transaction_status": "unknown" if dispatched else "not_started",
        "restore_availability": (
            "unavailable" if dispatched else "not_applicable"
        ),
    }


# The real schema-1 token's exact closed key set.
RECOVERY_TOKEN_FIELDS: frozenset[str] = frozenset({
    "kind",
    "schema_version",
    "sequence_name",
    "applied_member_count",
    "reverse_steps",
    "baseline_identity",
    "final_identity",
    "object_id",
    "baseline_state",
    "final_state",
    "resolved_plan_fingerprint",
    "fingerprint",
})


def _extract_transaction_recovery(
    outcome: Mapping[str, Any],
    sequence_name: Optional[str],
    command_count: int,
) -> Optional[dict[str, Any]]:
    """The single closed ``flame.editorial.temporal_transaction_recovery``.

    Returned at TOP-LEVEL ``apply_result.recovery`` — the member ``results``
    list beside it carries one row per transaction member, so the token is not
    inside ``results[0]``. The token has NO ``method`` field (its
    ``reverse_steps`` rows do).

    Kind, schema, sequence, closed key set, member count, reverse-step order,
    required state/identity fields, and the token's own canonical fingerprint
    are all validated; the body is otherwise opaque to Bridge and is persisted
    byte-for-byte. Never reconstructed.
    """
    token = extract_recovery_token(
        outcome,
        sequence_name,
        results_index=None,
        schema_version=RECOVERY_TOKEN_SCHEMA_VERSION,
        kind=RECOVERY_TOKEN_KIND,
        truthy_keys=("object_id", "resolved_plan_fingerprint"),
        required_keys=tuple(sorted(RECOVERY_TOKEN_FIELDS)),
    )
    if token is None or not _is_valid_transaction_token(token, command_count):
        return None
    return token


def _is_valid_transaction_token(token: Mapping[str, Any], count: int) -> bool:
    if set(token) != RECOVERY_TOKEN_FIELDS:
        return False
    if token.get("applied_member_count") != count:
        return False
    for field in (
        "baseline_identity",
        "final_identity",
        "baseline_state",
        "final_state",
    ):
        if not isinstance(token.get(field), dict) or not token[field]:
            return False
    steps = token.get("reverse_steps")
    if not isinstance(steps, list) or len(steps) != count:
        return False
    if not all(isinstance(step, dict) for step in steps):
        return False
    # Reverse steps undo the members in reverse order.
    if [step.get("source_member_index") for step in steps] != list(
        reversed(range(count))
    ):
        return False
    if any(not step.get("method") for step in steps):
        return False
    body = {key: value for key, value in token.items() if key != "fingerprint"}
    return canonical_fingerprint(body) == token.get("fingerprint")


def _restore_evidence(
    outcome: Mapping[str, Any],
    *,
    command_count: int,
    token_fingerprint: Optional[str],
) -> Optional[dict[str, Any]]:
    """Trusted host evidence from a successful restore commit, else ``None``.

    The real successful restore payload is TOP-LEVEL
    ``{ok: true, status: "restored", restored: <n>, results: [...],
    baseline_state: {...}, baseline_mismatches: [], recovery_fingerprint: ...}``.

    The echoed ``recovery_fingerprint`` is a real identity fence: it is the
    token's OWN ``fingerprint`` field (the host's digest over the token minus
    that field), NOT Bridge's ``recovery_token_fingerprint`` (Bridge's digest
    over the whole persisted token, which is its separate tamper fence). The
    two are deliberately different values over different bodies; comparing the
    wrong pair would fail every honest restore.
    """
    apply_result = _apply_result(outcome)
    if apply_result is None or apply_result.get("ok") is not True:
        return None
    if apply_result.get("status") != "restored":
        return None
    if apply_result.get("restored") != command_count:
        return None
    if apply_result.get("baseline_mismatches") != []:
        return None
    if apply_result.get("recovery_fingerprint") != token_fingerprint:
        return None
    baseline_state = apply_result.get("baseline_state")
    if not isinstance(baseline_state, dict) or not baseline_state:
        return None
    return {
        "baseline_state": dict(baseline_state),
        "recovery_fingerprint": apply_result["recovery_fingerprint"],
    }


def _terminal_baseline(
    outcome: Mapping[str, Any], evidence: Mapping[str, Any]
) -> tuple[str, bool]:
    """``(terminal_baseline_fingerprint, is_whole_state)``.

    Only a WHOLE-state digest is comparable to the proposal's
    ``source_state_fingerprint``; the caller sets
    ``terminal_baseline_verified`` from that comparison, and never from a
    segment-scope digest.

    ponytail ceiling: the host verifies the exact SEGMENT baseline before it
    returns success, and reports that segment state as ``baseline_state``. It
    does NOT currently report a whole-``EditState`` readback, so there is
    nothing comparable to the proposal's whole-state ``source_state_fingerprint``
    and ``terminal_baseline_verified`` is honestly ``False`` on every restore
    today. The fingerprint field carries the canonical digest of the
    host-reported segment baseline so a consumer has grounded evidence rather
    than a null; the boolean is what flips if and when Pipeline ships a fresh
    whole-state readback (the comparison below is already written for it).
    """
    apply_result = _apply_result(outcome) or {}
    reported = apply_result.get("terminal_state_fingerprint")
    if is_sha256(reported):
        return str(reported), True
    return canonical_fingerprint(evidence["baseline_state"]), False


# --------------------------------------------------------------------------- #
# Receipts
# --------------------------------------------------------------------------- #
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
    applied = status in {"applied", "restored"}
    restored = status == "restored"
    replayed = action == "replay" and applied
    dispatch_authorized = status in {"applied", "restored"}

    receipt: dict[str, Any] = {
        "kind": RECEIPT_KIND,
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "action": action,
        "status": status,
        "trust_status": _trust_status(status),
        "workflow_id": workflow["workflow_id"],
        "proposal_id": workflow["proposal_id"],
        "proposal_fingerprint": workflow["proposal_fingerprint"],
        "preview_id": workflow["preview_id"],
        "preview_authority_fingerprint": workflow[
            "preview_authority_fingerprint"
        ],
        "preview_fingerprint": workflow["preview_fingerprint"],
        "interaction_fingerprint": workflow["interaction_fingerprint"],
        "source_fingerprint": workflow["source_fingerprint"],
        "source_state_fingerprint": workflow["source_state_fingerprint"],
        "final_state_fingerprint": workflow["final_state_fingerprint"],
        "step_plan_fingerprint": workflow["step_plan_fingerprint"],
        "semantic_capability_plan_fingerprint": workflow[
            "semantic_capability_plan_fingerprint"
        ],
        "pure_apply_fingerprint": workflow["pure_apply_fingerprint"],
        "delta_set_fingerprint": workflow["delta_set_fingerprint"],
        "realization_plan_fingerprint": workflow[
            "realization_plan_fingerprint"
        ],
        "command_count": int(workflow["command_count"]),
        # Immutable forward manifest + assent identity, never rewritten by
        # the restore rail.
        "manifest_fingerprint": workflow["forward_manifest_fingerprint"],
        "assent_record_id": workflow["forward_assent_record_id"],
        "dispatch_authorized": dispatch_authorized,
        "applied": applied,
        "replayed": replayed,
        "restored": restored,
        "reason_code": reason_code
        or (
            workflow.get("reason_code")
            if status in {"failed", "unavailable"}
            else None
        ),
    }
    if proposed_view:
        # The IMMUTABLE original projection: an exact duplicate propose keeps
        # returning byte-identical bytes even after the workflow advances.
        receipt.update({
            "assent_status": "proposed",
            "commit_fingerprint": None,
            "transaction_status": "not_started",
            "recovery_token_fingerprint": None,
            "restore_availability": "not_applicable",
            "restore_manifest_fingerprint": None,
            "restore_assent_record_id": None,
            "restore_assent_status": None,
            "restore_commit_fingerprint": None,
            "terminal_baseline_fingerprint": None,
            "terminal_baseline_verified": False,
            "replay_observations": 0,
            "reason_code": None,
        })
    else:
        receipt.update({
            "assent_status": workflow.get("forward_assent_status"),
            "commit_fingerprint": workflow.get("forward_commit_fingerprint"),
            "transaction_status": (
                workflow.get("transaction_status") or "not_started"
            ),
            "recovery_token_fingerprint": workflow.get(
                "recovery_token_fingerprint"
            ),
            "restore_availability": workflow.get("restore_availability")
            or "not_applicable",
            "restore_manifest_fingerprint": workflow.get(
                "restore_manifest_fingerprint"
            ),
            "restore_assent_record_id": workflow.get(
                "restore_assent_record_id"
            ),
            "restore_assent_status": workflow.get("restore_assent_status"),
            "restore_commit_fingerprint": workflow.get(
                "restore_commit_fingerprint"
            ),
            "terminal_baseline_fingerprint": workflow.get(
                "terminal_baseline_fingerprint"
            ),
            "terminal_baseline_verified": bool(
                workflow.get("terminal_baseline_verified")
            ),
            # (c) Inside the fingerprinted set: a receipt is a per-action
            # value, not a workflow identity.
            "replay_observations": int(
                workflow.get("replay_observations", 0) or 0
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
    """Fail closed on any invariant a caller could otherwise leak."""
    status = receipt["status"]
    if receipt["transaction_status"] not in _TRANSACTION_STATUSES:
        raise ValueError("receipt transaction_status is unsupported")
    if receipt["restore_availability"] not in _RESTORE_AVAILABILITY:
        raise ValueError("receipt restore_availability is unsupported")
    if receipt["reason_code"] is not None and receipt[
        "reason_code"
    ] not in _REASON_CODES:
        raise ValueError("receipt reason_code is unsupported")
    if receipt["command_count"] < MIN_COMMANDS or receipt[
        "command_count"
    ] > MAX_COMMANDS:
        raise ValueError("receipt command_count is outside the admitted range")
    if receipt["replay_observations"] < 0:
        raise ValueError("receipt replay_observations must not be negative")
    # NB: "proposed" is deliberately NOT bound to the "propose" action — a
    # status poll on an unratified workflow is a healthy pre-ratification
    # projection (#242 correction 1, accepted by Pipeline).
    if status == "proposed" and (
        receipt["dispatch_authorized"]
        or receipt["applied"]
        or receipt["replayed"]
        or receipt["restored"]
        or receipt["transaction_status"] != "not_started"
        or receipt["commit_fingerprint"] is not None
        or receipt["recovery_token_fingerprint"] is not None
    ):
        raise ValueError("proposed receipt contains contradictory state")
    if status == "applied" and (
        not receipt["applied"]
        or receipt["restored"]
        or receipt["transaction_status"] != "committed"
        or receipt["commit_fingerprint"] is None
        or not receipt["dispatch_authorized"]
    ):
        raise ValueError("applied receipt lacks committed transaction evidence")
    if status == "restored" and (
        not receipt["restored"]
        or receipt["transaction_status"] != "restored"
        or receipt["restore_commit_fingerprint"] is None
        or receipt["restore_assent_record_id"] is None
        or receipt["restore_manifest_fingerprint"] is None
        or receipt["restore_manifest_fingerprint"]
        == receipt["manifest_fingerprint"]
        or receipt["restore_assent_record_id"] == receipt["assent_record_id"]
        or receipt["commit_fingerprint"] is None
    ):
        raise ValueError("restored receipt lacks separate restore evidence")
    if receipt["replayed"] and (
        receipt["action"] != "replay" or not receipt["applied"]
    ):
        raise ValueError("replayed receipt is contradictory")
    if receipt["terminal_baseline_verified"] and (
        receipt["terminal_baseline_fingerprint"]
        != receipt["source_state_fingerprint"]
    ):
        raise ValueError("verified terminal baseline is not the source state")
    for key, value in receipt.items():
        if isinstance(value, (dict, list)):
            raise ValueError(f"receipt field {key} carries a structured body")


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


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
async def _maybe_await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def _operation_data(result: Any) -> Optional[dict[str, Any]]:
    """The data mapping of a successful operation result, else ``None``.

    Accepts an operation result object/mapping carrying ``status`` + ``data``,
    or a raw realization payload (which carries its own ``status: ready``, so
    the envelope is detected by the ``data`` mapping, never by ``status``).
    """
    data = _field(result, "data")
    if isinstance(data, Mapping):
        status = _field(result, "status")
        status_value = str(getattr(status, "value", status or "")).casefold()
        if status_value and status_value not in {"succeeded", "success", "ok"}:
            return None
        return dict(data)
    if isinstance(result, Mapping):
        return dict(result)
    return None


def _field(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _tool_names(available: Any) -> set[str]:
    return {
        str(getattr(tool, "name", None))
        for tool in available
        if getattr(tool, "name", None)
    }


__all__ = [
    "ADMITTED_COMMAND_SHAPES",
    "RECOVERY_TOKEN_FIELDS",
    "AssentGateway",
    "EditorialTransactionWorkflowAPI",
    "EditorialTransactionWorkflowError",
    "InMemoryAssentGateway",
    "InMemoryEditorialTransactionWorkflowStore",
    "MAX_COMMANDS",
    "MIN_COMMANDS",
    "PROPOSAL_KIND",
    "RECEIPT_KIND",
    "RECOVERY_TOKEN_KIND",
    "SessionFactoryAssentGateway",
    "SessionFactoryEditorialTransactionWorkflowStore",
    "TRANSACTION_REALIZATION_OPERATION_TYPE",
    "TRANSACTION_RESTORE_TOOL",
    "TRANSACTION_TOOL",
    "WORKFLOW_KIND",
    "make_editorial_transaction_workflow_api",
    "transaction_entries",
    "realization_deltas",
    "realization_discovery_params",
    "restore_discovery_arguments",
    "transaction_discovery_arguments",
]
