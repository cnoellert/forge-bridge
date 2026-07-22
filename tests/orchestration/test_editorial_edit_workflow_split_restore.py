"""Focused matrix for #237 — governed split restore in the editorial workflow.

Proves: the forward split ``recovery`` token is captured byte-for-byte and
fingerprinted; restore discovers a separate manifest + AssentRecord and commits
through the same rail; unratified/drift/missing-token/undiscovered-tool all fail
closed; replay never touches a split tool; and duplicate/concurrent restore
performs at most one host mutation. Fakes stand in for the live commit rail,
exactly like the #235 matrix.
"""

from __future__ import annotations

import asyncio
import itertools

import pytest

import forge_bridge.orchestration.editorial_edit_workflow as eew
from forge_bridge.composition.admission import admit_mutation_counterpart
from forge_bridge.orchestration.editorial_edit_workflow import (
    EditorialEditWorkflowAPI,
    InMemoryEditorialEditWorkflowStore,
    canonical_fingerprint,
)
from tests.orchestration.test_editorial_edit_workflow import (
    _discovery_for,
    make_proposal,
)

SPLIT_RESTORE_TOOL = "forge_apply_segment_split_restore"
SEQ = "FORGE_UAT_HOST_APPLY_20260624"


def make_recovery(seq: str = SEQ, created_version_index: int = 1) -> dict:
    return {
        "schema_version": 1,
        "method": "delete_created_version",
        "sequence_name": seq,
        "source_version_index": 0,
        "created_version_index": created_version_index,
        "version_index": created_version_index,
        "created_track_index": 0,
        "restore_primary_version_index": 0,
        "restore_primary_track_index": 0,
        "expected_version_count": 2,
        "expected_created_version_state": [],
        "expected_source_version_state": [],
        "expected_restore_primary_track_state": [],
        "expected_primary_track_matches": [{"version_index": 1, "track_index": 0}],
        "expected_primary_track_matches_after_restore": [
            {"version_index": 0, "track_index": 0}
        ],
    }


class SplitRecorder:
    def __init__(self, *, recovery=None, tool_present=True, discover_ok=True,
                 restore_applies=True):
        self.recovery = recovery
        self.tool_present = tool_present
        self.discover_ok = discover_ok
        self.restore_applies = restore_applies
        self.forward_apply_calls = 0
        self.restore_apply_calls = 0
        self.split_preview_calls = 0
        self.restore_apply_delay = 0.0
        self._ids = itertools.count(1)

    async def forward_preview_fn(self, *, spec, display):
        n = next(self._ids)
        return {
            "graph_intent_id": f"fwd-intent-{n}",
            "assent_record_id": f"fwd-assent-{n}",
            "manifest": {
                "apply_counterpart": {"tool": "forge_apply_segment_split_delta"},
                "intent_parameters": {"sequence_name": SEQ},
                "resolved_plan": [{"i": n}],
                "type": "editorial_delta",
            },
        }

    async def apply_fn(self, *, graph_intent_id, requested_by):
        if graph_intent_id.startswith("split-restore"):
            self.restore_apply_calls += 1
            if self.restore_apply_delay:
                await asyncio.sleep(self.restore_apply_delay)
            if not self.restore_applies:
                return {
                    "outcome": "failed",
                    "assent_status": "failed",
                    "reason_code": eew.REASON_COMMIT_FAILED,
                    "commit_result": None,
                }
            return {
                "outcome": "applied",
                "assent_status": "applied",
                "reason_code": None,
                "commit_result": {
                    "type": "commit_applied",
                    "count": 1,
                    "apply_result": {
                        "ok": True,
                        "restored": 1,
                        "results": [{"ok": True, "restored": True}],
                    },
                },
            }
        # forward split apply — embed the closed recovery token, if any.
        self.forward_apply_calls += 1
        results = [{"ok": True, "recovery": self.recovery}] if self.recovery is \
            not None else []
        return {
            "outcome": "applied",
            "assent_status": "applied",
            "reason_code": None,
            "commit_result": {
                "type": "commit_applied",
                "count": 1,
                "apply_result": {"ok": True, "split": 1, "results": results},
            },
        }

    async def split_restore_preview_fn(self, *, sequence_name, recovery, display):
        self.split_preview_calls += 1
        if not self.tool_present:
            raise eew._SplitRestoreUnavailable("counterpart not declared")
        if not self.discover_ok:
            raise eew._SplitRestoreDrift("token/sequence mismatch")
        n = next(self._ids)
        return {
            "graph_intent_id": f"split-restore-intent-{n}",
            "assent_record_id": f"split-restore-assent-{n}",
            "manifest": {
                "apply_counterpart": {"tool": SPLIT_RESTORE_TOOL},
                "intent_parameters": {
                    "sequence_name": sequence_name,
                    "recovery": recovery,
                },
                "resolved_plan": [],
                "type": "mutation_plan",
            },
        }


def build_split_api(monkeypatch, *, recorder, proposal, store=None,
                    with_split_preview=True):
    store = store if store is not None else InMemoryEditorialEditWorkflowStore()

    async def fake_discover(step_plan, *, sequence_name, run_operation,
                            project_id=None, requested_by=None, **_):
        return _discovery_for(proposal, step_plan=step_plan)

    monkeypatch.setattr(eew, "discover_live_flame_realization", fake_discover)
    monkeypatch.setattr(
        eew, "build_live_flame_realization_preview_spec",
        lambda **kwargs: ("SPEC", kwargs.get("sequence_name")),
    )
    api = EditorialEditWorkflowAPI(
        run_operation=lambda *a, **k: None,
        preview_fn=recorder.forward_preview_fn,
        apply_fn=recorder.apply_fn,
        store=store,
        split_restore_preview_fn=(
            recorder.split_restore_preview_fn if with_split_preview else None
        ),
        clock=lambda: "2026-07-22T00:00:00Z",
    )
    return api, store


async def _propose_and_apply(api, proposal):
    r_prop = await api.propose(proposal)
    pid = r_prop["proposal_id"]
    fp = proposal["fingerprint"]
    r_apply = await api.ratify_apply(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    return pid, fp, r_apply


# --------------------------------------------------------------------------- #
# Admission
# --------------------------------------------------------------------------- #
def test_split_restore_counterpart_is_admitted():
    record = admit_mutation_counterpart(SPLIT_RESTORE_TOOL)
    assert record.tool_name == SPLIT_RESTORE_TOOL
    assert record.state_owner == "dcc_host"
    assert record.verify_before_apply is True
    assert record.assent_required is True
    assert record.idempotent_apply is True
    assert record.synchronous is True


# --------------------------------------------------------------------------- #
# Recovery token capture
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_forward_split_apply_persists_recovery_token_byte_for_byte(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="s")
    rec = SplitRecorder(recovery=make_recovery())
    api, store = build_split_api(monkeypatch, recorder=rec, proposal=proposal)

    pid, _, r_apply = await _propose_and_apply(api, proposal)

    assert r_apply["status"] == "applied"
    wf = await store.get_by_proposal_id(pid)
    assert wf["forward_split_recovery"] == make_recovery()
    assert wf["forward_split_recovery_fingerprint"] == canonical_fingerprint(
        make_recovery()
    )


@pytest.mark.asyncio
async def test_forward_split_apply_without_token_still_applies(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="s2")
    rec = SplitRecorder(recovery=None)  # no recovery result
    api, store = build_split_api(monkeypatch, recorder=rec, proposal=proposal)

    pid, _, r_apply = await _propose_and_apply(api, proposal)

    assert r_apply["status"] == "applied"  # forward mutation stands
    wf = await store.get_by_proposal_id(pid)
    assert "forward_split_recovery" not in wf


@pytest.mark.asyncio
async def test_invalid_recovery_shape_not_persisted(monkeypatch):
    # two results (not exactly one) => no token captured.
    proposal = make_proposal(operation="split_at_playhead", tag="s3")
    rec = SplitRecorder(recovery=make_recovery())

    async def apply_two_results(*, graph_intent_id, requested_by):
        rec.forward_apply_calls += 1
        return {
            "outcome": "applied", "assent_status": "applied", "reason_code": None,
            "commit_result": {"type": "commit_applied", "count": 1,
                              "apply_result": {"results": [
                                  {"recovery": make_recovery()},
                                  {"recovery": make_recovery()},
                              ]}},
        }

    api, store = build_split_api(monkeypatch, recorder=rec, proposal=proposal)
    rec.apply_fn = apply_two_results  # override just forward
    # re-inject
    api._apply_fn = rec.apply_fn
    pid, _, r_apply = await _propose_and_apply(api, proposal)
    assert r_apply["status"] == "applied"
    wf = await store.get_by_proposal_id(pid)
    assert "forward_split_recovery" not in wf


# --------------------------------------------------------------------------- #
# Successful split restore
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_split_restore_success_separate_evidence_and_root_intact(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="ok")
    rec = SplitRecorder(recovery=make_recovery())
    api, store = build_split_api(monkeypatch, recorder=rec, proposal=proposal)

    pid, fp, r_apply = await _propose_and_apply(api, proposal)
    fwd_manifest_fp = r_apply["manifest_fingerprint"]
    fwd_commit_fp = r_apply["commit_fingerprint"]
    fwd_assent = r_apply["assent_record_id"]

    r_restore = await api.restore(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )

    assert r_restore["status"] == "restored"
    assert r_restore["restored"] is True
    assert r_restore["applied"] is False and r_restore["replayed"] is False
    assert r_restore["dispatch_authorized"] is True
    assert r_restore["reason_code"] is None
    assert rec.restore_apply_calls == 1
    # root forward proposal identity retained
    assert r_restore["proposal_fingerprint"] == fp
    assert r_restore["step_plan_fingerprint"] == proposal["step_plan_fingerprint"]
    assert r_restore["delta_fingerprint"] == proposal["delta_fingerprint"]
    # separate restore evidence
    assert r_restore["assent_record_id"] != fwd_assent
    assert r_restore["manifest_fingerprint"] != fwd_manifest_fp
    assert r_restore["commit_fingerprint"] != fwd_commit_fp
    # durable: root forward fingerprints untouched
    wf = await store.get_by_proposal_id(pid)
    assert wf["forward_manifest_fingerprint"] == fwd_manifest_fp
    assert wf["forward_commit_fingerprint"] == fwd_commit_fp
    assert wf["restore"]["recovery_fingerprint"] == canonical_fingerprint(
        make_recovery()
    )
    # closed + canonically fingerprinted
    body = {k: v for k, v in r_restore.items() if k != "fingerprint"}
    assert r_restore["fingerprint"] == canonical_fingerprint(body)


# --------------------------------------------------------------------------- #
# Fail-closed paths
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_unratified_restore_never_calls_counterpart(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="u")
    rec = SplitRecorder(recovery=make_recovery())
    api, _ = build_split_api(monkeypatch, recorder=rec, proposal=proposal)

    r_prop = await api.propose(proposal)  # status proposed, not applied
    r_restore = await api.restore(
        proposal_id=r_prop["proposal_id"],
        expected_proposal_fingerprint=proposal["fingerprint"],
        requested_by="op",
    )
    assert r_restore["status"] == "refused"
    assert r_restore["reason_code"] == eew.REASON_RESTORE_UNAVAILABLE
    assert rec.split_preview_calls == 0
    assert rec.restore_apply_calls == 0


@pytest.mark.asyncio
async def test_missing_token_fails_unavailable(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="m")
    rec = SplitRecorder(recovery=None)  # forward applies, no token
    api, _ = build_split_api(monkeypatch, recorder=rec, proposal=proposal)

    pid, fp, _ = await _propose_and_apply(api, proposal)
    r_restore = await api.restore(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    assert r_restore["status"] == "refused"
    assert r_restore["reason_code"] == eew.REASON_RESTORE_UNAVAILABLE
    assert rec.split_preview_calls == 0
    assert rec.restore_apply_calls == 0


@pytest.mark.asyncio
async def test_undiscovered_tool_fails_unavailable(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="nd")
    rec = SplitRecorder(recovery=make_recovery(), tool_present=False)
    api, _ = build_split_api(monkeypatch, recorder=rec, proposal=proposal)

    pid, fp, _ = await _propose_and_apply(api, proposal)
    r_restore = await api.restore(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    assert r_restore["status"] == "refused"
    assert r_restore["reason_code"] == eew.REASON_RESTORE_UNAVAILABLE
    assert rec.restore_apply_calls == 0  # never dispatched


@pytest.mark.asyncio
async def test_no_split_preview_fn_wired_fails_unavailable(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="nw")
    rec = SplitRecorder(recovery=make_recovery())
    api, _ = build_split_api(
        monkeypatch, recorder=rec, proposal=proposal, with_split_preview=False
    )
    pid, fp, _ = await _propose_and_apply(api, proposal)
    r_restore = await api.restore(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    assert r_restore["reason_code"] == eew.REASON_RESTORE_UNAVAILABLE
    assert rec.restore_apply_calls == 0


@pytest.mark.asyncio
async def test_tampered_token_refuses_drift_before_dispatch(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="t")
    rec = SplitRecorder(recovery=make_recovery())
    api, store = build_split_api(monkeypatch, recorder=rec, proposal=proposal)
    pid, fp, _ = await _propose_and_apply(api, proposal)
    # tamper the persisted token so its fingerprint no longer matches
    wf = await store.get_by_proposal_id(pid)
    tampered = dict(wf["forward_split_recovery"])
    tampered["created_version_index"] = 99
    await store.update(pid, {"forward_split_recovery": tampered})

    r_restore = await api.restore(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    assert r_restore["status"] == "refused"
    assert r_restore["reason_code"] == eew.REASON_RESTORE_DRIFT
    assert rec.split_preview_calls == 0
    assert rec.restore_apply_calls == 0


@pytest.mark.asyncio
async def test_discover_mismatch_refuses_drift(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="dm")
    rec = SplitRecorder(recovery=make_recovery(), discover_ok=False)
    api, _ = build_split_api(monkeypatch, recorder=rec, proposal=proposal)
    pid, fp, _ = await _propose_and_apply(api, proposal)
    r_restore = await api.restore(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    assert r_restore["status"] == "refused"
    assert r_restore["reason_code"] == eew.REASON_RESTORE_DRIFT
    assert rec.restore_apply_calls == 0  # drift before dispatch


@pytest.mark.asyncio
async def test_restore_apply_failure_records_failed_and_keeps_applied(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="f")
    rec = SplitRecorder(recovery=make_recovery(), restore_applies=False)
    api, store = build_split_api(monkeypatch, recorder=rec, proposal=proposal)
    pid, fp, _ = await _propose_and_apply(api, proposal)
    r_restore = await api.restore(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    assert r_restore["status"] == "refused"
    assert r_restore["reason_code"] == eew.REASON_RESTORE_FAILED
    assert r_restore["restored"] is False
    wf = await store.get_by_proposal_id(pid)
    assert wf["status"] == "applied"  # forward apply still stands


# --------------------------------------------------------------------------- #
# Replay + idempotency + concurrency
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_replay_never_invokes_split_tools(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="r")
    rec = SplitRecorder(recovery=make_recovery())
    api, _ = build_split_api(monkeypatch, recorder=rec, proposal=proposal)
    pid, fp, _ = await _propose_and_apply(api, proposal)
    fwd_calls = rec.forward_apply_calls

    r_replay = await api.replay(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    assert r_replay["status"] == "replayed"
    assert rec.split_preview_calls == 0
    assert rec.restore_apply_calls == 0
    assert rec.forward_apply_calls == fwd_calls  # no new forward dispatch either


@pytest.mark.asyncio
async def test_second_restore_is_idempotent_no_second_mutation(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="i")
    rec = SplitRecorder(recovery=make_recovery())
    api, _ = build_split_api(monkeypatch, recorder=rec, proposal=proposal)
    pid, fp, _ = await _propose_and_apply(api, proposal)

    first = await api.restore(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    second = await api.restore(
        proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
    )
    assert first["status"] == "restored" and second["status"] == "restored"
    assert first["commit_fingerprint"] == second["commit_fingerprint"]
    assert rec.restore_apply_calls == 1  # exactly one host mutation


@pytest.mark.asyncio
async def test_concurrent_restore_at_most_one_mutation(monkeypatch):
    proposal = make_proposal(operation="split_at_playhead", tag="c")
    rec = SplitRecorder(recovery=make_recovery())
    rec.restore_apply_delay = 0.02
    api, _ = build_split_api(monkeypatch, recorder=rec, proposal=proposal)
    pid, fp, _ = await _propose_and_apply(api, proposal)

    results = await asyncio.gather(*[
        api.restore(
            proposal_id=pid, expected_proposal_fingerprint=fp, requested_by="op"
        )
        for _ in range(4)
    ])
    assert all(r["status"] == "restored" for r in results)
    assert rec.restore_apply_calls == 1
