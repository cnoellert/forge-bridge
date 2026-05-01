---
status: pending
phase: 20-reality-audit-canonical-install
source: [20-01-SUMMARY.md, 20-02-SUMMARY.md, 20-03-SUMMARY.md, 20-04-SUMMARY.md, 20-CONTEXT.md, 20-RESEARCH.md, docs/INSTALL.md]
started: [non-author fills ISO8601 at walk start]
updated: [non-author fills ISO8601 at walk completion]
track: A
---

# Phase 20 — Track A INSTALL.md Walk-through (Non-Author UAT)

**Date:** [non-author fills]
**Operator:** [non-author name + role / relation to project]
**Host:** assist-01 (Flame + Postgres + Ollama pre-installed; fresh conda env `forge` created for this walk)
**Branch / HEAD commit:** 1a3d1eacf85959f33563eae8055fcfadd24a4911
**INSTALL.md commit:** [same as branch HEAD unless explicitly different]

## Reference versions discovered during walk

| Dependency | Version found |
|------------|--------------|
| Python (after `conda activate forge`) | [non-author fills] |
| conda | [non-author fills] |
| PostgreSQL | [non-author fills — `psql --version`] |
| Ollama | [non-author fills — `ollama --version`] |
| qwen2.5-coder:32b pulled? | [non-author fills — yes/no, from `ollama list`] |
| Flame | [non-author fills if Track A; SKIP if Track B] |
| forge-bridge `__version__` (after Step 2) | [non-author fills — should be 1.4.1] |

## Pre-walk setup (author-prepared, ✓ when complete)

- [ ] Pre-existing `forge` conda env removed (`conda env remove -n forge` if it existed)
- [ ] Postgres daemon verified running on `localhost:5432`
- [ ] Ollama daemon verified running on `localhost:11434`
- [ ] `qwen2.5-coder:32b` verified pulled (`ollama list | grep qwen2.5-coder`)
- [ ] Any prior Flame hook removed (`rm -f /opt/Autodesk/shared/python/forge_bridge/scripts/forge_bridge.py` so the install step does real work)
- [ ] Phase 20 branch checked out at HEAD with Plans 20-01 through 20-04 landed
- [ ] `docs/INSTALL.md` open in a separate window for the non-author to follow

## Fixture state (recorded by non-author at walk start)

What was running on the box when the walk started, and what wasn't:

- **Postgres:** [running on :5432 / not running / unsure]
- **Ollama:** [running on :11434 / not running / unsure]
- **Flame:** [running with v1.4.1 hook installed / running with prior hook / not running]
- **forge conda env:** [exists from author prep / missing — non-author creates in Step 1]
- **forge-bridge:** [installed in this env? — if yes, NOT a fresh walk; surface this as a deviation]

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
[non-author fills]

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
- **code-fix (≤1 plan)** → spin a Phase 20 follow-up plan (20-06, 20-07, ...). Block the UAT until the code-fix plan lands.
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
