# Getting Started with forge-bridge

This document orients new users to forge-bridge's mental model and the five surfaces through which you interact with it. It is not an install guide (see [`docs/INSTALL.md`](INSTALL.md)) and it is not a workflow recipe (see [`docs/RECIPES.md`](RECIPES.md) — forthcoming). It is the map you read before either.

---

## Why this exists

Modern post-production runs on a constellation of tools that have no native way to talk to each other. Flame holds the timeline. An NLE owns the cut. Shot-tracking lives in a third database. Editorial conform happens in a fourth. AI-assisted workflows want to read and write across all of them. Each pair of systems that needs to communicate ends up wired together with custom integration code — and every new tool added to the pipeline multiplies the number of wires.

forge-bridge exists so that wiring becomes a one-to-many problem instead of a many-to-many one. Each connected system speaks a shared operational language. New tools join by writing a thin adapter, not by negotiating bilateral integrations with every other tool in the pipeline. AI agents and downstream consumers get stable semantics they can build against. Workflow surfaces — visual, scripted, conversational, embedded — share the same operational state without inventing their own.

That is the practical pressure. Everything else follows from it.

---

## The substrate

forge-bridge defines a canonical vocabulary — projects, sequences, shots, versions, traits, and the relationships between them — and serves as a runtime that holds the live state of that vocabulary. Each connected tool maps its native concepts onto the canonical model through a thin adapter layer. Flame's notion of a "clip" and editorial's notion of a "clip" both map to the same canonical `Version` of a canonical `Shot`. After that mapping is in place, the two tools can communicate without knowing anything about each other's internals.

The substrate is small and deliberately stable: projects contain sequences, sequences contain shots, shots have versions, versions have media, and traits (versionable, locatable, relational) describe cross-cutting capabilities that any entity can carry. Relationships between entities are inferred from the data as it flows through bridge — artists do not declare dependencies; the graph builds itself from the natural structure of the work.

forge-bridge exposes the same underlying operational model through several different interaction surfaces. Each surface optimizes for a different kind of user and workflow. The surfaces are not alternatives to each other — they are projections. You are not choosing between them; you are choosing the lens that matches what you are doing right now.

---

## The five surfaces

### Artist Console

A web interface at `http://localhost:9996/ui/` that shows the live operational state of the bridge — the tool registry, recent execution history, the canonical synthesis manifest, system health, and a chat panel for conversational workflows.

**Who reaches for it:** Artists and supervisors who want to *see* what bridge is doing — which tools exist, what ran recently, what is staged, whether things are healthy — without typing commands.

The Artist Console is the operational dashboard. When something feels off and you want to look at it, this is the surface. When you want to monitor synthesis activity or watch a staged operation move through its lifecycle, this is the surface.

**Learn more:** the console is co-hosted with the MCP server; see [`docs/INSTALL.md`](INSTALL.md) for how it comes up at boot.

### CLI

A command-line tool named `fbridge` that reads the same `:9996` API the Artist Console consumes. Subcommands cover tool listings, execution history, manifest inspection, health checks, and a post-install diagnostic.

**Who reaches for it:** Operators, scripters, and anyone composing bridge state into larger pipelines. The CLI is precise, scriptable, and machine-readable — every command supports a `--json` flag that short-circuits the human-friendly Rich output and returns raw JSON suitable for piping into `jq`, other commands, or test harnesses.

```
fbridge doctor            # post-install diagnostic
fbridge actions --json    # tool registry as JSON
fbridge console health    # daemon and dependency health
```

(Illustrative — see `fbridge --help` for the full surface area.)

**Learn more:** `fbridge --help` is self-documenting; the post-install diagnostic is the first command worth running.

### MCP server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes forge-bridge's operational surface as structured tools to external AI agents — Claude Desktop, Cursor, Gemini CLI, and any other MCP-compliant client.

**Who reaches for it:** Anything outside the bridge that needs to query or operate against it through an LLM. When you want an AI agent to read the manifest, query staged operations, run a synthesized tool, or compose multiple bridge operations into a higher-level workflow, you connect through MCP.

A typical MCP integration configures the agent's launch process to invoke `python -m forge_bridge mcp stdio` (or points at the streamable-HTTP endpoint at `http://localhost:9997/mcp`); the agent then discovers bridge's tool catalogue automatically.

**Learn more:** [`docs/INSTALL.md`](INSTALL.md) covers the Claude Desktop wiring. The MCP server's tool catalogue is the same one the Artist Console and CLI surface.

### Chat endpoint

An HTTP endpoint at `POST http://localhost:9996/api/v1/chat` that accepts conversational messages and runs an agentic tool-call loop against a local LLM (Ollama by default, with `qwen2.5-coder:32b` as the locked-in model). The agent reads forge-bridge's tool catalogue, calls tools, observes their results, and synthesizes a natural-language answer.

**Who reaches for it:** Workflow surfaces — internal or external — that want to drive bridge through natural language. The Artist Console's chat tab is the most visible consumer. Downstream tools like projekt-forge's Flame hooks call the same endpoint to give artists conversational access to the pipeline without needing to learn the underlying tool catalogue.

The chat endpoint is intent-driven and iterative. You ask "what's staged for review?" or "rename shots 010 through 015 to use the new convention" and the agent figures out which tools to call to satisfy the intent.

**Learn more:** the chat tab in the Artist Console is the easiest way to see this in action; the endpoint itself routes through the local LLM and does not require an `ANTHROPIC_API_KEY`.

### Flame hook

An HTTP server running *inside* Flame on `http://127.0.0.1:9999/` that accepts Python code and executes it against Flame's Python API on the main thread. Returns stdout, stderr, the result value, and any traceback as a structured JSON envelope.

**Who reaches for it:** Anything that needs to drive Flame's Python API from outside Flame — synthesized tools, the MCP server's Flame-specific tools, projekt-forge's pipeline integrations, ad-hoc debugging. The hook is what makes Flame a *bridge endpoint* rather than just a tool that happens to be running on the same machine.

There is also an interactive web console at `http://localhost:9999/` for typing Python directly into a running Flame — useful for poking at the API without leaving the browser.

**Learn more:** [`docs/API.md`](API.md) documents the HTTP envelope; [`docs/FLAME_API.md`](FLAME_API.md) is the domain reference for Flame's Python API surface.

---

## The canonical vocabulary

The canonical vocabulary — projects, sequences, shots, versions, traits, and the relationships between them — is the shared language every surface speaks. When you're ready for the full ontology, [`docs/VOCABULARY.md`](VOCABULARY.md) has the complete model.

You do not need to read VOCABULARY.md to use the bridge through any single surface — each surface presents its own affordances over the substrate. But understanding the vocabulary is what lets you move *between* surfaces fluently: a `Shot` in the Artist Console, a `forge_get_shot` MCP tool call, an entity returned by the CLI, and a `Shot` rendered inside Flame are all the same object viewed through different lenses.

---

## Choose your entry point

A short orientation, depending on what brought you here:

- **Integrating a new tool or building an adapter** → MCP server + [`docs/VOCABULARY.md`](VOCABULARY.md). Understand the canonical model first, then expose your tool's native concepts through MCP.
- **Operating the system day-to-day** → CLI + [`docs/INSTALL.md`](INSTALL.md). The CLI is the operator surface; INSTALL.md covers daemons, lifecycle, and troubleshooting.
- **Building workflows or monitoring state** → Artist Console + [`docs/RECIPES.md`](RECIPES.md) (forthcoming). The console is the operational dashboard; recipes will document the daily workflows that compose its surfaces.
- **Embedding inside a DCC** → Flame hook + [`docs/API.md`](API.md). The hook pattern is what makes Flame an endpoint; the same pattern is how future 2D/3D DCC and editorial endpoints will plug in.

---

## Where to go next

| Goal | Read |
|------|------|
| Install forge-bridge on a workstation | [`docs/INSTALL.md`](INSTALL.md) |
| Learn the canonical vocabulary in detail | [`docs/VOCABULARY.md`](VOCABULARY.md) |
| Understand architectural decisions and tradeoffs | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) |
| Run daily workflows (recipes) | [`docs/RECIPES.md`](RECIPES.md) — forthcoming (Phase 22) |

Phase 22 of the v1.5 Legibility milestone is the recipes layer: step-by-step workflows for first-time setup, Claude Desktop wiring, watching tool synthesis, chat-driven Flame automation, staged-ops approval, and manifest inspection. Until that lands, the README's Quick Start section is the closest thing to a working recipe.

---

*forge-bridge is the infrastructure layer; projekt-forge is the first first-party consumer built on top of it. If you arrived here through projekt-forge, the relationship section in the [README](../README.md) describes the split.*
