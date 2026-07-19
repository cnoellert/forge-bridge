"""Bridge-owned authorization and graph shape for live editorial previews."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import hashlib
import inspect
import json
from typing import Any

from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.graph.ports import PortContract, PortTopology


LIVE_FLAME_READ_OPERATION_TYPE = "flame.editorial.read_edit_state"
EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE = (
    "traffik.editorial.step_capabilities"
)
EDITORIAL_APPLY_STEPS_OPERATION_TYPE = "traffik.editorial.apply_steps"
FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE = "traffik.flame_delta.host_resolve"


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
    "FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE",
    "LIVE_FLAME_READ_OPERATION_TYPE",
    "LiveEditorialVerticalError",
    "authorize_live_flame_step_plan",
    "build_live_flame_rename_preview_spec",
    "validate_live_flame_authorization",
]
