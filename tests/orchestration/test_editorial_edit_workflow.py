"""Focused matrix for the #235 / Phase 149 editorial-edit workflow API.

These exercise the new workflow ORCHESTRATION with fakes: the real
``discover_live_flame_realization`` / ``build_live_flame_realization_preview_spec``
and the commit rail are monkeypatched or injected, because their internals are
already proven by the #229-#231 live-editorial suites. Here we prove the closed
contract, durable lifecycle, fences, idempotency, replay, and restore gating.
"""

from __future__ import annotations

import asyncio
import itertools

import pytest

import forge_bridge.orchestration.editorial_edit_workflow as eew
from forge_bridge.orchestration.editorial_edit_workflow import (
    PROPOSAL_KIND,
    RECEIPT_KIND,
    EditorialEditWorkflowAPI,
    EditorialEditWorkflowError,
    InMemoryEditorialEditWorkflowStore,
    canonical_fingerprint,
)
from forge_bridge.orchestration.live_editorial_vertical import (
    LiveEditorialVerticalError,
)


# --------------------------------------------------------------------------- #
# Fixtures / fakes
# --------------------------------------------------------------------------- #
def _h(seed: str) -> str:
    return canonical_fingerprint(seed)


def make_proposal(*, operation: str = "trim_tail", tag: str = "a", **overrides):
    step_plan = {
        "plan_id": f"plan-{tag}",
        "steps": [
            {
                "operation": operation,
                "step_id": f"step-{tag}",
                "node_id": f"node-{tag}",
                "params": {"sequence_id": "seq-1", "new_frame_out": {"number": 10}},
            }
        ],
    }
    proposal = {
        "kind": PROPOSAL_KIND,
        "schema_version": 1,
        "preview_id": f"preview-{tag}",
        "project_id": "proj-1",
        "sequence_id": "seq-1",
        "sequence_name": "FORGE_UAT_HOST_APPLY_20260624",
        "requested_by": "operator@example",
        "source_authority": "catalog",
        "source_fingerprint": _h(f"src-{tag}"),
        "preview_authority_fingerprint": _h(f"pa-{tag}"),
        "preview_fingerprint": _h(f"pf-{tag}"),
        "interaction_fingerprint": _h(f"if-{tag}"),
        "source_state_fingerprint": _h(f"sstate-{tag}"),
        "after_state_fingerprint": _h(f"astate-{tag}"),
        "step_plan": step_plan,
        "step_plan_fingerprint": canonical_fingerprint(step_plan),
        "delta_fingerprint": _h(f"delta-{tag}"),
        "semantic_capability_plan_fingerprint": _h(f"scpf-{tag}"),
        "expected_geometry_fingerprint": _h(f"geo-{tag}"),
    }
    proposal.update(overrides)
    body = {k: v for k, v in proposal.items() if k != "fingerprint"}
    proposal["fingerprint"] = canonical_fingerprint(body)
    return proposal


def _discovery_for(proposal, *, step_plan=None, rpf="rpf"):
    plan = step_plan if step_plan is not None else proposal["step_plan"]
    return {
        "live_state_fingerprint": proposal["source_state_fingerprint"],
        "step_plan_fingerprint": canonical_fingerprint(plan),
        "semantic_discovery": {
            "capability_plan_fingerprint": proposal[
                "semantic_capability_plan_fingerprint"
            ],
        },
        "realization_discovery": {
            "delta_fingerprint": proposal["delta_fingerprint"],
            "realization_plan_fingerprint": _h(rpf),
        },
    }


class _Recorder:
    def __init__(self):
        self.preview_calls = 0
        self.apply_calls = 0
        self.apply_actors = []
        self._ids = itertools.count(1)
        self.apply_outcome = {
            "outcome": "applied",
            "assent_status": "applied",
            "reason_code": None,
            "commit_result": {"type": "commit_applied", "count": 1},
        }
        self.apply_delay = 0.0

    async def preview_fn(self, *, spec, display):
        self.preview_calls += 1
        n = next(self._ids)
        return {
            "graph_intent_id": f"intent-{n}",
            "assent_record_id": f"assent-{n}",
            "manifest": {
                "apply_counterpart": {"tool": "forge_apply_segment_temporal_delta"},
                "intent_parameters": {"sequence_name": spec_seq(spec, display)},
                "resolved_plan": [{"i": n}],
                "type": "editorial_delta",
            },
        }

    async def apply_fn(self, *, graph_intent_id, requested_by):
        self.apply_calls += 1
        self.apply_actors.append(requested_by)
        if self.apply_delay:
            await asyncio.sleep(self.apply_delay)
        return dict(self.apply_outcome)


def spec_seq(spec, display):
    # spec is a sentinel in these tests; the manifest sequence name is fixed.
    return "FORGE_UAT_HOST_APPLY_20260624"


def build_api(monkeypatch, *, recorder=None, store=None, discovery_fn=None,
              build_inverse=None):
    recorder = recorder or _Recorder()
    store = store if store is not None else InMemoryEditorialEditWorkflowStore()

    async def fake_discover(step_plan, *, sequence_name, run_operation,
                            project_id=None, requested_by=None, **_):
        if discovery_fn is not None:
            return discovery_fn(step_plan)
        # default: build a discovery consistent with the single active proposal
        return _default_discovery(step_plan)

    monkeypatch.setattr(eew, "discover_live_flame_realization", fake_discover)
    monkeypatch.setattr(
        eew, "build_live_flame_realization_preview_spec",
        lambda **kwargs: ("SPEC", kwargs.get("sequence_name")),
    )

    api = EditorialEditWorkflowAPI(
        run_operation=lambda *a, **k: None,
        preview_fn=recorder.preview_fn,
        apply_fn=recorder.apply_fn,
        store=store,
        build_inverse_step_plan=build_inverse,
        clock=lambda: "2026-07-22T00:00:00Z",
    )
    return api, recorder, store


# module-level holder so the default discover can see the active proposal
_ACTIVE = {}


def _default_discovery(step_plan):
    proposal = _ACTIVE["proposal"]
    return _discovery_for(proposal, step_plan=step_plan)


@pytest.fixture(autouse=True)
def _reset_active():
    _ACTIVE.clear()
    yield
    _ACTIVE.clear()


def _activate(proposal):
    _ACTIVE["proposal"] = proposal


# --------------------------------------------------------------------------- #
# Contract & persistence
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_accepts_exact_proposal_and_returns_closed_receipt(monkeypatch):
    api, rec, _ = build_api(monkeypatch)
    proposal = make_proposal()
    _activate(proposal)

    receipt = await api.propose(proposal)

    assert receipt["kind"] == RECEIPT_KIND
    assert receipt["action"] == "propose"
    assert receipt["status"] == "proposed"
    assert receipt["assent_status"] == "proposed"
    assert receipt["manifest_fingerprint"]
    assert receipt["dispatch_authorized"] is False
    assert receipt["applied"] is False
    assert receipt["reason_code"] is None
    # closed + canonically fingerprinted
    assert set(receipt.keys()) == set(eew._RECEIPT_KEYS) | {"fingerprint"}
    body = {k: v for k, v in receipt.items() if k != "fingerprint"}
    assert receipt["fingerprint"] == canonical_fingerprint(body)
    assert rec.apply_calls == 0  # no MCP apply during propose


@pytest.mark.asyncio
async def test_rejects_unknown_field(monkeypatch):
    api, _, _ = build_api(monkeypatch)
    proposal = make_proposal()
    proposal["surprise"] = "nope"
    proposal["fingerprint"] = canonical_fingerprint(
        {k: v for k, v in proposal.items() if k != "fingerprint"}
    )
    with pytest.raises(EditorialEditWorkflowError) as exc:
        await api.propose(proposal)
    assert exc.value.code == eew.REASON_PROPOSAL_INVALID


@pytest.mark.asyncio
async def test_rejects_bad_proposal_fingerprint(monkeypatch):
    api, _, _ = build_api(monkeypatch)
    proposal = make_proposal()
    proposal["fingerprint"] = _h("wrong")
    with pytest.raises(EditorialEditWorkflowError) as exc:
        await api.propose(proposal)
    assert exc.value.code == eew.REASON_PROPOSAL_INVALID


@pytest.mark.asyncio
async def test_rejects_multi_step_plan(monkeypatch):
    api, _, _ = build_api(monkeypatch)
    proposal = make_proposal()
    proposal["step_plan"]["steps"].append(dict(proposal["step_plan"]["steps"][0]))
    proposal["step_plan_fingerprint"] = canonical_fingerprint(
        proposal["step_plan"]
    )
    proposal["fingerprint"] = canonical_fingerprint(
        {k: v for k, v in proposal.items() if k != "fingerprint"}
    )
    with pytest.raises(EditorialEditWorkflowError) as exc:
        await api.propose(proposal)
    assert exc.value.code == eew.REASON_PROPOSAL_INVALID


@pytest.mark.asyncio
async def test_exact_duplicate_propose_is_idempotent(monkeypatch):
    api, rec, _ = build_api(monkeypatch)
    proposal = make_proposal()
    _activate(proposal)
    first = await api.propose(proposal)
    second = await api.propose(proposal)
    assert first["proposal_id"] == second["proposal_id"]
    assert first["workflow_id"] == second["workflow_id"]
    assert first["fingerprint"] == second["fingerprint"]
    assert rec.preview_calls == 1  # second short-circuited, no re-discovery


@pytest.mark.asyncio
async def test_exact_duplicate_propose_retains_original_receipt_after_failure(
    monkeypatch,
):
    api, rec, _ = build_api(monkeypatch)
    proposal = make_proposal()
    proposed = await _proposed(api, proposal)
    rec.apply_outcome = {
        "outcome": "failed",
        "assent_status": "failed",
        "reason_code": eew.REASON_COMMIT_FAILED,
        "commit_result": {"type": "commit_failed"},
    }

    failed = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by="ratifier@example",
    )
    duplicate = await api.propose(proposal)

    assert failed["status"] == "failed"
    assert duplicate == proposed
    assert rec.preview_calls == 1
    assert rec.apply_calls == 1


@pytest.mark.asyncio
async def test_preview_authority_collision_refuses(monkeypatch):
    api, _, store = build_api(monkeypatch)
    a = make_proposal(tag="a")
    b = make_proposal(tag="b")
    # force same preview authority, different content
    b["preview_authority_fingerprint"] = a["preview_authority_fingerprint"]
    b["fingerprint"] = canonical_fingerprint(
        {k: v for k, v in b.items() if k != "fingerprint"}
    )
    _activate(a)
    await api.propose(a)
    _activate(b)
    with pytest.raises(EditorialEditWorkflowError) as exc:
        await api.propose(b)
    assert exc.value.code == eew.REASON_PROPOSAL_INVALID


@pytest.mark.asyncio
async def test_survives_service_reconstruction(monkeypatch):
    store = InMemoryEditorialEditWorkflowStore()
    api1, rec, _ = build_api(monkeypatch, store=store)
    proposal = make_proposal()
    _activate(proposal)
    proposed = await api1.propose(proposal)

    # brand-new API instance, same durable store
    api2 = EditorialEditWorkflowAPI(
        run_operation=lambda *a, **k: None,
        preview_fn=rec.preview_fn,
        apply_fn=rec.apply_fn,
        store=store,
        clock=lambda: "2026-07-22T00:00:00Z",
    )
    status = await api2.status(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )
    assert status["status"] == "proposed"
    assert status["proposal_id"] == proposed["proposal_id"]


# --------------------------------------------------------------------------- #
# Propose fences
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_stale_source_state_refuses_before_assent(monkeypatch):
    def drifted(step_plan):
        d = _discovery_for(_ACTIVE["proposal"], step_plan=step_plan)
        d["live_state_fingerprint"] = _h("moved")
        return d

    api, rec, _ = build_api(monkeypatch, discovery_fn=drifted)
    proposal = make_proposal()
    _activate(proposal)
    with pytest.raises(EditorialEditWorkflowError) as exc:
        await api.propose(proposal)
    assert exc.value.code == eew.REASON_LIVE_STATE_DRIFT
    assert rec.preview_calls == 0  # refused before manifest persistence


@pytest.mark.asyncio
async def test_delta_drift_refuses(monkeypatch):
    def drifted(step_plan):
        d = _discovery_for(_ACTIVE["proposal"], step_plan=step_plan)
        d["realization_discovery"]["delta_fingerprint"] = _h("otherdelta")
        return d

    api, _, _ = build_api(monkeypatch, discovery_fn=drifted)
    proposal = make_proposal()
    _activate(proposal)
    with pytest.raises(EditorialEditWorkflowError) as exc:
        await api.propose(proposal)
    assert exc.value.code == eew.REASON_DELTA_DRIFT


@pytest.mark.asyncio
async def test_realization_hold_refuses_before_manifest(monkeypatch):
    def blocked(step_plan):
        raise LiveEditorialVerticalError("exact realization is not trusted")

    api, rec, _ = build_api(monkeypatch, discovery_fn=blocked)
    proposal = make_proposal()
    _activate(proposal)
    with pytest.raises(EditorialEditWorkflowError) as exc:
        await api.propose(proposal)
    assert exc.value.code == eew.REASON_REALIZATION_BLOCKED
    assert rec.preview_calls == 0


# --------------------------------------------------------------------------- #
# Ratify / apply
# --------------------------------------------------------------------------- #
async def _proposed(api, proposal):
    _activate(proposal)
    return await api.propose(proposal)


@pytest.mark.asyncio
async def test_ratify_apply_applies_once_and_retains_authority(monkeypatch):
    api, rec, _ = build_api(monkeypatch)
    proposal = make_proposal()
    proposed = await _proposed(api, proposal)

    applied = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by="ratifier@example",
    )
    assert applied["status"] == "applied"
    assert applied["assent_status"] == "applied"
    assert applied["applied"] is True
    assert applied["replayed"] is False and applied["restored"] is False
    assert applied["dispatch_authorized"] is True
    assert applied["commit_fingerprint"]
    # retains every proposed authority field
    for key in (
        "proposal_fingerprint", "preview_id", "preview_authority_fingerprint",
        "step_plan_fingerprint", "semantic_capability_plan_fingerprint",
        "delta_fingerprint",
    ):
        assert applied[key] == proposed[key]
    assert rec.apply_calls == 1


@pytest.mark.asyncio
async def test_ratify_apply_never_returns_ratified(monkeypatch):
    api, _, _ = build_api(monkeypatch)
    proposed = await _proposed(api, make_proposal())
    applied = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by="r",
    )
    assert applied["status"] != "ratified"


@pytest.mark.asyncio
async def test_wrong_expected_fingerprint_refuses(monkeypatch):
    api, rec, _ = build_api(monkeypatch)
    proposed = await _proposed(api, make_proposal())
    out = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=_h("wrong"),
        requested_by="r",
    )
    assert out["status"] == "refused"
    assert out["reason_code"] == eew.REASON_PROPOSAL_CHANGED
    assert rec.apply_calls == 0  # refused before ratification


@pytest.mark.asyncio
async def test_verify_drift_marks_failed_truthfully(monkeypatch):
    api, rec, _ = build_api(monkeypatch)
    rec.apply_outcome = {
        "outcome": "failed",
        "assent_status": "failed",
        "reason_code": eew.REASON_COMMIT_FAILED,
        "commit_result": {"error": {"type": "PLAN_STATE_DRIFT"}},
    }
    proposed = await _proposed(api, make_proposal())
    out = await api.ratify_apply(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by="r",
    )
    assert out["status"] == "failed"
    assert out["assent_status"] == "failed"
    assert out["applied"] is False
    assert out["dispatch_authorized"] is False
    assert out["reason_code"] == eew.REASON_COMMIT_FAILED


@pytest.mark.asyncio
async def test_second_apply_after_applied_refuses_state_invalid(monkeypatch):
    api, rec, _ = build_api(monkeypatch)
    proposed = await _proposed(api, make_proposal())
    args = dict(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by="r",
    )
    await api.ratify_apply(**args)
    second = await api.ratify_apply(**args)
    assert second["status"] == "refused"
    assert second["reason_code"] == eew.REASON_STATE_INVALID
    assert rec.apply_calls == 1  # only one host dispatch


@pytest.mark.asyncio
async def test_two_concurrent_applies_dispatch_once(monkeypatch):
    api, rec, _ = build_api(monkeypatch)
    rec.apply_delay = 0.02
    proposed = await _proposed(api, make_proposal())
    args = dict(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by="r",
    )
    results = await asyncio.gather(
        api.ratify_apply(**args), api.ratify_apply(**args)
    )
    statuses = sorted(r["status"] for r in results)
    assert statuses == ["applied", "refused"]
    assert rec.apply_calls == 1


# --------------------------------------------------------------------------- #
# Status & replay
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_status_is_read_only_and_reports_terminals(monkeypatch):
    api, rec, _ = build_api(monkeypatch)
    proposed = await _proposed(api, make_proposal())
    args = dict(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )
    s0 = await api.status(**args)
    assert s0["status"] == "proposed" and s0["applied"] is False
    await api.ratify_apply(**args, requested_by="r")
    s1 = await api.status(**args)
    assert s1["status"] == "applied" and s1["applied"] is True
    assert s1["dispatch_authorized"] is True
    assert rec.apply_calls == 1  # status never dispatched


@pytest.mark.asyncio
async def test_replay_before_apply_refuses(monkeypatch):
    api, rec, _ = build_api(monkeypatch)
    proposed = await _proposed(api, make_proposal())
    out = await api.replay(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by="r",
    )
    assert out["status"] == "refused"
    assert out["reason_code"] == eew.REASON_REPLAY_UNAVAILABLE
    assert rec.apply_calls == 0


@pytest.mark.asyncio
async def test_replay_after_apply_returns_original_commit_no_dispatch(monkeypatch):
    api, rec, store = build_api(monkeypatch)
    proposed = await _proposed(api, make_proposal())
    args = dict(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )
    applied = await api.ratify_apply(**args, requested_by="r")
    replayed = await api.replay(**args, requested_by="r")
    assert replayed["status"] == "replayed"
    assert replayed["replayed"] is True
    assert replayed["applied"] is False and replayed["restored"] is False
    assert replayed["dispatch_authorized"] is True
    assert replayed["commit_fingerprint"] == applied["commit_fingerprint"]
    assert rec.apply_calls == 1  # replay performed zero additional dispatch

    # reconnect: new API on same store preserves replay behavior
    api2 = EditorialEditWorkflowAPI(
        run_operation=lambda *a, **k: None,
        preview_fn=rec.preview_fn, apply_fn=rec.apply_fn, store=store,
        clock=lambda: "2026-07-22T00:00:00Z",
    )
    replayed2 = await api2.replay(**args, requested_by="r")
    assert replayed2["commit_fingerprint"] == applied["commit_fingerprint"]
    assert rec.apply_calls == 1


# --------------------------------------------------------------------------- #
# Restore
# --------------------------------------------------------------------------- #
async def _build_inverse_ok(*, workflow, run_operation):
    return {
        "plan_id": "inverse-plan",
        "steps": [
            {
                "operation": "extend_edit",
                "step_id": "inv",
                "node_id": "inv-node",
                "params": {"side": "tail", "frame": {"number": 11}},
            }
        ],
    }


@pytest.mark.asyncio
async def test_split_restore_is_gated(monkeypatch):
    api, rec, _ = build_api(
        monkeypatch, build_inverse=_build_inverse_ok
    )
    proposal = make_proposal(operation="split_at_playhead")
    proposed = await _proposed(api, proposal)
    args = dict(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )
    await api.ratify_apply(**args, requested_by="r")
    out = await api.restore(**args, requested_by="r")
    assert out["status"] == "refused"
    assert out["reason_code"] == eew.REASON_RESTORE_UNAVAILABLE


@pytest.mark.asyncio
async def test_trim_restore_without_inverse_builder_is_gated(monkeypatch):
    api, rec, _ = build_api(monkeypatch)  # no build_inverse
    proposed = await _proposed(api, make_proposal())
    args = dict(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )
    await api.ratify_apply(**args, requested_by="r")
    out = await api.restore(**args, requested_by="r")
    assert out["status"] == "refused"
    assert out["reason_code"] == eew.REASON_RESTORE_UNAVAILABLE


@pytest.mark.asyncio
async def test_restore_before_apply_refuses(monkeypatch):
    api, _, _ = build_api(monkeypatch, build_inverse=_build_inverse_ok)
    proposed = await _proposed(api, make_proposal())
    out = await api.restore(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
        requested_by="r",
    )
    assert out["status"] == "refused"
    assert out["reason_code"] == eew.REASON_RESTORE_UNAVAILABLE


@pytest.mark.asyncio
async def test_successful_trim_restore_has_separate_identities(monkeypatch):
    api, rec, _ = build_api(monkeypatch, build_inverse=_build_inverse_ok)
    proposal = make_proposal()
    proposed = await _proposed(api, proposal)
    args = dict(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )
    applied = await api.ratify_apply(**args, requested_by="r")
    restored = await api.restore(**args, requested_by="op")

    assert restored["status"] == "restored"
    assert restored["restored"] is True
    assert restored["applied"] is False and restored["replayed"] is False
    assert restored["dispatch_authorized"] is True
    # forward proposal identity retained
    assert restored["proposal_fingerprint"] == proposed["proposal_fingerprint"]
    assert restored["preview_id"] == proposed["preview_id"]
    assert restored["step_plan_fingerprint"] == proposed["step_plan_fingerprint"]
    # inverse identities differ from the forward apply
    assert restored["assent_record_id"] != applied["assent_record_id"]
    assert restored["commit_fingerprint"]
    # forward + inverse were two separate host dispatches
    assert rec.apply_calls == 2


@pytest.mark.asyncio
async def test_restore_inverse_failure_is_not_restored(monkeypatch):
    api, rec, _ = build_api(monkeypatch, build_inverse=_build_inverse_ok)
    proposed = await _proposed(api, make_proposal())
    args = dict(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )
    await api.ratify_apply(**args, requested_by="r")
    # make the inverse apply fail
    rec.apply_outcome = {
        "outcome": "failed",
        "assent_status": "failed",
        "reason_code": eew.REASON_COMMIT_FAILED,
        "commit_result": {"error": {"type": "APPLY_FAILED"}},
    }
    out = await api.restore(**args, requested_by="op")
    assert out["status"] == "refused"
    assert out["restored"] is False
    assert out["reason_code"] == eew.REASON_RESTORE_FAILED
    # forward apply still stands
    status = await api.status(**args)
    assert status["status"] == "applied"


@pytest.mark.asyncio
async def test_restore_stale_host_refuses_drift(monkeypatch):
    async def stale_inverse(*, workflow, run_operation):
        raise LiveEditorialVerticalError("source_out timecode disagrees")

    api, rec, _ = build_api(monkeypatch, build_inverse=stale_inverse)
    proposed = await _proposed(api, make_proposal())
    args = dict(
        proposal_id=proposed["proposal_id"],
        expected_proposal_fingerprint=proposed["proposal_fingerprint"],
    )
    await api.ratify_apply(**args, requested_by="r")
    out = await api.restore(**args, requested_by="op")
    assert out["status"] == "refused"
    assert out["reason_code"] == eew.REASON_RESTORE_DRIFT


@pytest.mark.asyncio
async def test_proposal_not_found_raises(monkeypatch):
    api, _, _ = build_api(monkeypatch)
    with pytest.raises(EditorialEditWorkflowError) as exc:
        await api.status(
            proposal_id="eew_deadbeefdeadbeef",
            expected_proposal_fingerprint=_h("x"),
        )
    assert exc.value.code == eew.REASON_PROPOSAL_NOT_FOUND
