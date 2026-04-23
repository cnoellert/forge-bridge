"""ConsoleReadAPI -- sole read layer for the v1.3 Artist Console.

All read surfaces (Web UI HTTP handlers, CLI subcommands, MCP resources,
LLM chat context assembly) route through this class. No handler, resource,
or shim may parse JSONL, inspect ManifestService internals, or hit
ExecutionLog fields directly.

The instance-identity gate (API-04, D-16) -- enforced at boot by
`/api/v1/health.instance_identity` in Plan 09-03 -- proves there is exactly
one ExecutionLog and one ManifestService in the process by comparing
id(self._execution_log) against id(_canonical_execution_log) in
forge_bridge/mcp/server.py.

Return type philosophy (per RESEARCH.md section 2):
  - Methods return RAW domain objects (ToolRecord, ExecutionRecord, plain dicts).
  - The {data, meta} envelope is applied by the handler/resource wrapper
    (Plan 09-03), NOT here.
  - This keeps ConsoleReadAPI unit-testable without HTTP mocks and lets
    MCP resources + HTTP routes build byte-identical envelopes (D-26).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from forge_bridge.console.manifest_service import ManifestService, ToolRecord
    from forge_bridge.learning.execution_log import ExecutionLog, ExecutionRecord
    from forge_bridge.llm.router import LLMRouter

logger = logging.getLogger(__name__)


class ConsoleReadAPI:
    """Sole read layer for Web UI / CLI / MCP resources / chat.

    Constructor args:
        execution_log: canonical ExecutionLog (REQUIRED -- no default; the
                       _lifespan-owned instance must be passed to prove
                       instance identity at boot).
        manifest_service: canonical ManifestService (REQUIRED -- same contract).
        llm_router: optional LLMRouter for /api/v1/health.services.llm_backends
                    (used by get_health() in Plan 09-03; None in Plan 09-02).
        flame_bridge_url: optional; default reads FORGE_BRIDGE_HOST/PORT env.
        ws_bridge_url: optional; default reads FORGE_BRIDGE_URL env.
        console_port: HTTP bind port (default 9996 per D-27).
    """

    def __init__(
        self,
        execution_log: "ExecutionLog",
        manifest_service: "ManifestService",
        llm_router: Optional["LLMRouter"] = None,
        flame_bridge_url: Optional[str] = None,
        ws_bridge_url: Optional[str] = None,
        console_port: int = 9996,
    ) -> None:
        self._execution_log = execution_log
        self._manifest_service = manifest_service
        self._llm_router = llm_router
        # D-27/env-fallback pattern -- mirror LLMRouter.__init__
        self._flame_bridge_url = flame_bridge_url or (
            f"http://{os.environ.get('FORGE_BRIDGE_HOST', '127.0.0.1')}:"
            f"{os.environ.get('FORGE_BRIDGE_PORT', '9999')}"
        )
        self._ws_bridge_url = ws_bridge_url or os.environ.get(
            "FORGE_BRIDGE_URL", "ws://127.0.0.1:9998"
        )
        self._console_port = console_port

    # -- Tools --------------------------------------------------------------

    async def get_tools(self) -> list["ToolRecord"]:
        """Return every registered ToolRecord in insertion order."""
        return self._manifest_service.get_all()

    async def get_tool(self, name: str) -> Optional["ToolRecord"]:
        """Return a single ToolRecord by name, or None."""
        return self._manifest_service.get(name)

    # -- Executions ---------------------------------------------------------

    async def get_executions(
        self,
        limit: int = 50,
        offset: int = 0,
        since: Optional[datetime] = None,
        promoted_only: bool = False,
        code_hash: Optional[str] = None,  # prefix match per D-03
    ) -> tuple[list["ExecutionRecord"], int]:
        """Return (records, total_before_pagination) for the /api/v1/execs route.

        Forwards all filter kwargs to ExecutionLog.snapshot. The handler layer
        clamps `limit` to 500 per D-05 BEFORE calling this method.

        NOTE (W-01): `tool` kwarg is deliberately absent. The /api/v1/execs
        route in Plan 09-03 rejects `?tool=...` with a 400 `not_implemented`
        response; deferral to v1.4 is locked per RESEARCH.md Open Questions
        (RESOLVED).
        """
        return self._execution_log.snapshot(
            limit=limit,
            offset=offset,
            since=since,
            promoted_only=promoted_only,
            code_hash=code_hash,
        )

    # -- Manifest -----------------------------------------------------------

    async def get_manifest(self) -> dict:
        """Return the full synthesis manifest as a plain dict.

        Shape matches D-26 byte-identity contract with
        `forge://manifest/synthesis` (added in Plan 09-03):
          {"tools": [ToolRecord.to_dict(), ...], "count": N, "schema_version": "1"}
        """
        tools = self._manifest_service.get_all()
        return {
            "tools": [t.to_dict() for t in tools],
            "count": len(tools),
            "schema_version": "1",
        }

    # -- Health -------------------------------------------------------------

    async def get_health(self) -> dict:
        """Stub -- Plan 09-03 fills the full D-14 body (services + instance_identity).

        In Plan 09-02, returning a minimal shape lets upstream callers wire the
        method without blocking on the full multi-service fan-out. The full
        implementation lands as a task in Plan 09-03.
        """
        # Stub body -- must be a dict so the JSON serializer does not trip.
        return {
            "status": "ok",
            "ts": datetime.utcnow().isoformat(),
            "services": {},
            "instance_identity": {
                "execution_log": {"id": id(self._execution_log)},
                "manifest_service": {"id": id(self._manifest_service)},
            },
        }
