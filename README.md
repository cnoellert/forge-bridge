# forge-bridge

**forge-bridge** is a protocol-agnostic communication middleware for post-production pipelines. It enables any piece of software — Flame, Maya, editorial systems, shot tracking databases, AI models, custom scripts — to communicate through a shared, semantically-rich vocabulary.

forge-bridge is not a Flame utility. It is infrastructure. Flame is one endpoint. Everything else is another.

---

## Vision

Modern post-production involves many disparate software systems that have no native way to talk to each other. A "shot" in Flame, a "clip" in Resolve, an "entity" in ShotGrid, a "sequence" in an NLE — these are all pointing at the same real-world thing. forge-bridge holds the map and carries the messages.

The core insight: define a canonical vocabulary once. Each connected system provides a thin adapter that maps its native concepts to bridge's language. After that, any two systems that both speak bridge can communicate without knowing anything about each other.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      forge-bridge                        │
│                                                         │
│   ┌─────────────┐    ┌──────────────┐    ┌──────────┐  │
│   │  Vocabulary │    │  Dependency  │    │ Channel  │  │
│   │   (canon.   │    │    Graph     │    │ Manager  │  │
│   │  language)  │    │  (auto-built │    │  (sync + │  │
│   │             │    │  from data)  │    │  events) │  │
│   └─────────────┘    └──────────────┘    └──────────┘  │
│                                                         │
└──────┬──────────────────┬──────────────────┬───────────┘
       │                  │                  │
  ┌────┴────┐        ┌────┴────┐        ┌────┴────┐
  │  Flame  │        │  Maya   │        │   AI /  │
  │Endpoint │        │Endpoint │        │   LLM   │
  └─────────┘        └─────────┘        └─────────┘
```

### Current Implementation (Phase 1)

The current implementation is the **Flame endpoint** — an HTTP bridge that allows external processes to execute Python code inside a running Flame instance, and receive results back.

This consists of two parts:

**Flame-side hook** (`flame_hooks/forge_bridge/scripts/forge_bridge.py`)
An HTTP server running inside Flame on port 9999. Accepts Python code via `POST /exec`, executes it on Flame's Qt main thread via `schedule_idle_event`, and returns stdout/stderr/result as JSON.

**MCP client layer** (`forge_bridge/`)
A [Model Context Protocol](https://modelcontextprotocol.io) server that wraps the bridge's HTTP interface as structured tools, making the Flame Python API accessible to LLM agents.

---

## Current Status

Shipped at **v1.4.1** (2026-04-30). 19 phases across 6 milestones. Active milestone: **v1.5 Legibility** (Phases 20-23 — install + concept docs + recipes + diagnostics).

| Component | Status |
|-----------|--------|
| Flame HTTP bridge (`:9999`) | ✅ Shipped (v1.0) |
| MCP server (`python -m forge_bridge`, stdio) | ✅ Shipped (v1.0; expanded through v1.4) |
| Canonical vocabulary layer (`forge_bridge/core/`) | ✅ Shipped (v1.0) |
| Postgres persistence + migrations | ✅ Shipped (v1.0) |
| Async/sync WebSocket clients | ✅ Shipped (v1.0) |
| Tool provenance in MCP `_meta` (PROV-01..06) | ✅ Shipped (v1.2.0) |
| StoragePersistence Protocol + SQL mirror | ✅ Shipped (v1.3.0) |
| Artist Console / Web UI (`:9996/ui/`) | ✅ Shipped (v1.3.1, Phases 10/10.1) |
| CLI `forge-bridge console tools \| execs \| manifest \| health \| doctor` | ✅ Shipped (v1.3.1, Phase 11) |
| Staged-operations platform (`/api/v1/staged`, MCP tools, lifecycle) | ✅ Shipped (v1.4, FB-A + FB-B) |
| LLMRouter agentic tool-call loop (`complete_with_tools()`) | ✅ Shipped (v1.4, FB-C) |
| Chat endpoint (`POST /api/v1/chat`) | ✅ Shipped (v1.4, FB-D + 16.1 + 16.2) |
| WebSocket event server (`:9998`) | ✅ Shipped (graceful degradation per Phase 07.1) |
| Learning pipeline (synthesis + probation + manifest) | ✅ Shipped (v1.0; refined through v1.4) |
| Dependency graph traversal engine | 📋 Planned (relationships persist; no traversal module yet) |
| Canonical event-driven pub/sub abstraction | 📋 Planned (WS server ships; canonical layer does not) |
| Maya endpoint | 📋 Planned |
| Editorial / shot-tracking adapters | 📋 Planned |
| Authentication (multi-user, caller identity) | 📋 Planned (SEED-AUTH-V1.5; v1.6+) |

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
curl -fsSL https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh | bash
```

The installer copies `forge_bridge.py` into `/opt/Autodesk/shared/python/forge_bridge/scripts/` and sanity-checks the result. Override `FORGE_BRIDGE_VERSION` (default `v1.4.1`) or `FORGE_BRIDGE_HOOK_DIR` (default the Flame shared-python path) as needed.

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

### Run the MCP server

The same process boots the MCP server (stdio for Claude Desktop / Claude Code), the Artist Console Web UI on `:9996`, and the `/api/v1/chat` endpoint:

```bash
# Daily local launch — uses FORGE_DB_URL, FORGE_LOCAL_LLM_URL, FORGE_BRIDGE_HOST defaults
python -m forge_bridge

# Headless host where stdin closes immediately (deploy hosts, ssh-detached sessions):
tail -f /dev/null | python -m forge_bridge
```

Flame target host override (the bridge defaults to `127.0.0.1:9999`):

```bash
FORGE_BRIDGE_HOST=192.168.1.100 python -m forge_bridge
```

See `docs/INSTALL.md` for the full env-var reference and the canonical operator-workstation install path.

### Test the connection

Five surfaces should be reachable after install:

```bash
# 1. Flame hook (requires Flame running with the hook installed)
curl -s http://localhost:9999/status        # JSON with "flame_available": true

# 2. MCP server CLI
forge-bridge --help

# 3. Artist Console Web UI
curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"   # 200

# 4. Chat endpoint (requires Ollama + qwen2.5-coder:32b running)
curl -s -X POST http://localhost:9996/api/v1/chat \
  -H "content-type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'

# 5. Post-install diagnostic (covers JSONL log, sidecar dirs, port reachability, disk)
forge-bridge console doctor
```

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

---

## Relationship to projekt-forge

forge-bridge is extracted from [projekt-forge](https://github.com/cnoellert/projekt-forge), which is the project management frontend for Flame-based pipelines. projekt-forge creates and manages projects, folder structures, and pipeline configurations.

forge-bridge is the communication infrastructure that projekt-forge and other tools connect to. It is developed and versioned independently so it can serve as a stable platform for any number of tools without being coupled to any single one.

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
