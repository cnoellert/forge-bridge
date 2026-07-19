"""Bridge-owned authorization and graph shape for live editorial previews."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import hashlib
import inspect
import json
from typing import Any
from uuid import uuid4

from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.graph.ports import PortContract, PortTopology


LIVE_FLAME_READ_OPERATION_TYPE = "flame.editorial.read_edit_state"
EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE = (
    "traffik.editorial.step_capabilities"
)
EDITORIAL_APPLY_STEPS_OPERATION_TYPE = "traffik.editorial.apply_steps"
FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE = "traffik.flame_delta.host_resolve"
FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE = (
    "flame.editorial.delta_realization"
)
LIVE_FLAME_REALIZATION_DISCOVERY_KIND = (
    "bridge.live_flame.editorial_realization_discovery"
)


class LiveEditorialVerticalError(ValueError):
    """Raised before preview when held authority or graph inputs are invalid."""


async def authorize_live_flame_step_plan(
    step_plan: Mapping[str, Any],
    *,
    run_operation: Callable[..., Any],
    project_id: str | None = None,
    requested_by: str = "forge_bridge.live_editorial_vertical",
) -> dict[str, Any]:
    """Discover and hold trusted Flame authorization without mutating a host."""

    source_plan = dict(step_plan)
    source_fingerprint = _fingerprint(source_plan)
    shared = {
        "step_plan": source_plan,
        "target_plugin": "flame",
        "host_mode": "flame",
    }
    discovered = await _run_operation(
        run_operation,
        EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        params={"mode": "discover", **shared},
        idempotency_key=f"live-editorial-capability-discover:{source_fingerprint}",
        project_id=project_id,
        requested_by=requested_by,
    )
    discover_data = _successful_operation_data(discovered, label="discover")
    _validate_discovery(discover_data, source_fingerprint=source_fingerprint)

    authorized = await _run_operation(
        run_operation,
        EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        params={
            "mode": "apply",
            **shared,
            "held_step_plan_fingerprint": discover_data[
                "step_plan_fingerprint"
            ],
            "held_matrix_fingerprint": discover_data["matrix_fingerprint"],
            "held_capability_plan_fingerprint": discover_data[
                "capability_plan_fingerprint"
            ],
        },
        idempotency_key=f"live-editorial-capability-authorize:{source_fingerprint}",
        project_id=project_id,
        requested_by=requested_by,
    )
    authorization = _successful_operation_data(authorized, label="authorize")
    validate_live_flame_authorization(
        source_plan,
        authorization,
        discovered=discover_data,
    )
    return authorization


async def discover_live_flame_realization(
    step_plan: Mapping[str, Any],
    *,
    sequence_name: str,
    run_operation: Callable[..., Any],
    reel_names: Sequence[str] | None = None,
    project_id: str | None = None,
    requested_by: str = "forge_bridge.live_editorial_vertical",
    authorization_id: str | None = None,
) -> dict[str, Any]:
    """Read, apply purely, and hold exact plugin-owned realization evidence."""

    name = str(sequence_name).strip()
    if not name:
        raise LiveEditorialVerticalError("sequence_name must not be empty")
    normalized_reels = _normalize_reel_names(reel_names)
    source_plan = dict(step_plan)
    _require_single_step(source_plan)
    source_fingerprint = _fingerprint(source_plan)
    authorization_key = str(authorization_id or uuid4().hex).strip()
    if not authorization_key:
        raise LiveEditorialVerticalError("authorization_id must not be empty")

    semantic_result = await _run_operation(
        run_operation,
        EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        params={
            "mode": "discover",
            "step_plan": source_plan,
            "target_plugin": "flame",
            "host_mode": "flame",
        },
        idempotency_key=f"{authorization_key}:semantic-discover",
        project_id=project_id,
        requested_by=requested_by,
    )
    semantic = _successful_operation_data(
        semantic_result,
        label="semantic discover",
    )
    _validate_semantic_discovery(
        semantic,
        source_fingerprint=source_fingerprint,
    )

    read_params: dict[str, Any] = {"sequence_name": name}
    if normalized_reels:
        read_params["reel_names"] = normalized_reels
    if project_id is not None:
        read_params["project_id"] = project_id
    read_result = await _run_operation(
        run_operation,
        LIVE_FLAME_READ_OPERATION_TYPE,
        params=read_params,
        idempotency_key=f"{authorization_key}:live-read",
        project_id=project_id,
        requested_by=requested_by,
    )
    edit_state = _successful_operation_data(read_result, label="live read")

    apply_result = await _run_operation(
        run_operation,
        EDITORIAL_APPLY_STEPS_OPERATION_TYPE,
        params={"state": edit_state, "step_plan": source_plan},
        idempotency_key=f"{authorization_key}:apply-steps",
        project_id=project_id,
        requested_by=requested_by,
    )
    applied = _successful_operation_data(apply_result, label="pure apply_steps")

    realization_result = await _run_operation(
        run_operation,
        FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE,
        params={
            "mode": "discover",
            "step_plan": source_plan,
            "semantic_capability_plan": semantic["capability_plan"],
            "apply_result": applied,
        },
        idempotency_key=f"{authorization_key}:realization-discover",
        project_id=project_id,
        requested_by=requested_by,
    )
    realization = _successful_operation_data(
        realization_result,
        label="exact realization discover",
    )
    _validate_realization_discovery(
        realization,
        source_fingerprint=source_fingerprint,
        semantic_plan_fingerprint=str(
            semantic["capability_plan_fingerprint"]
        ),
    )
    evidence = {
        "kind": LIVE_FLAME_REALIZATION_DISCOVERY_KIND,
        "schema_version": 1,
        "authorization_id": authorization_key,
        "sequence_name": name,
        "reel_names": normalized_reels,
        "project_id": project_id,
        "step_plan_fingerprint": source_fingerprint,
        "semantic_discovery": semantic,
        "live_state_fingerprint": _fingerprint(edit_state),
        "apply_result_fingerprint": realization["apply_result_fingerprint"],
        "realization_discovery": realization,
        "status": "ready",
        "trust_status": "trusted",
        "dispatch_authorized": False,
        "read_only": True,
        "mutation_safe": True,
    }
    evidence["fingerprint"] = _fingerprint(evidence)
    return evidence


def build_live_flame_realization_preview_spec(
    *,
    sequence_name: str,
    step_plan: Mapping[str, Any],
    realization_discovery: Mapping[str, Any],
    reel_names: Sequence[str] | None = None,
    project_id: str | None = None,
) -> GraphSpec:
    """Build a graph that reruns and verifies held exact realization evidence."""

    name = str(sequence_name).strip()
    if not name:
        raise LiveEditorialVerticalError("sequence_name must not be empty")
    normalized_reels = _normalize_reel_names(reel_names)
    source_plan = dict(step_plan)
    _require_single_step(source_plan)
    discovery = dict(realization_discovery)
    validate_live_flame_realization_discovery(source_plan, discovery)
    semantic = discovery["semantic_discovery"]
    realization = discovery["realization_discovery"]

    read_arguments: dict[str, Any] = {"sequence_name": name}
    if normalized_reels:
        read_arguments["reel_names"] = normalized_reels
    if project_id is not None:
        read_arguments["project_id"] = project_id
    realization_arguments = {
        "mode": "apply",
        "step_plan": source_plan,
        "semantic_capability_plan": semantic["capability_plan"],
        "held_step_plan_fingerprint": realization[
            "step_plan_fingerprint"
        ],
        "held_semantic_capability_plan_fingerprint": realization[
            "semantic_capability_plan_fingerprint"
        ],
        "held_apply_result_fingerprint": realization[
            "apply_result_fingerprint"
        ],
        "held_realization_plan_fingerprint": realization[
            "realization_plan_fingerprint"
        ],
    }

    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="read_edit_state",
                operator_id=LIVE_FLAME_READ_OPERATION_TYPE,
                output_port=PortTopology.manifest(),
                config={"arguments": read_arguments},
            ),
            NodeSpec(
                node_id="apply_steps",
                operator_id=EDITORIAL_APPLY_STEPS_OPERATION_TYPE,
                input_ports={"state": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
                config={"arguments": {"step_plan": source_plan}},
            ),
            NodeSpec(
                node_id="authorize_realization",
                operator_id=FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE,
                input_ports={"apply_result": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
                config={"arguments": realization_arguments},
            ),
            NodeSpec(
                node_id="select_delta",
                operator_id="select_delta",
                input_ports={"result": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="host_resolve",
                operator_id=FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE,
                input_ports={"delta": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="delta_to_manifest",
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
        ),
        edges=(
            Edge(
                from_node="read_edit_state",
                to_node="apply_steps",
                to_port="state",
            ),
            Edge(
                from_node="apply_steps",
                to_node="authorize_realization",
                to_port="apply_result",
            ),
            Edge(
                from_node="authorize_realization",
                to_node="select_delta",
                to_port="result",
            ),
            Edge(
                from_node="select_delta",
                to_node="host_resolve",
                to_port="delta",
            ),
            Edge(
                from_node="host_resolve",
                to_node="delta_to_manifest",
                to_port="deltas",
            ),
        ),
    )


def validate_live_flame_realization_discovery(
    step_plan: Mapping[str, Any],
    discovery: Mapping[str, Any],
) -> None:
    """Fail closed unless discovery binds this exact step and both proof layers."""

    source_fingerprint = _fingerprint(dict(step_plan))
    required = {
        "kind": LIVE_FLAME_REALIZATION_DISCOVERY_KIND,
        "schema_version": 1,
        "status": "ready",
        "trust_status": "trusted",
        "dispatch_authorized": False,
        "read_only": True,
        "mutation_safe": True,
    }
    mismatches = {
        key: {"expected": expected, "actual": discovery.get(key)}
        for key, expected in required.items()
        if discovery.get(key) != expected
    }
    if mismatches:
        raise LiveEditorialVerticalError(
            f"live Flame realization discovery is not trusted: {mismatches}"
        )
    if discovery.get("step_plan_fingerprint") != source_fingerprint:
        raise LiveEditorialVerticalError(
            "live Flame realization discovery does not match step_plan"
        )
    semantic = discovery.get("semantic_discovery")
    realization = discovery.get("realization_discovery")
    if not isinstance(semantic, Mapping) or not isinstance(realization, Mapping):
        raise LiveEditorialVerticalError(
            "live Flame realization discovery is missing proof layers"
        )
    _validate_semantic_discovery(
        semantic,
        source_fingerprint=source_fingerprint,
    )
    _validate_realization_discovery(
        realization,
        source_fingerprint=source_fingerprint,
        semantic_plan_fingerprint=str(
            semantic.get("capability_plan_fingerprint") or ""
        ),
    )
    expected_fingerprint = _fingerprint(
        {key: value for key, value in discovery.items() if key != "fingerprint"}
    )
    if discovery.get("fingerprint") != expected_fingerprint:
        raise LiveEditorialVerticalError(
            "live Flame realization discovery fingerprint mismatch"
        )


def build_live_flame_rename_preview_spec(
    *,
    sequence_name: str,
    step_plan: Mapping[str, Any],
    capability_authorization: Mapping[str, Any],
    reel_names: Sequence[str] | None = None,
    project_id: str | None = None,
) -> GraphSpec:
    """Build the read-to-held-manifest graph after authorization is trusted."""

    name = str(sequence_name).strip()
    if not name:
        raise LiveEditorialVerticalError("sequence_name must not be empty")
    normalized_reels = _normalize_reel_names(reel_names)
    source_plan = dict(step_plan)
    _require_single_rename_step(source_plan)
    authorization = dict(capability_authorization)
    validate_live_flame_authorization(source_plan, authorization)

    read_arguments: dict[str, Any] = {"sequence_name": name}
    if normalized_reels:
        read_arguments["reel_names"] = normalized_reels
    if project_id is not None:
        read_arguments["project_id"] = project_id

    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="read_edit_state",
                operator_id=LIVE_FLAME_READ_OPERATION_TYPE,
                output_port=PortTopology.manifest(),
                config={"arguments": read_arguments},
            ),
            NodeSpec(
                node_id="apply_steps",
                operator_id=EDITORIAL_APPLY_STEPS_OPERATION_TYPE,
                input_ports={"state": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
                config={
                    "arguments": {"step_plan": source_plan},
                    "held_capability_authorization": authorization,
                },
            ),
            NodeSpec(
                node_id="select_delta",
                operator_id="select_delta",
                input_ports={"result": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="host_resolve",
                operator_id=FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE,
                input_ports={"delta": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="delta_to_manifest",
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
        ),
        edges=(
            Edge(
                from_node="read_edit_state",
                to_node="apply_steps",
                to_port="state",
            ),
            Edge(
                from_node="apply_steps",
                to_node="select_delta",
                to_port="result",
            ),
            Edge(
                from_node="select_delta",
                to_node="host_resolve",
                to_port="delta",
            ),
            Edge(
                from_node="host_resolve",
                to_node="delta_to_manifest",
                to_port="deltas",
            ),
        ),
    )


def validate_live_flame_authorization(
    step_plan: Mapping[str, Any],
    authorization: Mapping[str, Any],
    *,
    discovered: Mapping[str, Any] | None = None,
) -> None:
    """Fail closed unless a held Pipeline decision authorizes this exact plan."""

    expected_fingerprint = _fingerprint(dict(step_plan))
    required = {
        "operation_type": EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        "mode": "apply",
        "status": "authorized",
        "trust_status": "trusted",
        "allowed": True,
        "dispatch_authorized": True,
        "drift": False,
        "read_only": True,
        "mutation_safe": True,
    }
    mismatches = {
        key: {"expected": expected, "actual": authorization.get(key)}
        for key, expected in required.items()
        if authorization.get(key) != expected
    }
    if mismatches:
        raise LiveEditorialVerticalError(
            f"live editorial capability authorization is not trusted: {mismatches}"
        )
    if authorization.get("step_plan_fingerprint") != expected_fingerprint:
        raise LiveEditorialVerticalError(
            "live editorial capability authorization does not match step_plan"
        )
    capability_plan = authorization.get("capability_plan")
    if not isinstance(capability_plan, Mapping):
        raise LiveEditorialVerticalError(
            "live editorial capability authorization has no capability_plan"
        )
    if capability_plan.get("target_plugin") != "flame":
        raise LiveEditorialVerticalError(
            "live editorial capability authorization does not target Flame"
        )
    if capability_plan.get("source_step_plan_fingerprint") != expected_fingerprint:
        raise LiveEditorialVerticalError(
            "live editorial capability plan does not match step_plan"
        )
    if not str(authorization.get("matrix_fingerprint") or ""):
        raise LiveEditorialVerticalError("authorization has no matrix fingerprint")
    if not str(authorization.get("capability_plan_fingerprint") or ""):
        raise LiveEditorialVerticalError(
            "authorization has no capability-plan fingerprint"
        )
    if discovered is not None:
        for key in (
            "step_plan_fingerprint",
            "matrix_fingerprint",
            "capability_plan_fingerprint",
        ):
            if authorization.get(key) != discovered.get(key):
                raise LiveEditorialVerticalError(
                    f"live editorial capability {key} drifted after discover"
                )


def _validate_discovery(
    discovered: Mapping[str, Any],
    *,
    source_fingerprint: str,
) -> None:
    required = {
        "operation_type": EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        "mode": "discover",
        "status": "ready",
        "trust_status": "trusted",
        "allowed": True,
        "dispatch_authorized": False,
        "drift": False,
        "read_only": True,
        "mutation_safe": True,
    }
    if any(discovered.get(key) != value for key, value in required.items()):
        raise LiveEditorialVerticalError(
            "live editorial capability discovery did not produce a trusted plan"
        )
    if discovered.get("step_plan_fingerprint") != source_fingerprint:
        raise LiveEditorialVerticalError(
            "live editorial capability discovery fingerprint does not match step_plan"
        )


def _validate_semantic_discovery(
    discovered: Mapping[str, Any],
    *,
    source_fingerprint: str,
) -> None:
    required = {
        "operation_type": EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        "mode": "discover",
        "dispatch_authorized": False,
        "drift": False,
        "read_only": True,
        "mutation_safe": True,
    }
    mismatches = {
        key: {"expected": expected, "actual": discovered.get(key)}
        for key, expected in required.items()
        if discovered.get(key) != expected
    }
    if mismatches:
        raise LiveEditorialVerticalError(
            f"live editorial semantic discovery is invalid: {mismatches}"
        )
    if discovered.get("status") not in {"ready", "blocked"}:
        raise LiveEditorialVerticalError(
            "live editorial semantic discovery has an invalid status"
        )
    if discovered.get("trust_status") not in {
        "trusted",
        "provisional",
        "review_required",
        "untrusted",
    }:
        raise LiveEditorialVerticalError(
            "live editorial semantic discovery has an invalid trust status"
        )
    if discovered.get("step_plan_fingerprint") != source_fingerprint:
        raise LiveEditorialVerticalError(
            "live editorial semantic discovery does not match step_plan"
        )
    capability_plan = discovered.get("capability_plan")
    if not isinstance(capability_plan, Mapping):
        raise LiveEditorialVerticalError(
            "live editorial semantic discovery has no capability_plan"
        )
    if capability_plan.get("target_plugin") != "flame":
        raise LiveEditorialVerticalError(
            "live editorial semantic discovery does not target Flame"
        )
    if capability_plan.get("host_mode") != "flame":
        raise LiveEditorialVerticalError(
            "live editorial semantic discovery does not target flame mode"
        )
    if capability_plan.get("source_step_plan_fingerprint") != source_fingerprint:
        raise LiveEditorialVerticalError(
            "live editorial semantic capability plan does not match step_plan"
        )
    if capability_plan.get("fingerprint") != discovered.get(
        "capability_plan_fingerprint"
    ):
        raise LiveEditorialVerticalError(
            "live editorial semantic capability-plan fingerprint mismatch"
        )


def _validate_realization_discovery(
    discovered: Mapping[str, Any],
    *,
    source_fingerprint: str,
    semantic_plan_fingerprint: str,
) -> None:
    required = {
        "operation_type": FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE,
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
    mismatches = {
        key: {"expected": expected, "actual": discovered.get(key)}
        for key, expected in required.items()
        if discovered.get(key) != expected
    }
    if mismatches:
        raise LiveEditorialVerticalError(
            f"live editorial exact realization is not trusted: {mismatches}"
        )
    if discovered.get("step_plan_fingerprint") != source_fingerprint:
        raise LiveEditorialVerticalError(
            "live editorial exact realization does not match step_plan"
        )
    if discovered.get("semantic_capability_plan_fingerprint") != (
        semantic_plan_fingerprint
    ):
        raise LiveEditorialVerticalError(
            "live editorial exact realization does not match semantic plan"
        )
    for key in (
        "apply_result_fingerprint",
        "delta_fingerprint",
        "lowerer_contract_fingerprint",
        "realization_plan_fingerprint",
    ):
        if not str(discovered.get(key) or ""):
            raise LiveEditorialVerticalError(
                f"live editorial exact realization has no {key}"
            )
    plan = discovered.get("realization_plan")
    if not isinstance(plan, Mapping):
        raise LiveEditorialVerticalError(
            "live editorial exact realization has no realization_plan"
        )
    if plan.get("fingerprint") != discovered.get(
        "realization_plan_fingerprint"
    ):
        raise LiveEditorialVerticalError(
            "live editorial exact realization plan fingerprint mismatch"
        )
    if plan.get("delta_fingerprint") != discovered.get("delta_fingerprint"):
        raise LiveEditorialVerticalError(
            "live editorial exact realization delta fingerprint mismatch"
        )
    if "deltas" in discovered:
        raise LiveEditorialVerticalError(
            "realization discover mode must not emit routable deltas"
        )


def _require_single_rename_step(step_plan: Mapping[str, Any]) -> None:
    steps = step_plan.get("steps")
    if not isinstance(steps, list) or len(steps) != 1:
        raise LiveEditorialVerticalError(
            "the first live Flame vertical requires exactly one editorial step"
        )
    step = steps[0]
    if not isinstance(step, Mapping) or step.get("operation") != "rename_segment":
        raise LiveEditorialVerticalError(
            "the first live Flame vertical is limited to rename_segment"
        )


def _require_single_step(step_plan: Mapping[str, Any]) -> None:
    steps = step_plan.get("steps")
    if not isinstance(steps, list) or len(steps) != 1:
        raise LiveEditorialVerticalError(
            "exact Flame realization requires exactly one editorial step"
        )
    if not isinstance(steps[0], Mapping):
        raise LiveEditorialVerticalError(
            "exact Flame realization step must be a mapping"
        )


def _normalize_reel_names(value: Sequence[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise LiveEditorialVerticalError(
            "reel_names must be a sequence of non-empty strings"
        )
    return [item.strip() for item in value]


async def _run_operation(
    runner: Callable[..., Any],
    operation_type: str,
    **kwargs: Any,
) -> Any:
    result = runner(operation_type, **kwargs)
    return await result if inspect.isawaitable(result) else result


def _successful_operation_data(result: Any, *, label: str) -> dict[str, Any]:
    status = _field(result, "status")
    status_value = str(getattr(status, "value", status or "")).casefold()
    data = _field(result, "data")
    if status_value not in {"succeeded", "success", "ok"}:
        error = _field(result, "error") or _field(result, "message")
        raise LiveEditorialVerticalError(
            f"live editorial capability {label} failed: {error or status_value}"
        )
    if not isinstance(data, Mapping):
        raise LiveEditorialVerticalError(
            f"live editorial capability {label} returned no data mapping"
        )
    return dict(data)


def _field(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _fingerprint(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "EDITORIAL_APPLY_STEPS_OPERATION_TYPE",
    "EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE",
    "FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE",
    "FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE",
    "LIVE_FLAME_REALIZATION_DISCOVERY_KIND",
    "LIVE_FLAME_READ_OPERATION_TYPE",
    "LiveEditorialVerticalError",
    "authorize_live_flame_step_plan",
    "build_live_flame_realization_preview_spec",
    "build_live_flame_rename_preview_spec",
    "discover_live_flame_realization",
    "validate_live_flame_authorization",
    "validate_live_flame_realization_discovery",
]
