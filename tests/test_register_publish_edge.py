"""Regression: register_publish creates the version_of edge with correct kwargs.

It previously called `relationship_create(from_id=, to_id=, relationship_type=)`;
the signature is `relationship_create(source_id, target_id, rel_type)`, so the
call raised TypeError on every invocation (caught by the try/except → returned an
error envelope), leaving the publish unable to link version → shot. This locks
the corrected call.
"""

import asyncio
import json

import forge_bridge.mcp.tools as fbt
from forge_bridge.mcp.tools import register_publish, RegisterPublishInput
from forge_bridge.server.protocol import MsgType


class _CapturingClient:
    """Faithfully validates protocol-constructor kwargs (the bug was a kwargs
    mismatch), records emitted messages, returns minimal valid responses."""

    def __init__(self):
        self.sent = []

    async def request(self, msg, timeout=None):
        self.sent.append(dict(msg))
        t = msg["type"]
        if t == MsgType.ENTITY_LIST:
            return {"entities": []}  # no existing shots/versions → shot is created
        if t == MsgType.ENTITY_CREATE:
            # distinct ids per entity type so edge endpoints are unambiguous
            return {"id": "shot-new" if msg["entity_type"] == "shot" else "ver-1"}
        if t == MsgType.REL_CREATE:
            return {"ok": True}
        if t == MsgType.LOC_ADD:
            return {"ok": True}
        return {}


def _run():
    client = _CapturingClient()
    orig = fbt._client
    fbt._client = lambda: client
    try:
        out = asyncio.run(register_publish(RegisterPublishInput(
            segment_name="tst_010_graded_L01",
            output_path="/show/tst_010_graded_v001.exr",
            start_frame=1001, end_frame=1100,
            colour_space="ACEScg", project_id="proj-1",
        )))
    finally:
        fbt._client = orig
    return client, json.loads(out)


def test_register_publish_completes_without_error():
    """The from_id/to_id/relationship_type kwargs raised TypeError before the fix."""
    _client, data = _run()
    assert "error" not in data, data


def test_register_publish_emits_version_of_edge():
    client, _data = _run()
    rels = [m for m in client.sent if m["type"] == MsgType.REL_CREATE]
    assert len(rels) == 1
    edge = rels[0]
    assert edge["rel_type"] == "version_of"
    assert edge["source_id"] == "ver-1"           # version → ...
    assert edge["target_id"] == "shot-new"        # ... → shot (not version→version)
