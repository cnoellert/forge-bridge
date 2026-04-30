# Phase 20: Reality Audit + Canonical Install - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Walk a fresh forge-bridge install end-to-end on a clean machine, fix any gaps surfaced during the walk, and ship four artifacts:

1. `docs/INSTALL.md` — canonical operator-workstation install path
2. Refreshed `README.md` install section (no version drift; agrees with INSTALL.md)
3. Refreshed `CLAUDE.md` ground-truth (matches v1.4.1 reality, not the v1.0 "extracted from projekt-forge" snapshot)
4. `scripts/install-flame-hook.sh` default `FORGE_BRIDGE_VERSION` pinned to `v1.4.1`

**Forcing function:** if INSTALL.md does not work end-to-end on a clean machine for a non-author, the milestone does not ship. Phase 20 is the gate for v1.5.

**Five surfaces** must be reachable after a verbatim INSTALL.md walkthrough:
- Web UI on `:9996/ui/`
- CLI `forge-bridge`
- HTTP `/api/v1/chat`
- MCP server (`python -m forge_bridge`, stdio default)
- Flame hook on `:9999`

**Out of scope** (explicitly Phase 21 territory): new `docs/GETTING-STARTED.md`, README "What This Is" rewrite, surface-map deep-dive, projekt-forge consumer-pattern explainer. Phase 20 only refreshes content that *contradicts* v1.4.1 reality or blocks the install path.

</domain>

<decisions>
## Implementation Decisions

### Audit methodology (D-01..03)
- **D-01:** Hybrid two-track audit. **Track A — operator workstation** runs on a fresh conda env on assist-01 (Postgres + Ollama + Flame remain in place; only the Python/pip layer is "clean"). **Track B — integrator/MCP-only** runs on a second machine without Flame to surface "I assumed Postgres was already running" / "I assumed Ollama was already preloaded" gaps that Track A masks.
- **D-02:** A non-author runs the verbatim INSTALL.md walkthrough on Track A as the milestone gate. The non-author UAT is the locked acceptance criterion — "passes for the author" does not count. Pattern matches Phase 10.1 D-36 fresh-operator dogfood UAT and Phase 16.1/16.2 fresh-operator UAT precedent.
- **D-03:** Track B does not need a non-author UAT pass; an author-driven dry-run on a Flame-less machine is sufficient. Track B exists to catch dependency-presence assumptions, not to gate the milestone.

### Gap-fix gating (D-04..06)
- **D-04:** Aggressive in-flight gap-fix policy with a soft cap. Any gap that blocks Track A or Track B completion gets a code-fix plan added to Phase 20. "Document the workaround" is not an acceptable resolution for an install-blocking gap — the milestone goal is that the doc works end-to-end.
- **D-05:** Soft cap: if a single gap balloons beyond ~1 plan worth of code (e.g., a substantive feature gap, a new healthcheck endpoint, a config-file contract redesign), spin a decimal phase (20.1, 20.2) following the Phase 10/10.1 and Phase 16/16.1/16.2 precedent rather than letting Phase 20 grow unboundedly.
- **D-06:** Carry-forward seeds are still allowed for gaps that are genuinely v1.6+ scope (e.g., auth, multi-machine deployment, streaming chat). The forcing function applies to install-completion gaps only, not feature gaps surfaced by the audit.

### INSTALL.md scope (D-07..09)
- **D-07:** Single linear "operator workstation" path. Audience is the daily-user operator with Flame + Postgres + Ollama + Anthropic API key. The doc is opinionated — one path through.
- **D-08:** "If you don't have Flame" sidebar (or equivalent compact carveout) inside INSTALL.md. Tells an integrator/MCP-only reader which steps to skip and which surfaces will not be reachable. Avoids forking the doc into two parallel paths while still acknowledging Track B's reality.
- **D-09:** Multi-machine, multi-user, dev-only-with-tests, projekt-forge-consumer-walkthrough are **out of scope**. The single-operator path covers the v1.5 milestone goal; broader paths are deferred to v1.6+.

### Doc rewrite scope — Phase 20 vs Phase 21 boundary (D-10..12)
- **D-10:** Pragmatic boundary. Phase 20 fixes any README/CLAUDE.md content that *contradicts* v1.4.1 reality or blocks the install path. New structural sections (surface map, projekt-forge relationship explainer, GETTING-STARTED.md) are Phase 21.
- **D-11:** README.md scope in Phase 20: install section refresh + the "Current Status" table (currently claims canonical-vocabulary is "in design" and dep-graph is "planned" — both shipped). The README "What This Is" / "Vision" / "Architecture" sections are Phase 21 unless they directly contradict v1.4.1 reality.
- **D-12:** CLAUDE.md scope in Phase 20: rewrite "What exists and works" to enumerate the 5 surfaces + observability + learning pipeline + staged ops + chat (currently lists only Flame bridge + MCP server). Rewrite "Active Development Context" (currently says "As of 2026-02-24: Just extracted from projekt-forge"). Repository Layout, Vocabulary Summary, Key Decisions table all may need touch-ups but only where they actively mislead.

### External-dependency version stance (D-13..14)
- **D-13:** Minimum-version + reference-version model. Format: "Postgres ≥14, tested on 16.x" / "Python ≥3.10, reference is 3.11" / "Ollama: latest stable, tested on the version assist-01 runs at audit time". Phase 20 cannot verify every minor version of every dep; pretending otherwise creates a future-incident-waiting-to-happen.
- **D-14:** Reference versions captured during the audit walk are the canonical "tested on" anchors. The audit walkthrough records them as it goes; INSTALL.md's dep table cites them.

### install-flame-hook.sh source-of-truth (D-15..17)
- **D-15:** Bump `scripts/install-flame-hook.sh` default `FORGE_BRIDGE_VERSION` from `v1.1.0` to `v1.4.1` (current 3-way drift: script `v1.1.0`, README curl URL `v1.2.1`, live tag `v1.4.1`). Single-line value flip ships in its own commit per Phase 17 D-30 decoupled-commit purity. README curl URL bumped to `v1.4.1` in the same plan but as a separate commit if convenient.
- **D-16:** Pre-flip verification per Phase 17 MODEL-02 conservative-bump-first pattern: confirm `https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh` and `.../v1.4.1/flame_hooks/forge_bridge/scripts/forge_bridge.py` resolve before flipping the script default. Do not pin to a tag that does not exist.
- **D-17:** Add a regression guard against future 3-way drift. Lightweight options (any one suffices, in priority order): (a) `forge doctor` sub-check that diffs `scripts/install-flame-hook.sh` `FORGE_BRIDGE_VERSION` default against the README's curl URL version; (b) a CI lint that fails on mismatch; (c) a `tests/test_install_hook_version_consistency.py` unit test. Choice deferred to planner — pick the lightest one that's already aligned with the codebase's existing testing/CI conventions.

### Claude's Discretion
- Exact INSTALL.md ordering (e.g., conda first or pip-extras-block first); the planner picks based on what reads cleanly to the non-author UAT.
- Which CLAUDE.md sections survive verbatim vs. need rewrites; planner does a section-by-section diff against v1.4.1 reality.
- Whether the "if you don't have Flame" carveout is a sidebar, callout box, separate sub-section, or appendix — Markdown rendering choice.
- Whether `forge_config.yaml` gets an in-tree example template, a `forge doctor --print-example-config` flag, or just an inline INSTALL.md code block. Planner picks based on what reduces the most install friction without inventing new product surface.
- The exact format of dep version table (column order, "tested on" cell formatting).
- Whether the regression guard from D-17 lands in Phase 20 or as a Phase 20 follow-up plan; planner judges based on Phase 20 plan-count budget.

### Folded Todos
None — phase-todo match returned 0.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements + scope
- `.planning/PROJECT.md` — milestone goal "Make forge-bridge usable by its first daily user"; v1.4.1 close-state inventory (19 phases, 5 surfaces, ~40k LOC, 19-symbol `__all__`); v1.5 constraints ("Legibility, not features"; "no new external libraries"; forcing function)
- `.planning/REQUIREMENTS.md` — INSTALL-01..04, DOCS-02 acceptance criteria; v1.5 traceability table
- `.planning/ROADMAP.md` — Phase 20 success criteria (1–5); dependency on nothing (first phase of v1.5); UI hint: yes
- `.planning/STATE.md` — v1.4.1 close metrics, v1.5 phase pre-design, RECIPES-04/05 Flame-prerequisite caveat

### Artifacts to refresh / produce
- `README.md` — current "Current Status" table (lines 53–63) is stale; install section (lines 95–142) pinned to `v1.2.1`; "What This Is" / "Vision" / "Relationship to projekt-forge" sections are Phase 21 territory but the install section is Phase 20
- `CLAUDE.md` — "Current State / What exists and works" (lines 23–46) lists only Flame bridge + MCP server; "Active Development Context" (lines 147–154) says "As of 2026-02-24: Just extracted from projekt-forge"; full ground-truth refresh required
- `scripts/install-flame-hook.sh` — current `FORGE_BRIDGE_VERSION="${FORGE_BRIDGE_VERSION:-v1.1.0}"` default (line 29) and embedded README example URL (line 10) both need bump to `v1.4.1`
- `docs/INSTALL.md` — does not exist; Phase 20 creates it
- `flame_hooks/forge_bridge/scripts/forge_bridge.py` — Flame-side hook source; install path target; do not break

### Existing project docs (cite as cross-links from INSTALL.md, do not rewrite)
- `docs/ARCHITECTURE.md` — design decisions; INSTALL.md may link "for design rationale, see ..."
- `docs/API.md` — HTTP API for the Flame bridge; cite for "verify the bridge responds with curl"
- `docs/VOCABULARY.md` — canonical vocabulary spec; not install-relevant, do not touch
- `docs/ENDPOINTS.md` — endpoint adapter authoring guide; not install-relevant in Phase 20
- `docs/DATA_MODEL.md`, `docs/FLAME_API.md` — domain references, not install-relevant

### Codebase surfaces to verify reachability against
- `forge_bridge/__main__.py` — MCP server entry (`python -m forge_bridge`)
- `forge_bridge/console/app.py` — Web UI mount on `:9996/ui/`
- `forge_bridge/console/handlers.py` — `/api/v1/chat` HTTP route
- `forge_bridge/cli/` (client.py, doctor.py, execs.py, health.py, manifest.py, tools.py, render.py, since.py) — `forge-bridge` CLI (Typer+Rich)
- `flame_hooks/forge_bridge/scripts/forge_bridge.py` — Flame hook (`:9999`)
- `pyproject.toml` — package version, declared deps, optional extras (`[dev]`, `[llm]`)
- `alembic.ini` + `forge_bridge/store/migrations/` — DB migrations (operator must run `alembic upgrade head` against admin DB)

### Carry-forward seeds relevant to install-time guidance
- `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` — qwen3:32b cold-start `LLMLoopBudgetExceeded` context; INSTALL.md should default to `qwen2.5-coder:32b` (the locked default) and note the qwen3 caveat
- `.planning/seeds/SEED-OPUS-4-7-TEMPERATURE-V1.5.md` — Anthropic adapter `temperature` constraint; informs which Claude models work today (sonnet-4-6 is the verified default)
- `.planning/seeds/SEED-AUTH-V1.5.md` — authentication is deferred; INSTALL.md should not promise multi-user / shared-deployment behavior

### Conventions / precedents (locked patterns from prior phases)
- `.planning/milestones/v1.4.x-phases/17-default-model-bumps/17-CONTEXT.md` — D-30 decoupled-commit purity (constant-extraction commit separate from value-flip commit); MODEL-02 conservative-bump-first pre-run UAT pattern
- `.planning/milestones/v1.4-phases/16.2-bug-d-chat-tool-call-loop/16.2-CONTEXT.md` — fresh-operator UAT precedent for non-author dogfood gating
- `.planning/milestones/v1.3-phases/10.1-artist-ux-gap-closure/10.1-CONTEXT.md` (if present) — D-36 dogfood UAT pattern that this phase's audit-walk inherits

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`scripts/install-flame-hook.sh`** — already exists, already supports `curl | bash` standalone install, already has Python AST parse sanity check. Phase 20 only flips the default `FORGE_BRIDGE_VERSION` and updates the embedded README example URL.
- **`forge_bridge/cli/doctor.py`** — `forge doctor` already runs an expanded check matrix (JSONL parseability, sidecar dirs, port reachability, disk space). The D-17 regression guard for install-script-version-drift is a candidate sub-check here.
- **`forge_bridge/console/handlers.py`** — `/api/v1/chat` is shipped (FB-D, Phase 16). INSTALL.md verification step can curl this endpoint as part of "all 5 surfaces reachable" sanity check.
- **`forge_bridge/cli/health.py`** — already exposes a health-check path that INSTALL.md can use as a smoke test.
- **`alembic.ini` + migrations** — Alembic is already set up; INSTALL.md just needs to document the `alembic upgrade head` invocation against the consumer DB.

### Established patterns
- **Decoupled-commit purity (Phase 17 D-30):** structural changes (constant extractions, file moves) ship in their own commit separate from value flips. Applies to: `install-flame-hook.sh` version bump (single-line value flip in its own commit).
- **Conservative-bump-first (Phase 17 MODEL-02):** verify the candidate value works before flipping. Applies to: confirming `v1.4.1` GitHub raw-URL paths resolve before flipping the script default.
- **Fresh-operator dogfood UAT (Phase 10.1 D-36, Phase 16.1, Phase 16.2):** non-author runs the user-facing surface verbatim. Applies to: Track A INSTALL.md walkthrough.
- **Decimal phase insertion (10/10.1, 16/16.1/16.2):** when a single gap balloons beyond a plan, spin a 20.x rather than overgrowing the parent phase. Applies to: D-05 soft cap.
- **HUMAN-UAT artifact pattern:** prior phases produce `XX-HUMAN-UAT.md` capturing the non-author walk-through verbatim. Phase 20's Track A UAT should follow this pattern.

### Integration points
- **README ↔ INSTALL.md ↔ install-flame-hook.sh** — three artifacts must agree on every version number after Phase 20. The D-17 regression guard exists to keep them aligned post-Phase 20.
- **`pyproject.toml` ↔ INSTALL.md dep table** — INSTALL.md references the declared deps and extras; if `pyproject.toml` shifts in a future phase, INSTALL.md must follow.
- **Operator-workstation reality on assist-01** — Track A audits a fresh conda env on assist-01; the audit's "tested on" reference versions for Postgres/Ollama/Flame come from this environment.

</code_context>

<specifics>
## Specific Ideas

- The author has a strong preference for *strong recommendations* on technical decisions outside the user's pipeline expertise — Phase 20 plans should lean on Phase 17's decoupled-commit pattern, Phase 16.x's fresh-operator UAT pattern, and Phase 10.1's dogfood gate without re-litigating them.
- "Artist-first / non-developer dogfood UAT required on every UI phase" applies here in spirit: Track A's non-author walkthrough IS the UAT gate, even though Phase 20 ships docs not pixels.
- The forcing function ("if INSTALL.md doesn't work end-to-end, we don't ship") matches the user's "soft UAT gate is the right tool for technical surfaces" pattern from Phase 11 D-08.
- Reference versions for the dep table come from assist-01 at audit time, not from a hypothetical "current stable" claim. The doc should record what was actually tested.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-machine deployment guide.** Out of v1.5 scope (PROJECT.md). Stays deferred until auth lands.
- **projekt-forge consumer-pattern walk-through.** Phase 21 (DOCS-04) territory.
- **GETTING-STARTED.md and surface-map deep-dive.** Phase 21 (DOCS-01, DOCS-03).
- **Daily-workflow recipes (first-time setup, Claude Desktop wiring, tool synthesis observation, chat-driven Flame automation, staged-ops approval, manifest inspection).** Phase 22 (RECIPES-01..06).
- **TROUBLESHOOTING.md (Flame crash, Postgres restart, Ollama hang, qwen3 cold-start).** Phase 23 (DIAG-01..05).
- **`forge doctor` parity polish (every TROUBLESHOOTING.md failure mode covered by `forge doctor` output).** Phase 23 (DIAG-05) — but if Phase 20 audit surfaces a doctor-level gap (e.g., port-reachability check missing, version-drift check missing), it can land here per D-04 aggressive in-flight gating.
- **Auth (caller-identity migration, multi-user rate limiting).** SEED-AUTH-V1.5; v1.6+ scope.
- **Cloud / network deployment.** Out of v1.5 scope; stays local-first.
- **Maya / editorial endpoint adapters.** Future work; v1.5 documents Flame as the only shipped non-LLM endpoint.
- **`forge doctor --print-example-config` flag** (Claude's-discretion candidate from D-09 / config-template question). If planner decides against the inline INSTALL.md code block, this is the alternative — but only if it doesn't grow product surface.

### Reviewed Todos (not folded)
None — phase-todo match returned 0 hits.

</deferred>

---

*Phase: 20-reality-audit-canonical-install*
*Context gathered: 2026-04-30*
