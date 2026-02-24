# forge-bridge Architecture

This document captures the system design and the reasoning behind key decisions. It is a living document — decisions that change should be updated here with the original rationale preserved.

---

## System Overview

forge-bridge is middleware. It sits in the center of a pipeline and enables communication between any number of connected endpoints. It is not specific to Flame, not specific to post-production software, not specific to any workflow pattern.

```
                         ┌─────────────────┐
                         │   forge-bridge   │
                         │                 │
           ┌─────────────┤  Vocabulary     ├─────────────┐
           │             │  Dependency     │             │
           │             │  Graph          │             │
           │             │  Channel Mgr    │             │
           │             └────────┬────────┘             │
           │                      │                      │
    ┌──────┴──────┐         ┌──────┴──────┐        ┌──────┴──────┐
    │    Flame    │         │    Maya     │        │   AI / LLM  │
    │  Endpoint   │         │  Endpoint   │        │  Endpoint   │
    └─────────────┘         └─────────────┘        └─────────────┘
```

### Bridge is not a database

Bridge maintains a dependency graph and understands relationships, but it is not the system of record. Connected systems (ShotGrid, ftrack, filesystem) are the sources of truth. Bridge is the translator and the nervous system — it routes, transforms, and tracks change propagation.

### Bridge is not a workflow engine

Bridge does not orchestrate tasks. It observes events, tracks dependencies, and propagates change notifications. What systems do in response to those notifications is their own concern.

---

## Communication Model

Bridge supports two communication patterns:

### Synchronous (Request/Response)

One endpoint asks bridge a question and waits for an answer. Used for queries, lookups, and operations that need confirmation.

```
Endpoint A  →  bridge.query(...)  →  Bridge  →  response  →  Endpoint A
```

### Event-Driven (Publish/Subscribe)

An endpoint announces that something happened. Any endpoint that has subscribed to that event type receives a notification. The publisher does not wait for or care about responses.

```
Endpoint A  →  bridge.publish(event)  →  Bridge  →  notify(Endpoint B)
                                                  →  notify(Endpoint C)
```

The dependency graph makes publish/subscribe much more powerful: when Endpoint A publishes "Version 4 of Asset X was updated," bridge knows from the dependency graph which Shots reference that asset, and can automatically generate downstream notifications without Endpoint A knowing or caring about those relationships.

---

## Current Implementation: Phase 1

### The Flame HTTP Bridge

The first concrete implementation is an HTTP server that runs inside a Flame instance, enabling external processes to execute Python code in Flame's runtime and receive results.

**Why HTTP?**

Flame hosts a Python interpreter but has no built-in IPC mechanism. HTTP is the most universally accessible protocol — any language, any tool can speak it. The web UI for interactive use comes for free.

**Why `schedule_idle_event` for writes?**

Flame's Python API is only safe to call from the Qt main thread. Read operations can often run from any thread, but any operation that modifies Flame state (set_value, create, delete) must be dispatched to the main thread. `schedule_idle_event` is Flame's mechanism for safely queuing work to the main thread.

The bridge exposes this as `main_thread: true` in `/exec` requests. The MCP tools handle this automatically.

**Why code execution rather than a structured RPC?**

The Flame Python API is large and changes between versions. A code execution approach means bridge does not need to model every API surface — it passes code strings through and returns results. Structured wrappers for common operations (get_project, list_libraries, etc.) are built on top of this in the MCP tool layer, but the raw execution capability is always available as an escape hatch.

The tradeoff is that raw execution is powerful and therefore potentially dangerous. This is acceptable for now because bridge is local-only and we are the only users. Authentication (see below) is the correct long-term solution.

### The MCP Server

The MCP (Model Context Protocol) server wraps the HTTP bridge as structured tools, making the Flame API accessible to LLM agents. This is what allows an AI to be plugged directly into the pipeline as just another endpoint.

The MCP server lives in `forge_bridge/` and communicates with the Flame hook via HTTP. It is the first example of a "thin adapter" — it speaks bridge's client API on one side and a foreign protocol (MCP) on the other.

---

## Dependency Graph Design

The dependency graph is build automatically — it is never declared manually. This is a deliberate design choice.

**Why automatic?**

If dependencies required manual declaration, the graph would always be incomplete. Artists would not maintain it. The graph is only valuable if it is always current. The only way to guarantee that is to build it from the natural structure of the work as it arrives.

**How it works (planned)**

When data arrives at bridge from any endpoint, bridge's parser examines it:

1. Identify entity types from structure and content
2. Map each entity to its canonical type using the vocabulary
3. Look up existing entities in the graph that this new data connects to
4. Create or update relationship edges
5. Propagate any dependency notifications that result from changes

For example: when a new shot is published to bridge with sequence and project context, bridge automatically creates:
- `shot member_of sequence`
- `sequence member_of project`
- `version version_of shot` (if version info present)
- `media references version` (if media info present)

No human decision was required. The structure of the data declared the dependencies.

**Impact analysis**

With the graph populated, bridge can answer:
- "What is the blast radius of changing Version N of Asset X?"
- "What shots are currently depending on the old matte?"
- "If the editorial cut changes by 12 frames at this timecode, which shots are affected?"

---

## Transport Layer

The transport layer handles the mechanics of message delivery — independent of what the messages mean.

### Current: HTTP (REST-like)

Simple, universally accessible, easy to debug. The Flame hook runs an HTTP server. MCP and other clients connect via HTTP.

### Planned: Local socket / Unix socket

For same-machine communication, a Unix domain socket is faster and lower-overhead than HTTP. Planned for the local service model when latency matters.

### Planned: WebSocket / SSE

For event-driven communication and real-time notifications, HTTP polling is inadequate. WebSocket or Server-Sent Events will enable efficient subscription delivery.

### Not planned (yet): Network/cloud transport

Bridge starts local. The architecture does not prevent moving to network transport, but the current design does not require it. When the time comes, the transport layer should be swappable without changing the vocabulary or dependency graph.

---

## Authentication

Authentication is explicitly deferred. It is a later problem, but the architecture is designed to accommodate it.

**What this means practically:**
- Connection identity is a first-class concept even though we don't act on it yet
- Message format has a reserved `auth` context field
- Trust is not hardcoded — nothing says "all connections are trusted forever"
- The Endpoint concept (who is connecting) exists in the vocabulary even without enforcement

When authentication is added, it will need to address:
- Which endpoints are allowed to connect?
- Which endpoints are allowed to read which entities?
- Which endpoints are allowed to write / publish?
- How are credentials managed and rotated?

The most likely initial model: a shared secret or token per endpoint, configurable in a local config file. No external auth service required for local deployment.

---

## Versioning and Stability

forge-bridge is a platform. Once other tools depend on it, breaking changes are expensive.

**Versioning scheme:** Semantic versioning (MAJOR.MINOR.PATCH)
- MAJOR: Breaking changes to the vocabulary or API
- MINOR: New entities, traits, or operations added (backward compatible)
- PATCH: Bug fixes

**Vocabulary stability:** The canonical vocabulary is the most sensitive surface. Adding new entities is always safe. Renaming existing entities is a breaking change. Removing entities requires deprecation with a major version.

**HTTP API stability:** Endpoint paths and request/response shapes follow the same rules.

---

## Project Relationship

forge-bridge is extracted from [projekt-forge](https://github.com/cnoellert/projekt-forge).

projekt-forge is the project management and pipeline orchestration tool for Flame-based pipelines. It creates projects, manages folder structures, and coordinates pipeline configuration.

forge-bridge is the communication infrastructure. projekt-forge is one consumer of forge-bridge — the project management endpoint. It has no special status over other endpoints.

**Dependency direction:** projekt-forge depends on forge-bridge. forge-bridge does not depend on projekt-forge.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-24 | Extract bridge from projekt-forge into standalone repo | Bridge is infrastructure, not a workflow tool. Other tools need to depend on it independently. |
| 2026-02-24 | Start with HTTP transport | Universal compatibility. Simpler to debug. Web UI comes for free. |
| 2026-02-24 | Code execution rather than structured RPC for Flame | Flame API is large and version-variable. Code execution is more flexible and adds raw escape hatch. |
| 2026-02-24 | Defer authentication | Local-only for now. Auth is a real problem but not the immediate one. Framework designed to accommodate it. |
| 2026-02-24 | Automatic dependency graph (not manual) | Manual declaration would produce an incomplete, stale graph. Structure of data implies dependencies. |
| 2026-02-24 | Traits as cross-cutting capabilities (Versionable, Locatable, Relational) | Versioning and pathing are not properties of specific entities — they are behaviors multiple entities share. Centralizing avoids inconsistent reimplementation. |
