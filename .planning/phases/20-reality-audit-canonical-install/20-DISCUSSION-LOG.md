# Phase 20: Reality Audit + Canonical Install - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 20-reality-audit-canonical-install
**Mode:** Bulk-recommendation acceptance — user accepted all 6 area recommendations in a single turn ("The recos work for me") after reviewing the trade-offs presented up front.
**Areas discussed:** Audit methodology, Gap-fix gating, INSTALL.md scope, Doc rewrite scope (Phase 20 vs 21 boundary), External-dependency version stance, install-flame-hook.sh source-of-truth

---

## Audit methodology

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Fresh conda env on assist-01 | Keeps Postgres + Ollama + Flame in place, only Python/pip is "clean". Fastest. Catches pip/wheel/version issues. Misses: Postgres install, Ollama install, Flame install steps. | |
| (b) Second machine entirely | Friend's laptop / dev workstation. Catches everything but RECIPES-04/05 cannot be tested end-to-end without Flame. | |
| (c) Hybrid (assist-01 fresh conda env for operator full-stack + second Flame-less machine for integrator/MCP-only) | Best fidelity-to-effort ratio for a single-operator product. Doc covers full operator path; second machine catches "I assumed Postgres was already running" gaps. | ✓ |
| (d) Container/VM on assist-01 | Cleanest isolation, most overhead. | |

**User's choice:** (c) Hybrid (recommended)
**Notes:** Track A is the milestone gate (non-author UAT on assist-01 fresh conda env). Track B is an author dry-run on a Flame-less machine to surface dependency-presence assumptions Track A would mask. RECIPES-04/05 Flame prerequisite is acknowledged but is a Phase 22 concern, not Phase 20.

---

## Gap-fix gating

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Aggressive: any blocker → Phase 20 plan | Phase 20 grows but ships truly clean. Matches Phase 17 / 16.1 / 16.2 in-flight precedent. | ✓ |
| (b) Surgical: 1-line config defaults + trivial doc strings only | Bigger gaps get a 20.x decimal or v1.6 seed. | |
| (c) Doc-first: document the workaround in INSTALL.md, only patch code if the workaround is "ugly enough". | | |

**User's choice:** (a) Aggressive with a soft cap (recommended)
**Notes:** Soft cap: if a single gap balloons beyond ~1 plan worth of code, spin a 20.x decimal phase per Phase 10/10.1 and Phase 16/16.1/16.2 precedent rather than letting Phase 20 grow unboundedly. Carry-forward seeds are still allowed for genuinely v1.6+ scope (auth, multi-machine, streaming chat). The forcing function applies to install-completion gaps only.

---

## INSTALL.md scope

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Single linear "operator workstation" path | Flame + Postgres + Ollama + Anthropic key, opinionated. Matches v1.5's "first daily user" goal. | ✓ |
| (b) Two paths: operator (full) + integrator (MCP-only, no Flame, no chat) | Broader; touches the consumer pattern. | |
| (c) Three paths: operator + integrator + dev (editable + tests + alembic upgrade head) | Most complete; risks bloat. | |

**User's choice:** (a) Single operator path with an "if you don't have Flame" sidebar (recommended)
**Notes:** Sidebar covers integrator/MCP-only carveout without forking the doc. Multi-machine, multi-user, dev-only-with-tests, and projekt-forge-consumer paths drift toward Phase 21 surface-map territory and are out of scope.

---

## Doc rewrite scope (Phase 20 vs Phase 21 boundary)

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Strict lane discipline | Phase 20 only touches CLAUDE.md ground-truth + README install section. Leave README "Current Status" table and "What This Is" wholly to Phase 21 even though they're visibly stale. | |
| (b) Pragmatic: fix anything that contradicts v1.4.1 reality | Phase 21 owns new structural surface-map + "What This Is" rewrite. | ✓ |
| (c) Aggressive: full README + CLAUDE.md refresh in Phase 20 | Phase 21 narrows to GETTING-STARTED.md + projekt-forge relationship. | |

**User's choice:** (b) Pragmatic (recommended)
**Notes:** Strict discipline leaves the README's broken Status table contradicting reality for two weeks during Phase 20 audit, undermining the milestone goal. Aggressive eats Phase 21 scope and risks rewrite outpacing audit ground truth. Heuristic: "if a doc lies about reality, fix it now; new sections wait for Phase 21".

---

## External-dependency version stance

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Pin tight | Postgres 16.x, Ollama ≥0.5.x, conda 24.x, Python 3.11. | |
| (b) Minimum + reference | "Postgres ≥14, tested on 16.x" / "Python ≥3.10, reference is 3.11". | ✓ |
| (c) Loose | "modern Postgres / current Ollama / Python 3.10+". | |

**User's choice:** (b) Minimum + reference (recommended)
**Notes:** Phase 20 cannot verify every minor version of every dep; pretending otherwise creates a future-incident-waiting-to-happen. Reference versions captured during the Track A audit walk are the canonical "tested on" anchors.

---

## install-flame-hook.sh source-of-truth

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Keep both: hard-code in script + echo in README + add regression guard | Script default flipped to v1.4.1; README curl URL flipped to v1.4.1; add forge-doctor sub-check OR CI lint OR unit test to prevent future drift. | ✓ |
| (b) Single source: script writes its own version banner; README links to "see script default". | | |

**User's choice:** (a) Keep both with regression guard (recommended)
**Notes:** Bumping both to v1.4.1 is non-negotiable. Regression-guard mechanism deferred to planner — pick the lightest option (forge-doctor sub-check, CI lint, or unit test) that already aligns with the codebase's existing testing/CI conventions. Pre-flip verification (Phase 17 conservative-bump-first) confirms `v1.4.1` GitHub raw URLs resolve before the value flip lands.

## Claude's Discretion

- Exact INSTALL.md ordering (conda first vs pip-extras-block first) — planner picks based on what reads cleanly to the non-author UAT.
- Which CLAUDE.md sections survive verbatim vs. need rewrites — planner does a section-by-section diff against v1.4.1 reality.
- Whether the "if you don't have Flame" carveout is sidebar / callout / sub-section / appendix — Markdown rendering choice.
- Whether `forge_config.yaml` gets an in-tree example template, a `forge doctor --print-example-config` flag, or an inline INSTALL.md code block.
- Exact format of the dep version table (column order, "tested on" cell formatting).
- Whether the regression guard from D-17 lands in Phase 20 or as a Phase 20 follow-up plan.

## Deferred Ideas

- Multi-machine deployment guide (auth-blocked, v1.6+).
- projekt-forge consumer-pattern walk-through (Phase 21 DOCS-04).
- GETTING-STARTED.md and surface-map deep-dive (Phase 21 DOCS-01, DOCS-03).
- Daily-workflow recipes (Phase 22 RECIPES-01..06).
- TROUBLESHOOTING.md and forge-doctor failure-mode parity (Phase 23 DIAG-01..05).
- Auth (SEED-AUTH-V1.5).
- Cloud / network deployment (out of v1.5 scope).
- Maya / editorial endpoint adapters (future work).
- `forge doctor --print-example-config` flag (Claude's-discretion alternative if inline INSTALL.md code block is rejected).
