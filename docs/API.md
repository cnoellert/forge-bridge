# forge-bridge HTTP API Reference

This document describes the HTTP API exposed by the Flame-side bridge hook (`forge_bridge.py`).

The bridge runs inside Flame as an HTTP server. All requests are to `http://<host>:<port>/` (default: `http://127.0.0.1:9999/`).

---

## Endpoints

### GET /

Returns the interactive web UI — a browser-based Python REPL connected to Flame's runtime. Useful for exploration and debugging.

---

### GET /status

Returns the current state of the bridge.

**Response:**
```json
{
  "status": "running",
  "flame_available": true,
  "namespace_keys": ["flame", "json", "os", "pprint", "sys"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always "running" if bridge is responding |
| `flame_available` | bool | Whether the `flame` module loaded successfully |
| `namespace_keys` | list[string] | Non-private names in the current execution namespace |

---

### POST /exec

Execute Python code inside Flame's runtime and return the result.

**Request:**
```json
{
  "code": "print(flame.project.current_project.name)",
  "main_thread": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | Yes | Python source code to execute |
| `main_thread` | bool | No | If true, execute on Flame's Qt main thread (default: false) |

**When to use `main_thread: true`:**

Flame's Python API is only safe to call from the Qt main thread. Use `main_thread: true` for any operation that modifies Flame state:
- `set_value()` on any attribute
- Creating clips, segments, batch groups, etc.
- Deleting objects
- Moving or renaming objects

Read-only operations (inspecting properties, listing objects) are generally safe without `main_thread: true`, but when in doubt, use it.

**Response:**
```json
{
  "result": "'MyProject'",
  "stdout": "",
  "stderr": "",
  "error": null,
  "traceback": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `result` | string\|null | `repr()` of the last expression's value, or null |
| `stdout` | string | Captured stdout |
| `stderr` | string | Captured stderr |
| `error` | string\|null | Error type and message if execution failed |
| `traceback` | string\|null | Full traceback if execution failed |

**Expression vs statement behavior:**

The bridge uses Python's REPL pattern. If the last statement in the code is an expression, its value is captured as `result`. If the last statement is not an expression (e.g. an assignment, a for loop), `result` is null and any output should be captured via `print()` to `stdout`.

```python
# result will be the repr of the project name
"flame.project.current_project.name"

# result will be null; name will be in stdout
"print(flame.project.current_project.name)"

# result will be null; use print() to get the list
"for lib in flame.project.current_project.libraries: print(lib.name)"
```

**Error response:**
```json
{
  "result": null,
  "stdout": "",
  "stderr": "",
  "error": "AttributeError: 'NoneType' object has no attribute 'name'",
  "traceback": "Traceback (most recent call last):\n  ...\nAttributeError: ..."
}
```

---

### POST /reset

Resets the execution namespace to its initial state — clears all variables except the built-ins and standard imports (`flame`, `os`, `sys`, `json`, `pprint`).

**Request:** No body required.

**Response:**
```json
{
  "result": "Namespace reset"
}
```

---

## Execution Namespace

The bridge maintains a **persistent namespace** across requests. Variables assigned in one request are available in subsequent requests until reset.

The initial namespace contains:
- `flame` — the Flame Python API module
- `os` — standard library
- `sys` — standard library
- `json` — standard library
- `pprint` — standard library

Variables persist until either:
1. `POST /reset` is called explicitly
2. Flame restarts

This means multi-step operations can be written as separate requests:

```python
# Request 1: find a library
lib = [l for l in flame.project.current_project.libraries if l.name == 'shots'][0]

# Request 2: use it (lib is still in namespace)
print([r.name for r in lib.sequences])
```

---

## CORS

The bridge allows CORS from any origin:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

This allows the web UI to connect and allows any local tool to call the bridge from a browser context.

---

## Configuration

The bridge is configured via environment variables set before Flame starts:

| Variable | Default | Description |
|----------|---------|-------------|
| `FORGE_BRIDGE_HOST` | `127.0.0.1` | Bind address. Use `0.0.0.0` for LAN access. |
| `FORGE_BRIDGE_PORT` | `9999` | Listen port |
| `FORGE_BRIDGE_ENABLED` | `1` | Set to `0` to disable entirely |

---

## Flame Menu Integration

The bridge adds menu items to the FORGE menu in Flame:

- **FORGE > Bridge Status** — shows current status, URL, and namespace size in a dialog
- **FORGE > Bridge Server** — toggle to start/stop the bridge server

---

## Error Handling

### Bridge unreachable

If the bridge is not running, all requests will fail with a connection error. Check that Flame is running and the bridge hook is loaded.

### Execution timeout

By default, execution requests timeout after 60 seconds. If a main-thread operation takes longer (e.g. a render), increase the timeout via `FORGE_BRIDGE_TIMEOUT` or the `--bridge-timeout` flag on the MCP server.

### Flame not available

If `flame_available` is `false` in `/status`, the `flame` module failed to import. This should not happen if the bridge is running inside Flame. It can happen if the bridge is started outside of Flame for testing.

---

## Security Notes

The bridge executes arbitrary Python code with full access to Flame's API and the local filesystem. It is designed for trusted local use only.

**Do not bind to `0.0.0.0` (LAN) unless you understand the implications.** Anyone on the network with access to the port can execute arbitrary code on the Flame machine.

Authentication is planned but not yet implemented. See [ARCHITECTURE.md](ARCHITECTURE.md) for the current thinking.
