"""forge-bridge exec — PR37 deterministic in-process execution (no HTTP, no LLM)."""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Annotated

import typer

_EXIT_OK = 0
_EXIT_FAIL = 1


def exec_cmd(
    command: Annotated[
        str,
        typer.Argument(help="Command string (PR30 ``->`` chains, macro expand)."),
    ],
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit the PR31 response dict to stdout."),
    ] = False,
) -> None:
    """Run the shared chain engine without the chat HTTP endpoint or LLM."""

    async def _run() -> dict:
        from forge_bridge.console._execute import execute_command

        return await execute_command(command)

    result = asyncio.run(_run())

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
        raise typer.Exit(code=_EXIT_FAIL)
