"""Phase 10.1 D-39/D-43 — in-browser nav swap regression test.

Purpose
-------
The 2026-04-23 UAT surfaced a shipping render bug in shell.html line 7 —
`hx-boost="true"` combined with `hx-target="#view-main"` and
`hx-swap="innerHTML"` caused every nav-link click to inject the full shell
response INSIDE the existing `#view-main`, duplicating `.top-nav` and
`#health-strip` client-side. None of the Phase 10 tests caught it because
`starlette.testclient.TestClient` hits handlers in isolation — it never
performs an htmx swap in a real browser.

This test boots the console on an ephemeral port, loads /ui/tools in
Chromium, clicks a nav link, waits for the htmx-boost swap to settle, and
asserts the D-39 invariant:

  - exactly one `.top-nav` element in the rendered DOM
  - exactly one `#health-strip` element in the rendered DOM

Pre-commit verification (required by D-43) — stash-only round-trip
-----------------------------------------------------------------
This test MUST fail when run against the PRE-fix `shell.html` state. The
executor verifies this via a git-stash round-trip — NO manual file edits,
NO git checkout mid-cycle. The committed state of shell.html at this
point in Plan 10.1-04 IS the post-fix state (the Plan 10.1-02 edit was
committed upstream of this plan). Stashing surfaces the pre-fix state
from Git's perspective:

  0. Prerequisite: Plan 10.1-02's shell.html fix is already committed; so is
     Plan 10.1-04's test file and any pyproject.toml edits from Task 1.
     `git status` shows a clean working tree before the cycle begins.
  1. git stash push -m "10.1-04 D-43 pre-fix restore" forge_bridge/console/templates/shell.html
     -> stashes ONLY the fix file; working tree reverts shell.html to the
     pre-10.1-02 committed state, which contains the buggy hx-boost /
     hx-target / hx-swap attribute tuple on line 7.
  2. pytest tests/test_ui_nav_swap_regression.py -xvs
     -> expected: FAIL with an assertion like
        "After nav click, rendered DOM has 2 `.top-nav` elements; expected 1".
     Record the full pytest FAIL output for the SUMMARY.
  3. git stash pop
     -> restores the Plan 10.1-02 fix. Working tree returns to clean
     post-fix state.
  4. pytest tests/test_ui_nav_swap_regression.py -xvs
     -> expected: PASS. Record the green pytest output for the SUMMARY.
  5. git status
     -> expected: clean. No residual stash, no uncommitted shell.html
     changes.

If step 2 PASSES, STOP — the test is wrong (locator too permissive, wait
too short, or server response differs from the 2026-04-23 UAT observation).
Tighten the test until step 2 fails, then re-run the cycle from step 0.

If step 1 reports "No local changes to save", STOP — it means shell.html
is not in the state the plan expects. Check `git log --oneline forge_bridge/console/templates/shell.html` — the most recent commit must be the Plan 10.1-02 edit.

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

    Mirrors the D-44 fixture shape that will also be used in the
    Plan 10.1-05 re-UAT: 3 synthesized tools with distinct
    `synthesized_at` timestamps (so the operator can identify
    "most recent"), 1 synthesized-zero-obs tool, 1 builtin tool.
    No quarantined tools — they are removed from the registry by
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
            observation_count=0,   # -> "loaded" chip
        ),
        ToolRecord(
            name="flame_get_project",
            origin="builtin",
            namespace="flame",
            code_hash=None,
            observation_count=20,  # -> "loaded" chip (builtin, never "active" in the D-40 derivation)
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

    Mirrors tests/test_console_http_transport.py:24-75. Yields
    (port, fake_api) so the test can hit http://127.0.0.1:{port}/ui/tools
    in a real browser.
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
async def test_nav_click_yields_single_nav_and_single_health_strip(
    live_console_server,
) -> None:
    """D-39 invariant: after a boosted nav click, the rendered DOM must
    contain exactly one `.top-nav` element and exactly one `#health-strip`
    element. This test fails loudly against the PRE-fix `shell.html` state
    (where hx-target="#view-main" + hx-swap="innerHTML" cause a duplicate).
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

            # Click a nav link (Executions) — triggers hx-boost swap
            await page.locator('a.nav-link[href="/ui/execs"]').click()

            # htmx-boost swap settle: wait for the boosted request to complete + DOM to update.
            # networkidle is the safe default for boosted navigation since hx-push-url rewrites
            # the URL and htmx swaps the body synchronously once the response lands.
            await page.wait_for_load_state("networkidle")

            # D-39 invariant assertions
            post_nav_count = await page.locator("nav.top-nav").count()
            post_strip_count = await page.locator("#health-strip").count()
            assert post_nav_count == 1, (
                f"After nav click, rendered DOM has {post_nav_count} `.top-nav` elements; "
                "expected exactly 1. This is the 2026-04-23 duplicate-nav regression — the "
                "`hx-boost` + `hx-target=#view-main` + `hx-swap=innerHTML` mismatch is back "
                "on shell.html. Fix: remove `hx-target` and `hx-swap` from the `<nav>` element."
            )
            assert post_strip_count == 1, (
                f"After nav click, rendered DOM has {post_strip_count} `#health-strip` "
                "elements; expected exactly 1. Duplicate-health-strip is the same bug class "
                "as the duplicate-nav — check shell.html hx-boost swap configuration."
            )

            # Belt-and-suspenders: URL was actually pushed (hx-push-url contract)
            assert page.url.endswith("/ui/execs"), (
                f"Expected URL /ui/execs after nav click; got {page.url}. "
                "hx-push-url contract may be broken."
            )
        finally:
            await browser.close()
