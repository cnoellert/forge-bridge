# 2026-05-06 — Narrowing vocabulary findings

A `docs/learnings/` note required by the Phase A.5 spec, written **at the
moment the first narrowing-fix decision was made** (A.5.3.1).

This note is a single document covering both narrowing issues surfaced
during A.5 smoke testing. The A.5.3.1 entry is filled in below; the
A.5.3.2 entry is a placeholder until LLM reachability returns and the
second fix is decided.

---

## Issue 1 (A.5.3.1) — Semantic mismatch: "list projects" → wrong tool

### What real usage exposed

On the dev workstation, the Flame HTTP bridge on `127.0.0.1:9999` is not
running (no Flame install). The reachability filter
(`filter_tools_by_reachable_backends`) drops every `flame_*` and most
`forge_*` tool, leaving only the seven in-process staged-ops tools in
`_IN_PROCESS_FORGE_TOOLS`. None of those seven semantically maps to "list
projects" — `forge_list_projects` is Flame-backed and gets pruned.

A user typing `"list projects"` (chat or `/api/v1/exec`) saw the chain
silently execute `forge_list_staged` instead. The response was a list of
staged operations, not projects — a wildly wrong tool, not a runtime
error. The chat surface produced the wrong answer with a confident shape.

### Why "list projects" mapped to `forge_list_staged`

Mechanical trace through the narrower:

1. **`filter_tools_by_message`** (PR14/17/18/19): with only the seven
   in-process tools surviving the reachability filter, the message
   `"list projects"` (normalized tokens `{list, project}`) intersected
   only with `forge_list_staged` and `forge_get_staged` — both via the
   verb `list` (after PR19 maps `get → list`).
2. **`deterministic_narrow` Rule 1** (PR21 max-overlap): both tied at
   overlap 1 (the verb `list`).
3. **Rule 2** (PR21 domain priority `version > project`): didn't fire
   — only `project` was in the message, not the priority pair.
4. **Rule 3** (PR23 raw-token tie-breaker): the user's literal message
   contained `list`, so `forge_list_staged` (whose raw tokens contain
   `list`) won over `forge_get_staged` (whose raw tokens contain `get`).

The narrower returned a single survivor → PR20 short-circuit fired → the
chain executed `forge_list_staged` against an empty argument set.

### Why architecture review didn't reveal this

The narrower was designed against a candidate set assumed to contain the
natural-home tool for any reasonable query. The reachability filter,
which prunes the candidate set BEFORE the narrower sees it, is a
separate concern that runs first. **No subsystem owns the interaction
between the two.** The narrower has no awareness that the candidate
universe may have been pruned out from under it; the reachability
filter has no awareness of which tools are semantically essential to
which user queries.

That gap is structural. As long as the narrower's input is just "this
list of tools" with no signal about whether the list is the full
registry or a degraded subset, the failure mode is invisible at design
time — it only surfaces in deployments where backends are unreachable.

The broader observation: **vocabulary correctness is a function of the
candidate universe, not just keyword weights.** Any keyword-matching
narrower will pick a closest-match when none of the candidates is
correct. The real defect is not "wrong keyword scoring" — it's "no
exit clause for 'no candidate is a real match.'"

### What diagnostic evidence drove the fix

A static reproduction script (no LLM, no daemon) ran the narrower
against two scenarios:

- **Scenario A** (Flame reachable, full registry): `forge_list_projects`
  correctly wins. The narrower is structurally fine.
- **Scenario B** (Flame unreachable, in-process only): `forge_list_staged`
  is selected — the buggy outcome.

The difference made the bug obviously environmental rather than a
keyword-weight defect. The `forge_list_projects` candidate isn't being
mis-ranked — it's being **pruned out of the universe entirely** before
the narrower runs.

This shifted the fix from "tune keyword weights" to "add an exit clause
for the no-real-match case." The actual change is small: when Rule 1's
normalized overlap consists entirely of verb tokens (today: just `list`),
skip Rule 3's raw-token tie-breaker. The narrower returns >1 survivor;
the chat handler falls back to the LLM, and the chain executor
(`/api/v1/exec`) emits a structured `tool_selection_ambiguous` error.

### Fix landed

- `forge_bridge/console/_tool_filter.py` — adds `_VERB_TOKENS = frozenset({"list"})`
  and a Rule-3 guard that skips the raw-token tie-breaker when all
  survivors' overlaps are verb-only.
- `tests/test_a5_3_1_narrowing_semantic_mismatch_regression.py` —
  codifies Smoke Test 3 in both Flame-reachable and Flame-unreachable
  scenarios, plus a chain-step integration test asserting
  `tool_selection_ambiguous` is the user-facing recovery path.
- Discipline pin: a regression test asserts `_VERB_TOKENS` stays in
  sync with `NORMALIZATION_MAP`'s verb cluster, so a future
  `add/new/make → create` cluster gets caught at PR-review time.

### Follow-ups (NOT this fix, NOT this phase)

- The reachability filter and the narrower remain decoupled. A future
  phase should consider whether the narrower should be told "the
  candidate set has been pruned" — the symmetric fix on the producer
  side. Out of scope for A.5.3.1; capture as a v1.6 vocabulary-phase
  concern if it recurs.
- A "no semantic match" surface in the chat UI (rather than relying on
  the LLM to explain conversationally) would let the operator see
  "the tool you're asking for is unreachable" without needing the LLM
  loop. Out of scope; potential SEED-NO-SEMANTIC-MATCH-UI-V1.6+ if
  the operator UAT surfaces it.

---

## Issue 2 (A.5.3.2) — Over-eager collapse on multi-intent prompts

### Status: DEFERRED until LLM reachability returns

The over-eager collapse cannot be diagnosed in isolation. The narrower's
choice has to be compared against what the LLM would have picked given
the same prompt and tool list, and that comparison's reference is not
available against an unreachable LLM. With localhost Ollama now wired
in (`/etc/forge-bridge/forge-bridge.env` switched to
`http://localhost:11434/v1`), the comparison becomes possible — but
A.5.3.2 was deferred per the A.5 STATUS.md sharpened-scope decision.

This entry will be written when A.5.3.2 lands, following the same
shape as the A.5.3.1 entry above (what real usage exposed; why the
collapse was wrong; why architecture review didn't reveal it; what
diagnostic evidence drove the fix; what landed).

### Anticipated diagnostic structure (preview)

A small wrapper around `complete_with_tools` to capture both signals
side-by-side will likely be the right instrument:

- the narrower's tool selection (deterministic, observable now)
- the LLM's tool selection given the unfiltered candidate list
  (model-dependent, observable when LLM is up)

When the two diverge on a multi-intent prompt, the narrower is
over-collapsing. The instrument is similar in spirit to the A.6 timing
probe but at the selection layer rather than the timing layer.

---

## Methodological note

Both narrowing issues share a common shape: **the narrower's failure
modes are only visible at the seam between subsystems, not inside any
one subsystem.** A.5.3.1 is the seam between reachability filter and
narrower. A.5.3.2 (anticipated) is the seam between narrower and LLM.
Future reliability work in this layer should plan the diagnostic at the
seam, not at the component.
