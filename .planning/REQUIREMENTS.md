# Requirements: forge-bridge v1.1

**Defined:** 2026-04-15
**Core Value:** Make forge-bridge the single canonical package (`pip install forge-bridge`) that ships independently with full Flame tool parity, an LLM-powered learning pipeline, and a pluggable MCP server — so projekt-forge can consume it rather than duplicate it.

## v1.1 Requirements

Requirements for projekt-forge integration. Each maps to roadmap phases.

### API Surface

- [ ] **API-01**: forge-bridge declares `__all__` in `__init__.py` with all public symbols re-exported from package root
- [ ] **API-02**: `LLMRouter` accepts constructor injection for `local_url`, `local_model`, and `system_prompt` with env-var fallback
- [ ] **API-03**: `SkillSynthesizer` accepts an optional `router=` parameter to use a pre-configured LLMRouter
- [ ] **API-04**: `startup_bridge()` and `shutdown_bridge()` are public functions in `mcp/server.py`
- [ ] **API-05**: `register_tools()` raises `RuntimeError` if called after `mcp.run()` via `_server_started` guard

### Registry & Packaging

- [ ] **PKG-01**: `register_tools()` accepts `source="builtin"` from downstream consumers for `forge_*` prefixed tools
- [ ] **PKG-02**: forge-bridge `pyproject.toml` version bumped to `1.0.0`
- [ ] **PKG-03**: forge-specific content (`portofino`, `assist-01`, `ACM_`) purged from `_DEFAULT_SYSTEM_PROMPT` in router.py

### Import Rewiring

- [x] **RWR-01**: projekt-forge adds `forge-bridge>=1.0,<2.0` to `pyproject.toml` dependencies
- [x] **RWR-02**: Duplicated tool modules (`bridge.py`, `tools/*.py`) deleted from projekt-forge in same commit as pip dep addition
- [x] **RWR-03**: projekt-forge's forge-specific tools (catalog, orchestrate, scan, seed) registered via `register_tools()`
- [x] **RWR-04**: `forge_bridge.__file__` resolves to site-packages (not local directory) verified in CI

### Learning Pipeline

- [ ] **LRN-01**: `ExecutionLog` path is configurable at construction (no hardcoded `~/.forge-bridge/executions.jsonl`)
- [ ] **LRN-02**: projekt-forge startup calls `set_execution_callback()` with its own storage callback
- [ ] **LRN-03**: projekt-forge constructs `LLMRouter` with forge config values and injects into Synthesizer
- [ ] **LRN-04**: `SkillSynthesizer` supports a `pre_synthesis_hook` for prompt enrichment from projekt-forge's DB context

## Future Requirements

### Extended Integration

- **EXT-01**: Shared synthesis manifest between repos
- **EXT-02**: Tool provenance in MCP annotations
- **EXT-03**: SQL persistence backend for ExecutionLog via `typing.Protocol` and separate Alembic chain

## Out of Scope

| Feature | Reason |
|---------|--------|
| Authentication | Deferred — local-only deployment |
| Maya endpoint | Future work, not related to this milestone |
| PyPI publishing | Git-tag or editable install during v1.1; PyPI decision deferred |
| Cloud/network scaling | Local-first design, swappable later |
| Forge-specific tools in forge-bridge | catalog, orchestrate, scan, seed belong in projekt-forge |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| API-01 | Phase 4 | Pending |
| API-02 | Phase 4 | Pending |
| API-03 | Phase 4 | Pending |
| API-04 | Phase 4 | Pending |
| API-05 | Phase 4 | Pending |
| PKG-01 | Phase 4 | Pending |
| PKG-02 | Phase 4 | Pending |
| PKG-03 | Phase 4 | Pending |
| RWR-01 | Phase 5 | Complete |
| RWR-02 | Phase 5 | Complete |
| RWR-03 | Phase 5 | Complete |
| RWR-04 | Phase 5 | Complete |
| LRN-01 | Phase 6 | Pending |
| LRN-02 | Phase 6 | Pending |
| LRN-03 | Phase 6 | Pending |
| LRN-04 | Phase 6 | Pending |

**Coverage:**
- v1.1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 after roadmap creation*
