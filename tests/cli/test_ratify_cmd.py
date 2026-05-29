"""A.2 D8 — `fbridge ratify` CLI surface tests."""
from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from forge_bridge.cli import main as main_module
from forge_bridge.cli.main import _RatifyTransportError, _ratify_http, app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _apply_complete(graph_intent_id: str = "4bd83c2f1abc") -> dict:
    return {
        "apply_complete": {
            "kind": "apply_complete",
            "graph_intent_id": graph_intent_id,
            "chain": {"status": "success", "chain": [{"step": "commit x"}]},
            "stop_reason": "apply_complete",
            "chat_regime": "ratified_apply",
            "transport": "json",
        }
    }


def test_ratify_http_posts_graph_intent_and_actor(monkeypatch):
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_apply_complete())

    monkeypatch.setenv("FORGE_CONSOLE_HOST", "127.0.0.9")
    monkeypatch.setenv("FORGE_CONSOLE_PORT", "4455")

    body = _ratify_http("4bd83c2f1abc", "jdoe", client=_client(handler))

    assert body["apply_complete"]["graph_intent_id"] == "4bd83c2f1abc"
    assert captured["url"] == "http://127.0.0.9:4455/api/v1/ratify"
    assert captured["body"] == {"graph_intent_id": "4bd83c2f1abc", "actor": "jdoe"}


def test_ratify_http_connect_error_classified():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(_RatifyTransportError) as exc_info:
        _ratify_http("4bd83c2f1abc", "local", client=_client(handler))

    assert exc_info.value.url.endswith("/api/v1/ratify")
    assert exc_info.value.reason == "ConnectError"


def test_cli_ratify_success_default_renders_apply_result(runner, monkeypatch):
    monkeypatch.setattr(main_module, "_ratify_http", lambda graph_id, actor: _apply_complete(graph_id))

    result = runner.invoke(app, ["ratify", "4bd83c2f1abc"])

    assert result.exit_code == 0
    assert "apply_complete" in result.stdout
    assert "4bd83c2f1abc" in result.stdout


def test_cli_ratify_unknown_record_exits_1(runner, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "_ratify_http",
        lambda graph_id, actor: {
            "error": {
                "code": "assent_record_not_found",
                "message": "No AssentRecord found.",
                "details": {"graph_intent_id": graph_id},
            }
        },
    )

    result = runner.invoke(app, ["ratify", "4bd83c2f1abc", "--json"])

    assert result.exit_code == 1
    body = json.loads(result.stdout)
    assert body["error"]["code"] == "assent_record_not_found"


def test_cli_ratify_already_applied_exits_1(runner, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "_ratify_http",
        lambda graph_id, actor: {
            "error": {
                "code": "assent_illegal_state",
                "message": "AssentRecord is not in a ratifiable state.",
                "details": {
                    "graph_intent_id": graph_id,
                    "current_status": "applied",
                },
            }
        },
    )

    result = runner.invoke(app, ["ratify", "4bd83c2f1abc", "--json"])

    assert result.exit_code == 1
    body = json.loads(result.stdout)
    assert body["error"]["code"] == "assent_illegal_state"
    assert body["error"]["details"]["current_status"] == "applied"


def test_cli_ratify_invalid_graph_intent_rejected_before_dispatch(runner, monkeypatch):
    called = False

    def fake_ratify(graph_id, actor):
        nonlocal called
        called = True
        return _apply_complete(graph_id)

    monkeypatch.setattr(main_module, "_ratify_http", fake_ratify)

    result = runner.invoke(app, ["ratify", "INVALID_FORMAT", "--json"])

    assert result.exit_code == 1
    assert not called
    body = json.loads(result.stdout)
    assert body["error"]["code"] == "validation_error"


def test_cli_ratify_actor_passed_to_daemon(runner, monkeypatch):
    captured = {}

    def fake_ratify(graph_id, actor):
        captured["actor"] = actor
        return _apply_complete(graph_id)

    monkeypatch.setattr(main_module, "_ratify_http", fake_ratify)

    result = runner.invoke(app, ["ratify", "4bd83c2f1abc", "--actor", "jdoe"])

    assert result.exit_code == 0
    assert captured["actor"] == "jdoe"


def test_cli_ratify_whitespace_actor_rejected_before_dispatch(runner, monkeypatch):
    called = False

    def fake_ratify(graph_id, actor):
        nonlocal called
        called = True
        return _apply_complete(graph_id)

    monkeypatch.setattr(main_module, "_ratify_http", fake_ratify)

    result = runner.invoke(app, ["ratify", "4bd83c2f1abc", "--actor", "  ", "--json"])

    assert result.exit_code == 1
    assert not called
    assert json.loads(result.stdout)["error"]["code"] == "validation_error"


def test_cli_ratify_json_stdout_is_only_json(runner, monkeypatch):
    monkeypatch.setattr(main_module, "_ratify_http", lambda graph_id, actor: _apply_complete(graph_id))

    result = runner.invoke(app, ["ratify", "4bd83c2f1abc", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["apply_complete"]["graph_intent_id"] == "4bd83c2f1abc"
    assert result.stderr == ""


def test_cli_ratify_daemon_down_exits_2_with_envelope(runner, monkeypatch):
    def fake_ratify(graph_id, actor):
        raise _RatifyTransportError("http://127.0.0.1:9996/api/v1/ratify", "ConnectError")

    monkeypatch.setattr(main_module, "_ratify_http", fake_ratify)

    result = runner.invoke(app, ["ratify", "4bd83c2f1abc", "--json"])

    assert result.exit_code == 2
    body = json.loads(result.stdout)
    assert body["error"]["code"] == "daemon_unreachable"
    assert body["error"]["url"].endswith("/api/v1/ratify")


def test_cli_ratify_help_shows_locked_text(runner):
    result = runner.invoke(app, ["ratify", "--help"])

    assert result.exit_code == 0
    assert "12-char graph-intent identifier from a prior" in result.stdout
    assert "chat preview" in result.stdout
    assert "Caller identity (free string; future SEED-AUTH" in result.stdout
    assert "integration point" in result.stdout
    assert "Emit JSON result instead of Rich-rendered table" in result.stdout
