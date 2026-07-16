"""
FORGE Bridge — Remote Python execution for Flame.

Exposes an HTTP server that accepts Python code, queues it, and
executes it on Flame's main thread via QTimer.  Serves a web UI
at the root URL for interactive use.

Architecture:
    HTTP Server (daemon thread)  →  command queue  →  QTimer (main thread)
                                 ←  result dict    ←

The main-thread constraint is critical — Flame's Python API is only
safe to call from the thread that owns the Qt event loop.

Security:  Binds to 127.0.0.1 (localhost) by default.
           Set FORGE_BRIDGE_HOST=0.0.0.0 for LAN access.

Usage:
    1. Flame loads this hook automatically on startup.
    2. Navigate to http://<flame-host>:9999/ in a browser.
    3. Type Python code, press Shift+Enter to execute.
    4. The `flame` module is available in the execution namespace.

Based on LOGIK-PROJEKT (GPL-3.0) hook patterns.
"""

# ========================================================================== #
# Standard library only — Flame's bundled Python has no pip packages
# ========================================================================== #

import ast
import getpass
import http.server
import io
import json
import os
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request

# ========================================================================== #
# Configuration
# ========================================================================== #

BRIDGE_HOST = os.environ.get("FORGE_BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("FORGE_BRIDGE_PORT", "9999"))
BRIDGE_ENABLED = os.environ.get("FORGE_BRIDGE_ENABLED", "1") != "0"
BRIDGE_ANNOUNCE = os.environ.get("FORGE_BRIDGE_ANNOUNCE", "1") != "0"
# Long host operations can exceed one minute. Requests may override this value.
EXEC_TIMEOUT = int(os.environ.get("FORGE_BRIDGE_EXEC_TIMEOUT", "300"))

_REGISTRY_HTTP_URL = os.environ.get(
    "FORGE_SESSION_REGISTRY_HTTP_URL",
    "http://127.0.0.1:9991",
).rstrip("/")

_NONCE = os.urandom(4).hex()
_STARTED_AT = time.time()

# ========================================================================== #
# Shared state
# ========================================================================== #

_namespace = {}         # persistent execution namespace
_server = None          # HTTPServer instance
_bridge_active = False
_announce_started = False


def _log(msg):
    print(f"[FORGE BRIDGE] {msg}")


# ========================================================================== #
# Session registry announcer
#
# D-03: fail-soft — _http_post never raises; start_announce never blocks.
# D-04 (by omission): no deregister-on-shutdown; TTL reap is authoritative.
# ========================================================================== #

def _http_post(path, payload, timeout=2.0):
    """POST JSON to the session registry. Returns HTTP status or None on error."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        _REGISTRY_HTTP_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except (urllib.error.URLError, OSError):
        return None


def start_announce(descriptor):
    """Start background register+heartbeat daemon thread. Never raises."""
    global _announce_started
    if not BRIDGE_ANNOUNCE:
        return
    if _announce_started:
        return
    _announce_started = True
    instance_id = descriptor.get("instance_id", "")

    def _run():
        registered = False
        while True:
            if not registered:
                code = _http_post("/register", descriptor)
                registered = (code == 200)
            else:
                code = _http_post("/heartbeat", {"instance_id": instance_id})
                if code != 200:
                    registered = False  # re-register on next iteration (D-03)
            time.sleep(1.0)

    threading.Thread(
        target=_run,
        name="forge-announce-" + instance_id,
        daemon=True,
    ).start()


def _make_descriptor():
    """Return the 10-field SessionDescriptor dict for this Flame process.

    Rebuilds lazily on each call so `project` reflects the currently-open
    project (flame.project.current_project changes on project switch).
    No forge_core import — standalone file; see three-layer kill-switch / D-02.
    """
    project = None
    try:
        import flame as _fl
        project = str(_fl.project.current_project.name)
    except Exception:
        # Pitfall 6: project may not be loaded at app_initialized time, or
        # flame module may not be available in test/offline contexts.
        pass
    return {
        "instance_id": f"flame-{os.getpid()}-{_NONCE}",
        "dcc": "flame",
        "user": getpass.getuser(),
        "project": project,
        "shot": None,
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "port": BRIDGE_PORT,
        "started_at": _STARTED_AT,
        "version": "",
    }


# ========================================================================== #
# Main-thread code execution
# ========================================================================== #

def _init_namespace():
    """Initialize the execution namespace with useful defaults."""
    global _namespace
    _namespace = {
        "__builtins__": __builtins__,
        "__name__": "__forge_bridge__",
    }
    # Import flame if available
    try:
        import flame
        _namespace["flame"] = flame
    except ImportError:
        pass

    # Convenience imports
    for mod_name in ("os", "sys", "json", "pprint"):
        try:
            _namespace[mod_name] = __import__(mod_name)
        except ImportError:
            pass


def _execute_code(code):
    """Execute code in the persistent namespace.

    Uses the Python REPL pattern: if the last statement is an
    expression, its value is returned.  stdout/stderr are captured.

    Returns dict with keys: result, stdout, stderr, error, traceback
    """
    global _namespace
    if not _namespace:
        _init_namespace()

    result_data = {
        "result": None,
        "stdout": "",
        "stderr": "",
        "error": None,
        "traceback": None,
    }

    # Capture stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    cap_out = io.StringIO()
    cap_err = io.StringIO()
    sys.stdout = cap_out
    sys.stderr = cap_err

    try:
        tree = ast.parse(code)

        if not tree.body:
            result_data["result"] = ""
            return result_data

        # Split: all but last statement are exec'd,
        # last statement is eval'd if it's an expression
        last = tree.body[-1]

        if isinstance(last, ast.Expr):
            # Last node is an expression — exec preceding, eval last
            preceding = ast.Module(
                body=tree.body[:-1], type_ignores=[]
            )
            if preceding.body:
                exec(
                    compile(preceding, "<bridge>", "exec"),
                    _namespace,
                )

            value = eval(
                compile(
                    ast.Expression(body=last.value),
                    "<bridge>", "eval",
                ),
                _namespace,
            )
            if value is not None:
                result_data["result"] = repr(value)
        else:
            # All statements — just exec
            exec(compile(tree, "<bridge>", "exec"), _namespace)

    except Exception as e:
        result_data["error"] = f"{type(e).__name__}: {e}"
        result_data["traceback"] = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        result_data["stdout"] = cap_out.getvalue()
        result_data["stderr"] = cap_err.getvalue()

    return result_data


# ========================================================================== #
# Write detection — route mutations to main thread
# ========================================================================== #

def _exec_on_main_thread(code, timeout=None):
    """Execute code on Flame's main thread via schedule_idle_event.

    Returns result dict.  Blocks until execution completes or times out.
    """
    result_holder = {}
    event = threading.Event()

    def _run():
        r = _execute_code(code)
        result_holder.update(r)
        event.set()

    try:
        import flame as _fl
        _fl.schedule_idle_event(_run)
    except Exception as e:
        return {
            "error": f"Cannot schedule main-thread execution: {e}",
            "result": None, "stdout": "", "stderr": "",
            "traceback": None,
        }

    wait_s = EXEC_TIMEOUT if timeout is None else timeout
    event.wait(timeout=wait_s)
    if not result_holder:
        return {
            "error": (
                f"Main-thread execution timeout after {wait_s}s — "
                "Flame may be busy or the operation is still running."
            ),
            "result": None, "stdout": "", "stderr": "",
            "traceback": None,
        }
    return result_holder


def _execute_typed_host_load(params):
    """Execute one allowlisted typed load with Pipeline's Flame adapter."""
    _bootstrap_forge_runtime()
    from forge_core.shot_resources.host_load_dispatch import (
        execute_host_load_dispatch,
    )
    from forge_flame.plugin import FlamePlugin

    return execute_host_load_dispatch(params, plugins=[FlamePlugin()])


def _execute_typed_host_graph_read(params):
    """Execute one allowlisted read-only host-graph operation in Flame."""
    _bootstrap_forge_runtime()
    from forge_core.host_graph.routing import execute_host_graph_read_dispatch
    from forge_flame.plugin import FlamePlugin

    return execute_host_graph_read_dispatch(params, plugins=[FlamePlugin()])


def _bootstrap_forge_runtime():
    """Make an installed or source Forge runtime importable inside Flame."""
    repo_root = os.environ.get("FORGE_REPO_ROOT", "").strip()
    if repo_root:
        if not os.path.isdir(repo_root):
            raise RuntimeError(
                f"FORGE_REPO_ROOT is not a directory: {repo_root}"
            )
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)

    conda_site = os.environ.get("FORGE_CONDA_SITE", "").strip()
    if not conda_site:
        conda_site_file = os.path.join("/opt", "forge", "conda_site")
        try:
            with open(conda_site_file, encoding="utf-8") as handle:
                conda_site = handle.read().strip()
        except FileNotFoundError:
            if not repo_root:
                raise RuntimeError(
                    "Forge runtime is unavailable: set FORGE_REPO_ROOT or "
                    "install Forge so /opt/forge/conda_site exists."
                )

    if conda_site:
        if not os.path.isdir(conda_site):
            raise RuntimeError(
                f"FORGE_CONDA_SITE is not a directory: {conda_site}"
            )
        import site

        site.addsitedir(conda_site)


def _exec_typed_operation_on_main_thread(execute, params, timeout=None):
    """Run one typed operation on Flame's main thread."""
    wait_s = EXEC_TIMEOUT if timeout is None else timeout
    result_holder = {}
    event = threading.Event()

    def _run():
        try:
            result_holder["response"] = {"result": execute(params)}
        except Exception as exc:
            result_holder["response"] = {
                "result": None,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
        finally:
            event.set()

    try:
        import flame as _fl
        _fl.schedule_idle_event(_run)
    except Exception as exc:
        return {
            "result": None,
            "error": f"Cannot schedule main-thread execution: {exc}",
            "traceback": None,
        }

    event.wait(timeout=wait_s)
    if "response" not in result_holder:
        return {
            "result": None,
            "error": (
                f"Main-thread execution timeout after {wait_s}s — "
                "Flame may be busy or the operation is still running."
            ),
            "traceback": None,
        }
    return result_holder["response"]


def _exec_typed_host_load_on_main_thread(params, timeout=None):
    """Run a typed load on Flame's main thread and return its wire envelope."""
    return _exec_typed_operation_on_main_thread(
        _execute_typed_host_load,
        params,
        timeout=timeout,
    )


def _exec_typed_host_graph_read_on_main_thread(params, timeout=None):
    """Run a host-graph read on Flame's main thread."""
    return _exec_typed_operation_on_main_thread(
        _execute_typed_host_graph_read,
        params,
        timeout=timeout,
    )

# ========================================================================== #
# HTTP Server
# ========================================================================== #

class BridgeHandler(http.server.BaseHTTPRequestHandler):
    """Handles GET / for web UI and POST /exec for code execution."""

    def do_GET(self):
        if self.path == "/whoami":
            self._send_json(200, _make_descriptor())
        elif self.path in ("/", "/index.html"):
            self._send_html(200, _WEB_UI)
        elif self.path == "/status":
            self._send_json(200, {
                "status": "running",
                "flame_available": "flame" in _namespace,
                "namespace_keys": sorted(
                    k for k in _namespace
                    if not k.startswith("_")
                ),
            })
        elif self.path == "/favicon.ico":
            self.send_error(204)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/exec":
            self._handle_exec()
        elif self.path == "/":
            self._handle_operation()
        elif self.path == "/reset":
            _init_namespace()
            self._send_json(200, {"result": "Namespace reset"})
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _handle_exec(self):
        """Execute code — direct by default, main-thread via schedule_idle_event.

        Pass main_thread:true to execute on Flame's main thread
        (required for write operations like set_value, create, delete).
        """
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            code = data.get("code", "")
            use_main = data.get("main_thread", False)
            req_timeout = data.get("timeout")
        except Exception as e:
            self._send_json(400, {"error": f"Bad request: {e}"})
            return

        if not code.strip():
            self._send_json(200, {"result": ""})
            return

        if use_main:
            result = _exec_on_main_thread(code, timeout=req_timeout)
        else:
            result = _execute_code(code)

        self._send_json(200, result)

    def _handle_operation(self):
        """Dispatch the narrow typed-operation protocol used by Pipeline."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:
            self._send_json(400, {"error": f"Bad request: {exc}"})
            return

        if not isinstance(data, dict):
            self._send_json(400, {"error": "Request body must be an object"})
            return
        op_name = data.get("op")
        if op_name not in {"host_graph_read", "shot_resource_load"}:
            self._send_json(400, {"error": "Unknown operation"})
            return
        params = data.get("params")
        if not isinstance(params, dict):
            self._send_json(400, {"error": "params must be an object"})
            return

        timeout = data.get("timeout")
        if timeout is not None and not isinstance(timeout, (int, float)):
            self._send_json(400, {"error": "timeout must be numeric"})
            return
        if op_name == "shot_resource_load":
            result = _exec_typed_host_load_on_main_thread(
                params,
                timeout=timeout,
            )
        else:
            result = _exec_typed_host_graph_read_on_main_thread(
                params,
                timeout=timeout,
            )
        self._send_json(200, result)

    def _send_json(self, code, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, code, html):
        payload = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        """Suppress default stderr logging."""
        pass


class _ReusableHTTPServer(http.server.HTTPServer):
    """HTTPServer with SO_REUSEADDR to survive Flame restarts."""
    allow_reuse_address = True


def _server_loop():
    """Manual request loop — avoids serve_forever select() issues on macOS."""
    global _bridge_active
    while _bridge_active:
        try:
            _server.handle_request()
        except Exception:
            pass


def _start_server():
    """Start the HTTP server in a daemon thread."""
    global _server, _bridge_active
    if _bridge_active and _server is not None:
        _log("Bridge already running — skipping duplicate start")
        return

    try:
        srv = _ReusableHTTPServer((BRIDGE_HOST, BRIDGE_PORT), BridgeHandler)
        srv.timeout = 1
        _server = srv
        _bridge_active = True
        _log(f"Listening on http://{BRIDGE_HOST}:{BRIDGE_PORT}/")

        thread = threading.Thread(
            target=_server_loop,
            name="forge-bridge",
            daemon=True,
        )
        thread.start()
    except OSError as e:
        _log(f"Could not start server: {e}")
        if _server is None:
            _bridge_active = False


# ========================================================================== #
# Flame hooks
# ========================================================================== #

def app_initialized(project_name, *args, **kwargs):
    """Called when Flame starts — launch the bridge."""
    if not BRIDGE_ENABLED:
        _log("Disabled (FORGE_BRIDGE_ENABLED=0)")
        return

    try:
        _init_namespace()
        _start_server()
        start_announce(_make_descriptor())
        _log(f"Ready — project: {project_name}")
    except Exception as e:
        _log(f"Startup error (non-fatal): {e}")


def project_changed(project_name, *args, **kwargs):
    """Refresh flame reference when project changes."""
    try:
        import flame
        _namespace["flame"] = flame
    except ImportError:
        pass
    _log(f"Project changed: {project_name}")


# ========================================================================== #
# Custom action — show bridge status in FORGE menu
# ========================================================================== #

def get_main_menu_custom_ui_actions():
    """Register FORGE > Bridge Server menu items."""
    return [
        {
            "name": "FORGE",
            "actions": [
                {
                    "name": "Bridge Status",
                    "execute": _show_status,
                },
                {
                    "name": "Bridge Server",
                    "execute": _toggle_bridge,
                },
            ],
        }
    ]


def _show_status(selection):
    import flame
    host = BRIDGE_HOST if BRIDGE_HOST != "127.0.0.1" else "localhost"
    msg = (
        f"FORGE Bridge\n\n"
        f"Status: {'Running' if _bridge_active else 'Stopped'}\n"
        f"URL: http://{host}:{BRIDGE_PORT}/\n"
        f"Namespace: {len([k for k in _namespace if not k.startswith('_')])} objects\n"
        f"\nWrites use schedule_idle_event (main thread).\n"
        f"Pass main_thread:true in /exec requests."
    )
    flame.messages.show_in_dialog(
        title="FORGE Bridge",
        message=msg,
        type="info",
        buttons=["OK"],
    )


def _toggle_bridge(selection):
    """Start the bridge if stopped, stop it if running. Show result."""
    import flame
    global _server, _bridge_active

    host = BRIDGE_HOST if BRIDGE_HOST != "127.0.0.1" else "localhost"
    url = f"http://{host}:{BRIDGE_PORT}/"

    if _bridge_active:
        # Running — confirm stop
        reply = flame.messages.show_in_dialog(
            title="FORGE Bridge",
            message=f"Bridge is running at {url}\n\nStop it?",
            type="question",
            buttons=["Stop", "Cancel"],
        )
        if reply != "Stop":
            return
        try:
            _bridge_active = False
            if _server:
                _server.server_close()
            _log("Bridge stopped via toggle")
            flame.messages.show_in_dialog(
                title="FORGE Bridge",
                message="Bridge stopped.",
                type="info",
                buttons=["OK"],
            )
        except Exception as e:
            flame.messages.show_in_dialog(
                title="FORGE Bridge",
                message=f"Error stopping bridge:\n{e}",
                type="error",
                buttons=["OK"],
            )
    else:
        # Stopped — confirm start
        reply = flame.messages.show_in_dialog(
            title="FORGE Bridge",
            message=f"Bridge is stopped.\n\nStart it at {url}?",
            type="question",
            buttons=["Start", "Cancel"],
        )
        if reply != "Start":
            return
        try:
            _init_namespace()
            _start_server()
            _log("Bridge started via toggle")
            flame.messages.show_in_dialog(
                title="FORGE Bridge",
                message=f"Bridge started.\n\nURL: {url}",
                type="info",
                buttons=["OK"],
            )
        except Exception as e:
            flame.messages.show_in_dialog(
                title="FORGE Bridge",
                message=f"Error starting bridge:\n{e}",
                type="error",
                buttons=["OK"],
            )


# ========================================================================== #
# PR39 — Contextual command entry (right-click; calls run_command_from_flame)
# ========================================================================== #


def _forge_contextual_menu_groups():
    return (
        {
            "name": "FORGE",
            "actions": (
                {
                    "name": "forge_run_command",
                    "caption": "Forge: Run Command…",
                },
            ),
        },
    )


def get_custom_ui_actions():
    if not BRIDGE_ENABLED:
        return ()
    return _forge_contextual_menu_groups()


def get_media_panel_custom_ui_actions():
    if not BRIDGE_ENABLED:
        return ()
    return _forge_contextual_menu_groups()


def _forge_prompt_for_command():
    try:
        try:
            from PySide2 import QtWidgets
        except Exception:
            from PySide6 import QtWidgets

        # Label spells out the input shape — chain engine expects natural verb +
        # noun + optional key=value kwargs, NOT exact tool names. Typing
        # "forge_scan_roles" tokenizes against all tools and triggers
        # tool_selection_ambiguous; "scan roles" lands cleanly.
        text, ok = QtWidgets.QInputDialog.getText(
            None,
            "Forge",
            "Command (verb + noun, e.g. 'list projects' or 'list versions project_id=…'):",
        )

        if ok and text and text.strip():
            return text

        return None
    except Exception:
        try:
            import flame
            flame.messages.show_in_dialog(
                title="Forge",
                message="Qt not available. Use terminal or bridge instead.",
                type="info",
                buttons=["OK"],
            )
        except Exception:
            pass
        return None


def _forge_extract_context(info):
    context = {}

    try:
        import flame

        project = getattr(flame.projects, "current_project", None)
        if project:
            pid = getattr(project, "id", None)
            if isinstance(pid, str) and pid.strip():
                context["project_id"] = pid.strip()
    except Exception:
        pass

    return context


def _forge_summarize(value, limit=120):
    """Best-effort one-line preview of a chain step's result for dialog display."""
    if value is None:
        return ""
    if isinstance(value, dict):
        if "count" in value:
            return f"count={value['count']}"
        keys = list(value.keys())
        if keys:
            preview = ", ".join(keys[:5])
            if len(keys) > 5:
                preview += f", …+{len(keys) - 5}"
            return f"keys: {preview}"
        return ""
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    s = str(value)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _forge_format_result(result):
    """Render a PR31 envelope into a multi-line dialog message.

    Surfaces what the artist actually needs to act on:
      - error.message and original_error.message (the *human* explanation)
      - candidates list for tool_selection_ambiguous (what to try instead)
      - per-step preview for success
      - request_id (short) for log lookup when something is wrong
    """
    if not isinstance(result, dict):
        return f"Unexpected response: {result!r}"

    status = result.get("status", "unknown")
    rid = result.get("request_id", "") or ""
    rid_short = rid[:8] if isinstance(rid, str) else ""

    if status == "success":
        chain = result.get("chain") or []
        lines = [f"Success — {len(chain)} step(s)"]
        for i, item in enumerate(chain):
            if not isinstance(item, dict):
                continue
            step = item.get("step", "")
            preview = _forge_summarize(item.get("result"))
            lines.append(f"  {i + 1}. {step}")
            if preview:
                lines.append(f"     → {preview}")
        if rid_short:
            lines.append("")
            lines.append(f"request_id: {rid_short}")
        return "\n".join(lines)

    err = result.get("error") or {}
    if not isinstance(err, dict):
        return f"Error: {err}"

    code = err.get("code", "UNKNOWN")
    msg = err.get("message") or ""
    lines = [f"Error: {code}"]
    if msg:
        lines.append("")
        lines.append(msg)

    orig = err.get("original_error")
    if isinstance(orig, dict):
        orig_type = orig.get("type")
        orig_msg = orig.get("message")
        if orig_msg:
            lines.append("")
            lines.append(f"Cause ({orig_type}):" if orig_type else "Cause:")
            lines.append(orig_msg)
        candidates = orig.get("candidates")
        if isinstance(candidates, list) and candidates:
            shown = candidates[:5]
            lines.append("")
            lines.append("Did you mean (try a more specific verb + noun):")
            for c in shown:
                lines.append(f"  • {c}")
            if len(candidates) > 5:
                lines.append(f"  …and {len(candidates) - 5} more")

    if rid_short:
        lines.append("")
        lines.append(f"request_id: {rid_short}")
    return "\n".join(lines)


def _forge_show_result(result):
    try:
        import flame
        flame.messages.show_in_dialog(
            title="Forge",
            message=_forge_format_result(result),
            type="info",
            buttons=["OK"],
        )
    except Exception:
        print("Forge result:", result)


# PR42 — hook posts directly to /api/v1/exec via stdlib HTTP; no forge_bridge
# import required (the package isn't necessarily installed in Flame's interpreter).
# Mirrors forge_bridge/flame/integration.py:run_command_from_flame.

_FORGE_HTTP_TIMEOUT_S = 65.0
_FORGE_DEFAULT_BASE_URL = "http://127.0.0.1:9996"


def _forge_envelope(code, message):
    # Synthesizes a PR31-shaped envelope for failures that never reach the
    # daemon. Engine-originated envelopes pass through unchanged via json.loads.
    import uuid
    return {
        "status": "error",
        "request_id": str(uuid.uuid4()),
        "chain": [],
        "error": {
            "code": code,
            "message": message,
            "step_index": None,
            "original_error": None,
        },
    }


def _forge_post_exec(text, context=None):
    import json
    import os
    import socket
    from urllib import error as _url_error
    from urllib import request as _url_request

    command = (text or "").strip()

    parts = []
    if command:
        parts.append(command)
    if context:
        for k, v in context.items():
            if (
                isinstance(k, str)
                and k.strip()
                and isinstance(v, str)
                and v.strip()
            ):
                parts.append(f"{k.strip()}={v.strip()}")
    merged = " ".join(parts)

    base_url = os.getenv("FORGE_CONSOLE_URL", _FORGE_DEFAULT_BASE_URL)
    url = f"{base_url}/api/v1/exec"
    payload = json.dumps({"text": merged}).encode("utf-8")

    req = _url_request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with _url_request.urlopen(req, timeout=_FORGE_HTTP_TIMEOUT_S) as resp:
            body = resp.read()

        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return _forge_envelope(
                "INVALID_JSON", "Invalid JSON response from daemon"
            )

    # HTTPError is a URLError subclass — must come first.
    except _url_error.HTTPError as e:
        return _forge_envelope("HTTP_STATUS", f"HTTP {e.code}")

    except (_url_error.URLError, socket.timeout, TimeoutError) as e:
        return _forge_envelope("TRANSPORT_ERROR", str(e))

    # Broad catch is intentional. Flame runs this on the UI thread, and
    # uncaught exceptions can destabilize the host application.
    except Exception as e:  # noqa: BLE001
        return _forge_envelope("UNKNOWN_ERROR", str(e))


def custom_ui_action(info, user_data):
    if info.get("name") != "forge_run_command":
        return

    command = _forge_prompt_for_command()
    if not command or not command.strip():
        return

    context = _forge_extract_context(info)
    result = _forge_post_exec(command, context)
    _forge_show_result(result)


# ========================================================================== #
# Web UI
# ========================================================================== #

_WEB_UI = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>FORGE Bridge</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', monospace;
    background: #1a1d23;
    color: #c8ccd4;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
header {
    background: #21252b;
    border-bottom: 1px solid #333;
    padding: 8px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
}
header h1 {
    font-size: 14px;
    color: #E8B332;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.status {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 8px;
    background: #2a3a2a;
    color: #5a5;
}
.status.error { background: #3a2a2a; color: #a55; }
.toolbar {
    margin-left: auto;
    display: flex;
    gap: 8px;
}
.toolbar button {
    background: #3a3f4f;
    color: #aaa;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 11px;
    font-family: inherit;
    cursor: pointer;
}
.toolbar button:hover { background: #4a5060; color: #ddd; }

#output-panel {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
}
.entry { margin-bottom: 12px; }
.entry .cmd {
    color: #888;
    font-size: 11px;
    margin-bottom: 2px;
}
.entry .cmd::before { content: '>>> '; color: #E8B332; }
.entry .result { color: #abb2bf; }
.entry .stdout { color: #98c379; }
.entry .stderr { color: #e5c07b; }
.entry .error { color: #e06c75; }

#input-panel {
    background: #21252b;
    border-top: 1px solid #333;
    padding: 8px 16px;
    display: flex;
    gap: 8px;
    flex-shrink: 0;
    align-items: flex-end;
}
#input-panel .prompt {
    color: #E8B332;
    font-size: 14px;
    line-height: 32px;
    user-select: none;
}
#code-input {
    flex: 1;
    background: #1a1d23;
    color: #c8ccd4;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 6px 10px;
    font-family: inherit;
    font-size: 13px;
    resize: none;
    min-height: 32px;
    max-height: 200px;
    line-height: 1.4;
    outline: none;
}
#code-input:focus { border-color: #E8B332; }
#exec-btn {
    background: #3a6b30;
    color: #ddd;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-family: inherit;
    font-size: 12px;
    cursor: pointer;
    height: 32px;
    white-space: nowrap;
}
#exec-btn:hover { background: #4a8c3f; }
#exec-btn:disabled { background: #2a2d36; color: #666; cursor: default; }
.hint {
    font-size: 10px;
    color: #555;
    padding: 4px 16px 6px;
    background: #21252b;
    flex-shrink: 0;
}
</style>
</head>
<body>
<header>
    <h1>FORGE BRIDGE</h1>
    <span id="status" class="status">connecting...</span>
    <div class="toolbar">
        <button onclick="resetNamespace()">Reset NS</button>
        <button onclick="clearOutput()">Clear</button>
    </div>
</header>
<div id="output-panel"></div>
<div id="input-panel">
    <span class="prompt">&gt;&gt;&gt;</span>
    <textarea id="code-input" rows="1"
        placeholder="Python code... (Shift+Enter to execute)"
        autofocus></textarea>
    <button id="exec-btn" onclick="execute()">Run</button>
</div>
<div class="hint">Shift+Enter to execute · Up/Down for history · `flame` module available</div>

<script>
const BASE = window.location.origin;
const output = document.getElementById('output-panel');
const input = document.getElementById('code-input');
const execBtn = document.getElementById('exec-btn');
const statusEl = document.getElementById('status');

let history = [];
let historyIdx = -1;
let executing = false;

// Auto-resize textarea
input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 200) + 'px';
});

// Keyboard shortcuts
input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.shiftKey) {
        e.preventDefault();
        execute();
    } else if (e.key === 'ArrowUp' && input.selectionStart === 0) {
        e.preventDefault();
        navigateHistory(-1);
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        navigateHistory(1);
    }
});

function navigateHistory(dir) {
    if (history.length === 0) return;
    historyIdx = Math.max(-1, Math.min(history.length - 1, historyIdx + dir));
    if (historyIdx === -1) {
        input.value = '';
    } else {
        input.value = history[history.length - 1 - historyIdx];
    }
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 200) + 'px';
}

async function execute() {
    const code = input.value.trim();
    if (!code || executing) return;

    executing = true;
    execBtn.disabled = true;
    execBtn.textContent = '...';

    history.push(code);
    historyIdx = -1;

    // Show command
    const entry = document.createElement('div');
    entry.className = 'entry';

    const cmdEl = document.createElement('div');
    cmdEl.className = 'cmd';
    cmdEl.textContent = code.includes('\n')
        ? code.split('\n')[0] + '  (+' + (code.split('\n').length - 1) + ' lines)'
        : code;
    entry.appendChild(cmdEl);

    try {
        const resp = await fetch(BASE + '/exec', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
        });
        const data = await resp.json();

        if (data.stdout) {
            const el = document.createElement('div');
            el.className = 'stdout';
            el.textContent = data.stdout;
            entry.appendChild(el);
        }
        if (data.stderr) {
            const el = document.createElement('div');
            el.className = 'stderr';
            el.textContent = data.stderr;
            entry.appendChild(el);
        }
        if (data.error) {
            const el = document.createElement('div');
            el.className = 'error';
            el.textContent = data.traceback || data.error;
            entry.appendChild(el);
        }
        if (data.result) {
            const el = document.createElement('div');
            el.className = 'result';
            el.textContent = data.result;
            entry.appendChild(el);
        }

        statusEl.textContent = 'connected';
        statusEl.className = 'status';
    } catch (err) {
        const el = document.createElement('div');
        el.className = 'error';
        el.textContent = 'Connection error: ' + err.message;
        entry.appendChild(el);
        statusEl.textContent = 'disconnected';
        statusEl.className = 'status error';
    }

    output.appendChild(entry);
    output.scrollTop = output.scrollHeight;

    input.value = '';
    input.style.height = '32px';
    input.focus();
    executing = false;
    execBtn.disabled = false;
    execBtn.textContent = 'Run';
}

function clearOutput() {
    output.innerHTML = '';
}

async function resetNamespace() {
    try {
        await fetch(BASE + '/reset', { method: 'POST' });
        const entry = document.createElement('div');
        entry.className = 'entry';
        const el = document.createElement('div');
        el.className = 'stderr';
        el.textContent = '--- namespace reset ---';
        entry.appendChild(el);
        output.appendChild(entry);
    } catch (err) {}
}

// Check connection on load
async function checkStatus() {
    try {
        const resp = await fetch(BASE + '/status');
        const data = await resp.json();
        statusEl.textContent = data.flame_available
            ? 'connected (flame)' : 'connected (no flame)';
        statusEl.className = 'status';
    } catch {
        statusEl.textContent = 'disconnected';
        statusEl.className = 'status error';
    }
}
checkStatus();
setInterval(checkStatus, 10000);

// Welcome message
const welcome = document.createElement('div');
welcome.className = 'entry';
welcome.innerHTML =
    '<div class="result" style="color:#E8B332">FORGE Bridge — remote Python execution for Flame\n'
    + 'Shift+Enter to execute · Up/Down for history\n'
    + 'The `flame` module is available in the namespace.</div>';
output.appendChild(welcome);
</script>
</body>
</html>
"""

# Compatibility with builds expecting camelCase hooks
getCustomUIActions = get_custom_ui_actions
customUIAction = custom_ui_action
