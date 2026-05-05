---
name: SEED-CHAT-UI-TOOL-ROW-RENDERING-V1.5+
description: Improve rendering of tool call/result rows in Web UI to replace raw FastMCP TextContent serialization with readable, structured display
type: forward-looking-polish
planted_during: Phase A verification (2026-05-05) — first live confirmation of full transcript + tool_trace visibility
trigger_when: v1.5.x polish window OR Web UI usability friction observed OR Ask dialog work begins
---

# SEED-CHAT-UI-TOOL-ROW-RENDERING-V1.5+: readable tool rows in chat UI

## Idea

Replace raw FastMCP serialization (e.g. `[TextContent(type='text', text='{\n "error": ...')]`) in the Web UI with a structured, human-readable rendering of tool activity.

Phase A made tool execution visible. This seed makes it legible.

---

## Current State (Observed)

Tool rows render as raw serialized content blocks:

- Hard to scan
- Leaks internal representation (`TextContent(...)`)
- Obscures actual payload (especially errors)
- Not aligned with mental model of “tool call → result”

---

## Desired Rendering

Tool rows should be:

### 1. Collapsed by default
- Show:
  - tool name
  - success / error status
  - short summary (e.g. “error: forge-bridge client not connected”)

### 2. Expandable
- Click to expand full details

### 3. Structured display
- Pretty-printed JSON for:
  - tool results
  - error payloads
- No raw `TextContent(...)` leakage

### 4. tool_trace-aware
- Optionally render tool_trace alongside messages:
  - index
  - tool_name(arguments)
  - result | error

---

## Why This Matters

Phase A made the system truthful.

This makes it usable.

Without this:
- users see internal serialization artifacts
- debugging is technically possible but cognitively expensive

With this:
- tool execution becomes immediately understandable
- aligns with future Ask / Foundry / Schematic surfaces

---

## Boundaries

In scope:
- Web UI rendering only (forge-chat.js + templates)
- Formatting + interaction (collapse/expand)
- JSON pretty-printing

Out of scope:
- Backend changes
- Contract changes (Phase A already complete)
- Streaming / partial updates
- Tool synthesis UX

---

## Relationship to Phase A

This is **consumer polish on top of a now-correct contract**.

Do NOT modify:
- message structure
- tool_trace structure

Only improve presentation.

---

## When This Activates

Any of:
- v1.5.x polish pass
- Ask dialog work begins (needs readable tool output)
- repeated friction reading tool rows
- demo / external-facing usage

---

## Breadcrumbs

- forge_bridge/console/static/forge-chat.js
- Current rendering of tool rows (search for role === "tool")
- FastMCP TextContent serialization leak
- Phase A ChatTurnResult + tool_trace

---

## Why Plant Now

First live validation of Phase A exposed the gap immediately:

The data is correct, but the presentation is not.

Capturing now ensures the usability issue doesn’t get forgotten while focus shifts to Foundry and Schematic work.
