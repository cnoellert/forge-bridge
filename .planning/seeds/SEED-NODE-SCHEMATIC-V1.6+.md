---
name: SEED-NODE-SCHEMATIC-V1.6+
description: Frame forge-bridge as the node schematic for the pipeline layer that has never had one. Render the dependency graph and live event stream as a web-served, cross-tool node graph that artists, producers, and supervisors can read in language they already speak.
type: strategic-framing
planted_during: Architecture conversation 2026-05-04 — PR40-42 consolidation aftermath strategy session, re: deterministic-vs-generative dual-mode surfaces and the missing visual vocabulary
trigger_when: v1.6 milestone opens OR external demo/explanation needed OR adoption friction surfaces ("artists don't get what bridge is") OR vocabulary stabilizes enough to render
---

# SEED-NODE-SCHEMATIC-V1.6+: bridge as the pipeline-layer node graph

## Idea

Render forge-bridge as a node schematic — a visual graph of entities (Project, Sequence, Shot, Version, Media, Tool, Recommendation, AI service) with edges showing dependencies, hand-offs, and live events. Served from the existing console daemon as a web view at `localhost:9996/schematic/` (or similar route), reachable from any browser, with a "show schematic" menu item in Flame that opens it in a separate window.

This isn't a new feature so much as the *visible face* of infrastructure that already exists. The dependency graph, the vocabulary (Entities + Traits + Roles), the verb set, the canonical entity types — all of that has been the moat the whole time. What's been missing is the rendering. The moment the graph becomes a picture, bridge stops being "the thing Chris built" and becomes "the schematic for our pipeline" — in language Flame, Nuke, and Houdini artists already speak fluently.

## Why This Matters

Every Flame artist, every Nuke artist, every Houdini artist has a refined intuition for node graphs. They look at a graph of connected nodes and immediately understand: this is the data, this is what happens to it, this is the order, this is what depends on what. The mental model is already there. We don't have to teach it.

The pipeline layer — shots, versions, publishes, dependencies, hand-offs, AI services, recommendations — has never had a graph. USD describes scenes. ShotGrid tracks production. OpenAssetIO describes assets. None of them render the *flow of work* as a node schematic the way batch renders compositing or a Houdini network renders procedural geometry. Bridge can — the data is already there. The rendering is the missing visual vocabulary.

This may be the most important reframing the project has had since "communication layer." It's a 10-second elevator pitch to anyone who's used a node-based tool: *"it's the node schematic for your pipeline."* That's a much more durable adoption story than "agentic VFX OS" or even "communication fabric" — both of which require the listener to absorb a new concept rather than recognize an existing one.

## How Existing Surfaces Map

The framing makes the architecture click in a way prior framings didn't:

- **Deterministic dialog** (`/api/v1/exec`) = keyboard interface to the schematic. Like Nuke's `tab-X-create-node` shortcut. Power users live here because it's faster than placing nodes by mouse, and the dialog is the same conceptual operation: pick a node, instantiate it, run it.
- **LLM dialog** (`/api/v1/chat`, see SEED-FLAME-CHAT-FOUNDRY-V1.6+) = the foundry where new node *types* are authored. Like writing a Gizmo in Nuke. Output goes through staged-ops approval, then enters the registry, then becomes available to the deterministic dialog forever after.
- **Macros** (PR32-34) = subgraphs. Like Group nodes. Composition of existing nodes saved as a reusable unit. The persistence in PR34 is the equivalent of saving a Gizmo to disk.
- **Dependency graph** (existing internal infra) = the data layer the schematic renders from. Already exists; just needs a face.
- **Tool types vs tool instances** = node types in palette (e.g., `publish_version`) vs node instances in the live graph (e.g., the specific `publish_version` call run on shot 020 v07 last Tuesday). Both belong in the schematic, in different ways.
- **VOCABULARY.md Entities + Traits + Roles** = the schematic's type system. Entities are node types. Traits are visual badges or capability indicators on a node. Roles are how external endpoints declare which canonical node type they're talking about.

The three-tier loop becomes legible in graph terms: the deterministic path *uses* what's in the graph; the LLM path *grows* what's in the graph; staged-ops *gates* what becomes part of the graph.

## The Wedge: Real-Time Events Over Historical Completeness

The first version of the schematic doesn't need to render every entity in the project. It needs to render *what just happened*. If you publish a version and the schematic immediately shows a new node appearing with edges to its dependencies, that's the moment of magic. If an AI service returns a Recommendation and a new node attaches itself to the relevant Version, the system feels alive in a way no CLI output ever conveys.

Historical state, sophisticated layout, search and filtering — all of that is v1.7+ work. The wedge is: the schematic shows you what bridge is doing right now, and that alone is enough to make people care.

The post-publish triage demo we've been describing for weeks is a schematic event in disguise. Artist publishes v05 → bridge dispatches to denoise/roto/track-quality models → recommendations land on the version. In a schematic, that's not abstract anymore. It's: a node appears for the published version. Edges fan out to AI service nodes. Recommendation nodes attach with edges back to the version. The artist watches the graph grow in real time. That's a demo that sells itself in a way no amount of CLI output ever could.

## Boundaries

In scope (when this seed activates):
- Web view served by existing console daemon (one more route on the already-running process; no new infra).
- Real-time event rendering via SSE or WebSocket. Live updates as entities appear, change, or relate.
- Cross-tool by nature — shows entities from any endpoint (Flame, Maya, editorial, Frame.io, AI services), not just Flame.
- Flame menu item opens the schematic in a separate browser window. The schematic does *not* live inside Flame's UI.
- Tool-type palette / sidebar showing what's registered, alongside the live instance graph.
- Visual distinction between entity types (Shot vs Version vs Media vs Recommendation) and edge types (depends-on, derived-from, recommended-for, produced-by).

Out of scope (initial):
- Full historical state rendering — start with live events; backfill is later.
- Sophisticated layout algorithms — start with simple force-directed or topological; refinement is later.
- Search / filter UI — the live view is the wedge; filtering is v1.7+.
- Inline editing of the graph — read-only view first; mutation comes after the read shape is proven.
- Embedding the schematic *inside* Flame's UI — separate window is correct first cut.
- Mobile/tablet rendering — desktop-only first.
- Multi-project view — single-project schematic first; cross-project comes when the data demands it.

## Forcing Function on Vocabulary

Building the schematic is itself a vocabulary pressure-test. Can't render a `Recommendation` until we've decided what one *is* — its shape, what it points to, how it's distinguished from a Version or an Asset, which Traits it carries. Fuzzy entities don't render cleanly. The same pressure-test the macros applied to the verb set, the schematic applies to the noun set.

This is a feature, not a cost. Building the schematic in v1.6+ will surface every place where VOCABULARY.md is fuzzy and force resolution. Vocabulary clarity that came from doc-writing alone has limits; vocabulary clarity forced by *rendering* is much harder to fudge. If a node type can't be drawn distinctly, it isn't actually a distinct node type — it's a Trait masquerading as an Entity, or vice versa.

## When This Seed Activates

Any of:
1. **v1.6 milestone opens** — natural re-evaluation point as the next major feature arc after v1.5 Legibility.
2. **External demo or explanation is needed** — the schematic is the demo. If a producer, supervisor, or potential adopter needs to see what bridge does, this is the right answer.
3. **Adoption friction surfaces** — "artists don't get what bridge is" or "I can't explain this to my supervisor" are signals that the visual vocabulary is needed sooner.
4. **Vocabulary stabilizes** — the schematic is hardest to build against a fuzzy vocabulary. After a few v1.5/v1.6 iterations of real production use, the entity types will have settled enough to render.
5. **The post-publish triage demo is being prepared** — that demo is intrinsically a schematic event; do them together.

## Breadcrumbs

Code references (current as of 2026-05-04):
- `docs/VOCABULARY.md` — the conceptual entities, traits, and roles that need rendering. The schematic's type system is already specified here.
- `forge_bridge/store/` — the dependency graph + entity persistence layer. The data the schematic renders from already lives here.
- `forge_bridge/console/` — existing FastAPI/Starlette console process; the web view would be added here as a new route.
- `forge_bridge/server.py` — `/api/v1/exec` and `/api/v1/chat` live alongside the console; schematic data routes (e.g., `/api/v1/graph`, `/api/v1/events/stream`) join them.
- `forge_bridge/learning/` — synthesizer pipeline; new tools entering the registry are graph events the schematic should render as they happen.
- `flame_hooks/forge_bridge/` — Flame hook adds a "show schematic" menu item that opens the web view in a separate window.
- v1.4 staged-operations infrastructure (FB-C) — the gate for what enters the graph; should render as a "pending" zone in the schematic.
- v1.5 Phase 21 (surface map docs, in flight) — the schematic is essentially the surface map made executable.

## Open Questions (for v1.6+ planning)

- **Rendering library.** D3 has the flexibility, Cytoscape.js has more graph affordances out of the box, raw SVG is the simplest. Probably Cytoscape for first cut.
- **Scale handling.** A real production has hundreds of shots and thousands of versions. Layered/zoomable view? Per-sequence sub-schematics? Lazy-load on viewport pan?
- **Read-only vs limited mutation.** Is the schematic strictly read-only in v1.6, or do we add limited mutation (drag to re-parent, click to trigger a tool)? Read-only is the safe first cut; mutation is structurally fine because the same `/api/v1/exec` endpoint already handles it.
- **Tool types vs instances rendering.** How do they render differently? Color, shape, size, separate panel? A Nuke-like split where node types are in a tab/sidebar and instances are in the canvas is probably correct.
- **Staged-ops surfacing.** Does the schematic surface staged-ops directly (pending operations as ghost nodes), or is staged-ops a separate panel that the schematic links to? Probably surface — ghost nodes are more legible than a separate queue.
- **Live event firehose vs filtered subscription.** Does every schematic instance subscribe to the full event stream, or do clients subscribe to scoped views (this project, this sequence)? Scoped is the right call once data volume becomes real.

## Why Plant Now

The framing emerged in a strategy conversation on 2026-05-04 immediately after the PR40-42 single-runtime consolidation landed and the deterministic Flame dialog was verified working end-to-end. The architectural moves of the past two weeks (one daemon, one HTTP endpoint per concern, deterministic dialog working in Flame, transport verified from inside Flame's bundled Python) made the schematic *possible* in a way it wasn't before. Capturing the framing before it slips into "we talked about this once" status is the point of this seed.

v1.5 is feature-frozen (Legibility milestone — docs and install only). The schematic is unambiguously v1.6+ work. Multiple downstream decisions in v1.6 planning will benefit from having this framing as the north star, including the Flame chat/foundry surface (SEED-FLAME-CHAT-FOUNDRY-V1.6+), v1.5 Phase 21 (surface map docs — should be written knowing the schematic is coming), and any future producer-facing UI work.

This is the visual vocabulary that makes bridge legible to artists in language they already speak. It's worth getting right.
