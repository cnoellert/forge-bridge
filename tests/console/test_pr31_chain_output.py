"""PR31 — Unified chain response envelope (success + failure same top-level keys)."""
from __future__ import annotations

from starlette.testclient import TestClient

from tests.console.test_pr30_chain import (
    _MSG_TOO_LONG,
    _MSG_TWO_STEP,
    _make_chain_chat_app,
    _single_project_payload,
    _text_block,
    _versions_payload,
)


def test_chain_success_has_uniform_shape():
    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"status", "request_id", "chain", "error"}
    assert body["status"] == "success"
    assert isinstance(body["request_id"], str) and body["request_id"]
    assert isinstance(body["chain"], list)
    assert body["error"] is None


def test_chain_failure_has_uniform_shape():
    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            raise RuntimeError("boom")
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        )

    assert r.status_code == 400, r.text
    body = r.json()
    assert set(body.keys()) == {"status", "request_id", "chain", "error"}
    assert body["status"] == "error"
    assert isinstance(body["request_id"], str) and body["request_id"]
    assert isinstance(body["chain"], list)
    err = body["error"]
    assert isinstance(err, dict)
    assert set(err.keys()) == {"code", "message", "step_index", "original_error"}


def test_chain_always_includes_chain_field():
    async def fake_ok(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(fake_call_tool=fake_ok)
    with list_p, back_p, call_p:
        client = TestClient(app)
        ok_body = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        ).json()

    async def fake_fail(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            raise RuntimeError("boom")
        return _text_block("{}")

    list_p2, back_p2, call_p2, app2, _ = _make_chain_chat_app(
        fake_call_tool=fake_fail,
    )
    with list_p2, back_p2, call_p2:
        client = TestClient(app2)
        fail_body = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        ).json()

    assert "chain" in ok_body and isinstance(ok_body["chain"], list)
    assert "chain" in fail_body and isinstance(fail_body["chain"], list)


def test_error_is_null_on_success():
    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        body = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        ).json()

    assert body["error"] is None


def test_error_present_on_failure():
    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            raise RuntimeError("boom")
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        body = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        ).json()

    assert isinstance(body["error"], dict)
    assert body["error"]["code"] == "CHAIN_STEP_FAILED"
    assert "message" in body["error"]
    assert body["error"]["step_index"] == 1
    assert isinstance(body["error"]["original_error"], dict)


def test_partial_trace_preserved_on_failure():
    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            raise RuntimeError("boom")
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        body = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        ).json()

    assert len(body["chain"]) == 1
    assert body["chain"][0]["step"].strip().startswith("list forge projects")


def test_chain_too_long_uses_structured_envelope():
    async def fake_call_tool(name, arguments):
        return _text_block("{}")

    list_p, back_p, call_p, app, mock_router = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TOO_LONG}]},
        )

    assert resp.status_code == 400
    payload = resp.json()

    assert payload["status"] == "error"
    assert payload["chain"] == []
    assert payload["error"]["code"] == "CHAIN_TOO_LONG"
    assert payload["error"]["step_index"] is None
    assert payload["error"]["original_error"] is None
    assert isinstance(payload["request_id"], str)
    assert payload["request_id"]
    mock_router.complete_with_tools.assert_not_called()


def test_step_index_zero_based():
    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            raise RuntimeError("fail step 0")
        return _text_block("{}")

    list_p, back_p, call_p, app, mock_router = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        )

    assert r.status_code == 400, r.text
    body = r.json()
    assert body["status"] == "error"
    assert body["error"]["step_index"] == 0
    assert body["chain"] == []
    mock_router.complete_with_tools.assert_not_called()
