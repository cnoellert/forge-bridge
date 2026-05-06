# A.5 Status: RESUMED (sharpened scope)

**Paused:** 2026-05-06
**Resumed:** 2026-05-06 (same day; A.6 closed environmentally)
**A.6 outcome:** environmental finding, no code change. See `../A.6-daemon-runtime-integrity/A.6-CLOSE.md`.
**A.5.1 disposition:** **closed not-a-bug** — root cause was unreachable cross-host Ollama (`192.168.86.15:11434`), not a code regression in A.4 or elsewhere. The 75-second `LLMToolError` is the OS TCP connect default firing on an unreachable IPv4 host. The daemon's runtime substrate is structurally confirmed correct (`docs/learnings/a4-runtime-integrity-confirmed.md`).

---

## What changed in A.5 scope at resume

### A.5.1 — closed not-a-bug

The original A.5.1 framing was "router health." The router is healthy; its dependency was unreachable. No code fix needed. Operator-side remediation paths are documented in `../A.6-daemon-runtime-integrity/STEP-3-FINDINGS.md` (restore network, repoint env to localhost, or apply the seeded UX timeout fix).

### A.5.2 — proceeds (unchanged)

**Forced-tool wrapper schema contract.** Reproduces statically: `forge_list_staged` requires a `params` field, the forced wrapper passes `{}`, Pydantic rejects. No working LLM path needed to diagnose or verify the fix; the bug surfaces from `/api/v1/exec` as readily as from `/api/v1/chat`. Land first.

**Verification (when fix lands):** Smoke Tests 0 and 2. `final_text` non-empty for Test 2 will require LLM reachability — that's a deferred verification gate, not a blocker for the fix itself.

### A.5.3 — split into A.5.3.1 (proceeds) and A.5.3.2 (deferred)

**A.5.3.1 — semantic mismatch ("list projects" → `forge_list_staged`)** — proceeds.
The `_tool_filter` keyword-matching logic reproduces statically. Inspecting the wrong narrowing decision and validating a fix can be done by stepping through the filter against a known prompt; no LLM round-trip required. Land second.

**Verification:** Smoke Test 3 — re-runs against a working static narrower; outcome (correct tool selected) is observable in the response envelope without ever entering the LLM path because the deterministic narrower runs before the LLM.

**A.5.3.2 — over-eager collapse (multi-intent prompts hijacked by PR20 short-circuit)** — **deferred** until LLM reachability returns.
Rationale: diagnosing the over-eager collapse requires comparing the narrower's choice against what the LLM would do given the same prompt. That comparison's reference is not available against an unreachable LLM. A.5.3.2 will need its own instrumentation when it eventually runs (a small wrapper around `complete_with_tools` to capture the LLM's tool-selection vs. the narrower's, similar in spirit to the A.6 timing probe but at the selection layer).

**Verification:** Smoke Test 4 — requires a working LLM loop to validate that multi-intent prompts are no longer hijacked.

### Vocabulary learnings note — proceeds

Per the original spec, the note is written **at the moment the first narrowing-fix decision is made** (A.5.3.1). The second narrowing-fix entry (A.5.3.2) is appended later when that work runs.

### Codified smoke tests — proceeds with split

The integration tests for Tests 0, 2, 3 land alongside A.5.2 / A.5.3.1.
The integration test for Test 4 (multi-intent) waits with A.5.3.2.
Test 1 / Test 5 codification: recommended to land regardless — they verify "purely conversational, no tool" and "graceful degraded behavior" assertions that are valuable independently of the LLM. Can be marked `@pytest.mark.skipif` on LLM unreachability so CI passes when the daemon's configured LLM endpoint is down.

---

## What is preserved (unchanged from A.5 spec)

- Smoke-test results table (`PHASE-A.5-SPEC.md`).
- Masking-finding analysis (now structurally explained: forced-tool path bypasses lazy allocation; full LLM loop enters it. Both bugs 2 and 3.1 land statically against the unchanged narrower / forced-call wrapper code).
- All invariants (PR31 envelope, truthful chat contract, `__all__=19`, no new deps).
- All out-of-scope items.
- All phase-end conditions, with this addition: **if A.5.3.1's diagnostic surfaces a vocabulary issue larger than a single-keyword fix**, plant additional learnings + seed entries; do not absorb a full vocabulary phase into A.5 (defer to v1.6 per the spec's existing rule).

---

## Resume sequence

1. **A.5.2** — investigate + land forced-tool schema fix; codify Tests 0 + 2.
2. **A.5.3.1** — investigate + land "list projects" semantic-mismatch fix; write vocabulary learnings note (first entry); codify Test 3.
3. **Hold** — A.5.3.2 (over-eager collapse) and Test 4 codification + final smoke pass remain blocked on LLM reachability.
4. When LLM reachability returns: A.5.3.2 instrumentation + diagnosis + fix; Test 4 codification; final smoke pass; A.5 close.

---

## Audit trail

- `A.5.1-ELEVATE.md` — bisect, diff scope, trigger match, recommendation to open A.6.
- `../A.6-daemon-runtime-integrity/PHASE-A.6-SPEC.md` — A.6 spec (status: CLOSED).
- `../A.6-daemon-runtime-integrity/RUNTIME-MAP.md` — runtime lifecycle map (REQUIRED deliverable, preserved).
- `../A.6-daemon-runtime-integrity/STEP-2-FINDINGS.md` — timing-probe data (probe removed at close).
- `../A.6-daemon-runtime-integrity/STEP-3-FINDINGS.md` — environment / reachability evidence.
- `../A.6-daemon-runtime-integrity/A.6-CLOSE.md` — closure document.
- `docs/learnings/a4-runtime-integrity-confirmed.md` — A.4 structural confirmation captured during A.6.
- `.planning/seeds/SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+.md` — UX timeout fix seed.
- `.planning/seeds/SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+.md` — broader preflight audit seed.
