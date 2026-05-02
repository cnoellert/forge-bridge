"""Sync httpx client wrapping /api/v1/*.

Unwraps the {data, meta} envelope on success; raises typed exceptions on error.
Every CLI subcommand uses this single client — no per-command HTTP code.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
import typer

from forge_bridge import config

logger = logging.getLogger(__name__)

_DEFAULT_PORT = config.CONSOLE_PORT
_TIMEOUT_SECONDS = 10.0


class ServerError(Exception):
    """Raised when the console API returns a 4xx/5xx envelope. Maps to exit 1."""

    def __init__(self, code: str, message: str, status: int):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(f"{code}: {message}")


class ServerUnreachableError(Exception):
    """Raised when the console API is unreachable (network/timeout). Maps to exit 2."""

    def __init__(self, exc_class_name: str):
        # LRN-05 / T-11-01: never store str(original_exc) — only the class name.
        self.exc_class_name = exc_class_name
        super().__init__(f"server unreachable ({exc_class_name})")


def resolve_port() -> int:
    """Read FORGE_CONSOLE_PORT env (default 9996); validate range; T-11-04 mitigation."""
    raw = os.environ.get("FORGE_CONSOLE_PORT", str(_DEFAULT_PORT))
    try:
        port = int(raw)
    except ValueError:
        typer.echo(f"Invalid FORGE_CONSOLE_PORT: {raw!r}", err=True)
        raise typer.Exit(code=1)
    if not (1 <= port <= 65535):
        typer.echo(
            f"FORGE_CONSOLE_PORT out of range [1, 65535]: {port}",
            err=True,
        )
        raise typer.Exit(code=1)
    return port


def _build_base_url(port: int) -> str:
    """Construct the loopback-only base URL. T-11-03: loopback enforced via config."""
    return f"http://{config.CONSOLE_HOST}:{port}"


def fetch(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET /api/v1/<path> and return the unwrapped envelope `data` field.

    Raises:
        ServerError       — HTTP 4xx/5xx with {"error": {...}} envelope (exit 1)
        ServerUnreachableError — network/timeout/protocol error (exit 2)
    """
    port = resolve_port()
    base_url = _build_base_url(port)
    try:
        with httpx.Client(base_url=base_url, timeout=_TIMEOUT_SECONDS) as client:
            response = client.get(path, params=params)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
        # T-11-01: surface the class name only, never str(exc) (which can include URLs/state).
        raise ServerUnreachableError(type(exc).__name__) from exc

    if response.status_code >= 400:
        try:
            body = response.json()
            err = body.get("error", {})
            raise ServerError(
                code=err.get("code", "unknown"),
                message=err.get("message", ""),
                status=response.status_code,
            )
        except (ValueError, KeyError, TypeError):
            # Malformed error body — surface a generic ServerError.
            raise ServerError(
                code="malformed_response",
                message=f"non-JSON error body (status {response.status_code})",
                status=response.status_code,
            ) from None

    # 2xx — unwrap envelope
    body = response.json()
    return body.get("data")


def fetch_raw_envelope(path: str, params: dict[str, Any] | None = None) -> dict:
    """Like fetch(), but returns the FULL {data, meta} envelope unchanged.

    Used by --json mode to emit byte-faithful API responses. Same exception contract.
    """
    port = resolve_port()
    base_url = _build_base_url(port)
    try:
        with httpx.Client(base_url=base_url, timeout=_TIMEOUT_SECONDS) as client:
            response = client.get(path, params=params)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
        raise ServerUnreachableError(type(exc).__name__) from exc
    if response.status_code >= 400:
        body = (
            response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        err = body.get("error", {})
        raise ServerError(
            code=err.get("code", "unknown"),
            message=err.get("message", ""),
            status=response.status_code,
        )
    return response.json()
