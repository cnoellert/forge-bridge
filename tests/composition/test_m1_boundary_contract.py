"""Captured-contract regression for the M1 boundary adapter.

The payloads below are VERBATIM live captures from the forge_vision
``forge_is_greenscreen`` tool through the running daemon (2026-06-18), via the
mock clip-ref convention (``mock://perception/is_greenscreen/<id>_{true,false,
abstain}``). They are real artifacts, including their volatile provenance
(uuids / timestamps / content hashes) — those fields are inert to the
assertions and are kept rather than curated, so this stays a *capture*, not a
reconstructed subset.

Why this file exists: ``test_m1_boundary_adapter.py`` exercises the engine with
hand-written minimal fixtures. Those happen to be faithful, but nothing
*enforces* that they match vision's real contract — a 15-key payload with a
nested ``artifact``, a ``verdict`` vocabulary, and ``abstention_reason`` living
*inside* ``artifact``. This file pins the adapter's status mapping against the
ACTUAL captured shapes, so a vision-side drift (``abstention_reason`` leaving
the nested artifact, the ``verdict`` vocab changing, the ``is_greenscreen``
token moving) fails HERE instead of silently mis-mapping in production. It also
makes the one-time "live daemon proof" a durable, daemon-free regression.

Load-bearing cut these three cases prove: ``status`` encodes whether the
ASSESSMENT SUCCEEDED, not the boolean answer. A confident negative is ``ok``
(the answer rides in ``output``); only a genuine abstention is ``abstained``.
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

from forge_bridge.composition.boundary import MCPToolBoundary
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.graph.ports import PortContract, PortTopology

# ── verbatim live captures (forge_is_greenscreen mock backend, 2026-06-18) ───
_REAL_TRUE = r'''{"operator_id":"is_greenscreen","content_hash":"112eecb42d3cfa48095ab7fe343c62e7e1030d978c5ada3837c277964f700400","artifact":{"artifact_id":"b714d61a-72cf-496c-a1b0-a59e7f16a680","schema_version":"0.1","provenance":{"operator_id":"is_greenscreen","execution_surface":"forge-bridge","request_id":"65421d80-7af7-4c74-b825-d34293118653","created_at":"2026-06-18T00:32:03.616188+00:00","source_artifact_ids":["gs_probe"],"backend_id":null,"backend_version_hash":null,"graph_node_id":null,"supersedes":null},"artifact_type":"IsGreenscreenAssessment","shot_id":"gs_probe","assessment_reason":"Mock grounded greenscreen.","green_regions":[{"region_norm":[0.05,0.05,0.95,0.95],"role":"greenscreen_backdrop","grounding":"mock_chroma_screen_region"}],"evidence":[{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"assessment_reason","value":"Mock grounded greenscreen.","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"frames_evaluated","value":1,"supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"clip_ref","value":"mock://perception/is_greenscreen/gs_probe_true","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"is_greenscreen","value":true,"supporting_frames":[]}],"is_greenscreen":true},"confidence":1,"evidence":[{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"assessment_reason","value":"Mock grounded greenscreen.","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"frames_evaluated","value":1,"supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"clip_ref","value":"mock://perception/is_greenscreen/gs_probe_true","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"is_greenscreen","value":true,"supporting_frames":[]}],"diagnostics":[{"category":"is_greenscreen","message":"is_greenscreen=True; regions=1"}],"verdict":"pass","artifact_refs":[{"artifact_type":"IsGreenscreenArtifact","artifact_id":"b714d61a-72cf-496c-a1b0-a59e7f16a680","payload_id":null,"locator":null}],"graph_event_id":"2569b2a53e2e429eb2ff7eefe8684042","execution_surface":"forge-bridge","request_id":"65421d80-7af7-4c74-b825-d34293118653","items":[{"region_norm":[0.05,0.05,0.95,0.95],"role":"greenscreen_backdrop","grounding":"mock_chroma_screen_region"}],"is_greenscreen":true,"shots":[{"id":"gs_probe"}],"recommendation":"grounded greenscreen"}'''

_REAL_FALSE = r'''{"operator_id":"is_greenscreen","content_hash":"d39d5d1e2066d311f82bd37e35a6b3ce339ae1be34f54403f120cd89614e7768","artifact":{"artifact_id":"576a9e01-a4fe-48ec-be09-5ea016fb73e8","schema_version":"0.1","provenance":{"operator_id":"is_greenscreen","execution_surface":"forge-bridge","request_id":"30f0a240-4b25-4d7a-b40c-a44e6a60f807","created_at":"2026-06-18T00:33:09.153633+00:00","source_artifact_ids":["neg_probe"],"backend_id":null,"backend_version_hash":null,"graph_node_id":null,"supersedes":null},"artifact_type":"IsGreenscreenAssessment","shot_id":"neg_probe","assessment_reason":"Mock grounded confident-negative (bluescreen).","green_regions":[],"evidence":[{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"assessment_reason","value":"Mock grounded confident-negative (bluescreen).","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"frames_evaluated","value":1,"supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"clip_ref","value":"mock://perception/is_greenscreen/neg_probe_false","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"is_greenscreen","value":false,"supporting_frames":[]}],"is_greenscreen":false},"confidence":1,"evidence":[{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"assessment_reason","value":"Mock grounded confident-negative (bluescreen).","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"frames_evaluated","value":1,"supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"clip_ref","value":"mock://perception/is_greenscreen/neg_probe_false","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"is_greenscreen","value":false,"supporting_frames":[]}],"diagnostics":[{"category":"is_greenscreen","message":"is_greenscreen=False; regions=0"}],"verdict":"pass","artifact_refs":[{"artifact_type":"IsGreenscreenArtifact","artifact_id":"576a9e01-a4fe-48ec-be09-5ea016fb73e8","payload_id":null,"locator":null}],"graph_event_id":"ea92b552ea0e44288f607486bf6ad0cb","execution_surface":"forge-bridge","request_id":"30f0a240-4b25-4d7a-b40c-a44e6a60f807","items":[],"is_greenscreen":false,"shots":[{"id":"neg_probe"}],"recommendation":"grounded not greenscreen"}'''

_REAL_ABSTAIN = r'''{"operator_id":"is_greenscreen","content_hash":"9b891b26333b29e8802b5858cba544982ba1bea60782cdf10830f2072032c2cb","artifact":{"artifact_id":"c95bc809-36f3-4080-948c-e1995d3e4a0c","schema_version":"0.1","provenance":{"operator_id":"is_greenscreen","execution_surface":"forge-bridge","request_id":"eb55509c-7748-4e2e-8b31-387a79bb3ffc","created_at":"2026-06-18T00:32:19.348791+00:00","source_artifact_ids":["amb_probe"],"backend_id":null,"backend_version_hash":null,"graph_node_id":null,"supersedes":null},"artifact_type":"IsGreenscreenAssessment","shot_id":"amb_probe","assessment_reason":"Mock abstention on greenscreen question.","green_regions":[],"evidence":[{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"assessment_reason","value":"Mock abstention on greenscreen question.","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"frames_evaluated","value":0,"supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"clip_ref","value":"mock://perception/is_greenscreen/amb_probe_abstain","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"abstention_reason","value":"mock_abstain","supporting_frames":[]}],"abstention_reason":"mock_abstain"},"confidence":0,"evidence":[{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"assessment_reason","value":"Mock abstention on greenscreen question.","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"frames_evaluated","value":0,"supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"clip_ref","value":"mock://perception/is_greenscreen/amb_probe_abstain","supporting_frames":[]},{"source_operator":"is_greenscreen","evidence_type":"observation","metric":"abstention_reason","value":"mock_abstain","supporting_frames":[]}],"diagnostics":[{"category":"is_greenscreen","message":"is_greenscreen=abstained; regions=0"}],"verdict":"inconclusive","artifact_refs":[{"artifact_type":"IsGreenscreenArtifact","artifact_id":"c95bc809-36f3-4080-948c-e1995d3e4a0c","payload_id":null,"locator":null}],"graph_event_id":"98ba79d800164ffc835395f6e0ccc6fb","execution_surface":"forge-bridge","request_id":"eb55509c-7748-4e2e-8b31-387a79bb3ffc","items":[],"shots":[{"id":"amb_probe"}],"recommendation":"abstained on greenscreen question"}'''


class _CaptureMCP:
    """Returns canned payloads in the established in-process wire shape.

    Mirrors ``test_m1_boundary_adapter._FakeMCP`` exactly — the wire transport
    is held constant; what THIS file varies and pins is vision's real PAYLOAD
    contract (the parsed captures above).
    """

    def __init__(self, *captures: str):
        self._payloads = [json.loads(c) for c in captures]
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        payload = self._payloads.pop(0)
        return SimpleNamespace(
            structuredContent={"result": json.dumps(payload)},
            content=[],
        )


def _gs_node(node_id: str, *, input_ports: dict | None = None) -> NodeSpec:
    return NodeSpec(
        node_id=node_id,
        operator_id="forge_is_greenscreen",
        input_ports=input_ports or {},
        output_port=PortTopology.any(),
        config={
            "arguments": {
                "shot_id": node_id,
                "clip_ref": f"mock://perception/is_greenscreen/{node_id}",
            }
        },
    )


def _boundary(*captures: str) -> MCPToolBoundary:
    return MCPToolBoundary(
        mcp=_CaptureMCP(*captures),
        run_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )


# ── true: a confident positive is ok, answer carried in output ───────────────
async def test_real_greenscreen_true_maps_to_ok():
    result = await _boundary(_REAL_TRUE).dispatch(_gs_node("gs_010"), {})
    assert result.status == "ok"
    assert result.has_usable_output is True
    assert result.output["is_greenscreen"] is True
    assert result.output["verdict"] == "pass"


# ── false: a confident NEGATIVE is also ok — status is assessment-success, ───
#    not the boolean answer; downstream branches on output["is_greenscreen"].
async def test_real_greenscreen_false_maps_to_ok_with_negative_answer():
    result = await _boundary(_REAL_FALSE).dispatch(_gs_node("neg_010"), {})
    assert result.status == "ok"
    assert result.has_usable_output is True
    assert result.output["is_greenscreen"] is False
    assert result.output["verdict"] == "pass"


# ── abstain: nested artifact.abstention_reason + verdict=inconclusive → ───────
#    abstained, no usable output, honest reason/message surfaced.
async def test_real_greenscreen_abstain_maps_to_abstained():
    result = await _boundary(_REAL_ABSTAIN).dispatch(_gs_node("amb_030"), {})
    assert result.status == "abstained"
    assert result.has_usable_output is False
    assert result.output is None
    assert result.reason_code == "mock_abstain"
    assert result.message == "abstained on greenscreen question"


# ── the report's live proof, made hermetic: true upstream -> abstain ─────────
#    downstream through the executor, with forward lineage carried.
async def test_real_chain_true_then_abstain_through_executor():
    source = _gs_node("gs_010")
    consumer = _gs_node("amb_030", input_ports={"previous": PortContract.any()})
    graph = GraphSpec(
        nodes=(source, consumer),
        edges=(Edge(from_node="gs_010", to_node="amb_030", to_port="previous"),),
    )
    boundary = _boundary(_REAL_TRUE, _REAL_ABSTAIN)  # popped in topo order

    results = await GraphExecutor(boundary.dispatch).run(graph)

    assert results["gs_010"].status == "ok"
    assert results["amb_030"].status == "abstained"
    # forward-only lineage: the downstream names its upstream's artifact id.
    assert results["amb_030"].source_artifact_ids == (results["gs_010"].artifact_id,)
