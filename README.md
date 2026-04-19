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

| Component | Status |
|-----------|--------|
| Flame HTTP bridge | ✅ Working |
| MCP server (LLM tools) | ✅ Working |
| Canonical vocabulary spec | 🔧 In design |
| Dependency graph engine | 📋 Planned |
| Maya endpoint | 📋 Planned |
| Editorial/shot tracking adapters | 📋 Planned |
| Event-driven channel system | 📋 Planned |

---

## Quick Start

### Install the Flame hook

**One command** (works from a clone or standalone):

```bash
# From a clone:
./scripts/install-flame-hook.sh

# Or standalone on any Flame workstation — no clone required:
curl -fsSL https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.1.0/scripts/install-flame-hook.sh | bash
```

The installer copies `forge_bridge.py` into `/opt/Autodesk/shared/python/forge_bridge/scripts/` and sanity-checks the result. Override `FORGE_BRIDGE_VERSION` (default `v1.1.0`) or `FORGE_BRIDGE_HOOK_DIR` (default the Flame shared-python path) as needed.

Flame will load the hook automatically on next launch. The bridge starts on `http://127.0.0.1:9999/` by default.

**Environment variables:**
```
FORGE_BRIDGE_HOST=0.0.0.0     # bind to LAN (default: 127.0.0.1)
FORGE_BRIDGE_PORT=9999        # port (default: 9999)
FORGE_BRIDGE_ENABLED=0        # disable entirely
```

### Install the MCP server

```bash
pip install -e .
```

### Run the MCP server

```bash
# Local (stdio — for use with Claude Desktop or similar)
python -m forge_bridge

# Remote Flame (bridge on another machine)
python -m forge_bridge --bridge-host 192.168.1.100

# HTTP transport (multi-client)
python -m forge_bridge --http --port 8080
```

### Test the connection

Open `http://localhost:9999/` in a browser for the interactive Python console. Type `flame` to confirm the Flame API is available.

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
