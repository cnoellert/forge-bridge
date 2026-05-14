"""Utility tools — raw execution, shortcuts, system info."""

import json

from pydantic import BaseModel, Field

from forge_bridge import bridge


# ── Tool: flame_execute_python ──────────────────────────────────────────


class ExecutePythonInput(BaseModel):
    """Input for raw Python execution."""

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


async def execute_python(params: ExecutePythonInput) -> str:
    """Flame: the universal Flame introspection and automation surface.

    When a dedicated flame_* tool covers your need (flame_get_project,
    flame_list_desktop, flame_list_libraries, flame_context, etc.), prefer
    it — those tools are typed, validated, and cheaper. For everything
    else, this is the canonical answer.

    Use this tool whenever you need to inspect or manipulate Flame state
    and no dedicated flame_* tool directly exposes the required
    information. This is the escalation path when narrow tools either
    don't exist for your question or return adjacent-but-insufficient
    data (e.g. flame_list_desktop returns reel clip *counts* but the
    user wants clip *names* — reach here with a one-liner). It is the
    reflective surface of Flame itself: anything the Flame Python API
    can answer, this tool can answer.

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
    resp = await bridge.execute(params.code, main_thread=params.main_thread)
    result = {
        "stdout": resp.stdout,
        "stderr": resp.stderr,
        "result": resp.result,
    }
    if resp.error:
        result["error"] = resp.error
        result["traceback"] = resp.traceback
    return json.dumps(result, indent=2)


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

    Returns connection status, Flame version, and current project.
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
        return json.dumps({"connected": False, "error": str(e)}, indent=2)
