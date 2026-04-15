"""
Wave 0 test scaffolds for forge_bridge.learning.watcher — asyncio file watcher.

These tests are SKIPPED stubs — implementation lands in Plan 03.
They serve as living documentation of the behaviours Plan 03 must satisfy.

Requirements covered:
    MCP-03  Asyncio polling watcher: hot-load new/changed synthesized tools
            from mcp/synthesized/ using importlib; remove tools when file disappears.
"""

import pytest

# Uncomment when watcher is implemented in Plan 03:
# from forge_bridge.learning.watcher import watch_synthesized_tools, _scan_once


@pytest.mark.skip(reason="Implemented in Plan 03")
def test_watcher_loads_new_file():
    """Watcher detects a new .py file in synthesized/ and calls add_tool.

    Scenario:
        1. Start with an empty synthesized/ directory.
        2. Drop a valid synth_my_tool.py containing `def synth_my_tool() -> str: ...`
        3. Call _scan_once(mcp, seen={}).
        4. Assert 'synth_my_tool' is present in mcp._tool_manager._tools.
        5. Assert seen['synth_my_tool'] matches the file's SHA-256 digest.
    """
    pass


@pytest.mark.skip(reason="Implemented in Plan 03")
def test_watcher_reloads_changed_file():
    """Watcher detects a changed .py file and re-registers the updated tool.

    Scenario:
        1. Register an initial version of synth_my_tool via _scan_once.
        2. Overwrite the file with a new implementation (different bytes = new hash).
        3. Call _scan_once again with the existing seen dict.
        4. Assert the tool in mcp._tool_manager._tools reflects the updated function
           (e.g. check return annotation or docstring changed).
        5. Assert seen['synth_my_tool'] is updated to the new SHA-256 digest.
    """
    pass


@pytest.mark.skip(reason="Implemented in Plan 03")
def test_watcher_removes_deleted_file():
    """Watcher removes a tool from the registry when its .py file is deleted.

    Scenario:
        1. Register synth_my_tool via _scan_once (tool present in mcp._tool_manager._tools).
        2. Delete the file from synthesized/.
        3. Call _scan_once again.
        4. Assert 'synth_my_tool' is absent from mcp._tool_manager._tools.
        5. Assert 'synth_my_tool' is absent from the seen dict.
    """
    pass
