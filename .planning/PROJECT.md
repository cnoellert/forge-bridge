# forge-bridge: Canonical Package & Learning Pipeline

## What This Is

forge-bridge is protocol-agnostic middleware for post-production pipelines — a communication bus with a canonical vocabulary that any endpoint (Flame, Maya, editorial systems, LLM agents) can connect to. As of v1.0, it ships as a standalone pip-installable package with full Flame tool parity (matching projekt-forge), an LLM-powered learning pipeline that auto-promotes repeated operations into reusable MCP tools, and a pluggable MCP server that downstream consumers can extend.

## Current Milestone: v1.1 projekt-forge Integration

**Goal:** Make projekt-forge consume forge-bridge as a pip dependency — replacing duplicated code with imports and wiring the learning pipeline into forge's infrastructure — without breaking either system's existing functionality.

**Target features:**
- Harden forge-bridge's public API surface for external consumption
- Rewire projekt-forge to import from forge-bridge instead of duplicating
- Integrate learning pipeline into projekt-forge (override LLM, enrich prompts, persist to forge DB)

## Core Value

Make forge-bridge the single canonical package (`pip install forge-bridge`) that ships independently with full Flame tool parity, an LLM-powered learning pipeline, and a pluggable MCP server — so projekt-forge can consume it rather than duplicate it.

## Requirements

### Validated

- ✓ HTTP bridge running inside Flame on port 9999, accepting Python code via POST /exec — existing
- ✓ MCP server exposing Flame tools (project, timeline, batch, publish, utility) to LLM agents — existing
- ✓ Canonical vocabulary layer with entities and traits — existing
- ✓ WebSocket server with wire protocol, connection management, and event-driven pub/sub — existing
- ✓ PostgreSQL persistence for entities, relationships, events, and registry — existing
- ✓ Async/sync client pair for connecting to forge-bridge server — existing
- ✓ Flame endpoint that syncs Flame segments to forge-bridge shots bidirectionally — existing
- ✓ Registry system for roles and relationship types with orphan protection — existing
- ✓ Flame tools updated to parity with projekt-forge (reconform, switch_grade, expanded timeline/batch/publish) — v1.0
- ✓ Pydantic models for tool input validation — v1.0
- ✓ LLM router promoted to forge_bridge/llm/ with async API, configurable system prompt, optional deps — v1.0
- ✓ LLM router health check exposed as MCP resource (forge://llm/health) — v1.0
- ✓ MCP server rebuilt with flame_*/forge_* namespace, synthesized tool registration, pluggable tool API — v1.0
- ✓ Pluggable tool registration API (register_tools()) for downstream consumers — v1.0
- ✓ Learning pipeline: execution log with JSONL persistence, replay on startup, intent tracking — v1.0
- ✓ Learning pipeline: skill synthesizer targeting Python MCP tools, using LLM router as backend — v1.0
- ✓ Learning pipeline: registry watcher for dynamic tool registration — v1.0
- ✓ Learning pipeline: probation system for synthesized tools (success/failure tracking, quarantine) — v1.0
- ✓ Learning pipeline wired into bridge.py as optional hook — v1.0
- ✓ Public API surface hardened: 11-name `__all__` barrel, injectable `LLMRouter`, public `startup_bridge`/`shutdown_bridge`, `register_tools()` post-run guard, `pyproject.toml` 1.0.0, PKG-03 grep gate clean — v1.1 (Phase 4)

### Active

- [ ] Rewire projekt-forge to consume forge-bridge as pip dependency
- [ ] Learning pipeline integration in projekt-forge (override LLM, enrich prompts, persist to forge DB)

### Out of Scope

- Forge-specific tools (catalog, orchestrate, scan, seed) — belong in projekt-forge
- Forge-specific CLI, config, database (users/roles/invites), scanner, seeder — belong in projekt-forge
- Authentication — deferred, local-only for now
- Maya endpoint — future work
- Cloud/network scaling — local-first design, swappable later

## Context

- v1.0 shipped: 19,003 LOC Python, 159 tests passing, 66 commits across 3 phases
- forge-bridge is now the canonical standalone package. projekt-forge integration is next.
- FlameSavant learning pipeline successfully ported from JavaScript to Python with improvements (AST normalization, manifest-based file validation, safety blocklist)
- Live-tested end-to-end: Flame execution -> JSONL log -> promotion -> qwen2.5-coder:32b synthesis -> validated MCP tool on disk
- Local LLM (Ollama on assist-01, qwen2.5-coder:32b) confirmed working for synthesis

## Constraints

- **Backward compatibility**: Existing Flame hook and MCP server are deployed and working — don't break them during restructuring
- **Standalone independence**: forge-bridge must work without projekt-forge. No imports from forge-specific modules.
- **Optional dependencies**: LLM packages (openai, anthropic) must be optional extras, not hard requirements
- **Flame runtime**: flame_hooks/ code must use only Python stdlib (runs inside Flame's interpreter)
- **Python 3.10+**: Minimum version, as specified in pyproject.toml

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Phases 1-3 only in this project | Phases 4-5 require changes in projekt-forge repo | ✓ Shipped v1.0 |
| Port FlameSavant learning pipeline from JS to Python | Same concepts, different language — Python matches forge-bridge's ecosystem | ✓ Complete (Phase 3) |
| LLM router in forge_bridge/llm/ | Shared infrastructure for synthesizer and any tool needing generation | ✓ Complete (Phase 1) |
| Optional deps via pyproject.toml extras | Users who don't need LLM features shouldn't install openai/anthropic | ✓ Complete (Phase 1) |
| Synthesizer uses LLM router (not direct API calls) | Single point of control for model selection, sensitivity routing, cost management | ✓ Complete (Phase 3) |
| Namespace-enforcing registry with source tagging | Prevents tool name collisions, enables provenance tracking | ✓ Complete (Phase 2) |
| Manifest-based file validation in watcher | Prevents arbitrary code execution from rogue files in synthesized dir | ✓ Complete (Phase 3, code review fix) |
| Synthesized tools must use bridge.execute(), never import flame | Tools run in MCP server process, not inside Flame — discovered during live testing | ✓ Complete (Phase 3, live test fix) |
| Inject `LLMRouter` config via constructor kwargs with arg→env→default precedence | Downstream consumers (projekt-forge) need deterministic config without env-var side effects | ✓ Complete (Phase 4) |
| `register_tools()` post-run guard + public `startup_bridge`/`shutdown_bridge` | Clear lifecycle contract for pluggable MCP consumers; prevents silent no-op registrations | ✓ Complete (Phase 4) |
| Clean break on API renames (no aliases, no `_module_level_synthesize`) | Pre-1.0 — no external consumers yet, aliases are dead weight | ✓ Complete (Phase 4) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 after Phase 4 (API Surface Hardening) completion*
