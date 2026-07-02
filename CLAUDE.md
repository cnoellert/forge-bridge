# CLAUDE.md — forge-bridge Context Recovery

This file exists to get an AI assistant (Claude or otherwise) back up to speed on this project quickly when context is lost between sessions. Read this first, then read the docs in order listed below.

---

## What is this project?

forge-bridge is **middleware** — a protocol-agnostic communication bus for post-production pipelines. Any piece of software (Flame, Maya, editorial systems, shot tracking, AI models, custom scripts) can connect to it and communicate through a shared canonical vocabulary.

It is NOT a Flame utility. Flame is one endpoint. Everything is another.

The core ideas:
1. **Canonical vocabulary** — bridge speaks a defined language. Every connected system maps its native terms to this language. See `docs/VOCABULARY.md`.
2. **Automatic dependency graph** — as data flows through bridge, it parses relationships and builds a dependency graph. No manual declaration needed. Change propagation is automatic.
3. **Endpoint parity** — Flame, Maya, an LLM, a shot tracking system are all equal endpoints. Bridge does not prefer any of them.
4. **Local first** — starts as a local service, designed to scale later without architecture changes.

---

## Current State

Shipped at tag `v1.8.2` (2026-06-25); `pyproject.toml` version is `1.8.2`. The 19 symbols in `forge_bridge.__all__` have stayed byte-stable since the v1.4.1 baseline — five milestones of behavior (v1.5 → v1.9) deepened the runtime without expanding the public surface. Shipped since v1.4.1:

- **v1.5 Legibility** — reader docs (INSTALL.md, GETTING-STARTED.md, RECIPES.md, TROUBLESHOOTING.md).
- **v1.6 Operability** — graph-native operational runtime (`graph_store` JSONL append log, `fbridge flame-exec`, `fbridge graph list/show`), doctor observability (`postgres` + `graph_store` rows, daemon-routed Flame probe, `ollama-turn` / `ollama-compile` log lines), chat-layer convergence (default model `qwen2.5-coder:32b → :14b`, SSE streaming, K=2 orchestrator termination).
- **v1.7 Artist Readiness** — the authority chain end-to-end: NL → `compile_intent()` → `preview_emitted` → `AssentRecord` → `fbridge ratify` / `POST /api/v1/ratify` → store-and-replay apply.
- **v1.8 Console Authority** — CA.1 projected the ratify chain onto the Web UI (preview render + ratify affordance + the de-blank guard); CA.2/CA.3 unopened.
- **v1.9 Conversational Reads (ACTIVE)** — CR.1 landed: a `(b)` terminal-synthesis answer-pass at the `chain_complete` read seam (`acomplete`, local Ollama), so reads answer humans in plain language. Reads-only by structure; mutations stay deterministic preview+ratify. The author-driven dogfood (spike-1 comprehension corpus) is pending the projekt-forge v1.5.1 re-pin + `013_13_13` re-publish; non-developer UAT is an explicit carry-forward.

`.planning/STATE.md` is frozen archaeology (stopped at Phase 24.4); current continuity is distributed across milestone/phase docs, `.planning/JOURNAL.md`, `.planning/CONTINUITY-MAP.md`, and git history — there is no single live cursor (see CONTINUITY-MAP.md).

### What exists and works

**Five user-facing surfaces, all live:**

1. **Flame HTTP bridge** (`flame_hooks/forge_bridge/scripts/forge_bridge.py`)
   - Runs inside Flame as an HTTP server on port 9999
   - Accepts Python code via `POST /exec`, executes on Flame's main thread via `schedule_idle_event`
   - Returns `{result, stdout, stderr, error, traceback}` as JSON
   - Has an interactive web UI at `http://localhost:9999/`
   - Persistent namespace across requests
   - Installed via `./scripts/install-flame-hook.sh`

2. **MCP server** (`forge_bridge/mcp/server.py`)
   - Model Context Protocol server (FastMCP, streamable-HTTP for daemon mode, stdio for Claude Desktop / Code)
   - Daily launch: `fbridge up` (managed background daemon — starts `mcp_http` with co-hosted Console on `:9996` + `state_ws` on `:9998` in dependency order) or `fbridge mcp http` (direct foreground). For supervised systemd / launchd, `sudo ./scripts/install-bootstrap.sh`.
   - Claude Desktop / stdio MCP clients: `fbridge mcp stdio` (or `python -m forge_bridge mcp stdio`).
   - **Bare `python -m forge_bridge` now prints help and exits 0** — it does NOT start any services. Use the `mcp stdio` / `mcp http` subcommands.
   - Co-hosts the Artist Console + chat endpoint on `:9996` via lifespan
   - Tools: project, timeline, batch, publish, utility — plus staged-ops tools (`forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged`), manifest tools (`forge_manifest_read`, `forge_tools_read`), and any LLM-synthesized tools registered by the learning pipeline
   - Resources: `forge://manifest/synthesis`, `forge://staged/pending`, `forge://llm/health`

3. **Artist Console / Web UI** (`forge_bridge/console/app.py`) — Phase 10/10.1
   - Mount: `http://localhost:9996/ui/`
   - Five views: tools, execs, manifest, health, chat
   - Jinja2 + vendored htmx + Alpine.js with SRI; zero JS build step
   - LOGIK-PROJEKT amber-on-dark palette (UI-SPEC.md design contract)
   - Co-hosted with the MCP server on `:9996` via lifespan (NOT FastMCP `custom_route`)

4. **CLI `fbridge` / `forge-bridge`** (`forge_bridge/cli/main.py` is the Typer front door; `__main__.py` is a thin delegate to it) — Phase 11, expanded through v1.4.x + v1.7 Thread A
   - Both `fbridge` (canonical short name) and `forge-bridge` (back-compat alias) resolve to `forge_bridge.cli.main:app` (see `pyproject.toml` `[project.scripts]`)
   - Typer + Rich, sync `httpx` consumer of the `:9996` Read API for read commands; direct calls to the runtime manager / chain engine for write commands
   - Top-level subcommands: `doctor` (runtime doctor — covers Console, MCP, Flame, State WS, **`postgres`** (Phase 23), **`graph_store`** (Phase 24); Flame probe is **daemon-routed** via `POST :9996/api/v1/exec text="flame_ping"` since Phase 24.2), `actions` (browse registered tools), `chat` (exercise the chat endpoint), `exec` (deterministic chain engine via `/api/v1/exec`, no LLM), `run` (execute a registered tool by exact name), **`flame-exec`** (Phase 24 — operator surface onto `_execute_python_core` shared body; same dispatch substrate as the LLM tool-call path; emits `graph_id`), **`graph list / graph show`** (Phase 24 — read-only debug CLI over the JSONL graph store at `~/.forge-bridge/graphs/`), **`discover`** (v1.7 Thread B — substrate-derived vocabulary browser), **`ratify`** (v1.7 Thread A A.2 — ratify and apply a previewed graph-intent), `up` / `down` / `status` (managed background daemon lifecycle)
   - Subgroups: `console` (legacy Phase-11 Read API browser: `tools | execs | manifest | health | doctor`), `mcp` (`stdio | http`), `flame` (`ping`)
   - `--json` short-circuits Rich on every command (P-01 stdout purity)
   - Locked exit codes: 0=ok, 1=fail, 2=unreachable (`flame-exec` adds 1=Flame-error, 2=transport)

5. **Chat endpoint** (`forge_bridge/console/handlers.py:chat_handler`) — Phase 16/16.1/16.2 + v1.7 Thread A
   - `POST http://localhost:9996/api/v1/chat`
   - Chat now compiles before it executes: `LLMRouter.compile_intent()` produces validated chain-step text; non-mutating chains run immediately; mutating chains emit a preview and `graph_intent_id` for ratification.
   - `sensitive=True` hardcoded → routes through local Ollama (default model **`qwen2.5-coder:14b`** — bumped from `32b` in Phase 24.3 per measure-first canonical baseline); `ANTHROPIC_API_KEY` not required for chat
   - **Transport:** JSON response by default; SSE when client sends `Accept: text/event-stream`
   - **Terminal SSE event taxa:** `chain_complete`, `preview_emitted`, `apply_complete`, `chain_aborted`, `compile_error`, plus `error` for transport/runtime failures. `compile_complete` is an intermediate SSE event.
   - `POST /api/v1/ratify` backs `fbridge ratify <graph_intent_id>`: proposed `AssentRecord` → ratified → replay persisted chain → applied/failed.
   - Rate limit: 10 req/60s (IP-keyed; SEED-AUTH-V1.5 plants caller-identity migration)
   - Outer wall-clock 125s (FB-C 120s inner + 5s framing buffer)

**Subsystems behind the surfaces:**

- **Canonical vocabulary layer** (`forge_bridge/core/`) — `vocabulary.py`, `entities.py`, `traits.py`, `registry.py`. Project → Sequence → Shot → Version → Media + Stack/Layer/Asset, plus Versionable/Locatable/Relational traits. **Shipped** (was on the "not yet implemented" list in v1.0; corrected here).
- **WebSocket server** (`forge_bridge/server/`) — wire protocol, connection management, event-driven hooks. Standalone WS server on `:9998` (graceful degradation if unreachable per Phase 07.1).
- **Postgres persistence layer** (`forge_bridge/store/` + Alembic migrations in `forge_bridge/store/migrations/`) — entities, relationships, events, registry, the `staged_operation` table from FB-A, and the `assent_record` entity type from A.2.
- **Async/sync client pair** (`forge_bridge/client/`) — `AsyncClient` + `SyncClient` for connecting to the WS server.
- **Learning pipeline** (`forge_bridge/learning/`) — execution log (JSONL source of truth at `~/.forge-bridge/executions.jsonl`), threshold-driven promotion, LLM synthesizer (Ollama backend), registry watcher, probation system. SQL mirror via `StoragePersistence` Protocol (Phase 8) — JSONL-authoritative, SQL eventual. **Substrate, not autonomous producer:** bridge ships the recording machinery, synthesizer, watcher, and manifest, but a *consumer application* (projekt-forge in production) is responsible for calling `ExecutionLog.record(code, intent)` to feed observations. On a stock install without a consumer wired, the pipeline is dormant — the log file exists, the watcher polls, but no patterns ever cross threshold.
- **LLM router** (`forge_bridge/llm/router.py`) — `LLMRouter` with `acomplete()` and `complete_with_tools()`; sensitive routing to local Ollama vs. cloud Anthropic; hard caps (8 iterations, 120s wall-clock, 30s per-tool); `LLMLoopBudgetExceeded` / `RecursiveToolLoopError` / `LLMToolError` exported from the public API. **v1.6 Phase 24.4** added the **K=2 canonical-recurrence termination trigger** at the D-07 site (`router.py:639-662`): when the 2nd identical successful canonical dispatch is observed (matching `tool_name` + `args_hash` + `result_hash`, both `status=ok`), internal `_OrchestrationTerminated` is raised after the K-th iter's streaming emits + state update (deferred-raise per framing §5 + §8.3); the handler catches and emits a distinct `event: orchestration_terminated` SSE taxon. Load-bearing invariant: "orchestrator may terminate but does not impersonate the model" — no orchestrator-side synthesis, no system message changes, no prompt shaping.
- **Staged operations platform** (`forge_bridge/store/staged_operation.py` + console + MCP wiring) — `proposed → approved → executed/rejected/failed` state machine. Approval is bookkeeping; the proposer subscribes to events and executes against its own domain. **Approval surface, not propose-side:** bridge ships only `forge_list_staged` / `forge_get_staged` / `forge_approve_staged` / `forge_reject_staged` — the inspection-and-decision tools. The propose-side MCP tools (`forge_stage_rename`, `forge_stage_publish_shots`, `forge_stage_set_startframes`, …) live in the consumer (projekt-forge in production); on a stock install without a consumer, the `staged_operation` table stays empty until something feeds it. Same substrate/consumer pattern as the Learning pipeline above.
- **Federation orchestration layer** (`forge_bridge/orchestration/`) — the **phase-4b** substrate: `discovery.py` (sibling discovery via the `forge_bridge.siblings` entry-point group), `planner.py` + `planner_passes.py` (six-pass capability-routing planner), `manifest.py` (provenance manifest assembler), `replay.py`, `event_consumer.py`, `registration.py`, `drivers.py`, `lineage_graph.py` + `store/orch_capability_snapshot_repo.py`. This is bridge's half of the **forge-contracts federation** (forge-bridge is ONE peer; siblings = forge-vision, forge-pipeline, forge-generators; vocabulary in `forge-contracts` v0.1). It answers *"which declared capability satisfies this step?"* (capability-family routing) — distinct from Phase X's referent resolution (*"what does 'this' point to?"*). **Bridge Discovery is the active federation frontier**; bridge's discovery protocol diverged from the published `CapabilityDeclaration` contract and is being reconciled — see `.planning/PHASE-6A-DISCOVERY-ALIGNMENT.md`. NB: this subsystem, Phase X (`context_pressure/`), and the **composition / graph-native execution engine** (below) are the three parallel bridge workstreams as of 2026-06; none is in the older v1.x milestone narrative above. Per the operator's standing **graph-first** priority (the operator-drivable graph is the north-star, NL can wait), the composition engine is the primary frontier.
- **Composition / graph-native execution engine** (`forge_bridge/composition/` + `forge_bridge/graph/`) — the operator-drivable graph that is the project's graph-first north-star. `forge_bridge/graph/` holds the **node vocabulary** (atomic typed-port primitives: `filter` / `select` / `collect` value-transforms · `if_gate` / `foreach` control-flow · `commit` + `mutation` + `stage` authority/host-mutation · `ports` topology). `forge_bridge/composition/` is the **runtime**: `graph_spec.py` (`GraphSpec` IR of record), a pure async `GraphExecutor` (`executor.py`), `UnifiedDispatch` (`dispatch.py`) routing each admitted node — via the single `admission.py` table — to a concrete **boundary** (`MCPToolBoundary` · `PrimitiveBoundary` · `ForeachBoundary` · `CommitBoundary`), plus a legacy-vs-graph **compare harness** (`compare.py`) that proves parity against `run_chain_steps`. **Load-bearing doctrine:** *the executor interprets nothing — not assent, not errors, not clarification; the wrapping dispatch/boundaries interpret everything* ([[feedback_orchestrator_control_flow_not_meaning]]). `executor.py` is held **byte-for-byte stable** (a tested invariant) across the whole parity arc. **State (2026-06):** M1 built the engine (proven in isolation); the M2 "Parity & Cutover" milestone's **parity phase is complete** — slices 1 (unified dispatch + compare harness) · 2a/2b/2c (if-gate / foreach / fan-in control-flow + topology) · 3 (mutations/authority via `CommitBoundary`: verify held-vs-fresh manifest → require a ratified `AssentRecord` → apply exactly once, assent never in the executor or the `NodeResult`). The graph now reproduces legacy behaviour across reads, control-flow, fan-in, and ratified host mutations. **It still has ZERO production callers** — the engine is unreachable from the chat/NL/CLI surfaces. M2's remaining **cutover** slices wire it in: **4** (chain-text → `GraphSpec`) · **5** (planner/daemon dual-path reachability) · **6** (corpus-green → flag-flip → retire `run_chain_steps`). See `.planning/M2-PARITY-AND-CUTOVER-FRAMING.md` + the per-slice docs; cold-resume via [[project_passoff_2026_06_20_m2_closed_slice3_authority_shipped]]. **Foreach convergence (2026-07-01):** the `fbridge exec` multi-select rename fan-out is now a *graph-authored* delta rather than CLI hand-assembly — **PR #133** proved `foreach → collect → host_resolve → delta_to_manifest` authors a byte-identical multi-entry `TimelineDelta` (offline; fold parity at n/n+1), and **PR #135** (closes #134) made `ForEachNode.iteration_payload` author its ordinal iteration index (reserved `_foreach = {"index": <int>}` stamped on the throwaway item copy — foreach is sole author, provenance envelope untouched, executor still byte-stable) so `$n{}` counters expand from a real per-iteration index, not a fixture pre-stamp. Design + rationale (3-view convergence + redline): `.planning/CONVERGENCE-foreach-index.md`. **Still offline** — the live `_run_fanout` path is untouched; cutover is gated on an **unbound seam**: who owns timeline-ordering (assert at the foreach input edge vs. a dedicated upstream position-annotator node), decided at cutover by inspecting whether the live `select`/`collect` feeding foreach already emits timeline order. The "sequential-commits" foreach shape (body = `commit`, iteration sees prior applied state) is deferred until a reorder/cascading-trim case needs it. Cold-resume: [[project_passoff_2026_07_01_batch_author_foreach]].
- **Tool provenance** — every synthesized tool carries `_meta.forge-bridge/*` fields (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`); `annotations.readOnlyHint=False` always; sanitization at the read boundary (single-source `_sanitize_patterns.py` shared across Phase 7 + FB-C).

### What is designed but not yet implemented

- Dependency graph traversal engine (relationships exist in the schema via FK + `DBEvent` rows, but no graph-traversal module)
- Bridge core service as a separate router process
- Canonical event-driven pub/sub abstraction (the WebSocket server ships; the canonical pub/sub layer on top of it does not)
- Maya endpoint
- Editorial / shot-tracking adapters
- Authentication (deferred — SEED-AUTH-V1.5; v1.6+ scope)

---

## Repository Layout

```
forge-bridge/
├── CLAUDE.md               ← YOU ARE HERE
├── README.md               ← Project overview, install quick-start
├── pyproject.toml          ← Package config (version, deps, extras [dev], [llm], [test-e2e])
├── alembic.ini             ← DB migration config (sync URL; reads FORGE_DB_URL or hardcoded forge:forge@localhost)
│
├── forge_bridge/                ← Python package
│   ├── __init__.py             ← Public __all__ (19 symbols)
│   ├── __main__.py             ← Thin delegate to `forge_bridge.cli.main:app` (bare invocation prints help and exits)
│   ├── bridge.py               ← HTTP client to Flame bridge (`bridge.execute()` etc.)
│   ├── cli/                    ← Typer + Rich subcommands (tools, execs, manifest, health, doctor)
│   ├── client/                 ← Async/sync WS clients
│   ├── composition/            ← Graph-native execution runtime (GraphSpec IR, pure GraphExecutor, UnifiedDispatch→boundaries, admission table, legacy-vs-graph compare harness) — M1/M2; own __all__; proven in isolation, zero production callers
│   ├── console/                ← Artist Console (Web UI on :9996, /api/v1/chat handler, app.py mount)
│   ├── context_pressure/       ← Phase X Context Pressure Instrument (capture→S4 analysis; own __all__; measures referent-resolution failures) — dogfood-gated
│   ├── core/                   ← Canonical vocabulary (entities, traits, registry, vocabulary)
│   ├── flame/                  ← Flame-specific helpers shared across tools
│   ├── graph/                  ← Graph node vocabulary (atomic typed-port primitives: filter/select/collect, if_gate/foreach, commit/mutation/stage, ports) consumed by composition/
│   ├── learning/               ← Execution log, synthesizer, watcher, probation
│   ├── llm/                    ← LLMRouter, tool adapters (Ollama, Anthropic), sanitization
│   ├── mcp/                    ← FastMCP server + tool registry (the canonical MCP server lives HERE, not in server.py)
│   ├── orchestration/          ← Federation orchestration (phase-4b): sibling discovery, six-pass capability planner, provenance manifest, replay, event consumer, lineage — the Bridge Discovery / Phase 7 demonstrator substrate
│   ├── server/                 ← WebSocket server + protocol
│   ├── store/                  ← Postgres entities, sessions, Alembic migrations, staged_operation
│   └── tools/                  ← MCP tool implementations: project, timeline, batch, publish, utility
│
├── flame_hooks/             ← Installs into Flame's Python hooks dir
│   └── forge_bridge/
│       └── scripts/
│           └── forge_bridge.py   ← HTTP server running inside Flame on :9999
│
├── scripts/
│   └── install-flame-hook.sh    ← Deploys the Flame hook (defaults pinned to v1.8.2)
│
├── tests/                   ← pytest suite (test_*.py); see tests/llm/, tests/integration/, tests/console/
│
└── docs/
    ├── INSTALL.md          ← Canonical install guide (Phase 20 ships this)
    ├── VOCABULARY.md       ← The canonical language
    ├── ARCHITECTURE.md     ← Design decisions
    ├── API.md              ← HTTP API for the Flame bridge endpoint
    ├── ENDPOINTS.md        ← How to write new endpoint adapters
    ├── DATA_MODEL.md       ← Domain reference
    └── FLAME_API.md        ← Domain reference
```

**Note:** `forge_bridge/server.py` (top-level file, NOT the `server/` directory) is a pre-Phase-5 orphan — broken imports, not re-exported, not runtime-imported. The canonical MCP server lives at `forge_bridge/mcp/server.py`. Tracked as a follow-up dead-code cleanup.

---

## Key Design Decisions (brief version)

Full reasoning in `docs/ARCHITECTURE.md`.

| Decision | What | Why |
|----------|------|-----|
| HTTP transport | Flame bridge uses HTTP | Universal compatibility, easy debug, web UI free |
| Code execution not RPC | Bridge passes Python strings to Flame | Flame API is large/changing. Structured wrappers on top. |
| Automatic dependency graph | No manual declaration | Manual = always incomplete. Infer from data structure. |
| Traits (Versionable, Locatable, Relational) | Cross-cutting capabilities | Same behavior shared across entity types, not reimplemented per type. |
| Auth deferred | Not implemented yet | Local only for now. Framework accommodates it. |
| Local first | No cloud/network initially | Avoid premature complexity. Swappable later. |

---

## Vocabulary Summary

Entities: Project → Sequence → Shot → Version → Media

Stack = group of Layers that belong to the same Shot, each with a Role
Layer = member of a Stack, carries a Role (primary/reference/matte/etc.)
Asset = non-shot thing used in shots (characters, elements, textures)

Traits (cross-cutting):
- Versionable — can have numbered iterations
- Locatable — has path-based addresses (multiple locations possible)
- Relational — can declare and traverse relationships to other entities

Dependency: Relational + consequences. "If this changes, these are affected."

Full spec: `docs/VOCABULARY.md`

---

## Relationship to projekt-forge

forge-bridge is the infrastructure layer; projekt-forge is the first first-party consumer built on top of it.

projekt-forge pins specific forge-bridge versions and builds production workflows against the stable vocabulary and runtime surfaces bridge provides. The split is intentional: forge-bridge stays generic infrastructure, while consumer-specific workflow behavior lives downstream.

projekt-forge repo: https://github.com/cnoellert/projekt-forge

---

## How to Get Running

See `docs/INSTALL.md` for the canonical operator-workstation install path. Quick reference:

```bash
# 1. conda env (matches the reference deployment)
conda create -n forge python=3.11 -y
conda activate forge

# 2. Install with the LLM extras (mandatory for chat + synthesis)
pip install -e ".[dev,llm]"

# 3. Install the Flame hook
./scripts/install-flame-hook.sh
# or standalone: curl -fsSL https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.8.2/scripts/install-flame-hook.sh | bash

# 4. Run migrations (defaults to forge:forge@localhost:5432/forge_bridge — set FORGE_DB_URL to override)
alembic upgrade head

# 5. Bring up the bridge runtime (mcp_http + co-hosted Console on :9996, state_ws on :9998)
# Option A: ad-hoc managed background daemons (good for dev / single workstation)
fbridge up
# Option B: supervised systemd / launchd daemons (operator-workstation path)
sudo ./scripts/install-bootstrap.sh
# Note: bare `python -m forge_bridge` prints help and exits 0 — it does NOT start any services.

# 6. Smoke-test the surfaces
curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"   # Web UI → 200
curl -s   http://localhost:9999/status                                  # Flame hook → JSON with flame_available
forge-bridge console doctor                                             # CLI + post-install diagnostic
```

`ANTHROPIC_API_KEY` is **optional for ordinary chat** — the chat endpoint hardcodes `sensitive=True`, which routes through local Ollama (`qwen2.5-coder:14b` since Phase 24.3). It is **required for format chains** that end in `format_result` (for example, `get segments on 30sec 21 -> format as email summary`), because that tool sends a condensed payload to the Anthropic cloud model via `sensitive=False`.

**Do not use `qwen3:32b` as the default model.** It exceeds the 60s wall-clock budget due to thinking-mode token verbosity (SEED-DEFAULT-MODEL-BUMP-V1.4.x).

---

## Active Development Context

Milestone: **v1.9 Conversational Reads** (active). There is no single live state cursor — continuity is distributed across milestone/phase docs under `.planning/`, `.planning/JOURNAL.md`, and git history; `.planning/CONTINUITY-MAP.md` maps which artifact carries what authority. The most recent milestone-close doc plus that map is the cold-resume surface.

**Primary current frontier — the graph-native execution engine (M1/M2, `composition/` + `graph/`; see the subsystem bullet above).** Per the operator's standing graph-first priority, this is the lead workstream and runs in parallel to the v1.x narrative. As of 2026-06-22 the M2 "Parity & Cutover" milestone's **parity phase is complete** (slices 1 · 2a/2b/2c · 3) **and slice 4 has shipped** (PR #101 — `composition/chain_compiler.py` compiles chain-step text → `GraphSpec`, run **offline** through `GraphExecutor` + `CommitBoundary`; the live `run_apply_branch` path stays untouched — Option A). The engine reproduces legacy behaviour across reads, control-flow, fan-in, ratified host mutations, and (offline) compiled chain-apply — but still has **zero live production callers** (slice 4 is offline-proven). **NEXT = slice 5** (dual-path reachability, both paths live) then **6** (cutover / retire `run_chain_steps`). **Slice 5's real prerequisite: a capture source that persists replayable `chain_steps`** — the broad-real-corpus bar was deferred from slice 4 because the only execution log is the learning-pipeline code log (no NL chat intents); capture from `compile_intent` over real intents, minding the "no shared-path JSONL writers" non-goal. Cold-resume cursor: [[project_passoff_2026_06_22_m2_slice4_compiler_shipped]]; framing: `.planning/M2-PARITY-AND-CUTOVER-FRAMING.md`. **Newest concrete cutover vertical (2026-07-01):** the `fbridge exec` rename fan-out has been reproduced as a graph-authored delta (**#133/#135**, still offline) — see the composition subsystem bullet above + [[project_passoff_2026_07_01_batch_author_foreach]] for the foreach batch-author + iteration-index convergence and the unbound timeline-ordering seam that gates its live cutover. NB the planning archaeology carries several overlapping naming schemes (v1.x milestones · M1/M2 composition · JOURNAL "Phase N/25.x" / "v1.12") — the per-milestone close docs + `CONTINUITY-MAP.md` reconcile authority; do not assume one scheme subsumes the others.

**v1.9 thesis:** the chat surface stopped answering humans — it returns dispatch envelopes (`chain_complete` with raw results), not plain-language answers. v1.9 reattaches a model answer-pass on **reads** as a *pressure instrument*: rough-but-usable, so an artist can finally drive the tool and generate a real comprehension-failure corpus to rank later legibility work. **CR.1 has landed** (the `(b)` terminal-synthesis pass at the `chain_complete` seam, via `LLMRouter.acomplete`); the author-driven dogfood is pending the projekt-forge re-pin + data publish.

**Architectural baseline (inherited from v1.6-FRAMING §2.5, still binding):** forge-bridge is **a low-latency conversational runtime + a graph-native operational runtime sharing a common dispatch substrate**. Three engineering domains held separately: runtime economics (token/model/prefix budget), protocol serialization (provider-native `tool_calls` + Bug-D salvage normalization on qwen2.5-coder), and dispatch substrate (`_execute_python_core` shared across MCP tool-call path + `fbridge flame-exec` + graph_store JSONL log).

**Load-bearing doctrine that constrains every chat/answer change (do not relitigate casually):**

- **The orchestrator may terminate but does not impersonate the model** (24.4, K=2 canonical-recurrence trigger in `router.py`). Three terminal taxa — `done` (model-decided) / `orchestration_terminated` (policy-decided) / `error` (transport) — encode *who decided*, not just *what*. Consumers branch on the taxon.
- **The cut line for synthesis (v1.9):** the system MAY synthesize *explanations of facts that exist* in the substrate; it MAY NOT synthesize *facts that do not exist* (no invented state, results, authority decisions, provenance, or predicted-outcome-as-fact). The operative axis is not facts-vs-explanations alone — it is **grounded AND understandable AND authored-by-an-entitled-layer**. The model authors answers (attributed `done`); the orchestrator/handler never authors prose; assent stays the operator's.
- **Reads vs mutations split:** reads may carry a model answer-pass; mutations stay deterministic preview → ratify → apply with no model prose anywhere near `AssentRecord`. In CR.1 this is enforced *structurally* — the answer-pass lives only in the `compiled_non_mutating` branch, not behind a runtime flag.
- **Substrate, not producer:** bridge ships recording/synthesis/staging machinery; a consumer (projekt-forge in production) feeds it. On a stock install the learning pipeline and staged-ops tables stay dormant.

**Milestones shipped since the v1.4.1 baseline** (writer's-room cadence — framing + commits + cursors carry archaeology; no formal GSD plan substrate): **v1.5** Legibility (reader docs) · **v1.6** Operability (graph-native runtime, doctor observability, 24.x chat-layer convergence — model bump to `qwen2.5-coder:14b`, SSE streaming, K=2 termination) · **v1.7** Artist Readiness (the NL → compile → preview → ratify → apply authority chain; `AssentRecord` substrate; `fbridge ratify` + `POST /api/v1/ratify`) · **v1.8** Console Authority (CA.1 projected the ratify chain onto the Web UI; CA.2/CA.3 unopened) · **v1.9** Conversational Reads (CR.1 answer-pass, active).

**Constraints (binding):**

- Public `forge_bridge.__all__` is **19** and has not moved since v1.4.1; `pyproject.toml` is `1.8.2`. New internal packages (e.g. `forge_bridge/comprehension/`, `forge_bridge/corpus/`) carry their own `__all__` and do NOT touch the top-level 19. No new external libraries.
- The CR.1 comprehension corpus (`forge_bridge/comprehension/`) is a **distinct instrument** from the v1.6 divergence corpus (`forge_bridge/corpus/`) — mirror the atomic-append-JSONL + versioned-schema pattern, never couple schemas or gates, and keep the two named distinctly forever.
- Writer's-room cadence persists: framing → discuss → plan → execute, cross-voice review (DT grounding / Creative experience / Orch synthesis), grounded against live file reads.

**Don't break:** the Flame hook + MCP server + Artist Console + CLI + chat endpoint are all in production use across portofino + flame-01 + assist-01. Every milestone since v1.4.1 has preserved existing surfaces byte-equivalently; the answer-pass is additive (a synthesis failure must never regress a successful read — `acomplete` is bounded and its failure swallowed to an empty answer).

---

## Housekeeping discipline (cleanup actions)

Before any destructive housekeeping that touches the filesystem layout this project anchors to — `git worktree remove`, moving the repo, deleting a checkout — **check whether an editable install is anchored to the target path first:**

```bash
pip show forge-bridge | grep -E '^(Location|Editable)'
```

If the `Location` (or `Editable project location`) points into the path you're about to delete, **re-anchor the editable install from a checkout you're keeping before removing anything:**

```bash
cd /path/to/the/checkout/you/are/keeping
pip install -e ".[dev,llm]"
```

THEN remove the worktree. Reversing the order leaves the env with a dangling `.pth` pointer — `fbridge` stays on `$PATH` but every invocation surfaces `ModuleNotFoundError: No module named 'forge_bridge'` until the install is re-anchored. The long-running daemon usually keeps serving (its interpreter holds an open file handle to the deleted source), so the breakage doesn't surface until the next `pytest` / `fbridge` / `python -c "import forge_bridge"` invocation — at which point it can look like a much deeper problem than it actually is.

Full recovery + symptom catalogue: `docs/TROUBLESHOOTING.md` → "Failure mode: `ModuleNotFoundError: No module named 'forge_bridge'` (editable-install anchor lost)".

This precondition check matters more on this project than on most because the daily workflow involves multiple checkouts (main + worktrees + AI-assistant scratch branches) and the active conda env is typically anchored to exactly one of them.

---

## Questions To Come Back To

1. What format should bridge use for inter-service messages? JSON? MessagePack? Something else?
2. Should the bridge core service be a single process or multiple cooperating processes?
3. When is a Unix socket preferable to HTTP for same-machine communication?
4. What does the bridge core service look like from an endpoint's perspective — is it a library you import or a service you connect to?
