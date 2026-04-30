# Requirements — Milestone v1.5 Legibility

**Milestone goal:** Make forge-bridge usable by its first daily user — close the gap between what's shipped (19 phases, 5 user-facing surfaces, ~40k LOC) and what a person can sit down and actually use without re-deriving the deployment topology each time.

**Categories:**

- **DOCS** — concept/orientation docs (what forge-bridge is, surface map, projekt-forge relationship)
- **INSTALL** — canonical install path verified on a clean machine
- **RECIPES** — step-by-step daily-workflow guides
- **DIAG** — diagnostics + recovery from common failure modes

---

## v1.5 Requirements

### DOCS — Concept and surface orientation

- [ ] **DOCS-01**: User can read `README.md` and understand what forge-bridge is, what it ships at v1.4.1, and which surfaces are available, without reading source code.
- [ ] **DOCS-02**: User can read `CLAUDE.md` and find a ground-truth section that reflects v1.4.1 state (not the v1.0 "extract from projekt-forge" snapshot).
- [ ] **DOCS-03**: User can read `docs/GETTING-STARTED.md` and learn the five user-facing surfaces (Web UI on `:9996/ui/`, CLI `forge-bridge`, `/api/v1/chat` HTTP, MCP server `python -m forge_bridge`, Flame hook on `:9999`) — what each is for and how they fit together.
- [ ] **DOCS-04**: User can find an explicit statement of forge-bridge's relationship to projekt-forge (consumer pattern, version pin discipline) in either `README.md` or `docs/GETTING-STARTED.md`.

### INSTALL — Canonical install path

- [ ] **INSTALL-01**: User can follow `docs/INSTALL.md` end-to-end on a fresh machine and reach a working forge-bridge install with all five surfaces reachable (Python env, `pip install`, Postgres reachable, Ollama reachable, Flame hook installed, MCP server boots cleanly).
- [ ] **INSTALL-02**: User running `install-flame-hook.sh` with default settings gets the `v1.4.1` Flame hook installed (current default points at a stale tag).
- [ ] **INSTALL-03**: README.md install section and `docs/INSTALL.md` agree — no version drift between them; install section in README either inlines the canonical steps or links unambiguously into `docs/INSTALL.md`.
- [ ] **INSTALL-04**: User can identify all required external dependencies (Postgres version, Ollama, conda env, Python version, Anthropic API key surface) from the install doc before starting, not by hitting errors mid-install.

### RECIPES — Daily-workflow step-by-steps

- [ ] **RECIPES-01**: User can follow a "first-time setup on a personal workstation" recipe (assumes fresh INSTALL-01 install completed) and reach a state where they can run a sample query against `:9996/ui/`.
- [ ] **RECIPES-02**: User can follow a "connect Claude Desktop / Claude Code to forge-bridge" recipe and successfully invoke an MCP tool from their LLM client.
- [ ] **RECIPES-03**: User can follow a "watch tool synthesis happen, then use the synthesized tool" recipe and observe the learning pipeline promoting a repeated operation into a new MCP tool with provenance metadata.
- [ ] **RECIPES-04**: User can follow a "drive a multi-step Flame automation via `/api/v1/chat`" recipe and see the agentic tool-call loop execute Flame operations end-to-end with a natural-language answer at the end (the FB-D shipped path).
- [ ] **RECIPES-05**: User can follow an "approve / reject staged operations from the Web UI" recipe and complete a full staged-operation lifecycle (`proposed → approved → executed`).
- [ ] **RECIPES-06**: User can follow an "inspect the manifest to see auto-promoted tools" recipe — Web UI, CLI, and MCP resource paths — and verify provenance fields (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`).

### DIAG — Failure modes and recovery

- [ ] **DIAG-01**: User can follow `docs/TROUBLESHOOTING.md` to diagnose a Flame crash and recover the bridge (Flame hook restart, MCP server graceful-degradation behavior verified).
- [ ] **DIAG-02**: User can follow `docs/TROUBLESHOOTING.md` to diagnose a Postgres restart / unavailability and recover (forge-bridge JSONL-authoritative + SQL-mirror semantics, restart sequence).
- [ ] **DIAG-03**: User can follow `docs/TROUBLESHOOTING.md` to diagnose an Ollama hang / cold start and recover (model preload, timeout signals).
- [ ] **DIAG-04**: User can follow `docs/TROUBLESHOOTING.md` to diagnose a qwen3 cold-start `LLMLoopBudgetExceeded` and apply a recovery path (model selection guidance + `SEED-DEFAULT-MODEL-BUMP-V1.4.x` context).
- [ ] **DIAG-05**: `forge doctor` output covers every failure mode named in `docs/TROUBLESHOOTING.md` — or this milestone explicitly polishes `forge doctor` to do so. Gaps surfaced during recipe / install authoring are closed in-flight.

---

## Future Requirements (deferred to v1.6+)

Carry-forward seeds remain planted in `.planning/seeds/`:

- `SEED-OPUS-4-7-TEMPERATURE-V1.5` — AnthropicAdapter `temperature` elision
- `SEED-DEFAULT-MODEL-BUMP-V1.4.x` — qwen3:32b default after thinking-mode mitigation
- `SEED-AUTH-V1.5` — caller-identity migration for chat rate limiting
- `SEED-CHAT-STREAMING-V1.4.x` — streaming chat responses (deferred unless operator feedback triggers)
- `SEED-CHAT-CLOUD-CALLER`, `SEED-CHAT-PARTIAL-OUTPUT`, `SEED-CHAT-PERSIST-HISTORY`, `SEED-CHAT-TOOL-ALLOWLIST`, `SEED-CMA-MEMORY`, `SEED-CROSS-PROVIDER-FALLBACK`, `SEED-MESSAGE-PRUNING`, `SEED-PARALLEL-TOOL-EXEC`, `SEED-STAGED-CLOSURE`, `SEED-STAGED-REASON`, `SEED-TOOL-EXAMPLES`

---

## Out of Scope (explicit exclusions for v1.5)

- **New external dependencies.** Legibility milestone only — public `forge_bridge.__all__` stays at 19 unless an install audit surfaces a genuine need.
- **New features (auth, streaming, model bumps, parallel tools, etc.).** All planted seeds defer to v1.6+. v1.5 is documentation, install ergonomics, and diagnostics; not feature work.
- **Multi-user / multi-machine deployment guides.** v1.5 targets the single-operator daily workstation. Multi-host deployment is a separate milestone after auth lands.
- **Maya / editorial endpoint adapters.** Future work. v1.5 documents Flame as the only shipped non-LLM endpoint.
- **External-research-driven design.** v1.5 is an internal codebase audit + workflow articulation milestone. No 4-agent project research; no external pattern discovery.

---

## Traceability

| REQ-ID | Description | Phase |
|---|---|---|
| DOCS-01 | README is accurate to v1.4.1 | Phase 21 |
| DOCS-02 | CLAUDE.md ground-truth refresh | Phase 20 |
| DOCS-03 | GETTING-STARTED surface map | Phase 21 |
| DOCS-04 | projekt-forge relationship documented | Phase 21 |
| INSTALL-01 | INSTALL.md verified on clean machine | Phase 20 |
| INSTALL-02 | install-flame-hook.sh default v1.4.1 | Phase 20 |
| INSTALL-03 | README install ↔ INSTALL.md consistency | Phase 20 |
| INSTALL-04 | External dep inventory complete | Phase 20 |
| RECIPES-01 | First-time setup recipe | Phase 22 |
| RECIPES-02 | Claude Desktop / Code wiring recipe | Phase 22 |
| RECIPES-03 | Tool synthesis observation recipe | Phase 22 |
| RECIPES-04 | Multi-step Flame chat recipe | Phase 22 |
| RECIPES-05 | Staged-ops approval recipe | Phase 22 |
| RECIPES-06 | Manifest inspection recipe | Phase 22 |
| DIAG-01 | Flame crash recovery | Phase 23 |
| DIAG-02 | Postgres restart recovery | Phase 23 |
| DIAG-03 | Ollama hang recovery | Phase 23 |
| DIAG-04 | qwen3 cold-start LLMLoopBudgetExceeded | Phase 23 |
| DIAG-05 | forge doctor coverage parity | Phase 23 |
