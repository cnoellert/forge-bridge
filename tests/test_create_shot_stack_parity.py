"""Regression: tool-created stacks mirror core Stack shot membership."""

import asyncio
import json

import forge_bridge.mcp.tools as fbt
from forge_bridge.mcp.tools import CreateShotInput, create_shot
from forge_bridge.server.protocol import MsgType


class _CapturingClient:
    """Record create_shot protocol messages and return stable ids."""

    def __init__(self):
        self.sent = []

    async def request(self, msg, timeout=None):
        self.sent.append(dict(msg))
        if msg["type"] == MsgType.ENTITY_CREATE:
            ids = {
                "shot": "shot-1",
                "stack": "stack-1",
                "layer": f"layer-{len([m for m in self.sent if m.get('entity_type') == 'layer'])}",
            }
            return {"entity_id": ids[msg["entity_type"]]}
        if msg["type"] == MsgType.REL_CREATE:
            return {"ok": True}
        return {}


def _run_create_shot():
    client = _CapturingClient()
    orig = fbt._client
    fbt._client = lambda: client
    try:
        out = asyncio.run(
            create_shot(
                CreateShotInput(
                    project_id="project-1",
                    sequence_id="sequence-1",
                    name="SHOT_010",
                    layers=[{"role": "primary"}],
                )
            )
        )
    finally:
        fbt._client = orig
    return client, json.loads(out)


def test_create_shot_stack_has_shot_id_attribute_and_member_of_edge():
    client, data = _run_create_shot()
    assert "error" not in data, data

    stack_creates = [
        msg
        for msg in client.sent
        if msg["type"] == MsgType.ENTITY_CREATE and msg["entity_type"] == "stack"
    ]
    assert len(stack_creates) == 1
    assert stack_creates[0]["attributes"]["shot_id"] == "shot-1"

    rels = [msg for msg in client.sent if msg["type"] == MsgType.REL_CREATE]
    assert len(rels) == 1
    edge = rels[0]
    assert edge["rel_type"] == "member_of"
    assert edge["source_id"] == "stack-1"
    assert edge["target_id"] == "shot-1"
