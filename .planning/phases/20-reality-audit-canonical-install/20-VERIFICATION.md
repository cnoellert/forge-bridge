---
phase: 20-reality-audit-canonical-install
verified: 2026-04-30T20:00:00Z
status: gaps_found
score: 4/5 must-haves verified
overrides_applied: 0
gaps:
  - truth: "A non-author can follow docs/INSTALL.md verbatim on a clean machine and reach all five surfaces without hitting undocumented errors (INSTALL-01 / SC-1)"
    status: partial
    reason: >
      docs/INSTALL.md exists and shipped at v1.4.1. All five surfaces were reached
      by the author-walk. However, the author-walk hit 13 documented gaps, two of
      which are structural blockers that would prevent a normal Flame artist from
      completing the install without sysadmin knowledge not in the doc: (a) Step 3
      Postgres setup requires pg_hba.conf editing, password_encryption probing,
      and cluster init knowledge the doc does not provide; (b) Step 6 contains a
      substantive doc lie — the claim that 'python -m forge_bridge' boots all four
      hosted surfaces in one shot is false; forge_bridge.server must be started
      separately as a prerequisite. The architecture is sound; the install
      procedure is not yet accessible to the target user (Flame artists / pipeline
      operators without Linux sysadmin background). Gap is routed to Phase 20.1 as
      a v1.5 ship blocker — NOT a --gaps re-plan inside Phase 20.
    artifacts:
      - path: "docs/INSTALL.md"
        issue: >
          Step 6 line 234 claims 'python -m forge_bridge boots all four hosted
          surfaces in one shot' — false. forge_bridge.server is a separate process
          (the WebSocket bus on :9998) that must start first; python -m forge_bridge
          is a CLIENT of :9998. Gap #11 in 20-HUMAN-UAT.md. Step 3 Postgres setup
          requires Linux/Postgres knowledge (pg_hba.conf, password_encryption,
          --initdb lifecycle) that the doc does not provide — gaps #1, #3, #4, #6
          in 20-HUMAN-UAT.md.
    missing:
      - "install-bootstrap.sh script handling Postgres init, pg_hba, role+db creation, alembic"
      - "systemd units for two-process start order (forge-bridge-server.service + forge-bridge.service)"
      - "env file template at /etc/forge-bridge/forge-bridge.env"
      - "INSTALL.md Step 3 collapse to 'run install-bootstrap.sh'"
      - "INSTALL.md Step 6 corrected to remove the single-process lie"
    phase_20_1_reference: ".planning/phases/20-reality-audit-canonical-install/20-PHASE-20.1-CANDIDATE.md"
deferred:
  - truth: "Track B integrator dry-run confirms INSTALL.md works for MCP-only operators without Flame"
    addressed_in: "Phase 20.1"
    evidence: >
      20-HUMAN-UAT.md Action section: 'Plan 20-06 (Track B dry-run) is subsumed by
      Phase 20.1's acceptance criteria — running Track B against the current INSTALL.md
      would just re-discover the same 13 gaps. Defer Track B to 20.1 where the
      install.sh path makes Track B mostly automatic.'
human_verification: []
---

# Phase 20: Reality Audit + Canonical Install — Verification Report

**Phase Goal:** A new user can follow `docs/INSTALL.md` on a fresh machine and reach a working forge-bridge install — every gap found during the audit walk-through is fixed in-flight before the doc ships.
**Verified:** 2026-04-30T20:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

> ## CRITICAL FRAMING — read before interpreting any table below
>
> This phase presents a dual reality that must be stated plainly:
>
> **Artifacts shipped: YES.** Every declared artifact exists at HEAD at v1.4.1.
> Version consistency is enforced. Regression guard passes. CLAUDE.md, README.md,
> and INSTALL.md all reflect v1.4.1 ground truth.
>
> **Phase goal as stated met for a non-author (Flame artist): NO.** The Track A
> UAT walk (20-HUMAN-UAT.md) found that no normal Flame artist could complete
> docs/INSTALL.md. 13 gaps were surfaced. Two are structural blockers that cannot
> be fixed with prose patches alone: the Postgres setup complexity (Steps 3a–3c
> require pg_hba.conf knowledge) and the substantive doc lie in Step 6 (the
> two-process architecture is undocumented — docs/INSTALL.md claims
> `python -m forge_bridge` boots "all four surfaces in one shot"; it does not —
> forge_bridge.server must be started separately).
>
> **The gaps are not --gaps re-plan items inside Phase 20.** They are the input
> requirements for Phase 20.1, already captured as a v1.5 ship blocker candidate
> in `.planning/phases/20-reality-audit-canonical-install/20-PHASE-20.1-CANDIDATE.md`.
> Do NOT run `/gsd-plan-phase 20 --gaps`. Open Phase 20.1 instead.

---

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Non-author follows docs/INSTALL.md verbatim on a clean machine, all five surfaces reachable, no undocumented errors | PARTIAL | Author-walked with 13 gaps; 5/5 surfaces reached by walker with SSH triage access. A true non-author (Flame artist) would be blocked at Step 3 (Postgres) and Step 6 (two-process lie). See 20-HUMAN-UAT.md. |
| SC-2 | Running install-flame-hook.sh with default settings installs the v1.4.1 Flame hook | VERIFIED | `VERSION="${FORGE_BRIDGE_VERSION:-v1.4.1}"` confirmed at scripts/install-flame-hook.sh line 29. No `v1.1.0` references remain. |
| SC-3 | README install section and docs/INSTALL.md agree on every version number; a reader following either reaches the same state | VERIFIED | v1.4.1 curl URL confirmed in both README.md and docs/INSTALL.md. `tests/test_install_hook_version_consistency.py` regression guard passes. Both docs reference same env vars, same conda env name, same pip extras. |
| SC-4 | User can identify all required external dependencies from the install doc before starting, not by hitting them mid-install | VERIFIED | docs/INSTALL.md "Before you start" section includes split dependency table: "Operator host" (conda, Python, PostgreSQL, Flame) and "Reachable network services" (Ollama daemon, qwen2.5-coder:32b, Anthropic API optional). Topology/network reachability subsection added by Plan 20-07. All seven dependency categories present. |
| SC-5 | CLAUDE.md reflects v1.4.1 ground truth — "what exists and works" and "what is designed but not yet implemented" match shipped reality | VERIFIED | CLAUDE.md: all 5 surfaces enumerated (`:9996/ui/`, `/api/v1/chat`, `forge-bridge console doctor`, `flame_hooks/.../forge_bridge.py`, `python -m forge_bridge`). "As of 2026-02-24: Just extracted from projekt-forge" purged. "Milestone: v1.5 Legibility" present. `forge_bridge/core/` correctly listed as shipped (not "in design"). `[dev,llm]` extras documented. Bare `--http --port 8080` flag removed. |

**Score: 4/5** truths verified (SC-1 partially met; gap routed to Phase 20.1)

---

## Per-Requirement Status

### INSTALL-01: docs/INSTALL.md verified on clean machine

**Requirement:** User can follow `docs/INSTALL.md` end-to-end on a fresh machine and reach a working forge-bridge install with all five surfaces reachable.

| Dimension | Status | Evidence |
|-----------|--------|----------|
| Artifact shipped | VERIFIED | `docs/INSTALL.md` exists at HEAD, 374 lines, 8-step structure with all Plan 20-04 and 20-07 content |
| Author-walk result | PARTIAL | 20-HUMAN-UAT.md status: `partial`. Track A result: `PASS-with-deviations`. 13 gaps surfaced, 5/5 surfaces reached only with author SSH-triage access |
| Non-author clean walk | NOT MET | D-02.1 amendment: no fully-non-author walker available. Walker is non-author of the install procedure but is author of planning artifacts. Author-walk accepted as deviation from the milestone gate, logged as `SEED-PHASE-20-NON-AUTHOR-UAT-V1.6+.md` |
| Artist accessibility | NOT MET | Headline finding from 20-HUMAN-UAT.md: "No normal artist could complete this install." Step 3 (Postgres) and Step 6 (two-process startup lie) are structural blockers for non-sysadmin users |

**What shipped:** docs/INSTALL.md at v1.4.1, 8-step opinionated operator path, Track B carveout, multi-host topology framing (Plan 20-07), external dep tables, env-var reference, port reference, LLM service host appendix.

**What is pending in 20.1:** install-bootstrap.sh (handles Postgres init/pg_hba/role+db/migrations), two systemd units (forge-bridge-server.service + forge-bridge.service) enforcing correct start order, env file template, INSTALL.md Step 3 and Step 6 collapse to script-based invocations.

**Does this requirement meet its stated success criterion?** Partially. The artifact exists and is substantive. A technically sophisticated operator could follow it with effort. An artist (the target user) could not. INSTALL-01 closes only when Phase 20.1 closes.

---

### INSTALL-02: install-flame-hook.sh defaults to v1.4.1

**Requirement:** User running install-flame-hook.sh with default settings gets the v1.4.1 Flame hook installed.

| Artifact | Status | Evidence |
|----------|--------|----------|
| `pyproject.toml` | VERIFIED | `version = "1.4.1"` confirmed at line 7. No `version = "1.3.0"` present. |
| `scripts/install-flame-hook.sh` | VERIFIED | `VERSION="${FORGE_BRIDGE_VERSION:-v1.4.1}"` confirmed. All three load-bearing lines (comment example URL, env-override comment, actual default) flip to v1.4.1. Zero `v1.1.0` references remain. |
| `tests/test_public_api.py::test_package_version` | VERIFIED | Asserts `1.4.1`, updated from `1.3.0`. |
| `tests/test_install_hook_version_consistency.py` | VERIFIED | 80-line file. Both regression tests (`test_install_hook_default_version_matches_pyproject`, `test_readme_curl_url_version_matches_pyproject`) present. Guards against three-way version drift. |

**Does this requirement meet its stated success criterion?** YES. INSTALL-02 is fully met.

---

### INSTALL-03: README.md install section and docs/INSTALL.md agree

**Requirement:** README.md install section and docs/INSTALL.md agree — no version drift; install section links or inlines the canonical steps.

| Check | Status | Evidence |
|-------|--------|----------|
| curl URL version (README) | VERIFIED | `cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh` confirmed in README.md |
| curl URL version (INSTALL.md) | VERIFIED | Same v1.4.1 URL confirmed in docs/INSTALL.md |
| Stale `--http --port 8080` flag in README | VERIFIED PURGED | Zero occurrences of `--http --port 8080` in README.md |
| `[dev,llm]` extras in README | VERIFIED | `pip install -e ".[dev,llm]"` present in README.md |
| Current Status table | VERIFIED | "Canonical vocabulary layer" marked Shipped. "Artist Console", "CLI", "Staged-operations platform", "LLMRouter agentic tool-call loop", "Chat endpoint" all present as Shipped rows. "🔧 In design" row absent. |
| Five-surface smoke test block in README | VERIFIED | All five surfaces covered including `:9996/ui/`, `/api/v1/chat`, `forge-bridge console doctor` |
| Consistency regression guard | VERIFIED | `tests/test_install_hook_version_consistency.py` enforces README curl URL == pyproject.toml version |
| Cross-reference from README to INSTALL.md | VERIFIED | README.md references `docs/INSTALL.md` for full env-var reference |

**Does this requirement meet its stated success criterion?** YES. INSTALL-03 is fully met.

---

### INSTALL-04: External dependency inventory complete before install begins

**Requirement:** User can identify all required external dependencies from the install doc before starting, not by hitting errors mid-install.

| Dependency | Covered in INSTALL.md | Notes |
|------------|----------------------|-------|
| conda | YES | "Operator host" table; reference ~24.x |
| Python | YES | "Operator host" table; minimum 3.10, reference 3.11 |
| PostgreSQL | YES | "Operator host" table; minimum 14, reference 16.x |
| Ollama daemon | YES | "Reachable network services" table; reference 0.21.0 |
| qwen2.5-coder:32b model | YES | "Reachable network services" table; pull command provided |
| Flame | YES | "Operator host" table; Track B carveout explains how to skip |
| Anthropic API key | YES | "Reachable network services" table; explicitly OPTIONAL with reason |
| Topology / network reachability | YES | Separate subsection added by Plan 20-07; pre-walk reachability checks included |

**Caveat noted in UAT:** Gap #7 (env var persistence) and gap #9 (conda env must be active at Step 6) are not listed in "Before you start" — these are gaps Phase 20.1 addresses structurally via the systemd+env-file model. They do not block INSTALL-04's stated criterion (dep identification before starting), but they do indicate the doc has comprehension holes mid-walk.

**Does this requirement meet its stated success criterion?** YES for the dep identification criterion. All required external dependencies are listed in the "Before you start" section before Step 1. INSTALL-04 is met as stated, with the Phase 20.1 caveat that mid-walk comprehension gaps exist.

---

### DOCS-02: CLAUDE.md ground-truth refresh

**Requirement:** User can read CLAUDE.md and find a ground-truth section that reflects v1.4.1 state.

| Check | Status | Evidence |
|-------|--------|----------|
| All five surfaces enumerated by file path + port | VERIFIED | `:9996/ui/`, `/api/v1/chat`, `forge-bridge console doctor`, `flame_hooks/.../forge_bridge.py`, `python -m forge_bridge` — all confirmed present |
| "As of 2026-02-24" stale anchor purged | VERIFIED | Zero occurrences in CLAUDE.md |
| "Just extracted from projekt-forge" stale framing purged | VERIFIED | Zero occurrences in CLAUDE.md |
| Canonical vocabulary layer correctly listed as SHIPPED | VERIFIED | `forge_bridge/core/` enumerated under "What exists and works"; removed from "What is designed but not yet implemented" |
| Active Development Context references v1.5 Legibility | VERIFIED | "Milestone: v1.5 Legibility" present (2 occurrences) |
| `pip install -e ".[dev,llm]"` in How to Get Running | VERIFIED | `[dev,llm]` extras documented; bare `pip install -e .` absent |
| stdin-keepalive note present | VERIFIED | `tail -f /dev/null | python -m forge_bridge` confirmed present |
| Stale `--http --port 8080` absent | VERIFIED | Zero occurrences |
| CLAUDE.md line count | VERIFIED | 238 lines (minimum 150 satisfied) |
| Six preserve-verbatim sections intact | VERIFIED | "What is this project?", "Key Design Decisions", "Vocabulary Summary", "Relationship to projekt-forge", "Questions To Come Back To" all confirmed present |

**Does this requirement meet its stated success criterion?** YES. DOCS-02 is fully met. CLAUDE.md is a substantially refreshed, accurate ground-truth document for AI assistants resuming context.

---

## Required Artifacts

| Artifact | Provided | Status | Notes |
|----------|---------|--------|-------|
| `pyproject.toml` | `version = "1.4.1"` | VERIFIED | Was `1.3.0` |
| `scripts/install-flame-hook.sh` | Default `v1.4.1` | VERIFIED | Was `v1.1.0` |
| `README.md` | v1.4.1 install section + refreshed Current Status table | VERIFIED | 261 lines |
| `tests/test_public_api.py::test_package_version` | Asserts `1.4.1` | VERIFIED | Was `1.3.0` |
| `tests/test_install_hook_version_consistency.py` | Three-way drift regression guard | VERIFIED | 80 lines, both tests present |
| `CLAUDE.md` | v1.4.1 ground-truth refresh (5 surfaces, subsystems, v1.5 context) | VERIFIED | 238 lines |
| `docs/INSTALL.md` | 8-step operator install guide with multi-host topology framing | PARTIALLY VERIFIED | 374 lines; artifact is substantive and correct in most respects; Step 6 single-process claim is a documented lie (gap #11); Step 3 Postgres setup gaps are structural artist-blockers |
| `.planning/phases/20-reality-audit-canonical-install/20-HUMAN-UAT.md` | Track A author-walk record, 13 gaps, outcome PASS-with-deviations | VERIFIED | status: partial; signed by cnoellert 2026-05-01 |
| `.planning/phases/20-reality-audit-canonical-install/20-PHASE-20.1-CANDIDATE.md` | Phase 20.1 input requirements (install.sh + systemd + env file + INSTALL.md reshape) | VERIFIED | Durable candidate doc, 11795 bytes |

---

## Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `tests/test_install_hook_version_consistency.py` | `scripts/install-flame-hook.sh` | regex extraction of `FORGE_BRIDGE_VERSION:-` default | WIRED |
| `tests/test_install_hook_version_consistency.py` | `README.md` | regex extraction of raw.githubusercontent.com URL version segment | WIRED |
| `tests/test_install_hook_version_consistency.py` | `pyproject.toml` | regex extraction of `version = "..."` field | WIRED |
| `docs/INSTALL.md` | `scripts/install-flame-hook.sh` | documented invocation + matching `v1.4.1` default | WIRED |
| `docs/INSTALL.md` | `alembic.ini` + migrations | `alembic upgrade head` with alembic.ini hardcode caveat documented | WIRED |
| `docs/INSTALL.md` | `forge_bridge/cli/doctor.py` | `forge-bridge console doctor` referenced in Step 8 | WIRED |
| `forge_bridge/mcp/server.py` | `forge_bridge/server/` (WebSocket bus) | AsyncClient CONNECTS to `:9998` — does NOT start it | DOCUMENTED GAP (#11) — INSTALL.md claims single-process boot; reality requires two processes |

---

## Data-Flow Trace (Level 4)

Not applicable for this phase — the deliverables are documentation, version pinning, and a regression test. No dynamic data-rendering components were modified.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| pyproject.toml version is 1.4.1 | `grep '^version = "1.4.1"$' pyproject.toml` | 1 match | PASS |
| install-flame-hook.sh defaults to v1.4.1 | `grep 'FORGE_BRIDGE_VERSION:-v1.4.1' scripts/install-flame-hook.sh` | 1 match | PASS |
| No stale v1.1.0 in script | `grep -c 'v1.1.0' scripts/install-flame-hook.sh` | 0 | PASS |
| No stale v1.2.1 in README | `grep -c 'v1.2.1' README.md` | 0 | PASS |
| No stale v1.3.0 in pyproject | `grep -c 'v1.3.0' pyproject.toml` | 0 | PASS |
| README has v1.4.1 curl URL | `grep -c 'cnoellert/forge-bridge/v1.4.1/scripts' README.md` | 1 | PASS |
| INSTALL.md has v1.4.1 curl URL | `grep -c 'cnoellert/forge-bridge/v1.4.1/scripts' docs/INSTALL.md` | 1 | PASS |
| INSTALL.md line count ≥ 290 | `wc -l docs/INSTALL.md` | 374 | PASS |
| INSTALL.md "one shot" single-process lie | `grep 'all four hosted surfaces in one shot' docs/INSTALL.md` | 1 match (the lie is still present at line 234) | GAP #11 |
| forge_bridge.server is a separate runnable module | `python3 -c "import forge_bridge.server"` | succeeds; server/app.py exists | CONFIRMS two-process requirement |
| MCP server connects to (not starts) ws://127.0.0.1:9998 | `grep 'AsyncClient' forge_bridge/mcp/server.py` | AsyncClient confirmed — CONNECT pattern, not subprocess start | CONFIRMS gap #11 |
| CLAUDE.md five surfaces enumerated | `grep -c ':9996/ui/' CLAUDE.md && grep -c '/api/v1/chat' CLAUDE.md` | 2, 2 | PASS |
| CLAUDE.md stale date purged | `grep -c 'As of 2026-02-24' CLAUDE.md` | 0 | PASS |
| Consistency test file exists | `wc -l tests/test_install_hook_version_consistency.py` | 80 lines | PASS |

---

## Requirements Coverage

| Requirement | Plan(s) | Description | Status | Evidence |
|-------------|---------|-------------|--------|----------|
| INSTALL-01 | 20-04, 20-05, 20-07 | INSTALL.md verified on clean machine | PARTIAL | Artifact exists and is substantive; artist-walk blocked at Step 3 + Step 6; routed to Phase 20.1 |
| INSTALL-02 | 20-01 | install-flame-hook.sh defaults to v1.4.1 | SATISFIED | Script default, README URL, pyproject all at v1.4.1; regression guard in place |
| INSTALL-03 | 20-01, 20-03 | README ↔ INSTALL.md consistency | SATISFIED | Version consistency confirmed; test guard enforces it |
| INSTALL-04 | 20-04, 20-07 | External dep inventory complete before install | SATISFIED | "Before you start" split tables cover all 7 deps; topology subsection added |
| DOCS-02 | 20-02 | CLAUDE.md v1.4.1 ground truth | SATISFIED | All 5 surfaces enumerated; stale framing purged; v1.5 Legibility context present |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/INSTALL.md` | 234 | "boots all four hosted surfaces in one shot" — the WebSocket bus (`forge_bridge.server` on `:9998`) must be started as a separate prior process; `python -m forge_bridge` is a CLIENT of `:9998`, not its launcher | BLOCKER | An operator following Step 6 verbatim gets the two-process start order wrong; the console HTTP surface on `:9996` appears to start but then drops the WS connection with "Could not connect to forge-bridge at ws://127.0.0.1:9998"; the doc provides no recovery path. This is gap #11 from the UAT. |
| `docs/INSTALL.md` | Step 3 (multiple lines) | Postgres setup assumes pg_hba.conf awareness, password_encryption versioning knowledge, and postgresql-setup --initdb — none of which are explained | WARNING | Artist-blocking. A Flame artist without Linux sysadmin background would fail here. Gaps #1, #3, #4, #5, #6 from the UAT all originate here. |

---

## Human Verification Required

None — all automated checks passed or failed definitively. The UAT (20-HUMAN-UAT.md) constitutes the human verification record for this phase.

---

## Deferred Items

Items not yet met but explicitly addressed in Phase 20.1.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | docs/INSTALL.md Step 6 corrected to reflect two-process start order (gap #11) | Phase 20.1 | "Two systemd units… forge-bridge-server.service… forge-bridge.service with Requires=forge-bridge-server.service… Solves gaps 7, 8, 9, 10, 11, 12 in one architectural choice." (20-PHASE-20.1-CANDIDATE.md §Deliverables) |
| 2 | docs/INSTALL.md Step 3 collapsed to install-bootstrap.sh handling Postgres init/pg_hba/migrations | Phase 20.1 | "scripts/install-bootstrap.sh — imperative bootstrap of Postgres… pg_hba.conf auth-method alignment… probe SHOW password_encryption, set pg_hba accordingly" (20-PHASE-20.1-CANDIDATE.md §Deliverables) |
| 3 | Env var persistence (gap #7 — bare export is ephemeral) | Phase 20.1 | "packaging/forge-bridge.env.example — systemd EnvironmentFile=" (20-PHASE-20.1-CANDIDATE.md §Deliverables) |
| 4 | Track B integrator dry-run | Phase 20.1 | 20-HUMAN-UAT.md Action: "Plan 20-06 (Track B dry-run) is subsumed by Phase 20.1's acceptance criteria" |
| 5 | Non-author Flame artist UAT (D-02.1 amendment) | v1.6+ | Seeded as SEED-PHASE-20-NON-AUTHOR-UAT-V1.6+.md per D-02.1 |

---

## Gaps Summary

**One structural gap blocks the phase goal as stated in ROADMAP.md.** The gap is not remediable inside Phase 20 — it requires an `install-bootstrap.sh` script, two systemd units, an env file, and INSTALL.md reshaped to reference the script rather than walk a Postgres setup and two-process launch sequence by hand. These are exactly the deliverables of Phase 20.1, already fully scoped in `20-PHASE-20.1-CANDIDATE.md`.

**What this means:**

- INSTALL-01 and SC-1 are partially met. The artifact exists and is architecturally correct. An experienced operator or the project author (with triage access) can reach all five surfaces by following the doc. A Flame artist cannot.
- INSTALL-02, INSTALL-03, INSTALL-04, and DOCS-02 are fully met.
- The architecture works end-to-end (confirmed by the UAT: chat via cross-host Ollama on assist-01 returned correct responses; all five surfaces were verified via curl and browser).
- The install procedure-as-prose, not the code, is the artifact with gaps.

**Remediation path:** Open Phase 20.1 from `.planning/phases/20-reality-audit-canonical-install/20-PHASE-20.1-CANDIDATE.md`. Do NOT run `/gsd-plan-phase 20 --gaps` — that would attempt to re-plan Phase 20, which is complete and closed. Phase 20.1 is the correct successor decimal phase per CONTEXT.md D-05 and the explicit decision recorded in 20-HUMAN-UAT.md Action section.

**Phase 20.1 primary acceptance criterion (from the candidate doc):**
> A Flame artist with no Linux sysadmin background, no Postgres administration knowledge, and no familiarity with conda, systemd, or the forge-bridge architecture can complete the install end-to-end and reach all 5 surfaces.

---

_Verified: 2026-04-30T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Cross-references: 20-HUMAN-UAT.md, 20-PHASE-20.1-CANDIDATE.md, 20-CONTEXT.md D-02.1 / D-05_
