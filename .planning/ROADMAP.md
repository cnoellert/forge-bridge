# Roadmap: forge-bridge Canonical Package & Learning Pipeline

## Overview

Starting from a working Flame HTTP bridge and MCP server, this milestone builds three additive layers: Flame tool parity with projekt-forge plus a production-ready async LLM router (Phase 1), a rebuilt pluggable MCP server with namespace separation and Pydantic validation (Phase 2), and the full learning pipeline — execution log, skill synthesizer, registry watcher, and probation system — wired into the bridge as an optional callback (Phase 3). Each phase is independently shippable and testable before the next begins. The dependency graph is fixed: synthesizer needs the router, watcher needs the MCP registry, bridge hook needs the log.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Tool Parity & LLM Router** - Bring Flame tools to projekt-forge parity and promote llm_router.py to a production async package (completed 2026-04-15)
- [x] **Phase 2: MCP Server Rebuild** - Rebuild MCP server with pluggable API, namespace separation, and Pydantic validation (completed 2026-04-15)
- [ ] **Phase 3: Learning Pipeline** - Port FlameSavant learning loop — execution log, skill synthesizer, registry watcher, probation system

## Phase Details

### Phase 1: Tool Parity & LLM Router
**Goal**: forge-bridge ships complete Flame tool coverage matching projekt-forge, and llm_router.py is a production-grade async package with optional dependencies
**Depends on**: Nothing (first phase)
**Requirements**: TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05, TOOL-06, TOOL-07, TOOL-08, TOOL-09, LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-08
**Success Criteria** (what must be TRUE):
  1. All Flame operations available in projekt-forge (reconform, switch_grade, disconnect_segments, inspect_sequence_versions, create_version, reconstruct_track, clone_version, replace_segment_media, scan_roles, assign_roles, rename_segments, inspect_batch_xml, prune_batch_xml) are callable as MCP tools
  2. `pip install forge-bridge` installs without openai or anthropic; `pip install forge-bridge[llm]` installs both
  3. `LLMRouter.acomplete()` completes a request asynchronously and returns a string response without blocking the event loop
  4. `forge://llm/health` MCP resource returns which backends (local Ollama, cloud Claude) are available
  5. All MCP tool inputs pass through Pydantic models — invalid inputs are rejected before any Flame code executes
**Plans:** 7/7 plans complete

Plans:
- [x] 01-01-PLAN.md — Fix pyproject.toml, bump bridge timeout, create Wave 0 test scaffolds
- [x] 01-02-PLAN.md — Promote llm_router.py to async forge_bridge/llm/ package
- [x] 01-03-PLAN.md — Add LLM health check and forge://llm/health MCP resource
- [x] 01-04-PLAN.md — Port 8 timeline functions and verify publish.py
- [x] 01-05-PLAN.md — Port batch.py additions, create reconform.py and switch_grade.py
- [x] 01-06-PLAN.md — Verify Pydantic coverage and register all new MCP tools
- [ ] 01-07-PLAN.md — Gap closure: register publish tools, unskip and fix Wave 0 tests

### Phase 2: MCP Server Rebuild
**Goal**: The MCP server has a clean pluggable API, namespace-separated tool registry, and downstream consumers can inject tools via register_tools() without forking server.py
**Depends on**: Phase 1
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06
**Success Criteria** (what must be TRUE):
  1. All existing Flame tools appear under flame_* prefix in the MCP tool list; synthesized slots are reserved under synth_* and cannot be overridden by static registrations
  2. A downstream consumer (e.g. projekt-forge) can call `register_tools(mcp, [fn1, fn2])` before `mcp.run()` and see those tools in the tool list
  3. Every tool in the tool list carries a _source field with value builtin, synthesized, or user-taught
  4. `mcp.add_tool()` / `remove_tool()` successfully registers and deregisters tools at runtime without server restart
**Plans:** 3/3 plans complete

Plans:
- [ ] 02-01-PLAN.md — Create registry.py with namespace enforcement, source tagging, and Wave 0 test scaffolds
- [ ] 02-02-PLAN.md — Rebuild server.py to route all registrations through registry, export public API
- [ ] 02-03-PLAN.md — Create synthesized tool watcher with lifespan integration

### Phase 3: Learning Pipeline
**Goal**: The bridge observes repeated Flame operations, synthesizes them into reusable MCP tools, hot-registers them in the live server, and tracks their reliability via a probation system
**Depends on**: Phase 2
**Requirements**: LEARN-01, LEARN-02, LEARN-03, LEARN-04, LEARN-05, LEARN-06, LEARN-07, LEARN-08, LEARN-09, LEARN-10, LEARN-11
**Success Criteria** (what must be TRUE):
  1. Every Flame execution (when opt-in callback is active) is appended to ~/.forge-bridge/executions.jsonl; the log survives process kill and is fully replayed on restart without re-triggering synthesis for already-promoted hashes
  2. After a code pattern crosses the promotion threshold (default 3), the synthesizer generates a Python async MCP tool, validates it (ast.parse + signature check + dry-run), and writes it to mcp/synthesized/
  3. A newly synthesized tool appears in the MCP tool list under synth_* prefix without a server restart
  4. A synthesized tool that fails probation (breach of failure threshold) is quarantined and removed from the tool list without being deleted from disk
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Tool Parity & LLM Router | 7/7 | Complete   | 2026-04-15 |
| 2. MCP Server Rebuild | 3/3 | Complete   | 2026-04-15 |
| 3. Learning Pipeline | 0/TBD | Not started | - |
