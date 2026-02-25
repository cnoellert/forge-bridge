"""
FORGE Bridge — Flame Python hook.

Two services in one hook:

  1. HTTP bridge (port 9999) — unchanged
     Accepts Python code, executes on Flame's main thread, returns result.
     Used by MCP server for Flame-native operations (list libraries, etc.)

  2. forge-bridge endpoint — NEW
     WebSocket client connecting to forge-bridge server.
     Publishes Flame events (segments created/renamed, versions published)
     and applies incoming pipeline events back to Flame.

The HTTP bridge and the endpoint are independent — if forge-bridge server
is unreachable, only the endpoint is affected. The HTTP bridge keeps working.

Installation:
    Copy this file to:
    ~/.flame/python/shared/hooks/forge_bridge.py

    Or link it from the flame_hooks directory in this repo.

Configuration (environment variables):
    FORGE_BRIDGE_HOST     HTTP bridge bind host  (default: 127.0.0.1)
    FORGE_BRIDGE_PORT     HTTP bridge port       (default: 9999)
    FORGE_BRIDGE_URL      forge-bridge WebSocket (default: ws://127.0.0.1:9998)
    FORGE_BRIDGE_ENABLED  Set to 0 to disable    (default: 1)
"""

# Standard library only for the HTTP bridge section — Flame's Python
# environment is constrained.  The forge-bridge endpoint imports are
# guarded so the hook still loads if forge_bridge package isn't installed.

import ast
import http.server
import io
import json
import os
import socket
import sys
import threading
import traceback

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

BRIDGE_HOST    = os.environ.get("FORGE_BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT    = int(os.environ.get("FORGE_BRIDGE_PORT", "9999"))
BRIDGE_URL     = os.environ.get("FORGE_BRIDGE_URL", "ws://127.0.0.1:9998")
BRIDGE_ENABLED = os.environ.get("FORGE_BRIDGE_ENABLED", "1") != "0"
EXEC_TIMEOUT   = 60

# ─────────────────────────────────────────────────────────────
# Shared state
# ─────────────────────────────────────────────────────────────

_namespace      = {}
_http_server    = None
_bridge_active  = False
_endpoint       = None   # FlameEndpoint instance, set on project open


def _log(msg: str) -> None:
    print(f"[FORGE BRIDGE] {msg}")


# ─────────────────────────────────────────────────────────────
# HTTP bridge (unchanged from original)
# ─────────────────────────────────────────────────────────────

import queue as _queue
_cmd_queue   = _queue.Queue()
_result_store = {}
_result_lock  = threading.Lock()


class _BridgeHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def do_POST(self):
        if self.path != "/exec":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        code        = data.get("code", "")
        main_thread = data.get("main_thread", False)

        import uuid as _uuid
        cmd_id = str(_uuid.uuid4())
        event  = threading.Event()
        with _result_lock:
            _result_store[cmd_id] = {"event": event, "result": None}

        _cmd_queue.put({"id": cmd_id, "code": code, "event": event})

        event.wait(timeout=EXEC_TIMEOUT)

        with _result_lock:
            result = _result_store.pop(cmd_id, {}).get("result") or {}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        html = b"""<!DOCTYPE html><html><body>
<h2>FORGE Bridge</h2>
<textarea id="code" rows="10" cols="80" placeholder="Enter Python code..."></textarea><br>
<button onclick="run()">Run</button>
<pre id="out"></pre>
<script>
async function run() {
  const code = document.getElementById('code').value;
  const r = await fetch('/exec', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({code})});
  const d = await r.json();
  document.getElementById('out').textContent =
    d.stdout || d.stderr || d.error || '(no output)';
}
</script></body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html)


def _run_http_server():
    global _http_server, _bridge_active
    try:
        _http_server = http.server.HTTPServer((BRIDGE_HOST, BRIDGE_PORT), _BridgeHandler)
        _bridge_active = True
        _log(f"HTTP bridge listening on http://{BRIDGE_HOST}:{BRIDGE_PORT}")
        _http_server.serve_forever()
    except Exception as e:
        _log(f"HTTP bridge failed to start: {e}")
        _bridge_active = False


def _execute_pending():
    """Process queued commands on Flame's main thread. Called by QTimer."""
    while not _cmd_queue.empty():
        try:
            item = _cmd_queue.get_nowait()
        except Exception:
            break

        cmd_id = item["id"]
        code   = item["code"]
        event  = item["event"]

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        result_val = None
        error_msg  = None
        tb_str     = None

        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout_buf, stderr_buf

        try:
            tree = ast.parse(code)
            # If last statement is an expression, capture its value
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                last = ast.Expression(body=tree.body.pop().value)
                exec(compile(tree, "<forge>", "exec"), _namespace)
                result_val = eval(compile(last, "<forge>", "eval"), _namespace)
            else:
                exec(compile(tree, "<forge>", "exec"), _namespace)
        except Exception as e:
            error_msg = str(e)
            tb_str    = traceback.format_exc()
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

        with _result_lock:
            if cmd_id in _result_store:
                _result_store[cmd_id]["result"] = {
                    "stdout":    stdout_buf.getvalue(),
                    "stderr":    stderr_buf.getvalue(),
                    "result":    result_val,
                    "error":     error_msg,
                    "traceback": tb_str,
                }
        event.set()


# ─────────────────────────────────────────────────────────────
# forge-bridge endpoint integration
# ─────────────────────────────────────────────────────────────

def _start_endpoint() -> None:
    """Start the forge-bridge endpoint in a background thread.

    Wrapped in try/except so a missing forge_bridge package or
    unreachable server doesn't prevent the hook from loading.
    """
    global _endpoint

    def _connect():
        global _endpoint
        try:
            # Add forge_bridge to path if running from the repo
            repo_path = os.environ.get("FORGE_BRIDGE_REPO")
            if repo_path and repo_path not in sys.path:
                sys.path.insert(0, repo_path)

            from forge_bridge.flame.endpoint import FlameEndpoint
            _endpoint = FlameEndpoint.start(server_url=BRIDGE_URL)
            _log(f"forge-bridge endpoint {'connected' if _endpoint.is_connected else 'offline'}")
        except ImportError:
            _log(
                "forge_bridge package not found. "
                "Pipeline sync unavailable. Set FORGE_BRIDGE_REPO to enable."
            )
        except Exception as e:
            _log(f"forge-bridge endpoint error: {e}")

    thread = threading.Thread(target=_connect, name="forge-endpoint", daemon=True)
    thread.start()


# ─────────────────────────────────────────────────────────────
# Flame hook callbacks
# ─────────────────────────────────────────────────────────────

def app_initialized(project_name: str) -> None:
    """Called once when Flame initializes."""
    if not BRIDGE_ENABLED:
        _log("Bridge disabled (FORGE_BRIDGE_ENABLED=0)")
        return

    # Start HTTP bridge
    t = threading.Thread(target=_run_http_server, name="forge-http", daemon=True)
    t.start()

    # QTimer for main-thread command execution
    try:
        from PySide2.QtCore import QTimer
        _timer = QTimer()
        _timer.timeout.connect(_execute_pending)
        _timer.start(100)   # 10hz polling
        _log("QTimer registered for main-thread execution")
    except ImportError:
        _log("PySide2 not available — main-thread execution disabled")

    # Start forge-bridge endpoint
    _start_endpoint()


def project_changed_dict(info: dict) -> None:
    """Called when the Flame project changes (open/switch)."""
    global _endpoint

    project_name = info.get("project_name", "")
    _log(f"Project changed: {project_name!r}")

    if _endpoint and _endpoint.is_connected:
        # Minimal stub — real Flame passes a project object
        class _FakeProject:
            project_name = info.get("project_name", "unknown")
            nickname     = info.get("nickname",     "")
        _endpoint.on_project_opened(_FakeProject())


def segment_created(segment, *args) -> None:
    """Called when a segment is created on the Flame timeline."""
    if _endpoint and _endpoint.is_connected:
        sequence = args[0] if args else None
        _endpoint.on_segment_created(segment, sequence)


def segment_deleted(segment, *args) -> None:
    """Called when a segment is deleted from the Flame timeline."""
    if _endpoint and _endpoint.is_connected:
        _endpoint.on_segment_deleted(segment)


def batch_render_completed(info: dict) -> None:
    """Called when a Flame batch render completes.

    info dict typically contains: clip_name, path, version, shot_name
    """
    if not _endpoint or not _endpoint.is_connected:
        return

    shot_name = info.get("shot_name", info.get("clip_name", "unknown"))
    version   = info.get("version", 1)
    path      = info.get("path")
    _log(f"Batch render complete: {shot_name!r} v{version:03d}")

    _endpoint.on_version_published(
        clip=info,
        shot_name=shot_name,
        version_number=version,
        media_path=path,
    )


# ─────────────────────────────────────────────────────────────
# Flame hook registration
# ─────────────────────────────────────────────────────────────

def get_media_panel_custom_ui_actions():
    """Not used — required stub to prevent Flame errors."""
    return []


def get_main_menu_custom_ui_actions():
    """Add forge-bridge status to Flame's main menu."""
    actions = []
    if not BRIDGE_ENABLED:
        return actions

    def show_status(selection):
        lines = [
            f"HTTP bridge: {'active' if _bridge_active else 'inactive'} → port {BRIDGE_PORT}",
        ]
        if _endpoint:
            s = _endpoint.status()
            lines.append(f"forge-bridge: {'connected' if s['connected'] else 'offline'}")
            if s["project_id"]:
                lines.append(f"Project: {s['project_id']}")
                lines.append(f"Shots tracked: {s['known_shots']}")
        else:
            lines.append("forge-bridge: not started")

        import flame
        flame.messages.show_in_console("\n".join(lines), duration=5)

    actions.append({
        "name":     "FORGE Bridge — Status",
        "execute":  show_status,
        "minimumVersion": "2025",
    })

    return actions
