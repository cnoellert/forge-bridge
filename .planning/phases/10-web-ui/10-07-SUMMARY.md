---
phase: 10-web-ui
plan: "07"
subsystem: console-ui-chat
tags: [jinja2, chat-stub, d28, d29, nav, wave-5]
dependency_graph:
  requires:
    - phase: 10-web-ui plan 01
      provides: forge-console.css with .chat-stub-card rule
    - phase: 10-web-ui plan 02
      provides: shell.html template block contract, active_view nav convention
    - phase: 10-web-ui plan 03
      provides: ui_chat_stub_handler 501 stub + route /ui/chat registered in app.py
  provides:
    - /ui/chat: full-shell 200 response with centered LLM Chat placeholder card
    - chat/stub.html: D-28 compliant template extending shell.html
    - ui_chat_stub_handler: real implementation (replaces Wave 1 501 stub)
    - active_view='chat': nav active-state highlighting for the Chat link
  affects:
    - 10-08 (UAT verification — /ui/chat smoke-tested as part of five-view coverage)
tech-stack:
  added: []
  patterns:
    - Static content stub template extending shell.html — no Alpine, no htmx attributes, no dynamic data
    - D-28/D-29 nav contract: ship the nav surface now, Phase 12 fills in the panel body without shell.html churn
    - active_view='chat' context var drives aria-current="page" on the Chat nav link (established by plan 10-02)
key-files:
  created:
    - forge_bridge/console/templates/chat/stub.html
    - tests/test_ui_chat_stub.py
  modified:
    - forge_bridge/console/ui_handlers.py
key-decisions:
  - "Chat stub is explicitly minimal per D-29 — no Alpine component, no htmx attribute, no dynamic data. Phase 12 replaces the template body without touching shell.html or the route table."
  - "Chip-link hrefs are exact per UI-SPEC: /ui/tools?origin=synthesized and /ui/execs — these are plain anchor tags, not htmx-powered, so they work with JS disabled per D-05"
  - "Arrow character uses HTML entity &#x2192; (U+2192) rather than the UTF-8 literal — safe across all charset contexts; no behavior difference at render time"
  - "TDD gate compliance: RED commit (703a6ae) precedes GREEN commit (ed4035d) — both gates present in git log"

# Metrics
duration: 10min
completed: 2026-04-23
tasks_completed: 1
files_created: 2
files_modified: 1
---

# Phase 10 Plan 07: Chat Nav Stub Summary

**Chat nav stub replacing the 501 placeholder at /ui/chat with a full-shell D-28/D-29 compliant placeholder card containing verbatim UI-SPEC copy and two on-ramp chip-links back to the tools and execs views**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-04-23
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files created:** 2
- **Files modified:** 1

## Accomplishments

- `chat/stub.html` — Jinja2 template extending `shell.html` via `{% block view %}`. Centered `.card.chat-stub-card` with `aria-labelledby`, h1 heading, verbatim UI-SPEC body copy, and two chip-link anchors pointing to `/ui/tools?origin=synthesized` and `/ui/execs`.
- `ui_chat_stub_handler` — 501 placeholder replaced with `TemplateResponse("chat/stub.html", {"request": request, "active_view": "chat"})`. No data fetched, no exception path needed — purely static content.
- `tests/test_ui_chat_stub.py` — 5 pytest assertions: 200 status, body copy verbatim match, chip-link href + label presence, shell chrome (`<nav class="top-nav"` + `id="health-strip"` + `aria-current="page"`), CSS class contract.

## TDD Gate Compliance

| Gate | Commit | Verified |
|------|--------|---------|
| RED (failing test) | 703a6ae | test(10-07): add failing tests for /ui/chat nav stub — 5 tests, all fail with 501 |
| GREEN (implementation) | ed4035d | feat(10-07): implement /ui/chat nav stub view — 5 tests pass |

## Task Commits

1. **RED — failing test** — `703a6ae` (test)
2. **GREEN — template + handler** — `ed4035d` (feat)

## Files Created

- `forge_bridge/console/templates/chat/stub.html` — Chat nav stub template; extends shell.html; centered card; verbatim UI-SPEC copy; two chip-link anchors
- `tests/test_ui_chat_stub.py` — 5 functional pytest assertions covering all acceptance criteria

## Files Modified

- `forge_bridge/console/ui_handlers.py` — `ui_chat_stub_handler` replaced; 501 inline HTML removed; real `TemplateResponse` with `active_view="chat"` installed

## Decisions Made

1. **Chat stub is intentionally minimal per D-29.** No Alpine `x-data`, no htmx attributes, no dynamic data. The template body is pure static HTML. Phase 12 replaces `{% block view %}` content in `chat/stub.html` without touching `shell.html`, the route table (`app.py`), or `ui_handlers.py`'s handler signature.

2. **Chip-links are plain `<a>` anchors, not htmx-enhanced.** This preserves D-05 JS-disabled graceful degradation for the chat stub's on-ramp path. Artists can click through to `/ui/tools?origin=synthesized` even without JS.

3. **Arrow character rendered as HTML entity (`&#x2192;`).** The plan permitted the UTF-8 literal `→` per UI-SPEC, but the entity form is safe across all charset contexts without relying on template encoding settings. Visually identical.

## Deviations from Plan

None — plan executed exactly as written. Template content, handler pattern, and test assertions all match the plan spec verbatim.

## Known Stubs

None. This plan's purpose is to replace the only remaining stub in the `/ui/*` route table (`ui_chat_stub_handler`). All five Phase 10 full-page routes now return 200 with real rendered content.

The chat view body itself is intentionally a placeholder — but this is documented D-29 behavior, not a stub. Phase 12 is the explicit resolution target.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The chat stub renders only template-literal strings — no user data, no dynamic content. T-10-33 (XSS via static stub copy) and T-10-34 (Phase 12 roadmap disclosure) are both `accept` dispositions per the plan's threat model. Nothing outside the plan's threat register.

## Self-Check: PASSED

- forge_bridge/console/templates/chat/stub.html: FOUND
- tests/test_ui_chat_stub.py: FOUND
- forge_bridge/console/ui_handlers.py: FOUND (modified)
- Commit 703a6ae (RED): FOUND
- Commit ed4035d (GREEN): FOUND
- pytest tests/test_ui_chat_stub.py -x: 5/5 PASS
- Full regression (77 tests): PASS
- ruff check forge_bridge/console/ui_handlers.py tests/test_ui_chat_stub.py: PASS
- template acceptance criteria (9 grep checks): ALL PASS
