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
from typing import Any, Callable, Optional

import httpx

@dataclass(frozen=True)
class _BridgeConfig:
    """Immutable bridge connection settings — swapped atomically."""
    host: str = "127.0.0.1"
    port: int = 9999
    timeout: int = 60

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


# Module-level config — read via _config, replaced atomically by configure().
_config = _BridgeConfig(
    host=os.environ.get("FORGE_BRIDGE_HOST", "127.0.0.1"),
    port=int(os.environ.get("FORGE_BRIDGE_PORT", "9999")),
    timeout=int(os.environ.get("FORGE_BRIDGE_TIMEOUT", "60")),
)

# Legacy module-level names for backward compatibility (read-only references).
BRIDGE_HOST = _config.host
BRIDGE_PORT = _config.port
BRIDGE_TIMEOUT = _config.timeout
BRIDGE_URL = _config.url

_on_execution_callback: Optional[Callable] = None


def set_execution_callback(fn: Optional[Callable] = None) -> None:
    """Set (or clear) the execution callback. Pass None to disable."""
    global _on_execution_callback
    _on_execution_callback = fn


def configure(host: str = None, port: int = None, timeout: int = None):
    """Override bridge connection settings. Call before any tool use.

    Builds a new frozen _BridgeConfig and swaps the module-level reference
    atomically, avoiding torn reads from concurrent threads.
    """
    global _config, BRIDGE_HOST, BRIDGE_PORT, BRIDGE_TIMEOUT, BRIDGE_URL
    _config = _BridgeConfig(
        host=host if host is not None else _config.host,
        port=port if port is not None else _config.port,
        timeout=timeout if timeout is not None else _config.timeout,
    )
    # Keep legacy module-level names in sync for backward compatibility.
    BRIDGE_HOST = _config.host
    BRIDGE_PORT = _config.port
    BRIDGE_TIMEOUT = _config.timeout
    BRIDGE_URL = _config.url


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

    # Snapshot config atomically to avoid torn reads
    cfg = _config

    try:
        async with httpx.AsyncClient(timeout=cfg.timeout) as client:
            resp = await client.post(
                f"{cfg.url}/exec",
                json={"code": code, "main_thread": main_thread},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        raise BridgeConnectionError(
            f"Cannot reach FORGE Bridge at {cfg.url}. "
            "Is Flame running with the bridge hook loaded?"
        )
    except httpx.TimeoutException:
        raise BridgeConnectionError(
            f"FORGE Bridge at {cfg.url} timed out after {cfg.timeout}s. "
            "The Flame operation may still be running."
        )
    except Exception as e:
        raise BridgeConnectionError(f"Bridge communication error: {e}")

    response = BridgeResponse(
        stdout=data.get("stdout", ""),
        stderr=data.get("stderr", ""),
        result=data.get("result"),
        error=data.get("error"),
        traceback=data.get("traceback"),
    )

    if _on_execution_callback is not None:
        try:
            _on_execution_callback(code, response)
        except Exception:
            pass  # never let callback errors break bridge operation

    return response


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
