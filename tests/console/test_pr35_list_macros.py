"""PR35 — Read-only macro listing via chat."""
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


def test_list_macros_empty(chat_client):
    client, _ = chat_client
    resp = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "list macros"}]},
    )

    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert payload["macros"] == {}


def test_list_macros_returns_copy(chat_client):
    client, _ = chat_client
    register_macro("x", "list projects")

    resp = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "list macros"}]},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"

    payload["macros"]["x"] = "modified"

    assert get_macro("x") == "list projects"


def test_list_macros_returns_registered(chat_client):
    client, _ = chat_client
    register_macro("deploy_check", "list projects -> list versions")

    resp = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "list macros"}]},
    )

    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert payload["macros"].get("deploy_check") == "list projects -> list versions"


def test_list_macros_does_not_execute_chain(chat_client):
    client, call_mock = chat_client
    register_macro("test_macro", "list projects")

    resp = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "list macros"}]},
    )

    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert call_mock.call_count == 0
