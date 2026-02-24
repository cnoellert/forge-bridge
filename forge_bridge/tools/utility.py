"""Utility tools — raw execution, shortcuts, system info."""

import json

from pydantic import BaseModel, Field

from forge_mcp import bridge


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
    """Execute arbitrary Python code inside Flame's runtime.

    This is the escape hatch for operations not covered by other tools.
    The `flame` module is available. Print results to stdout.

    ⚠️ Use with care — bad code can crash Flame.
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
