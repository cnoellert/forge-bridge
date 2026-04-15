# Requirements: forge-bridge Canonical Package & Learning Pipeline

**Defined:** 2026-04-14
**Core Value:** Make forge-bridge the single canonical package (pip install forge-bridge) that ships independently with full Flame tool parity, an LLM-powered learning pipeline, and a pluggable MCP server.

## v1 Requirements

Requirements for this milestone (Phases 0-3). Each maps to roadmap phases.

### Flame Tool Parity

- [x] **TOOL-01**: Update tools/timeline.py with projekt-forge's expanded version (disconnect_segments, inspect_sequence_versions, create_version, reconstruct_track, clone_version, replace_segment_media, scan_roles, assign_roles)
- [x] **TOOL-02**: Update tools/batch.py with projekt-forge additions (inspect_batch_xml, prune_batch_xml)
- [x] **TOOL-03**: Update tools/publish.py with projekt-forge additions (rename_segments)
- [x] **TOOL-04**: Update tools/project.py with Pydantic models from projekt-forge
- [x] **TOOL-05**: Update tools/utility.py with Pydantic models from projekt-forge
- [x] **TOOL-06**: Add tools/reconform.py from projekt-forge
- [x] **TOOL-07**: Add tools/switch_grade.py from projekt-forge
- [x] **TOOL-08**: Add Pydantic input models for all existing and new MCP tools
- [x] **TOOL-09**: Bump bridge.py default timeout from 30s to 60s

### LLM Router

- [x] **LLM-01**: Promote llm_router.py to forge_bridge/llm/ package with router.py
- [x] **LLM-02**: Add async acomplete() using AsyncOpenAI for local Ollama and AsyncAnthropic for cloud Claude
- [x] **LLM-03**: Keep sync complete() as convenience wrapper
- [x] **LLM-04**: Extract hardcoded system prompt and infrastructure hostnames (assist-01, portofino) into configuration (env vars)
- [x] **LLM-05**: Move openai and anthropic to optional dependencies in pyproject.toml (pip install forge-bridge[llm])
- [x] **LLM-06**: Add health check reporting which backends are available (async and sync)
- [x] **LLM-07**: Expose LLM health check as MCP resource (forge://llm/health)
- [x] **LLM-08**: Fix duplicate dependency declarations in pyproject.toml

### Learning Pipeline

- [ ] **LEARN-01**: Create forge_bridge/learning/ package with execution_log.py
- [ ] **LEARN-02**: JSONL execution log at ~/.forge-bridge/executions.jsonl with append-only writes
- [ ] **LEARN-03**: Replay JSONL on startup to rebuild in-memory promotion counters
- [ ] **LEARN-04**: AST-based code normalization (ast.unparse with literal stripping) and SHA-256 hash fingerprinting
- [ ] **LEARN-05**: Promotion threshold counter (configurable, default 3) returning promoted=True signal
- [ ] **LEARN-06**: Intent tracking — optional intent string logged alongside code for synthesis prompt enrichment
- [ ] **LEARN-07**: Create forge_bridge/learning/synthesizer.py targeting Python MCP tools
- [ ] **LEARN-08**: Synthesizer uses LLM router as backend with sensitive=True (always local, production code in prompts)
- [ ] **LEARN-09**: Synthesized tool validation: ast.parse, function signature check, sample parameter dry-run
- [ ] **LEARN-10**: Probation system: success/failure counters per synthesized tool, quarantine on threshold breach
- [ ] **LEARN-11**: Wire execution logging into bridge.py as optional on_execution callback (off by default)

### MCP Server & Pluggability

- [ ] **MCP-01**: Rebuild mcp/server.py with flame_*/forge_*/synth_* namespace separation
- [ ] **MCP-02**: Dynamic tool registration using FastMCP add_tool()/remove_tool() for synthesized tools
- [ ] **MCP-03**: Create forge_bridge/learning/watcher.py — asyncio polling on mcp/synthesized/, importlib hot-load
- [ ] **MCP-04**: Expose register_tools(mcp) pluggable API for downstream consumers (projekt-forge)
- [ ] **MCP-05**: Source tagging on all tools (_source: builtin/synthesized/user-taught) visible to LLM agents
- [ ] **MCP-06**: Synthesized tools use synth_* prefix, enforced at synthesis time against reserved name set

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Learning Pipeline Enhancements

- **LEARN-V2-01**: Re-synthesis on failure — regenerate using failure trace when probation fails
- **LEARN-V2-02**: User-taught skill path — forge_save_skill(name, description, code) MCP tool
- **LEARN-V2-03**: Parameter diversity tracking — require N distinct parameter sets before promotion
- **LEARN-V2-04**: Recency decay — weight recent executions higher in promotion scoring

### projekt-forge Integration (Separate GSD Project)

- **FORGE-01**: Rewire projekt-forge to consume forge-bridge as pip dependency
- **FORGE-02**: Configure LLM router with forge-specific system prompt and hostnames
- **FORGE-03**: Persist execution logs to forge database for multi-user visibility
- **FORGE-04**: Expose LLM router through forge CLI

## Out of Scope

| Feature | Reason |
|---------|--------|
| Forge-specific tools (catalog, orchestrate, scan, seed) | Belong in projekt-forge, not forge-bridge |
| Forge CLI, config, database (users/roles/invites) | Belong in projekt-forge |
| Authentication | Deferred — local-only for now, framework exists |
| Maya endpoint | Future work, not part of this milestone |
| Cloud/network scaling | Local-first design, swappable later |
| Execution log in PostgreSQL | JSONL is simpler, proven, no migration burden |
| Sandboxed Python execution of synthesized tools | Complex, breaks Flame API access; use validation + probation instead |
| Auto-purge of synthesized skills | Risk losing captured knowledge; quarantine instead |
| Real-time chat/video posts | Not applicable to this domain |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TOOL-01 | Phase 1 | Complete |
| TOOL-02 | Phase 1 | Complete |
| TOOL-03 | Phase 1 | Complete |
| TOOL-04 | Phase 1 | Complete |
| TOOL-05 | Phase 1 | Complete |
| TOOL-06 | Phase 1 | Complete |
| TOOL-07 | Phase 1 | Complete |
| TOOL-08 | Phase 1 | Complete |
| TOOL-09 | Phase 1 | Complete |
| LLM-01 | Phase 1 | Complete |
| LLM-02 | Phase 1 | Complete |
| LLM-03 | Phase 1 | Complete |
| LLM-04 | Phase 1 | Complete |
| LLM-05 | Phase 1 | Complete |
| LLM-06 | Phase 1 | Complete |
| LLM-07 | Phase 1 | Complete |
| LLM-08 | Phase 1 | Complete |
| LEARN-01 | Phase 3 | Pending |
| LEARN-02 | Phase 3 | Pending |
| LEARN-03 | Phase 3 | Pending |
| LEARN-04 | Phase 3 | Pending |
| LEARN-05 | Phase 3 | Pending |
| LEARN-06 | Phase 3 | Pending |
| LEARN-07 | Phase 3 | Pending |
| LEARN-08 | Phase 3 | Pending |
| LEARN-09 | Phase 3 | Pending |
| LEARN-10 | Phase 3 | Pending |
| LEARN-11 | Phase 3 | Pending |
| MCP-01 | Phase 2 | Pending |
| MCP-02 | Phase 2 | Pending |
| MCP-03 | Phase 2 | Pending |
| MCP-04 | Phase 2 | Pending |
| MCP-05 | Phase 2 | Pending |
| MCP-06 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0

---
*Requirements defined: 2026-04-14*
*Last updated: 2026-04-14 after roadmap creation*
