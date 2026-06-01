---
name: console-launch-decoupling
description: "The HTTP console/chat (:9996, the artist-facing surface including POST /api/v1/chat) is co-hosted INSIDE the MCP server's lifespan, and that lifespan only fires under STDIO transport. Consequence: serving an HTTP endpoint requires running a stdio process with stdin held open, while the HTTP MCP transport explicitly does NOT bind/host :9996 (the 'Phase 20.1 walk gap'). This single inversion is the root of recurring launch confusion — stdin-keepalive hacks, '--http fixes the MCP but not the chat', and consumer daemons (forge_flame/projekt_forge) inheriting the gap. Fix: make the console/chat a first-class, directly-launched ASGI service independent of MCP transport mode (or close the Phase 20.1 gap so the http path co-hosts it). Then 'start the chat server' is one transport-independent command with no stdin tricks."
type: tech-debt
planted: 2026-05-31
planted_during: "CR.1 dogfood-enablement thrash (2026-05-31). Surfaced while trying to bring up a current-code :9996 daemon for the answer-pass pipeline check; operator named it 'insanely complex for no tangible reason' — correctly. The CR.1 mechanism confirm ultimately succeeded ONLY via stdio-with-stdin-held-open (`tail -f /dev/null | python -m forge_bridge mcp stdio`); the consumer `--http` path crashed on a separate port-kwarg bug AND, even fixed, would likely not have co-hosted :9996 chat (same gap)."
trigger_when: "After v1.9 clears. A small dedicated bridge-side phase, NOT bundled into CR.1 or the dogfood (which proceed fine on the existing stdio-lifespan path). Also relevant whenever a consumer (forge-pipeline / forge_flame) hits the same '--http serves MCP but not /api/v1/chat' gap."
relates_to:
  - forge_bridge/mcp/server.py (~509-549 — lifespan co-hosts console under stdio; http path is the Phase 20.1 walk gap; default http MCP port 9997)
  - .planning/phases/CR.1-conversational-reads-answer-pass-spike/CR.1-AMENDMENT-forced-tool-seam.md (the dogfood this blocked)
  - .planning/seeds/SEED-MIGRATION-HEAD-ASSERTION-V1.9+.md (sibling operability seed)
---

# Seed — decouple the console/chat HTTP launch from the MCP transport lifespan

## The inversion (the actual problem, one thing)

The artist-facing HTTP surface — the Artist Console + `POST /api/v1/chat` on
`:9996` — is mounted via the **MCP server's lifespan**
(`forge_bridge/mcp/server.py`, the stdio branch ~`:509-513`; CLAUDE.md: "co-hosted
with the MCP server on :9996 via lifespan, NOT FastMCP custom_route"). That
lifespan co-hosts `:9996` **only under stdio transport**. The **HTTP** transport
path (`:526-549`, `streamable_http_app()` + uvicorn, default MCP port `9997`)
explicitly does **not** persistently bind/host `:9996` — the in-code "Phase 20.1
walk gap."

So an HTTP endpoint is served as a **side-effect of a stdio process's lifespan**,
and the obvious way to serve HTTP (the http transport) doesn't serve it. To bring
the chat up you run a stdio MCP server and keep its stdin open (how Claude Desktop
/ Codex launch it; how this session's mechanism-confirm worked). That is
backwards, and it is the single root of every launch-confusion symptom this
project keeps hitting.

## Essential vs accidental (don't over-fix)

**Essential, leave alone:** the `:9998` DB/registry bus as its own process;
MCP-over-stdio for Claude Desktop / per-session clients; the Flame hook on
`:9999`. Endpoint parity is sound.

**Accidental, the target:** only the `:9996` console/chat being entangled with
MCP transport mode + the stdio lifespan. Nothing else needs touching.

## The fix (bounded)

Either:
- **(A) Decouple** — the console/chat ASGI app becomes a first-class service with
  its own launch entry (`fbridge console` / part of `fbridge up`), bound to
  `:9996` regardless of whether/how an MCP server runs. The MCP server stops
  owning the HTTP surface; it connects to the same `:9998` bus like any client.
- **(B) Close the Phase 20.1 gap** — make the http MCP transport co-host the
  console lifespan so `--http` serves `:9996` chat too.

(A) is the cleaner shape — the chat surface should not be a tenant of the MCP
transport at all. (B) is smaller but preserves the entanglement.

**Win condition:** "start the chat server" is one command, transport-independent,
no stdin-keepalive, and consumers (forge_flame) don't inherit a
"--http-serves-MCP-but-not-chat" trap.

## Anti-scope

Not a daemon-supervision rewrite, not a port-topology redesign, not touching the
`:9998` bus or MCP-stdio. One thing: give the `:9996` HTTP surface its own launch
path. If it grows past that, stop.

## Grounding (live, 2026-05-31)

- `forge_bridge/mcp/server.py` ~`:509-513` (stdio → lifespan co-hosts `:9996`),
  `:526-549` (http → `streamable_http_app()`+uvicorn, the gapped path), default
  http MCP port `9997` (`main(port=9997)`).
- Confirmed empirically this session: `:9996` chat came up only via
  `tail -f /dev/null | python -m forge_bridge mcp stdio`; backgrounded stdio
  EOF-exited; `python -m projekt_forge --no-db --http --port 9996` crashed
  (consumer port bug) and is on the gapped http path regardless.
