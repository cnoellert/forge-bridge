"""`fbridge ratify-generation` CLI surface tests (#146)."""
from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from forge_bridge.cli import main as main_module
from forge_bridge.cli.main import (
    _RatifyTransportError,
    _ratify_generation_http,
    app,
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _grant_dict(grant_id: str = "4bd83c2f1abc") -> dict:
    return {
        "grant_id": grant_id,
        "entity_type": "generation_grant",
        "status": "ratified",
        "run_kind": "generation",
        "decided_by": "jdoe",
        "estimated_cost": {"currency": "USD", "amount": 1.5},
    }


def test_ratify_generation_http_posts_grant_and_actor(monkeypatch):
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_grant_dict())

    monkeypatch.setenv("FORGE_CONSOLE_HOST", "127.0.0.9")
    monkeypatch.setenv("FORGE_CONSOLE_PORT", "4455")

    body = _ratify_generation_http("4bd83c2f1abc", "jdoe", client=_client(handler))

    assert body["status"] == "ratified"
    assert captured["url"] == "http://127.0.0.9:4455/api/v1/ratify-generation"
    assert captured["body"] == {"grant_id": "4bd83c2f1abc", "actor": "jdoe"}


def test_ratify_generation_http_connect_error_classified():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(_RatifyTransportError) as exc_info:
        _ratify_generation_http("4bd83c2f1abc", "local", client=_client(handler))

    assert exc_info.value.url.endswith("/api/v1/ratify-generation")
    assert exc_info.value.reason == "ConnectError"


def test_cli_ratify_generation_success(runner, monkeypatch):
    monkeypatch.setattr(
        main_module, "_ratify_generation_http", lambda gid, actor: _grant_dict(gid),
    )
    result = runner.invoke(app, ["ratify-generation", "4bd83c2f1abc"])
    assert result.exit_code == 0
    assert "ratified" in result.stdout
    assert "4bd83c2f1abc" in result.stdout


def test_cli_ratify_generation_json(runner, monkeypatch):
    monkeypatch.setattr(
        main_module, "_ratify_generation_http", lambda gid, actor: _grant_dict(gid),
    )
    result = runner.invoke(app, ["ratify-generation", "4bd83c2f1abc", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["grant_id"] == "4bd83c2f1abc"
    assert body["status"] == "ratified"


def test_cli_ratify_generation_bad_id_exits_1(runner):
    result = runner.invoke(app, ["ratify-generation", "NOT-HEX"])
    assert result.exit_code == 1


def test_cli_ratify_generation_transport_error_exits_2(runner, monkeypatch):
    def _raise(gid, actor):
        raise _RatifyTransportError("http://x/api/v1/ratify-generation", "ConnectError")

    monkeypatch.setattr(main_module, "_ratify_generation_http", _raise)
    result = runner.invoke(app, ["ratify-generation", "4bd83c2f1abc"])
    assert result.exit_code == 2


def test_cli_ratify_generation_failure_exits_1(runner, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "_ratify_generation_http",
        lambda gid, actor: {"error": {"code": "illegal_transition", "message": "nope"}},
    )
    result = runner.invoke(app, ["ratify-generation", "4bd83c2f1abc"])
    assert result.exit_code == 1
