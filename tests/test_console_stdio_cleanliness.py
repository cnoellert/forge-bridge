"""SC#1 — the P-01 critical runtime UAT.

Spawns `python -m forge_bridge` as a real subprocess, waits for the console
uvicorn task to bind, hammers :9996 with 100 concurrent GETs via httpx while
sending MCP initialize + tools/list on stdin, and verifies stdout contains
ONLY valid Content-Length-framed JSON-RPC messages (no uvicorn access log
lines, no stray bytes).

This test is the belt-and-suspenders verification for D-19..D-23:
  - D-20: custom LOGGING_CONFIG routes uvicorn to stderr.
  - D-21: access_log=False on uvicorn.Config.
  - D-22: ruff T20 lint gate bans print() in forge_bridge/console/.
  - D-23: this test.

If this test fails, the MCP stdio wire is corrupted by the console task —
P-01 regression. Zero tolerance.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_port_up(host: str, port: int, timeout: float = 15.0) -> bool:
    """Poll until the port accepts TCP connections, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.1)
    return False


def _parse_content_length_frames(raw: bytes) -> list[dict]:
    r"""Parse MCP stdio-framed JSON-RPC messages out of `raw`.

    Format per MCP spec: "Content-Length: <N>\r\n\r\n<JSON>".
    MCP stdio transport (2025-06-18 spec) also supports a newline-delimited
    JSON fallback — newline-terminated JSON objects are valid frames too.
    Returns list of parsed messages. Raises AssertionError if any stray
    bytes appear between frames (P-01 violation).
    """
    messages: list[dict] = []
    pos = 0
    n = len(raw)
    while pos < n:
        # Skip leading whitespace (newlines between frames are normal).
        while pos < n and raw[pos:pos + 1] in (b"\r", b"\n"):
            pos += 1
        if pos >= n:
            break

        # Case 1: Content-Length framed (classic LSP/MCP shape).
        header_sentinel = raw.find(b"\r\n\r\n", pos)
        looks_like_header = (
            raw[pos:pos + len(b"Content-Length:")].lower()
            == b"content-length:"
        )
        if looks_like_header and header_sentinel != -1:
            header = raw[pos:header_sentinel]
            header_str = header.decode("ascii", errors="replace").strip()
            try:
                length = int(header_str.split(":", 1)[1].strip())
            except ValueError:
                raise AssertionError(
                    f"SC#1 violation — malformed Content-Length header: "
                    f"{header_str!r}"
                )
            body_start = header_sentinel + 4  # skip \r\n\r\n
            body_end = body_start + length
            if body_end > n:
                raise AssertionError(
                    f"SC#1 violation — truncated frame: header claims {length} "
                    f"bytes but only {n - body_start} available"
                )
            body_bytes = raw[body_start:body_end]
            try:
                msg = json.loads(body_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise AssertionError(
                    f"SC#1 violation — frame body is not valid JSON: "
                    f"{body_bytes[:200]!r} ({type(exc).__name__})"
                )
            messages.append(msg)
            pos = body_end
            continue

        # Case 2: newline-delimited JSON (NDJSON-style MCP stdio).
        eol = raw.find(b"\n", pos)
        if eol == -1:
            line_bytes = raw[pos:].rstrip(b"\r\n")
        else:
            line_bytes = raw[pos:eol].rstrip(b"\r")

        # A line that doesn't decode or parse means SOMETHING non-MCP is on
        # stdout — that is exactly the P-01 failure mode.
        line_str = line_bytes.decode("utf-8", errors="replace")
        stripped = line_str.strip()
        if not stripped:
            pos = (eol + 1) if eol != -1 else n
            continue
        try:
            msg = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"SC#1 violation — non-JSON byte on stdout: {line_bytes[:200]!r} "
                f"({type(exc).__name__}). This usually means uvicorn access log "
                f"or print() leaked to stdout."
            )
        messages.append(msg)
        pos = (eol + 1) if eol != -1 else n

    return messages


async def _hammer_console(port: int, n_requests: int = 100) -> list[int]:
    """Issue N concurrent GETs to /api/v1/health; return status codes."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = [
            client.get(f"http://127.0.0.1:{port}/api/v1/health")
            for _ in range(n_requests)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    codes = []
    for r in results:
        if isinstance(r, Exception):
            codes.append(-1)
        else:
            codes.append(r.status_code)
    return codes


@pytest.mark.timeout(60)
def test_mcp_stdio_frames_are_clean_while_console_under_load(tmp_path):
    """SC#1 — P-01 critical test.

    Spawns the full MCP server + console task, hammers :9996 with 100
    concurrent requests, sends MCP initialize + tools/list on stdin,
    captures stdout, asserts every byte is a valid Content-Length frame
    (or newline-delimited JSON).
    """
    console_port = _find_free_port()
    bridge_dead_port = _find_free_port()  # ensure startup_bridge degrades cleanly

    env = dict(os.environ)
    env["FORGE_CONSOLE_PORT"] = str(console_port)
    env["FORGE_BRIDGE_URL"] = f"ws://127.0.0.1:{bridge_dead_port}"
    env["FORGE_EXEC_SNAPSHOT_MAX"] = "100"
    # Avoid polluting the user's real ~/.forge-bridge during the test
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(fake_home)

    proc = subprocess.Popen(
        [sys.executable, "-m", "forge_bridge"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        # Wait for the console port to come up — proves _lifespan reached step 6
        assert _wait_port_up("127.0.0.1", console_port, timeout=15.0), (
            "Console uvicorn task did not bind within 15s — "
            "check startup_bridge + _start_console_task wiring"
        )

        # Send MCP initialize on stdin per MCP 2025-06-18 spec
        init_req = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "sc1-test", "version": "0.1"},
            },
        }
        tools_req = {
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {},
        }

        # FastMCP (mcp[cli] >= 1.19) uses NDJSON stdio framing — send each
        # request as a single line terminated by \n. Length-prefixed framing
        # is also accepted by the standard; NDJSON is simpler and what the
        # Python MCP server expects for stdin.
        for req in (init_req, tools_req):
            line = (json.dumps(req) + "\n").encode("utf-8")
            proc.stdin.write(line)
            proc.stdin.flush()

        # Hammer the console with 100 concurrent GETs
        loop = asyncio.new_event_loop()
        try:
            codes = loop.run_until_complete(
                _hammer_console(console_port, 100),
            )
        finally:
            loop.close()

        # Give the MCP server ~1s to respond to init + tools/list
        time.sleep(1.5)

        # Terminate the subprocess cleanly so communicate() collects stdout.
        # Do NOT close stdin first — that causes communicate() to try to
        # flush an already-closed pipe and raise ValueError.
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate(timeout=5.0)

        # Assertion 1: all console GETs succeeded
        success_count = sum(1 for c in codes if c == 200)
        assert success_count >= 95, (
            f"Expected at least 95/100 GETs to succeed, got {success_count}. "
            f"Sample codes: {codes[:10]}"
        )

        # Assertion 2: stdout is ONLY valid JSON-RPC frames (CL-framed or NDJSON)
        # This is the CORE SC#1 assertion.
        messages = _parse_content_length_frames(stdout)
        assert len(messages) >= 1, (
            f"Expected at least 1 MCP message on stdout, got 0. "
            f"stdout (first 500 bytes): {stdout[:500]!r}, "
            f"stderr (first 500 bytes): {stderr[:500]!r}"
        )
        # At least the init response should be present
        init_responses = [m for m in messages if m.get("id") == 1]
        assert len(init_responses) >= 1, (
            f"Expected MCP 'initialize' response on stdout. "
            f"Got messages: {messages!r}"
        )

    finally:
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.communicate(timeout=5.0)
        except Exception:
            pass


@pytest.mark.timeout(60)
def test_stderr_contains_no_access_log_lines(tmp_path):
    """D-21 — access_log=False means no '127.0.0.1:<port> "GET ..." 200' lines."""
    console_port = _find_free_port()
    bridge_dead_port = _find_free_port()

    env = dict(os.environ)
    env["FORGE_CONSOLE_PORT"] = str(console_port)
    env["FORGE_BRIDGE_URL"] = f"ws://127.0.0.1:{bridge_dead_port}"
    env["FORGE_EXEC_SNAPSHOT_MAX"] = "100"
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(fake_home)

    proc = subprocess.Popen(
        [sys.executable, "-m", "forge_bridge"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env,
    )

    try:
        assert _wait_port_up("127.0.0.1", console_port, timeout=15.0)

        # Issue 10 GETs — should produce NO access log lines
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_hammer_console(console_port, 10))
        finally:
            loop.close()

        time.sleep(0.5)

        # Terminate cleanly; communicate() collects stderr without needing
        # to flush a pre-closed stdin (see Task 6 bug fix in the SC#1 test).
        proc.terminate()
        try:
            _, stderr = proc.communicate(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr = proc.communicate(timeout=5.0)

        stderr_str = stderr.decode("utf-8", errors="replace")
        # Access log lines look like: '127.0.0.1:NNNNN - "GET /api/v1/health HTTP/1.1" 200 OK'
        forbidden_patterns = [
            'GET /api/v1/health HTTP/1.1',
            '127.0.0.1:' + str(console_port) + ' - "GET',
        ]
        for pat in forbidden_patterns:
            assert pat not in stderr_str, (
                f"D-21 violation — access log line matching {pat!r} appeared on stderr. "
                f"stderr (first 2000 bytes): {stderr_str[:2000]!r}"
            )

    finally:
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.communicate(timeout=5.0)
        except Exception:
            pass
