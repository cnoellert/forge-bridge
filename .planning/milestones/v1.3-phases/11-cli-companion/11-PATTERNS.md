# Phase 11: CLI Companion — Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 21 (11 create, 3 modify, 7 test-create)
**Analogs found:** 21 / 21

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `forge_bridge/__main__.py` | entry-point (modify) | request-response | `forge_bridge/__main__.py` itself | self |
| `forge_bridge/cli/__init__.py` | package init (create) | — | `forge_bridge/console/__init__.py` | role-match |
| `forge_bridge/cli/client.py` | http-client utility (create) | request-response | `forge_bridge/bridge.py` | role-match |
| `forge_bridge/cli/render.py` | render utility (create) | transform | `forge_bridge/console/ui_handlers.py` | role-match |
| `forge_bridge/cli/since.py` | parser utility (create) | transform | `forge_bridge/console/handlers.py` `_parse_filters` | partial-match |
| `forge_bridge/cli/tools.py` | cli-command (create) | request-response | `forge_bridge/console/handlers.py` `tools_handler` | role-match |
| `forge_bridge/cli/execs.py` | cli-command (create) | request-response | `forge_bridge/console/handlers.py` `execs_handler` | role-match |
| `forge_bridge/cli/manifest.py` | cli-command (create) | request-response | `forge_bridge/console/handlers.py` `manifest_handler` | role-match |
| `forge_bridge/cli/health.py` | cli-command (create) | request-response | `forge_bridge/console/handlers.py` `health_handler` | role-match |
| `forge_bridge/cli/doctor.py` | cli-command (create) | request-response + file-I/O | `forge_bridge/console/read_api.py` `get_health` | partial-match |
| `pyproject.toml` | config (modify) | — | `pyproject.toml` itself | self |
| `tests/conftest.py` | test-fixture (modify) | — | `tests/test_console_http_transport.py` | role-match |
| `tests/test_cli_commands.py` | test/unit (create) | — | `tests/test_typer_entrypoint.py` | exact |
| `tests/test_cli_client.py` | test/unit (create) | — | `tests/test_console_http_transport.py` | role-match |
| `tests/test_cli_json_mode.py` | test/unit (create) | — | `tests/test_typer_entrypoint.py` | role-match |
| `tests/test_cli_rendering.py` | test/unit (create) | — | `tests/test_ui_js_disabled_graceful_degradation.py` | partial-match |
| `tests/test_cli_tools.py` | test/unit (create) | — | `tests/test_ui_js_disabled_graceful_degradation.py` | partial-match |
| `tests/test_cli_execs.py` | test/unit (create) | — | `tests/test_ui_js_disabled_graceful_degradation.py` | partial-match |
| `tests/test_cli_manifest.py` | test/unit (create) | — | `tests/test_ui_js_disabled_graceful_degradation.py` | partial-match |
| `tests/test_cli_health.py` | test/unit (create) | — | `tests/test_ui_js_disabled_graceful_degradation.py` | partial-match |
| `tests/test_cli_doctor.py` | test/unit (create) | — | `tests/test_console_http_transport.py` | partial-match |

---

## Pattern Assignments

### `forge_bridge/__main__.py` (entry-point, modify)

**Analog:** `forge_bridge/__main__.py` (self — lines 1-59)

**Current scaffold pattern** (lines 17-29 — the `console_app` group Phase 11 fills):

```python
app = typer.Typer(
    name="forge-bridge",
    help="forge-bridge — MCP server + Artist Console.",
    no_args_is_help=False,  # bare invocation must boot MCP, not print help (D-10)
)

# Empty subcommand group for Phase 11 to fill
console_app = typer.Typer(
    name="console",
    help="Artist Console CLI (subcommands arrive in Phase 11).",
    no_args_is_help=True,  # `forge-bridge console` alone prints help
)
app.add_typer(console_app, name="console")
```

**D-27 env-override pattern** (lines 43-55 — port propagation the CLI subcommands inherit):

```python
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    console_port: Optional[int] = typer.Option(
        None,
        "--console-port",
        help="Override console HTTP API port (default 9996, or $FORGE_CONSOLE_PORT).",
        envvar=None,  # manual env lookup below for D-27 precedence clarity
    ),
) -> None:
    if ctx.invoked_subcommand is not None:
        return  # subcommand will run; callback returns early
    if console_port is not None:
        os.environ["FORGE_CONSOLE_PORT"] = str(console_port)
    from forge_bridge.mcp.server import main as mcp_main
    mcp_main()
```

**Delta:** Phase 11 adds five `console_app.command("tools")(tools.tools_cmd)` style registrations after the existing `app.add_typer(console_app, name="console")` line. No other changes to this file.

---

### `forge_bridge/cli/__init__.py` (package init, create)

**Analog:** `forge_bridge/console/__init__.py` (empty package marker)

**Pattern:** Empty file or single-line docstring. No re-exports needed — commands are imported directly in `__main__.py`.

**Delta:** New package; zero runtime content required.

---

### `forge_bridge/cli/client.py` (http-client utility, create)

**Analog:** `forge_bridge/bridge.py` (lines 1-168 — async httpx client; same pattern inverted to sync)

**Typed-exception pattern** (bridge.py lines 100-110 — class hierarchy to copy, sync variant):

```python
class BridgeError(Exception):
    """Raised when Flame code execution fails."""
    pass


class BridgeConnectionError(Exception):
    """Raised when the bridge is unreachable."""
    pass
```

**httpx error catch pattern** (bridge.py lines 141-152 — connection error matrix; adapt to sync):

```python
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
```

**Config-from-env pattern** (bridge.py lines 32-38 — read port from env):

```python
_config = _BridgeConfig(
    host=os.environ.get("FORGE_BRIDGE_HOST", "127.0.0.1"),
    port=int(os.environ.get("FORGE_BRIDGE_PORT", "9999")),
    timeout=int(os.environ.get("FORGE_BRIDGE_TIMEOUT", "60")),
)
```

**Envelope shape consumed by client** (handlers.py lines 43-60 — what the CLI unwraps):

```python
def _envelope(data, **meta) -> JSONResponse:
    """2xx envelope — applied on every success path (D-01)."""
    return JSONResponse({"data": data, "meta": meta})


def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    """4xx/5xx envelope — applied on every failure path. NEVER leak tracebacks."""
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)
```

**LRN-05 credential-leak rule** (read_api.py lines 200-205 — `type(exc).__name__` not `str(exc)`):

```python
            except Exception as exc:  # noqa: BLE001 - intentional: never surface
                return {
                    "status": "fail",
                    "url": self._flame_bridge_url,
                    "detail": type(exc).__name__,
                }
```

**Delta:** CLI `client.py` INVERTS the direction — it reads `{"data": ..., "meta": ...}` and unwraps to `data`, raises typed `ServerUnreachableError` / `ServerError` instead of `BridgeConnectionError`. Must use sync `httpx.Client(base_url=..., timeout=10.0)` as a context manager per RESEARCH.md anti-pattern note. Catch matrix extends bridge.py by adding `httpx.RemoteProtocolError` (verified not subclass of NetworkError — must be caught separately). `FORGE_CONSOLE_PORT` default is `9996` (not `9999`). `int()` conversion must be wrapped in try/except for `ValueError` on malformed env values.

---

### `forge_bridge/cli/render.py` (render utility, create)

**Analog:** `forge_bridge/console/ui_handlers.py` (no Rich — this is the closest existing "presentation layer" module; all Rich usage is new territory)

**No existing Rich usage in the codebase** — confirmed by grep: zero `from rich` or `import rich` hits in `forge_bridge/`. The render module is greenfield.

**Recommended pattern from RESEARCH.md** (lines 221-224 — `make_console` factory):

```python
def make_console(no_color: bool = False, stderr: bool = False) -> Console:
    return Console(no_color=no_color, stderr=stderr)
```

**CONTEXT.md Area 3 locked choices to encode in render.py:**
- `rich.box.SQUARE` for all tables
- Header style = `bold yellow`
- Status color map: `ok` → green, `degraded`/`warn` → amber (yellow), `fail` → red, `absent` → dim
- Hash truncation: 8 chars on lists, full on drilldowns
- `Created ▼` column header glyph (sort-order affordance)

**Delta:** Entirely new module; no codebase analog. The Web UI uses Jinja2 templates + CSS; the CLI uses Rich primitives. The column choices are ported from Phase 10.1 D-40/D-41 decisions (artist columns first, `code_hash`/`namespace`/`observation_count` demoted to `--json`-only).

---

### `forge_bridge/cli/since.py` (parser utility, create)

**Analog:** `forge_bridge/console/handlers.py` `_parse_filters` (lines 80-100 — server-side ISO 8601 parse; the `since.py` module does the client-side relative-grammar parse + ISO passthrough)

**Server-side `since` parse pattern to invert** (handlers.py lines 88-100):

```python
    since_raw = qp.get("since")
    since: Optional[datetime] = None
    if since_raw is not None:
        try:
            since = datetime.fromisoformat(since_raw)
        except ValueError:
            # Surface as a parse error at the route boundary
            raise ValueError(f"invalid 'since' value: {since_raw!r} (expected ISO 8601)")
```

**Complete implementation from RESEARCH.md** (lines 238-265 — verbatim; ~15 LOC, stdlib only):

```python
import re
from datetime import datetime, timedelta, timezone


_RELATIVE_RE = re.compile(r'^(\d+)(m|h|d|w)$')
_UNIT_SECONDS = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}


def parse_since(value: str) -> str:
    """Parse --since value into an ISO 8601 string for the API.

    Accepts:
      - Relative: "30m", "24h", "7d", "2w"
      - ISO 8601: "2026-04-24T10:00:00Z", "2026-04-24T10:00:00+00:00"

    Returns an ISO 8601 UTC string. Raises ValueError on bad input.
    """
    m = _RELATIVE_RE.match(value)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        dt = datetime.now(timezone.utc) - timedelta(seconds=n * _UNIT_SECONDS[unit])
        return dt.isoformat()
    # Normalize Z suffix for Python 3.10 compatibility
    normalized = value[:-1] + '+00:00' if value.endswith('Z') else value
    dt = datetime.fromisoformat(normalized)  # ValueError on bad input — let it propagate
    return dt.isoformat()
```

**Delta:** Client-side extension of the server-side pattern. Adds relative grammar (`Nm/Nh/Nd/Nw`) before falling through to ISO parse. Z-normalization handles Python 3.10 compat (`datetime.fromisoformat` does not accept `Z` in 3.10). `ValueError` propagates to the CLI command body which converts it to a user error + exit 1.

---

### `forge_bridge/cli/tools.py` (cli-command, create)

**Analog:** `forge_bridge/console/handlers.py` `tools_handler` + `tool_detail_handler` (lines 105-123)

**Handler call pattern** (handlers.py lines 105-123 — what the CLI mirrors at HTTP layer):

```python
async def tools_handler(request: Request) -> JSONResponse:
    try:
        tools = await request.app.state.console_read_api.get_tools()
        return _envelope([t.to_dict() for t in tools], total=len(tools))
    except Exception as exc:
        logger.warning("tools_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read tools", status=500)


async def tool_detail_handler(request: Request) -> JSONResponse:
    name = request.path_params["name"]
    try:
        tool = await request.app.state.console_read_api.get_tool(name)
    except Exception as exc:
        logger.warning("tool_detail_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read tool", status=500)
    if tool is None:
        return _error("tool_not_found", f"no tool named {name!r}", status=404)
    return _envelope(tool.to_dict())
```

**ToolRecord dict shape** (manifest_service.py lines 39-86 — the dict the CLI renderer receives):

```python
@dataclass(frozen=True)
class ToolRecord:
    name: str
    origin: str                         # "builtin" | "synthesized"
    namespace: str                      # "flame" | "forge" | "synth"
    synthesized_at: Optional[str] = None
    code_hash: Optional[str] = None
    version: Optional[str] = None
    observation_count: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)
    meta: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = list(self.tags)
        d["meta"] = dict(self.meta)
        return d
```

**Typer command registration pattern** (test_typer_entrypoint.py lines 145-157 — how CliRunner invokes commands):

```python
from typer.testing import CliRunner
runner = CliRunner()
with patch("forge_bridge.mcp.server.main", side_effect=_stub_mcp_main):
    result = runner.invoke(entrypoint.app, ["--console-port", "9997"])
assert result.exit_code == 0
```

**Delta:** CLI reads the `{data, meta}` envelope via `client.py`, receives a list of `ToolRecord.to_dict()` dicts, applies client-side filters (origin, namespace, search), then passes filtered list to `render.py`. No async — sync function body. `typer.Option(...)` with `Annotated` type hints for flag declarations. Positional `typer.Argument` for the optional `name` drilldown param. Exit codes: `0` success, `1` server error, `2` unreachable.

---

### `forge_bridge/cli/execs.py` (cli-command, create)

**Analog:** `forge_bridge/console/handlers.py` `execs_handler` (lines 126-153)

**W-01 client-side tool-filter pattern** (handlers.py lines 126-138 — the server REJECTS `?tool=...`; CLI must avoid sending it):

```python
async def execs_handler(request: Request) -> JSONResponse:
    try:
        # W-01: reject `?tool=...` with 400 `not_implemented`
        if request.query_params.get("tool"):
            return _error(
                "not_implemented",
                "tool filter reserved for v1.4",
                status=400,
            )
        limit, offset = _parse_pagination(request)
        try:
            since, promoted_only, code_hash = _parse_filters(request)
        except ValueError as ve:
            return _error("bad_request", str(ve), status=400)
        records, total = await request.app.state.console_read_api.get_executions(
            limit=limit, offset=offset, since=since,
            promoted_only=promoted_only, code_hash=code_hash,
        )
```

**ExecutionRecord dict shape** (execution_log.py lines 37-54):

```python
@dataclass(frozen=True)
class ExecutionRecord:
    code_hash: str
    raw_code: str
    intent: Optional[str]
    timestamp: str
    promoted: bool
```

**Pagination defaults** (handlers.py lines 37-38):

```python
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500  # D-05
```

**Delta:** CLI builds the API query URL using only server-supported params (`since`, `promoted_only`, `code_hash`, `limit`, `offset`). Does NOT send `tool` to the server (would get 400). After receiving records, applies `--tool` client-side filter in Python. Emits one stderr line on every `--tool` invocation: `note: --tool is filtered client-side until v1.4 API support; narrow with --since to scan less history.` Suppress stderr note when `--json` flag is active. The `--since`/`--until` values go through `since.py:parse_since()` before being appended to the query string.

---

### `forge_bridge/cli/manifest.py` (cli-command, create)

**Analog:** `forge_bridge/console/handlers.py` `manifest_handler` (lines 156-163)

**Manifest handler pattern** (handlers.py lines 156-163):

```python
async def manifest_handler(request: Request) -> JSONResponse:
    try:
        data = await request.app.state.console_read_api.get_manifest()
        return _envelope(data)
    except Exception as exc:
        logger.warning("manifest_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read manifest", status=500)
```

**Manifest dict shape** (read_api.py lines 148-160 — the inner `data` the CLI unwraps):

```python
    async def get_manifest(self) -> dict:
        tools = self._manifest_service.get_all()
        return {
            "tools": [t.to_dict() for t in tools],
            "count": len(tools),
            "schema_version": "1",
        }
```

**Delta:** Simplest subcommand — single GET, no filters, no pagination. `--json` outputs the byte-identical `/api/v1/manifest` body (envelope and all). Rich table reuses the tools column set from `render.py` (manifest IS the tool list). No client-side filtering.

---

### `forge_bridge/cli/health.py` (cli-command, create)

**Analog:** `forge_bridge/console/handlers.py` `health_handler` (lines 165-172) + `forge_bridge/console/read_api.py` `get_health` return shape (lines 370-406)

**Health handler pattern** (handlers.py lines 165-172):

```python
async def health_handler(request: Request) -> JSONResponse:
    try:
        data = await request.app.state.console_read_api.get_health()
        return _envelope(data)
    except Exception as exc:
        logger.warning("health_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read health", status=500)
```

**Health response structure** (read_api.py lines 370-406 — the inner `data` shape the CLI renders):

```python
        services = {
            "mcp": mcp,
            "flame_bridge": flame_bridge,
            "ws_server": ws_server,
            "llm_backends": llm_backends,
            "watcher": watcher,
            "storage_callback": storage_callback,
            "console_port": console_port,
        }
        # ... aggregate logic ...
        return {
            "status": status,           # "ok" | "degraded" | "fail"
            "ts": datetime.now(timezone.utc).isoformat(),
            "version": __version__,
            "services": services,
            "instance_identity": instance_identity,
        }
```

**Service group blocks for Rich Panel layout** (read_api.py lines 248-298 — per D-15 critical vs non-critical):

```python
        def _check_mcp() -> dict:
            ...
            return {"status": "ok", "detail": "lifespan started"}
            # or: {"status": "fail", "detail": "lifespan not started"}

        def _check_watcher() -> dict:
            ...
            return {"status": "ok", "task_done": False, "detail": ""}
            # or: {"status": "fail", "task_done": True, "detail": type(exc).__name__}
```

**D-15 aggregate logic** (read_api.py lines 381-399 — critical vs non-critical classification):

```python
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
```

**Delta:** CLI renders four Rich Panels matching CONTEXT.md Area 3 group layout: (1) `mcp · watcher · console_port` critical block, (2) `flame_bridge · ws_server` degraded-tolerant, (3) `llm_backends` one line per backend, (4) `storage_callback · instance_identity` provenance. Status colors via `render.py` chip map. `--json` outputs byte-identical envelope body.

---

### `forge_bridge/cli/doctor.py` (cli-command + file-I/O, create)

**Analog:** `forge_bridge/console/read_api.py` (lines 178-406 — server-side health probe fan-out pattern; doctor mirrors this client-side with additional file probes)

**Probe structure to mirror** (read_api.py lines 182-298 — check → dict with status/detail):

```python
        async def _check_flame_bridge() -> dict:
            try:
                async with httpx.AsyncClient(timeout=1.5) as client:
                    r = await asyncio.wait_for(
                        client.get(self._flame_bridge_url, timeout=1.5),
                        timeout=2.0,
                    )
                if r.status_code < 500:
                    return {"status": "ok", "url": ..., "detail": f"http {r.status_code}"}
                return {"status": "fail", "url": ..., "detail": f"http {r.status_code}"}
            except Exception as exc:  # noqa: BLE001
                return {"status": "fail", "url": ..., "detail": type(exc).__name__}
```

**JSONL tail-read pattern** (execution_log.py lines 158-201 — file open + line parse; doctor adapts to read last 100 lines):

```python
    def _replay(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path, "r") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed JSONL line")
                        continue
```

**RESEARCH.md safe tail-read recipe** (lines 453-463 — partial-write boundary guard):

```python
def _tail_jsonl(path: str, n: int = 100) -> list[str]:
    with open(path, 'r') as f:
        lines = f.readlines()
    tail = lines[-n:] if len(lines) >= n else lines
    # Skip last line if no trailing newline (partial write boundary)
    if tail and not tail[-1].endswith('\n'):
        tail = tail[:-1]
    return [line.rstrip('\n') for line in tail if line.strip()]
```

**LRN-05 parse-error reporting** (read_api.py line 203 — exception class name only, never `str(exc)`):

```python
                return {"status": "fail", "url": ..., "detail": type(exc).__name__}
```

**Exit code propagation** (test_typer_entrypoint.py lines 152-155 — `typer.Exit(code=N)` pattern):

```python
    result = runner.invoke(entrypoint.app, ["--console-port", "9997"])
    assert result.exit_code == 0
```

**Delta:** Doctor runs entirely sync (no `asyncio.wait_for`). Probe sequence: (1) HTTP GET `/api/v1/health` → if fails, exit 2 immediately with "server is not running on :9996. Start it with: python -m forge_bridge" on stderr. (2) JSONL parseability probe — tail 100 lines, report `line N: ExcClassName` for failures (never raw line content — LRN-05). (3) `~/.forge-bridge/synthesized/` + probation dir presence + `os.access(..., os.W_OK)`. (4) Optional disk-space probe. Exit 0 if all ok/warn; exit 1 if any fail; exit 2 if unreachable. Rich table for TTY, one-line-per-check for `--quiet`.

---

### `pyproject.toml` (config, modify)

**Analog:** `pyproject.toml` itself (lines 51-66 — ruff config and existing T20 carve-out pattern)

**Existing T20 per-file-ignores pattern** (pyproject.toml lines 57-66):

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["T20"]
# Phase 11: add "forge_bridge/cli/**" carve-out when CLI subcommands ship.
# Pre-Phase-5 orphaned modules — broken imports (references nonexistent `forge_mcp`
# module), not re-exported in forge_bridge/__init__.py, not runtime-imported anywhere.
# Carved out so the T20 gate can be live for new code (especially forge_bridge/console/)
# without requiring a pre-emptive dead-code deletion inside Plan 09-01. Track cleanup
# as a follow-up refactor.
"forge_bridge/server.py" = ["T20"]
"forge_bridge/shell.py" = ["T20"]
```

**Existing deps block** (pyproject.toml lines 12-21 — where `rich>=13.9.4` inserts):

```toml
dependencies = [
    "httpx>=0.27",
    "websockets>=13.0",
    "mcp[cli]>=1.19,<2",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "psycopg2-binary>=2.9",
    "jinja2>=3.1",
]
```

**Delta:** Two changes only: (1) Add `"rich>=13.9.4"` to `[project.dependencies]` (transitive via `mcp[cli]→typer` is fragile per RESEARCH.md analysis). (2) The `"forge_bridge/cli/**" = ["T20"]` carve-out comment on line 60 is already a placeholder — activate it only if any CLI module legitimately needs `print()` (none expected; `Console.print()` and `sys.stdout.write()` cover all cases).

---

### `tests/conftest.py` (test-fixture, modify)

**Analog:** `tests/test_console_http_transport.py` (lines 24-75 — `_find_free_port()` and `console_server` fixture; extract into shared conftest)

**`_find_free_port` utility** (test_console_http_transport.py lines 24-27):

```python
def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
```

**Full `console_server` fixture** (test_console_http_transport.py lines 38-74):

```python
@pytest.fixture
async def console_server(tmp_path, monkeypatch):
    """Spin up a real uvicorn-served ConsoleReadAPI on an ephemeral port."""
    from forge_bridge.learning.execution_log import ExecutionLog

    monkeypatch.setattr(
        "forge_bridge.mcp.server._server_started", True, raising=False,
    )
    monkeypatch.setattr(
        "forge_bridge.mcp.server._canonical_watcher_task", None, raising=False,
    )

    log = ExecutionLog(log_path=tmp_path / "execs.jsonl")
    ms = ManifestService()
    await ms.register(_record("a_tool"))
    register_canonical_singletons(log, ms)
    api = ConsoleReadAPI(execution_log=log, manifest_service=ms)

    app = build_console_app(api)
    port = _find_free_port()
    task, server = await _start_console_task(app, "127.0.0.1", port)
    assert task is not None and server is not None

    try:
        yield port, log, ms, api
    finally:
        if server is not None:
            server.should_exit = True
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                task.cancel()
                try:
                    await task
                except Exception:
                    pass
```

**Existing conftest fixture style** (conftest.py lines 17-42 — docstring + usage comment convention):

```python
@pytest.fixture
def monkeypatch_bridge(monkeypatch):
    """Patch forge_bridge.bridge.execute to return a predictable BridgeResponse.

    Usage:
        def test_something(monkeypatch_bridge):
            # bridge.execute is now a coroutine returning the mock response
            ...

    The fixture yields the mock so tests can reconfigure it:
        monkeypatch_bridge.result = '{"key": "value"}'
    """
```

**Delta:** Extract `_find_free_port` as a `@pytest.fixture` called `free_port` (not a bare function). Extract `console_server` from `test_console_http_transport.py` into conftest with a `fake_read_api`-style parameter for the tool records to seed. CLI tests that use CliRunner + `respx` mocking do NOT need the live `console_server` fixture — it is only needed for integration-level tests that invoke CLI commands with a real HTTP round-trip.

---

### `tests/test_cli_commands.py` (test/unit, create — CLI-01)

**Analog:** `tests/test_typer_entrypoint.py` (lines 1-172 — subprocess + CliRunner patterns for Typer entrypoint tests)

**Subprocess-based help test pattern** (test_typer_entrypoint.py lines 20-33):

```python
def test_bare_forge_bridge_help_exits_zero():
    result = subprocess.run(
        [PYTHON, "-m", MODULE, "--help"],
        capture_output=True, text=True, timeout=10.0,
    )
    assert result.returncode == 0, (
        f"python -m forge_bridge --help must exit 0. "
        f"stderr: {result.stderr!r}"
    )
    assert "forge-bridge" in result.stdout
```

**CliRunner-based registration test pattern** (test_typer_entrypoint.py lines 133-157):

```python
from typer.testing import CliRunner
runner = CliRunner()
with patch("forge_bridge.mcp.server.main", side_effect=_stub_mcp_main):
    result = runner.invoke(entrypoint.app, ["--console-port", "9997"])
assert result.exit_code == 0
```

**Delta:** Test five new `console_app.command()` registrations: `tools`, `execs`, `manifest`, `health`, `doctor`. Pattern: `runner.invoke(app, ['console', 'tools', '--help'])` exits 0 and contains `Examples:` in output. No live server needed — `--help` is pure Typer introspection.

---

### `tests/test_cli_client.py` (test/unit, create — CLI-02)

**Analog:** `tests/test_console_http_transport.py` (lines 77-106 — httpx integration tests against a live server)

**httpx async client pattern** (test_console_http_transport.py lines 77-85):

```python
async def test_console_http_transport_serves_tools_on_bound_port(console_server):
    port, _, _, _ = console_server
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"http://127.0.0.1:{port}/api/v1/tools")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
```

**Delta:** CLI-02 tests the SYNC `httpx.Client` (not async). Tests: (1) successful GET returns unwrapped `data`; (2) `httpx.ConnectError` → `ServerUnreachableError`; (3) HTTP 400/500 → `ServerError`; (4) malformed `FORGE_CONSOLE_PORT` env → `ValueError` caught + user error. Use `respx` or `unittest.mock.patch` to mock `httpx.Client.get` — no live server needed for unit tests.

---

### `tests/test_cli_json_mode.py` (test/unit, create — CLI-03 + P-01)

**Analog:** `tests/test_typer_entrypoint.py` (lines 104-124 — import side-effect test using `subprocess.run`) + RESEARCH.md P-01 recipe

**P-01 JSON purity test recipe from RESEARCH.md** (lines 154-161):

```python
def test_json_stdout_is_pure_json(runner, fake_server):
    result = runner.invoke(app, ['console', 'tools', '--json'])
    # stdout = result.output minus any stderr content
    stdout = result.output[len(result.stderr):]  # strip stderr prefix if any
    json.loads(stdout.strip())  # raises on non-JSON bytes — test fails
```

**CliRunner env isolation pattern** (RESEARCH.md lines 494-497):

```python
runner = CliRunner()
result = runner.invoke(app, ['console', 'health'], env={'FORGE_CONSOLE_PORT': str(port)})
```

**Delta:** Three required test cases per RESEARCH.md: (1) positive path — valid data → stdout parseable JSON, stderr empty; (2) connection error → stdout `{"error": {"code": "server_unreachable", ...}}`, exit 2; (3) HTTP error → stdout `{"error": ...}` envelope, exit 1. Must test all five subcommands. `result.stderr` isolation is critical for P-01 — use `result.output[len(result.stderr):]` to strip stderr before JSON parse.

---

### `tests/test_cli_rendering.py` (test/unit, create — CLI-04)

**Analog:** `tests/test_ui_js_disabled_graceful_degradation.py` (lines 1-112 — fake_read_api + Starlette TestClient pattern for rendering assertions)

**`fake_read_api` fixture pattern** (test_ui_js_disabled_graceful_degradation.py lines 21-51):

```python
@pytest.fixture
def fake_read_api():
    tool = ToolRecord(
        name="synth_example", origin="synthesized", namespace="synth",
        synthesized_at="2026-04-22T10:00:00Z",
        code_hash="a" * 64, version="1.0.0", observation_count=5,
        tags=("cursor",), meta=(),
    )
    api = MagicMock()
    api.get_tools = AsyncMock(return_value=[tool])
    api.get_tool = AsyncMock(return_value=tool)
    api.get_executions = AsyncMock(return_value=([], 0))
    api.get_manifest = AsyncMock(return_value={
        "tools": [tool.to_dict()], "count": 1, "schema_version": "1",
    })
    api.get_health = AsyncMock(return_value={
        "status": "ok",
        "services": {
            "mcp": {"status": "ok", "detail": ""},
            "flame_bridge": {"status": "ok", "detail": ""},
            "ws_server": {"status": "ok", "detail": ""},
            "llm_backends": [],
            "watcher": {"status": "ok", "detail": ""},
            "storage_callback": {"status": "absent", "detail": ""},
            "console_port": {"status": "ok", "port": 9996, "detail": ""},
        },
        "instance_identity": {
            "execution_log": {"id_match": True, "detail": "canonical"},
            "manifest_service": {"id_match": True, "detail": "canonical"},
        },
    })
    return api
```

**Delta:** CLI-04 tests use `CliRunner` (not `TestClient`). Non-TTY detection: `CliRunner` runs non-TTY by default — assert Rich SQUARE box chars present in output (Rich renders box chars without ANSI even in non-TTY). `--no-color` test: `Console(no_color=True)` should suppress ANSI codes. `NO_COLOR` env test: `runner.invoke(app, [...], env={'NO_COLOR': '1'})`.

---

### `tests/test_cli_tools.py` (test/unit, create — TOOLS-03)

**Analog:** `tests/test_ui_js_disabled_graceful_degradation.py` (lines 58-67 — parametrized path/content-string pattern; adapt to CliRunner + output substring checks)

**Parametrize pattern** (test_ui_js_disabled_graceful_degradation.py lines 58-67):

```python
@pytest.mark.parametrize("path,expected_substr", [
    ("/ui/tools",                "Registered Tools"),
    ("/ui/tools/synth_example",  "Provenance (_meta)"),
    ...
])
def test_direct_navigation_renders_full_document(client, path, expected_substr):
    r = client.get(path)
    assert r.status_code == 200
    assert expected_substr in r.text
```

**Delta:** Replace HTTP GET + `.text` with `runner.invoke(app, ['console', 'tools']) + result.output`. Test column header presence (`Name`, `Status`, `Type`, `Created ▼`). Test `--origin synthesized` produces only synthesized tools. Test empty result produces "No tools found" footer text (not a crash).

---

### `tests/test_cli_execs.py` (test/unit, create — EXECS-03)

**Analog:** `tests/test_ui_js_disabled_graceful_degradation.py` (same CliRunner-adapted pattern as tools)

**`since.py` test cases from RESEARCH.md** (lines 270-279 — 9 required cases):

```
"30m"  → ISO string ~30min ago
"24h"  → ISO string ~24h ago
"7d"   → ISO string ~7d ago
"2w"   → ISO string ~2w ago
"2026-04-24T10:00:00Z"  → "2026-04-24T10:00:00+00:00"
"2026-04-24"  → parses without error
"bad_input"   → ValueError
"P1D"         → ValueError
"yesterday"   → ValueError
```

**Delta:** Test `--tool` flag emits stderr note (D-04). Test `--since 24h` produces a valid API call with ISO 8601 value. Test `--tool` with zero matches produces empty table + stderr note. Test `execs <hash>` drilldown (implemented as `?code_hash=<hash>&limit=1`).

---

### `tests/test_cli_manifest.py` (test/unit, create — MFST-05)

**Analog:** `tests/test_ui_js_disabled_graceful_degradation.py` (parametrize pattern)

**Delta:** Two tests minimum: (1) Rich table output contains tool name column; (2) `--json` output parses as valid JSON with `data.tools` list. No filters to test (manifest has only `--search`).

---

### `tests/test_cli_health.py` (test/unit, create — HEALTH-02)

**Analog:** `tests/test_console_http_transport.py` `test_console_http_transport_serves_health_on_bound_port` (lines 98-106)

**Health assertion pattern** (test_console_http_transport.py lines 98-106):

```python
async def test_console_http_transport_serves_health_on_bound_port(console_server):
    port, _, _, _ = console_server
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"http://127.0.0.1:{port}/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["instance_identity"]["execution_log"]["id_match"] is True
```

**Delta:** CLI-layer test asserts Rich Panel present in output. Service group names appear in output (`mcp`, `watcher`). `--json` output parses as envelope. Use the `fake_read_api`-style mock (not a live server) for unit speed.

---

### `tests/test_cli_doctor.py` (test/unit, create — HEALTH-03)

**Analog:** `tests/test_console_http_transport.py` (integration test pattern with live server for the HTTP probe; `tmp_path` fixture for JSONL file probe)

**`tmp_path` JSONL file pattern** (execution_log.py lines 113 — how tests pass a temp path):

```python
log = ExecutionLog(log_path=tmp_path / "execs.jsonl")
```

**Exit code assertion pattern** (test_typer_entrypoint.py line 153):

```python
assert result.exit_code == 0
```

**Delta:** Six required test cases per RESEARCH.md: all-ok → exit 0; critical fail → exit 1; non-critical degraded → exit 0; server unreachable → exit 2 + correct message on stderr; JSONL parse error → exit 1; sidecar dir not writable → exit 1. JSONL probe tests use `tmp_path` to write a file with a malformed line and set `FORGE_EXECUTION_LOG_PATH` env via `runner.invoke(..., env={...})`.

---

## Shared Patterns

### Exit code propagation
**Source:** `tests/test_typer_entrypoint.py` lines 152-157 + RESEARCH.md lines 437-443
**Apply to:** All cli command modules + all test files
```python
# In command body:
raise typer.Exit(code=2)   # preferred — Typer-idiomatic; propagates through CliRunner

# In tests:
assert result.exit_code == 0   # or 1 or 2 per taxonomy
```

### LRN-05 credential-leak guard
**Source:** `forge_bridge/console/read_api.py` lines 200-205
**Apply to:** `forge_bridge/cli/client.py`, `forge_bridge/cli/doctor.py`
```python
# Use type(exc).__name__ — NEVER str(exc) or f"...{exc}..."
return {"status": "fail", "detail": type(exc).__name__}
```

### Logger-per-module
**Source:** `forge_bridge/console/handlers.py` line 35
**Apply to:** All `forge_bridge/cli/*.py` modules
```python
logger = logging.getLogger(__name__)
```

### `from __future__ import annotations`
**Source:** `forge_bridge/console/handlers.py` line 10, `forge_bridge/__main__.py` line 10
**Apply to:** All new `forge_bridge/cli/*.py` modules (project-wide convention)
```python
from __future__ import annotations
```

### Env-var-then-default config
**Source:** `forge_bridge/console/read_api.py` lines 99-107 + `forge_bridge/bridge.py` lines 32-37
**Apply to:** `forge_bridge/cli/client.py` port resolution
```python
# D-27 precedence: flag > env > default
port_str = os.environ.get("FORGE_CONSOLE_PORT", "9996")
try:
    port = int(port_str)
except ValueError:
    typer.echo(f"Invalid FORGE_CONSOLE_PORT: {port_str!r}", err=True)
    raise typer.Exit(code=1)
```

### CliRunner env isolation
**Source:** RESEARCH.md lines 494-497
**Apply to:** All `tests/test_cli_*.py` files
```python
runner = CliRunner()
result = runner.invoke(app, ['console', 'health'], env={'FORGE_CONSOLE_PORT': str(port)})
# Never mutate os.environ directly in tests
```

### `--json` guard as first statement
**Source:** RESEARCH.md lines 596-601 (anti-pattern description)
**Apply to:** All `forge_bridge/cli/*.py` command bodies
```python
def tools_cmd(as_json: bool = typer.Option(False, "--json"), ...):
    if as_json:
        # fetch + write raw envelope to sys.stdout.write() + return
        # NEVER instantiate Console() before this guard fires
        ...
        return
    # Only reach here for Rich rendering path
    console = make_console(no_color=no_color_flag)
```

---

## No Analog Found

No files are entirely without analog. The closest "greenfield" module is `forge_bridge/cli/render.py` — no existing codebase code uses Rich, so the render module has no direct analog. The planner should use RESEARCH.md lines 180-228 (Rich primitives: `Console`, `Table`, `Panel`, `Syntax`, `SQUARE` box, `make_console` factory) as the primary reference for this module.

---

## Metadata

**Analog search scope:**
- `forge_bridge/` (all `.py` files)
- `tests/` (all `.py` files)
- `pyproject.toml`

**Files scanned:**
- `forge_bridge/__main__.py`
- `forge_bridge/bridge.py`
- `forge_bridge/console/handlers.py`
- `forge_bridge/console/read_api.py`
- `forge_bridge/console/app.py`
- `forge_bridge/console/manifest_service.py`
- `forge_bridge/learning/execution_log.py`
- `tests/conftest.py`
- `tests/test_typer_entrypoint.py`
- `tests/test_console_http_transport.py`
- `tests/test_ui_js_disabled_graceful_degradation.py`
- `tests/test_console_stdio_cleanliness.py`
- `pyproject.toml`

**Rich usage search result:** Zero existing `from rich` / `import rich` hits in `forge_bridge/`. CLI render module is greenfield.

**Sync httpx usage search result:** Zero existing `httpx.Client` (sync) hits in `forge_bridge/`. All existing httpx usage is `httpx.AsyncClient`. CLI `client.py` introduces the first sync httpx usage in the codebase.

**Pattern extraction date:** 2026-04-24
