---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: projekt-forge Integration
status: defining
stopped_at: null
last_updated: "2026-04-15"
last_activity: 2026-04-15
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Make forge-bridge the single canonical package (pip install forge-bridge) with full Flame tool parity, an LLM-powered learning pipeline, and a pluggable MCP server
**Current focus:** Defining requirements for v1.1

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-15 — Milestone v1.1 started

## Performance Metrics

**Velocity:**

- Total plans completed: 6
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3 | - | - |
| 03 | 3 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-tool-parity-llm-router P02 | 2min | 2 tasks | 3 files |
| Phase 01-tool-parity-llm-router P01 | 2m | 2 tasks | 5 files |
| Phase 01 P04 | 3m | 2 tasks | 2 files |
| Phase 01 P05 | 275 | 2 tasks | 8 files |
| Phase 01-tool-parity-llm-router P03 | 5 | 2 tasks | 3 files |
| Phase 01-tool-parity-llm-router P06 | 2min | 2 tasks | 2 files |
| Phase 01-tool-parity-llm-router P07 | 155s | 2 tasks | 3 files |
| Phase 02-mcp-server-rebuild P01 | 2min | 2 tasks | 3 files |
| Phase 02-mcp-server-rebuild P03 | 2min | 2 tasks | 4 files |
| Phase 02-mcp-server-rebuild P02 | 8min | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Phases 0-3 only in this project (Phases 4-5 require projekt-forge repo changes)
- LLM router in forge_bridge/llm/ as shared infrastructure for synthesizer and any tool needing generation
- Optional deps via pyproject.toml extras — base install stays lean, [llm] adds openai/anthropic
- Synthesizer uses LLM router with sensitive=True (always routes to local Ollama, never sends production code to cloud)
- [Phase 01-tool-parity-llm-router]: acomplete() is the primary LLM API; sync complete() is for non-async callers only (asyncio.run())
- [Phase 01-tool-parity-llm-router]: Lazy imports inside _get_local_client()/_get_cloud_client() so base install works without openai/anthropic
- [Phase 01-tool-parity-llm-router]: FORGE_SYSTEM_PROMPT env var added to make VFX system prompt configurable
- [Phase 01-tool-parity-llm-router]: openai and anthropic moved to [llm] optional extra; base pip install stays lean
- [Phase 01-tool-parity-llm-router]: BRIDGE_TIMEOUT default raised from 30s to 60s to handle longer Flame operations
- [Phase 01-tool-parity-llm-router]: Wave 0 stub pattern established: skipped tests as living documentation of what each plan must implement
- [Phase 01]: publish.py rename_segments verified identical to projekt-forge; no logic changes needed
- [Phase 01]: 8 timeline functions ported from projekt-forge using 'from forge_mcp import bridge' import pattern
- [Phase 01]: inspect_batch_xml and prune_batch_xml stubbed with RuntimeError — forge_batch_xml/forge_batch_prune scripts not in standalone repo
- [Phase 01]: query_alternatives stubbed with JSON error — catalog WebSocket is projekt-forge infrastructure, not standalone
- [Phase 01]: Fixed broken from forge_mcp import bridge across all tool files — forge_mcp does not exist in standalone repo
- [Phase 01-tool-parity-llm-router]: register_llm_resources(mcp) follows module-level registration pattern — called once before main()
- [Phase 01-tool-parity-llm-router]: get_router() lazy-imported inside async resource handler to avoid circular imports
- [Phase 01-tool-parity-llm-router]: Active MCP server is forge_bridge/mcp/server.py not forge_bridge/server.py — new tool registrations target the active server
- [Phase 01-tool-parity-llm-router]: forge_bridge/__main__.py fixed from broken forge_mcp import to forge_bridge.mcp.server
- [Phase 01-tool-parity-llm-router]: test_pydantic_coverage filters imported functions using fn.__module__ check and resolves string annotations via typing.get_type_hints()
- [Phase 02-mcp-server-rebuild]: register_builtins() is a stub in Plan 01 — filled when server.py is rebuilt in Plan 02
- [Phase 02-mcp-server-rebuild]: meta={'_source': source} is the source tagging mechanism for MCP tools — surfaced in tools/list response
- [Phase 02-mcp-server-rebuild]: synth_ prefix exclusively reserved for source='synthesized' — ValueError raised for all other sources
- [Phase 02-mcp-server-rebuild]: SHA-256 polling (5s interval) chosen over filesystem events — no platform-specific dependencies, consistent cross-platform behavior
- [Phase 02-mcp-server-rebuild]: watcher.py imports register_tool inline inside _scan_once() to avoid circular import at module load time
- [Phase 02-mcp-server-rebuild]: _lifespan defined before mcp = FastMCP() — Python resolves _startup/_shutdown at call time not definition time
- [Phase 02-mcp-server-rebuild]: register_builtins() is now fully populated — all ~42 builtin tools route through registry with source='builtin'; server.py has zero direct mcp.tool() calls
- [Phase 02-mcp-server-rebuild]: forge_bridge.mcp public API: register_tools and get_mcp importable from package __init__ for downstream consumers

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2: FastMCP tools/list_changed notification behaviour for hot-registered tools is confirmed at protocol level but unverified in installed FastMCP implementation — check during Phase 2 planning
- Phase 3: Probation human review gate for write-side synthesized tools needs a concrete implementation decision before Phase 3 planning (approval MCP tool vs. log-only gate vs. UI notification)

## Session Continuity

Last session: 2026-04-15T03:14:22.394Z
Stopped at: Completed 02-02-PLAN.md
Resume file: None
