"""Regression proof for the live trim/apply/revert UAT runner."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge_core.operations.protocol import OperationRequest
from forge_core.traffik.core.objects import TraffickFrame, TraffickFrameRate
from forge_core.traffik.editorial_step_capability_operation import (
    TraffikEditorialStepCapabilitiesOperator,
)
from forge_core.traffik.execution import TraffikEditorialOperator
from forge_core.traffik.plugin import TraffikPlugin
from forge_flame.operators.editorial_delta_realization import (
    FlameEditorialDeltaRealizationOperator,
)
from forge_flame.operators.editorial_read_edit_state import (
    FlameEditorialReadEditStateOperator,
)
from forge_flame.plugin import FlamePlugin
from scripts.live_flame_editorial_trim_vertical_uat import (
    LiveEditorialTrimUATError,
    run_live_uat,
)
from tests.orchestration.flame_editorial_live_fixture import (
    trusted_live_flame_sequence_data,
)


class _FakeLiveTrimRuntime:
    def __init__(
        self,
        *,
        fail_ratified_apply_number: int | None = None,
        stale_source_timecode_after_apply: bool = False,
    ) -> None:
        self.current_record_out = 86424
        self.current_source_out = 1024
        self.fail_ratified_apply_number = fail_ratified_apply_number
        self.stale_source_timecode_after_apply = stale_source_timecode_after_apply
        self.targets: dict[str, int] = {}
        self.preview_count = 0
        self.ratified_apply_count = 0
        self.refusal_count = 0
        self.segment_ids: list[str] = []
        self.capability_operator = TraffikEditorialStepCapabilitiesOperator(
            plugins=(FlamePlugin(), TraffikPlugin())
        )
        self.apply_steps_operator = TraffikEditorialOperator()
        self.realization_operator = FlameEditorialDeltaRealizationOperator()

    def _sequence_data(self) -> dict:
        data = trusted_live_flame_sequence_data()
        data["name"] = "FORGE_UAT_HOST_APPLY_20260624"
        data["reel_name"] = "Testing"
        segment = data["versions"][0]["tracks"][0]["segments"][0]
        segment["record_out"] = self.current_record_out - 1
        segment["record_duration_frames"] = (
            self.current_record_out - segment["record_in"]
        )
        segment["source_out"] = self.current_source_out - 1
        source_timecode_frame = (
            1023
            if self.stale_source_timecode_after_apply
            and self.current_source_out != 1024
            else self.current_source_out - 1
        )
        source_out_tc = TraffickFrame(
            source_timecode_frame,
            TraffickFrameRate.FPS_24,
        ).to_timecode()
        segment["source_out_tc"] = (
            f"{source_out_tc.hours:02d}:{source_out_tc.minutes:02d}:"
            f"{source_out_tc.seconds:02d}+{source_out_tc.frames:02d}"
        )
        return data

    async def runner(self, operation_type: str, **kwargs):
        request = OperationRequest(
            operation_type=operation_type,
            bridge_asset_ids=[],
            idempotency_key=kwargs["idempotency_key"],
            params=kwargs["params"],
            project_id=kwargs.get("project_id"),
            requested_by=kwargs.get("requested_by"),
        )
        if operation_type == "flame.editorial.read_edit_state":
            async def execute_json(_code: str) -> dict:
                return {"sequences": [self._sequence_data()]}

            result = await FlameEditorialReadEditStateOperator(
                execute_json=execute_json
            ).execute(request)
            self.segment_ids.append(
                result.data["project"]["sequences"][0]["tracks"][0][
                    "versions"
                ][0]["segments"][0]["id"]
            )
            return result
        if operation_type == "traffik.editorial.step_capabilities":
            return await self.capability_operator.execute(request)
        if operation_type == "traffik.editorial.apply_steps":
            return await self.apply_steps_operator.execute(request)
        if operation_type == "flame.editorial.delta_realization":
            return await self.realization_operator.execute(request)
        raise AssertionError(operation_type)

    async def preview(self, graph, **_kwargs):
        self.preview_count += 1
        graph_intent_id = f"intent-{self.preview_count}"
        step_plan = graph.node("apply_steps").config["arguments"]["step_plan"]
        step = step_plan["steps"][0]
        params = step["params"]
        if step["operation"] == "trim_tail":
            target = params["new_frame_out"]["number"]
        else:
            assert step["operation"] == "extend_edit"
            assert params["side"] == "tail"
            target = params["frame"]["number"]
        self.targets[graph_intent_id] = target
        return {
            "graph_intent_id": graph_intent_id,
            "summary": {
                "manifest": {
                    "apply_tool": "forge_apply_segment_temporal_delta",
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
        target = self.targets[graph_intent_id]
        delta = target - self.current_record_out
        self.current_record_out = target
        self.current_source_out += delta
        return SimpleNamespace(
            regime="apply_complete",
            assent_record={
                "graph_intent_id": graph_intent_id,
                "status": "applied",
                "decided_by": actor,
            },
        )


@pytest.mark.asyncio
async def test_live_trim_uat_elevates_exact_delta_and_restores_state() -> None:
    runtime = _FakeLiveTrimRuntime()

    evidence = await run_live_uat(
        sequence_name="FORGE_UAT_HOST_APPLY_20260624",
        reel_names=["Testing"],
        actor="phase115-test",
        runner=runtime.runner,
        session_factory=object(),
        mcp=object(),
        preview_fn=runtime.preview,
        apply_fn=runtime.apply,
    )

    assert evidence["status"] == "passed"
    assert evidence["trust_status"] == "trusted"
    assert evidence["forward"]["semantic_allowed"] is False
    assert evidence["forward"]["semantic_trust_status"] == "review_required"
    assert evidence["forward"]["realization_trust_status"] == "trusted"
    assert evidence["forward"]["operation"] == "trim_tail"
    assert evidence["inverse"]["operation"] == "extend_edit"
    assert evidence["forward"]["executor"] == (
        "forge_apply_segment_temporal_delta"
    )
    assert evidence["forward"]["unratified_refusal"]["reason_code"] == (
        "assent_illegal_state"
    )
    assert evidence["inverse"]["unratified_refusal"]["reason_code"] == (
        "assent_illegal_state"
    )
    assert evidence["forward_verification"]["status"] == "passed"
    assert evidence["forward_verification"]["observed_source_out"]["number"] == 1023
    assert evidence["final_verification"]["matches_initial_state"] is True
    assert evidence["final_verification"]["observed_source_out"]["number"] == 1024
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
    assert runtime.current_record_out == 86424
    assert runtime.current_source_out == 1024
    assert len(set(runtime.segment_ids)) == 1


@pytest.mark.asyncio
async def test_live_trim_uat_recovers_after_inverse_apply_failure() -> None:
    runtime = _FakeLiveTrimRuntime(fail_ratified_apply_number=2)

    with pytest.raises(LiveEditorialTrimUATError) as raised:
        await run_live_uat(
            sequence_name="FORGE_UAT_HOST_APPLY_20260624",
            reel_names=["Testing"],
            actor="phase115-test",
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
    assert runtime.current_record_out == 86424
    assert runtime.current_source_out == 1024


@pytest.mark.asyncio
async def test_live_trim_uat_refuses_stale_source_timecode_evidence() -> None:
    runtime = _FakeLiveTrimRuntime(stale_source_timecode_after_apply=True)

    with pytest.raises(LiveEditorialTrimUATError) as raised:
        await run_live_uat(
            sequence_name="FORGE_UAT_HOST_APPLY_20260624",
            reel_names=["Testing"],
            actor="phase115-test",
            runner=runtime.runner,
            session_factory=object(),
            mcp=object(),
            preview_fn=runtime.preview,
            apply_fn=runtime.apply,
        )

    evidence = raised.value.evidence
    assert evidence["mutation"]["forward_applied"] is True
    assert evidence["mutation"]["residue_free"] is False
    assert "source_out timecode disagrees" in evidence["error"]["message"]
