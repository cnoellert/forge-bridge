"""forge-bridge exec — PR41 deterministic execution via the console daemon (HTTP).

Posts ``{text}`` to ``POST /api/v1/exec`` on the console daemon (default
``:9996``, override via ``FORGE_CONSOLE_URL``). Output rendering is unchanged
from PR37: default per-step formatted output, ``--json`` for raw PR31 envelope.
No fallback to in-process execution — fails loudly if the daemon isn't running.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Annotated

import typer

_EXIT_OK = 0
_EXIT_USAGE = 1
_EXIT_TRANSPORT = 2
_EXIT_PROTOCOL = 3
_EXIT_EXEC_FAIL = 4

_DEFAULT_BASE_URL = "http://127.0.0.1:9996"
_HTTP_TIMEOUT_S = 65.0


class ExecTransportError(Exception):
    """Transport / protocol failure from `_exec_http`.

    `kind`:
      ``CONNECT_ERROR`` — daemon unreachable (refused or connect-timeout).
      ``HTTP_ERROR``    — other httpx error (read timeout, network, etc.).
      ``HTTP_STATUS``   — non-200 response from the daemon.
      ``INVALID_JSON``  — 200 response but body not decodable JSON.
    """

    def __init__(self, kind: str, detail: str | None = None) -> None:
        self.kind = kind
        self.detail = detail or kind
        super().__init__(self.detail)


def _exec_http(text: str, *, client=None) -> dict:
    """POST `text` to /api/v1/exec and return the PR31 envelope.

    `client` may be injected (typically `httpx.Client(transport=MockTransport(...))`)
    for tests; production callers pass None and a one-off client is created here.
    """
    # Lazy-import httpx — cli/__init__.py contract: keep `--help` fast.
    import httpx

    base_url = os.getenv("FORGE_CONSOLE_URL", _DEFAULT_BASE_URL)
    url = f"{base_url}/api/v1/exec"

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=_HTTP_TIMEOUT_S)

    try:
        try:
            resp = client.post(url, json={"text": text})
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise ExecTransportError("CONNECT_ERROR")
        except httpx.HTTPError as e:
            raise ExecTransportError("HTTP_ERROR", str(e))

        if resp.status_code != 200:
            raise ExecTransportError("HTTP_STATUS", str(resp.status_code))

        try:
            return resp.json()
        except Exception:
            raise ExecTransportError("INVALID_JSON")
    finally:
        if own_client:
            client.close()


def exec_cmd(
    command: Annotated[
        str | None,
        typer.Argument(help="Command string (PR30 ``->`` chains). Omit for interactive mode."),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit the PR31 response dict to stdout."),
    ] = False,
    verb: Annotated[
        str | None,
        typer.Option("--verb", help="One-shot verb (rename | trim). Needs --sequence/--segment/--new-name."),
    ] = None,
    sequence: Annotated[
        str | None, typer.Option("--sequence", help="One-shot: target sequence name.")
    ] = None,
    segment: Annotated[
        str | None, typer.Option("--segment", help="One-shot: exact current segment name.")
    ] = None,
    new_name: Annotated[
        str | None, typer.Option("--new-name", help="One-shot: new value (segment name, or in-point frame number for trim).")
    ] = None,
    do_apply: Annotated[
        bool,
        typer.Option("--apply", help="One-shot: stage for ratification (prints `fbridge ratify <id>`); default previews only."),
    ] = False,
) -> None:
    """Run the shared chain engine via the console daemon (POST /api/v1/exec).

    With no command, drops into the interactive verb shell — pick an action,
    fill a couple of values, preview, ratify, apply — on the host-mutation rail.
    Power users can inline the args: ``/rename <sequence> #<n> <new name>``.
    With ``--verb`` runs a single verb non-interactively (preview by default).
    """
    if verb is not None:
        import asyncio
        from forge_bridge.cli.interactive import run_oneshot
        missing = [n for n, v in (("--sequence", sequence), ("--segment", segment),
                                  ("--new-name", new_name)) if v is None]
        if missing:
            sys.stderr.write(f"Error: --verb requires {', '.join(missing)}\n")
            raise typer.Exit(code=_EXIT_USAGE)
        if not (sequence.strip() and segment.strip() and new_name.strip()):
            sys.stderr.write("Error: --sequence, --segment, --new-name must not be empty\n")
            raise typer.Exit(code=_EXIT_USAGE)
        code = asyncio.run(run_oneshot(
            verb=verb, sequence=sequence, segment_name=segment,
            new_name=new_name, do_apply=do_apply, as_json=as_json,
        ))
        raise typer.Exit(code=code)
    if command is None:
        import asyncio
        from forge_bridge.cli.interactive import run_interactive
        asyncio.run(run_interactive())
        return
    try:
        result = _exec_http(command)
    except ExecTransportError as e:
        if e.kind == "CONNECT_ERROR":
            sys.stderr.write(
                "Error: forge_bridge console is not running.\n"
                "Start it with `fbridge up`.\n"
            )
            raise typer.Exit(code=_EXIT_TRANSPORT)
        if e.kind in ("HTTP_STATUS", "INVALID_JSON"):
            sys.stderr.write(f"Error: {e.detail}\n")
            raise typer.Exit(code=_EXIT_PROTOCOL)
        # HTTP_ERROR — other httpx failures (read timeout, network) treated as transport.
        sys.stderr.write(f"Error: {e.detail}\n")
        raise typer.Exit(code=_EXIT_TRANSPORT)

    if as_json:
        sys.stdout.write(json.dumps(result, default=str) + "\n")
    else:
        status = result.get("status", "error")
        if status == "success":
            chain = result.get("chain") or []
            for item in chain:
                step = item.get("step", "")
                res = item.get("result")
                sys.stdout.write(f"--- {step}\n")
                sys.stdout.write(json.dumps(res, indent=2, default=str) + "\n")
        else:
            err = result.get("error")
            if isinstance(err, dict):
                sys.stderr.write(
                    f"{err.get('code', 'error')}: "
                    f"{err.get('message', err)}\n",
                )
            else:
                sys.stderr.write(str(err) + "\n")

    if result.get("status") != "success":
        raise typer.Exit(code=_EXIT_EXEC_FAIL)
