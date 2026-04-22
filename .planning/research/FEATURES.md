# Features Research — v1.3 Artist Console

**Domain:** Artist-first Web UI + CLI + MCP resource console for forge-bridge observability
**Research mode:** Feature-landscape (subsequent milestone, v1.3 scope)
**Researched:** 2026-04-22
**Overall confidence:** HIGH — MCP spec, FastMCP docs, reference UI patterns (Temporal, Dagster, Prefect, ComfyUI), and existing codebase internals all converge on clear conventions.

---

## Context: What Exists, What Is New

**Already shipped (do not re-research or re-specify):**
- MCP server with ~42 tools under `flame_*` / `forge_*` / `synth_*` prefixes
- LLM router (`LLMRouter.acomplete()`, `ahealth_check()`) — Ollama + Anthropic + OpenAI with lazy optional-dep guards
- Synthesis pipeline: `ExecutionLog` (JSONL, `~/.forge-bridge/executions.jsonl`), threshold promotion, `SkillSynthesizer`, registry watcher, `ProbationTracker`
- `.sidecar.json` envelope with canonical `_meta` provenance under `forge-bridge/*` namespace
- `_sanitize_tag()` injection boundary with 64-char/16-tag/4KB budgets
- `StoragePersistence` Protocol; projekt-forge holds the SQLAlchemy adapter + Alembic 005
- `forge://llm/health` MCP resource — the one existing resource; proves `forge://` scheme is already committed
- Flame HTTP bridge on `:9999`; WebSocket server on `:9998`

**New in v1.3:**
- Web UI dashboard served on a new port (`:9996`) inside the MCP server process
- CLI companion (`forge-bridge console <subcommand>`)
- Synthesis manifest as MCP resource (`forge://manifest/synthesis`)
- Shared read-side API powering Web UI + CLI + chat (JSONL + live state; optional SQL mirror)
- Structured query console (primary Web UI interaction mode — deterministic, no LLM in hot path)
- LLM chat layered over the same read API using the existing `LLMRouter`

**Locked non-goals for v1.3:**
- No admin / mutation actions (read-only milestone)
- No auth (localhost-bound, same posture as `:9999`)
- No Maya/editorial manifest producers
- No `LLMRouter` hot-reload, no shared-path JSONL writers (carried forward)

---

## User Taxonomy

Two distinct users interact with this console. Their needs diverge sharply.

### Artist / Operator (primary target)
A Flame artist or senior operator running shots day-to-day. Not a Python developer. Asks:
- "What tools has the system learned that I can use?"
- "Did that thing I just ran work?"
- "Why did that synthesized tool fail — is it broken or did I do something wrong?"
- "Is the LLM backend up?"

**UX contract:** Answers in 5 seconds or fewer. No jargon. Status at a glance. No configuration required to read. No "inspect element" required to understand what's shown.

### Pipeline Engineer (secondary target)
The person who built or maintains the pipeline. Asks:
- "What's the code_hash for that tool — does it match what's in the DB?"
- "How many executions crossed the promotion threshold?"
- "Which tools are on probation and why?"
- "Is the sanitization budget being hit?"

**UX contract:** Full provenance data available. Correlatable across JSONL + DB. Exportable/grep-able. Doesn't require the Web UI — CLI is sufficient.

### LLM Agent (tertiary — MCP consumer)
An agent (Claude Code, custom orchestrator, AI assistant) that needs programmatic read access to bridge state. Asks via MCP:
- "What has bridge synthesized? Give me the manifest."
- "What tools are available and what are their provenance hashes?"
- "Is the LLM router healthy before I attempt a synthesis call?"

**UX contract:** Machine-readable JSON via MCP resources. Deterministic URIs. No pagination gymnastics.

---

## Feature Categories

Five categories anchor all features. Each maps to a Web UI view, a CLI subcommand, and (for manifest/tools/health) an MCP resource.

| Category | Web UI view | CLI subcommand | MCP resource |
|----------|-------------|----------------|--------------|
| Tools | Tools table | `console tools` | `forge://tools` |
| Executions | Exec history | `console execs` | — |
| Manifest | Manifest browser | `console manifest` | `forge://manifest/synthesis` |
| Health | Health panel | `console health` + `console doctor` | `forge://llm/health` (exists) |
| Chat | Chat surface | — (CLI not a chat surface) | — |

---

## Table Stakes

Features whose absence makes the product feel incomplete or broken. Grouped by user.

### TS-A: Artist / Operator Table Stakes

**TS-A.1 — Tools table view**
A filterable list of all registered MCP tools: name, namespace prefix (`flame_*` / `forge_*` / `synth_*`), origin (`synthesized` / `builtin`), and a single status chip (active / quarantined).
- **Data needed:** `mcp.list_tools()` response + probation state from `ProbationTracker`; provenance from `Tool._meta["forge-bridge/*"]` for synthesized tools
- **Artist relevance:** "What can I ask forge-bridge to do?" is the first question any artist asks
- **Engineer relevance:** Confirms registration succeeded and namespace rules are enforced
- **Complexity:** Trivial — data already exists at `mcp.list_tools()`; needs a basic table renderer
- **Dependencies:** MCP server running; registry state in memory; probation tracker state

**TS-A.2 — Per-tool drilldown**
Click/select a tool to see: full description, input schema, provenance fields (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`), tags, probation history (pass/fail counts), and the raw sidecar JSON.
- **Artist relevance:** "What does this tool actually do and is it trustworthy?"
- **Engineer relevance:** Verifiable provenance; code_hash traceable to JSONL
- **Complexity:** Medium — requires joining tool registry state + probation tracker + sidecar file read
- **Dependencies:** TS-A.1; sidecar files at `~/.forge-bridge/synthesized/*.sidecar.json`; probation tracker

**TS-A.3 — Execution history list**
A time-sorted list of recent executions from the JSONL log: timestamp, intent (if captured), promoted flag, code_hash (truncated). Default: last 50 rows. Filterable by promoted=true and by date range.
- **Artist relevance:** "Did that run I just did get logged?"
- **Engineer relevance:** Verify the `bridge.execute() → ExecutionLog.record()` chain is live; identify promotion candidates
- **Complexity:** Medium — JSONL read with streaming parse; date filtering needs care for large logs
- **Dependencies:** JSONL at `~/.forge-bridge/executions.jsonl`; STORE-06 invariant (JSONL = source of truth, no retry)

**TS-A.4 — Health panel**
Single-screen status: Flame bridge reachability (`:9999`), WebSocket server (`:9998`), LLM router backends (Ollama / Anthropic / OpenAI), synthesis watcher status (last scan, tool count). Traffic-light indicator (green/amber/red) per service.
- **Artist relevance:** "Is everything working before I start a session?"
- **Engineer relevance:** Rapid triage — which service is down?
- **Complexity:** Trivial for aggregation; medium for auto-refresh cadence
- **Dependencies:** `LLMRouter.ahealth_check()`; HTTP probe to `:9999`; watcher state

**TS-A.5 — Manifest view**
A tabular view of the synthesis manifest (`~/.forge-bridge/synthesized/.manifest.json`): filename, sha256, corresponding tool name, registration status (loaded / not loaded). Read-only.
- **Artist relevance:** "How many tools has the system learned?"
- **Engineer relevance:** Detect orphaned manifest entries (file on disk but not registered); detect registration failures
- **Complexity:** Trivial — manifest is a JSON file; join against loaded tool names from registry
- **Dependencies:** Manifest file; watcher state (to know what's loaded vs just on disk)

### TS-E: Pipeline Engineer Table Stakes

**TS-E.1 — Execution detail / drilldown**
Click an execution in the list to see: full `raw_code`, full `intent`, `code_hash`, `promoted` flag, `timestamp`, and (if SQL mirror is enabled) a "View in DB" indicator. Raw JSON view of the JSONL record.
- **Artist relevance:** Secondary — useful if an artist is debugging why a run didn't promote
- **Engineer relevance:** Primary — full code inspection, hash cross-reference
- **Complexity:** Trivial — data already in JSONL record
- **Dependencies:** TS-A.3

**TS-E.2 — Probation state per tool**
For synthesized tools: pass count, fail count, quarantine status, quarantine reason (if set). Surfaced in per-tool drilldown (TS-A.2) but also available as a list filter on the tools table ("show quarantined only").
- **Artist relevance:** "Is this tool reliable?"
- **Engineer relevance:** "What's the error rate? Should I intervene?"
- **Complexity:** Trivial — data already in `ProbationTracker`
- **Dependencies:** TS-A.1; probation tracker instance

**TS-E.3 — Raw JSONL access in CLI**
`forge-bridge console execs --raw` outputs newline-delimited JSON to stdout, suitable for `jq` piping. `--limit N`, `--since ISO8601`, `--promoted-only` flags.
- **Artist relevance:** None — artist uses Web UI
- **Engineer relevance:** Primary — integrates with existing shell workflows; grep-able
- **Complexity:** Trivial — streaming JSONL read with flag filtering
- **Dependencies:** JSONL file existence

### TS-L: LLM Agent Table Stakes

**TS-L.1 — `forge://manifest/synthesis` MCP resource**
A static resource returning a JSON manifest of all synthesized tools with their full provenance: name, code_hash, synthesized_at, version, observation_count, tags, probation state. One call returns the complete current state.
- **Agent relevance:** "What has the system learned? Give me names and hashes I can reference."
- **Complexity:** Medium — aggregates registry + sidecar data + probation state; needs to be fast (< 200ms for typical tool counts)
- **Dependencies:** Registry state; sidecar files; probation tracker; manifest file

**TS-L.2 — `forge://tools` MCP resource**
A resource returning the full tool list as JSON: name, description, namespace, input_schema, annotations, `_meta`. Redundant with `tools/list` wire call but useful as a named, cacheable artifact for agents building plans.
- **Agent relevance:** "What can I call? Give me a machine-readable snapshot."
- **Complexity:** Trivial — wraps `mcp.list_tools()` as a resource
- **Dependencies:** MCP server running

---

## Differentiators

Features that set forge-bridge apart. Not expected by default but valued once seen.

**DF-1 — Structured query console (Web UI)**
An input bar in the Web UI accepting structured queries: `tool:synth_*`, `exec:promoted=true since:7d`, `manifest:loaded=false`. Results appear in the main content area without a page reload. No LLM in this path — entirely deterministic.
- **Why valuable:** Artist can answer "which synthesized tools are currently loaded and healthy?" without understanding the internal data model
- **Artist vs engineer:** Both users benefit; artist uses preset query chips; engineer types raw filters
- **Complexity:** Medium — query parser for the filter DSL; straightforward against in-memory data
- **Dependencies:** TS-A.1, TS-A.3, TS-A.5

**DF-2 — LLM chat layer (Web UI)**
A second panel alongside the structured console where the artist types natural language: "Show me tools synthesized last week" or "Why did that reconform tool fail?" Routed through existing `LLMRouter.acomplete()` with the manifest and recent exec context injected as system context.
- **Why valuable:** Lowers the floor to zero — no query DSL required; artist asks in plain English
- **Artist vs engineer:** Artist primary; engineer uses structured console
- **Complexity:** Hard — requires careful context assembly (manifest + exec snippets + tool list must fit in model context window without leaking sensitive code); must degrade gracefully when LLM router is down
- **Dependencies:** DF-1 (uses same read API); `LLMRouter` healthy (health check required pre-call); manifest resource (TS-L.1)

**DF-3 — `console doctor` CLI subcommand**
Runs a checklist of pre-flight checks and prints a structured pass/fail report:
- Flame bridge reachable at `:9999`?
- WebSocket server reachable at `:9998`?
- At least one LLM backend healthy?
- JSONL log file exists and is parseable (last N rows)?
- Synthesized tools dir exists and manifest is valid?
- At least one synthesized tool loaded?
- StoragePersistence callback registered? (if projekt-forge integration is active)

Output: table of checks with PASS/FAIL/WARN and actionable fix hints. Zero dependencies on the Web UI.
- **Artist vs engineer:** Artist uses it before a session to confirm setup; engineer uses it in CI/CD
- **Pattern:** Follows npm/Homebrew/React Native CLI `doctor` convention — well-understood, low cognitive load
- **Complexity:** Medium — multiple async health checks in parallel; structured output formatter
- **Dependencies:** TS-A.4; LLMRouter health; JSONL file; manifest file

**DF-4 — `forge://tools/{name}` MCP resource template**
A parameterized resource returning per-tool detail JSON for a single tool by name. Useful for agents that want to introspect one tool before calling it.
- **Agent relevance:** "Tell me everything about `synth_reconform_timeline` before I use it."
- **Complexity:** Trivial once TS-L.2 exists — filter by name from the same data source
- **Dependencies:** TS-L.2; `forge://tools` resource

**DF-5 — Execution promotion rate sparkline**
In the manifest view, a mini time-series showing execution count vs promoted count over the last 7 days per synthesized tool. Derived from the JSONL log.
- **Artist relevance:** "Is this tool still being used and getting better?"
- **Engineer relevance:** "Is the promotion threshold correctly calibrated?"
- **Complexity:** Medium — JSONL aggregation by day + tool (requires joining by code_hash to tool name via sidecar); charting in Web UI
- **Dependencies:** JSONL; sidecar files for code_hash → name join

**DF-6 — SSE / poll-based live update in Web UI**
The health panel and tool count auto-refresh without full page reload. Minimum viable: long-poll every 5 seconds. Preferred: Server-Sent Events on a `/events` endpoint pushed by the watcher whenever tool registration changes.
- **Artist relevance:** "Is that new tool I just triggered being picked up?"
- **Complexity:** Medium for SSE; trivial for poll — PROJECT.md calls this an open question (SSE vs poll-only). Recommend starting with poll (5s) and shipping SSE as a follow-on.
- **Dependencies:** Web server in MCP process; watcher event hooks

---

## Anti-Features

Features to explicitly NOT build in v1.3.

**AF-1 — No admin / mutation actions in the Web UI**
No quarantine/promote/kill buttons. No tool deletion. No manual synthesis trigger. PROJECT.md locks this: "admin is a follow-on once auth is in scope." Building mutation surfaces without auth creates an unintended attack surface on localhost.
- **What to do instead:** CLI `forge-bridge console doctor` surfaces issues; engineer uses direct API calls for admin actions until auth ships

**AF-2 — No auth in the console**
Mirrors `:9999` posture. Auth adds complexity without protecting a localhost-only service. Deferred to a future milestone.
- **What to do instead:** Document that the console port should be firewalled in any multi-user environment

**AF-3 — No Grafana-style metric cardinality explosion**
Do not expose every internal counter as a time-series metric with fine-grained labels. Grafana's own engineering team acknowledges this leads to "a stack of dashboard anti-patterns — big and complex, displays far too many metrics in one place." The console is an artist-facing dashboard, not an observability platform.
- **What to do instead:** Surface exactly the counters that answer the artist's 3 questions (is it healthy, what tools exist, did my run log). Aggregate aggressively.

**AF-4 — No code editor or synthesis UI**
Do not let the artist browse or edit raw synthesized Python files through the Web UI. v1.3 is read-only; code editing introduces XSS vectors and would require auth and sandboxing.
- **What to do instead:** CLI `forge-bridge console manifest --show-path` prints the filesystem path for engineers who want to inspect files directly

**AF-5 — No separate database / new storage for the console**
The console reads JSONL + in-memory state + optionally the SQL mirror that already exists via StoragePersistence. Do not add a new SQLite or embedded DB to serve the Web UI.
- **What to do instead:** The shared read-side API abstracts this — it reads JSONL directly; if a SQL mirror is registered it uses it; if not, JSONL is sufficient

**AF-6 — No multi-project view in v1.3**
PROJECT.md flags multi-project view as an open question for the roadmapper. The read-side API should use `~/.forge-bridge/` as the data root and not assume a project namespace yet. Keep scope tight.
- **What to do instead:** Single-project (current bridge instance) view only; project context shown as a display label if available

**AF-7 — No ComfyUI-style node graph visualization**
Do not render the synthesis pipeline as a visual node graph. This is appealing but expensive to build correctly and adds no operational value for v1.3's read-only scope. ComfyUI's complexity is justified by its edit-in-graph workflow — forge-bridge's console does not edit.
- **What to do instead:** Tabular views with clear provenance metadata are faster to build and faster to read

**AF-8 — No Temporal-style "workflow execution timeline" drill-down**
Temporal's timeline view of activity execution chains is powerful for debugging orchestration. forge-bridge's execution log records individual `bridge.execute()` calls, not orchestrated workflow chains — the graph doesn't exist yet. Building a timeline visualization without the graph data would be misleading.
- **What to do instead:** Linear exec list with timestamp + intent; graph visualization is a future milestone once the dependency graph engine exists

---

## Feature Dependencies

```
TS-A.1 (tools table)
  └─ TS-A.2 (per-tool drilldown)
       └─ TS-E.2 (probation state)

TS-A.3 (exec history list)
  └─ TS-E.1 (execution detail)
  └─ DF-5 (promotion sparkline)

TS-A.4 (health panel)
  └─ DF-3 (doctor CLI)
  └─ DF-2 (LLM chat — requires health check before call)

TS-A.5 (manifest view)
  └─ TS-L.1 (forge://manifest/synthesis resource)
       └─ DF-2 (LLM chat — injects manifest as context)
       └─ DF-4 (per-tool resource template)

TS-L.2 (forge://tools resource)
  └─ DF-4 (per-tool resource template)

DF-1 (structured query console)
  └─ DF-2 (LLM chat — uses same read API)

TS-A.1 + TS-A.3 + TS-A.5
  └─ DF-1 (structured query console — queries across all three)
```

---

## Shared Read-Side API

All five categories draw from a single read-side data layer. This must be designed first (Phase 9-01 or equivalent) to avoid each view building its own JSONL parser.

### Data sources

| Source | What it feeds | Access pattern |
|--------|--------------|----------------|
| `~/.forge-bridge/executions.jsonl` | Exec history, promotion rates | Streaming line parse; tail from end for recency |
| `~/.forge-bridge/synthesized/*.sidecar.json` | Tool provenance, tags, code_hash | Directory scan; cached after initial load |
| `~/.forge-bridge/synthesized/.manifest.json` | Manifest integrity, file registration | Single JSON file |
| In-memory MCP registry | Tool list, namespaces, schemas | `mcp.list_tools()` call |
| In-memory `ProbationTracker` | Pass/fail counts, quarantine state | Direct attribute access |
| `LLMRouter.ahealth_check()` | LLM backend status | Async call; cached 10s |
| HTTP probe to `:9999` | Flame bridge health | HTTP GET with short timeout |
| WebSocket probe to `:9998` | WS server health | Connect + disconnect check |
| SQL mirror (optional) | Structured exec queries | Via StoragePersistence adapter if registered |

### API shape recommendation

A `ConsoleReadAPI` class (or module with functions) that:
- Exposes `async def get_tools() -> list[ToolSummary]` — joins registry + sidecar + probation
- Exposes `async def get_executions(limit, since, promoted_only) -> list[ExecSummary]` — reads JSONL
- Exposes `async def get_manifest() -> ManifestState` — reads manifest + cross-references registry
- Exposes `async def get_health() -> HealthState` — fans out all health checks in parallel
- Web UI, CLI, and MCP resources all call this API — no view-specific data access

---

## CLI Subcommand Proposals

All under `forge-bridge console <subcommand>`. These mirror the Web UI surface for scripting and SSH workflows.

### `forge-bridge console tools`

```
forge-bridge console tools [OPTIONS]

Options:
  --namespace [flame|forge|synth|all]   Filter by prefix (default: all)
  --origin [synthesized|builtin|all]    Filter by origin (default: all)
  --quarantined                          Show only quarantined tools
  --json                                 Output as JSON array
  --format [table|json|names]            Output format (default: table)

Output (table):
  NAME                       ORIGIN       STATUS      HASH
  flame_get_project_info     builtin      active      —
  synth_reconform_timeline   synthesized  active      a3f7c2...
  synth_switch_grade         synthesized  quarantined d4b1e9...
```

**Artist vs engineer:** Artist reads the table; engineer uses `--json` to pipe into `jq`.
**Complexity:** Trivial.
**Dependencies:** Registry state + probation tracker (server must be running OR state serialized on disk).

### `forge-bridge console execs`

```
forge-bridge console execs [OPTIONS]

Options:
  --limit N                    Number of rows (default: 50)
  --since ISO8601              Filter by timestamp (e.g. 2026-04-01T00:00:00Z)
  --promoted-only              Show only promoted executions
  --raw                        Emit newline-delimited JSON (machine-readable)
  --format [table|json|ndjson] Output format (default: table)

Output (table):
  TIMESTAMP            INTENT                        HASH       PROMOTED
  2026-04-22T10:31:00  reconform timeline ep60 010   a3f7c2...  yes
  2026-04-22T10:28:44  switch grade to logc3          d4b1e9...  no
```

**Artist vs engineer:** Artist uses default table to confirm logging; engineer uses `--raw` for scripted analysis.
**Complexity:** Trivial.
**Dependencies:** JSONL file.

### `forge-bridge console manifest`

```
forge-bridge console manifest [OPTIONS]

Options:
  --loaded-only              Show only tools currently registered in MCP
  --show-path                Print filesystem path alongside each entry
  --format [table|json]      Output format (default: table)

Output (table):
  FILE                          HASH       LOADED  TOOL NAME
  synth_reconform_timeline.py   a3f7c2...  yes     synth_reconform_timeline
  synth_switch_grade.py         d4b1e9...  yes     synth_switch_grade
  synth_orphan_script.py        9f1c43...  no      —
```

**Artist vs engineer:** Artist checks tool count and loaded status; engineer looks for orphaned entries.
**Complexity:** Trivial.
**Dependencies:** Manifest file + watcher state.

### `forge-bridge console health`

```
forge-bridge console health [OPTIONS]

Options:
  --watch              Refresh every 5 seconds (Ctrl-C to stop)
  --format [table|json]

Output:
  SERVICE           STATUS   DETAIL
  Flame bridge      OK       :9999 responded in 23ms
  WebSocket server  OK       :9998 connected
  LLM Ollama        OK       qwen2.5-coder:32b available
  LLM Anthropic     WARN     ANTHROPIC_API_KEY not set
  LLM OpenAI        SKIP     openai not installed
  Synthesis watcher OK       12 tools loaded, last scan 4s ago
```

**Artist vs engineer:** Artist runs before a session; engineer runs in scripts/CI.
**Complexity:** Medium — parallel async health checks.
**Dependencies:** All health sources.

### `forge-bridge console doctor`

```
forge-bridge console doctor [OPTIONS]

Options:
  --json   Output as structured JSON for scripting

Output:
  CHECKING: forge-bridge doctor

  [PASS] Flame bridge reachable at :9999
  [PASS] WebSocket server reachable at :9998
  [PASS] Ollama backend healthy (qwen2.5-coder:32b)
  [WARN] Anthropic backend: ANTHROPIC_API_KEY not set — synthesis will use Ollama only
  [SKIP] OpenAI: openai package not installed
  [PASS] JSONL log exists: 247 records, last written 2m ago
  [PASS] Synthesis manifest valid: 12 entries, all hashes match
  [PASS] Synthesized tools loaded: 11 of 12 (1 on probation)
  [WARN] synth_orphan_script.py: in manifest but NOT loaded — watcher may have rejected it
  [PASS] StoragePersistence callback: registered (type=PostgresAdapter)

  Result: 2 warnings, 0 errors
  Run `forge-bridge console tools --quarantined` to inspect probation details.
```

**Artist vs engineer:** Artist: "is everything ready?" Engineer: "what exactly is wrong?"
**Complexity:** Medium — wraps all health checks + manifest validation + probation summary.
**Dependencies:** TS-A.4; manifest; JSONL; probation tracker.

---

## Web UI Views

All views served on `:9996` from inside the MCP server process. Dark `#242424` base + `#cc9c00` amber palette (LOGIK-PROJEKT heritage, per PROJECT.md design contract).

### View 1: Tools Table

**Purpose:** Answer "what can I use?"
**Data needed:** `mcp.list_tools()` result; per-tool: origin from `_meta["forge-bridge/origin"]`, status from probation tracker, code_hash from `_meta["forge-bridge/code_hash"]`, tags from tool registration.

| Column | Notes |
|--------|-------|
| Name | `flame_*` / `forge_*` / `synth_*` with namespace color-coding |
| Origin | builtin / synthesized chip |
| Status | active (green) / quarantined (red) |
| Tags | Up to 3 tags shown, `+N more` overflow |
| Last synthesized | Relative time for synth tools; — for builtins |

**Interactions:** Click row → per-tool drilldown. Filter bar (namespace, origin, status). Search by name.
**Artist vs engineer split:** Artist sees the status chip and description. Engineer sees code_hash and clicks through to sidecar JSON.
**Complexity:** Medium — table renderer + filter state; data fetch is trivial.

### View 2: Execution History

**Purpose:** Answer "did my last run log?"
**Data needed:** JSONL tail (last 100 rows by default); each row: timestamp, intent, code_hash (6-char prefix), promoted flag.

| Column | Notes |
|--------|-------|
| Time | Relative ("2m ago") with tooltip showing ISO-8601 |
| Intent | Truncated to 60 chars; full text on hover |
| Hash | First 8 chars of code_hash; click copies full hash |
| Promoted | Boolean chip |

**Interactions:** Click row → execution detail drawer (full raw_code, full intent, hash, promoted, sidecar match if any). Filter: promoted only, last N hours.
**Artist vs engineer split:** Artist checks the last row to confirm their run was logged. Engineer reads raw_code in the drawer.
**Complexity:** Medium — JSONL streaming read + drawer/modal component.

### View 3: Per-Tool Drilldown

**Purpose:** Answer "what is this tool and is it trustworthy?"
**Data needed:** Single tool from registry; sidecar JSON; probation tracker state for this tool.

Sections:
1. **Header** — name, description, origin chip, status chip
2. **Provenance** — code_hash, synthesized_at, version, observation_count (from `_meta`)
3. **Tags** — full tag list with namespace-aware rendering (`flame:timeline` → Flame badge)
4. **Input schema** — formatted JSON schema with field descriptions
5. **Probation history** — pass count, fail count, quarantine reason (if any), last-called timestamp
6. **Raw sidecar** — collapsible JSON viewer showing the full `.sidecar.json` content

**Artist vs engineer split:** Artist reads the header and probation summary. Engineer reads provenance + raw sidecar.
**Complexity:** Medium — requires joining three data sources; collapsible sections.

### View 4: Manifest Browser

**Purpose:** Answer "what has been learned, and is it all loaded?"
**Data needed:** Manifest file (`{filename: sha256}`); cross-reference with loaded tool names from registry; cross-reference with sidecar files for tool names.

| Column | Notes |
|--------|-------|
| File | Filename with `.py` highlighted |
| Manifest hash | 8-char prefix |
| Loaded | Yes (green) / No (amber — not an error, could be intentional) / Orphaned (red — in manifest but file missing from disk) |
| Tool name | Resolved from sidecar if available |
| Synthesized at | From sidecar if available |

**Artist vs engineer split:** Artist sees loaded count vs total. Engineer reads orphaned entries and investigates.
**Complexity:** Trivial render; medium data join (manifest + sidecar + registry).

### View 5: Health Panel

**Purpose:** Answer "is everything working right now?"
**Data needed:** Parallel health checks — Flame bridge, WS server, LLM backends, watcher.

Layout: Card grid (2-3 per row). Each card: service name, status circle (green/amber/red), key metric (e.g., "23ms", "12 tools loaded"), last-checked timestamp.

**Auto-refresh:** Poll every 10 seconds (or SSE push if implemented). Status changes trigger amber pulse animation on the changed card.
**Artist vs engineer split:** Artist reads the status circles only. Engineer clicks a card to see the raw health JSON (e.g., full `LLMRouter.ahealth_check()` response).
**Complexity:** Medium — parallel health fetch + card renderer + auto-refresh.

### View 6: Structured Query Console + LLM Chat

**Purpose:** Answer freeform operational questions.

Two sub-surfaces, same screen:
1. **Left / top: Structured query bar** — type `tool:synth_* status:active` or `exec:promoted=true since:24h` or `manifest:loaded=false`. Results in a table below. Preset chip suggestions for common queries.
2. **Right / bottom: LLM chat panel** — natural-language input routed to `LLMRouter.acomplete()` with manifest + recent-exec context injected. Response streamed back. Disabled and grayed out if no LLM backend is healthy.

**Artist vs engineer split:** Artist uses the chat panel; engineer uses the structured query bar.
**Complexity:**
- Structured query: Medium (filter DSL parser; results reuse Views 1-4 table components)
- LLM chat: Hard (context assembly without leaking full `raw_code` to model; streaming response; degradation when LLM is down; token budget management)

---

## MCP Resource URI Conventions

forge-bridge already uses the `forge://` custom scheme (established by `forge://llm/health` in v1.0). This scheme is confirmed valid under RFC 3986 for custom URI schemes. FastMCP implements RFC 6570 URI templates via `@mcp.resource("forge://{param}/...")` decorators.

### Confirmed existing resource
- `forge://llm/health` — LLM backend health status (ships as `forge_bridge.llm.health.register_llm_resources`)

### New resources for v1.3

| URI | Type | Returns | Dependencies |
|-----|------|---------|-------------|
| `forge://manifest/synthesis` | Static resource | JSON: synthesis manifest with provenance for all synthesized tools | Sidecar files + manifest file + probation tracker |
| `forge://tools` | Static resource | JSON: full tool list with `_meta` and annotations | MCP registry state |
| `forge://tools/{name}` | Resource template (RFC 6570 `{name}`) | JSON: single tool detail | `forge://tools` |
| `forge://execs/recent` | Static resource | JSON: last 50 execution records from JSONL | JSONL file |
| `forge://health` | Static resource | JSON: aggregated health state (all services) | All health sources; wraps existing `forge://llm/health` |

**URI scheme rationale:** `forge://` is the project's committed scheme (v1.0 precedent). Sub-paths use noun/noun or noun/template format — no verbs. Aligns with MCP conventions (e.g., `db://tables/{name}`, `file://{path}`, `weather://{city}/current`).

**Registration pattern** (follows `forge://llm/health` precedent):
```python
def register_console_resources(mcp: FastMCP) -> None:
    @mcp.resource("forge://manifest/synthesis")
    async def synthesis_manifest() -> str:
        ...

    @mcp.resource("forge://tools")
    async def tools_list() -> str:
        ...

    @mcp.resource("forge://tools/{name}")
    async def tool_detail(name: str) -> str:
        ...
```

**Caching note:** `forge://tools` and `forge://manifest/synthesis` should cache for 5-10 seconds to avoid hammering the registry on every agent loop iteration. FastMCP does not have built-in cache-control for resources; implement a simple `asyncio.Lock` + TTL cache in the resource function.

---

## Artist-vs-Engineer Divergence Summary

| Feature | Artist UX | Engineer UX |
|---------|-----------|-------------|
| Tools table | Name + status chip | Name + code_hash + namespace validation |
| Per-tool drilldown | Description + "is it healthy?" | Full provenance + raw sidecar JSON |
| Exec history | "Did my run log?" — last row | `--raw` JSON piped to `jq` |
| Exec detail | Not needed | Full `raw_code` + hash cross-reference |
| Manifest view | Loaded count vs total | Orphaned entries + hash mismatch detection |
| Health panel | Traffic-light status circles | Raw health JSON per service |
| Doctor command | "Is everything ready?" | Structured JSON output for CI gates |
| LLM chat | Primary interaction mode | Not the preferred mode — uses structured query |
| Structured query | Preset chips only | Full filter DSL |
| MCP resources | Not applicable | Machine-readable JSON for agent orchestration |

**Key divergence point:** Artist tolerates 10-second refresh cycles and wants status at a glance. Engineer wants raw data exportable and correlatable. The architecture handles this by keeping raw JSON accessible one click/flag away from every summary view, but not the default presentation.

---

## Reference UI Analysis

### Temporal UI — What it does well
Compact/Timeline/Full History views for workflow execution; child workflow drill-down without navigation; dark mode for late-night debugging. Actionable operator controls (cancel/terminate) even for non-backend team members.

**What applies to forge-bridge:** Execution history list + drilldown structure; dark theme as operator default; making operational data accessible to non-backend users.

**What to avoid:** Temporal's UI requires Temporal's full stack and is tightly coupled to workflow orchestration concepts (activities, signals, task queues) that don't exist in forge-bridge's execution model. Don't import those concepts.

### Dagster — What it does well
Asset catalog with breakdown by compute kind, group, code location, tags. Health indicators that highlight issues in real time. Insights dashboard showing success rate and time-to-resolution per asset.

**What applies to forge-bridge:** Tool catalog organized by namespace + origin (analogous to compute kind + code location); health indicators per tool (probation state); manifest browser (analogous to asset catalog).

**What to avoid:** Dagster's graph visualization for asset lineage is its signature feature — impressive but requires the lineage graph to be meaningful. forge-bridge's dependency graph engine is not yet implemented; building a visualization without the graph data is premature.

### Prefect — What it does well
Flow runs dashboard with filter-by-status-and-tags; operational dashboards grouping analytics by deployment; Run Tracing showing the interconnected nature of the data platform.

**What applies to forge-bridge:** Execution history with status/tag filters maps directly to forge-bridge's exec list + promoted filter. Grouping by deployment ≈ grouping by synthesis origin.

**What to avoid:** Prefect's "Resources" feature revealing interconnected system components (S3 buckets, DBs, APIs) is an advanced observability concept that requires system-wide instrumentation — out of scope for v1.3's local-first, single-service console.

### ComfyUI — What it does well
App Mode converts complex node graphs into clean user-facing interfaces by exposing only the relevant controls. Senior artists build and lock approved workflows; end users see only prompts and sliders. This artist-vs-engineer split is directly relevant.

**What applies to forge-bridge:** The "App Mode" principle — Web UI is the simplified, artist-facing surface; CLI is the engineer surface with full raw access. Don't put raw sidecar JSON on the default artist view; put it behind a "Show details" collapse.

**What to avoid:** ComfyUI's node graph editing interface is justified because its entire workflow IS the graph. forge-bridge's console is observability, not editing.

### Grafana — What it does well
Powerful, flexible, extensible. Near-universal in infrastructure monitoring.

**What to avoid:** Grafana's own founder acknowledges the complexity-UX tradeoff failure: "every new feature almost every case makes it more complicated." The Tempo operational dashboard is cited as "a stack of dashboard anti-patterns — big and complex, displays far too many metrics in one place." For a Flame artist audience, Grafana-style metric cardinality and panel proliferation would be immediately hostile. The forge-bridge console must aggressively aggregate and prioritize, not expose all raw counters.

---

## MVP Recommendation

Prioritize (Phase 9 + Phase 10 scope):

**Phase 9 — Foundation and read API:**
1. Shared `ConsoleReadAPI` — JSONL reader, manifest reader, registry snapshot, health checks
2. MCP resources: `forge://manifest/synthesis`, `forge://tools`, `forge://tools/{name}`, `forge://health`
3. CLI: `console tools`, `console execs`, `console manifest`, `console health`, `console doctor`

**Phase 10 — Web UI:**
4. Web server on `:9996` inside MCP process (FastAPI + Jinja2 or similar — see STACK.md)
5. Tools table (TS-A.1) + per-tool drilldown (TS-A.2)
6. Execution history (TS-A.3) + execution detail (TS-E.1)
7. Manifest view (TS-A.5)
8. Health panel (TS-A.4)
9. Structured query console (DF-1) — preset chips only for v1.3

**Defer to v1.4:**
- LLM chat layer (DF-2) — depends on careful context assembly; ship after Web UI is stable
- Promotion rate sparklines (DF-5) — nice-to-have; complex JSONL aggregation
- SSE live updates (DF-6) — poll (5s) is sufficient for v1.3; SSE is a follow-on
- Multi-project view — open question per PROJECT.md

---

## Sources

### Primary (HIGH confidence)
- Direct source analysis: `forge_bridge/learning/execution_log.py`, `forge_bridge/learning/manifest.py`, `forge_bridge/learning/watcher.py`, `forge_bridge/mcp/registry.py`, `forge_bridge/llm/health.py`, `forge_bridge/__init__.py` (v1.3.0)
- FastMCP resources + resource templates docs — https://gofastmcp.com/servers/resources
- MCP Specification 2025-06-18, Resources section — https://modelcontextprotocol.io/specification/2025-06-18/server/resources
- `.planning/PROJECT.md` (v1.3 milestone target features, locked non-goals)

### Secondary (MEDIUM confidence)
- Temporal UI redesign blog — https://temporal.io/blog/the-dark-magic-of-workflow-exploration
- Dagster asset catalog docs — https://docs.dagster.io/guides/observe/asset-catalog
- Prefect observability suite announcement — https://www.prefect.io/blog/summit-25-product-announcement
- ComfyUI App Mode — https://www.mindstudio.ai/blog/comfyui-app-mode-node-workflows-simple-interfaces
- Grafana dashboard best practices (anti-pattern analysis) — https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/
- Grafana anti-pattern article (Tempo dashboard cited) — https://chronosphere.io/learn/three-pesky-observability-anti-patterns-that-impact-developer-efficiency/
- npm doctor CLI pattern — https://docs.npmjs.com/cli/v7/commands/npm-doctor/
- React Native CLI doctor pattern — https://www.npmjs.com/package/@react-native-community/cli-doctor

---

*Research completed: 2026-04-22*
*Previous milestone's FEATURES.md archived as FEATURES-v1.2.md*
*Ready for roadmap: yes — 2 phases (foundation+CLI, Web UI), read-only milestone, no auth required*
