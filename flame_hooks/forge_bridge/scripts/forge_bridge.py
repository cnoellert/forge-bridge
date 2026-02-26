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
import http.server
import io
import json
import os
import sys
import threading
import traceback

# ========================================================================== #
# Configuration
# ========================================================================== #

BRIDGE_HOST = os.environ.get("FORGE_BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("FORGE_BRIDGE_PORT", "9999"))
BRIDGE_ENABLED = os.environ.get("FORGE_BRIDGE_ENABLED", "1") != "0"
EXEC_TIMEOUT = 60  # seconds to wait for result

# ========================================================================== #
# Shared state
# ========================================================================== #

_namespace = {}         # persistent execution namespace
_server = None          # HTTPServer instance
_bridge_active = False


def _log(msg):
    print(f"[FORGE BRIDGE] {msg}")


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

def _exec_on_main_thread(code):
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

    event.wait(timeout=EXEC_TIMEOUT)
    if not result_holder:
        return {
            "error": "Main-thread execution timeout — Flame may be busy.",
            "result": None, "stdout": "", "stderr": "",
            "traceback": None,
        }
    return result_holder

# ========================================================================== #
# HTTP Server
# ========================================================================== #

class BridgeHandler(http.server.BaseHTTPRequestHandler):
    """Handles GET / for web UI and POST /exec for code execution."""

    def do_GET(self):
        if self.path in ("/", "/index.html"):
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
        except Exception as e:
            self._send_json(400, {"error": f"Bad request: {e}"})
            return

        if not code.strip():
            self._send_json(200, {"result": ""})
            return

        if use_main:
            result = _exec_on_main_thread(code)
        else:
            result = _execute_code(code)

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
    try:
        _server = _ReusableHTTPServer(
            (BRIDGE_HOST, BRIDGE_PORT), BridgeHandler
        )
        _server.timeout = 1
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
            if _server:
                _server.shutdown()
            _bridge_active = False
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
