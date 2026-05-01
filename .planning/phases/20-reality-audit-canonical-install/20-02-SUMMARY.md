---
phase: 20
plan: "02"
subsystem: docs
tags: [claude-md, ground-truth, docs-refresh, context-recovery]
dependency_graph:
  requires: [20-01]
  provides: [DOCS-02, claude-md-v1.4.1-ground-truth]
  affects: [CLAUDE.md]
tech_stack:
  added: []
  patterns: [surgical-edit, preserve-verbatim-sections]
key_files:
  created: []
  modified:
    - CLAUDE.md
decisions:
  - "Four sections rewritten in place; six sections preserved verbatim — no structural restructuring (Phase 21 territory per D-12)"
  - "Vocabulary layer correctly reclassified as SHIPPED (was erroneously in 'not yet implemented' list since v1.0 snapshot)"
  - "forge_bridge/server.py flagged as pre-Phase-5 orphan distinct from forge_bridge/mcp/server.py (the canonical MCP server)"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-30"
  tasks: 1
  files: 1
requirements: [DOCS-02]
---

# Phase 20 Plan 02: CLAUDE.md Ground-Truth Refresh (DOCS-02) Summary

Rewrote four stale sections of `CLAUDE.md` to reflect v1.4.1 reality. The file had been anchored to the 2026-02-24 "just extracted from projekt-forge" snapshot across 19 phases and 6 milestones of development.

## What Was Built

Four surgical edits to `CLAUDE.md`, six sections preserved verbatim. The file grew from 164 lines to 238 lines (+74 net), gaining accurate coverage of all 5 surfaces, all major subsystems, the corrected "not yet implemented" list, the actual directory layout, and the v1.5 milestone context.

## Commits Landed

| Commit | Message | Files |
|--------|---------|-------|
| `102bd40` | `docs(20): refresh CLAUDE.md to v1.4.1 ground truth (DOCS-02)` | `CLAUDE.md` |

## Diff Summary

### Sections rewritten

| Section | Before | After |
|---------|--------|-------|
| `## Current State` | Listed only 2 surfaces: Flame bridge + MCP server; vocab listed as "not yet implemented" | 5 surfaces enumerated by canonical file path + port; 8 subsystems listed; vocab correctly marked as SHIPPED |
| `## Repository Layout` | v1.0 layout: `server.py`, `tools/` only; 6 major dirs missing | v1.4.1 layout: `cli/`, `client/`, `console/`, `core/`, `flame/`, `learning/`, `llm/`, `mcp/`, `server/`, `store/`, `tools/`; `server.py` orphan flagged |
| `## How to Get Running` | `pip install -e .`; manual `cp` of hook; `--http --port 8080` (stale flag); no conda, no alembic | `pip install -e ".[dev,llm]"`; `./scripts/install-flame-hook.sh`; conda env step; alembic migration step; stdin-keepalive note; `:9996/ui/` + `:9999/status` smoke tests; `forge doctor` |
| `## Active Development Context` | "As of 2026-02-24: Just extracted from projekt-forge" | "Milestone: v1.5 Legibility (opened 2026-04-30)"; all four v1.5 phases described; v1.5 constraints documented |

### Sections preserved verbatim

- `# CLAUDE.md — forge-bridge Context Recovery` (header + intro)
- `## What is this project?`
- `## Key Design Decisions (brief version)`
- `## Vocabulary Summary`
- `## Relationship to projekt-forge`
- `## Questions To Come Back To`

## All 5 Surfaces Enumerated by Canonical Path + Port

| Surface | Canonical Path | Port | Smoke Test |
|---------|---------------|------|------------|
| Flame HTTP bridge | `flame_hooks/forge_bridge/scripts/forge_bridge.py` | `:9999` | `curl -s http://localhost:9999/status` |
| MCP server | `forge_bridge/mcp/server.py` | stdio | `python -m forge_bridge` |
| Artist Console / Web UI | `forge_bridge/console/app.py` | `:9996/ui/` | `curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"` |
| CLI `forge-bridge` | `forge_bridge/__main__.py` + `forge_bridge/cli/` | n/a | `forge-bridge console doctor` |
| Chat endpoint | `forge_bridge/console/handlers.py:chat_handler` | `:9996/api/v1/chat` | `curl -s -X POST http://localhost:9996/api/v1/chat ...` |

## Verification Grep Results

All automated verification checks passed at commit time:

| Check | Result |
|-------|--------|
| `grep -q '## Current State' CLAUDE.md` | PASS |
| `grep -q ':9996/ui/' CLAUDE.md` | PASS |
| `grep -q '/api/v1/chat' CLAUDE.md` | PASS |
| `grep -q 'forge-bridge console doctor' CLAUDE.md` | PASS |
| `grep -q 'flame_hooks/forge_bridge/scripts/forge_bridge.py' CLAUDE.md` | PASS |
| `grep -q 'python -m forge_bridge' CLAUDE.md` | PASS |
| `grep -q 'v1.5 Legibility' CLAUDE.md` | PASS |
| `grep -q 'Phase 20' CLAUDE.md` | PASS |
| `grep -q 'forge_bridge/core/' CLAUDE.md` | PASS |
| `grep -c 'As of 2026-02-24' CLAUDE.md` returns 0 | PASS |
| `grep -c 'Just extracted from projekt-forge' CLAUDE.md` returns 0 | PASS |
| `grep -c 'python -m forge_bridge --http --port 8080' CLAUDE.md` returns 0 | PASS |
| `grep -c 'pip install -e \.$' CLAUDE.md` returns 0 | PASS |
| `grep -q '\[dev,llm\]' CLAUDE.md` | PASS |
| `grep -q 'tail -f /dev/null | python -m forge_bridge' CLAUDE.md` | PASS |
| All six preserve-verbatim sections present | PASS |

## Test Results

**Quick suite** (`pytest tests/test_public_api.py tests/test_install_hook_version_consistency.py -x`):
- 21 passed, 0 failed

## Discoveries During Rewrite

### Subsystems/surfaces confirmed but not in the original CLAUDE.md surface list

All of the following were verified in source during the rewrite and are now documented:
- Staged operations platform (`forge_bridge/store/staged_operation.py` + MCP wiring)
- LLM router (`forge_bridge/llm/router.py`) with `sensitive` routing
- Learning pipeline (`forge_bridge/learning/`) with probation/quarantine system
- Tool provenance via `_meta.forge-bridge/*` fields and `_sanitize_patterns.py`
- WebSocket server (`forge_bridge/server/`) on `:9998` with graceful-degradation

### Drift in preserved sections (Phase 21 candidates)

The "Key Design Decisions" table contains "Automatic dependency graph — No manual declaration — Infer from data structure" — the dep-graph traversal engine is not shipped. The decision is architecturally correct (it describes the design intent) but could mislead an AI reading it as a description of what exists today. Logged as a Phase 21 refinement candidate — the table is described as "Key Design Decisions" (intent) not "What is shipped" (inventory), so the current wording is directionally acceptable.

## Deviations from Plan

None — plan executed exactly as written. All four edits landed in a single task as specified. All six preserve-verbatim sections confirmed intact.

## Known Stubs

None. All changes are factual rewrites reflecting v1.4.1 codebase reality.

## Threat Flags

No new security surface introduced. This plan modifies only `CLAUDE.md` — a documentation file already in the public repository. Per threat register T-20-04: accept (LOW). T-20-05 mitigation: all five surfaces are now enumerated by canonical file path + port; the verify-step grep gates confirm each surface is present.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `CLAUDE.md` exists | FOUND |
| `CLAUDE.md` line count >= 150 | FOUND (238 lines) |
| `CLAUDE.md` contains "v1.5 Legibility" | FOUND |
| `CLAUDE.md` contains ":9996/ui/" | FOUND |
| `CLAUDE.md` contains "/api/v1/chat" | FOUND |
| `CLAUDE.md` contains "forge_bridge/core/" | FOUND |
| `CLAUDE.md` does NOT contain "As of 2026-02-24" | CONFIRMED ABSENT |
| `CLAUDE.md` does NOT contain "Just extracted from projekt-forge" | CONFIRMED ABSENT |
| Commit `102bd40` exists | FOUND |
| 20-02-SUMMARY.md committed | PENDING (final commit) |
