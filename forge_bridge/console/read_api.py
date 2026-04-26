"""ConsoleReadAPI -- sole read layer for the v1.3 Artist Console.

All read surfaces (Web UI HTTP handlers, CLI subcommands, MCP resources,
LLM chat context assembly) route through this class. No handler, resource,
or shim may parse JSONL, inspect ManifestService internals, or hit
ExecutionLog fields directly.

The instance-identity gate (API-04, D-16) -- enforced at boot by
`/api/v1/health.instance_identity` -- proves there is exactly one
ExecutionLog and one ManifestService in the process by comparing
id(self._execution_log) against id(_canonical_execution_log_id) recorded
at boot via register_canonical_singletons().

Return type philosophy (per RESEARCH.md section 2):
  - Methods return RAW domain objects (ToolRecord, ExecutionRecord, plain dicts).
  - The {data, meta} envelope is applied by the handler/resource wrapper,
    NOT here.
  - This keeps ConsoleReadAPI unit-testable without HTTP mocks and lets
    MCP resources + HTTP routes build byte-identical envelopes (D-26).
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from forge_bridge.console.manifest_service import ManifestService, ToolRecord
    from forge_bridge.core.staged import StagedOperation
    from forge_bridge.learning.execution_log import ExecutionLog, ExecutionRecord
    from forge_bridge.llm.router import LLMRouter

logger = logging.getLogger(__name__)


# Module-level canonical references -- set once by _lifespan via
# register_canonical_singletons(); used by get_health() for the D-16
# instance-identity gate. Default None until the _lifespan startup path
# installs them.
_canonical_execution_log_id: Optional[int] = None
_canonical_manifest_service_id: Optional[int] = None


def register_canonical_singletons(
    execution_log: "ExecutionLog",
    manifest_service: "ManifestService",
    *,
    watcher_task: "asyncio.Task | None" = None,
) -> None:
    """Record id() of the canonical instances for the D-16 gate.

    Called by _lifespan step 2 AFTER instantiating the canonical ExecutionLog
    and ManifestService, BEFORE constructing ConsoleReadAPI (step 4). The
    get_health() method compares id(self._execution_log) against this
    recorded id to detect LRN-05-class drift -- e.g. if a test or caller
    accidentally passes a second instance to the read API.

    The optional `watcher_task` kwarg (I-02) installs the canonical watcher
    task handle into `forge_bridge.mcp.server._canonical_watcher_task` so
    `_check_watcher()` can differentiate "ok / still running" from
    "fail / done with exception". Passing None leaves the coarse
    `_server_started` gate active.
    """
    global _canonical_execution_log_id, _canonical_manifest_service_id
    _canonical_execution_log_id = id(execution_log)
    _canonical_manifest_service_id = id(manifest_service)
    if watcher_task is not None:
        from forge_bridge.mcp import server as _mcp_server
        _mcp_server._canonical_watcher_task = watcher_task


class ConsoleReadAPI:
    """Sole read layer for Web UI / CLI / MCP resources / chat.

    Constructor args:
        execution_log: canonical ExecutionLog (REQUIRED -- no default; the
                       _lifespan-owned instance must be passed to prove
                       instance identity at boot).
        manifest_service: canonical ManifestService (REQUIRED -- same contract).
        llm_router: optional LLMRouter for /api/v1/health.services.llm_backends.
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
        session_factory: Optional["async_sessionmaker"] = None,
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
        self._session_factory = session_factory  # NEW (D-03) — None by default for backward-compat

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
        route rejects `?tool=...` with a 400 `not_implemented` response;
        deferral to v1.4 is locked per RESEARCH.md Open Questions (RESOLVED).
        """
        return self._execution_log.snapshot(
            limit=limit,
            offset=offset,
            since=since,
            promoted_only=promoted_only,
            code_hash=code_hash,
        )

    # -- Staged operations --------------------------------------------------

    async def get_staged_ops(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        project_id: uuid.UUID | None = None,
    ) -> tuple[list["StagedOperation"], int]:
        """Return (records, total) for FB-B staged-ops list surface (D-03).

        Opens a session per call, instantiates StagedOpRepo, returns repo.list().
        Read-side facade per Phase 9 D-25 single-facade invariant.
        """
        from forge_bridge.store.staged_operations import StagedOpRepo
        async with self._session_factory() as session:
            repo = StagedOpRepo(session)
            return await repo.list(
                status=status, limit=limit, offset=offset, project_id=project_id,
            )

    async def get_staged_op(self, op_id: uuid.UUID) -> "StagedOperation | None":
        """Return single op by UUID, or None if absent / wrong entity_type (D-03)."""
        from forge_bridge.store.staged_operations import StagedOpRepo
        async with self._session_factory() as session:
            repo = StagedOpRepo(session)
            return await repo.get(op_id)

    # -- Manifest -----------------------------------------------------------

    async def get_manifest(self) -> dict:
        """Return the full synthesis manifest as a plain dict.

        Shape matches D-26 byte-identity contract with
        `forge://manifest/synthesis`:
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
        """Return the full D-14 health body.

        Fan-out is bounded per D-17 (each service check wrapped in
        asyncio.wait_for with a 2s timeout). Total handler latency is
        O(N_services * 2s) worst-case = ~14s for 7 services; expected
        steady-state is sub-50ms.

        Aggregation (D-15):
          - ok: all services ok AND instance_identity matches.
          - degraded: any non-critical fails (llm_backends, storage_callback,
            flame_bridge, ws_server).
          - fail: any critical fails (mcp, watcher, instance_identity).
        """
        import httpx

        from forge_bridge import __version__

        async def _check_flame_bridge() -> dict:
            try:
                async with httpx.AsyncClient(timeout=1.5) as client:
                    r = await asyncio.wait_for(
                        client.get(self._flame_bridge_url, timeout=1.5),
                        timeout=2.0,
                    )
                if r.status_code < 500:
                    return {
                        "status": "ok",
                        "url": self._flame_bridge_url,
                        "detail": f"http {r.status_code}",
                    }
                return {
                    "status": "fail",
                    "url": self._flame_bridge_url,
                    "detail": f"http {r.status_code}",
                }
            except Exception as exc:  # noqa: BLE001 - intentional: never surface
                return {
                    "status": "fail",
                    "url": self._flame_bridge_url,
                    "detail": type(exc).__name__,
                }

        async def _check_ws_server() -> dict:
            # Best-effort TCP reachability -- full WS handshake is expensive.
            import socket
            try:
                url = self._ws_bridge_url
                host_port = url.split("://", 1)[-1]
                host, _, port_s = host_port.partition(":")
                port = int(port_s) if port_s else 9998
                with socket.create_connection((host, port), timeout=1.5):
                    return {"status": "ok", "url": url, "detail": "tcp reachable"}
            except Exception as exc:  # noqa: BLE001
                return {
                    "status": "fail",
                    "url": self._ws_bridge_url,
                    "detail": type(exc).__name__,
                }

        async def _check_llm_backends() -> list:
            if self._llm_router is None:
                return []
            try:
                status = await asyncio.wait_for(
                    self._llm_router.ahealth_check(), timeout=2.0,
                )
            except Exception as exc:  # noqa: BLE001
                return [{
                    "name": "router",
                    "status": "fail",
                    "detail": type(exc).__name__,
                }]
            # router.ahealth_check returns {local, cloud, local_model, cloud_model}
            backends = []
            for key in ("local", "cloud"):
                val = status.get(key)
                backends.append({
                    "name": key,
                    "status": "ok" if val else "fail",
                    "detail": f"model={status.get(key + '_model', '')}",
                })
            return backends

        def _check_mcp() -> dict:
            # Import here to avoid circular -- mcp.server imports from us indirectly
            from forge_bridge.mcp import server as mcp_server
            if getattr(mcp_server, "_server_started", False):
                return {"status": "ok", "detail": "lifespan started"}
            return {"status": "fail", "detail": "lifespan not started"}

        def _check_watcher() -> dict:
            """Inspect the canonical watcher task held by _lifespan (I-02).

            If the task is still running we return ok; if it is done() with an
            exception, we flip to fail and report the exception class name in
            `detail` (never str(exc) -- Phase 8 LRN: avoid leaking credentials
            that appear in exception messages).

            Falls back to the older `_server_started` gate when
            `_canonical_watcher_task` has not yet been installed (e.g. inside
            unit tests that monkeypatch server state but never call _lifespan).
            """
            from forge_bridge.mcp import server as mcp_server
            task = getattr(mcp_server, "_canonical_watcher_task", None)
            if task is not None:
                if task.done():
                    try:
                        exc = task.exception()
                    except Exception as probe_exc:  # noqa: BLE001
                        return {
                            "status": "fail",
                            "task_done": True,
                            "detail": type(probe_exc).__name__,
                        }
                    if exc is not None:
                        return {
                            "status": "fail",
                            "task_done": True,
                            "detail": type(exc).__name__,
                        }
                    return {
                        "status": "fail",
                        "task_done": True,
                        "detail": "watcher_task completed without exception (unexpected)",
                    }
                return {"status": "ok", "task_done": False, "detail": ""}
            # No canonical task installed yet -- fall back to the coarse boot gate.
            started = getattr(mcp_server, "_server_started", False)
            return {
                "status": "ok" if started else "fail",
                "task_done": False,
                "detail": "",
            }

        def _check_storage_callback() -> dict:
            registered = self._execution_log._storage_callback is not None
            if not registered:
                return {
                    "status": "absent",
                    "registered": False,
                    "detail": "no callback set",
                }
            return {
                "status": "ok",
                "registered": True,
                "detail": "callback attached",
            }

        def _check_console_port() -> dict:
            # We're already serving on this port if get_health is being called
            # via the HTTP route. If called via MCP resource, the port MAY still
            # be bound or not -- no cheap way to probe from inside the process.
            return {"status": "ok", "port": self._console_port, "detail": "serving"}

        def _check_instance_identity() -> dict:
            el_match = (
                _canonical_execution_log_id is None
                or id(self._execution_log) == _canonical_execution_log_id
            )
            ms_match = (
                _canonical_manifest_service_id is None
                or id(self._manifest_service) == _canonical_manifest_service_id
            )
            return {
                "execution_log": {
                    "id_match": el_match,
                    "detail": (
                        "canonical" if el_match
                        else "DRIFT -- two ExecutionLog instances detected"
                    ),
                },
                "manifest_service": {
                    "id_match": ms_match,
                    "detail": (
                        "canonical" if ms_match
                        else "DRIFT -- two ManifestService instances detected"
                    ),
                },
            }

        # Fan out the async checks in parallel (bounded per D-17)
        results = await asyncio.gather(
            _check_flame_bridge(),
            _check_ws_server(),
            _check_llm_backends(),
            return_exceptions=True,
        )
        flame_bridge = (
            results[0] if not isinstance(results[0], BaseException)
            else {"status": "fail", "detail": type(results[0]).__name__}
        )
        ws_server = (
            results[1] if not isinstance(results[1], BaseException)
            else {"status": "fail", "detail": type(results[1]).__name__}
        )
        llm_backends = (
            results[2] if not isinstance(results[2], BaseException) else []
        )

        mcp = _check_mcp()
        watcher = _check_watcher()
        storage_callback = _check_storage_callback()
        console_port = _check_console_port()
        instance_identity = _check_instance_identity()

        services = {
            "mcp": mcp,
            "flame_bridge": flame_bridge,
            "ws_server": ws_server,
            "llm_backends": llm_backends,
            "watcher": watcher,
            "storage_callback": storage_callback,
            "console_port": console_port,
        }

        # Aggregate per D-15
        critical_failures = (
            mcp["status"] == "fail"
            or watcher["status"] == "fail"
            or not instance_identity["execution_log"]["id_match"]
            or not instance_identity["manifest_service"]["id_match"]
        )
        non_critical_failures = (
            any(b.get("status") == "fail" for b in llm_backends)
            or storage_callback["status"] == "fail"
            or flame_bridge["status"] == "fail"
            or ws_server["status"] == "fail"
        )
        if critical_failures:
            status = "fail"
        elif non_critical_failures:
            status = "degraded"
        else:
            status = "ok"

        return {
            "status": status,
            "ts": datetime.now(timezone.utc).isoformat(),
            "version": __version__,
            "services": services,
            "instance_identity": instance_identity,
        }
