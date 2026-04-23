# Phase 9: Read API Foundation - Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 21 (11 new modules/tests + 6 modified)
**Analogs found:** 18 / 21

## File Classification

### New files (to create)

| New file | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `forge_bridge/console/__init__.py` | barrel | config | `forge_bridge/llm/__init__.py`, `forge_bridge/learning/__init__.py` | exact (barrel re-export) |
| `forge_bridge/console/manifest_service.py` | service (in-memory registry) | CRUD (insert/remove/snapshot-read) | `forge_bridge/learning/execution_log.py` (`ExecutionRecord` + in-memory dicts), `forge_bridge/learning/storage.py` (module docstring tone) | role-match (new singleton pattern; no existing asyncio.Lock-protected registry) |
| `forge_bridge/console/read_api.py` | service/facade | request-response (read-only aggregator) | `forge_bridge/llm/router.py` (class + env-fallback __init__ + singleton factory) | role-match |
| `forge_bridge/console/app.py` | config/factory | request-response (Starlette ASGI) | NO direct analog in codebase (first Starlette+uvicorn embedding) | no-analog — use RESEARCH.md §1 pattern |
| `forge_bridge/console/routes.py` (may merge into app.py) | controller/handlers | request-response | NO direct analog | no-analog — use RESEARCH.md §Pattern 2 |
| `forge_bridge/console/resources.py` | registration (MCP) | request-response | `forge_bridge/llm/health.py` (`register_llm_resources`) | exact |
| `forge_bridge/console/logging_config.py` | config (dict literal) | — | NO direct analog | no-analog — use RESEARCH.md §3 verbatim |
| `tests/test_console_read_api.py` | test (unit) | request-response | `tests/test_llm.py` (pure unit — class + method presence), `tests/test_execution_log.py` (tmp_path + log-path pattern) | exact |
| `tests/test_manifest_service.py` | test (unit) | CRUD | `tests/test_execution_log.py` (replay/snapshot/record tests), `tests/test_storage_protocol.py` (Protocol + isinstance) | role-match |
| `tests/test_console_http_transport.py` | test (integration) | request-response | `tests/test_mcp_server_graceful_degradation.py` (async + port bind + caplog) | role-match |
| `tests/test_console_routes.py` | test (unit/integration) | request-response | `tests/test_llm.py` (MagicMock(mcp) + call_args inspection) | role-match |
| `tests/test_console_health.py` | test (integration) | request-response | `tests/test_mcp_server_graceful_degradation.py` (caplog WARNING + graceful-degradation) | role-match |
| `tests/test_console_instance_identity.py` | test (integration) | request-response | `tests/test_public_api.py` (singleton `is` checks via `get_mcp()`) | role-match |
| `tests/test_console_port_degradation.py` | test (integration) | request-response | `tests/test_mcp_server_graceful_degradation.py` (exact pattern — `_find_free_port` + dead-port url + caplog WARNING) | exact |
| `tests/test_console_mcp_resources.py` | test (unit) | request-response | `tests/test_llm.py::test_health_resource_registered` (MagicMock(mcp) + call_args inspection) | exact |
| `tests/test_console_stdio_cleanliness.py` | test (integration/SC#1) | request-response (over subprocess stdio) | NO direct analog — `tests/test_public_api.py::test_no_forge_specific_strings` uses `subprocess.run` but not for an MCP wire | no-analog — see RESEARCH.md §Integration test §D-23 notes |
| `tests/test_typer_entrypoint.py` | test (integration) | request-response (subprocess + --help) | `tests/test_public_api.py::test_no_forge_specific_strings` (`subprocess.run` returncode assertion), `tests/test_public_api.py::test_public_api_importable` (import-surface) | role-match |

### Modified files

| Modified file | Role | Change | Existing Pattern |
|---------------|------|--------|------------------|
| `forge_bridge/__main__.py` | entry-point script | Replace 4-line `main()` bootstrap with Typer root | `forge_bridge/__main__.py` current (bare import + call) — replace wholesale |
| `forge_bridge/mcp/server.py` | lifecycle orchestration | Extend `_lifespan` per D-31 (6-step sequence) + reuse `startup_bridge` graceful-degradation shape for `_start_console_task` | `_lifespan` existing pattern (lines 68-89), `startup_bridge` existing pattern (lines 114-154) |
| `forge_bridge/learning/execution_log.py` | model (in-memory + disk) | Add `_records: deque`, `snapshot()`, `_promoted_hashes`, deque-append in `record()`, deque-replay in `_replay()` | `ExecutionLog.__init__` (lines 110-119) — in-memory dict/set pattern; `record()` (lines 182-235) — JSONL+callback write path; `_replay()` (lines 147-180) — JSONL-iteration shape |
| `forge_bridge/learning/watcher.py` | watcher (write-side of ManifestService) | Add `manifest_service: ManifestService \| None = None` kwarg to `watch_synthesized_tools` and `_scan_once`; call `manifest_service.register(ToolRecord(...))` after `register_tool()` succeeds | `watch_synthesized_tools` signature (lines 33-38), `_scan_once` registration point (lines 183-186) |
| `forge_bridge/__init__.py` | barrel | Optional re-exports of `ManifestService`, `ToolRecord`, `ConsoleReadAPI`; version bump `1.3.0` → `1.4.0` if `__all__` grows | `forge_bridge/__init__.py` existing import-block + `__all__` list (lines 24-77) |
| `pyproject.toml` | build config | Add ruff `extend-select = ["T20"]` + `per-file-ignores` carve-out per D-22 | `pyproject.toml` existing `[tool.ruff]` block (lines 42-44) |

---

## Pattern Assignments

### `forge_bridge/console/__init__.py` (barrel)

**Analog:** `forge_bridge/llm/__init__.py` (3 imports, 1 `__all__` block)

**Full file excerpt — copy shape verbatim** (`forge_bridge/llm/__init__.py` lines 1-5):
```python
"""LLM routing package for forge-bridge."""
from forge_bridge.llm.router import LLMRouter, get_router
from forge_bridge.llm.health import register_llm_resources

__all__ = ["LLMRouter", "get_router", "register_llm_resources"]
```

**Adaptation for Phase 9:**
```python
"""Console package — Artist Console read layer (ConsoleReadAPI + ManifestService + HTTP API on :9996)."""
from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.console.resources import register_console_resources

__all__ = [
    "ManifestService",
    "ToolRecord",
    "ConsoleReadAPI",
    "register_console_resources",
]
```

**Secondary analog:** `forge_bridge/learning/__init__.py` (8 re-exports, multi-line `__all__`) for the larger-barrel shape if planner elects to re-export more.

---

### `forge_bridge/console/manifest_service.py` (service, CRUD)

**Analog:** `forge_bridge/learning/execution_log.py` (`ExecutionRecord` frozen dataclass shape + in-memory dict pattern)

**Frozen dataclass pattern** (`forge_bridge/learning/execution_log.py` lines 33-50):
```python
@dataclass(frozen=True)
class ExecutionRecord:
    """Payload delivered to storage callbacks after every ExecutionLog.record() write.

    Mirrors the JSONL row written by ExecutionLog.record() — same field names,
    same types. ...

    Frozen so consumer code cannot mutate state shared between the log write and
    the callback fire.
    """

    code_hash: str
    raw_code: str
    intent: Optional[str]
    timestamp: str
    promoted: bool
```

**Adaptation notes:**
- Copy the `@dataclass(frozen=True)` decorator + snake_case field convention (D-04) verbatim.
- `ToolRecord` uses `tuple[str, ...]` instead of `list[str]` for `tags` (frozen dataclass requires hashable field types — `list` is mutable and triggers `unhashable type` errors in some use paths). `tags: tuple[str, ...] = field(default_factory=tuple)` per RESEARCH.md §8.
- Add `to_dict()` method (returns `dataclasses.asdict(self)`) — `ExecutionRecord` uses `asdict(record)` at the call site (line 209 `json.dumps(asdict(record))`); inline a method on `ToolRecord` for convenience at the resource/handler boundary.

**In-memory registry pattern** (`forge_bridge/learning/execution_log.py` lines 110-119):
```python
def __init__(self, log_path: Path = LOG_PATH, threshold: int = 3) -> None:
    self._path = log_path
    self._threshold = int(os.environ.get("FORGE_PROMOTION_THRESHOLD", threshold))
    self._counters: dict[str, int] = {}
    self._promoted: set[str] = set()
    self._code_by_hash: dict[str, str] = {}
    self._intent_by_hash: dict[str, Optional[str]] = {}
    self._replay()
    self._storage_callback: Optional[StorageCallback] = None
    self._storage_callback_is_async: bool = False
```

**Adaptation — `ManifestService.__init__`:**
- Single `dict[str, ToolRecord]` keyed by `name` (matches `_code_by_hash` shape).
- Plus `self._lock = asyncio.Lock()` — **no existing analog in the codebase** (verified: `grep asyncio.Lock()` returns zero hits). This is a de novo addition. Document the concurrency model inline per RESEARCH.md §8.

**Reader-returns-shallow-copy pattern** (no direct analog): `get_all()` returns `list(self._tools.values())` — fresh list so callers can iterate without holding the lock. Reads are lockless (race-acceptable for a dict whose entries never mutate in-place; replacement is atomic in CPython).

**Docstring tone analog:** `forge_bridge/learning/storage.py` lines 1-71 — multi-paragraph module docstring with "Canonical X", "Consistency model", "Usage". Copy this register for `ManifestService` docstring (this file becomes the canonical manifest spec consumed by projekt-forge per MFST-06).

---

### `forge_bridge/console/read_api.py` (service/facade)

**Analog:** `forge_bridge/llm/router.py` (class + env-fallback `__init__` + singleton-factory pattern)

**Class + env-fallback `__init__` pattern** (`forge_bridge/llm/router.py` lines 79-100):
```python
def __init__(
    self,
    local_url: str | None = None,
    local_model: str | None = None,
    cloud_model: str | None = None,
    system_prompt: str | None = None,
) -> None:
    self.local_url = local_url or os.environ.get(
        "FORGE_LOCAL_LLM_URL", "http://localhost:11434/v1"
    )
    self.local_model = local_model or os.environ.get(
        "FORGE_LOCAL_MODEL", "qwen2.5-coder:32b"
    )
    ...
```

**Adaptation for `ConsoleReadAPI.__init__`:**
- Constructor kwargs > env vars > hardcoded defaults (same precedence chain as `LLMRouter`).
- Wire `execution_log` and `manifest_service` as required (no defaults — these are canonical singletons owned by `_lifespan`, not env-derived).
- `flame_bridge_url`, `ws_bridge_url`, `console_port` as optional env-derived — mirror `LLMRouter.local_url` pattern.

**Async method signature pattern** (`forge_bridge/llm/router.py` lines 105-132):
```python
async def acomplete(
    self,
    prompt: str,
    sensitive: bool = True,
    system: Optional[str] = None,
    temperature: float = 0.1,
) -> str:
    ...
```

**Adaptation:** Every `ConsoleReadAPI` read method is `async def` (even though most bodies are sync) — keeps the interface uniform for handler wrappers and MCP resources. Per RESEARCH.md §2 method-signature-philosophy: raw domain-object returns; envelope wrapping happens in handler/resource layer.

**Health-check fan-out analog:** `LLMRouter.ahealth_check()` (lines 152-178) — returns a dict, best-effort, never raises, logs warnings for failed backends. This is the exact shape `ConsoleReadAPI.get_health()` needs for the `services.llm_backends` block (D-14). Reuse `self._llm_router.ahealth_check()` directly — do not re-implement.

---

### `forge_bridge/console/app.py` (Starlette factory)

**No direct analog** — this is the first Starlette+uvicorn embedding in the codebase.

**Pattern source:** RESEARCH.md §1 (Starlette routes list + CORS middleware) — copy verbatim.

**Code to lift from RESEARCH.md §1:**
```python
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route

def build_console_app(read_api: ConsoleReadAPI) -> Starlette:
    routes = [
        Route("/api/v1/tools", tools_handler, methods=["GET"]),
        Route("/api/v1/tools/{name}", tool_detail_handler, methods=["GET"]),
        Route("/api/v1/execs", execs_handler, methods=["GET"]),
        Route("/api/v1/manifest", manifest_handler, methods=["GET"]),
        Route("/api/v1/health", health_handler, methods=["GET"]),
    ]
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["http://127.0.0.1:9996", "http://localhost:9996"],
            allow_methods=["GET"],
            allow_headers=["*"],
            allow_credentials=False,
        ),
    ]
    app = Starlette(routes=routes, middleware=middleware)
    app.state.console_read_api = read_api
    return app
```

**Logger pattern — copy from every module in the codebase:**
```python
import logging
logger = logging.getLogger(__name__)
```
Then use `logger.info/warning/exception(...)` — NEVER `print()` (D-22 enforced via ruff).

---

### `forge_bridge/console/routes.py` (request handlers)

**No direct analog** — route handlers over Starlette are new.

**Pattern source:** RESEARCH.md §Pattern 2 (envelope wrapper) + §5 (snapshot filter translation).

**Envelope wrapper excerpt (RESEARCH.md §Pattern 2):**
```python
from starlette.requests import Request
from starlette.responses import JSONResponse

def _envelope(data, **meta) -> JSONResponse:
    return JSONResponse({"data": data, "meta": meta})

def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)
```

**Parallel analog for error-handling style:** `forge_bridge/mcp/server.py::startup_bridge` (lines 142-154) — try/except at the entry boundary, WARNING log, null out the resource, never re-raise. Route handlers adopt the same shape: try → `_envelope(...)`; except → log WARNING, return `_error(...)` with a sensible HTTP status. Never leak internal traceback strings to HTTP clients.

---

### `forge_bridge/console/resources.py` (MCP resource registration)

**Analog:** `forge_bridge/llm/health.py` (entire file — canonical shape)

**Full file excerpt to mirror** (`forge_bridge/llm/health.py` lines 1-17):
```python
"""LLM health check — MCP resource registration."""
import json

from mcp.server.fastmcp import FastMCP


def register_llm_resources(mcp: FastMCP) -> None:
    """Register forge://llm/health resource on the MCP server."""

    @mcp.resource("forge://llm/health")
    async def llm_health() -> str:
        """Report available LLM backends for forge-bridge."""
        from forge_bridge.llm.router import get_router
        router = get_router()
        status = await router.ahealth_check()
        return json.dumps(status, indent=2)
```

**Adaptation for Phase 9 (register_console_resources):**
- Function signature gains two service dependencies: `register_console_resources(mcp, manifest_service, console_read_api)` — NOT module-level globals like `get_router()` (because `_lifespan` owns these; see Pitfall P9-2).
- Register 4 resources + 2 tool shims (total 6 decorator calls inside the function body).
- Every resource decorator includes `mime_type="application/json"` per D-26.
- Every resource body: `data = await console_read_api.<method>()`; `return _envelope_json(data)` where `_envelope_json` matches the HTTP handler's JSON serializer byte-for-byte (D-26).

**Tool annotation pattern source:** `forge_bridge/mcp/registry.py` `register_tool` calls (lines 183-193) use `annotations={"title": "...", "readOnlyHint": True, "idempotentHint": True}`. The tool shims (`forge_manifest_read`, `forge_tools_read`) should include `annotations={"readOnlyHint": True}` — both are pure reads (MCP Tool Annotations as Risk Vocabulary, CANON_REFS).

**Registration timing:** Called from `_lifespan` step 5 per D-31, NOT at module import. FastMCP accepts `@mcp.resource`/`@mcp.tool` registration after server construction (RESEARCH.md §Pitfall P9-2 + A5). Do NOT mirror `register_builtins(mcp)` import-time call (that relies on builtin tools with no runtime deps).

---

### `forge_bridge/console/logging_config.py` (config dict)

**No direct analog** — first custom uvicorn logging config in the codebase.

**Pattern source:** RESEARCH.md §3 verbatim.

**Full dict (paste into module):**
```python
STDERR_ONLY_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(name)s %(message)s",
            "use_colors": False,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "uvicorn":        {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.error":  {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "WARNING", "propagate": False},
    },
}
```

Planner note: may be inlined into `app.py` rather than split into its own module (the dict is a 20-line config constant). Either shape is fine; split preferred for test-isolation (you can assert on the config dict without pulling Starlette).

---

### `tests/test_console_read_api.py` (unit tests)

**Analog:** `tests/test_llm.py` (pure unit tests against the class surface, no subprocess)

**Structure to copy** (`tests/test_llm.py` lines 25-111):
- One test per method-existence assertion (e.g. `test_get_tools_exists`, `test_get_executions_is_coroutine`).
- `asyncio.iscoroutinefunction(router.acomplete)` (line 42) → `asyncio.iscoroutinefunction(read_api.get_tools)` etc.
- `monkeypatch.setenv(...)` + re-instantiate for env-fallback tests (lines 63-75).
- Mock singletons by constructing `ExecutionLog(log_path=tmp_path/...)` and `ManifestService()` directly — they're lightweight.

**Secondary analog:** `tests/test_execution_log.py` (tmp_path fixture + fresh `ExecutionLog(log_path=tmp_path/...)` — copy for `ConsoleReadAPI` tests that need a fresh log).

---

### `tests/test_manifest_service.py` (unit tests)

**Analog:** `tests/test_execution_log.py` (same shape: frozen dataclass + in-memory registry + record-and-read)

**Test patterns to mirror:**
- `test_register_inserts_record` ← mirrors `test_record_appends_jsonl` (line 38)
- `test_register_replaces_existing` ← mirrors `test_record_returns_false_below_threshold` (line 65)
- `test_get_all_returns_insertion_order` ← new (ManifestService-specific)
- `test_remove_drops_record` ← new; use `pytest.mark.asyncio` for async method tests

**Protocol-compliance pattern:** `tests/test_storage_protocol.py` lines 17-50 — class-with-method isinstance check. Applies if `ToolRecord` is typed at a Protocol boundary (likely not needed in v1.3).

---

### `tests/test_console_http_transport.py` (integration)

**Analog:** `tests/test_mcp_server_graceful_degradation.py` (exact pattern for async port-bind + caplog assertion)

**Reusable fixtures to copy** (`tests/test_mcp_server_graceful_degradation.py` lines 25-48):
```python
def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return port


@pytest.fixture(autouse=True)
def _reset_server_module():
    """Ensure the mcp.server module globals are clean before + after each test."""
    mcp_server._client = None
    mcp_server._server_started = False
    yield
    ...
```

**Adaptation:** For HTTP transport tests, use `httpx.AsyncClient` to hit `http://127.0.0.1:<port>/api/v1/...` against a real uvicorn task launched by a test-local `_lifespan` setup. Pattern: construct `ConsoleReadAPI` with tmp-path `ExecutionLog`, build `Starlette`, launch uvicorn task, httpx-request, assert envelope shape, cancel task.

---

### `tests/test_console_routes.py` (handler unit tests)

**Analog:** `tests/test_llm.py::test_health_resource_registered` (lines 194-211) — MagicMock(mcp) + `call_args_list` inspection

**Pattern excerpt** (`tests/test_llm.py` lines 194-211):
```python
def test_health_resource_registered():
    """register_llm_resources(mcp) must register a resource at forge://llm/health."""
    from unittest.mock import MagicMock
    from forge_bridge.llm.health import register_llm_resources

    mock_mcp = MagicMock()
    register_llm_resources(mock_mcp)

    registered_uris = [
        call.args[0]
        for call in mock_mcp.resource.call_args_list
    ]
    assert "forge://llm/health" in registered_uris, ...
```

**Adaptation — for route-handler tests, use Starlette `TestClient` (from `starlette.testclient`) instead:**
- `TestClient(app)` wraps the ASGI app synchronously (no uvicorn needed).
- Assert envelope shape (`response.json()["data"]`, `response.json()["meta"]["total"]`).
- Assert clamping per D-05 (pass `?limit=1000`; assert `meta.limit == 500`).

---

### `tests/test_console_health.py` (integration)

**Analog:** `tests/test_mcp_server_graceful_degradation.py` (caplog WARNING + graceful-degradation shape)

**Adaptation:** Most health assertions are structural (D-14 response shape) — use Starlette TestClient for normal-case; use `caplog.at_level(logging.WARNING, logger="forge_bridge.console")` for degraded-case (forge-bridge WS down, LLM unavailable, etc.).

---

### `tests/test_console_instance_identity.py` (integration)

**Analog:** `tests/test_public_api.py::test_get_mcp_returns_singleton` (lines 84-90) — `is` identity check pattern

**Pattern excerpt:**
```python
def test_get_mcp_returns_singleton():
    from forge_bridge import get_mcp
    from forge_bridge.mcp.server import mcp as server_mcp

    assert get_mcp() is server_mcp
    assert get_mcp() is get_mcp()  # idempotent
```

**Adaptation for D-16 instance-identity gate:**
- Construct one `ExecutionLog` + `ManifestService`.
- Pass them to a `watch_synthesized_tools(manifest_service=ms, ...)` spawn AND to `ConsoleReadAPI(execution_log=el, manifest_service=ms, ...)`.
- Hit `/api/v1/health`; assert `data.instance_identity.execution_log.id_match == True`.
- Negative test: construct TWO ExecutionLog instances, pass different ones to watcher and ConsoleReadAPI; assert health returns `status="fail"` + `id_match=False`.

---

### `tests/test_console_port_degradation.py` (integration)

**Analog:** `tests/test_mcp_server_graceful_degradation.py` (exact — same pattern mirrored)

**Full test shape to mirror** (`tests/test_mcp_server_graceful_degradation.py` lines 51-78):
```python
async def test_startup_bridge_graceful_degradation_on_dead_port(caplog, monkeypatch):
    dead_port = _find_free_port()
    dead_url = f"ws://127.0.0.1:{dead_port}"
    monkeypatch.setenv("FORGE_BRIDGE_URL", dead_url)

    with caplog.at_level(logging.WARNING, logger="forge_bridge.mcp.server"):
        # MUST NOT raise. This is the nyquist assertion.
        await mcp_server.startup_bridge()

    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("Could not connect to forge-bridge" in m for m in warning_messages), ...
```

**Adaptation for console port degradation:**
- Bind `127.0.0.1:<busy_port>` on a socket in the test, hold it open.
- Invoke `_start_console_task(app, "127.0.0.1", busy_port)` (or the Typer flag path with `--console-port=<busy_port>`).
- Assert: returns `(None, None)`, logs WARNING matching "Console API disabled — port", never raises.
- Secondary assertion: MCP server still works (unchanged stdio behavior).

---

### `tests/test_console_mcp_resources.py` (unit)

**Analog:** `tests/test_llm.py::test_health_resource_registered` (lines 194-211) — exact pattern

**Adaptation:** Mirror the MagicMock(mcp) pattern, call `register_console_resources(mock_mcp, manifest_service, console_read_api)`, then assert each of `forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}`, `forge://health` appears in `mock_mcp.resource.call_args_list`, and `forge_manifest_read` + `forge_tools_read` appear in `mock_mcp.tool.call_args_list`.

---

### `tests/test_console_stdio_cleanliness.py` (integration — SC#1)

**No direct analog.**

**Partial pattern source:** `tests/test_public_api.py::test_no_forge_specific_strings` (lines 208-224) uses `subprocess.run` but only for a grep.

**Pattern guidance (de novo):**
1. Spawn `forge-bridge` as a subprocess (`subprocess.Popen([sys.executable, "-m", "forge_bridge"], stdin=PIPE, stdout=PIPE, stderr=PIPE)`).
2. Wait for MCP `initialize` framing on stdout — confirm server is ready.
3. In the test loop: concurrently hit `http://127.0.0.1:9996/api/v1/tools` via `httpx` N times while sending `tools/list` over stdin.
4. Assert: the raw bytes on stdout are ONLY MCP JSON-RPC frames — no extra bytes between frames. Use a simple length-prefix validator or regex that matches `Content-Length: <N>\r\n\r\n<JSON>` per MCP stdio framing spec.
5. Document in the test docstring: D-23 runtime UAT, SC#1 nyquist gate.

This is the hardest test to write — flag it as a plan-level implementation risk.

---

### `tests/test_typer_entrypoint.py` (integration — subprocess)

**Analog:** `tests/test_public_api.py::test_no_forge_specific_strings` (lines 208-224) — `subprocess.run` returncode assertion

**Pattern excerpt:**
```python
result = subprocess.run(
    ["grep", "-r", "-E", "portofino|assist-01|ACM_", str(root), "--include=*.py"],
    capture_output=True,
    text=True,
)
assert result.returncode == 1, ...
```

**Adaptation — Typer acceptance tests per D-11:**
```python
def test_forge_bridge_console_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "forge_bridge", "console", "--help"],
        capture_output=True, text=True, timeout=5.0,
    )
    assert result.returncode == 0, (
        f"forge-bridge console --help must exit 0. stderr: {result.stderr}"
    )
    assert "Artist Console" in result.stdout
```

**Bare-invocation test:** Use `subprocess.Popen` with `timeout`, kill after a short wait, assert that stderr shows the "Connected to forge-bridge" (or graceful-degradation WARNING) log line — confirming `mcp_main()` was entered.

---

### `forge_bridge/__main__.py` (MODIFIED — Typer root)

**Existing pattern** (lines 1-4):
```python
"""Allow running as: python -m forge_bridge"""
from forge_bridge.mcp.server import main

main()
```

**Replacement pattern source:** RESEARCH.md §7 verbatim. Typer is transitive via `mcp[cli]` (verified STACK.md). No existing Typer usage in codebase — this is the first.

**Key adaptations:**
- `no_args_is_help=False` on root app (D-10: bare call boots MCP, doesn't print help).
- `invoke_without_command=True` on callback (RESEARCH.md §7 + Pitfall P9-6).
- Manual env-var handling inside callback for D-27 precedence (`flag > env > default`) — NOT `envvar=` kwarg on `typer.Option` (RESEARCH.md §7 comment).
- Lazy import of `forge_bridge.mcp.server.main` INSIDE the callback (defer heavy imports until after Typer has confirmed bare invocation).

---

### `forge_bridge/mcp/server.py` (MODIFIED — `_lifespan` extension)

**Existing pattern** (`forge_bridge/mcp/server.py` lines 68-89):
```python
@asynccontextmanager
async def _lifespan(mcp_server: FastMCP):
    """Server lifespan: connect client, start watcher, clean up on exit."""
    global _server_started
    # Connect to forge-bridge
    await startup_bridge()
    _server_started = True

    # Launch synthesized tool watcher as background task
    from forge_bridge.learning.watcher import watch_synthesized_tools
    watcher_task = asyncio.create_task(watch_synthesized_tools(mcp_server))

    try:
        yield
    finally:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass
        await shutdown_bridge()
        _server_started = False
```

**Extension guidance (D-31 6-step sequence) — insert AFTER `_server_started = True` and BEFORE existing `watcher_task = ...` line:**

Step 2 (ManifestService + canonical ExecutionLog):
```python
from forge_bridge.learning.execution_log import ExecutionLog
from forge_bridge.console.manifest_service import ManifestService
execution_log = ExecutionLog()
manifest_service = ManifestService()
global _canonical_execution_log, _canonical_manifest_service
_canonical_execution_log = execution_log
_canonical_manifest_service = manifest_service
```

Step 3 (modify existing watcher_task line to inject manifest_service):
```python
watcher_task = asyncio.create_task(
    watch_synthesized_tools(mcp_server, manifest_service=manifest_service),
    name="watcher_task",
)
```

Steps 4-6 (new — ConsoleReadAPI + register_console_resources + _start_console_task) — follow RESEARCH.md §10 excerpt.

**`_start_console_task` helper — graceful-degradation pattern source is the existing `startup_bridge`** (`forge_bridge/mcp/server.py` lines 114-154):

```python
async def startup_bridge(
    server_url: str | None = None,
    client_name: str | None = None,
) -> None:
    ...
    try:
        await _client.start()
        await _client.wait_until_connected(timeout=10.0)
        logger.info(f"Connected to forge-bridge at {server_url}")
    except Exception as e:
        logger.warning(
            f"Could not connect to forge-bridge at {server_url}: {e}\n"
            "forge_* tools will fail. flame_* tools still work if Flame is running."
        )
        try:
            await _client.stop()
        except Exception:
            pass
        _client = None
```

**Mirror this exactly for `_start_console_task` (API-06 / D-29):**
- Try: socket precheck + construct uvicorn.Config + Server + create_task + startup barrier.
- Except OSError: WARNING log with port info + reason, return `(None, None)`.
- The WARNING message must include "Console API disabled — port" per test assertion.

**Teardown extension** — insert before existing `watcher_task.cancel()`:
```python
if console_task is not None:
    console_server.should_exit = True
    try:
        await asyncio.wait_for(console_task, timeout=5.0)
    except asyncio.TimeoutError:
        console_task.cancel()
        try:
            await console_task
        except (asyncio.CancelledError, Exception):
            pass
```

**New module-level globals per D-16 instance-identity:**
- `_canonical_execution_log: ExecutionLog | None = None`
- `_canonical_manifest_service: ManifestService | None = None`

These are exposed so `get_health()` can verify `id(execution_log) == id(_canonical_execution_log)` and same for `manifest_service`. Same shape as existing `_client` and `_server_started` module globals.

---

### `forge_bridge/learning/execution_log.py` (MODIFIED — deque + snapshot)

**Existing `__init__` pattern** (lines 110-119) — extend with deque construction:
```python
# Before existing _replay() call:
maxlen = int(os.environ.get("FORGE_EXEC_SNAPSHOT_MAX", _DEFAULT_MAX_SNAPSHOT))
self._records: collections.deque[ExecutionRecord] = collections.deque(maxlen=maxlen)
self._promoted_hashes: set[str] = set()  # RESEARCH.md §Pitfall P9-3 recommendation (b)
```

**Existing `_replay` pattern** (lines 147-180) — extend the normal-record branch (line 173) to append to `_records`:
```python
# After existing counters/code/intent updates:
rec_obj = ExecutionRecord(
    code_hash=code_hash,
    raw_code=rec["raw_code"],
    intent=rec.get("intent"),
    timestamp=rec.get("timestamp", ""),
    promoted=bool(rec.get("promoted", False)),
)
self._records.append(rec_obj)  # newest-wins naturally via deque maxlen
```

Also extend the promotion-only branch (line 168) to populate `self._promoted_hashes.add(code_hash)` for D-09.

**Existing `record` pattern** (lines 182-235) — append to deque AFTER the existing JSONL flush + callback fire (after line 231, before the threshold check):
```python
# D-06 contract: deque append AFTER JSONL flush + callback fire
self._records.append(record)
```

**NEW `snapshot` method** — no existing analog; use RESEARCH.md §5 verbatim:
```python
def snapshot(
    self,
    limit: int = 50,
    offset: int = 0,
    since: Optional[datetime] = None,
    promoted_only: bool = False,
    tool: Optional[str] = None,
    code_hash: Optional[str] = None,
) -> tuple[list[ExecutionRecord], int]:
    ...
```

**NEW `mark_promoted` extension** — set addition per D-09:
```python
def mark_promoted(self, code_hash: str) -> None:
    self._promoted.add(code_hash)
    self._promoted_hashes.add(code_hash)  # NEW — D-09 for snapshot projection
    rec = {...}  # existing JSONL write unchanged
```

**Module-level additions:**
- `_DEFAULT_MAX_SNAPSHOT = 10_000` (top of file, alongside `LOG_PATH`)
- `import collections, fnmatch, dataclasses` (alongside existing imports)

---

### `forge_bridge/learning/watcher.py` (MODIFIED — ManifestService injection)

**Existing signature** (lines 33-38):
```python
async def watch_synthesized_tools(
    mcp: "FastMCP",
    synthesized_dir: Path | None = None,
    poll_interval: float = _POLL_INTERVAL,
    tracker: "ProbationTracker | None" = None,
) -> None:
```

**Extension — add kwarg (backward-compatible default per Claude's discretion):**
```python
async def watch_synthesized_tools(
    mcp: "FastMCP",
    synthesized_dir: Path | None = None,
    poll_interval: float = _POLL_INTERVAL,
    tracker: "ProbationTracker | None" = None,
    manifest_service: "ManifestService | None" = None,
) -> None:
```

**TYPE_CHECKING block** — add the import (line 19-22):
```python
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from forge_bridge.learning.probation import ProbationTracker
    from forge_bridge.console.manifest_service import ManifestService
```

**Registration point** (lines 183-186 of existing):
```python
try:
    provenance = _read_sidecar(path)
    register_tool(mcp, fn, name=stem, source="synthesized", provenance=provenance)
    seen[stem] = digest
    logger.info(f"Registered synthesized tool: {stem}")
except ValueError as e:
    logger.warning(f"Skipped {stem}: {e}")
```

**Extension — insert after `seen[stem] = digest`:**
```python
if manifest_service is not None:
    # Build ToolRecord from sidecar + register_tool kwargs; register with manifest.
    # This is run sync-in-async (watcher scan is sync; manifest_service.register is async).
    # Use asyncio.get_event_loop().create_task(...) to schedule without blocking scan.
    try:
        record = _build_tool_record(stem, provenance, digest)
        asyncio.create_task(manifest_service.register(record))
    except Exception:
        logger.exception("Failed to register %s with manifest service", stem)
```

Planner note: the `_build_tool_record` helper is new; plans should extract sidecar fields (`_meta.version`, `tags`, etc.) into `ToolRecord` kwargs. Follow `_read_sidecar`'s existing size-budget + sanitization outputs as the input shape.

**Remove-tool path extension** (lines 190-198) — insert `manifest_service.remove(stem)` call alongside existing `mcp.remove_tool(stem)`.

---

### `forge_bridge/__init__.py` (MODIFIED — optional re-exports)

**Existing pattern** (lines 31-77): import block + `__all__` list (16 entries).

**Extension (if planner opts to re-export console symbols):**
```python
# Insert before "# Flame HTTP bridge" section:
# Console (v1.3 Artist Console read layer)
from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI

# Add to __all__:
"ManifestService", "ToolRecord", "ConsoleReadAPI",
```

**Version bump ceremony** (historical precedent in `tests/test_public_api.py` lines 172-180 — every phase that grows `__all__` bumps the minor version):
- Phase 4 pinned `1.0.0` (16 → stable surface).
- Phase 6-03 bumped `1.1.0` (added 3 LRN-02/LRN-04 symbols).
- Phase 8 bumped `1.3.0` (added `StoragePersistence` — surface 15 → 16).
- **Phase 9 bumps `1.3.0` → `1.4.0`** IF re-exports land. Update `pyproject.toml` version + `tests/test_public_api.py::test_package_version` + `test_public_surface_has_16_symbols` (grow to 19).

Planner decision (per Claude's discretion in CONTEXT.md): Whether to re-export `ConsoleReadAPI` or keep it internal to `forge_bridge.console`. Recommendation (matches forge_bridge.llm pattern — `LLMRouter` and `get_router` are re-exported): YES, re-export, so projekt-forge (MFST-06) has a first-class import path.

---

### `pyproject.toml` (MODIFIED — ruff T20 gate per D-22)

**Existing pattern** (lines 42-44):
```toml
[tool.ruff]
line-length = 100
target-version = "py310"
```

**Extension (paste in after existing `[tool.ruff]` block):**
```toml
[tool.ruff.lint]
extend-select = ["T20"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["T20"]
# Phase 11: add "forge_bridge/cli/**" carve-out when CLI subcommands ship.
```

Version field — only bump `version = "1.3.0"` to `"1.4.0"` in pyproject.toml if `__init__.py` re-exports are added per planner decision above.

---

## Shared Patterns

### Logger-per-module (EVERY new file)

**Source:** Universal in codebase — `logging.getLogger(__name__)` at module top.

**Canonical excerpt** (`forge_bridge/mcp/server.py` line 44, `forge_bridge/learning/execution_log.py` line 23, `forge_bridge/llm/router.py` line 35):
```python
import logging
logger = logging.getLogger(__name__)
```

**Apply to:** Every new file under `forge_bridge/console/`. D-22 ruff gate enforces no `print(` anywhere in the package.

---

### Graceful degradation (NO new file raises from a background task)

**Source:** `forge_bridge/mcp/server.py::startup_bridge` (lines 138-154).

**Excerpt:**
```python
try:
    await _client.start()
    await _client.wait_until_connected(timeout=10.0)
    logger.info(f"Connected to forge-bridge at {server_url}")
except Exception as e:
    logger.warning(
        f"Could not connect to forge-bridge at {server_url}: {e}\n"
        "forge_* tools will fail. flame_* tools still work if Flame is running."
    )
    try:
        await _client.stop()
    except Exception:
        pass
    _client = None
```

**Apply to:**
- `_start_console_task` (API-06 / D-29 port-unavailable degradation).
- Every route handler error path (log WARNING, return envelope `_error(...)` — never re-raise to ASGI).
- `_lifespan` task bodies: each of `watcher_task`, `console_task` wraps its own failure in `try: ... except Exception: logger.warning(...)` so one failure doesn't cancel siblings (D-30).

**Error-message hygiene per Phase 8 LRN:** Use `type(exc).__name__` instead of `str(exc)` in WARNING logs — some exceptions (SQLAlchemy DB URLs, anthropic API errors) stringify with credentials attached. RESEARCH.md §Anti-Patterns.

---

### Frozen-dataclass wire records

**Source:** `forge_bridge/learning/execution_log.py::ExecutionRecord` (lines 33-50).

**Apply to:** `ToolRecord` in `forge_bridge/console/manifest_service.py`. See detailed adaptation above.

---

### Env-var-then-default config

**Source:** `forge_bridge/llm/router.py::LLMRouter.__init__` (lines 79-97), `forge_bridge/learning/execution_log.py::__init__` line 112 (`FORGE_PROMOTION_THRESHOLD`), `forge_bridge/mcp/server.py::startup_bridge` line 128 (`FORGE_BRIDGE_URL`).

**Apply to:**
- `FORGE_CONSOLE_PORT` in `__main__.py` callback and `_lifespan`.
- `FORGE_EXEC_SNAPSHOT_MAX` in `ExecutionLog.__init__`.

**Precedence chain:** explicit constructor arg > env var > hardcoded default. Verified by `tests/test_llm.py::test_env_fallback_at_init_time` (lines 63-75) and `::test_injected_arg_beats_env` (lines 78-83).

---

### `asyncio.create_task` + cancel-on-exit

**Source:** `forge_bridge/mcp/server.py::_lifespan` (lines 78, 83-87) + `forge_bridge/client/async_client.py::start/stop` (lines 183-185, 200-205).

**Excerpt:**
```python
# Startup
watcher_task = asyncio.create_task(watch_synthesized_tools(mcp_server))

# Teardown in finally:
watcher_task.cancel()
try:
    await watcher_task
except asyncio.CancelledError:
    pass
```

**Apply to:** `console_task` lifecycle in `_lifespan`. Identical shape; add `asyncio.wait_for(task, timeout=5.0)` for uvicorn's graceful shutdown (set `server.should_exit = True` first).

---

### MCP resource registration via dedicated register function

**Source:** `forge_bridge/llm/health.py::register_llm_resources` (lines 7-17) + call site `forge_bridge/mcp/registry.py` lines 722-723.

**Two call-site patterns to consider:**
1. **At module import** — `register_builtins(mcp)` is called at `forge_bridge/mcp/server.py` line 107 (module-import time). This works for `register_llm_resources(mcp)` because it has no runtime singleton deps (it lazy-imports `get_router()` inside the resource body).
2. **From `_lifespan` startup** — Phase 9 REQUIRES this pattern because `register_console_resources(mcp, manifest_service, console_read_api)` needs live singletons. Call it from `_lifespan` step 5 per D-31.

This is a pattern divergence: Phase 9 introduces a second resource-registration call site (runtime vs import). Plans should document this explicitly.

---

### Async context manager `_lifespan` extension (ADDITIVE)

**Source:** `forge_bridge/mcp/server.py::_lifespan` (lines 68-89).

**Extension rule:** All new setup runs BEFORE `try: yield`; all teardown runs in `finally:` in reverse order of setup. Preserve the existing `_server_started` guard (used by `register_tools` post-run check per `forge_bridge/mcp/registry.py` lines 160-165). Do not restructure the context manager — additive-only.

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `forge_bridge/console/app.py` | Starlette factory | First Starlette embedding in codebase. Use RESEARCH.md §1 verbatim. |
| `forge_bridge/console/routes.py` | Starlette route handlers | First ASGI route handlers. Use RESEARCH.md §Pattern 2 + §5 verbatim. |
| `forge_bridge/console/logging_config.py` | Uvicorn log config dict | First custom uvicorn logging config. Use RESEARCH.md §3 verbatim. |
| `tests/test_console_stdio_cleanliness.py` | Subprocess MCP wire test | No existing test uses subprocess for an MCP wire check. SC#1 test is de novo — call out as implementation risk. |

**Note on pattern divergence:** The Phase 9 plan introduces three firsts for this codebase: Starlette/ASGI embedding, programmatic uvicorn task, and Typer CLI. All three are transitive deps from `mcp[cli]` (no new pip deps per CONTEXT.md and RESEARCH.md §Standard Stack). Planner should reference RESEARCH.md §Code Examples for the canonical shapes — no existing analogs in the forge-bridge tree.

---

## Metadata

**Analog search scope:**
- `forge_bridge/` package (all subpackages)
- `tests/` directory
- `pyproject.toml`
- `.planning/phases/09-read-api-foundation/` (inputs)

**Files scanned:** ~60 Python files across forge_bridge/ + tests/, plus pyproject.toml.

**Key insights:**
1. The `forge_bridge/llm/` package (router.py + health.py + __init__.py) is the most load-bearing analog — mirror its layout and style for `forge_bridge/console/`.
2. `forge_bridge/mcp/server.py::startup_bridge` is the canonical graceful-degradation shape — mirror for every new fallible startup step (Phase 9 `_start_console_task`, future Phase 10 endpoints).
3. `forge_bridge/learning/execution_log.py` is the canonical frozen-dataclass + in-memory-state + JSONL-replay analog — all new registry-like components (`ManifestService`, future Phase 10 state) copy this shape.
4. `tests/test_mcp_server_graceful_degradation.py` is the canonical port-bind/caplog test fixture — copy `_find_free_port()` + `_reset_server_module` fixture + `caplog.at_level(...)` pattern for every Phase 9 degradation test.
5. `tests/test_llm.py::test_health_resource_registered` is the canonical MagicMock(mcp) + call_args_list test for MCP registration — copy for `test_console_mcp_resources.py`.

**Pattern extraction date:** 2026-04-22
