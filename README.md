# What is forge-bridge?

forge-bridge is middleware for post-production pipelines — a protocol-agnostic communication bus that lets different tools speak a shared operational language. Flame, Maya, editorial systems, shot-tracking databases, AI models, and custom scripts can all connect to it. None of them needs to know anything about the others.

forge-bridge is not a Flame utility. Flame is one endpoint. Everything else is another.

The core idea is simple: define a canonical vocabulary once — projects, sequences, shots, versions, traits, relationships — then let each connected system map its native concepts onto that vocabulary through a thin adapter layer. Once two systems both speak bridge, they can communicate without custom point-to-point integration code.

The five primary surfaces — Artist Console, CLI, MCP server, chat endpoint, and Flame hook — are not separate tools. They are different interaction lenses over the same operational substrate.

- The CLI is precise and scriptable.
- The chat endpoint is intent-driven and conversational.
- The Artist Console is operational and visual.
- MCP exposes the system to external AI consumers.
- The Flame hook embeds bridge directly into artist workflow.

Each surface optimizes for a different mode of interaction while operating against the same underlying model.

## Relationship to projekt-forge

forge-bridge is the infrastructure layer; projekt-forge is the first first-party consumer built on top of it.

projekt-forge pins specific forge-bridge versions and builds production workflows against the stable vocabulary and runtime surfaces bridge provides. The split is intentional: forge-bridge stays generic infrastructure, while consumer-specific workflow behavior lives downstream.

---

## Current Status

Shipped at **v1.9.0** (2026-07-18). Conversational Reads now distinguishes missing information from missing capability, renders complete pure shot-name lists without a second model pass, and grounds directly named projects to exact registry identities. Milestones v1.5 Legibility (install + concept docs + recipes + diagnostics), v1.6 Operability (graph-native operational runtime, doctor observability, chat-layer convergence), v1.7 Artist Readiness (NL → compile → preview → ratify → apply authority chain), and v1.8 Console Authority (ratification projection onto the Console) have all shipped since the v1.4.1 baseline. Public `forge_bridge.__all__` remains **19 symbols** — the surface has stayed stable while behavior deepened.

| Component | Status |
|-----------|--------|
| Flame HTTP bridge (`:9999`) | ✅ Shipped (v1.0) |
| MCP server (`fbridge mcp stdio` / `fbridge mcp http`) | ✅ Shipped (v1.0; expanded through v1.4) |
| Canonical vocabulary layer (`forge_bridge/core/`) | ✅ Shipped (v1.0) |
| Postgres persistence + migrations | ✅ Shipped (v1.0) |
| Async/sync WebSocket clients | ✅ Shipped (v1.0) |
| Tool provenance in MCP `_meta` (PROV-01..06) | ✅ Shipped (v1.2.0) |
| StoragePersistence Protocol + SQL mirror | ✅ Shipped (v1.3.0) |
| Artist Console / Web UI (`:9996/ui/`) | ✅ Shipped (v1.3.1, Phases 10/10.1) |
| CLI `fbridge` — top-level commands + `console` / `mcp` / `flame` groups | ✅ Shipped (v1.3.1 Phase 11; expanded through v1.4) |
| Staged-operations platform (`/api/v1/staged`, MCP tools, lifecycle) | ✅ Shipped (v1.4, FB-A + FB-B) |
| LLMRouter agentic tool-call loop (`complete_with_tools()`) | ✅ Shipped (v1.4, FB-C) |
| Chat endpoint (`POST /api/v1/chat`) | ✅ Shipped (v1.4, FB-D + 16.1 + 16.2; compile-then-dispatch since v1.7) |
| Direct execution (`execute_command` / `fbridge exec`, PR31 envelope) | ✅ Shipped — see [docs/DIRECT_EXECUTION.md](docs/DIRECT_EXECUTION.md) |
| WebSocket event server (`:9998`) | ✅ Shipped (graceful degradation per Phase 07.1) |
| Learning pipeline (synthesis + probation + manifest) | ✅ Shipped (v1.0; refined through v1.4) |
| Graph-native operational runtime (`graph_store` JSONL, `fbridge flame-exec` / `graph list/show`) | ✅ Shipped (v1.6) |
| Runtime doctor observability (`fbridge doctor` — Console/MCP/Flame/postgres/graph_store rows) | ✅ Shipped (v1.6) |
| Authority chain: NL → compile → preview → ratify → apply (`AssentRecord`, `fbridge ratify`, `POST /api/v1/ratify`) | ✅ Shipped (v1.7 Thread A) |
| Console ratification projection (preview render + ratify affordance in the Web UI) | ✅ Shipped (v1.8 CA.1) |
| Conversational read answer-pass (plain-language answers on read queries) | ✅ Shipped (v1.9.0; live planner-front UAT 3/3 trusted) |
| Dependency graph traversal engine | 📋 Planned (relationships persist; no traversal module yet) |
| Canonical event-driven pub/sub abstraction | 📋 Planned (WS server ships; canonical layer does not) |
| Maya endpoint | 📋 Planned |
| Editorial / shot-tracking adapters | 📋 Planned |
| Authentication (multi-user, caller identity) | 📋 Planned (SEED-AUTH-V1.5; `AssentRecord.decided_by` is free-string until then) |

---

## Conda environment

forge-bridge (and its downstream consumer projekt-forge) use a shared conda environment named `forge` so the two codebases can resolve each other's editable installs without polluting the system Python.

Create and activate the environment:

```bash
conda create -n forge python=3.11 -y
conda activate forge
```

Install forge-bridge in editable mode with the test extras:

```bash
pip install -e ".[dev]"
```

Install with the optional LLM extras (for synthesis via Ollama / OpenAI / Anthropic):

```bash
pip install -e ".[dev,llm]"
```

Downstream consumers (projekt-forge, other pipeline tools) install forge-bridge as a git-URL pinned dependency inside the same conda environment — see projekt-forge's README for the pin pattern.

Python 3.10 is the minimum supported version (per `pyproject.toml`); the `forge` env defaults to 3.11 to match the reference deployment on the primary workstation.

---

## Quick Start

### Install the Flame hook

**One command** (works from a clone or standalone):

```bash
# From a clone:
./scripts/install-flame-hook.sh

# Or standalone on any Flame workstation — no clone required:
curl -fsSL https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.9.0/scripts/install-flame-hook.sh | bash
```

The installer copies `forge_bridge.py` into `/opt/Autodesk/shared/python/forge_bridge/scripts/` and sanity-checks the result. Override `FORGE_BRIDGE_VERSION` (default `v1.9.0`) or `FORGE_BRIDGE_HOOK_DIR` (default the Flame shared-python path) as needed.

Flame will load the hook automatically on next launch. The bridge starts on `http://127.0.0.1:9999/` by default.

**Environment variables:**
```
FORGE_BRIDGE_HOST=0.0.0.0     # bind to LAN (default: 127.0.0.1)
FORGE_BRIDGE_PORT=9999        # port (default: 9999)
FORGE_BRIDGE_ENABLED=0        # disable entirely
```

### Install forge-bridge

Install with the LLM extras (mandatory for chat + learning-pipeline synthesis):

```bash
pip install -e ".[dev,llm]"
```

`[dev]` adds pytest + ruff. `[llm]` adds `openai`, `anthropic`, `ollama`. Bare `pip install -e .` skips both extras and silently breaks the chat endpoint and tool synthesis.

### Bring up forge-bridge

forge-bridge runs as two long-lived daemons — a WebSocket bus on `:9998` and the MCP + Artist Console process co-hosted on `:9996` (with MCP HTTP on `:9997`). Both are managed by systemd (Linux) or launchd (macOS). The bootstrap script installs the units, bootstraps Postgres, installs the env file at `/etc/forge-bridge/forge-bridge.env`, and starts both daemons in dependency order:

```bash
sudo ./scripts/install-bootstrap.sh
```

The script is idempotent — re-runs are no-ops on unchanged substrate. Pass `--no-postgres` to point at an existing remote DB, `--mcp-only` to skip the Console daemon, or `--non-interactive` to skip the `FORGE_LOCAL_LLM_URL` prompt. Full flag matrix: `sudo ./scripts/install-bootstrap.sh --help`.

See [`docs/INSTALL.md`](docs/INSTALL.md) for the canonical operator-workstation install path — pre-reqs, env-file editing, custom Postgres credentials, lifecycle commands, troubleshooting.

**Claude Desktop / stdio MCP clients:** use `python -m forge_bridge mcp stdio` as the launch-process command. Claude Desktop spawns the process per-invocation and feeds tool calls over stdin/stdout. The systemd/launchd daemon path above is for streamable-HTTP MCP clients (URL: `http://localhost:9997/mcp`).

**`python -m forge_bridge` alone** (no subcommand) prints help and exits 0 — it does **not** start any services. Use the `mcp stdio` / `mcp http` subcommands to start the MCP server, or the bootstrap script above for the supervised daemon path.

### Test the connection

Five surfaces should be reachable after install:

```bash
# 1. Flame hook (requires Flame running with the hook installed)
curl -s http://localhost:9999/status        # JSON with "flame_available": true

# 2. MCP server CLI
fbridge --help

# 3. Artist Console Web UI
curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"   # 200

# 4. Chat endpoint (requires Ollama + qwen2.5-coder:14b running)
curl -s -X POST http://localhost:9996/api/v1/chat \
  -H "content-type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'

# 5. Post-install diagnostic (covers JSONL log, sidecar dirs, port reachability, disk)
fbridge doctor
```

`forge-bridge` is preserved as a back-compat alias for `fbridge` — both resolve to the same Typer app. New docs use `fbridge`.

`ANTHROPIC_API_KEY` is **optional** — chat hardcodes `sensitive=True`, which routes through local Ollama. The key is only needed for `sensitive=False` cloud routing.

The Flame bridge's interactive Python console is still available at `http://localhost:9999/` if you want to drive Flame's Python API directly (handy for ad-hoc debugging).

---

## Repository Structure

```
forge-bridge/
├── forge_bridge/           # MCP server + bridge client (Python package)
│   ├── __init__.py
│   ├── __main__.py         # Entry point: python -m forge_bridge
│   ├── bridge.py           # HTTP client to Flame bridge
│   ├── server.py           # MCP server, tool registration
│   └── tools/              # MCP tool implementations
│       ├── project.py      # Project/library/desktop tools
│       ├── timeline.py     # Sequence/segment tools
│       ├── batch.py        # Batch/node tools
│       ├── publish.py      # Publish workflow tools
│       └── utility.py      # Raw exec + diagnostics
│
├── flame_hooks/            # Flame Python hook (installed into Flame)
│   └── forge_bridge/
│       └── scripts/
│           └── forge_bridge.py   # HTTP server inside Flame
│
├── docs/                   # Design documentation
│   ├── VOCABULARY.md       # Canonical vocabulary spec
│   ├── ARCHITECTURE.md     # System design + decision log
│   ├── API.md              # HTTP API reference
│   └── ENDPOINTS.md        # Guide to writing new endpoint adapters
│
├── tests/
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

---

## Documentation

- [Vocabulary](docs/VOCABULARY.md) — The canonical language forge-bridge speaks
- [Architecture](docs/ARCHITECTURE.md) — Design decisions and system overview  
- [API Reference](docs/API.md) — HTTP API for the Flame bridge endpoint
- [Writing Endpoints](docs/ENDPOINTS.md) — How to connect new software to bridge
- [Manual Targeted Authoring](docs/AUTHORING.md) — Human-QC prompt authoring and grant-gated make workflow

---

## Design Principles

**Bridge is neutral.** It does not prefer Flame over Maya, or any software over another. All endpoints are equal participants.

**Vocabulary is primary.** The canonical language is the most important design surface. Get it right and everything else follows. See [VOCABULARY.md](docs/VOCABULARY.md).

**Dependencies are inferred, not declared.** When data flows into bridge, the relationships and dependencies within it are parsed and recorded automatically. Artists do not declare dependencies — the graph builds itself from the natural structure of the work.

**Local first.** Bridge runs locally to start. The architecture does not prevent future network or cloud deployment, but does not require it.

**Authentication is deferred, not ignored.** The message format and connection model are designed to accommodate auth context. It is not implemented yet. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the current thinking.

---

## License

GPL-3.0 — see LICENSE
