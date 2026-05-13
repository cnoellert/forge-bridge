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

### What real usage exposed

Once localhost Ollama was wired in (`/etc/forge-bridge/forge-bridge.env`
pointing at `http://localhost:11434/v1`), the question A.5.3.2 had been
deferred for became answerable: did the narrower's confident
single-tool selection actually agree with what the LLM would have
selected, given the unfiltered candidate set?

Testing with real prompts showed three shapes of divergence:

- **Most prompts.** The narrower and the LLM agreed. The deterministic
  confidence gate was doing its job. This is the population that
  matters — most of the time, the narrower is right.
- **Some prompts.** They diverged in shape rather than magnitude. The
  narrower picked tool A; the LLM picked tools A and B (a multi-step
  plan). The narrower hadn't picked a "wrong" tool — it had collapsed
  a multi-intent prompt into single-intent execution. The user got
  something useful, but less than they asked for.
- **A few prompts.** The narrower confidently picked one tool, and the
  LLM declined to use tools at all (it answered the prompt
  conversationally). On those, the narrower was about to execute a
  tool the user never wanted. This is the strongest hijacking shape,
  even though it's rare.

No single prompt was definitively wrong. The pattern was distributional.

### Why this was harder than Issue 1

Issue 1 (A.5.3.1) was tractable: one prompt, one wrong tool, four
rules to trace through, one verb-guard fix. Issue 2 wasn't.

The narrower wasn't catastrophically broken — it was right most of
the time and wrong-but-recoverable some of the time. There was no
single rule to flip or single tool to deprioritize. The defect — to
the extent there was one — lived in the **shape of divergence between
two arbitration paths**, not in either path alone.

You can't fix that with a code change to the narrower. You can only
fix it by first measuring it.

### Why architecture review didn't reveal this

The Methodological note below applies fully here: the narrower's
failure modes are visible only at the seam between subsystems, not
inside any one. Issue 1 was the seam between the reachability filter
and the narrower. Issue 2 is the seam between the narrower and the
LLM.

Architecture review can verify that the narrower stays deterministic
and the LLM stays a planner. That separation is clean. What review
can't verify is what happens at their seam under distributional
pressure — what fraction of prompts collapse confidently when they
shouldn't, what fraction escalate when they could have collapsed
correctly, what fraction land in territory where neither path is
clearly right.

That information lives in the prompts themselves, run against both
arbitration paths, with each divergence classified. Architecture
review doesn't have that data. Only running real prompts through both
paths does.

### What diagnostic evidence drove the work

A.5.3.2 turned out to need a comparison instrument, not a code change.
The instrument captures both signals side-by-side for every prompt:
the narrower's tool selection (deterministic) and the LLM's tool
selection (model-dependent, observable now that the LLM is up).

The instrument lives at test time, not at runtime. Production prompts
are not side-channeled through the LLM for comparison — that would be
the wrong cost shape. The instrument is the diagnostic substrate: a
structured corpus of (prompt, narrower selection, LLM selection,
classification) tuples that future Layer 2 work can extend, query,
and run regressions against.

Building this substrate surfaced what the original framing had
anticipated: **most divergences fall into a small number of
operationally distinct shapes**. The classification taxonomy:

- `SAME_TOOL` — narrower and LLM agree; deterministic wins; PR20 is
  doing its job.
- `DIFFERENT_TOOL` — both pick a tool, but different ones; the
  canonical hijacking case.
- `MULTI_TOOL` — LLM picks a multi-step plan; narrower collapses to
  one step; over-eager collapse case.
- `LLM_DECLINED` — LLM answers conversationally; narrower would have
  hijacked; the strongest hijacking signal.
- `AMBIGUOUS` — none of the above can be cleanly determined. The
  bucket exists so we don't shoehorn records into categories that
  don't fit; forcing a fit would corrupt the analysis.

The classification was the unlock. Once divergences have shapes, you
can ask "is the narrower mostly correct?" with an actual answer.

It was. Across the divergence corpus the substrate exercises, the
narrower turned out to be operationally well-behaved. Specific cases
got addressed inline as they surfaced; no narrower rewrite was needed.

### What landed

The substrate, not a single fix:

- **Comparison instrument contract** —
  `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-INSTRUMENT-CONTRACT.md`
  defines what the instrument captures, with an explicit exclusions
  section so diagnostic scope doesn't grow by accretion.
- **Divergence corpus + fixture substrate** — 17 active fixture
  carriers exercise the comparator under three divergence vectors
  (cardinality, ordering, multi-survivor cardinality); 220 forge env
  tests collect against the corpus + instrument substrate.
- **Boundary discipline preserved** — the narrower is still a
  deterministic confidence gate; the LLM is still a planner. No
  heuristics were added that blur the line. The original phase
  framing's anti-pattern list ("just one more heuristic," "implicit
  confidence floors," "conversational interpretation in the narrower")
  stayed binding throughout.
- **`forge_bridge.__all__` preserved at 19 symbols** across six PRs
  without modification. The substrate did its job without leaking
  pressure into the public API.

Any future work that touches arbitration between deterministic and
planner paths inherits this instrument as the diagnostic surface. New
divergence shapes get added to the corpus rather than discovered in
production.

The phase-arc archaeology — gates, PRs, methodology evolution — lives
in `.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-PHASE-CLOSE.md`
for anyone wanting the internal detail of how this work was
structured. This entry is the operator-readable view.

### Follow-ups (NOT this phase)

- **Layer 2 ↔ Layer 3 seam questions.** Four open ontological
  questions about how arbitration interacts with user-facing surfaces
  (foundry, Ask, schematic). These belong to whichever future phase
  first touches a Layer 3 surface; trying to answer them here would
  be premature.
- **Candidate methodologies awaiting a third corroboration.** Two
  patterns observed across two PRs each (parallel-not-regenerative
  fixture handling; direction selection rationale at
  direction-symmetric pressure). Both wait for a third independent
  instance in future work before promoting to named methodologies.
  Preserved as candidates, not as latent pressure to manufacture
  corroboration.
- **PR 12 — the unfilled numbered slot.** A conditional
  helper-extraction question that the phase preserved as numbered but
  didn't deliver. Numerical pressure (the threshold for the
  abstraction) was met; qualitative pressure ("preserving the
  decomposition becomes harder than abstracting it") never surfaced
  across four PRs of opportunity. Under that absence, deferral is the
  honest disposition. Re-evaluable at a future gate if qualitative
  pressure surfaces.

These aren't open issues. They're **deferred candidates preserved as
governance acts** — the project's way of saying "we considered this,
we didn't have enough evidence to land it, and we don't want to
manufacture evidence to land it prematurely."

---

## Methodological note

Both narrowing issues share a common shape: **the narrower's failure
modes are only visible at the seam between subsystems, not inside any
one subsystem.** A.5.3.1 is the seam between reachability filter and
narrower. A.5.3.2 (anticipated) is the seam between narrower and LLM.
Future reliability work in this layer should plan the diagnostic at the
seam, not at the component.
