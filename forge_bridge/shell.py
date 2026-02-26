"""
forge-bridge interactive shell.

Connects to a running forge-bridge server (or spins up an in-memory
one if no server is reachable) and drops you into a Python REPL with
a live client pre-connected.

Usage:
    python -m forge_bridge.shell                    # auto-connect or start in-memory
    python -m forge_bridge.shell --url ws://host:9998
    python -m forge_bridge.shell --inmemory         # always use in-memory server

Inside the shell, you have:
    client      AsyncClient connected to the server
    p           protocol module (all message constructors)
    req(msg)    shorthand for await client.request(msg)
    store       MemoryStore (if in-memory mode)
    show(x)     pretty-print any dict/list

Example session:
    >>> req(p.role_list())
    >>> req(p.project_create("Epic Sixty", "EP60"))
    >>> req(p.entity_create("shot", project_id, {"sequence_id": seq_id}, name="EP60_010"))
"""

from __future__ import annotations

import argparse
import asyncio
import code
import inspect
import json
import os
import sys
import threading
from typing import Any


# ─────────────────────────────────────────────────────────────
# Pretty printer
# ─────────────────────────────────────────────────────────────

def show(obj: Any, indent: int = 2) -> None:
    """Pretty-print a dict, list, or any JSON-serialisable object."""
    print(json.dumps(obj, indent=indent, default=str))


# ─────────────────────────────────────────────────────────────
# In-memory server bootstrap
# ─────────────────────────────────────────────────────────────

def _start_memory_server(port: int = 19876) -> str:
    """Spin up an in-memory forge-bridge server. Returns the ws:// URL."""
    from forge_bridge.store.memory import patch_for_memory
    patch_for_memory()

    from forge_bridge.core.registry import Registry
    from forge_bridge.server.app import ForgeServer
    from forge_bridge.server.connections import ConnectionManager
    from forge_bridge.server.router import Router

    registry = Registry.default()
    ready    = threading.Event()

    def _run():
        import asyncio
        from websockets.asyncio.server import serve

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _start():
            connections = ConnectionManager()
            router      = Router(connections, registry)
            server      = ForgeServer(host="127.0.0.1", port=port)
            server.connections = connections
            server.registry    = registry
            server.router      = router
            server._server     = await serve(
                server._connection_handler, "127.0.0.1", port
            )
            ready.set()
            await asyncio.Event().wait()

        loop.run_until_complete(_start())

    t = threading.Thread(target=_run, daemon=True, name="forge-shell-server")
    t.start()
    assert ready.wait(timeout=10), "Shell server failed to start"
    return f"ws://127.0.0.1:{port}"


# ─────────────────────────────────────────────────────────────
# Async helpers for the sync REPL
# ─────────────────────────────────────────────────────────────

_loop: asyncio.AbstractEventLoop | None = None
_client = None


def _run_async(coro):
    """Submit a coroutine to the background event loop and block for result."""
    if _loop is None:
        raise RuntimeError("No event loop running")
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=30)


def req(msg, timeout: float = 30.0):
    """Send a request to forge-bridge and return the result dict.

    Usage:
        result = req(p.project_list())
        result = req(p.role_register("my_role", label="My Role"))
    """
    return _run_async(_client.request(msg, timeout=timeout))


def on(event_type: str):
    """Decorator to register an event listener.

    Usage:
        @on("entity.updated")
        def handle(event):
            show(event)
    """
    def decorator(fn):
        async def _wrapper(event):
            fn(event)
        _client._listeners[event_type].append(_wrapper)
        print(f"Registered listener for {event_type!r}")
        return fn
    return decorator


# ─────────────────────────────────────────────────────────────
# Shell banner and helpers
# ─────────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════════════╗
║          forge-bridge interactive shell                  ║
╠══════════════════════════════════════════════════════════╣
║  client     AsyncClient (connected)                      ║
║  p          protocol module (message constructors)       ║
║  req(msg)   send request, return result dict             ║
║  on(type)   decorator to register event listener         ║
║  show(x)    pretty-print dict/list                       ║
║  store      MemoryStore (in-memory mode only)            ║
╠══════════════════════════════════════════════════════════╣
║  Quick start:                                            ║
║    req(p.role_list())                                    ║
║    req(p.project_create("Test", "TST"))                  ║
║    req(p.entity_list("shot", project_id))                ║
║    show(store.summary())    # in-memory mode             ║
╚══════════════════════════════════════════════════════════╝
"""


def _make_namespace(url: str, memory_mode: bool) -> dict:
    """Build the REPL namespace with everything pre-imported."""
    import forge_bridge.server.protocol as proto

    namespace = {
        # Core objects
        "client":  _client,
        "p":       proto,
        "req":     req,
        "on":      on,
        "show":    show,

        # All protocol constructors at top level for convenience
        "role_list":     proto.role_list,
        "role_register": proto.role_register,
        "role_rename":   proto.role_rename,
        "role_delete":   proto.role_delete,
        "project_create": proto.project_create,
        "project_list":  proto.project_list,
        "project_get":   proto.project_get,
        "entity_create": proto.entity_create,
        "entity_update": proto.entity_update,
        "entity_get":    proto.entity_get,
        "entity_list":   proto.entity_list,
        "query_shot_stack":   proto.query_shot_stack,
        "query_dependents":   proto.query_dependents,
        "query_events":       proto.query_events,
        "relationship_create": proto.relationship_create,
        "location_add":        proto.location_add,
        "subscribe":   proto.subscribe,
        "ping":        proto.ping,

        # Utilities
        "json": json,
        "uuid": __import__("uuid"),
    }

    if memory_mode:
        from forge_bridge.store.memory import get_store
        namespace["store"] = get_store()

    return namespace


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    global _loop, _client

    parser = argparse.ArgumentParser(description="forge-bridge interactive shell")
    parser.add_argument(
        "--url", default=None,
        help="Server URL (default: ws://127.0.0.1:9998, or auto in-memory if unreachable)"
    )
    parser.add_argument(
        "--inmemory", action="store_true",
        help="Always use in-memory server (no Postgres required)"
    )
    parser.add_argument(
        "--port", type=int, default=19876,
        help="Port for in-memory server (default: 19876)"
    )
    parser.add_argument(
        "--name", default="shell",
        help="Client name shown in server logs"
    )
    args = parser.parse_args()

    memory_mode = args.inmemory
    url = args.url or os.environ.get("FORGE_BRIDGE_URL", "ws://127.0.0.1:9998")

    # ── Start background event loop ──
    loop_ready = threading.Event()

    def _run_loop():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        loop_ready.set()
        _loop.run_forever()

    loop_thread = threading.Thread(target=_run_loop, daemon=True, name="forge-shell-loop")
    loop_thread.start()
    loop_ready.wait()

    # ── Connect or start in-memory ──
    from forge_bridge.client import AsyncClient

    if memory_mode:
        print("Starting in-memory forge-bridge server...", end=" ", flush=True)
        url = _start_memory_server(args.port)
        print(f"ready on {url}")
    else:
        # Try to connect; fall back to in-memory if server unreachable
        pass

    print(f"Connecting to {url} as {args.name!r}...", end=" ", flush=True)

    _client = AsyncClient(
        client_name=args.name,
        server_url=url,
        endpoint_type="shell",
        auto_reconnect=not memory_mode,
    )

    try:
        future = asyncio.run_coroutine_threadsafe(_client.start(), _loop)
        future.result(timeout=5)
        future = asyncio.run_coroutine_threadsafe(
            _client.wait_until_connected(timeout=8), _loop
        )
        future.result(timeout=10)
        print("connected ✓")
    except Exception as e:
        if not memory_mode and not args.url:
            print(f"\n  Could not reach {url}: {e}")
            print("  Starting in-memory server instead...")
            url = _start_memory_server(args.port)
            memory_mode = True
            future = asyncio.run_coroutine_threadsafe(_client.start(), _loop)
            future.result(timeout=5)
            future = asyncio.run_coroutine_threadsafe(
                _client.wait_until_connected(timeout=8), _loop
            )
            future.result(timeout=10)
            print("  connected ✓")
        else:
            print(f"failed: {e}")
            sys.exit(1)

    # ── Print connection info ──
    roles    = len(_client.registry_summary.get("roles", {}))
    rel_types = len(_client.registry_summary.get("relationship_types", {}))
    print(f"  session  = {_client.session_id}")
    print(f"  registry = {roles} roles, {rel_types} relationship types")
    if memory_mode:
        print("  mode     = in-memory (no Postgres)")

    # ── Drop into REPL ──
    namespace = _make_namespace(url, memory_mode)
    console   = code.InteractiveConsole(locals=namespace)
    console.interact(banner=BANNER, exitmsg="Disconnecting...")

    # ── Cleanup ──
    future = asyncio.run_coroutine_threadsafe(_client.stop(), _loop)
    try:
        future.result(timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
