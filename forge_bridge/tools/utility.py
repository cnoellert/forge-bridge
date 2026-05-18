"""Utility tools — raw execution, shortcuts, system info."""

import hashlib
import json
import logging
import time

from pydantic import BaseModel, Field

from forge_bridge import bridge
from forge_bridge.runtime.graph_emit import emit_event, new_graph_id

logger = logging.getLogger(__name__)


# ── Tool: flame_execute_python ──────────────────────────────────────────
#
# Phase 23.1 in-flight gap-fix (D-20): the function previously took a
# single `params: ExecutePythonInput` pydantic BaseModel argument. FastMCP
# introspected that and generated a JSON schema requiring
# {"params": {"code": "...", "main_thread": false}} — a nested wrapped
# shape. The chat model consistently generated the flat
# {"code": "...", "main_thread": false} shape, so pydantic validation
# failed at MCP-dispatch BEFORE the function body ran. Zero tool-wrapper
# log lines fired despite the router's per-iter log showing
# `tool=flame_execute_python` — the function was named but never invoked.
#
# Flattening the signature to direct kwargs makes FastMCP generate a flat
# JSON schema matching what the model naturally produces. The
# `ExecutePythonInput` BaseModel is retained for back-compat callers
# (direct Python use, the v1.0 invocation shape) but is no longer the
# function signature.


class ExecutePythonInput(BaseModel):
    """Back-compat input model — retained for direct-Python callers that
    constructed an ExecutePythonInput pre-23.1. The MCP-registered
    function signature is now flat (code: str, main_thread: bool); MCP
    callers should use direct kwargs, not this wrapper."""

    code: str = Field(
        ...,
        description="Python code to execute inside Flame. The `flame` module "
        "is pre-imported. Use `print()` to return data. For write "
        "operations, use schedule_idle_event.",
        min_length=1,
    )
    main_thread: bool = Field(
        default=False,
        description="If True, execute on Flame's Qt main thread. Required "
        "for any write operations (set_value, create, delete).",
    )


async def execute_python(code: str, main_thread: bool = False) -> str:
    """Flame: the canonical introspection surface for reel structure,
    clip enumeration, timeline traversal, and Flame state inspection.

    Canonical use cases:
    - reel inspection (clip names, sequence enumeration, reel-group structure)
    - clip enumeration (per-reel, per-library, per-folder contents by name)
    - timeline traversal (sequence segments with start/end frames, track
      structure, segment metadata, version layers)
    - batch graph traversal (batch group node enumeration, node attribute
      inspection, write-file output paths)
    - sequence inspection (segment counts, frame ranges, layer structure)
    - selection queries (what is the artist currently looking at)
    - any state question that doesn't map to a narrow flame_* tool

    This is the reflective surface of Flame itself: anything the Flame
    Python API can answer, this tool can answer. Use it whenever you need
    to inspect or manipulate Flame state and no dedicated flame_* tool
    directly exposes the required information. It is also the escalation
    path when narrow tools return adjacent-but-insufficient data (e.g.
    flame_list_desktop returns reel clip *counts* but the user wants
    clip *names* — reach here with a one-liner).

    Dedicated flame_* tools remain useful for narrow typed operations
    (flame_get_project, flame_list_desktop, flame_list_libraries,
    flame_context, etc.) because they are validated and cheaper to run.
    But when the question requires structural traversal, enumeration,
    cross-surface inspection, or reflective access to Flame state,
    this is the canonical answer surface.

    Do NOT use this tool when:
    - a narrow flame_* tool exists for the exact question — those are
      typed and validated; prefer them
    - the user is asking about pipeline-registry state — use forge_* tools
    - the operation is a destructive mutation that should route through
      staged-ops approval — don't bypass the approval gate

    The `flame` module is pre-imported in the bridge namespace. Print
    results to stdout — wrap with `json.dumps(...)` for structured returns,
    or plain `print(...)` for human-readable text. Returns a JSON object
    with stdout, stderr, result, and (if execution raised) error +
    traceback. Read stdout for the answer to your query; error/traceback
    indicate the snippet itself failed.

    Example 1 — list clip names on a named reel (canonical introspection):

        code = '''
            import flame, json
            desk = flame.project.current_project.current_workspace.desktop
            target_reel = None
            for rg in desk.reel_groups:
                for r in rg.reels:
                    name = r.name.get_value() if hasattr(r.name, "get_value") else str(r.name)
                    if name == "Reel 1":
                        target_reel = r
                        break
            if target_reel is None:
                print(json.dumps({"error": "Reel 1 not found"}))
            else:
                clips = [
                    c.name.get_value() if hasattr(c.name, "get_value") else str(c.name)
                    for c in target_reel.clips
                ]
                print(json.dumps({"reel": "Reel 1", "clips": clips}))
        '''

    Example 2 — enumerate nodes in the current Batch group (graph traversal):

        code = '''
            import flame, json
            bg = flame.batch
            nodes = []
            for n in bg.nodes:
                nodes.append({
                    "name": str(n.name),
                    "type": n.type,
                })
            print(json.dumps({"batch_group": str(bg.name), "nodes": nodes}))
        '''

    Example 3 — list timeline segments with frame ranges (sequence inspection):

        code = '''
            import flame, json
            seq = flame.project.current_project.current_workspace.desktop.reel_groups[0].reels[0].sequences[0]
            segments = []
            for v in seq.versions:
                for t in v.tracks:
                    for seg in t.segments:
                        segments.append({
                            "name": str(seg.name),
                            "start": seg.record_in.frame if hasattr(seg.record_in, "frame") else None,
                            "end": seg.record_out.frame if hasattr(seg.record_out, "frame") else None,
                        })
            print(json.dumps({"sequence": str(seq.name), "segments": segments}))
        '''

    Mutation note. The `main_thread` parameter defaults to False (read-only
    safe — the canonical use cases above all run on the worker thread).
    Set main_thread=True ONLY for write operations (set_value, create,
    delete, rename) that require Flame's Qt main thread. For destructive
    mutations, prefer routing through the staged-ops platform
    (forge_stage_*) so the operator has an approval surface; this tool is
    primarily a discovery interface, not a mutation primitive.

    ⚠️ Flame-side exceptions return as `error` + `traceback` in the
    response, not raised — check the response shape before assuming
    success. Bad Python (infinite loops, runaway resource use) can hang
    Flame's main thread when main_thread=True.
    """
    # Phase 23.1 observability: every invocation logs code_hash + main_thread
    # + elapsed + status + code_len so post-walk diagnostics can correlate
    # per-call behavior without re-running the failure. SEED-FLAME-EXEC-
    # OBSERVABILITY-V1.6+ captures the richer instrumentation arc (queue-
    # wait timing, hook-side per-stage breakdown) that requires hook-
    # protocol cooperation and so belongs in v1.6's observability phase.
    #
    # Phase 24 Commit 2 — alongside the structured stderr log, emit two
    # graph events per invocation (`started` at entry, terminal status at
    # exit) into ~/.forge-bridge/graphs/<graph_id>.jsonl. Each call is
    # its own one-graph for now; chat-session graph propagation lands in
    # a later commit. The structured log line above stays unchanged —
    # operators read it in real time; the JSONL events are the
    # observability artifact for replay + non-author audit.
    return await _execute_python_core(code, main_thread, new_graph_id())


async def _execute_python_core(code: str, main_thread: bool, graph_id: str) -> str:
    """Shared execution body for ``execute_python`` and operator-side surfaces.

    The caller provides the ``graph_id``. ``execute_python`` (the MCP tool
    entry point) calls this with a freshly-minted graph_id each invocation;
    operator-side CLI surfaces (``fbridge flame-exec``) call it with a
    graph_id they pre-allocated so they can report it back to the operator.

    Single execution path, single observability emission, single error
    shaping. The operator surface boundary is metadata (who initiated),
    NOT ontology — both paths emit ``node_kind="python"`` because the
    substrate truth is the same: a Python execution against Flame occurred.
    """
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]
    started = time.monotonic()
    status = "unknown"
    # node_kind is substrate-level runtime semantics, NOT MCP-tool-name.
    # The Flame hook executes Python; that's the substrate kind. A future
    # `flame_run_batch` MCP tool would emit `node_kind="batch_run"`; a future
    # `maya_execute_python` would still emit `node_kind="python"` because
    # the substrate is the same. Closed enumeration per v1.6-FRAMING.md §4.
    emit_event(
        graph_id=graph_id,
        node_kind="python",
        status="started",
        payload={
            "code_hash": code_hash,
            "main_thread": main_thread,
            "code_len": len(code),
        },
    )
    try:
        resp = await bridge.execute(code, main_thread=main_thread)
        result = {
            "stdout": resp.stdout,
            "stderr": resp.stderr,
            "result": resp.result,
        }
        if resp.error:
            result["error"] = resp.error
            result["traceback"] = resp.traceback
            status = "flame_error"  # Flame-side Python raised; tool surface returned cleanly
        else:
            status = "ok"
        return json.dumps(result, indent=2)
    except Exception:
        # Transport-layer failure — bridge.execute raised (BridgeConnectionError
        # for refused/timeout/comm-error). This is what the router sees as
        # `status=tool_error` in its iteration log. Capturing here means
        # operators can correlate the model-side `tool_error` event with the
        # tool-side cause without cross-referencing two log streams.
        status = "transport_error"
        raise
    finally:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "flame_execute_python code_hash=%s main_thread=%s "
            "elapsed_ms=%d status=%s code_len=%d",
            code_hash, main_thread, elapsed_ms, status, len(code),
        )
        emit_event(
            graph_id=graph_id,
            node_kind="python",
            status=status,
            payload={
                "code_hash": code_hash,
                "main_thread": main_thread,
                "elapsed_ms": elapsed_ms,
                "code_len": len(code),
            },
        )


# ── Tool: flame_execute_shortcut ────────────────────────────────────────


class ShortcutInput(BaseModel):
    """Input for triggering a keyboard shortcut."""

    description: str = Field(
        ...,
        description="The shortcut description as shown in Flame's hotkey "
        "editor (e.g. 'Undo', 'Redo', 'Select All').",
    )


async def execute_shortcut(params: ShortcutInput) -> str:
    """Trigger a Flame keyboard shortcut by its description.

    Runs on Flame's main thread. Use the exact description string
    from Flame's hotkey editor.
    """
    data = await bridge.execute_json(f"""
        import flame, json, threading
        event = threading.Event()
        result = {{}}
        def _do():
            try:
                flame.execute_shortcut({params.description!r})
                result['ok'] = True
                result['shortcut'] = {params.description!r}
            except Exception as e:
                result['error'] = str(e)
            event.set()
        flame.schedule_idle_event(_do)
        event.wait(timeout=10)
        print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_ping ────────────────────────────────────────────────────


async def ping() -> str:
    """Check if the FORGE Bridge is reachable and Flame is running.

    Returns connection status, Flame version, current project, and the
    daemon's effective `bridge.BRIDGE_URL`. The `bridge_url` field is echoed
    on BOTH success and failure paths so that Phase 24.2's daemon-routed
    doctor probe can distinguish "wrong target, no response" (WARN-divergent)
    from "right target, no response" (FAIL-daemon-says-broken) — the
    pre-Phase-24.2 failure-path body omitted bridge_url, which caused
    doctor's divergence detection to mis-classify the portofino env-file
    conflation case as FAIL-daemon-says-broken instead of WARN-divergent.

    See: .planning/milestones/v1.6-PHASE-24-2-FRAMING.md §6.4 (Q4 4-state
    truth-authority degradation table); ~/.forge-bridge/measurements/
    2026-05-15-phase-24-2-rerun/ (the canonical-probe re-fire that
    surfaced the design gap).
    """
    try:
        data = await bridge.execute_json("""
            import flame, json
            print(json.dumps({
                'connected': True,
                'version': flame.get_version(),
                'project': flame.projects.current_project.project_name,
                'current_tab': flame.get_current_tab(),
                'bridge_url': '""" + bridge.BRIDGE_URL + """',
            }))
        """)
        return json.dumps(data, indent=2)
    except bridge.BridgeConnectionError as e:
        return json.dumps({
            "connected": False,
            "error": str(e),
            "bridge_url": bridge.BRIDGE_URL,
        }, indent=2)
