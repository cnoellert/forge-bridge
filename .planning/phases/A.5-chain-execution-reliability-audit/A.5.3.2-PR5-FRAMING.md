# A.5.3.2 PR 5 — Framing (registered, not yet drafted)

**Status:** framing draft surfaced for review during the post-PR-4
writer's-room reseed pass. **NO spec drafted, NO code written.**
This artifact exists so the spec session opens to the right pressure
profile — and so the three §4.7 open questions inherited from PR 4
travel into the spec as resolved commitments, not as latent
ambiguities that surface mid-implementation.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants, eleven explicit exclusions.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs;
  call-site visual-asymmetry pattern (§5.1); architecturally
  prohibited patterns (§5.3).
- `A.5.3.2 PR 1` (commit `ee019be`) — package skeleton.
- `A.5.3.2 PR 2` (commit `a33c135`) — topology + identity.
- `A.5.3.2 PR 3` (commit `a9e3e47`) — capture builder + writer +
  reader; persistence layer ships callable but uncalled.
- `A.5.3.2-PR3-SPEC.md` — orthogonal-truth-surfaces (§5),
  atomic-append discipline (§6.5), corruption locality (§9), the
  six verbatim carrier sentences.
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift, four risks, integration-discipline quartet.
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — implementation
  contract for chat-handler integration.
- **`A.5.3.2-PR4-CLOSE.md`** (commit `fab26cb`) — durable archival
  state PR 5 inherits. **Mandatory predecessor read.** §1 lists
  what PR 4 established; §2 lists what PR 5 inherits unchanged;
  §3 lists what changes; §4.7 lists the three open questions this
  framing resolves.

This document is **binding framing** for PR 5. The eventual PR 5
spec must derive from it; the implementation must derive from the
spec. Deviations re-open this artifact for explicit re-review, not
absorbed silently into spec drafting.

---

## 0. The opening framing (verbatim — load-bearing)

> **PR 5 is the second call site under the integration discipline
> PR 4 established. The risk profile is inherited; the surface
> geometry is not.**

> **The chain-step's deployment identity is the caller's view,
> not the global daemon registry view.**

These two sentences travel verbatim from this framing into the
eventual PR 5 spec, the chain-step integration site's adjacent
comment block at `forge_bridge/console/_step.py::
execute_chain_step`, and the PR 5 commit message body. They are
the durable carriers of architectural intent specific to PR 5.

The seven PR 4 carrier sentences (CLOSE §1.5) travel verbatim
unchanged. They document the introduction event — the controlled
introduction of observational side-effects into live arbitration
surfaces, the risk-category shift, the integration-discipline
quartet, and the finalized-state contract. PR 5 inherits all
seven; it does not re-introduce them.

PR 5's framing is therefore smaller than PR 4's. The risk-category
shift was load-bearing context for PR 4; for PR 5 it is inherited
posture. What PR 5 must articulate explicitly is the **surface
geometry difference** — the chain-step site is structurally
different from the chat-handler site in three ways, and each
difference forces a distinct architectural commitment.

---

## 1. What PR 5 inherits unchanged

CLOSE §2 is the canonical statement; this section is a pointer,
not a re-derivation.

- **Observational adjacency discipline** (CLOSE §1.1) — capture
  is adjacent to arbitration, never participatory.
- **Visual-asymmetry pattern** (Gate 1 §5.1; PR 4 framing §1.1) —
  carries verbatim into the chain-step adjacent comment block.
- **Arbitration-invariance under all four capture states**
  (PR 4 framing §1.2; PR 4 CLOSE §1.3) — the four hostile-
  environment probes (`disabled / enabled / failing / recovering`)
  apply at the chain-step surface unchanged. The
  `capture_state_cycling` fixture in `tests/corpus/_pr4_helpers.py`
  is reused without modification. **The fixture is closed for
  extension.** PR 5 must NOT add a fifth state.
- **No-dependency invariant** (PR 4 framing §1.4) — arbitration
  must not depend on capture infrastructure. Strongest form:
  arbitration runs without corpus, so the dependency is
  structurally absent.
- **Integration-discipline quartet** (PR 4 framing §3) — verbatim
  into PR 5's call-site adjacent comment block:
  - The call site is the source of the three explicit inputs.
  - The integration layer passes truth.
  - The integration layer never reconstructs truth.
  - The builder does not discover runtime state.
- **Shape A topology** (CLOSE §3.4 → option (a) committed) —
  re-import the corpus emission helpers at `_step.py` module load
  with the same guarded `try/except ImportError` shape used in
  `handlers.py`. Symmetric topology, identical fallback semantics.
  The duplicate WARNING-on-load (one per call-site module) is an
  O(1) cost per process lifetime, not O(N) per emission.
- **Seven verbatim carrier sentences** (CLOSE §1.5) — travel
  byte-identical-as-text into the chain-step adjacent comment
  block, the PR 5 spec, and the commit message body. They are not
  paraphrased, not condensed, not reframed. The wrapped-carrier
  flattening pipeline (`sed -E 's/^[[:space:]]*#[[:space:]]?//' |
  tr '\n' ' ' | tr -s ' ' | grep -F`) verifies presence under
  comment-line wrapping.
- **Four-layer verification vocabulary** (CLOSE §2.3) —
  architectural property / operational expression / verification
  mechanism / bite-verification mutation. Reviewers reading the
  PR 5 spec should expect each invariant to name the layer
  explicitly.
- **Review-mode discipline** (CLOSE §2.4) — light-touch for
  plumbing (allowlist update, fixture reuse, helper extension);
  full three-round review for the chain-step call site itself
  (step 6) and the integration test bundle (step 7).
- **Bite-verification expectations** (CLOSE §2.5) — each
  invariant demonstrates falsifiability via surgical scratch +
  expected-failure framing + revert. Scratch design lives at
  incarnation, not topology.
- **Construction infrastructure** (CLOSE §2.6) — `_make_test_tool`,
  `_passthrough_filter`, `_stub_chat_result`, the
  `capture_state_cycling` fixture, the four step-7 assertion
  helpers. Reused without modification.

---

## 2. What changes at this surface

Three structural differences from PR 4 force distinct
architectural commitments. Each is named explicitly here so the
spec inherits a resolved framing rather than re-deriving the
semantics from CLOSE §3.

### 2.1 Caller-owned deployment identity

**The chain-step's `tools` parameter is caller-owned.** It is
**not** freshly fetched from `mcp.list_tools()` at this surface.
The chat handler holds the global daemon registry view; the
chain-step site sees only what the chat handler chose to thread
through.

**Architectural commitment (Q1 resolved):**

The inbound `tools` parameter IS this surface's deployment
identity. Name it explicitly in the spec; surface it explicitly
in the call-site adjacent comment block. The hash field
`registered_tools_snapshot_hash` is computed from `tools` —
exactly as the chat handler computes it from `registered_tools`,
because at the chain-step site, `tools` and `registered_tools` are
the same authoritative producer surface.

**Stability invariant (PR 3 §5 generalization):**

The PR 3 §5 deployment-identity stability invariant holds at the
**per-chain-invocation level**. `run_chain_steps` passes the same
`tools` list to every step in a single chain; therefore every
capture record emitted within one chain shares the same
`registered_tools_snapshot_hash`. Cross-chain variance — different
chain invocations seeing different `tools` lists — is the
**caller's** identity definition, not the chain step's. This
distinction is real and load-bearing; conflating it would push
chain-step records into a fingerprint-instability story that
isn't actually there.

**Carrier sentence (additive — verbatim into spec + call-site
comment + commit message):**

> The chain-step's deployment identity is the caller's view,
> not the global daemon registry view.

**Failure mode if violated:**

A future contributor who "improves" the chain-step capture by
fetching a fresh `mcp.list_tools()` snapshot at emission time
would silently corrupt the deployment identity — the snapshot
would no longer reflect the caller's truth, and records would
drift from the arbitration's actual input. This is a
participation-creep vector dressed as a "completeness improvement."

**Architectural protection:**

- `_step.py` imports nothing from `forge_bridge.mcp` for
  registry-discovery purposes. The participation-creep grep at
  `tests/corpus/test_pr4_participation_creep.py` (extended in
  step 3) protects this structurally.
- The call-site adjacent comment block names this explicitly so
  future contributors reading the call site understand the
  authoritative source.

### 2.2 Ambiguity-rejection capture-correctness

**At this surface, ambiguity is a failure mode.** The chat
handler's narrowing path falls through to LLM disambiguation when
`tools_filtered_count > 1`; the chain-step path returns a
`tool_selection_ambiguous` error envelope when `len(filtered) != 1`.

The architectural question (CLOSE §4.7 Q2) is whether capture
fires on the rejection path.

**Architectural commitment (Q2 resolved):**

**Yes, capture fires on ambiguity rejection.** The rejection IS
the arbitration outcome — Layer 1 must record it. Capture happens
ONCE, at the narrowing-finalization boundary, BEFORE the
success/failure branch. The same emission call, the same fields,
the same fire-and-forget contract.

**Surface guard precision:** `_step.py` line 89 reads
`if len(filtered) != 1`. That guard rejects on **two distinct
paths** — zero-match (`len == 0`) and multi-match
(`len > 1`) — both routed to the `tool_selection_ambiguous`
error envelope. The architectural property is therefore not
"preserve the multi-survivor interpretation" but rather
**"`narrower_decision` carries the filtered list verbatim at the
narrowing boundary."** Treating the rejection branch as
implicitly multi-survivor would silently suppress zero-match
truth.

**Schema field semantics at this surface (additive — locked in
this framing, binding for the spec):**

| Field | Chat-handler semantics | Chain-step semantics |
|---|---|---|
| `narrower_decision` | Final tool list passed to the LLM (post-PR21) | **Filtered list verbatim at narrowing finalization.** Three operational expressions: `[]` on zero-match rejection, `[a, b, …]` on multi-match rejection, `[a]` on single-match success. No empty-list suppression, no sentinel, no semantic overloading of the list itself — the arbitration outcome expresses rejection; the list expresses the actual narrowing result |
| `pr20_condition_met` | True iff narrowing collapsed to 1 from a larger reachable set (PR20 short-circuit fired) | **Always False at this surface** — there is no LLM fall-through path here, so the PR20 short-circuit semantics do not apply |
| `collapse_occurred` | True iff `tools_filtered_count == 1 and len(tools_post_pr14) > 1` (multi-to-single transition) | True iff narrowing collapsed multi-to-single on the success path; **False on all rejection paths** (zero-match-to-error and multi-match-to-error are both distinct from the multi-to-single transition `collapse_occurred` records) |
| `ambiguity_state` | `_ambiguity_state_for(tools_filtered_count)` | `_ambiguity_state_for(len(filtered))` — same translation helper, applied at `_step.py`'s narrowing boundary. Translation produces `zero_survivor` / `single_survivor` / `multi_survivor` per PR 4 spec §4.1 (deterministic, one-line, no inferential logic) |

**Why these semantics differ load-bearingly:**

These fields measure **what arbitration did at this surface**, not
arbitration in general. Chat-handler arbitration has a fall-through
path (LLM disambiguation); chain-step arbitration does not. The
PR20 short-circuit is a chat-handler concept that does not exist at
the chain-step site. The zero-match-to-error and multi-match-to-
error transitions are chain-step concepts that do not exist at the
chat-handler site.

**Silent overload is the failure mode this framing names
explicitly:** a future contributor reading both call sites and
"harmonizing" the field semantics by treating `pr20_condition_met`
as "did narrowing succeed deterministically" (with chain-step
ambiguity-rejection setting it to True on the success path), or
collapsing the zero-match and multi-match rejection branches into
a single "rejected" interpretation that drops `narrower_decision`'s
verbatim-list discipline, would collapse the cross-site
distinction. The capture corpus would silently lose the ability to
distinguish "chat-handler PR20 short-circuit fired" from
"chain-step narrowed deterministically," or to distinguish
zero-match-rejected from multi-match-rejected. That is not a
feature; that is participation-creep on the schema-semantics axis.

**Carrier sentence (additive — verbatim into spec + call-site
comment + commit message):**

> Ambiguity rejection is an arbitration outcome. Capture must
> record it. At this surface, `narrower_decision` carries the
> filtered list verbatim at narrowing finalization — including
> zero-match and multi-match rejection paths.
> `pr20_condition_met` is always False and `collapse_occurred`
> is False on all rejection paths. These semantics differ from
> the chat-handler case and must not be silently overloaded.

**Architectural protection:**

- The call-site adjacent comment block names the field semantics
  explicitly. Future readers see the difference at the call site,
  not from spec archaeology.
- The integration test bundle (PR 5 step 7) asserts the field
  values at both narrowing outcomes (success and ambiguity-
  rejection). Bite-verification mutations target the silent-
  overload regression directly.
- The orthogonal-truth-surfaces discipline (PR 3 §5) extends to
  field-semantics surfaces. The chat-handler and chain-step views
  of `pr20_condition_met` are orthogonal authority surfaces; they
  must not be conflated by helper extraction or schema-validation
  shortcuts.

### 2.3 Latency budget posture

**Q3 resolved:** PR 5 inherits PR 4's `<5ms target / <20ms ceiling`
unchanged.

The capture work is structurally identical at both surfaces — one
syscall per emission, one `json.dumps`, no LLM calls, no network.
Chain steps run at higher cadence than single chat requests, but
each individual capture's per-emission cost is the same. CLOSE
§4.7's default holds.

**Architectural commitment:**

If empirical data during incarnation surfaces a real conflict —
e.g., the chain-step capture-state-cycling probe reproducibly
exceeds the 5ms target — the response is to investigate, not to
loosen the threshold. PR 5 remains observational integration, not
persistence-budget engineering.

The latency-budget posture for chain steps is identical to the
chat-handler's. Naming it explicitly here so the spec doesn't have
to re-derive the routing.

---

## 3. The discipline-grep test extends by exactly one allowlist entry

PR 4 transitioned `test_zero_production_imports_outside_corpus`
from literal asymmetry ("zero imports") to bounded asymmetry
("zero imports outside the named allowlist"). The initial allowlist
was a single entry: `console/handlers.py`.

**PR 5 adds exactly one entry: `console/_step.py`.**

The allowlist contract from PR 4 framing §2 carries unchanged:

- The test continues to walk the production tree.
- Files matching the allowlist are permitted to import
  `forge_bridge.corpus`.
- Files not on the allowlist still produce zero imports.
- The allowlist is explicit and reviewable; growth requires spec
  amendment.
- Allowlisted files are still subject to §1.3 of PR 4 framing's
  prohibition: imports may include the emission path
  (`_capture` / `divergence_capture_enabled` /
  `emit_divergence_capture`) but **must not** include reader,
  comparator, or replay-analysis surfaces. The allowlist relaxes
  "does this file import `forge_bridge.corpus` at all"; it does
  not relax "what is this file allowed to use the corpus for."

**Same paths to "make the test pass" remain rejected** (mocking,
test removal, test inversion). The mechanical visibility of
bounded asymmetry is the durable property; eroding it via test
manipulation collapses the protection.

**Forward extension clause carries:** Gate 4 modules (reader,
comparator, replay-analysis helpers, historical lookup helpers,
corpus-derived heuristic surfaces) inherit the responsibility to
extend the allowlist contract — but at that point, the per-file
allowlist itself becomes the wrong granularity, and the contract
will need to evolve to per-file × per-import-target. That
evolution is Gate 4's spec problem, not PR 5's.

---

## 4. The participation-creep grep test extends to the chain-step surface

PR 4 step 3 introduced
`tests/corpus/test_pr4_participation_creep.py` as the mechanical
guard for §1.3 of PR 4 framing — the narrowing subsystem
(`forge_bridge.console._tool_filter` and the chat-handler's
narrowing path) imports zero modules from `forge_bridge.corpus`
except `_capture` / `divergence_capture_enabled` /
`emit_divergence_capture`.

**PR 5 step 3 extends the test to cover the chain-step surface.**

The protected property remains **one-directional observational
flow**, not "don't import this one specific module." The test's
invariant generalizes naturally:

> The narrowing subsystem (now: `_tool_filter.py`,
> `console/handlers.py` chat-narrowing path, **and**
> `console/_step.py` chain-step-narrowing path) imports zero
> modules from `forge_bridge.corpus` except the legitimate
> emission path.

Forward extension (PR 4 framing §1.3) inherits — when corpus-read
modules land (`reader` already exists; `comparator`,
replay-analysis helpers, etc. land later), the participation-creep
test must expand with them.

**Why this test exists at the integration boundary, not just at
import-graph review:**

A future contributor "improving" chain-step error handling by
reading prior corpus records — "let's enrich the
`tool_selection_ambiguous` envelope with historically-similar
prompts" — would cross the participation boundary while staying
within the allowlist contract (the file is allowed to import
`forge_bridge.corpus`). The participation-creep grep is the
backstop: even within the allowlist, the file may not reach for
read/analysis surfaces.

---

## 5. The no-dependency assertion — measured coverage required

PR 4 step 5 introduced
`tests/corpus/test_pr4_no_dependency.py` — the strongest form of
the no-dependency invariant: arbitration runs successfully with
the entire `forge_bridge.corpus` package structurally absent.

**The PR 4 step 6 lesson applies directly here:** verification
mechanisms must validate the protected semantic property itself,
not a nearby approximation. Saying "the existing test covers the
chain path because the chat handler delegates to `_execute_chain`"
is **inferred truth**, not **measured truth** — and inferred truth
is exactly the failure mode the four-layer verification vocabulary
(CLOSE §2.3) exists to prevent.

**Empirical state (verified at framing time):**

The existing probe drives the chat request with prompt `"hi"`.
The chat handler's `parse_chain` returns a 1-element list for
that input; the multi-step branch (`if len(chain_steps) > 1:
return await _execute_chain(...)`) is not taken. Control flow
returns through the LLM-router path in `handlers.py`. **The
chain-step call site at `_step.py::execute_chain_step` is not
reached.** The chain path is therefore not currently measured
under corpus absence.

**Architectural commitment (Q3-revision-acceptable paths,
preference-ordered):**

PR 5's no-dependency coverage of the chain-step surface MUST be
**measured**, not inferred. Two acceptable paths; the spec commits
to one explicitly:

1. **Preferred — extend the existing probe.** Parametrize
   `test_arbitration_completes_when_corpus_unavailable` over
   `[single_step_prompt, multi_step_chain_prompt]`. The
   single-step prompt remains `"hi"` (existing coverage
   unchanged); the multi-step prompt is a `parse_chain`-
   recognizable input (e.g., `"list projects -> list shots"`)
   that drives `_execute_chain → run_chain_steps →
   execute_chain_step` end-to-end. Both must complete
   successfully under the corpus-sentinel. This path keeps the
   no-dependency invariant in a single test surface; one
   sentinel-aliasing mechanism, two measured call-site
   coverages.
2. **Fallback — add a chain-step-specific no-dependency
   assertion.** A sibling test file
   (`tests/corpus/test_pr5_no_dependency.py` or equivalent)
   that drives the multi-step chain path under the same corpus
   sentinel mechanism. Acceptable only if path (1) surfaces a
   concrete obstruction during incarnation that resists in-test
   resolution (e.g., chain-execution wiring imposes a fixture
   shape the existing test cannot accommodate without
   architectural distortion).

**Path (1) preference rationale:**

A single no-dependency test surface composing both call-site
paths under one sentinel mechanism is structurally simpler than
two parallel files. The protected property — *arbitration runs
without corpus, period* — is one property; expressing it as one
parametrized test reads as one invariant. Splitting it across
two files invites future readers to wonder whether the two
checks protect different properties (they don't).

Path (2) exists as an explicit escape valve so the spec can
commit to path (1) without locking incarnation into a corner if
the parametrization surfaces concrete friction. The framing's
preference order is binding; the choice itself is an incarnation
finding documented in the PR 5 close artifact.

**What does NOT carry forward:**

The original framing draft's claim that "no new no-dependency
assertion is needed because PR 4 step 5's mechanism covers the
chain path" is rejected. The mechanism covers the chat-handler's
single-step path; coverage of the chain-step path is an
incremental measurement responsibility PR 5 owns explicitly.

**Carrier sentence (additive — verbatim into spec + commit
message; not into the call-site comment block, where it would
duplicate the §2 carriers):**

> No-dependency coverage at the chain-step surface must be
> measured, not inferred. The existing probe drives only the
> chat-handler single-step path; PR 5 owns the responsibility
> to extend coverage to the chain-step path empirically.

The integration-test bundle (PR 5 step 7) includes a chain-
step-specific arbitration-invariance probe across all four
capture states — but that is the §1.2 invariance check, not the
§1.4 no-dependency check. The two protect different properties
and remain separately enforced regardless of which path (1) or
(2) the spec selects.

---

## 6. Surface-before-implementation discipline (carries from PR 3 + PR 4)

The PR 3 + PR 4 surface-before-implementation discipline carries
through PR 5 unchanged:

1. **This framing artifact** (registered now, this commit, after
   user review).
2. **PR 5 spec** (`A.5.3.2-PR5-SPEC.md`) — drafted from this
   framing in the next session segment. Surfaces for review
   before any code lands.
3. **Implementation** — derived from the spec. Each step
   surfaces for review before staging per the cadence-matches-
   work-depth rule (CLOSE §2.4): light-touch for plumbing
   (steps 0/2/3/4/5), full three-round for boundary work
   (steps 6/7).
4. **Atomic merge** — PR 5 ships as one coherent integration
   landing. Implementation pacing may vary; review pacing may
   vary; merge cadence does not.

The user's pacing clause from PR 3 + PR 4 still applies: pausing
at structural seams (call-site shape, schema field semantics,
test fixtures) is explicitly acceptable. Partial surfacing is
review-only, not mergeable. PR 5's mergeability contract:
chain-step call site + allowlist update + participation-creep
grep extension + integration tests land together or not at all.

---

## 7. What PR 5 is NOT

- **Not the introduction of capture into arbitration.** PR 4 was.
  PR 5 is the second call site under the integration discipline
  PR 4 established. The risk-category shift, the four risks, the
  integration-discipline quartet — all inherited unchanged.
- **Not a fifth capture state.** The
  `capture_state_cycling` fixture is closed for extension at the
  spec layer. PR 5 must not add `permission_denied`,
  `partial_write`, `disk_full`, or any other state. Spec
  amendment is the only path.
- **Not a schema bump.** The `pr20_fired → pr20_condition_met`
  rename in PR 4 step 0 was a v1-correction caught before any
  production corpus existed. PR 5 ships chain-step records under
  the same v1 schema; the field-semantics distinction (§2.2) is
  documented at the call sites, not encoded as a schema variant.
- **Not the visual-asymmetry lint.** PR 6's job. PR 4 ships call
  site #1; PR 5 ships call site #2 — together they give PR 6
  enough operational reading exposure to crystallize the lint.
- **Not the seed corpus drive.** Gate 2.
- **Not the comparator.** Gate 4.
- **Not feature work.** PR 5 ships the integration that turns on
  Layer 1 capture at the chain-step site in production.
  Operator-visible behavior change: none, until
  `FORGE_BRIDGE_DIVERGENCE_CAPTURE=1` is set.

---

## 8. Resume protocol

When the next session opens (spec-drafting session):

1. **Read this framing first** before drafting anything. The
   three §4.7 resolutions (Q1 caller-owned identity, Q2 ambiguity
   capture-correctness, Q3 latency posture unchanged) are the
   load-bearing context; skipping them is how the chain-step
   integration accidentally collapses field semantics across the
   two call sites.
2. **Draft `A.5.3.2-PR5-SPEC.md`** from this framing. The spec
   sequences the implementation across the nine-step cadence
   inherited from PR 4 (schema-decision step 0; allowlist
   transition step 2; participation-creep grep extension step 3;
   helper extension step 4; no-dependency check inheritance step
   5; chain-step integration step 6; integration tests step 7;
   full suite verification step 8; close + reseed step 9). Step 1
   in PR 4 was the cold-vs-warm topology docstring polish; PR 5
   step 1 is reserved for any analogous polish surfaced during
   spec drafting and may be a no-op if none surface.
3. **Surface the spec for review** per the established discipline.
4. **Then implement** against the spec.
5. **Commit** with the framing's two opening sentences in the
   commit message body.

Do not begin drafting the spec without re-reading this framing.
The schema field semantics (§2.2) are the most likely site of
silent drift if the framing is short-circuited.

---

## 9. Cross-references

- `A.5.3.2-PR4-CLOSE.md` — durable archival; §2 inheritance,
  §3 surface differences, §4.7 open questions resolved here.
- `A.5.3.2-PR4-FRAMING.md` §1.2 — arbitration-invariance
  invariant; carries to PR 5 unchanged.
- `A.5.3.2-PR4-FRAMING.md` §1.4 — no-dependency invariant;
  carries to PR 5 unchanged.
- `A.5.3.2-PR4-FRAMING.md` §3 — integration-discipline quartet;
  verbatim into PR 5 call-site comment block.
- `A.5.3.2-PR4-SPEC.md` §4.1 — `_ambiguity_state_for` translation
  helper constraint (deterministic, one-line, free of inferential
  logic). Reused at the chain-step surface.
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern.
- `A.5.3.2-GATE-1-SPEC.md` §5.3 — three architecturally-prohibited
  patterns at the capture call sites.
- `A.5.3.2-PR3-SPEC.md` §5 — orthogonal truth surfaces;
  generalizes to field-semantics surfaces in PR 5 §2.2.
- `A.5.3.2-PR3-SPEC.md` §10 — discipline-grep mechanism;
  allowlist extension in PR 5 §3.
- `forge_bridge/console/_step.py::execute_chain_step` (lines
  52-147) — the PR 5 surface.
- `forge_bridge/console/_engine.py::run_chain_steps` — the
  caller; passes the same `tools` list to every step in a chain.
- `forge_bridge/console/handlers.py::_execute_chain` — the
  chain-entry surface; passes its post-reachability `tools` to
  `run_chain_steps`.
- `tests/corpus/_pr4_helpers.py` — shared fixture and assertion
  helpers; reused without modification.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` § 2.3 —
  property-preservation discipline; the §0 + §2.1 + §2.2
  carrier sentences are instances.
