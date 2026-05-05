"""PR42 — Flame adapter HTTP transport tests.

Replaces ``tests/flame/test_pr38_integration.py`` (which tested the in-process
MCP path that no longer exists). Mocks ``urllib.request.urlopen`` at the
adapter's import site to pin transport/protocol behavior.
"""
from __future__ import annotations

import json
import socket
from urllib import error

import pytest

from forge_bridge.flame.integration import run_command_from_flame


# ────────────────────────────────────────────────────────────────────────────
# Mock helpers
# ────────────────────────────────────────────────────────────────────────────


class _MockResponse:
    """Context-manager-compatible stand-in for ``urlopen``'s return value."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_MockResponse":
        return self

    def __exit__(self, *_a: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _patch_urlopen(monkeypatch, fake):
    monkeypatch.setattr(
        "forge_bridge.flame.integration.request.urlopen",
        fake,
    )


# ────────────────────────────────────────────────────────────────────────────
# Success / engine-originated envelopes pass through unchanged
# ────────────────────────────────────────────────────────────────────────────


def test_success(monkeypatch):
    _patch_urlopen(
        monkeypatch,
        lambda *_a, **_k: _MockResponse(
            b'{"status":"success","request_id":"rid","chain":[],"error":null}'
        ),
    )

    result = run_command_from_flame("list projects")

    assert result["status"] == "success"
    assert result["request_id"] == "rid"


def test_engine_error_passes_through_unchanged(monkeypatch):
    """Engine-originated error envelopes are returned verbatim, not wrapped."""
    body = (
        b'{"status":"error","request_id":"engine-rid","chain":[],'
        b'"error":{"code":"CHAIN_STEP_FAILED","message":"step 0 failed",'
        b'"step_index":0,"original_error":null}}'
    )
    _patch_urlopen(monkeypatch, lambda *_a, **_k: _MockResponse(body))

    result = run_command_from_flame("list projects")

    assert result["request_id"] == "engine-rid"
    assert result["error"]["code"] == "CHAIN_STEP_FAILED"
    assert result["error"]["step_index"] == 0


# ────────────────────────────────────────────────────────────────────────────
# Regression guard — empty input MUST route to daemon (no local short-circuit)
# ────────────────────────────────────────────────────────────────────────────


def test_empty_input_routes_to_daemon(monkeypatch):
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["payload"] = json.loads(req.data)
        return _MockResponse(
            b'{"status":"error","chain":[],"request_id":"x","error":'
            b'{"code":"EMPTY_COMMAND","message":"Nothing to execute after parsing.",'
            b'"step_index":null,"original_error":null}}'
        )

    _patch_urlopen(monkeypatch, fake_urlopen)

    result = run_command_from_flame("")

    # Critical: we MUST have called the daemon (no local short-circuit).
    assert captured["payload"] == {"text": ""}
    # And the daemon's envelope passed through unchanged.
    assert result["error"]["code"] == "EMPTY_COMMAND"
    assert result["error"]["message"] == "Nothing to execute after parsing."


# ────────────────────────────────────────────────────────────────────────────
# Context merge format + filtering
# ────────────────────────────────────────────────────────────────────────────


def test_context_merge_format(monkeypatch):
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["text"] = json.loads(req.data)["text"]
        return _MockResponse(
            b'{"status":"success","chain":[],"request_id":"x","error":null}'
        )

    _patch_urlopen(monkeypatch, fake_urlopen)

    run_command_from_flame(
        "list projects",
        context={
            "project_id": "abc",
            "shot_id": "def",
            "bad": 123,         # non-string value → dropped
            "blank": "  ",      # whitespace-only value → dropped
            "": "ignored",      # empty key → dropped
        },
    )

    assert captured["text"] == "list projects project_id=abc shot_id=def"


# ────────────────────────────────────────────────────────────────────────────
# Transport / protocol error classification (regression guards for ordering)
# ────────────────────────────────────────────────────────────────────────────


def test_url_error(monkeypatch):
    """Plain URLError (e.g. connection refused) → TRANSPORT_ERROR."""
    def raise_url_error(*_a, **_k):
        raise error.URLError("connection refused")

    _patch_urlopen(monkeypatch, raise_url_error)

    result = run_command_from_flame("x")

    assert result["error"]["code"] == "TRANSPORT_ERROR"


def test_socket_timeout(monkeypatch):
    """``socket.timeout`` is NOT a URLError subclass — must still map to TRANSPORT_ERROR."""
    def raise_timeout(*_a, **_k):
        raise socket.timeout("timed out")

    _patch_urlopen(monkeypatch, raise_timeout)

    result = run_command_from_flame("x")

    assert result["error"]["code"] == "TRANSPORT_ERROR"


def test_http_error(monkeypatch):
    """HTTPError is a URLError subclass — order matters; must hit HTTP_STATUS branch first."""
    def raise_http_error(*_a, **_k):
        raise error.HTTPError(
            url="http://x", code=500, msg="boom", hdrs=None, fp=None
        )

    _patch_urlopen(monkeypatch, raise_http_error)

    result = run_command_from_flame("x")

    assert result["error"]["code"] == "HTTP_STATUS"
    assert "500" in result["error"]["message"]


def test_invalid_json(monkeypatch):
    _patch_urlopen(
        monkeypatch,
        lambda *_a, **_k: _MockResponse(b"not json at all"),
    )

    result = run_command_from_flame("x")

    assert result["error"]["code"] == "INVALID_JSON"


def test_unknown_error_caught_for_ui_safety(monkeypatch):
    """Bare Exception catch is intentional — programming bugs must NOT escape into Flame UI."""
    def raise_attribute_error(*_a, **_k):
        raise AttributeError("something internal broke")

    _patch_urlopen(monkeypatch, raise_attribute_error)

    result = run_command_from_flame("x")

    assert result["error"]["code"] == "UNKNOWN_ERROR"
    assert "something internal broke" in result["error"]["message"]


# ────────────────────────────────────────────────────────────────────────────
# Env override
# ────────────────────────────────────────────────────────────────────────────


def test_env_override_changes_target_url(monkeypatch):
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        return _MockResponse(
            b'{"status":"success","chain":[],"request_id":"x","error":null}'
        )

    monkeypatch.setenv("FORGE_CONSOLE_URL", "http://test-host:5555")
    _patch_urlopen(monkeypatch, fake_urlopen)

    run_command_from_flame("list projects")

    assert captured["url"] == "http://test-host:5555/api/v1/exec"
