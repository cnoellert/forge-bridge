"""SKELETON — first live INLINE temporal vertical (pre-staged 2026-06-25).

Graph shape is LOCKED (Bridge+Pipeline converged); this is wiring, not redesign.

    ingest -> apply_steps -> select_delta -> host_resolve -> delta_to_manifest -> commit
    (Flame seq    (temporal    (deltas[0])    (op: project)   (boundary)        (ratified
     -> EditState)  edit)                                                         apply)

edit_state SEAM = path C (operator decision 2026-06-25, executor NOT thawed):
ingest's operation `data` IS the EditState payload, so `ingest --(state)--> apply_steps`
works with the current whole-output executor — NO select node, NO from_port.
>>> PIPELINE-PENDING: #50 reshape — make ingest's OperationResult.data == the EditState
    dict (what EditState.from_dict consumes); move evidence (flame_sequence_ingest) into
    the OperationResult envelope/logs, OFF the graph-routed data surface.

All nodes are OPERATOR nodes — ingest is NOT config (see
project_graph_represents_work_not_decisions). Remaining PENDING: the temporal edit
step (apply_steps) and the ingest input params. When #50 reshapes + merges + the env
exposes traffik entry points, this runs via the assent-required rail.

Bridge change required = ONE admission row (fork-independent):
  AdmissionRecord(operator_id="traffik.flame_sequence.ingest_edit_state",
    resolved_class="pipeline.traffik.flame_sequence.ingest_edit_state",
    dispatch_kind="operation", synchronous=True, returns_reference=False,
    no_state_mutation=True,  # sibling-contractual: reads Flame -> EditState, writes nothing
    idempotent_result=True)

Run (once filled):  python scratchpad/temporal_vertical_uat_SKELETON.py [--apply]
"""
from __future__ import annotations

from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.graph.ports import PortContract, PortTopology

SEQUENCE = "FORGE_UAT_HOST_APPLY_20260624"
FIRST_SEGMENT = "260511_HMA_FIFA_DIEGO__recharge_011_9x16"  # track 0, record_in '01:00:00+00'


def temporal_vertical_spec() -> GraphSpec:
    return GraphSpec(
        nodes=(
            # ingest operator (real id from PR #50). config.arguments carries the
            # ingest input params; PENDING: confirm the exact param set / Flame source
            # (PR #50 reads version_index/project_id/project_name + the flame data).
            # After the #50 reshape (path C), this node's data output IS the EditState,
            # so the edge below (to_port="state") feeds apply_steps.state directly.
            NodeSpec(
                node_id="ingest",
                operator_id="traffik.flame_sequence.ingest_edit_state",
                output_port=PortTopology.manifest(),
                config={"arguments": {"sequence_name": SEQUENCE}},  # PENDING: real params
            ),
            # >>> PIPELINE-PENDING #2: apply_steps consumes the ingested EditState via the
            # edge (port "state"), plus a TEMPORAL edit step (e.g. trim_tail on the first
            # segment). The delta it emits must carry a classifier-selected executor id
            # (PENDING #3) — Bridge routes by trusting that id, NOT by a hardcoded string.
            NodeSpec(
                node_id="apply_steps",
                operator_id="traffik.editorial.apply_steps",
                input_ports={"state": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
                config={"arguments": {"steps": [
                    # PENDING #2: a temporal atom on FIRST_SEGMENT, e.g.
                    # {"operation": "trim_tail", "params": {...real frames...}}
                ]}},
            ),
            NodeSpec(
                node_id="select_delta",
                operator_id="select_delta",
                input_ports={"result": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
                # config={"index": 0}  # default; set if apply_steps emits >1 delta
            ),
            NodeSpec(
                node_id="host_resolve",
                operator_id="traffik.flame_delta.host_resolve",
                input_ports={"delta": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="delta_to_manifest",
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
            NodeSpec(
                node_id="commit",
                operator_id="commit",
                input_ports={"held": PortContract.manifest_gate()},
            ),
        ),
        edges=(
            Edge(from_node="ingest", to_node="apply_steps", to_port="state"),
            Edge(from_node="apply_steps", to_node="select_delta", to_port="result"),
            Edge(from_node="select_delta", to_node="host_resolve", to_port="delta"),
            Edge(from_node="host_resolve", to_node="delta_to_manifest", to_port="deltas"),
            Edge(from_node="delta_to_manifest", to_node="commit", to_port="held"),
        ),
    )


# ── UAT runbook (once PENDING #1-3 land) ──────────────────────────────────────
# 0. Preconditions: Flame up; Pipeline v2.1.1+ in Bridge env; FORGE_PLUGINS=traffik
#    (so ingest+apply_steps+host_resolve discover WITHOUT manual register — closes
#    #116 item 2 at the same time). Note the first segment's current temporal
#    geometry (record_out/duration) for the revert check.
# 1. PREVIEW (read-only): preview_editorial_delta_for_ratification(temporal_vertical_spec(),
#    session_factory=get_async_session_factory()) -> graph_intent_id + held manifest.
#    Assert host_resolve routed via the TEMPORAL executor id (classifier-selected),
#    not held_for_review. INSPECT the manifest targets FIRST_SEGMENT.
# 2. RATIFY: fbridge ratify <graph_intent_id> --actor <you>  -> live temporal apply.
# 3. VERIFY: flame_get_sequence_segments -> first segment's record_out/duration changed
#    as intended.
# 4. REVERT: inverse temporal delta through the same path (or restore via Flame), then
#    re-probe -> geometry restored, residue-free.
# Pass = temporal edit applied live via the INLINE apply_steps-authored chain (real
# ingest, real apply_steps, select_delta in the live commit path) + clean revert.
#
# Reference oracle: scratchpad/ Gate B harness shape (name-delta) — same boundaries,
# swap the authored delta for the real ingest->apply_steps temporal output.
