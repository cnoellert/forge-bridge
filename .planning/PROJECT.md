# forge-bridge: Canonical Package & Learning Pipeline

## What This Is

forge-bridge is protocol-agnostic middleware for post-production pipelines — a communication bus with a canonical vocabulary that any endpoint (Flame, Maya, editorial systems, LLM agents) can connect to. This project consolidates the standalone forge-bridge as the canonical pip-installable package, brings it to parity with the evolved tools in projekt-forge, adds a learning pipeline ported from FlameSavant that auto-promotes repeated operations into reusable skills, and makes the MCP server pluggable so projekt-forge can extend it as a downstream dependency.

## Core Value

Make forge-bridge the single canonical package (`pip install forge-bridge`) that ships independently with full Flame tool parity, an LLM-powered learning pipeline, and a pluggable MCP server — so projekt-forge can consume it rather than duplicate it.

## Requirements

### Validated

<!-- Shipped and confirmed valuable — inferred from existing codebase. -->

- ✓ HTTP bridge running inside Flame on port 9999, accepting Python code via POST /exec — existing
- ✓ MCP server exposing Flame tools (project, timeline, batch, publish, utility) to LLM agents — existing
- ✓ Canonical vocabulary layer with entities (Project, Sequence, Shot, Version, Media, Layer, Stack, Asset) and traits (Versionable, Locatable, Relational) — existing
- ✓ WebSocket server with wire protocol, connection management, and event-driven pub/sub — existing
- ✓ PostgreSQL persistence for entities, relationships, events, and registry — existing
- ✓ Async/sync client pair for connecting to forge-bridge server — existing
- ✓ Flame endpoint that syncs Flame segments to forge-bridge shots bidirectionally — existing
- ✓ Registry system for roles and relationship types with orphan protection — existing
- ✓ LLM router with sensitivity-based routing between local Ollama and cloud Claude — existing (llm_router.py, untracked)

### Active

<!-- Current scope. Building toward these. Phases 0-3. -->

- [ ] Flame tools updated to parity with projekt-forge (reconform, switch_grade, expanded timeline/batch/publish)
- [ ] Pydantic models for tool input validation
- [ ] LLM router promoted to forge_bridge/llm/ with async API, configurable system prompt, optional deps
- [ ] LLM router health check exposed as MCP resource
- [x] Learning pipeline: execution log with JSONL persistence, replay on startup, intent tracking — Validated in Phase 3: Learning Pipeline
- [x] Learning pipeline: skill synthesizer targeting Python MCP tools, using LLM router as backend — Validated in Phase 3: Learning Pipeline
- [x] Learning pipeline: registry watcher for dynamic tool registration — Validated in Phase 2: MCP Server Rebuild
- [x] Learning pipeline: probation system for synthesized tools (success/failure tracking) — Validated in Phase 3: Learning Pipeline
- [x] Learning pipeline wired into bridge.py as optional hook — Validated in Phase 3: Learning Pipeline
- [ ] MCP server rebuilt with flame_*/forge_* namespace, synthesized tool registration, pluggable tool API
- [ ] Pluggable tool registration API (register_tools()) for downstream consumers like projekt-forge

### Out of Scope

<!-- Explicit boundaries. Phases 4-5 are a separate project in projekt-forge. -->

- Rewiring projekt-forge to consume forge-bridge as dependency — Phase 4, separate GSD project
- Learning pipeline integration in projekt-forge (override LLM, enrich prompts, persist to forge DB) — Phase 5, separate GSD project
- Forge-specific tools (catalog, orchestrate, scan, seed) — belong in projekt-forge
- Forge-specific CLI, config, database (users/roles/invites), scanner, seeder — belong in projekt-forge
- Authentication — deferred, local-only for now
- Maya endpoint — future work
- Cloud/network scaling — local-first design, swappable later

## Context

- forge-bridge diverged into two codebases: standalone (has vocabulary/WebSocket/store) and projekt-forge (has evolved CLI/tools/DB). This project merges the best of both into standalone.
- FlameSavant (Josh's project, JavaScript) has a learning pipeline (ExecutionLog, SkillSynthesizer, RegistryWatcher) that will be ported to Python with improvements. Source: `/Users/cnoellert/Documents/GitHub/FlameSavant/src/learning/` and `/Users/cnoellert/Documents/GitHub/FlameSavant/src/agents/SkillSynthesizer.js`
- projekt-forge tools to pull from: `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/`
- The existing `llm_router.py` (untracked) has working sensitivity-based routing but needs async support, configurable prompts, and optional dependencies before promotion.
- Local LLM (Ollama on assist-01, qwen2.5-coder:32b) changes economics — synthesis becomes free, enabling lower promotion thresholds and re-synthesis on failure.

## Constraints

- **Backward compatibility**: Existing Flame hook and MCP server are deployed and working — don't break them during restructuring
- **Standalone independence**: forge-bridge must work without projekt-forge. No imports from forge-specific modules.
- **Optional dependencies**: LLM packages (openai, anthropic) must be optional extras, not hard requirements
- **Flame runtime**: flame_hooks/ code must use only Python stdlib (runs inside Flame's interpreter)
- **Python 3.10+**: Minimum version, as specified in pyproject.toml

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Phases 0-3 only in this project | Phases 4-5 require changes in projekt-forge repo | — Pending |
| Port FlameSavant learning pipeline from JS to Python | Same concepts, different language — Python matches forge-bridge's ecosystem | ✓ Complete (Phase 3) |
| LLM router in forge_bridge/llm/ | Shared infrastructure for synthesizer and any tool needing generation | — Pending |
| Optional deps via pyproject.toml extras | Users who don't need LLM features shouldn't install openai/anthropic | — Pending |
| Synthesizer uses LLM router (not direct API calls) | Single point of control for model selection, sensitivity routing, cost management | ✓ Complete (Phase 3) |

---
*Last updated: 2026-04-15 after Phase 3 completion*
