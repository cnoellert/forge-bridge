"""Deterministic host-graph selection over sibling-declared affordances."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from forge_bridge.composition.admission import AdmissionRejected, admit_operator


HOST_GRAPH_CAPABILITY_ID = "forge_pipeline.host_graph.operations"
HOST_GRAPH_PLANNER_INVENTORY_KIND = "pipeline.host_graph.planner_inventory"

DecisionStatus = Literal["selected", "refused"]


class PlannerInventoryError(ValueError):
    """A sibling planner declaration is absent or structurally invalid."""


@dataclass(frozen=True)
class HostGraphPlannerDecision:
    """Serializable deterministic selection or fail-closed refusal evidence."""

    status: DecisionStatus
    trust_status: str
    intent: str
    reason_code: str
    message: str
    selected_operation_types: tuple[str, ...] = ()
    operator_sequence: tuple[dict[str, Any], ...] = ()
    candidates: tuple[str, ...] = ()
    execution_ready: bool = False
    review_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "bridge.host_graph.planner_decision",
            "schema_version": 1,
            "status": self.status,
            "trust_status": self.trust_status,
            "intent": self.intent,
            "reason_code": self.reason_code,
            "message": self.message,
            "selected_operation_types": list(self.selected_operation_types),
            "operator_sequence": [deepcopy(row) for row in self.operator_sequence],
            "candidates": list(self.candidates),
            "execution_ready": self.execution_ready,
            "review_required": self.review_required,
            "edge_value_semantics": "whole_operation_output",
            "from_port": "reserved",
        }


def host_graph_planner_inventory(tool_registry: Any) -> dict[str, Any]:
    """Read Pipeline's declaration from ToolRegistry without changing admission."""

    registration = tool_registry.get(HOST_GRAPH_CAPABILITY_ID)
    if registration is None:
        raise PlannerInventoryError(
            f"capability {HOST_GRAPH_CAPABILITY_ID!r} is not registered"
        )
    capabilities = registration.capabilities
    if not isinstance(capabilities, Mapping):
        raise PlannerInventoryError("host graph capability metadata must be a mapping")
    inventory = capabilities.get("planner_inventory")
    if not isinstance(inventory, Mapping):
        raise PlannerInventoryError("host graph planner_inventory is not declared")
    if inventory.get("kind") != HOST_GRAPH_PLANNER_INVENTORY_KIND:
        raise PlannerInventoryError("host graph planner_inventory kind is invalid")
    if inventory.get("grants_execution_authority") is not False:
        raise PlannerInventoryError("planner inventory must not grant execution authority")
    if inventory.get("discovery_only") is not True:
        raise PlannerInventoryError("planner inventory must be discovery-only")
    if inventory.get("automatic_mutation_admission") is not False:
        raise PlannerInventoryError("planner inventory must disable automatic admission")
    if inventory.get("edge_value_semantics") != "whole_operation_output":
        raise PlannerInventoryError("planner inventory must preserve whole outputs")
    if inventory.get("from_port") != "reserved":
        raise PlannerInventoryError("planner inventory must keep from_port reserved")
    operations = inventory.get("operations")
    profiles = inventory.get("profiles")
    if not _mapping_sequence(operations) or not _mapping_sequence(profiles):
        raise PlannerInventoryError(
            "planner inventory requires operation and profile declarations"
        )
    return deepcopy(dict(inventory))


def select_host_graph_plan(
    tool_registry: Any,
    request: Mapping[str, Any],
    *,
    live_sessions: Sequence[Mapping[str, Any]],
    require_execution: bool = False,
) -> HostGraphPlannerDecision:
    """Select semantic-first host-graph operations or refuse deterministically."""

    inventory = host_graph_planner_inventory(tool_registry)
    intent = str(request.get("intent") or "").strip()
    scope = request.get("scope")
    if not intent or not isinstance(scope, Mapping):
        return _refusal(
            intent,
            "invalid_request",
            "intent and exact scope are required",
        )
    dcc = str(scope.get("dcc") or "").strip()
    graph_kind = str(scope.get("graph_kind") or "").strip()
    if not dcc or not graph_kind:
        return _refusal(
            intent,
            "invalid_scope",
            "scope requires non-empty dcc and graph_kind",
        )

    profiles = [dict(row) for row in inventory["profiles"]]
    dcc_profiles = [row for row in profiles if _same(row.get("dcc"), dcc)]
    if not dcc_profiles:
        return _refusal(
            intent,
            "dcc_unavailable",
            f"no declared host-graph adapter is loaded for {dcc!r}",
            candidates=sorted(str(row.get("dcc") or "") for row in profiles),
        )
    scope_profiles = [
        row for row in dcc_profiles if graph_kind in (row.get("graph_kinds") or [])
    ]
    if not scope_profiles:
        return _refusal(
            intent,
            "unsupported_graph_scope",
            f"{dcc!r} does not declare graph scope {graph_kind!r}",
            candidates=sorted(
                {
                    str(kind)
                    for row in dcc_profiles
                    for kind in row.get("graph_kinds") or []
                }
            ),
        )
    trusted_profiles = [
        row for row in scope_profiles if row.get("proof_status") == "trusted"
    ]
    if not trusted_profiles:
        return _refusal(
            intent,
            "capability_not_trusted",
            f"{dcc}:{graph_kind} has no trusted capability proof",
            candidates=sorted(
                {str(row.get("proof_status") or "unknown") for row in scope_profiles}
            ),
        )
    if not _matching_session(scope, live_sessions):
        return _refusal(
            intent,
            "session_not_live",
            "the exact requested DCC session is not live",
            candidates=_session_candidates(dcc, live_sessions),
        )

    operations = [dict(row) for row in inventory["operations"]]
    candidates = [
        row
        for row in operations
        if intent in (row.get("planner_intents") or [])
        and _operation_supports(row, dcc, graph_kind)
    ]
    if not candidates:
        available_intents = sorted(
            {
                str(value)
                for row in operations
                if _operation_supports(row, dcc, graph_kind)
                for value in row.get("planner_intents") or []
            }
        )
        return _refusal(
            intent,
            "intent_unsupported",
            f"no declared operation satisfies intent {intent!r} in this scope",
            candidates=available_intents,
        )

    candidates.sort(
        key=lambda row: (
            int(row.get("selection_priority", 1000)),
            str(row.get("operation_type") or ""),
        )
    )
    try:
        selected, sequence, node_type_error = _selection(
            intent,
            request,
            scope,
            candidates,
            trusted_profiles,
        )
    except PlannerInventoryError as exc:
        return _refusal(intent, "invalid_request", str(exc))
    if node_type_error is not None:
        return node_type_error

    unadmitted = tuple(
        operator_id for operator_id in _sequence_operator_ids(sequence)
        if not _admitted(operator_id)
    )
    if require_execution and unadmitted:
        return _refusal(
            intent,
            "unadmitted_mutation",
            "selected mutation atoms are discoverable but not admitted to execution",
            candidates=unadmitted,
        )
    execution_ready = not unadmitted
    return HostGraphPlannerDecision(
        status="selected",
        trust_status="trusted" if execution_ready else "review_required",
        intent=intent,
        reason_code="semantic_selected" if candidates[0].get("selection_class") == "semantic" else "atomic_selected",
        message=(
            "selected the highest-priority declared semantic operation"
            if candidates[0].get("selection_class") == "semantic"
            else "selected explicitly requested declared atomic operations"
        ),
        selected_operation_types=selected,
        operator_sequence=tuple(sequence),
        candidates=tuple(
            str(row.get("operation_type") or "") for row in candidates
        ),
        execution_ready=execution_ready,
        review_required=bool(unadmitted),
    )


def _selection(
    intent: str,
    request: Mapping[str, Any],
    scope: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
) -> tuple[tuple[str, ...], list[dict[str, Any]], HostGraphPlannerDecision | None]:
    if intent == "canonical_shot_output_graph":
        if candidates[0].get("selection_class") != "semantic":
            if request.get("nodes") and request.get("connection"):
                operations = (
                    "pipeline.host_graph.ensure_node",
                    "pipeline.host_graph.connect",
                )
                return operations, _atomic_sequence(request, scope), None
            return (), [], _refusal(
                intent,
                "semantic_operation_unavailable",
                "canonical output intent has no semantic operation and lacks explicit atomic details",
                candidates=tuple(
                    str(row.get("operation_type") or "") for row in candidates
                ),
            )
        operation_type = str(candidates[0]["operation_type"])
        return (
            (operation_type,),
            _canonical_sequence(request, scope),
            None,
        )
    if intent in {"inspect_node_types", "describe_node_type"}:
        node_type = str(request.get("node_type") or "").strip()
        selected = ["pipeline.host_graph.list_node_types"]
        if node_type:
            canonical, error = _resolve_node_type(
                node_type,
                profiles,
                scope,
                intent=intent,
                evidence=request.get("node_type_evidence"),
            )
            if error is not None:
                return (), [], error
            selected.append("pipeline.host_graph.describe_node_type")
            return (
                tuple(selected),
                _read_sequence(scope, node_type=canonical),
                None,
            )
        return tuple(selected), _read_sequence(scope), None
    if intent == "inspect_graph":
        return (
            ("pipeline.host_graph.inspect",),
            _single_read_sequence("pipeline.host_graph.inspect", scope),
            None,
        )
    if intent == "ensure_and_connect":
        nodes = request.get("nodes")
        connection = request.get("connection")
        if (
            not _mapping_sequence(nodes)
            or not nodes
            or not isinstance(connection, Mapping)
        ):
            return (), [], _refusal(
                intent,
                "invalid_atomic_request",
                "ensure_and_connect requires nodes and one exact connection",
            )
        for node in nodes:
            if isinstance(node, Mapping) and node.get("native_type"):
                _, error = _resolve_node_type(
                    str(node["native_type"]),
                    profiles,
                    scope,
                    intent=intent,
                    evidence=request.get("node_type_evidence"),
                )
                if error is not None:
                    return (), [], error
        operations = (
            "pipeline.host_graph.ensure_node",
            "pipeline.host_graph.connect",
        )
        return operations, _atomic_sequence(request, scope), None
    if intent == "ensure_node":
        node = request.get("node")
        if not isinstance(node, Mapping):
            return (), [], _refusal(
                intent,
                "invalid_atomic_request",
                "ensure_node requires one exact node declaration",
            )
        _, error = _resolve_node_type(
            str(node.get("native_type") or ""),
            profiles,
            scope,
            intent=intent,
            evidence=request.get("node_type_evidence"),
        )
        if error is not None:
            return (), [], error
        values = dict(request)
        values["nodes"] = [dict(node)]
        return (
            ("pipeline.host_graph.ensure_node",),
            _atomic_sequence(values, scope),
            None,
        )
    if intent == "connect_nodes":
        if not isinstance(request.get("connection"), Mapping):
            return (), [], _refusal(
                intent,
                "invalid_atomic_request",
                "connect_nodes requires one exact connection declaration",
            )
        return (
            ("pipeline.host_graph.connect",),
            _atomic_sequence(request, scope),
            None,
        )
    operation_type = str(candidates[0]["operation_type"])
    if candidates[0].get("effect_class") == "host_mutation":
        return (), [], _refusal(
            intent,
            "unadmitted_mutation",
            "the declared mutation has no reviewed planner compiler",
            candidates=(operation_type,),
        )
    return (
        (operation_type,),
        _single_read_sequence(operation_type, scope),
        None,
    )


def _canonical_sequence(
    planner_request: Mapping[str, Any],
    scope: Mapping[str, Any],
) -> list[dict[str, Any]]:
    semantic = planner_request.get("semantic_request")
    if not isinstance(semantic, Mapping):
        raise PlannerInventoryError(
            "canonical_shot_output_graph requires semantic_request"
        )
    required = ("canonical", "shot", "task", "role", "stream", "dcc")
    missing = [name for name in required if not semantic.get(name)]
    if missing:
        raise PlannerInventoryError(
            f"semantic_request is missing {', '.join(missing)}"
        )
    if dict(semantic.get("target_graph") or {}) != dict(scope):
        raise PlannerInventoryError(
            "semantic_request.target_graph must exactly match scope"
        )
    config_path = planner_request.get("config_path")
    current_args = {
        name: semantic[name] for name in ("canonical", "shot", "task", "dcc", "stream")
    }
    plan_args: dict[str, Any] = {"request": dict(semantic)}
    if config_path:
        current_args["config_path"] = str(config_path)
        plan_args["config_path"] = str(config_path)
    return [
        _step(
            "pipeline.shot_resource.current",
            current_args,
            "planner:shot-current",
            "pipeline.shot_resource.current_result",
        ),
        _step(
            "pipeline.host_graph.inspect",
            {"scope": dict(scope)},
            "planner:host-snapshot",
            "pipeline.host_graph.snapshot",
        ),
        _step(
            "pipeline.shot_output_graph.plan",
            plan_args,
            "planner:shot-output-plan",
            "pipeline.shot_output_graph.plan_result",
            inputs=[
                _input("planner:shot-current", "pipeline.shot_resource.current_result", "stream_context"),
                _input("planner:host-snapshot", "pipeline.host_graph.snapshot", "host_graph_snapshot"),
            ],
        ),
        _step(
            "commit",
            {},
            "planner:commit",
            "commit_result",
            effect_class="host_mutation",
            state_owner="dcc_host",
            inputs=[
                _input("planner:shot-output-plan", "mutation_plan", "held")
            ],
        ),
        _step(
            "pipeline.host_graph.verify",
            {"scope": dict(scope)},
            "planner:verification",
            "pipeline.host_graph.verification_receipt",
            inputs=[
                _input("planner:shot-output-plan", "pipeline.shot_output_graph.plan_result", "expectations"),
                _input("planner:commit", "commit_result", "apply_receipt"),
            ],
        ),
    ]


def _read_sequence(
    scope: Mapping[str, Any],
    *,
    node_type: str = "",
) -> list[dict[str, Any]]:
    sequence = _single_read_sequence("pipeline.host_graph.list_node_types", scope)
    if node_type:
        sequence.extend(
            _single_read_sequence(
                "pipeline.host_graph.describe_node_type",
                scope,
                extra={"node_type": node_type},
                suffix="describe",
            )
        )
    return sequence


def _single_read_sequence(
    operation_type: str,
    scope: Mapping[str, Any],
    *,
    extra: Mapping[str, Any] | None = None,
    suffix: str = "read",
) -> list[dict[str, Any]]:
    arguments = {"scope": dict(scope), **dict(extra or {})}
    return [
        _step(
            operation_type,
            arguments,
            f"planner:{suffix}:{operation_type}",
            "pipeline.host_graph.operation_result",
        )
    ]


def _atomic_sequence(
    request: Mapping[str, Any],
    scope: Mapping[str, Any],
) -> list[dict[str, Any]]:
    nodes = [dict(row) for row in request.get("nodes") or [] if isinstance(row, Mapping)]
    connection = request.get("connection")
    sequence = [
        _step(
            "forge_host_graph_ensure_node",
            {
                "target": dict(request.get("target") or {}),
                "scope": dict(scope),
                "node": node,
                "mode": "discover",
            },
            f"planner:ensure:{index}",
            "pipeline.host_graph.mutation_plan",
            effect_class="mutation_plan_authoring",
        )
        for index, node in enumerate(nodes)
    ]
    if isinstance(connection, Mapping):
        sequence.append(
            _step(
                "forge_host_graph_connect",
                {
                    "target": dict(request.get("target") or {}),
                    "scope": dict(scope),
                    "connection": dict(connection),
                    "mode": "discover",
                },
                "planner:connect",
                "pipeline.host_graph.mutation_plan",
                effect_class="mutation_plan_authoring",
            )
        )
    return sequence


def _step(
    operator_id: str,
    arguments: Mapping[str, Any],
    output_id: str,
    output_type: str,
    *,
    effect_class: str = "read",
    state_owner: str = "read_only",
    inputs: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "operator_id": operator_id,
        "effect_class": effect_class,
        "state_owner": state_owner,
        "arguments": dict(arguments),
        "inputs": [dict(row) for row in inputs],
        "output_artifact_id": output_id,
        "output_artifact_type": output_type,
    }


def _input(artifact_id: str, artifact_type: str, role: str) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "metadata": {"role": role},
    }


def _resolve_node_type(
    query: str,
    profiles: Sequence[Mapping[str, Any]],
    scope: Mapping[str, Any],
    *,
    intent: str,
    evidence: Any = None,
) -> tuple[str, HostGraphPlannerDecision | None]:
    graph_kind = str(scope.get("graph_kind") or "")
    node_types = [
        dict(row)
        for profile in profiles
        for row in profile.get("node_types") or []
        if isinstance(row, Mapping) and graph_kind in (row.get("graph_kinds") or [])
    ]
    if evidence is not None:
        evidence_rows, evidence_error = _node_type_evidence(
            evidence,
            scope,
            intent=intent,
        )
        if evidence_error is not None:
            return "", evidence_error
        node_types.extend(evidence_rows)
    unique: dict[str, dict[str, Any]] = {}
    for row in node_types:
        native_type = str(row.get("native_type") or "")
        if native_type:
            unique.setdefault(native_type, row)
    node_types = list(unique.values())
    exact = [row for row in node_types if row.get("native_type") == query]
    if len(exact) == 1:
        return query, None
    matches = [
        row
        for row in node_types
        if _same(row.get("native_type"), query)
        or _same(row.get("display_name"), query)
    ]
    native_types = sorted({str(row.get("native_type") or "") for row in matches})
    if len(native_types) == 1:
        return native_types[0], None
    if len(native_types) > 1:
        return "", _refusal(
            intent,
            "ambiguous_node_type",
            f"node type {query!r} matches multiple native types",
            candidates=native_types,
        )
    return "", _refusal(
        intent,
        "unsupported_node_type",
        f"node type {query!r} is not declared in this graph scope",
        candidates=sorted(
            {str(row.get("native_type") or "") for row in node_types}
        ),
    )


def _node_type_evidence(
    evidence: Any,
    scope: Mapping[str, Any],
    *,
    intent: str,
) -> tuple[list[dict[str, Any]], HostGraphPlannerDecision | None]:
    if not isinstance(evidence, Mapping):
        return [], _refusal(
            intent,
            "node_type_evidence_invalid",
            "node type evidence must be a trusted operation result",
        )
    trust_status = str(evidence.get("trust_status") or "")
    if trust_status != "trusted":
        return [], _refusal(
            intent,
            "node_type_evidence_not_trusted",
            "node type evidence must carry trusted fresh host proof",
            candidates=(trust_status or "missing",),
        )
    payload = evidence.get("result")
    if not isinstance(payload, Mapping):
        payload = evidence
    rows = payload.get("node_types")
    if not _mapping_sequence(rows):
        return [], _refusal(
            intent,
            "node_type_evidence_invalid",
            "node type evidence does not contain node_types",
        )
    dcc = str(scope.get("dcc") or "")
    graph_kind = str(scope.get("graph_kind") or "")
    compatible = [
        dict(row)
        for row in rows
        if (not row.get("dcc") or _same(row.get("dcc"), dcc))
        and (
            not row.get("graph_kinds")
            or graph_kind in (row.get("graph_kinds") or [])
        )
    ]
    return compatible, None


def _operation_supports(
    operation: Mapping[str, Any],
    dcc: str,
    graph_kind: str,
) -> bool:
    return any(
        _same(row.get("dcc"), dcc)
        and graph_kind in (row.get("graph_kinds") or [])
        and row.get("proof_status") == "trusted"
        for row in operation.get("dcc_scopes") or []
        if isinstance(row, Mapping)
    )


def _matching_session(
    scope: Mapping[str, Any],
    live_sessions: Sequence[Mapping[str, Any]],
) -> bool:
    identities = {
        key: str(scope.get(key) or "").strip()
        for key in ("session_id", "instance_id")
        if scope.get(key)
    }
    if not identities:
        return False
    for session in live_sessions:
        if not _same(session.get("dcc"), scope.get("dcc")):
            continue
        if session.get("live") is False:
            continue
        if all(str(session.get(key) or "") == value for key, value in identities.items()):
            return True
    return False


def _session_candidates(
    dcc: str,
    live_sessions: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(row.get("session_id") or row.get("instance_id") or "")
                for row in live_sessions
                if _same(row.get("dcc"), dcc) and row.get("live") is not False
            }
            - {""}
        )
    )


def _sequence_operator_ids(sequence: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(str(row.get("operator_id") or "") for row in sequence)


def _admitted(operator_id: str) -> bool:
    try:
        admit_operator(operator_id)
    except AdmissionRejected:
        return False
    return True


def _mapping_sequence(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and all(isinstance(row, Mapping) for row in value)
    )


def _same(left: Any, right: Any) -> bool:
    return str(left or "").strip().casefold() == str(right or "").strip().casefold()


def _refusal(
    intent: str,
    reason_code: str,
    message: str,
    *,
    candidates: Sequence[str] = (),
) -> HostGraphPlannerDecision:
    return HostGraphPlannerDecision(
        status="refused",
        trust_status="review_required",
        intent=intent,
        reason_code=reason_code,
        message=message,
        candidates=tuple(value for value in candidates if value),
        execution_ready=False,
        review_required=True,
    )


__all__ = [
    "HOST_GRAPH_CAPABILITY_ID",
    "HOST_GRAPH_PLANNER_INVENTORY_KIND",
    "HostGraphPlannerDecision",
    "PlannerInventoryError",
    "host_graph_planner_inventory",
    "select_host_graph_plan",
]
