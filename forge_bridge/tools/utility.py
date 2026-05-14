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
    """Flame: execute arbitrary Python code inside the running Flame session.

    The escape hatch for any Flame introspection or operation that no
    narrow flame_* tool covers. The `flame` module is pre-imported in the
    bridge namespace. Print results to stdout — wrap with `json.dumps(...)`
    for structured returns, or plain `print(...)` for human-readable text.

    Returns a JSON object with stdout, stderr, result, and (if execution
    raised) error + traceback. The model should read stdout for the
    answer to its query; error/traceback indicate the snippet itself failed.

    Use this tool when:
    - the user asks about Flame session state that no narrow flame_* tool
      surfaces (e.g. clip names on a specific reel, segment counts per
      sequence, batch node enumeration, custom selector queries)
    - the narrow tools return adjacent-but-insufficient data (e.g.
      flame_list_desktop returns reel clip *counts* but the user wants
      clip *names* — reach for flame_execute_python with a one-liner)
    - composing a small ad-hoc query across multiple Flame entities

    Do NOT use this tool when:
    - a narrow flame_* tool exists for the exact question (prefer
      flame_get_project, flame_list_desktop, flame_context, etc. — they're
      typed, validated, and cheaper)
    - the user is asking about pipeline-registry state (use forge_* tools)
    - the operation is a destructive mutation that should route through
      staged-ops approval (don't bypass the approval gate)

    The `main_thread` parameter defaults to False (read-only safe). Set
    main_thread=True ONLY for write operations (set_value, create, delete,
    rename) that require Flame's Qt main thread.

    Example 1 — list clip names on a named reel (read-only, structured):

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
        # main_thread=False (default)

    Example 2 — print current Flame version + OCIO config (read-only, plain):

        code = '''
            import flame, os
            proj = flame.project.current_project
            cfg = os.path.join(proj.setups_folder, "colour_mgmt", "config.ocio")
            print("Flame version:", flame.get_version())
            print("OCIO config:", os.path.realpath(cfg) if os.path.exists(cfg) else "(none)")
        '''
        # main_thread=False (default)

    Example 3 — rename a single segment (mutation, main_thread=True required):

        code = '''
            import flame
            seq = flame.project.current_project.current_workspace.desktop.reel_groups[0].reels[0].sequences[0]
            seg = seq.versions[0].tracks[0].segments[0]
            seg.name = "shot_010_v01"
        '''
        # main_thread=True  ← required for set_value / mutation

    ⚠️ Use with care — Flame-side exceptions return as `error` + `traceback`
    in the response, not raised; check the response shape before assuming
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
