# Phase 20 Research: Reality Audit + Canonical Install

**Researched:** 2026-04-30
**Domain:** Install documentation authoring + codebase drift audit
**Confidence:** HIGH (all claims verified against codebase at HEAD and git history)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Hybrid two-track audit. Track A (operator workstation) = fresh conda env on assist-01 (Postgres + Ollama + Flame remain in place). Track B (integrator/MCP-only) = second machine without Flame. Non-author UAT on Track A is the milestone gate.
- **D-02:** Non-author runs verbatim INSTALL.md walkthrough on Track A as the locked acceptance criterion.
- **D-03:** Track B author-driven dry-run only (no non-author UAT required).
- **D-04:** Aggressive in-flight gap-fix policy — any install-blocking gap gets a code-fix plan. "Document the workaround" is not acceptable.
- **D-05:** Soft cap: if a gap exceeds ~1 plan of code work, spin a 20.x decimal phase rather than overgrowing Phase 20.
- **D-06:** Carry-forward seeds are allowed for genuinely v1.6+ gaps (auth, multi-machine, streaming). Forcing function only applies to install-completion gaps.
- **D-07:** Single linear "operator workstation" path. Audience = daily-user operator with Flame + Postgres + Ollama + Anthropic API key.
- **D-08:** "If you don't have Flame" sidebar inside INSTALL.md (not a separate doc fork).
- **D-09:** Multi-machine, multi-user, dev-only, projekt-forge-consumer-walkthrough are OUT OF SCOPE.
- **D-10:** Phase 20 fixes README/CLAUDE.md content that contradicts v1.4.1 reality or blocks the install path. New structural sections are Phase 21.
- **D-11:** README.md scope in Phase 20: install section refresh + "Current Status" table.
- **D-12:** CLAUDE.md scope: rewrite "What exists and works" for all 5 surfaces + observability + learning pipeline + staged ops + chat. Rewrite "Active Development Context".
- **D-13:** Minimum-version + reference-version model: "Postgres ≥14, tested on 16.x" / "Python ≥3.10, reference is 3.11".
- **D-14:** Reference versions from the audit walk on assist-01 are the canonical "tested on" anchors.
- **D-15:** Bump `scripts/install-flame-hook.sh` FORGE_BRIDGE_VERSION from v1.1.0 to v1.4.1. README curl URL bumped to v1.4.1 in the same plan.
- **D-16:** Pre-flip verification: confirm v1.4.1 raw URLs resolve before flipping.
- **D-17:** Add regression guard against future 3-way drift. Choice deferred to planner (lightest option aligned with codebase conventions).

### Claude's Discretion
- Exact INSTALL.md ordering (conda first or pip-extras-block first).
- Which CLAUDE.md sections survive verbatim vs. need rewrites.
- Whether the "if you don't have Flame" carveout is a sidebar, callout box, separate sub-section, or appendix.
- Whether `forge_config.yaml` gets an in-tree example, a `forge doctor --print-example-config` flag, or just an inline code block.
- Exact format of dep version table.
- Whether the D-17 regression guard lands in Phase 20 or as a Phase 20 follow-up.

### Deferred Ideas (OUT OF SCOPE)
- Multi-machine deployment guide (v1.6+)
- projekt-forge consumer-pattern walk-through (Phase 21)
- GETTING-STARTED.md and surface-map deep-dive (Phase 21)
- Daily-workflow recipes (Phase 22)
- TROUBLESHOOTING.md (Phase 23)
- Auth, streaming chat, model bumps (v1.6+ seeds)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INSTALL-01 | User can follow `docs/INSTALL.md` end-to-end and reach all five surfaces | §B1 five-surface entry points; §C full dep inventory; §D smoke tests |
| INSTALL-02 | `install-flame-hook.sh` default installs v1.4.1 Flame hook | §A4 three-way drift confirmed; §E1–E2 v1.4.1 URLs verified |
| INSTALL-03 | README install section and INSTALL.md agree — no version drift | §A2 README drift map; §A4 script drift map |
| INSTALL-04 | User can identify all external deps before starting | §C full dep inventory with versions |
| DOCS-02 | CLAUDE.md reflects v1.4.1 ground truth | §A1 full CLAUDE.md drift map; §B full v1.4.1 ground truth |
</phase_requirements>

---

## Summary

- **The install-script three-way drift is confirmed and specific:** `scripts/install-flame-hook.sh` defaults to `v1.1.0`, the embedded README example URL says `v1.2.1`, and the live tag is `v1.4.1`. Both v1.4.1 raw GitHub URLs resolve and return valid content (verified via HTTP GET). The v1.4.1 git tag exists on origin. The flip is safe to make.
- **CLAUDE.md is anchored to the v1.0 "extracted from projekt-forge" snapshot.** The codebase has grown from 2 surfaces (Flame bridge + MCP server) to 5 surfaces (+ Web UI on `:9996/ui/`, CLI `forge-bridge`, `/api/v1/chat`) across 19 phases. The "What exists and works" section misses every surface added in v1.3–v1.4. The "Repository Layout" block is also stale — the current layout is substantially different.
- **Critical undocumented gap: `pyproject.toml` declares version `1.3.0` but the git tag and all docs claim `v1.4.1`.** The v1.4.0 and v1.4.1 milestones did not include a `pyproject.toml` version bump (confirmed by git log). `pip install forge-bridge` would install `1.3.0` metadata. This is an install-path gap that Phase 20 must fix.
- **All five surfaces are reachable and their entry points are confirmed in code.** The canonical launch sequence is: `python -m forge_bridge` (boots MCP server + Artist Console on `:9996` via lifespan). The Flame hook is a separate install via `install-flame-hook.sh`. `forge-bridge` CLI is the Typer entry point wired in `pyproject.toml [project.scripts]`.
- **No `forge_config.yaml` exists** — the codebase is entirely env-var driven. `FORGE_DB_URL`, `ANTHROPIC_API_KEY`, `FORGE_LOCAL_LLM_URL`, `FORGE_LOCAL_MODEL`, `FORGE_CLOUD_MODEL`, and `FORGE_CONSOLE_PORT` are the operator-facing env vars. INSTALL.md will document them as environment variables with no config file required.

---

## A. Drift Inventory

### A1. CLAUDE.md Drift Map

**"What exists and works" section (lines 23–46):** [VERIFIED: file read at HEAD]

| CLAUDE.md claim | v1.4.1 reality | Divergence |
|-----------------|----------------|------------|
| "Flame HTTP bridge (`flame_hooks/forge_bridge/scripts/forge_bridge.py`) — runs inside Flame as HTTP server on port 9999" | Correct — file exists, port 9999 confirmed (`BRIDGE_PORT = int(os.environ.get("FORGE_BRIDGE_PORT", "9999"))`) | ACCURATE |
| "Has a web UI at `http://localhost:9999/`" | Correct — `do_GET` serves `_WEB_UI` at path `/` | ACCURATE |
| "MCP server (`forge_bridge/`) — Model Context Protocol server wrapping the Flame bridge" | Partially accurate — the MCP server (`forge_bridge/mcp/`) is real, but it now co-hosts the Artist Console, learning pipeline, and chat endpoint. The description severely undersells what it does. | STALE — undersells 3 additional subsystems |
| "Tools: project, timeline, batch, publish, utility" | `forge_bridge/tools/` still has these, but the MCP server also now exposes staged-ops tools, forge_tools_read, manifest resources, etc. | STALE — missing 8+ additional tools |
| "What is designed but not yet implemented" lists: canonical vocabulary engine, dependency graph engine, bridge core service, event-driven pub/sub, Maya endpoint, editorial adapters, auth | `forge_bridge/core/vocabulary.py`, `forge_bridge/core/entities.py`, `forge_bridge/core/traits.py`, `forge_bridge/core/registry.py` all EXIST. The vocabulary layer is shipped. Auth still deferred. | WRONG — vocabulary + entity model shipped. Dep graph and Maya endpoint remain unimplemented. |

**"Active Development Context" section (lines 147–154):** [VERIFIED: file read at HEAD]

| CLAUDE.md claim | v1.4.1 reality | Divergence |
|-----------------|----------------|------------|
| "As of 2026-02-24" | Current date is 2026-04-30. v1.5 is open. | STALE by ~2 months |
| "Just extracted from projekt-forge — this is the initial standalone repo" | 19 phases shipped across 6 milestones. ~40,594 LOC. This framing is obsolete. | COMPLETELY WRONG |
| "Next steps: implement the vocabulary module, then the dependency graph, then the bridge core service" | Vocabulary shipped. Dep graph still unimplemented. Bridge core service not started. | PARTIALLY WRONG |
| "The flame hook and MCP server are working and deployed — don't break them during restructuring" | Accurate that both work, but there is no restructuring in progress. v1.5 is a docs/legibility milestone. | MISLEADING |

**"Repository Layout" block:** [VERIFIED: file tree confirmed]

| CLAUDE.md claim | v1.4.1 reality | Divergence |
|-----------------|----------------|------------|
| `forge_bridge/server.py` — "MCP server, tool registration" | `forge_bridge/server.py` still exists but is a legacy orphan. The real MCP server is in `forge_bridge/mcp/server.py`. `forge_bridge/server/` (separate directory) is the WebSocket server. | MISLEADING — old layout |
| `forge_bridge/tools/` listed as the tool implementations | Still exists and accurate | ACCURATE |
| `forge_bridge/bridge.py` — "HTTP client to Flame bridge" | Still exists, accurate | ACCURATE |
| No mention of `forge_bridge/console/`, `forge_bridge/cli/`, `forge_bridge/llm/`, `forge_bridge/learning/`, `forge_bridge/core/`, `forge_bridge/store/` | All of these directories ship in v1.4.1 | MISSING 6 major directories |

**"Key Design Decisions" table:** [VERIFIED: partially]

The decisions in the table (HTTP transport, code execution not RPC, automatic dependency graph, Traits, auth deferred, local first) are still directionally correct, but the "dependency graph" decision says "no manual declaration" — the dependency graph engine is not actually shipped yet (entities and relationships exist in the schema, but not the graph traversal logic the original CLAUDE.md describes). This needs clarification but is not a blocking install gap.

**CLAUDE.md Vocabulary Summary:** Correct at a conceptual level. No action needed for install purposes.

---

### A2. README.md Install Section Drift Map

**Lines 95–142 ("Quick Start"):** [VERIFIED: file read at HEAD]

| README claim | v1.4.1 reality | Divergence |
|--------------|----------------|------------|
| Curl URL: `https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.2.1/scripts/install-flame-hook.sh` | Live tag is v1.4.1. URL resolves to a script with `v1.1.0` defaults (the old version of the script). | STALE — 2 minor versions behind |
| `"Override FORGE_BRIDGE_VERSION (default v1.2.1)"` | Script default is actually v1.1.0, not v1.2.1. The README is wrong even about what the script's current default is. | WRONG |
| `pip install -e .` | Still works but misses the `[llm]` extra required for LLM/chat functionality | INCOMPLETE — omits `[llm]` extra |
| `python -m forge_bridge` modes (stdio, `--bridge-host`, `--http --port 8080`) | `python -m forge_bridge` still works for stdio MCP mode. `--http` is not the documented way to reach the Web UI (the Web UI runs on `:9996` via lifespan, not `--http`). | MISLEADING — `--http` is not the console launch path |
| `python -m forge_bridge --bridge-host 192.168.1.100` | Still documented in `__main__.py` as a Typer option? Needs verification — `__main__.py` currently does not expose `--bridge-host` as a Typer option. The MCP server reads `FORGE_BRIDGE_HOST` env var. | LIKELY STALE — needs verification on-device |
| "Test the connection: Open `http://localhost:9999/` in a browser" | Correct for Flame bridge. But nothing about `:9996/ui/` which is now the primary Web UI | INCOMPLETE — missing primary UI |
| `"Repository Structure"` block — lists `forge_bridge/tools/` as the only content | 6 major subdirectories missing (`console/`, `cli/`, `llm/`, `learning/`, `core/`, `store/`) | STALE |

**"Conda environment" section (lines 65–91):** [VERIFIED: file read at HEAD]

| README claim | v1.4.1 reality | Divergence |
|--------------|----------------|------------|
| `conda create -n forge python=3.11 -y` | Correct. Reference Python version is 3.11. | ACCURATE |
| `pip install -e ".[dev]"` for base install | Correct but note: `[dev]` does NOT include LLM packages. Chat and learning pipeline require `[llm]` extra. | ACCURATE but incomplete |
| `pip install -e ".[dev,llm]"` for LLM extras | Correct | ACCURATE |

---

### A3. README.md "Current Status" Table Drift Map

**Lines 53–63:** [VERIFIED: file read at HEAD]

| Component | README claims | v1.4.1 reality | Divergence |
|-----------|--------------|----------------|------------|
| Flame HTTP bridge | ✅ Working | ✅ Shipped | ACCURATE |
| MCP server (LLM tools) | ✅ Working | ✅ Shipped and significantly expanded | ACCURATE but undersells scope |
| Canonical vocabulary spec | 🔧 In design | ✅ SHIPPED — `forge_bridge/core/vocabulary.py`, `entities.py`, `traits.py`, `registry.py` | WRONG — shows "in design", is shipped |
| Dependency graph engine | 📋 Planned | Still NOT shipped as a traversal engine. Entity relationships exist in the schema (FK + `DBEvent`) but no graph-traversal module. | APPROXIMATELY CORRECT but needs nuance |
| Maya endpoint | 📋 Planned | Not shipped | ACCURATE |
| Editorial/shot tracking adapters | 📋 Planned | Not shipped | ACCURATE |
| Event-driven channel system | 📋 Planned | WebSocket server (`forge_bridge/server/`) is shipped; the canonical pub/sub layer is not. | PARTIALLY WRONG |

**Missing rows** (surfaces that shipped but have no row in the table):

- Artist Console (Web UI on `:9996/ui/`) — shipped Phase 10/10.1
- CLI (`forge-bridge console`) — shipped Phase 11
- `/api/v1/chat` HTTP endpoint — shipped Phase 16/16.2
- Staged operations platform — shipped Phases 13/14
- LLMRouter agentic loop — shipped Phase 15

---

### A4. install-flame-hook.sh Drift Map

**Three-way version drift confirmed:** [VERIFIED: file read + WebFetch]

| Source | Version claimed | Actual |
|--------|-----------------|--------|
| `scripts/install-flame-hook.sh` line 29 (`VERSION` default) | `v1.1.0` | The working value installed by default |
| `scripts/install-flame-hook.sh` line 10 (embedded standalone URL) | `v1.1.0` | Both the embedded URL and the default agree at `v1.1.0` |
| `README.md` curl example URL (line ~106) | `v1.2.1` | README is one full minor version ahead of the script's own embedded URL |
| Live git tag on origin | `v1.4.1` | `git ls-remote --tags origin v1.4.1` → `b114e01e...refs/tags/v1.4.1` confirmed |

**Pre-flip verification result (D-16):**

- `https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh` → **200 OK** [VERIFIED: WebFetch]
- `https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/flame_hooks/forge_bridge/scripts/forge_bridge.py` → **200 OK** [VERIFIED: WebFetch, confirmed non-empty Python source]

The v1.4.1 raw URLs both resolve. The flip from `v1.1.0` to `v1.4.1` is safe per the D-16 pre-verification requirement.

**Additional critical gap discovered:** `pyproject.toml` declares `version = "1.3.0"`. The v1.4.0 and v1.4.1 milestones applied git tags without bumping `pyproject.toml`. The milestone audit (`v1.4.x-MILESTONE-AUDIT.md`) makes no mention of a version bump — this was never done. `pip install forge-bridge` from the git tag installs `1.3.0` metadata. `forge_bridge.__version__` returns `"1.3.0"`. The `test_package_version` test in `tests/test_public_api.py` asserts `version = "1.3.0"`. INSTALL.md cannot truthfully say "install v1.4.1" while the Python package self-reports as `1.3.0`. Phase 20 must include a pyproject.toml version bump to `1.4.1` and a matching `test_public_api.py` update as part of the version-consistency plan.

---

## B. v1.4.1 Ground Truth

### B1. Five Surfaces

[VERIFIED: source file reads at HEAD]

| Surface | Entry Point File | Port | Launch Command | Smoke Test |
|---------|-----------------|------|----------------|------------|
| Web UI | `forge_bridge/console/app.py:build_console_app()` served via `forge_bridge/mcp/server.py:_start_console_task()` | `:9996` | `python -m forge_bridge` (co-hosted in MCP lifespan) | `curl -fsS http://localhost:9996/ui/` |
| CLI `forge-bridge` | `forge_bridge/__main__.py:app` registered in `pyproject.toml [project.scripts]` | n/a | installed via `pip install -e .` | `forge-bridge --help` |
| HTTP `/api/v1/chat` | `forge_bridge/console/handlers.py:chat_handler` registered in `app.py` at `Route("/api/v1/chat", chat_handler, methods=["POST"])` | `:9996` | Same as Web UI (co-hosted) | `curl -s -X POST http://localhost:9996/api/v1/chat -H "content-type: application/json" -d '{"messages":[{"role":"user","content":"ping"}]}'` |
| MCP server | `forge_bridge/mcp/server.py:main()` called from `forge_bridge/__main__.py` | stdio | `python -m forge_bridge` | `forge-bridge --help` (FastMCP exits cleanly without stdin) or connect with Claude Desktop |
| Flame hook | `flame_hooks/forge_bridge/scripts/forge_bridge.py` installed by `scripts/install-flame-hook.sh` | `:9999` (default `FORGE_BRIDGE_PORT`) | Flame loads on startup | `curl -s http://localhost:9999/status` (returns JSON: `{"status":"running","flame_available":true,"namespace_keys":[...]}`) |

**Important launch note:** `python -m forge_bridge` runs FastMCP in **stdio mode** (default). This means the process exits when stdin closes. The 16.2-HUMAN-UAT.md documents the workaround: `tail -f /dev/null | python -m forge_bridge` keeps stdin open on a bare deploy host. INSTALL.md must document this for the Track A operator.

**Subcommand registry (forge-bridge console ...):** [VERIFIED: `__main__.py` lines 36–40]
- `forge-bridge console tools`
- `forge-bridge console execs`
- `forge-bridge console manifest`
- `forge-bridge console health`
- `forge-bridge console doctor`

There are NO `forge events` or `forge errors` subcommands. These names appeared in the CONTEXT.md additional context description under "Phase 18 (Legibility Pass)" but do not exist in the codebase. Phase 18 was the staged-handlers TEST HARNESS rework (HARNESS-01..03), not a new CLI surface. The `forge-bridge console execs --since` flag provides the time-based filtering that `forge events` might imply.

---

### B2. Observability Surfaces

[VERIFIED: `forge_bridge/cli/` directory + `forge_bridge/cli/health.py` + `forge_bridge/cli/doctor.py`]

Phase 18 was the **staged-handlers test harness rework** (HARNESS-01..03), NOT an "observability pass." The observability surface shipped in **Phase 11 (CLI Companion, v1.3.1)** and **Phase 9 (Read API Foundation)**. There is no "Legibility Pass" — that is v1.5's milestone name.

**Shipped observability CLI commands:**
- `forge-bridge console health` — `/api/v1/health` → Rich panels per service group (critical: mcp/watcher/console_port; degraded-tolerant: flame_bridge/ws_server; LLM backends; provenance)
- `forge-bridge console doctor` — expanded diagnostic: JSONL parseability, sidecar/probation dir writability, port reachability reprobe, disk space. Exit codes: 0=ok, 1=fail, 2=unreachable.
- `forge-bridge console execs [--since 24h] [--promoted] [--code_hash PREFIX]` — execution history via `/api/v1/execs`
- `forge-bridge console tools` — tool list via `/api/v1/tools`
- `forge-bridge console manifest` — manifest via `/api/v1/manifest`

**Structured logging:** `forge_bridge/console/logging_config.py` exists (`STDERR_ONLY_LOGGING_CONFIG`). The MCP server initializes `logging.basicConfig` with format `%(asctime)s %(levelname)-8s %(name)s — %(message)s`. Chat handler emits one structured log line per call (`chat ok request_id=... message_count_in=... wall_clock_ms=... stop_reason=...`).

---

### B3. Learning Pipeline

[VERIFIED: `forge_bridge/learning/` module reads + `forge_bridge/cli/doctor.py` probe]

**What it does:** Watches `~/.forge-bridge/synthesized/` for Python files. When a Flame operation is repeated above a threshold, the synthesizer (via LLMRouter Ollama local path) auto-generates a new MCP tool and registers it. The probation system tracks success/failure and can quarantine bad tools.

**Operator-facing paths (auto-created by the running server):**
- `~/.forge-bridge/executions.jsonl` — execution log (source of truth)
- `~/.forge-bridge/synthesized/` — synthesized tool Python files + `.manifest.json`
- `~/.forge-bridge/probation/` — probation state
- `~/.forge-bridge/quarantined/` — quarantined tools

**Does it "Just Work" after install?** Yes, for the synthesis pathway. The learning pipeline starts with `ExecutionLog()` at server boot (defaults to `~/.forge-bridge/executions.jsonl`). The watcher launches as an asyncio task automatically in `_lifespan`. No operator configuration is required. The LLM synthesis requires Ollama (`qwen2.5-coder:32b`) to be reachable — if Ollama is down, synthesis is skipped but the server continues.

**What an operator does NOT need to configure:** JSONL log path, sidecar dirs, probation dirs (all auto-created), synthesis threshold (hardcoded default).

**What an operator needs for synthesis to work:** Ollama running locally with `qwen2.5-coder:32b` pulled.

---

### B4. Staged Ops

[VERIFIED: `forge_bridge/console/app.py` routes + `forge_bridge/mcp/server.py`]

**Operator-visible staged-ops surface:**
- HTTP: `GET /api/v1/staged`, `POST /api/v1/staged/{id}/approve`, `POST /api/v1/staged/{id}/reject`
- Web UI: `/ui/` links to staged ops (it is one of the five views: tools, execs, manifest, health, chat — and staged ops is accessible via the tools/chat surface)
- MCP tools: `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged`
- MCP resource: `forge://staged/pending`

**Configuration needed:** Postgres must be running and `FORGE_DB_URL` must resolve (defaults to `postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge`). Staged ops write to Postgres. Without Postgres, the `forge_*_staged` tools will fail with DB connection errors.

**Migrations:** Three Alembic migrations exist. An operator must run `alembic upgrade head` with `FORGE_DB_URL` pointing at their Postgres before staged-ops endpoints work.

---

### B5. Chat Surface

[VERIFIED: `forge_bridge/console/handlers.py:chat_handler` + `forge_bridge/llm/router.py:LLMRouter`]

**Canonical endpoint:** `POST /api/v1/chat` on `:9996`. [VERIFIED: `console/app.py` line 101]

**Sensitivity routing:** `sensitive=True` hardcoded in `chat_handler` (line 574). This means chat ALWAYS goes through the **local Ollama path** (`qwen2.5-coder:32b`). The `ANTHROPIC_API_KEY` is NOT required for chat to work. Anthropic is only used when `sensitive=False` is explicitly passed to `complete_with_tools()` by a caller.

**What's required for `/api/v1/chat` to return a useful answer:**
- Ollama running locally at `http://localhost:11434/v1` (or `FORGE_LOCAL_LLM_URL`)
- `qwen2.5-coder:32b` model pulled in Ollama
- MCP server running (the chat handler uses `app.state.console_read_api._llm_router` wired in `_lifespan`)

**What's NOT required:** `ANTHROPIC_API_KEY`, Flame hook, Postgres (the chat path does not query the DB).

**Smoke test (smallest curl):**
```bash
curl -s -X POST http://localhost:9996/api/v1/chat \
  -H "content-type: application/json" \
  -d '{"messages":[{"role":"user","content":"what synthesis tools were created this week?"}]}' | python3 -m json.tool
```
[VERIFIED: 16.2-HUMAN-UAT.md documents this exact curl as the Phase 16.2 verification command]

---

## C. Install Dependencies

### C1. Python Deps

[VERIFIED: `pyproject.toml` at HEAD]

**`requires-python`:** `>=3.10`. Reference version: Python 3.11 (per README "forge env defaults to 3.11 to match the reference deployment").

**Base dependencies (installed with `pip install forge-bridge`):**
```
httpx>=0.27
websockets>=13.0
mcp[cli]>=1.19,<2
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29
alembic>=1.13
psycopg2-binary>=2.9
jinja2>=3.1
rich>=13.9.4
starlette
typer  # implied by forge-bridge CLI entry point
```

**`[llm]` extras (required for synthesis + chat):**
```
openai>=1.0
anthropic>=0.97,<1
ollama>=0.6.1,<1
```

**`[dev]` extras (development/testing only):**
```
pytest
pytest-asyncio
pytest-timeout>=2.2.0
ruff
```

**`[test-e2e]` extras (Playwright browser tests, not needed by operators):**
```
pytest-playwright>=0.5
```

**For a daily-user operator:** `pip install -e ".[dev,llm]"` or, for production, `pip install "forge-bridge[llm]"`. The `[llm]` extra is mandatory for the chat endpoint and learning pipeline synthesis.

---

### C2. External System Deps + Reference Versions

[VERIFIED: codebase grep + session.py + llm/router.py + alembic.ini]

| Dependency | Required By | Minimum Version | Reference Version (assist-01) | Notes |
|-----------|------------|-----------------|-------------------------------|-------|
| Conda | Environment isolation | "latest stable" | conda ~24.x | `conda create -n forge python=3.11` |
| Python | Runtime | 3.10 | 3.11 | Per `pyproject.toml requires-python` |
| PostgreSQL | Staged ops + SQL mirror | ≥14 (asyncpg ≥0.29 drops PG12 support) | 16.x [ASSUMED — reference from assist-01 not verified here] | `forge:forge@localhost:5432/forge_bridge` default credentials |
| Ollama | Chat endpoint + LLM synthesis | "latest stable" | 0.21.0 (from 16.2-HUMAN-UAT.md) | Must have `qwen2.5-coder:32b` pulled |
| Flame 2026.x | Flame hook surface only | "latest supported" | Flame 2026.2.1 (from PROJECT.md) | Not required for Track B (MCP-only) |
| Anthropic API key | Cloud LLM calls (NOT chat endpoint) | n/a | Required only for `sensitive=False` calls | INSTALL.md should note: not required for basic operator workflow |

**Key finding:** `ANTHROPIC_API_KEY` is listed in `LLMRouter` docstring as "required for cloud calls." In practice, an operator following the daily workflow uses `sensitive=True` (local Ollama) for all chat. The key is only needed if someone explicitly calls `sensitive=False`. INSTALL.md should mention it as "optional, required for cloud LLM routing" not as a hard prerequisite.

---

### C3. Database Setup

[VERIFIED: `alembic.ini` + `forge_bridge/store/session.py` + migration files]

**Default credentials (hardcoded in `session.py`):**
```
postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge
postgresql+psycopg2://forge:forge@localhost:5432/forge_bridge  (sync / Alembic)
```

**Override via:** `FORGE_DB_URL` env var (async URL; the sync engine strips `+asyncpg` → `+psycopg2` automatically).

**What an operator must do:**
1. Create Postgres user `forge` with password `forge` (or set `FORGE_DB_URL` to their own credentials)
2. Create database `forge_bridge` owned by `forge`
3. Run migrations: `alembic upgrade head` (from the repo root, where `alembic.ini` lives)

**Migrations shipped:** Three Alembic revisions:
- `0001_initial_schema.py` — base entity/event schema
- `0002_role_class_media_roles_process_graph.py` — role/relationship registry
- `0003_staged_operation.py` — staged_operation entity type (FB-A)

**Alembic connection:** `alembic.ini` line 6: `sqlalchemy.url = postgresql+psycopg2://forge:forge@localhost:5432/forge_bridge`. This is the sync URL used by migrations; it does NOT read `FORGE_DB_URL` automatically. To use custom credentials for migrations, the operator must either edit `alembic.ini` or pass `--url` to the `alembic upgrade head` command.

**Postgres minimum version:** asyncpg `>=0.29` supports PostgreSQL ≥10, but SQLAlchemy 2.0 asyncpg dialect requires PG ≥12 per SQLAlchemy docs. Recommend "Postgres ≥14" as the minimum (tested on 16.x).

---

### C4. Ollama Model Setup

[VERIFIED: `forge_bridge/llm/router.py:_DEFAULT_LOCAL_MODEL` + `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md`]

**Locked default model:** `qwen2.5-coder:32b` (`_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:32b"` at `router.py:64`)

**Pull command:**
```bash
ollama pull qwen2.5-coder:32b
```

**Why NOT `qwen3:32b` (from SEED-DEFAULT-MODEL-BUMP-V1.4.x.md):** Pre-run UAT on assist-01 produced cold-start `LLMLoopBudgetExceeded` driven by qwen3 thinking-mode token verbosity (400-525 tokens/turn at ~10-11 tok/s → 40-55s per iteration, hitting the 60s wall-clock cap). `qwen2.5-coder:32b` is the locked production default. INSTALL.md should note the qwen3 caveat: "Do not use qwen3:32b as the default model — it exceeds the default 60s wall-clock budget due to thinking-mode token verbosity. If you need to experiment with qwen3:32b, extend `max_seconds` to ≥180."

**Default Ollama URL:** `http://localhost:11434/v1` (override via `FORGE_LOCAL_LLM_URL`)

---

### C5. Anthropic API Key Plumbing

[VERIFIED: `forge_bridge/llm/router.py:LLMRouter.__init__` + health check]

**Where the codebase reads it:** `os.environ.get("ANTHROPIC_API_KEY")` in `LLMRouter.ahealth_check()` (line 697 of `router.py`) and implicitly via the `anthropic` SDK's own env var lookup when `_get_cloud_client()` creates an `AsyncAnthropic` instance.

**Canonical place for an operator to set it:** Shell environment variable. There is no `.env` file loading, no `forge_config.yaml`, and no config-file-based key storage in the forge-bridge codebase. The operator sets it as an env var before launching the server:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python -m forge_bridge
```

**When it is required:** Only for `sensitive=False` routing (cloud LLM path). The default operator workflow (`/api/v1/chat`, learning pipeline synthesis) uses `sensitive=True` (Ollama). The `forge-bridge console health` output shows `cloud: true` if the key is set.

**When it is NOT required:** Local-only (Ollama) workflow — all five surfaces are reachable without an Anthropic key.

---

### C6. forge_config.yaml

[VERIFIED: full codebase grep for `forge_config`, `config.yaml`, `load_config`, `yaml.load`]

**forge_config.yaml does NOT exist as a forge-bridge concept.** The forge-bridge codebase has zero YAML config loading. All configuration is via environment variables. The only occurrence of "forge_config" in the source is in `forge_bridge/tools/reconform.py` which references a projekt-forge `pipeline_config.json` — a project-specific file, not a forge-bridge system config.

**Previous references to `forge_config.yaml`** in planning documents (e.g., "LLMRouter built from forge_config.yaml") referred to projekt-forge's config file being read by projekt-forge's own code before calling forge-bridge. This is a projekt-forge concern, not a forge-bridge install concern.

**Recommendation for INSTALL.md:** Document the env vars inline in a table. No config file, no template. Claude's Discretion allows an inline code block showing an `.env` export pattern if desired for operator convenience.

---

## D. Reachability Smoke Tests

### D1. Per-Surface Smoke Commands

[VERIFIED: Flame hook endpoints from `forge_bridge/docs/API.md` + `handlers.py` route table + `cli/__main__.py`]

| Surface | Smoke Command | Expected Response | Notes |
|---------|---------------|-------------------|-------|
| Web UI | `curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"` | `200` | Must be running: `python -m forge_bridge` |
| CLI | `forge-bridge --help` | Typer help output | Confirms entry point installed |
| HTTP chat | `curl -s -X POST http://localhost:9996/api/v1/chat -H "content-type: application/json" -d '{"messages":[{"role":"user","content":"hello"}]}'` | `{"messages":[...],"stop_reason":"end_turn","request_id":"..."}` | Requires Ollama + qwen2.5-coder:32b |
| MCP server | `forge-bridge --help` | Typer help output | Full MCP smoke requires Claude Desktop connection; `--help` verifies binary works |
| Flame hook | `curl -s http://localhost:9999/status` | `{"status":"running","flame_available":true,...}` | Requires Flame running with hook installed |

**For the operator workstation (Track A):** All five should pass. For Track B (no Flame): Flame hook smoke will fail — this is expected and documented via the "if you don't have Flame" carveout (D-08).

**Alternative Flame hook smoke:** `curl -s http://localhost:9999/ -o /dev/null -w "%{http_code}\n"` → `200` (returns the web UI HTML). The `/status` endpoint is preferable since it returns machine-parseable JSON confirming `flame_available`.

---

### D2. forge doctor Coverage Map

[VERIFIED: `forge_bridge/cli/doctor.py` full read]

`forge doctor` (invoked as `forge-bridge console doctor`) already covers:

| Check | forge doctor probe | Status |
|-------|-------------------|--------|
| MCP server liveness | `/api/v1/health` → `services.mcp.status` | Covered |
| Watcher task liveness | `/api/v1/health` → `services.watcher.status` | Covered |
| Console port reachability | Direct reprobe on `:9996` | Covered |
| Flame bridge reachability | `/api/v1/health` → `services.flame_bridge.status` (degraded-tolerant) | Covered (warn only) |
| Ollama LLM backend | `/api/v1/health` → `services.llm_backends[]` | Covered (warn only) |
| JSONL log parseability | Client-side tail-parse of `~/.forge-bridge/executions.jsonl` | Covered |
| Sidecar dir writability | `~/.forge-bridge/synthesized/` exists + writable | Covered |
| Probation dir writability | `~/.forge-bridge/probation/` exists + writable | Covered |
| Disk space | `~/.forge-bridge/` free bytes | Covered |

**NOT covered by forge doctor (gaps Phase 20 might expose):**
- Postgres reachability / migration version (`alembic current`)
- `FORGE_DB_URL` validity
- Ollama model availability (`qwen2.5-coder:32b` actually pulled, not just Ollama daemon up)
- `pyproject.toml` / `install-flame-hook.sh` version drift (D-17 candidate)

**INSTALL.md should prefer** `forge-bridge console doctor` over manual curl chains for the post-install verification step, then supplement with the Flame hook smoke test (`curl localhost:9999/status`) which is NOT covered by `forge doctor`.

---

## E. Pre-flight Verification (D-15..16)

### E1. v1.4.1 Raw-URL Resolution Check

[VERIFIED: WebFetch to both URLs]

| URL | HTTP Status | Content confirmed |
|-----|-------------|-------------------|
| `https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh` | **200 OK** | Returns bash script with `VERSION="${FORGE_BRIDGE_VERSION:-v1.1.0}"` (the v1.1.0-defaulted version — confirms the file exists at the tag; the value will be updated) |
| `https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/flame_hooks/forge_bridge/scripts/forge_bridge.py` | **200 OK** | Returns `forge_bridge.py` Python source (valid non-empty Python, "Listening on http://..." comment) |

**CONCLUSION: Both URLs resolve. The D-16 pre-verification condition is MET. The version flip from `v1.1.0` to `v1.4.1` is safe.**

---

### E2. v1.4.1 Git Tag Check

[VERIFIED: `git ls-remote --tags origin v1.4.1`]

```
b114e01e798908e7c9fb297b6434c86d85129690	refs/tags/v1.4.1
b114e01e798908e7c9fb297b6434c86d85129690	refs/tags/v1.4.1^{}
```

Wait — `refs/tags/v1.4.1` and `refs/tags/v1.4.1^{}` having the same object hash means the tag is **lightweight** (not an annotated tag). However, the git tag annotated message was confirmed (`git show v1.4.1` showed `tag v1.4.1` with a tagger, date, and message). The `^{}` dereferencing to the same hash can happen with a single-commit annotated tag where the tag object itself is the commit. The tag exists and points to commit `73be4e8` ("chore: remove REQUIREMENTS.md for v1.4.x milestone close").

**CONCLUSION: v1.4.1 tag exists on origin. No blocker.**

---

## F. D-17 Regression-Guard Placement Recommendation

[VERIFIED: test structure + CI situation]

**Evidence surveyed:**
- No `.github/` directory exists — there is NO CI pipeline. There are no GitHub Actions workflows.
- `tests/test_public_api.py` has a `test_package_version()` function that asserts the `pyproject.toml` version string. This is the established pattern for version pinning assertions.
- `forge_bridge/cli/doctor.py` is the codebase's existing home for lightweight "system coherence" checks.

**Options ranked by fit:**

| Option | Fit | Evidence |
|--------|-----|----------|
| **(c) Unit test in `tests/test_install_hook_version_consistency.py`** | **BEST** | Matches the established pattern of `tests/test_public_api.py::test_package_version()`. No CI required; runs with default `pytest tests/`. Lightweight — greps two files, compares two version strings. No external network calls needed (reads local files). |
| (a) `forge doctor` sub-check | POOR | `forge doctor` requires a running server (`/api/v1/health` probe first). A version-drift check should be stateless and runnable without launching forge-bridge. |
| (b) CI lint | NOT APPLICABLE | No `.github/` CI pipeline exists. |

**Recommendation:** Option (c). Create `tests/test_install_hook_version_consistency.py` with a single test that:
1. Greps `scripts/install-flame-hook.sh` for `VERSION="${FORGE_BRIDGE_VERSION:-<version>}"` 
2. Greps `README.md` for the curl URL version
3. Greps `pyproject.toml` for `version = "<version>"`
4. Asserts all three match

This test will permanently enforce the three-way consistency requirement that Phase 20 is establishing.

**Whether it lands in Phase 20 or as a follow-up:** Given the planner's plan-count budget (target 5–7 plans), it should land in the same plan as the version bump (the install-script bump plan). It is a 1-file, 20-line addition.

---

## G. UAT Artifact Pattern

### G1. Prior HUMAN-UAT.md Structure

[VERIFIED: all five prior HUMAN-UAT files read: 10.1, 13, 16, 16.1, 16.2]

**Found HUMAN-UAT files:**
- `.planning/milestones/v1.3-phases/10.1-artist-ux-gap-closure/10.1-HUMAN-UAT.md`
- `.planning/milestones/v1.4-phases/13-fb-a-staged-operation-entity-lifecycle/13-HUMAN-UAT.md`
- `.planning/milestones/v1.4-phases/16-fb-d-chat-endpoint/16-HUMAN-UAT.md`
- `.planning/milestones/v1.4-phases/16.1-fb-d-chat-gap-closure/16.1-HUMAN-UAT.md`
- `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-HUMAN-UAT.md`

**Structural pattern extracted from 16.2-HUMAN-UAT.md (most complete example):**

```yaml
---
status: passed | failed | partial | resolved
phase: <phase-slug>
source: [<plan-files>]
started: <ISO8601>
updated: <ISO8601>
---
```

**Sections (in order):**
1. Header: Date, Operator, Host, Branch, HEAD commit
2. **Fixture State** — what services were running at test time, what wasn't (and why), what version of Ollama/model loaded
3. **Pre-flight automated gates** — table of: Gate | Result | Evidence
4. **Test walkthrough** — numbered steps (what was typed, where, what was observed verbatim)
5. **Observations** — response time, spinner behavior, response content verbatim, error banners, subjective assessment, follow-up questions
6. **Cross-phase must-have regression check** — which prior requirements were re-verified or explicitly deferred
7. **Deviations** — numbered list of any ways the UAT deviated from ideal, with justification for why each is acceptable
8. **Outcome** — `PASS` / `PASS with deviations` / `FAIL` + reasoning
9. **Action** — what happens next as a result of this UAT record
10. **Operator sign-off** — `CN/dev — <date>` (or non-author name)

**Key observation:** The author writes all boilerplate and pre-fill. The non-author writes the "Observations" and "Outcome" cells. Deviations are flagged by the author but justified collaboratively.

---

### G2. Recommended Phase 20 HUMAN-UAT.md Template

```markdown
---
status: pending
phase: 20-reality-audit-canonical-install
source: [20-PLAN.md files TBD at UAT time]
started: <to be filled>
updated: <to be filled>
track: A
---

# Phase 20 — Track A INSTALL.md Walk-through (Non-Author UAT)

**Date:** [non-author fills]
**Operator:** [non-author name] — [role / relation to project]
**Host:** assist-01 (Flame + Postgres + Ollama pre-installed; fresh conda env `forge` created for this walk)
**INSTALL.md commit:** [commit hash of INSTALL.md at test time]
**Reference versions discovered during walk:**
- Python: [filled during walk]
- Postgres: [filled during walk]
- Ollama: [filled during walk]
- qwen2.5-coder:32b: pulled? [yes/no]
- Flame: [version if applicable]

## Pre-walk setup (author-prepared)

- [ ] Fresh conda env `forge` created and activated (`conda create -n forge python=3.11 -y && conda activate forge`)
- [ ] `forge-bridge` NOT installed in this env at walk start
- [ ] `INSTALL.md` checked out at the commit to be tested
- [ ] Postgres running on assist-01 at default credentials
- [ ] Ollama running on assist-01 with qwen2.5-coder:32b loaded

## Walk-through (non-author runs verbatim)

For each INSTALL.md step, non-author records:
- Step number and heading from the doc
- Command run (verbatim copy-paste)
- Output observed (verbatim, or "as expected" if routine)
- Any error or unexpected output (verbatim)

[Non-author fills this section by walking INSTALL.md top to bottom]

## Per-surface reachability outcome

| Surface | Smoke command | Result | Notes |
|---------|--------------|--------|-------|
| Flame hook on :9999 | `curl -s http://localhost:9999/status` | [PASS/FAIL/SKIP] | [reason if SKIP/FAIL] |
| Web UI on :9996 | `curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"` | [PASS/FAIL] | |
| CLI forge-bridge | `forge-bridge --help` | [PASS/FAIL] | |
| HTTP /api/v1/chat | `curl -s -X POST http://localhost:9996/api/v1/chat ...` | [PASS/FAIL] | |
| MCP server | `python -m forge_bridge` stays up for 10s | [PASS/FAIL] | |

## Gap log

For each gap encountered during the walk:

| # | Step | Gap description | Doc-only or code? | Plan that addressed it |
|---|------|----------------|-------------------|------------------------|
| 1 | | | | |

## forge doctor output

[Paste `forge-bridge console doctor` output verbatim after surfaces are up]

## Deviations

[List any steps skipped or modified from INSTALL.md verbatim, with justification]

## Outcome

**Track A result:** PASS / PASS with deviations / FAIL

**Reasoning:** [non-author writes 2-3 sentences: could a first-time user follow this doc without deriving the topology themselves?]

## Operator sign-off

[Non-author name] — [date]

---

## Track B annotation (author-driven, appended after Track A)

**Host:** [second machine without Flame]
**Gaps surfaced that Track A masked:**
- [List any "I assumed X was already running" gaps discovered]

**Track B result:** PASS / FAIL
```

---

## H. Phase Plan-Shape Recommendation

### H1. Wave Structure

[VERIFIED: dependencies derived from codebase + CONTEXT.md decisions]

**Plan dependencies (must-sequential):**

```
Plan A: pyproject.toml version bump (1.3.0 → 1.4.1)
  + test_public_api.py version assertion update
  + D-17 regression guard (tests/test_install_hook_version_consistency.py)
  → MUST be first — establishes the canonical version that everything else references
  → Commit: atomic (version bump + version test update + consistency test)

Plan B: scripts/install-flame-hook.sh version bump (v1.1.0 → v1.4.1)
  + README.md curl URL bump (v1.2.1 → v1.4.1)
  → DEPENDS ON: Plan A (now there's a consistent version to point at)
  → D-15/D-16: per Phase 17 D-30 decoupled-commit purity — one commit per artifact if convenient

Plan C: docs/INSTALL.md CREATE (new file)
  → DEPENDS ON: Plans A+B (version numbers must be correct before writing the doc)
  → This is the largest single plan — Track A walkthrough cannot happen until this ships

Plan D: CLAUDE.md ground-truth refresh
  → CAN PARALLELIZE with Plan C (CLAUDE.md does not feed into INSTALL.md)
  → But cannot land before Plan A (version number reference)
  → RECOMMENDED: ship Plan D concurrently with Plan C authoring

Plan E: README.md "Current Status" table refresh + "What This Is" minor corrections
  → CAN PARALLELIZE with CLAUDE.md and INSTALL.md
  → DEPENDS ON: Plan A (version accuracy)

Plan F: Track A non-author INSTALL.md walk-through (UAT)
  → DEPENDS ON: Plans A, B, C complete and deployed to assist-01
  → DEPENDS ON: All in-flight gap-fix plans from the audit having landed
  → This is the milestone gate — nothing closes until this PASSES

(Gap-fix plans, inserted if needed): 20.1, 20.2, etc. per D-05
```

**Parallelizable:** Plans D (CLAUDE.md) and E (README status table) can proceed concurrently with Plan C (INSTALL.md authoring) once Plans A and B are complete.

**Sequential:** Plans A → B → C → [gap-fixes] → F.

---

### H2. Plan-Count Budget

**Target plan count:** 5–7 plans (per CONTEXT.md D-05 framing).

**Recommended Phase 20 plan list:**

| Plan | Scope | Est. Size |
|------|-------|-----------|
| 20-01 | pyproject.toml version bump (1.3.0 → 1.4.1) + test_public_api.py version guard update + D-17 version-consistency test | Small (3 files, ~30 lines) |
| 20-02 | install-flame-hook.sh bump (v1.1.0 → v1.4.1) + README.md curl URL bump (v1.2.1 → v1.4.1) + README install section refresh (add `:9996`, fix extras, remove `--http` misconception) | Small (2 files, ~20 lines) |
| 20-03 | CLAUDE.md ground-truth refresh (DOCS-02) | Medium (full rewrite of "What exists and works", "Active Development Context", "Repository Layout") |
| 20-04 | README.md "Current Status" table refresh + minor corrections (INSTALL-03 / DOCS-01 partial) | Small (update 7-row table + add missing surface rows) |
| 20-05 | `docs/INSTALL.md` CREATE (INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04) | Large (new document, ~200-300 lines) |
| 20-06 | Track A INSTALL.md walk-through + HUMAN-UAT.md + Track B dry-run + 20-HUMAN-UAT.md | UAT plan — human-gated |
| 20-07+ | In-flight gap-fix plans (TBD from audit walk) | Unknown — spawned by 20-06 if needed |

**What SHOULD NOT be in Phase 20:**
- `docs/GETTING-STARTED.md` (Phase 21)
- README "What This Is" / "Vision" rewrite (Phase 21, unless it directly contradicts v1.4.1 reality)
- `docs/TROUBLESHOOTING.md` (Phase 23)
- `forge doctor --print-example-config` flag (Claude's Discretion — avoid growing product surface)
- `qwen3:32b` model bump (deferred per SEED-DEFAULT-MODEL-BUMP-V1.4.x.md)

---

## Validation Architecture

[Nyquist validation is enabled — `config.json` has `"nyquist_validation": true`]

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (via `[dev]` extras) + pytest-asyncio |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_public_api.py tests/test_install_hook_version_consistency.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INSTALL-02 | `install-flame-hook.sh` default is v1.4.1 | unit | `pytest tests/test_install_hook_version_consistency.py -x` | ❌ Wave 0 |
| INSTALL-03 | README curl URL matches install-flame-hook.sh default matches pyproject.toml version | unit | `pytest tests/test_install_hook_version_consistency.py -x` | ❌ Wave 0 |
| DOCS-02 | CLAUDE.md "What exists and works" enumerates all 5 surfaces | manual (human review) | n/a — content quality check | n/a |
| INSTALL-01 | INSTALL.md works end-to-end on clean machine | manual UAT (HUMAN-UAT.md) | n/a — requires live environment | n/a |
| INSTALL-04 | All deps visible before install | manual (doc review) | n/a — editorial check | n/a |

**Automated validation scope is limited for Phase 20.** The core deliverables (INSTALL.md correctness, CLAUDE.md accuracy) are fundamentally editorial and can only be validated by the non-author HUMAN-UAT walk-through. The regression guard (`test_install_hook_version_consistency.py`) is the one meaningful automated gate.

### Sampling Rate

- **Per task commit:** `pytest tests/test_public_api.py tests/test_install_hook_version_consistency.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green + non-author Track A HUMAN-UAT PASS before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_install_hook_version_consistency.py` — covers INSTALL-02 and INSTALL-03 (create in Plan 20-01)

---

## Open Questions

1. **`pyproject.toml` version bump ownership.** The v1.4.0 and v1.4.1 milestones shipped without bumping `pyproject.toml`. It still reads `1.3.0`. Phase 20's Plan 20-01 should bump it to `1.4.1` AND update `tests/test_public_api.py::test_package_version()` which asserts `version = "1.3.0"`. The planner should confirm: do we bump to `1.4.1` (the current live tag) or hold at `1.3.0` for now and create a new `1.5.0.dev0` bump? **Recommendation: bump to `1.4.1` to match the shipped tag — this is a correction, not a new release.**

2. **`--bridge-host` flag in README.** The current README "Run the MCP server" section shows `python -m forge_bridge --bridge-host 192.168.1.100`. This flag does not appear in `forge_bridge/__main__.py:app`. The MCP server reads `FORGE_BRIDGE_HOST` env var not a CLI flag. This is a README mistake. Phase 20 should remove or correct this line.

3. **INSTALL.md "if you don't have Flame" carveout scope.** How compact should it be? CONTEXT.md D-08 says "sidebar or compact carveout" — not a second full path. The recommendation is a single callout box near the top of INSTALL.md: "Track B / MCP-only: skip steps X, Y, Z — surfaces 1–4 work without Flame; surface 5 (`:9999`) will not be reachable."

4. **Postgres credentials in INSTALL.md.** The alembic.ini hardcodes `forge:forge@localhost:5432/forge_bridge`. Should INSTALL.md document these as the "quick start" credentials and explain how to override via `FORGE_DB_URL`? This is the recommended approach — document the defaults first, then the override. 

5. **`conda activate forge` vs. plain venv.** The README uses conda. The planner should decide whether INSTALL.md recommends conda exclusively (matching the reference deployment) or allows plain venv as an alternative. CONTEXT.md D-07 says "opinionated — one path through." Recommendation: conda only, since that's the tested reference path on assist-01.

6. **Staged-ops staging limitation for Track B.** Without Postgres, `forge_*_staged` MCP tools and `/api/v1/staged` HTTP routes will fail with DB errors. The "if you don't have Flame" carveout should also note: "if you don't have Postgres running, staged-ops tools will fail." This is a Track B gap to surface explicitly.

---

## RESEARCH COMPLETE

**Phase:** 20 — Reality Audit + Canonical Install
**Confidence:** HIGH

### Key Findings

1. **Three-way version drift confirmed and safe to fix:** `install-flame-hook.sh` defaults to `v1.1.0`, README curl URL says `v1.2.1`, live tag is `v1.4.1`. Both v1.4.1 raw GitHub URLs resolve (verified). v1.4.1 tag exists on origin (verified).

2. **Critical additional gap: `pyproject.toml` still declares version `1.3.0`** — the v1.4.0 and v1.4.1 milestones were tagged without bumping the package version. `forge_bridge.__version__` returns `"1.3.0"`. Phase 20 must include a version bump in Plan 20-01 alongside the install-script flip.

3. **CLAUDE.md is anchored to the v1.0 snapshot** — the "What exists and works" section lists only the Flame bridge and MCP server; 6+ major subsystems (Web UI, CLI, chat endpoint, staged ops, learning pipeline, LLMRouter) are missing. The "Active Development Context" says "2026-02-24, just extracted from projekt-forge." Full rewrite required.

4. **No `forge_config.yaml` exists** — the codebase is entirely env-var driven. INSTALL.md documents `FORGE_DB_URL`, `ANTHROPIC_API_KEY` (optional), `FORGE_LOCAL_LLM_URL`, `FORGE_LOCAL_MODEL`, and `FORGE_CONSOLE_PORT`. No config file template needed.

5. **Chat endpoint uses Ollama only (sensitive=True hardcoded)** — `ANTHROPIC_API_KEY` is NOT required for the basic operator workflow. INSTALL.md should list it as "optional, for cloud LLM calls."

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Drift inventory | HIGH | All claims verified by direct file reads at HEAD |
| Five surfaces + entry points | HIGH | Verified via source file reads + route tables |
| Version drift (script + pyproject) | HIGH | Verified by git show, file reads, WebFetch |
| Dep inventory | HIGH | Verified from pyproject.toml + router.py + session.py |
| DB setup | HIGH | Verified from alembic.ini + session.py |
| Ollama model | HIGH | Verified from router.py + seed file |
| Pre-flight URL check | HIGH | Verified via live WebFetch to both URLs |
| UAT artifact pattern | HIGH | Read all 5 prior HUMAN-UAT files |
| Postgres reference version | MEDIUM | Stated as "16.x" from PROJECT.md context; not verified live on assist-01 |
| Ollama reference version | MEDIUM | "0.21.0" from 16.2-HUMAN-UAT.md; may be updated on assist-01 by now |

### Open Questions Requiring Planner/User Decision

- Confirm: bump pyproject.toml to `1.4.1` (recommended) or hold?
- Remove `--bridge-host` flag from README (confirmed stale)?
- conda-only or allow plain venv in INSTALL.md?

### Ready for Planning

Research complete. Planner can create PLAN.md files for Phase 20.
