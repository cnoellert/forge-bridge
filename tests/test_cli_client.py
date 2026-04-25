"""CLI-02 — sync httpx client tests.

Covers: typed exceptions, envelope unwrap, port resolution, T-11-01/T-11-03/T-11-04.
"""
from __future__ import annotations

import httpx
import pytest
import typer

from forge_bridge.cli.client import (
    ServerError,
    ServerUnreachableError,
    _build_base_url,
    fetch,
    fetch_raw_envelope,
    resolve_port,
)


class TestResolvePort:
    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("FORGE_CONSOLE_PORT", raising=False)
        assert resolve_port() == 9996

    def test_valid_int(self, monkeypatch):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9997")
        assert resolve_port() == 9997

    def test_malformed_raises_exit_1(self, monkeypatch, capsys):
        # T-11-04
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "not_a_port")
        with pytest.raises(typer.Exit) as exc_info:
            resolve_port()
        assert exc_info.value.exit_code == 1
        captured = capsys.readouterr()
        assert "Invalid FORGE_CONSOLE_PORT" in captured.err

    def test_out_of_range_low_raises_exit_1(self, monkeypatch, capsys):
        # T-11-04 clamp
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "0")
        with pytest.raises(typer.Exit) as exc_info:
            resolve_port()
        assert exc_info.value.exit_code == 1
        assert "out of range" in capsys.readouterr().err

    def test_out_of_range_high_raises_exit_1(self, monkeypatch, capsys):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "65536")
        with pytest.raises(typer.Exit) as exc_info:
            resolve_port()
        assert exc_info.value.exit_code == 1


class TestBuildBaseURL:
    def test_loopback_only(self):
        # T-11-03: never any host other than 127.0.0.1
        import re
        url = _build_base_url(9996)
        assert url == "http://127.0.0.1:9996"
        assert re.match(r"^http://127\.0\.0\.1:\d+$", url)


class TestServerUnreachableError:
    def test_stores_class_name_only(self):
        # T-11-01 / LRN-05: never str(exc), only type(exc).__name__
        exc = ServerUnreachableError("ConnectError")
        assert exc.exc_class_name == "ConnectError"
        assert "ConnectError" in str(exc)


class TestFetch:
    """Unit tests for fetch() — uses httpx.MockTransport via patched __init__."""

    def _mock_client(self, monkeypatch, transport: httpx.MockTransport):
        """Patch httpx.Client to inject a MockTransport for the duration of fetch()."""
        real_client_init = httpx.Client.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            real_client_init(self, *args, **kwargs)

        monkeypatch.setattr(httpx.Client, "__init__", patched_init)

    def test_unwraps_envelope_on_200(self, monkeypatch):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"x": 1}, "meta": {}})

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        result = fetch("/api/v1/tools")
        assert result == {"x": 1}

    def test_raises_server_error_on_400(self, monkeypatch):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": {"code": "bad_request", "message": "boom"}},
            )

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        with pytest.raises(ServerError) as exc_info:
            fetch("/api/v1/tools")
        assert exc_info.value.code == "bad_request"
        assert exc_info.value.message == "boom"
        assert exc_info.value.status == 400

    def test_raises_unreachable_on_connect_error(self, monkeypatch):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        with pytest.raises(ServerUnreachableError) as exc_info:
            fetch("/api/v1/tools")
        assert exc_info.value.exc_class_name == "ConnectError"

    def test_raises_unreachable_on_timeout(self, monkeypatch):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")  # subclass of TimeoutException

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        with pytest.raises(ServerUnreachableError) as exc_info:
            fetch("/api/v1/tools")
        assert exc_info.value.exc_class_name == "ReadTimeout"

    def test_raises_unreachable_on_remote_protocol_error(self, monkeypatch):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.RemoteProtocolError("server died")

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        with pytest.raises(ServerUnreachableError) as exc_info:
            fetch("/api/v1/tools")
        assert exc_info.value.exc_class_name == "RemoteProtocolError"

    def test_malformed_error_body_surfaces_malformed_response(self, monkeypatch):
        # Server returns 500 with HTML body (no JSON envelope) — fetch() should
        # surface a generic ServerError(code='malformed_response').
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="<html>oops</html>")

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        with pytest.raises(ServerError) as exc_info:
            fetch("/api/v1/tools")
        assert exc_info.value.code == "malformed_response"
        assert exc_info.value.status == 500


class TestFetchRawEnvelope:
    """Unit tests for fetch_raw_envelope() — used by --json mode for byte-faithful output."""

    def _mock_client(self, monkeypatch, transport: httpx.MockTransport):
        real_client_init = httpx.Client.__init__

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = transport
            real_client_init(self, *args, **kwargs)

        monkeypatch.setattr(httpx.Client, "__init__", patched_init)

    def test_returns_full_envelope_on_200(self, monkeypatch):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": [1, 2], "meta": {"total": 2}})

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        envelope = fetch_raw_envelope("/api/v1/tools")
        assert envelope == {"data": [1, 2], "meta": {"total": 2}}

    def test_raises_server_error_on_400(self, monkeypatch):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": {"code": "bad_request", "message": "boom"}},
            )

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        with pytest.raises(ServerError) as exc_info:
            fetch_raw_envelope("/api/v1/tools")
        assert exc_info.value.code == "bad_request"

    def test_raises_unreachable_on_connect_error(self, monkeypatch):
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        with pytest.raises(ServerUnreachableError) as exc_info:
            fetch_raw_envelope("/api/v1/tools")
        assert exc_info.value.exc_class_name == "ConnectError"

    def test_non_json_error_body_uses_empty_dict(self, monkeypatch):
        # Server returns 503 with text/plain body — fetch_raw_envelope should
        # not crash; it should surface ServerError with default code/message.
        monkeypatch.setenv("FORGE_CONSOLE_PORT", "9996")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="service unavailable",
                                  headers={"content-type": "text/plain"})

        self._mock_client(monkeypatch, httpx.MockTransport(handler))
        with pytest.raises(ServerError) as exc_info:
            fetch_raw_envelope("/api/v1/tools")
        assert exc_info.value.status == 503
        assert exc_info.value.code == "unknown"  # default when no JSON body
