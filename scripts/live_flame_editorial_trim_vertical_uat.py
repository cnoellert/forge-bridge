#!/usr/bin/env python3
"""Run a ratified live Flame trim-tail vertical and restore exact timing."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping, Sequence
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

from forge_bridge.console._chat_compile import run_apply_branch
from forge_bridge.orchestration.apply_editorial_delta import (
    preview_editorial_delta_for_ratification,
)
from forge_bridge.orchestration.live_editorial_vertical import (
    LIVE_FLAME_READ_OPERATION_TYPE,
    build_live_flame_realization_preview_spec,
    discover_live_flame_realization,
)
from forge_bridge.orchestration.operation_runner import build_operation_runner
from forge_bridge.store.session import get_async_session_factory


EVIDENCE_KIND = "bridge.live_flame_editorial_trim_vertical_uat"
EVIDENCE_SCHEMA_VERSION = 1


class LiveEditorialTrimUATError(RuntimeError):
    """A failed live trim run carrying partial and recovery evidence."""

    def __init__(self, message: str, evidence: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.evidence = dict(evidence)


async def run_live_uat(
    *,
    sequence_name: str,
    actor: str,
    reel_names: Sequence[str] | None = None,
    segment_id: str | None = None,
    trim_frames: int = 1,
    project_id: str | None = None,
    read_timeout_seconds: float = 60.0,
    receipt_dir: str | Path | None = None,
    runner: Any | None = None,
    session_factory: Any | None = None,
    mcp: Any | None = None,
    preview_fn: Any = preview_editorial_delta_for_ratification,
    apply_fn: Any = run_apply_branch,
) -> dict[str, Any]:
    """Trim one tail, verify it, and govern the exact inverse trim."""

    name = str(sequence_name).strip()
    decided_by = str(actor).strip()
    if not name:
        raise ValueError("sequence_name must not be empty")
    if not decided_by:
        raise ValueError("actor must not be empty")
    if isinstance(trim_frames, bool) or not isinstance(trim_frames, int):
        raise ValueError("trim_frames must be an integer")
    if trim_frames <= 0:
        raise ValueError("trim_frames must be greater than zero")
    normalized_reels = [str(item).strip() for item in (reel_names or [])]
    if any(not item for item in normalized_reels):
        raise ValueError("reel_names must contain only non-empty strings")

    operation_runner = runner or build_operation_runner(receipt_dir=receipt_dir)
    sessions = session_factory or get_async_session_factory()
    shared_mcp = mcp or _default_mcp()
    evidence: dict[str, Any] = {
        "kind": EVIDENCE_KIND,
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "trust_status": "review_required",
        "source": {
            "sequence_name": name,
            "reel_names": normalized_reels,
            "read_operation_type": LIVE_FLAME_READ_OPERATION_TYPE,
            "operation": "trim_tail",
            "trim_frames": trim_frames,
        },
        "assent": {
            "actor": decided_by,
            "unratified_refusals_required": 2,
        },
        "mutation": {
            "forward_applied": False,
            "inverse_applied": False,
            "residue_free": False,
        },
        "recovery": {"attempted": False, "status": "not_needed"},
    }
    original_frame_out: Any | None = None
    stable_segment_id: str | None = None
    initial_fingerprint: str | None = None

    try:
        initial = await _read_state(
            operation_runner,
            sequence_name=name,
            reel_names=normalized_reels,
            project_id=project_id,
            timeout_seconds=read_timeout_seconds,
            label="initial",
        )
        sequence, track, segment = _select_segment(
            initial["state"],
            segment_id=segment_id,
        )
        original_frame_out = segment.frame_out
        stable_segment_id = segment.id
        initial_fingerprint = initial["read_evidence"]["result"][
            "state_fingerprint"
        ]
        target_frame_out = original_frame_out - trim_frames
        if target_frame_out <= segment.frame_in:
            raise RuntimeError(
                "trim_frames would collapse or invert the selected segment"
            )
        evidence["identity"] = {
            "project_id": initial["state"].project.id,
            "sequence_id": sequence.id,
            "track_id": track.id,
            "segment_id": stable_segment_id,
            "original_frame_in": segment.frame_in.to_dict(),
            "original_frame_out": original_frame_out.to_dict(),
            "temporary_frame_out": target_frame_out.to_dict(),
            "initial_state_fingerprint": initial_fingerprint,
        }

        forward = await _execute_trim(
            operation_runner,
            session_factory=sessions,
            mcp=shared_mcp,
            preview_fn=preview_fn,
            apply_fn=apply_fn,
            sequence_name=name,
            reel_names=normalized_reels,
            project_id=project_id,
            sequence_id=sequence.id,
            track_id=track.id,
            segment_id=stable_segment_id,
            target_frame_out=target_frame_out,
            actor=decided_by,
            direction="forward",
            receipt_dir=receipt_dir,
        )
        evidence["forward"] = forward
        evidence["mutation"]["forward_applied"] = True

        changed = await _read_state(
            operation_runner,
            sequence_name=name,
            reel_names=normalized_reels,
            project_id=project_id,
            timeout_seconds=read_timeout_seconds,
            label="forward-verify",
        )
        changed_sequence, changed_track, changed_segment = _select_segment(
            changed["state"],
            segment_id=stable_segment_id,
        )
        if changed_segment.frame_out != target_frame_out:
            raise RuntimeError(
                "independent forward verification did not observe trimmed tail"
            )
        if changed_segment.frame_in != segment.frame_in:
            raise RuntimeError("trim_tail changed the selected segment head")
        if changed_segment.id != stable_segment_id:
            raise RuntimeError("segment identity changed after trim")
        evidence["forward_verification"] = {
            "status": "passed",
            "sequence_id": changed_sequence.id,
            "track_id": changed_track.id,
            "segment_id": changed_segment.id,
            "observed_frame_out": changed_segment.frame_out.to_dict(),
            "state_fingerprint": changed["read_evidence"]["result"][
                "state_fingerprint"
            ],
        }

        inverse = await _execute_trim(
            operation_runner,
            session_factory=sessions,
            mcp=shared_mcp,
            preview_fn=preview_fn,
            apply_fn=apply_fn,
            sequence_name=name,
            reel_names=normalized_reels,
            project_id=project_id,
            sequence_id=changed_sequence.id,
            track_id=changed_track.id,
            segment_id=changed_segment.id,
            target_frame_out=original_frame_out,
            actor=decided_by,
            direction="inverse",
            receipt_dir=receipt_dir,
        )
        evidence["inverse"] = inverse
        evidence["mutation"]["inverse_applied"] = True

        final = await _read_state(
            operation_runner,
            sequence_name=name,
            reel_names=normalized_reels,
            project_id=project_id,
            timeout_seconds=read_timeout_seconds,
            label="final",
        )
        _, _, final_segment = _select_segment(
            final["state"],
            segment_id=stable_segment_id,
        )
        final_fingerprint = final["read_evidence"]["result"][
            "state_fingerprint"
        ]
        if final_segment.frame_out != original_frame_out:
            raise RuntimeError("final verification did not restore frame_out")
        if final_segment.id != stable_segment_id:
            raise RuntimeError("final verification observed segment identity drift")
        if final_fingerprint != initial_fingerprint:
            raise RuntimeError(
                "final EditState fingerprint differs from the initial live state"
            )

        evidence["final_verification"] = {
            "status": "passed",
            "segment_id": final_segment.id,
            "observed_frame_out": final_segment.frame_out.to_dict(),
            "state_fingerprint": final_fingerprint,
            "matches_initial_state": True,
        }
        evidence["mutation"]["residue_free"] = True
        evidence["status"] = "passed"
        evidence["trust_status"] = "trusted"
        return evidence
    except Exception as exc:
        evidence["status"] = "failed"
        evidence["trust_status"] = "review_required"
        evidence["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if original_frame_out is not None and stable_segment_id is not None:
            evidence["recovery"] = await _attempt_recovery(
                evidence=evidence,
                runner=operation_runner,
                session_factory=sessions,
                mcp=shared_mcp,
                preview_fn=preview_fn,
                apply_fn=apply_fn,
                sequence_name=name,
                reel_names=normalized_reels,
                project_id=project_id,
                segment_id=stable_segment_id,
                original_frame_out=original_frame_out,
                actor=decided_by,
                read_timeout_seconds=read_timeout_seconds,
                receipt_dir=receipt_dir,
            )
        raise LiveEditorialTrimUATError(str(exc), evidence) from exc


async def _execute_trim(
    runner: Any,
    *,
    session_factory: Any,
    mcp: Any,
    preview_fn: Any,
    apply_fn: Any,
    sequence_name: str,
    reel_names: Sequence[str],
    project_id: str | None,
    sequence_id: str,
    track_id: str,
    segment_id: str,
    target_frame_out: Any,
    actor: str,
    direction: str,
    receipt_dir: str | Path | None,
) -> dict[str, Any]:
    from forge_core.traffik.execution import build_editorial_step_plan

    operation = "trim_tail" if direction == "forward" else "extend_edit"
    params = {
        "sequence_id": sequence_id,
        "track_id": track_id,
        "segment_id": segment_id,
    }
    if operation == "trim_tail":
        params["new_frame_out"] = target_frame_out.to_dict()
    else:
        params.update(side="tail", frame=target_frame_out.to_dict())
    step_plan = build_editorial_step_plan(
        [
            {
                "operation": operation,
                "step_id": f"phase115-{direction}-{operation}",
                "node_id": f"phase115-{direction}-{operation}-node",
                "params": params,
            }
        ],
        plan_id=f"phase115-{direction}-{operation}-plan",
        metadata={"source": EVIDENCE_KIND, "direction": direction},
    )
    discovery = await discover_live_flame_realization(
        step_plan,
        sequence_name=sequence_name,
        reel_names=reel_names,
        project_id=project_id,
        run_operation=runner,
        requested_by=EVIDENCE_KIND,
        authorization_id=f"phase115-{direction}-{time.time_ns()}",
    )
    graph = build_live_flame_realization_preview_spec(
        sequence_name=sequence_name,
        reel_names=reel_names,
        project_id=project_id,
        step_plan=step_plan,
        realization_discovery=discovery,
    )
    preview = await preview_fn(
        graph,
        session_factory=session_factory,
        mcp=mcp,
        receipt_dir=receipt_dir,
        display=f"Phase 115 {direction} live editorial {operation}",
    )
    manifest_summary = preview.get("summary", {}).get("manifest", {})
    if manifest_summary.get("apply_tool") != (
        "forge_apply_segment_temporal_delta"
    ):
        raise RuntimeError(f"{direction} preview selected an unexpected apply tool")
    if manifest_summary.get("sequence_name") != sequence_name:
        raise RuntimeError(f"{direction} preview selected an unexpected sequence")

    graph_intent_id = str(preview["graph_intent_id"])
    refused = await apply_fn(
        graph_intent_id=graph_intent_id,
        session_factory=session_factory,
        tools=[],
        mcp=mcp,
        request_id=f"phase115-{direction}-unratified",
        client_ip="127.0.0.1",
        started=time.monotonic(),
        actor=None,
    )
    refused_error = _field(refused, "error") or {}
    if _field(refused, "regime") != "error" or refused_error.get("code") != (
        "assent_illegal_state"
    ):
        raise RuntimeError(f"{direction} unratified replay did not fail closed")

    applied = await apply_fn(
        graph_intent_id=graph_intent_id,
        session_factory=session_factory,
        tools=[],
        mcp=mcp,
        request_id=f"phase115-{direction}-ratified",
        client_ip="127.0.0.1",
        started=time.monotonic(),
        actor=actor,
    )
    if _field(applied, "regime") != "apply_complete":
        raise RuntimeError(
            f"{direction} ratified replay failed: "
            f"{_field(applied, 'error') or _field(applied, 'chain_body')}"
        )
    semantic = discovery["semantic_discovery"]
    realization = discovery["realization_discovery"]
    return {
        "status": "passed",
        "direction": direction,
        "operation": operation,
        "target_frame_out": target_frame_out.to_dict(),
        "step_plan_fingerprint": discovery["step_plan_fingerprint"],
        "semantic_allowed": semantic["allowed"],
        "semantic_trust_status": semantic["trust_status"],
        "semantic_capability_plan_fingerprint": semantic[
            "capability_plan_fingerprint"
        ],
        "realization_trust_status": realization["trust_status"],
        "realization_plan_fingerprint": realization[
            "realization_plan_fingerprint"
        ],
        "apply_result_fingerprint": realization["apply_result_fingerprint"],
        "delta_fingerprint": realization["delta_fingerprint"],
        "executor": realization["realization_plan"]["executor"],
        "discovery_fingerprint": discovery["fingerprint"],
        "graph_intent_id": graph_intent_id,
        "manifest_summary": copy.deepcopy(manifest_summary),
        "unratified_refusal": {
            "status": "passed",
            "reason_code": refused_error["code"],
        },
        "ratified_apply": {
            "status": "passed",
            "regime": _field(applied, "regime"),
            "assent_record": copy.deepcopy(_field(applied, "assent_record")),
        },
    }


async def _read_state(
    runner: Any,
    *,
    sequence_name: str,
    reel_names: Sequence[str],
    project_id: str | None,
    timeout_seconds: float,
    label: str,
) -> dict[str, Any]:
    from forge_core.traffik.editing import EditState

    params: dict[str, Any] = {
        "sequence_name": sequence_name,
        "timeout_seconds": timeout_seconds,
    }
    if reel_names:
        params["reel_names"] = list(reel_names)
    result = await runner(
        LIVE_FLAME_READ_OPERATION_TYPE,
        params=params,
        idempotency_key=f"phase115-live-read:{label}:{time.time_ns()}",
        project_id=project_id,
        requested_by=EVIDENCE_KIND,
    )
    status = _status_value(_field(result, "status"))
    data = _field(result, "data")
    if status != "succeeded" or not isinstance(data, Mapping):
        raise RuntimeError(
            f"{label} live read failed: "
            f"{_field(result, 'error') or _field(data, 'error_code')}"
        )
    logs = _field(result, "logs") or []
    prefix = "flame_editorial_read_edit_state_evidence: "
    evidence_line = next(
        (item for item in logs if isinstance(item, str) and item.startswith(prefix)),
        None,
    )
    if evidence_line is None:
        raise RuntimeError(f"{label} live read emitted no evidence")
    return {
        "state": EditState.from_dict(dict(data)),
        "read_evidence": json.loads(evidence_line.removeprefix(prefix)),
    }


def _select_segment(state: Any, *, segment_id: str | None):
    sequence = state.project.get_sequence(state.session.active_sequence_id or "")
    if sequence is None:
        raise RuntimeError("live EditState has no active sequence")
    for track in sequence.tracks:
        version = track.active_version
        if version is None:
            continue
        for segment in version.segments:
            if segment_id is None or segment.id == segment_id:
                return sequence, track, segment
    if segment_id:
        raise RuntimeError(f"segment not found in active sequence: {segment_id}")
    raise RuntimeError("live EditState active sequence has no editable segment")


async def _attempt_recovery(
    *,
    evidence: Mapping[str, Any],
    runner: Any,
    session_factory: Any,
    mcp: Any,
    preview_fn: Any,
    apply_fn: Any,
    sequence_name: str,
    reel_names: Sequence[str],
    project_id: str | None,
    segment_id: str,
    original_frame_out: Any,
    actor: str,
    read_timeout_seconds: float,
    receipt_dir: str | Path | None,
) -> dict[str, Any]:
    recovery: dict[str, Any] = {"attempted": True, "status": "failed"}
    try:
        observed = await _read_state(
            runner,
            sequence_name=sequence_name,
            reel_names=reel_names,
            project_id=project_id,
            timeout_seconds=read_timeout_seconds,
            label="recovery-probe",
        )
        sequence, track, segment = _select_segment(
            observed["state"],
            segment_id=segment_id,
        )
        recovery["observed_frame_out"] = segment.frame_out.to_dict()
        if segment.frame_out != original_frame_out:
            recovery["apply"] = await _execute_trim(
                runner,
                session_factory=session_factory,
                mcp=mcp,
                preview_fn=preview_fn,
                apply_fn=apply_fn,
                sequence_name=sequence_name,
                reel_names=reel_names,
                project_id=project_id,
                sequence_id=sequence.id,
                track_id=track.id,
                segment_id=segment.id,
                target_frame_out=original_frame_out,
                actor=actor,
                direction="recovery",
                receipt_dir=receipt_dir,
            )
        final = await _read_state(
            runner,
            sequence_name=sequence_name,
            reel_names=reel_names,
            project_id=project_id,
            timeout_seconds=read_timeout_seconds,
            label="recovery-verify",
        )
        _, _, final_segment = _select_segment(
            final["state"],
            segment_id=segment_id,
        )
        if final_segment.frame_out != original_frame_out:
            raise RuntimeError("recovery did not restore original frame_out")
        final_fingerprint = final["read_evidence"]["result"][
            "state_fingerprint"
        ]
        expected_fingerprint = (
            evidence.get("identity", {}).get("initial_state_fingerprint")
            if isinstance(evidence.get("identity"), Mapping)
            else None
        )
        if expected_fingerprint and final_fingerprint != expected_fingerprint:
            raise RuntimeError(
                "recovery restored frame_out but not the original EditState"
            )
        recovery.update(
            status="passed",
            final_frame_out=final_segment.frame_out.to_dict(),
            final_state_fingerprint=final_fingerprint,
            matches_initial_state=(
                final_fingerprint == expected_fingerprint
                if expected_fingerprint
                else None
            ),
            residue_free=True,
            original_error=copy.deepcopy(evidence.get("error")),
        )
    except Exception as exc:  # noqa: BLE001 - recovery evidence must survive
        recovery["error"] = {"type": type(exc).__name__, "message": str(exc)}
    return recovery


def _field(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value or "")).casefold()


def _default_mcp() -> Any:
    from forge_bridge.mcp.server import mcp

    return mcp


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--sequence-name", required=True)
    parser.add_argument("--reel-name", action="append", dest="reel_names")
    parser.add_argument("--segment-id")
    parser.add_argument("--trim-frames", type=int, default=1)
    parser.add_argument("--project-id")
    parser.add_argument("--actor", required=True)
    parser.add_argument("--read-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--receipt-dir", type=Path)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--quiet", action="store_true")
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    if not args.apply:
        parser.error("--apply is required because this UAT performs live mutation")
    exit_code = 0
    try:
        evidence = asyncio.run(
            run_live_uat(
                sequence_name=args.sequence_name,
                actor=args.actor,
                reel_names=args.reel_names,
                segment_id=args.segment_id,
                trim_frames=args.trim_frames,
                project_id=args.project_id,
                read_timeout_seconds=args.read_timeout_seconds,
                receipt_dir=args.receipt_dir,
            )
        )
    except LiveEditorialTrimUATError as exc:
        evidence = exc.evidence
        exit_code = 2
    payload = json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n"
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(payload, encoding="utf-8")
    if not args.quiet:
        print(payload, end="")  # noqa: T201 - CLI evidence output
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
