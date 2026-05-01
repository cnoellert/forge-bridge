---
status: pending
phase: 20-reality-audit-canonical-install
source: [20-01-SUMMARY.md, 20-02-SUMMARY.md, 20-03-SUMMARY.md, 20-04-SUMMARY.md, 20-07-SUMMARY.md, 20-CONTEXT.md, 20-RESEARCH.md, docs/INSTALL.md]
started: [non-author fills ISO8601 at walk start]
updated: [non-author fills ISO8601 at walk completion]
track: A
---

# Phase 20 — Track A INSTALL.md Walk-through (Non-Author UAT)

**Date:** [non-author fills]
**Operator:** [non-author name + role / relation to project]
**Operator workstation (the host the non-author walks on):** flame-01 (preferred — cleaner) OR portofino (dev box) — non-author records which one was actually used
**LLM service host (separate; reached over the network):** assist-01 @ `192.168.86.15` — runs Ollama + `qwen2.5-coder:32b`. The non-author does NOT touch this host during the walk; it must be reachable from the operator workstation.
**Branch / HEAD commit:** 854704a6457eba9796b9f84ce8d99b68573d94a4
**INSTALL.md commit:** [same as branch HEAD unless explicitly different]
**FORGE_LOCAL_LLM_URL the operator sets in Step 5:** `http://192.168.86.15:11434/v1`

## Reference versions discovered during walk

| Dependency | Where | Version found |
|------------|-------|---------------|
| Python (after `conda activate forge`) | operator workstation | [non-author fills] |
| conda | operator workstation | [non-author fills] |
| PostgreSQL | operator workstation (local) | [non-author fills — `psql --version`] |
| Flame | operator workstation | [non-author fills if Track A; SKIP if Track B] |
| forge-bridge `__version__` (after Step 2) | operator workstation | [non-author fills — should be 1.4.1] |
| Ollama | LLM service host (assist-01 @ 192.168.86.15) | [author pre-fills before handoff — `curl -s http://192.168.86.15:11434/api/version`] |
| qwen2.5-coder:32b pulled? | LLM service host | [author pre-fills before handoff — yes/no, from `ollama list` on assist-01] |

## Pre-walk setup (author-prepared on each host, ✓ when complete)

**Operator workstation** (flame-01 or portofino — the host the non-author will walk on):

- [ ] Pre-existing `forge` conda env removed (`conda env remove -n forge` if it existed)
- [ ] Postgres daemon running locally on `:5432` (or operator will install it during INSTALL.md Step 3 — record which path applies)
- [ ] Any prior Flame hook removed (`rm -f /opt/Autodesk/shared/python/forge_bridge/scripts/forge_bridge.py` so the install step does real work)
- [ ] Flame is installed and runnable (Track A only)
- [ ] Phase 20 branch checked out at HEAD with Plans 20-01 through 20-04 + 20-07 landed (HEAD `854704a` or descendant)
- [ ] `docs/INSTALL.md` open in a separate window for the non-author to follow
- [ ] Network reachability confirmed from this host: `curl -s http://192.168.86.15:11434/api/version` returns JSON (proves assist-01 is reachable)

**LLM service host** (assist-01 @ 192.168.86.15 — the non-author does NOT touch this; the author pre-verifies before handoff):

- [ ] Ollama daemon running on `:11434`, listening on the network interface (not just localhost) so the operator workstation can reach it
- [ ] `qwen2.5-coder:32b` pulled (`ollama list | grep qwen2.5-coder` on assist-01)
- [ ] Firewall on assist-01 permits inbound `:11434` from the operator workstation's subnet

## Fixture state (recorded by non-author at walk start, on the operator workstation)

What was running on the operator workstation when the walk started:

- **Postgres (local):** [running on :5432 / not running / unsure / will-install-in-Step-3]
- **Flame (local):** [running with v1.4.1 hook installed / running with prior hook / not running / not installed]
- **forge conda env:** [exists from author prep / missing — non-author creates in Step 1]
- **forge-bridge:** [installed in this env? — if yes, NOT a fresh walk; surface this as a deviation]
- **Reachability to assist-01 :11434:** [reachable / unreachable — confirm by `curl -s http://192.168.86.15:11434/api/version` before starting Step 1]

## Walk-through (non-author runs verbatim)

Walk `docs/INSTALL.md` top to bottom. For EACH numbered step, record:
- The exact command pasted (verbatim)
- The observable output (verbatim, OR "as expected" if it matched the doc's prediction)
- Any error, warning, or surprise (verbatim)
- Time elapsed if longer than 10s

### Step 1: Prepare the conda environment
[non-author fills — commands run, output observed, any deviation from doc]

### Step 2: Install forge-bridge
[non-author fills]

### Step 3: Set up Postgres
[non-author fills]

### Step 4: Install the Flame hook (Track A only)
[non-author fills; SKIP if Track B]

### Step 5: Configure environment variables
[non-author fills — IMPORTANT: set `FORGE_LOCAL_LLM_URL="http://192.168.86.15:11434/v1"` so chat + synthesis route to the assist-01 LLM service host. Leaving it at the default `http://localhost:11434/v1` will fail because Ollama is NOT installed on the operator workstation. Record any other env-var values you set or override.]

### Step 6: Start the server
[non-author fills — including time-to-ready]

### Step 7: Verify all five surfaces
[non-author fills the per-surface table below]

### Step 8: Post-install diagnostic
[non-author fills — paste `forge-bridge console doctor` output verbatim in the section below]

## Per-surface reachability outcome

| # | Surface | Smoke command | Result | Notes |
|---|---------|--------------|--------|-------|
| 1 | Flame hook on :9999 | `curl -s http://localhost:9999/status` | [PASS / FAIL / SKIP] | |
| 2 | MCP server CLI | `forge-bridge --help` | [PASS / FAIL] | |
| 3 | Web UI on :9996/ui/ | `curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"` | [PASS / FAIL] | |
| 4 | HTTP /api/v1/chat | `curl -s -X POST http://localhost:9996/api/v1/chat -H "content-type: application/json" -d '{"messages":[{"role":"user","content":"hello"}]}'` | [PASS / FAIL] | |
| 5 | Browser visual check | open http://localhost:9996/ui/ — confirm 5 views render (tools, execs, manifest, health, chat) | [PASS / FAIL] | |

## forge doctor output

```
[non-author pastes `forge-bridge console doctor` output verbatim here]
```

## Gap log

Each gap surfaced during the walk gets a disposition per CONTEXT.md D-04 / D-05 / D-06:
- **doc-only** → patch INSTALL.md inline; re-walk the affected step. Do NOT close the UAT until the patched doc walks clean.
- **code-fix (≤1 plan)** → spin a Phase 20 follow-up plan (20-08, 20-09, ... — note that 20-06 is Track B and 20-07 was the multi-host topology fix). Block the UAT until the code-fix plan lands.
- **code-fix (>1 plan)** → spin a 20.1 decimal phase per D-05. UAT outcome is FAIL until the decimal phase closes.
- **v1.6+ deferred** → log here, plant a seed in `.planning/seeds/`. Do not block the UAT.

| # | Step | Gap description | Disposition | Plan / seed that addressed it |
|---|------|----------------|-------------|-------------------------------|
| [non-author + author fill collaboratively as gaps surface] | | | | |

## Deviations

Anything the non-author did that wasn't strictly verbatim from INSTALL.md, with justification:

1. [non-author + author fill collaboratively]

## Outcome

**Track A result:** [PASS / PASS with deviations / FAIL]

**Reasoning** (non-author writes 2-3 sentences answering: could a first-time user follow this doc without deriving the topology themselves?):

[non-author fills]

## Action

Based on the outcome:
- **PASS** → Phase 20 milestone gate cleared. Proceed to Plan 20-06 (Track B dry-run).
- **PASS with deviations** → review deviations with author; if all are acceptable per the Phase 10.1 / 16.1 / 16.2 PASS-with-deviations precedent, proceed.
- **FAIL** → fix gaps via the disposition rules above; re-walk; do not close Phase 20 until a clean PASS or PASS-with-deviations is recorded.

## Operator sign-off

[non-author name] — [date]
