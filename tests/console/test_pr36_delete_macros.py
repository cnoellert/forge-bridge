"""PR36 — Safe, deterministic macro deletion via chat."""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from forge_bridge.console._macros import get_macro, register_macro
from tests.console.test_pr30_chain import _make_chain_chat_app, _text_block


@pytest.fixture
def chat_client():
    async def fake_call_tool(name, arguments):
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p as call_mock:
        yield TestClient(app), call_mock


@pytest.fixture
def client(chat_client):
    c, _ = chat_client
    return c


@pytest.fixture
def call_tool(chat_client):
    _, m = chat_client
    return m


def test_delete_existing_macro(client):
    register_macro("x", "list projects")

    resp = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "delete macro x"}]},
    )

    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert payload["deleted"] == "x"
    assert get_macro("x") is None


def test_delete_macro_empty_name_deleted_null(client):
    resp = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "delete macro     "}]},
    )

    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert payload["deleted"] is None


def test_delete_missing_macro_idempotent(client):
    resp = client.post(
        "/api/v1/chat",
        json={
            "messages": [
                {"role": "user", "content": "delete macro does_not_exist"},
            ],
        },
    )

    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert payload["deleted"] == "does_not_exist"


def test_delete_macro_does_not_execute_tools(client, call_tool):
    register_macro("x", "list projects")

    resp = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "delete macro x"}]},
    )

    assert resp.status_code == 200
    assert call_tool.call_count == 0


def test_delete_macro_trims_name(client):
    register_macro("x", "list projects")

    resp = client.post(
        "/api/v1/chat",
        json={
            "messages": [{"role": "user", "content": "delete macro   x   "}],
        },
    )

    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert payload["deleted"] == "x"
    assert get_macro("x") is None
