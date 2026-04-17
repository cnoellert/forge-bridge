"""Tests for v1.0.1 async_client response correlation fix + sync_client narrowing.

The canonical _handle_message previously only read msg.msg_id ("id" field)
to find pending requests. Servers that distinguish between the response's
own id and the request id they are answering put the request id in
"ref_msg_id". This test suite pins the new fallback behavior:

    ref_id = msg.get("ref_msg_id") or msg.msg_id

Also covers sync_client.entity_list narrowing signature.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

from forge_bridge.client.async_client import AsyncClient, PendingRequest
from forge_bridge.client.sync_client import SyncClient
from forge_bridge.server.protocol import Message


# ── async_client ref_msg_id correlation ────────────────────────────────


@pytest.mark.asyncio
async def test_ok_response_correlates_via_ref_msg_id():
    """When server uses ref_msg_id field, the pending request resolves."""
    loop = asyncio.get_running_loop()
    client = AsyncClient(client_name="test", server_url="ws://example/ws")
    pending = PendingRequest(loop)
    client._pending["req-42"] = pending

    response = Message({
        "type":       "ok",
        "id":         "resp-7",       # response's own id (not correlation key)
        "ref_msg_id": "req-42",       # the request id we are answering
        "result":     None,
    })
    await client._handle_message(response)

    assert pending.future.done()
    assert pending.future.result() is response


@pytest.mark.asyncio
async def test_ok_response_correlates_via_id_echo_backward_compat():
    """Back-compat: servers that echo the request id in 'id' field still work."""
    loop = asyncio.get_running_loop()
    client = AsyncClient(client_name="test", server_url="ws://example/ws")
    pending = PendingRequest(loop)
    client._pending["req-77"] = pending

    response = Message({
        "type":   "ok",
        "id":     "req-77",   # id echo of request id; no ref_msg_id
        "result": None,
    })
    await client._handle_message(response)

    assert pending.future.done()


@pytest.mark.asyncio
async def test_error_response_correlates_via_ref_msg_id():
    """Error branch must use the same fallback."""
    loop = asyncio.get_running_loop()
    client = AsyncClient(client_name="test", server_url="ws://example/ws")
    pending = PendingRequest(loop)
    client._pending["req-99"] = pending

    response = Message({
        "type":       "error",
        "id":         "resp-99",
        "ref_msg_id": "req-99",
        "code":       "X",
        "message":    "nope",
    })
    await client._handle_message(response)

    assert pending.future.done()


# ── sync_client entity_list narrowing ─────────────────────────────────


def test_sync_entity_list_accepts_shot_id_kwarg():
    sig = inspect.signature(SyncClient.entity_list)
    assert "shot_id" in sig.parameters


def test_sync_entity_list_accepts_role_kwarg():
    sig = inspect.signature(SyncClient.entity_list)
    assert "role" in sig.parameters


def test_sync_entity_list_accepts_source_name_kwarg():
    sig = inspect.signature(SyncClient.entity_list)
    assert "source_name" in sig.parameters


def test_sync_entity_list_narrowing_kwargs_are_keyword_only():
    """Narrowing args must be keyword-only so positional (entity_type, project_id)
    callers still work."""
    sig = inspect.signature(SyncClient.entity_list)
    for name in ("shot_id", "role", "source_name"):
        assert sig.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY


# ── async_client must NOT gain project_name (forge-specific) ──────────


def test_async_client_does_not_add_project_name_kwarg():
    """project_name routing is projekt-forge-specific; canonical must stay clean."""
    sig = inspect.signature(AsyncClient.__init__)
    assert "project_name" not in sig.parameters
