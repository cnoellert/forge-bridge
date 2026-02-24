"""
FORGE Bridge Client — HTTP interface to Flame's Python runtime.

Sends Python code to the FORGE Bridge HTTP server running inside Flame,
which executes it on Flame's main thread and returns stdout/stderr/result.

Architecture:
    MCP Server  →  HTTP POST /exec  →  FORGE Bridge (inside Flame)
                ←  JSON response     ←  {stdout, stderr, result, error}
"""

import json
import os
import textwrap
from dataclasses import dataclass
from typing import Any, Optional

import httpx

BRIDGE_HOST = os.environ.get("FORGE_BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("FORGE_BRIDGE_PORT", "9999"))
BRIDGE_TIMEOUT = int(os.environ.get("FORGE_BRIDGE_TIMEOUT", "30"))

BRIDGE_URL = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}"


def configure(host: str = None, port: int = None, timeout: int = None):
    """Override bridge connection settings. Call before any tool use."""
    global BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT, BRIDGE_URL
    if host is not None:
        BRIDGE_HOST = host
    if port is not None:
        BRIDGE_PORT = port
    if timeout is not None:
        BRIDGE_TIMEOUT = timeout
    BRIDGE_URL = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}"


@dataclass
class BridgeResponse:
    """Parsed response from FORGE Bridge."""

    stdout: str
    stderr: str
    result: Any
    error: Optional[str]
    traceback: Optional[str]

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def output(self) -> str:
        """Combined stdout output, stripped."""
        return self.stdout.strip()

    def raise_on_error(self) -> "BridgeResponse":
        """Raise if the bridge returned an error."""
        if self.error:
            detail = self.traceback or self.error
            raise BridgeError(detail)
        return self


class BridgeError(Exception):
    """Raised when Flame code execution fails."""

    pass


class BridgeConnectionError(Exception):
    """Raised when the bridge is unreachable."""

    pass


async def execute(code: str, *, main_thread: bool = False) -> BridgeResponse:
    """Execute Python code on Flame via FORGE Bridge.

    Args:
        code: Python source code to execute. The `flame` module is
              pre-imported in the bridge namespace.
        main_thread: If True, execute on Flame's Qt main thread
                     (required for write operations like set_value,
                     create, delete).

    Returns:
        BridgeResponse with stdout, stderr, result, and error fields.

    Raises:
        BridgeConnectionError: If the bridge is unreachable.
    """
    code = textwrap.dedent(code).strip()

    try:
        async with httpx.AsyncClient(timeout=BRIDGE_TIMEOUT) as client:
            resp = await client.post(
                f"{BRIDGE_URL}/exec",
                json={"code": code, "main_thread": main_thread},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        raise BridgeConnectionError(
            f"Cannot reach FORGE Bridge at {BRIDGE_URL}. "
            "Is Flame running with the bridge hook loaded?"
        )
    except httpx.TimeoutException:
        raise BridgeConnectionError(
            f"FORGE Bridge at {BRIDGE_URL} timed out after {BRIDGE_TIMEOUT}s. "
            "The Flame operation may still be running."
        )
    except Exception as e:
        raise BridgeConnectionError(f"Bridge communication error: {e}")

    return BridgeResponse(
        stdout=data.get("stdout", ""),
        stderr=data.get("stderr", ""),
        result=data.get("result"),
        error=data.get("error"),
        traceback=data.get("traceback"),
    )


async def execute_and_read(code: str, *, main_thread: bool = False) -> str:
    """Execute code and return stdout, raising on errors."""
    resp = await execute(code, main_thread=main_thread)
    resp.raise_on_error()
    return resp.output


async def execute_json(code: str, *, main_thread: bool = False) -> Any:
    """Execute code that prints JSON, parse and return it.

    The code should print exactly one JSON object/array to stdout.
    """
    output = await execute_and_read(code, main_thread=main_thread)
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        raise BridgeError(
            f"Expected JSON from bridge, got: {output[:200]!r}\nParse error: {e}"
        )


async def ping() -> bool:
    """Check if the bridge is reachable and Flame is connected."""
    try:
        resp = await execute("print('ok')")
        return resp.ok and "ok" in resp.stdout
    except BridgeConnectionError:
        return False
