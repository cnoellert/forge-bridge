# forge-bridge Separation & Learning Pipeline — Migration Plan

## Context

forge-bridge exists in two places with significant divergence:

- **forge-bridge (standalone)** — the original experiment. Has the vocabulary/entities/traits layer (`core/`), the Flame endpoint/sidecar concept, WebSocket server with wire protocol, PostgreSQL store, and a basic MCP server. Intended as a pip-installable package the community can use without committing to full projekt-forge.
- **projekt-forge/forge_bridge/** — where the real work has gone. Has a full CLI, database with migrations (users, roles, invites), scanner, seed profiles, config system, and more MCP tools (catalog, orchestrate, scan, seed, switch_grade). But it's missing the vocabulary layer that standalone has.

Additionally, **FlameSavant** (Josh's project) has a learning pipeline (ExecutionLog, SkillSynthesizer, RegistryWatcher) that auto-promotes repeated ad-hoc operations into reusable, parameterized skills. This pipeline is worth porting into standalone forge-bridge with improvements.

## Goals

1. Make standalone forge-bridge the canonical package (`pip install forge-bridge`)
2. Bring it to parity with projekt-forge's evolved Flame tools
3. Add an improved learning pipeline (ported from FlameSavant)
4. Make the MCP server pluggable so projekt-forge can extend it
5. Rewire projekt-forge to consume forge-bridge as a dependency (separate project, Phase 4-5)

## What belongs in standalone forge-bridge

- `bridge.py` — HTTP client to Flame
- `client/` — WebSocket client (async + sync)
- `core/` — Vocabulary: entities, traits, roles, timecode
- `flame/` — Flame endpoint + sidecar
- `learning/` — NEW: execution log, synthesizer, registry watcher
- `llm/` — LLM router: sensitivity-based routing between local (Ollama) and cloud (Claude) models
- `mcp/` — MCP server (forge_* + flame_* tools)
- `server/` — WebSocket server, wire protocol, connections
- `store/` — PostgreSQL persistence for vocabulary
- `tools/` — Flame-direct MCP tools (project, timeline, batch, publish, utility, reconform, switch_grade)
- `flame_hooks/` — HTTP bridge running inside Flame

## What stays in projekt-forge (consumes forge-bridge as dependency)

- `cli/` — Forge-specific CLI (auth, installer, launcher, project, scan, seed)
- `config/` — Forge project configuration
- `db/` — Forge database (users, roles, invites, content hashes)
- `scanner/` — Media scanner, role resolver
- `seed/` — Test data seeding
- `server/` — Forge's own server layer (extends bridge server)
- `tools/` — Forge-specific MCP tools (catalog, orchestrate, scan, seed)

## Learning Pipeline Improvements (over FlameSavant)

Ranked by impact:

1. **Replay JSONL on startup** to rebuild counts — patterns currently never promote across sessions (trivial fix, high impact)
2. **Semantic/intent matching** — embed user's natural language request alongside code hash, not just structural code matching (high impact)
3. **Test synthesized tools before registration** — call the generated function with sample params, optionally dry-run on the bridge (high impact)
4. **Post-synthesis feedback loop** — probation period, track success/failure rate, flag for re-synthesis or demotion (medium impact)
5. **AST-level normalization** instead of regex string stripping for code fingerprinting (medium impact)
6. **Parameter diversity and recency weighting** for promotion — require N distinct parameter sets, weight recent executions higher (medium impact)
7. **Connect manual and automatic synthesis paths** to prevent duplicate tool generation (low impact)

Local LLM integration changes the economics — synthesis becomes free, enabling lower promotion thresholds, re-synthesis on failure, and dry-run validation without cost pressure.

## LLM Router

An `llm_router.py` already exists (untracked) that routes LLM requests based on data sensitivity:

- **Sensitive** (shot names, client info, file paths, SQL, openclip XML) → local Ollama on assist-01 (`qwen2.5-coder:32b`)
- **Non-sensitive** (architecture, design reasoning, skill templates) → Anthropic Claude (cloud)

This router belongs in standalone forge-bridge as `forge_bridge/llm/` and serves as the backend for the learning pipeline's synthesizer. It also provides a general-purpose LLM interface for any tool that needs generation.

Improvements needed over the current implementation:
- **Add async API** — the MCP server and bridge are async; the router's `complete()` is currently sync. Add `async def acomplete()` using `httpx.AsyncClient` for local and `anthropic.AsyncAnthropic` for cloud. Keep sync as convenience wrapper.
- **Make optional deps graceful** — `openai` and `anthropic` should be optional extras (`pip install forge-bridge[local]`, `pip install forge-bridge[cloud]`), not hard requirements.
- **Decouple the system prompt** — the hardcoded `FORGE_SYSTEM_PROMPT` with specific hostnames (portofino, assist-01) should be configurable, not baked in. Standalone users will have different infrastructure.
- **Health check as MCP resource** — expose router health (which backends are available) as an MCP resource so Claude can see what's online.

---

## Phase 0: Snapshot and branch

**Both repos:**
- Create branch `separation` from current `main` (forge-bridge)
- Create branch `bridge-dependency` from current `main` (projekt-forge)
- Tag current state as `v0.0.1-pre-separation` for rollback

---

## Phase 1: Bring standalone forge-bridge up to parity

### 1a. Update `forge_bridge/tools/` with projekt-forge's evolved versions

| File | Changes from projekt-forge |
|---|---|
| `tools/project.py` | Pydantic models added |
| `tools/timeline.py` | Significantly expanded — disconnect_segments, inspect_sequence_versions, create_version, reconstruct_track, clone_version, replace_segment_media, scan_roles, assign_roles |
| `tools/batch.py` | Added inspect_batch_xml, prune_batch_xml |
| `tools/publish.py` | Added rename_segments |
| `tools/utility.py` | Pydantic models added |
| `tools/reconform.py` | **New** — add from projekt-forge |
| `tools/switch_grade.py` | **New** — add from projekt-forge |

Do NOT bring: `tools/catalog.py`, `tools/orchestrate.py`, `tools/scan.py`, `tools/seed.py` — forge-specific.

### 1b. Update `bridge.py`

Bump default timeout from 30s to 60s to match projekt-forge.

### 1c. Update `flame_hooks/`

Only bring `forge_http_bridge.py` if it's a standalone improvement. The catalog and LLM clients are forge-specific.

### 1d. Rebuild `forge_bridge/mcp/server.py`

Include new tools from 1a. Keep dual `forge_*` / `flame_*` namespace. Don't bring forge-specific tools.

### 1e. Add Pydantic dependency

Add `pydantic>=2.0.0` to `pyproject.toml`.

### 1f. Promote and clean up the LLM router

The existing `llm_router.py` becomes `forge_bridge/llm/`:

```
forge_bridge/llm/
├── __init__.py       # re-exports LLMRouter, get_router
└── router.py         # cleaned-up router with async support
```

Changes:
- Add `async def acomplete()` alongside sync `complete()` — use `httpx.AsyncClient` for local Ollama, `anthropic.AsyncAnthropic` for cloud
- Extract the hardcoded system prompt and infrastructure hostnames into configuration (env vars are fine, but don't bake in `assist-01` or `portofino`)
- Add optional dependencies in `pyproject.toml`:
  ```toml
  [project.optional-dependencies]
  local = ["openai>=1.0"]
  cloud = ["anthropic>=0.30"]
  all = ["openai>=1.0", "anthropic>=0.30"]
  ```
- Add health check that reports which backends are available

---

## Phase 2: Add the learning pipeline

### 2a. Create `forge_bridge/learning/`

```
forge_bridge/learning/
├── __init__.py
├── execution_log.py    # Port from FlameSavant, improved
├── synthesizer.py      # Port from FlameSavant, adapted for Python MCP tools
└── watcher.py          # Port from FlameSavant, watches tools/ directory
```

### 2b. `execution_log.py`

Port ExecutionLog with improvements:
- JSONL at `~/.forge-bridge/executions.jsonl`
- Replay on startup to rebuild `_counts`
- Log user intent alongside code (optional `intent` param)
- Parameter diversity tracking — require N distinct param sets before promotion
- Recency decay — weight recent executions higher
- Fix multiline string and f-string regex gaps in normalisation

### 2c. `synthesizer.py`

Port SkillSynthesizer targeting Python MCP tools:
- Output: Python files matching existing `tools/*.py` pattern (Pydantic model + async function calling `bridge.execute()`)
- Validation: import generated module, check function signature, call with sample params in dry-run
- Probation tagging: `_synthesized = True` attribute + creation timestamp, track success/failure
- **Uses `LLMRouter` from Phase 1f as its backend** — synthesis prompts are non-sensitive (code templates, skill descriptions) so they route to cloud by default. Users who want everything local can set `sensitive=True`. Local LLM makes synthesis free, enabling lower promotion thresholds and re-synthesis on failure without cost pressure.

### 2d. `watcher.py`

Port RegistryWatcher:
- Watch `forge_bridge/tools/` for new `.py` files
- Import, validate function signature, register with live MCP server
- Emit events: `tool-added`, `tool-updated`, `tool-error`
- Verify FastMCP supports runtime tool registration, or maintain parallel registry

### 2e. Wire into `bridge.py`

Optional hook in `execute()` that calls `execution_log.record()` on success. Off by default, enabled when learning module is imported. Standalone users who don't want learning aren't affected.

---

## Phase 3: Rebuild MCP server as canonical

### 3a. Restructure `mcp/server.py`

- `flame_*` tools: from `forge_bridge/tools/` (direct Flame HTTP bridge)
- `forge_*` tools: from `forge_bridge/core/` queries through WebSocket client (pipeline state)
- Synthesized tools: registered dynamically by watcher
- `flame://project/state` resource for live context
- `forge://llm/health` resource exposing LLM router status (which backends are online)

### 3b. Pluggable tool registration

Expose `register_tools(mcp_server)` function so downstream consumers (projekt-forge) can add their own tools on top of the base set.

---

## Phases 4-5 (separate GSD project in projekt-forge)

### Phase 4: Rewire projekt-forge to consume forge-bridge as dependency

- Add `forge-bridge` to projekt-forge's `pyproject.toml` dependencies
- Rename `forge_bridge/` to `forge_pipeline/` (or similar)
- Update all imports: `from forge_bridge.bridge` stays (now from pip), `from forge_bridge.db` becomes `from forge_pipeline.db`
- Update entry points in `pyproject.toml`
- Remove transitive deps from projekt-forge (httpx, websockets, mcp, sqlalchemy, etc.)

### Phase 5: Learning pipeline + LLM integration in projekt-forge

- Configure LLMRouter with forge-specific system prompt (project context, hostnames, naming conventions)
- Override synthesizer sensitivity routing if needed (e.g., force all synthesis local for client projects)
- Enrich synthesis prompts with forge context (roles, naming conventions, publish paths)
- Optionally persist execution logs to forge database for multi-user visibility
- Wire learning into `flame_execute_python` tool
- Expose LLM router through forge's CLI for pipeline scripting (`forge llm "generate a shot list for..."`)


---

## Execution order and risk

| Phase | Effort | Risk | Ships independently |
|---|---|---|---|
| 0: Snapshot | 10 min | None | N/A |
| 1: Standalone parity | 1 session | Low — additive | Yes |
| 2: Learning pipeline | 2-3 sessions | Medium — new subsystem | Yes |
| 3: MCP server rebuild | 1 session | Medium — architecture change | Yes (test with Claude Desktop) |
| 4: Rewire projekt-forge | 1-2 sessions | **Highest** — bulk rename | No — do in one shot |
| 5: Learning integration | 1 session | Low — additive | Yes |

Phases 1-3 are in standalone forge-bridge and land incrementally. Phase 4 is the big bang — branch, test, merge. Phase 5 is gravy.
