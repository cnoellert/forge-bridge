"""Phase 10.1 D-39 — in-browser chip-click swap regression test (companion to
tests/test_ui_nav_swap_regression.py).

Purpose
-------
The 2026-04-24 pre-UAT smoke check surfaced a second shipping render bug in
the same D-39 invariant class fixed by Plan 10.1-02 for nav links. This
time the offender is `forge_bridge/console/templates/fragments/query_console.html`:
`submit()` (and `clearAndReset()`) called `htmx.ajax('GET', url, { target:
'#view-main', swap: 'innerHTML', ... })` where `url` is a full-page route
like `/ui/tools?origin=synthesized`. The server returns the full shell+view
(per D-01), and htmx injects it inside `#view-main`, producing shell-inside-
shell (exactly the same bug class as the 2026-04-23 nav bug, but via a
different code path — JS `htmx.ajax`, not `hx-boost`).

Plan 10.1-04's Playwright regression only exercised nav-link clicks via
`hx-boost`; chip clicks route through the `stuffAndSubmit()` -> `submit()`
JS path, which was never covered end-to-end in a real browser. This test
closes the chip-click branch of D-43 coverage.

Assertion contract (mirrors test_ui_nav_swap_regression.py):
  - exactly one `.top-nav` element in the rendered DOM after chip click
  - exactly one `#health-strip` element in the rendered DOM after chip click
  - URL pushed to `/ui/tools?origin=synthesized` (belt-and-suspenders)
  - query-console input shows the chip's tokens (`origin:synthesized`) —
    proves `submit()` actually ran and the page state reflects it.

FAIL/PASS cycle
---------------
Per Plan 10.1-06 Task 2 action, the executor runs:

  git stash push -m "10.1-06 FAIL-check" forge_bridge/console/templates/fragments/query_console.html
  pytest tests/test_ui_chip_click_regression.py -xvs   # expect FAIL — duplicate nav
  git stash pop
  pytest tests/test_ui_chip_click_regression.py -xvs   # expect PASS
  git status                                            # expect clean

The SUMMARY records both pytest outputs.

Fixture + harness
-----------------
Reuses `_find_free_port`, `_make_fake_read_api`, and the `live_console_server`
fixture shape from `tests/test_ui_nav_swap_regression.py` verbatim (module-
local copies, following the existing convention established by that test).

Dev setup
---------
pip install -e '.[test-e2e]'
python -m playwright install chromium
"""
from __future__ import annotations

import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ToolRecord
from forge_bridge.mcp.server import _start_console_task


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_fake_read_api() -> MagicMock:
    """Build a fake ConsoleReadAPI with 5 ToolRecords.

    Mirrors tests/test_ui_nav_swap_regression.py._make_fake_read_api() (the
    canonical D-44 fixture shape): 3 synthesized tools with distinct
    `synthesized_at` timestamps, 1 synthesized-zero-obs tool, 1 builtin
    tool. No quarantined tools — they are removed from the registry by
    the watcher's removal-mirror path (locked by
    tests/test_tool_quarantine_surface.py).
    """
    tools = [
        ToolRecord(
            name="synth_set_segment_note",
            origin="synthesized",
            namespace="synth",
            synthesized_at="2026-04-23T18:45:00Z",
            code_hash="a" * 64,
            version="1.0.0",
            observation_count=4,
        ),
        ToolRecord(
            name="synth_batch_rename_by_grade",
            origin="synthesized",
            namespace="synth",
            synthesized_at="2026-04-23T15:20:00Z",
            code_hash="b" * 64,
            version="1.0.0",
            observation_count=11,
        ),
        ToolRecord(
            name="synth_promote_last_render",
            origin="synthesized",
            namespace="synth",
            synthesized_at="2026-04-23T11:05:00Z",
            code_hash="c" * 64,
            version="1.0.0",
            observation_count=2,
        ),
        ToolRecord(
            name="synth_draft_shot_brief",
            origin="synthesized",
            namespace="synth",
            synthesized_at="2026-04-22T09:00:00Z",
            code_hash="d" * 64,
            version="1.0.0",
            observation_count=0,
        ),
        ToolRecord(
            name="flame_get_project",
            origin="builtin",
            namespace="flame",
            code_hash=None,
            observation_count=20,
        ),
    ]
    api = MagicMock()
    api.get_tools = AsyncMock(return_value=tools)
    api.get_tool = AsyncMock(return_value=tools[0])
    api.get_executions = AsyncMock(return_value=([], 0))
    api.get_manifest = AsyncMock(return_value={
        "tools": [t.to_dict() for t in tools],
        "count": len(tools),
        "schema_version": "1",
    })
    api.get_health = AsyncMock(return_value={
        "status": "ok",
        "ts": "2026-04-23T19:00:00Z",
        "version": "1.3.0",
        "services": {
            "mcp": {"status": "ok", "detail": "lifespan started"},
            "flame_bridge": {"status": "ok", "detail": "http 200"},
            "ws_server": {"status": "ok", "detail": "tcp reachable"},
            "llm_backends": [],
            "watcher": {"status": "ok", "task_done": False, "detail": ""},
            "storage_callback": {"status": "absent", "registered": False, "detail": ""},
            "console_port": {"status": "ok", "port": 9996, "detail": "serving"},
        },
        "instance_identity": {
            "execution_log": {"id_match": True, "detail": "canonical"},
            "manifest_service": {"id_match": True, "detail": "canonical"},
        },
    })
    return api


@pytest.fixture
async def live_console_server(monkeypatch):
    """Spin up a real uvicorn-served console app on an ephemeral port.

    Mirrors tests/test_ui_nav_swap_regression.py live_console_server fixture
    verbatim. Yields (port, fake_api) so the test can hit
    http://127.0.0.1:{port}/ui/tools in a real browser.
    """
    monkeypatch.setattr(
        "forge_bridge.mcp.server._server_started", True, raising=False,
    )
    monkeypatch.setattr(
        "forge_bridge.mcp.server._canonical_watcher_task", None, raising=False,
    )

    api = _make_fake_read_api()
    app = build_console_app(api)
    port = _find_free_port()
    task, server = await _start_console_task(app, "127.0.0.1", port)
    assert task is not None and server is not None

    try:
        yield port, api
    finally:
        if server is not None:
            server.should_exit = True
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                task.cancel()
                try:
                    await task
                except Exception:
                    pass


@pytest.mark.asyncio
async def test_chip_click_yields_single_nav_and_single_health_strip(
    live_console_server,
) -> None:
    """D-39 invariant: clicking a preset chip (a JS `htmx.ajax` swap path,
    not an `hx-boost` path) must yield a rendered DOM with exactly one
    `.top-nav` and one `#health-strip`. This test fails loudly against the
    pre-10.1-06 `query_console.html` state (where submit() used
    `target: '#view-main' / swap: 'innerHTML'`, stuffing the full shell
    inside `#view-main`).
    """
    pytest.importorskip("playwright.async_api")
    from playwright.async_api import async_playwright

    port, _api = live_console_server

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(f"http://127.0.0.1:{port}/ui/tools")

            # Sanity: initial page has exactly one of each
            initial_nav_count = await page.locator("nav.top-nav").count()
            initial_strip_count = await page.locator("#health-strip").count()
            assert initial_nav_count == 1, (
                f"Initial page load has {initial_nav_count} `.top-nav` elements; expected 1. "
                "Server-rendered shell.html is malformed before any htmx interaction."
            )
            assert initial_strip_count == 1, (
                f"Initial page load has {initial_strip_count} `#health-strip` elements; expected 1."
            )

            # Click the 'Synth only' preset chip — triggers stuffAndSubmit() ->
            # submit() -> htmx.ajax() JS swap. Uses a text-based locator so
            # the test binds to the user-facing label, not to DOM ordering.
            await page.locator("button.chip", has_text="Synth only").click()

            # htmx swap settle: wait for the ajax request to complete + DOM to
            # update. networkidle is the safe default because submit() uses
            # pushUrl: true which triggers a URL rewrite on response.
            await page.wait_for_load_state("networkidle")

            # D-39 invariant assertions
            post_nav_count = await page.locator("nav.top-nav").count()
            post_strip_count = await page.locator("#health-strip").count()
            assert post_nav_count == 1, (
                f"After chip click, rendered DOM has {post_nav_count} `.top-nav` elements; "
                "expected exactly 1. Chip click produces shell-duplicate — query_console.html "
                "submit() swap target mismatch (2026-04-24 regression)."
            )
            assert post_strip_count == 1, (
                f"After chip click, rendered DOM has {post_strip_count} `#health-strip` "
                "elements; expected exactly 1. Chip click produces shell-duplicate — "
                "query_console.html submit() swap target mismatch (2026-04-24 regression)."
            )

            # Belt-and-suspenders: URL was actually pushed (pushUrl contract)
            assert page.url.endswith("/ui/tools?origin=synthesized"), (
                f"Expected URL /ui/tools?origin=synthesized after chip click; got {page.url}. "
                "pushUrl contract may be broken in query_console.html submit()."
            )

            # Belt-and-suspenders: the query-console input reflects the chip's
            # tokens, proving submit() actually ran (not just that the page
            # rendered without breaking).
            input_value = await page.locator("#query-console-input").input_value()
            assert input_value == "origin:synthesized", (
                f"Expected query-console input value 'origin:synthesized' after chip click; "
                f"got {input_value!r}. D-26 re-hydration from URL params may be broken, or "
                "submit() did not actually fire."
            )
        finally:
            await browser.close()
