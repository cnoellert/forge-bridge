"""Regression proof for the live rename/apply/revert UAT runner."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge_core.operations.protocol import OperationRequest
from forge_core.traffik.editorial_step_capability_operation import (
    TraffikEditorialStepCapabilitiesOperator,
)
from forge_core.traffik.plugin import TraffikPlugin
from forge_flame.operators.editorial_read_edit_state import (
    FlameEditorialReadEditStateOperator,
)
from forge_flame.plugin import FlamePlugin
from scripts.live_flame_editorial_rename_vertical_uat import (
    LiveEditorialUATError,
    run_live_uat,
)
from tests.orchestration.flame_editorial_live_fixture import (
    trusted_live_flame_sequence_data,
)


class _FakeLiveRuntime:
    def __init__(self, *, fail_ratified_apply_number: int | None = None) -> None:
        self.current_name = "shot-010-comp-v003"
        self.fail_ratified_apply_number = fail_ratified_apply_number
        self.targets: dict[str, str] = {}
        self.preview_count = 0
        self.ratified_apply_count = 0
        self.refusal_count = 0
        self.segment_ids: list[str] = []
        self.capability_operator = TraffikEditorialStepCapabilitiesOperator(
            plugins=(FlamePlugin(), TraffikPlugin())
        )

    def _sequence_data(self) -> dict:
        data = trusted_live_flame_sequence_data()
        data["name"] = "FORGE_UAT_HOST_APPLY_20260624"
        data["reel_name"] = "Testing"
        data["versions"][0]["tracks"][0]["segments"][0]["name"] = (
            self.current_name
        )
        return data

    async def runner(self, operation_type: str, **kwargs):
        if operation_type == "flame.editorial.read_edit_state":
            async def execute_json(_code: str) -> dict:
                return {"sequences": [self._sequence_data()]}

            result = await FlameEditorialReadEditStateOperator(
                execute_json=execute_json
            ).execute(
                OperationRequest(
                    operation_type=operation_type,
                    bridge_asset_ids=[],
                    idempotency_key=kwargs["idempotency_key"],
                    params=kwargs["params"],
                    project_id=kwargs.get("project_id"),
                    requested_by=kwargs.get("requested_by"),
                )
            )
            self.segment_ids.append(
                result.data["project"]["sequences"][0]["tracks"][0][
                    "versions"
                ][0]["segments"][0]["id"]
            )
            return result
        if operation_type == "traffik.editorial.step_capabilities":
            return await self.capability_operator.execute(
                OperationRequest(
                    operation_type=operation_type,
                    bridge_asset_ids=[],
                    idempotency_key=kwargs["idempotency_key"],
                    params=kwargs["params"],
                    project_id=kwargs.get("project_id"),
                    requested_by=kwargs.get("requested_by"),
                )
            )
        raise AssertionError(operation_type)

    async def preview(self, graph, **_kwargs):
        self.preview_count += 1
        graph_intent_id = f"intent-{self.preview_count}"
        step_plan = graph.node("apply_steps").config["arguments"]["step_plan"]
        target = step_plan["steps"][0]["params"]["name"]
        self.targets[graph_intent_id] = target
        return {
            "graph_intent_id": graph_intent_id,
            "summary": {
                "manifest": {
                    "apply_tool": "forge_apply_segment_delta",
                    "sequence_name": "FORGE_UAT_HOST_APPLY_20260624",
                    "resolved_count": 1,
                }
            },
        }

    async def apply(self, *, graph_intent_id: str, actor: str | None, **_kwargs):
        if actor is None:
            self.refusal_count += 1
            return SimpleNamespace(
                regime="error",
                error={
                    "code": "assent_illegal_state",
                    "current_status": "proposed",
                },
            )
        self.ratified_apply_count += 1
        if self.ratified_apply_count == self.fail_ratified_apply_number:
            return SimpleNamespace(
                regime="chain_aborted",
                error={"code": "simulated_apply_failure"},
                chain_body={"status": "error"},
            )
        self.current_name = self.targets[graph_intent_id]
        return SimpleNamespace(
            regime="apply_complete",
            assent_record={
                "graph_intent_id": graph_intent_id,
                "status": "applied",
                "decided_by": actor,
            },
        )


@pytest.mark.asyncio
async def test_live_uat_proves_refusal_apply_verify_inverse_and_no_residue() -> None:
    runtime = _FakeLiveRuntime()

    evidence = await run_live_uat(
        sequence_name="FORGE_UAT_HOST_APPLY_20260624",
        reel_names=["Testing"],
        actor="phase114-test",
        runner=runtime.runner,
        session_factory=object(),
        mcp=object(),
        preview_fn=runtime.preview,
        apply_fn=runtime.apply,
    )

    assert evidence["status"] == "passed"
    assert evidence["trust_status"] == "trusted"
    assert evidence["forward"]["unratified_refusal"]["reason_code"] == (
        "assent_illegal_state"
    )
    assert evidence["inverse"]["unratified_refusal"]["reason_code"] == (
        "assent_illegal_state"
    )
    assert evidence["forward"]["dispatch_authorized"] is True
    assert evidence["inverse"]["dispatch_authorized"] is True
    assert evidence["forward_verification"]["status"] == "passed"
    assert evidence["final_verification"]["matches_initial_state"] is True
    assert evidence["mutation"] == {
        "forward_applied": True,
        "inverse_applied": True,
        "residue_free": True,
    }
    assert evidence["recovery"] == {
        "attempted": False,
        "status": "not_needed",
    }
    assert runtime.refusal_count == 2
    assert runtime.ratified_apply_count == 2
    assert runtime.current_name == "shot-010-comp-v003"
    assert len(set(runtime.segment_ids)) == 1


@pytest.mark.asyncio
async def test_live_uat_recovers_original_name_after_inverse_apply_failure() -> None:
    runtime = _FakeLiveRuntime(fail_ratified_apply_number=2)

    with pytest.raises(LiveEditorialUATError) as raised:
        await run_live_uat(
            sequence_name="FORGE_UAT_HOST_APPLY_20260624",
            reel_names=["Testing"],
            actor="phase114-test",
            runner=runtime.runner,
            session_factory=object(),
            mcp=object(),
            preview_fn=runtime.preview,
            apply_fn=runtime.apply,
        )

    evidence = raised.value.evidence
    assert evidence["status"] == "failed"
    assert evidence["trust_status"] == "review_required"
    assert evidence["mutation"]["forward_applied"] is True
    assert evidence["mutation"]["inverse_applied"] is False
    assert evidence["recovery"]["attempted"] is True
    assert evidence["recovery"]["status"] == "passed"
    assert evidence["recovery"]["residue_free"] is True
    assert runtime.ratified_apply_count == 3
    assert runtime.current_name == "shot-010-comp-v003"
