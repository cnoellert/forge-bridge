from __future__ import annotations

import time

import pytest

from forge_bridge.console import _engine
from forge_bridge.core.assent import AssentRecord


@pytest.mark.asyncio
async def test_run_chain_steps_passes_ratified_assent_to_apply_replay(monkeypatch):
    assent = AssentRecord(
        graph_intent_id="abc123def456",
        chain_steps=["list shots", "commit", "format"],
        status="ratified",
    )
    seen: list[tuple[str, AssentRecord | None]] = []

    async def fake_execute_chain_step(
        *,
        step_text,
        tools,
        mcp,
        inherited_context,
        step_index=0,
        assent_record=None,
    ):
        _ = (tools, mcp, inherited_context, step_index)
        seen.append((step_text, assent_record))
        return {
            "result": {"step": step_text},
            "extracted_context": {},
            "emitted_topology": {"kind": "scalar", "type": "dict"},
        }

    monkeypatch.setattr(_engine, "execute_chain_step", fake_execute_chain_step)

    result = await _engine.run_chain_steps(
        steps=["list shots", "commit", "format"],
        tools=[],
        mcp=object(),
        request_id="req",
        client_ip="127.0.0.1",
        started=time.monotonic(),
        assent_record=assent,
    )

    assert result["status"] == "success"
    assert seen == [
        ("list shots", assent),
        ("commit", assent),
        ("format", assent),
    ]
