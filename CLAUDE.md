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

### What exists and works

**Flame HTTP bridge** (`flame_hooks/forge_bridge/scripts/forge_bridge.py`)
- Runs inside Flame as an HTTP server on port 9999
- Accepts Python code via `POST /exec`, executes on Flame's main thread via `schedule_idle_event`
- Returns `{result, stdout, stderr, error, traceback}` as JSON
- Has a web UI at `http://localhost:9999/` for interactive use
- Persistent namespace across requests (variables survive between calls)

**MCP server** (`forge_bridge/`)
- Model Context Protocol server wrapping the Flame bridge
- Makes Flame's Python API available as structured tools to LLM agents (Claude, etc.)
- Entry point: `python -m forge_bridge`
- Tools: project, timeline, batch, publish, utility

### What is designed but not yet implemented

- Canonical vocabulary engine (the spec is in `docs/VOCABULARY.md` — code doesn't exist yet)
- Dependency graph engine
- Bridge core service (the central router)
- Event-driven pub/sub channels
- Maya endpoint
- Editorial/shot tracking adapters
- Authentication

---

## Repository Layout

```
forge-bridge/
├── CLAUDE.md               ← YOU ARE HERE
├── README.md               ← Project overview, quick start
├── pyproject.toml          ← Package config
│
├── forge_bridge/           ← Python package (MCP server + Flame client)
│   ├── __main__.py         ← Entry point: python -m forge_bridge
│   ├── server.py           ← MCP server, tool registration
│   ├── bridge.py           ← HTTP client to Flame bridge
│   └── tools/              ← MCP tool implementations
│       ├── project.py
│       ├── timeline.py
│       ├── batch.py
│       ├── publish.py
│       └── utility.py
│
├── flame_hooks/            ← Installs into Flame's Python hooks dir
│   └── forge_bridge/
│       └── scripts/
│           └── forge_bridge.py   ← HTTP server running inside Flame
│
└── docs/
    ├── VOCABULARY.md       ← The canonical language (READ THIS)
    ├── ARCHITECTURE.md     ← Design decisions and system design
    ├── API.md              ← HTTP API for the Flame bridge
    └── ENDPOINTS.md        ← How to write new endpoint adapters
```

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

- projekt-forge: project management + pipeline orchestration frontend for Flame
- forge-bridge: the communication infrastructure everything connects to

forge-bridge was extracted from projekt-forge when it became clear it needed to be a standalone platform.

projekt-forge repo: https://github.com/cnoellert/projekt-forge

---

## How to Get Running

```bash
# Install
pip install -e .

# Install Flame hook (copy to Flame's Python hooks dir)
# Typical location: /opt/Autodesk/shared/python/
cp flame_hooks/forge_bridge/scripts/forge_bridge.py /opt/Autodesk/shared/python/forge_bridge/scripts/

# Run MCP server (connects to Flame bridge at localhost:9999)
python -m forge_bridge

# Or HTTP mode
python -m forge_bridge --http --port 8080
```

---

## Active Development Context

As of 2026-02-24:

- Just extracted from projekt-forge — this is the initial standalone repo
- Vocabulary spec is written (docs/VOCABULARY.md) but not yet implemented in code
- Next steps: implement the vocabulary module, then the dependency graph, then the bridge core service
- The flame hook and MCP server are working and deployed — don't break them during restructuring

---

## Questions To Come Back To

1. What format should bridge use for inter-service messages? JSON? MessagePack? Something else?
2. Should the bridge core service be a single process or multiple cooperating processes?
3. When is a Unix socket preferable to HTTP for same-machine communication?
4. What does the bridge core service look like from an endpoint's perspective — is it a library you import or a service you connect to?
