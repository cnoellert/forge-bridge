# A.5.3.2 PR 5 — Close

**Status:** PR 5 closed at `0cd915d` (origin/main). Archival framing
+ continuity definition for the room as it crosses the PR 5 → PR 6
boundary.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs.
- `A.5.3.2-PR3-FRAMING.md` + `A.5.3.2-PR3-SPEC.md` — persistence
  layer.
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category shift,
  four risks, integration-discipline quartet.
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — chat-handler integration
  contract.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival state
  PR 5 inherited.
- `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`) — surface geometry
  asymmetry; three §4.7 open questions resolved.
- `A.5.3.2-PR5-SPEC.md` (commit `42336c3`) — chain-step integration
  contract.
- PR 5 step commits: `529ba12` → `0cd915d` (5 commits ending at
  step 7 — chain-step integration tests).

**The threshold PR 5 confirmed:**

> The room continued reviewing "architectural-state preservation
> under integration pressure" — without re-establishing it.

This sentence carries forward as the methodology PR 4 introduced
(CLOSE §5.8) and PR 5 exercised. PR 5 did not need to re-establish
the review mode; it inherited it cleanly. PR 6 inherits the same
posture as inherited posture, not as something to re-articulate.

---

## 1. What PR 5 established

### 1.1 Two operational call sites under the integration discipline

PR 4 introduced the discipline at one call site
(`handlers.py:1185-1203`). PR 5 extended it to a second call site
(`_step.py:96-152`) without re-litigating the contract. Both sites
emit the same ten-field capture record under the same gate, the
same fire-and-forget contract, the same fallback-on-absence
topology.

The bounded-asymmetry that PR 4 introduced (Allowlist mode in
`test_pr3_discipline.py`) now contains exactly two named entries.
The participation-creep grep that PR 4 wrote forward-narrowing now
covers both call-site narrowing surfaces (the test code did not
change in PR 5; the prophetic `_step.py` row in `_NARROWING_SUBSYSTEM`
became exercised post-step-6).

The two sites are intentionally NOT consolidated through shared
helpers. `_ambiguity_state_for` (handlers.py) and
`_ambiguity_state_for_chain_step` (_step.py) are byte-identical in
operational expression. They are deliberately duplicated. The
duplication is the protection against future "harmonization" PRs
that would silently overload field semantics across sites.

### 1.2 Caller-owned deployment identity (validated empirically)

The chain-step's deployment identity is the caller-passed `tools`
parameter. Per-chain-invocation stability (CLOSE §3.1; framing
§2.1) is now empirically confirmed: integration test
`enabled-single_match` asserts both records emitted from a 2-step
chain share the same `registered_tools_snapshot_hash`. Cross-chain
variance is the caller's identity definition, not the chain step's
— a property that holds at the architectural level and is now
testable at the integration level.

A future contributor "improving" `_step.py` by fetching a fresh
`mcp.list_tools()` snapshot at emission time would silently corrupt
this property — and the integration test would fire. The
participation-creep vector dressed as a "completeness improvement"
is now mechanically guarded.

### 1.3 Verbatim-list discipline at rejection paths

Framing §2.2 committed `narrower_decision` to carry the filtered
list verbatim at narrowing finalization, including zero-match
(`[]`), multi-match (`[a, b, …]`), and single-match (`[a]`)
expressions. The integration test bundle's `enabled-multi_match`
parametrization empirically bite-verifies this:

- `narrower_decision == ["forge_alpha_probe", "forge_beta_probe"]`
  on rejection (verbatim, NOT empty, NOT a sentinel).
- `pr20_condition_met == False` (always at this surface).
- `collapse_occurred == False` (rejection paths are distinct from
  the multi-to-single transition).
- `ambiguity_state == "multi_survivor"`.
- `mcp.call_tool` invocation count == 0 (chain aborts at rejection
  envelope before tool execution).

Without this parametrization, the framing §2.2 silent-overload
failure mode would remain a documentation claim. With it, the
property is a tested invariant. The schema-field-semantics table is
now covered by mechanical assertions.

### 1.4 Helper-duplication-as-protection (operationalized)

PR 5 introduced `_ambiguity_state_for_chain_step` deliberately
parallel to `handlers.py::_ambiguity_state_for`. Both helpers
return identical output for identical input; both are
translation-only with the binding constraint inherited from PR 4
spec §4.1.

The duplication is now operational protection against future
consolidation pressure. The PR 5 spec §8 phase-end conditions
explicitly reject "consolidate `_ambiguity_state_for` and
`_ambiguity_state_for_chain_step` into a shared module helper"
at the spec layer. Reviewers reading both files see the visible
parallel structure as an anti-normalization defense, not a
cleanup opportunity.

### 1.5 Visual section separators preserve archaeology

The `── PR 5 specializations ──` section break inside the call-site
carrier comment block (and inside the integration test file's
docstring) is the user's convergence directive operationalized.
A future reader walking downward through the carrier block
experiences:

1. Why the discipline exists (PR 3 §0).
2. What philosophical posture governs it (PR 4 framing §0 risk-
   category; §3 quartet).
3. What integration contract emerged (PR 4 spec §0 finalized-state).
4. **── PR 5 specializations ──**
5. Why this call site differs from the chat handler (PR 5 framing
   §0 + §2.1).
6. What semantic overload is being prevented here specifically
   (PR 5 framing §2.2).
7. What the architectural-property-vs-branch-aware framing
   protects (PR 5 spec §4.1).

The visual separation is for archaeology, not implementation.
Future readers should visually feel "this surface inherits a
doctrine, then specializes it." That is the real semantic shape of
PR 5.

### 1.6 Forward-looking module-deletion in test infrastructure

`test_pr4_no_dependency.py` now deletes `forge_bridge.console._step`
and `forge_bridge.console._engine` from `sys.modules` alongside the
PR 4 handler/app modules. Pre-step-6 these delitems were no-ops;
post-step-6 they make the multi-step parametrization meaningfully
exercise `_step.py`'s Shape A fallback bindings under the corpus-
sentinel patch.

The pattern is: when an integration site lands at one PR but its
test infrastructure is added preemptively at an earlier PR, the
test's module-deletion list grows forward-looking. Reviewers see
the comment "Pre-step-6 these are no-ops" and understand the test
is preparing for the next-step landing without breaking the current
suite.

---

## 2. What PR 6 inherits unchanged

### 2.1 The 11 carrier sentences

Seven inherited from PR 4 (CLOSE §1.5) plus four additive PR 5
carriers (PR 5 framing §0/§2.1/§2.2/§5 + PR 5 spec §4.1's
arbitration-aware-not-branch-aware) travel verbatim into PR 6's
work. PR 6's scope is the visual-asymmetry executable lint backstop
— the lint validates the call-site shape that the carriers
articulate, so the carriers travel into the lint's documentation
and failure messages.

The carriers do not regenerate. PR 6 inherits them verbatim. New
carriers introduced by PR 6 framing (if any) are additive; the
existing eleven do not change.

### 2.2 Two call sites as input for lint design

PR 6 has two operational call sites to draw from:

- `forge_bridge/console/handlers.py:1185-1203` — chat-handler
  integration site (PR 4 step 6).
- `forge_bridge/console/_step.py:96-152` — chain-step integration
  site (PR 5 step 6).

Both sites follow the §5.1 visual-asymmetry pattern with the same
structural shape: blank line + carrier comment block + explicit
`if divergence_capture_enabled():` guard + emission call. The lint
must accept BOTH and reject deviations. The two-site input set is
what makes the lint earnable — a lint with one input would
fossilize incidental formatting; two inputs let PR 6 distinguish
structural choices from incidental ones.

### 2.3 Construction infrastructure

`tests/corpus/_pr4_helpers.py` ships shared PR 4 + PR 5
infrastructure that PR 6 reuses without modification:

- `CaptureState` Literal + `capture_state_cycling` fixture —
  closed for extension; PR 6 must NOT add a fifth state.
- Chat-handler helpers (`_make_test_tool`, `_passthrough_filter`,
  `_stub_chat_result`, `_drive_chat_request`).
- Chain-step helpers (`_drive_chain_request`, `_stub_call_tool`,
  `_stub_resolve_required_params`).
- Assertion helpers for both envelope shapes:
  `_assert_arbitration_invariance`,
  `_assert_chain_step_arbitration_invariance`,
  `_assert_arbitration_response_equivalent`,
  `_assert_chain_step_arbitration_response_equivalent`,
  `_assert_no_failed_write_residue`,
  `_assert_authority_surface_invariance`.

PR 6 does not need to introduce additional construction
infrastructure unless the lint's bite-verification scratches
require it.

### 2.4 Bounded-asymmetry mechanism (allowlist)

`test_pr3_discipline.py::_ALLOWLIST` now contains:

```python
_ALLOWLIST: tuple[str, ...] = (
    "console/handlers.py",
    "console/_step.py",
)
```

PR 6 does NOT add to this list — the visual-asymmetry lint is a
test-side mechanism, not a production code path that imports
corpus. The allowlist's growth is per-call-site, not per-tooling.

### 2.5 Participation-creep grep (now exercising both sites)

`test_pr4_participation_creep.py::_NARROWING_SUBSYSTEM` already
contains `_step.py` (PR 4 wrote it forward-narrowing); the test
now exercises both `_tool_filter.py` and `_step.py` post-step-6.
PR 6 does not need to extend this test unless a Gate 4 corpus-read
module surfaces.

### 2.6 Review-mode discipline

The cadence-matches-work-depth rule from CLOSE §2.4 carries:

- **Light-touch review** for plumbing (allowlist updates, helper
  extensions, fixture reuses, verification-only steps).
- **Full three-round review** for participation-creep boundary
  work (call-site landings, integration test bundles).

For PR 6, the lint design + bite-verification scratches warrant
full review (the lint is the mechanical enforcement of a
participation-creep boundary). Surrounding plumbing (test
infrastructure, helper additions if any) runs light-touch.

### 2.7 Bite-verification expectations

Each architectural invariant in PR 6 must demonstrate
falsifiability via surgical scratch + expected-failure framing +
revert. Specifically for the visual-asymmetry lint: scratch a
real call site (e.g., remove the blank line; fold the conditional
into the helper; collapse the comment block) → expect lint to fire
→ revert → expect lint to pass. PR 5 inherited this discipline
from PR 4; PR 6 inherits it from both.

### 2.8 Latency budget posture

5ms target / 20ms ceiling per emission, inherited unchanged.
PR 6's lint runs at test time, not at runtime, so the budget does
not directly apply — but the latency-delta tests in both PR 4 and
PR 5 integration bundles exercise the budget continuously, and PR 6
must not break them.

---

## 3. What changes in PR 6

### 3.1 The lint becomes executable

Through PR 5, the visual-asymmetry pattern was a code-review-only
check. PR 6 transitions it into an executable test that mechanically
validates the canonical pattern at every present and future call
site.

The lint's input set is the production tree's matches for the
canonical pattern. The current matches:

- `forge_bridge/console/handlers.py:1185-1203` (PR 4).
- `forge_bridge/console/_step.py:96-152` (PR 5).

The lint must accept both. Future call sites (Gate 2 seed corpus
drive, additional integration surfaces) inherit acceptance by
matching the same canonical shape; deviations fire the lint.

### 3.2 The lint is mechanical, not interpretive

PR 4 framing §1.1 named the deferral rationale: "PR 4 is still
discovering the stable integration *reading shape*. Locking visual
structure into executable lint too early risks freezing accidental
formatting rather than codifying intentional structure."

By PR 6, two operational call sites give the lint the input
diversity it needs to distinguish structural from incidental. The
lint's design must:

- Accept the canonical pattern (blank line + carrier block + `if
  divergence_capture_enabled():` guard + emission call).
- Reject deviations that fold capture into a helper call
  (`narrow_with_capture(...)`-style fusions per Gate 1 §5.3).
- Reject deviations that emit before narrowing finalizes.
- Reject deviations that emit conditionally on branch state rather
  than on `divergence_capture_enabled()`.

The lint must NOT validate carrier content (that's the room's job,
not the test's). The lint validates structural shape; carrier
content is validated separately via the byte-identical-as-text
flattening pipeline (PR 4 step 6 introduced this; PR 5 inherited
unchanged).

### 3.3 Stray-header-mid-file warning sharpness (queued from PR 3 UAT)

Per PR 4 framing §4.2 + PR 4 spec §2 out-of-scope: the reader's
`validate_capture_record` rejection of a stray header appearing
mid-file produces a generic "missing required top-level keys"
WARNING. Sharpening to "stray header mid-file" would improve
operator legibility.

PR 6 may absorb this if the lint design surfaces no friction;
otherwise it routes to v1.5.x patch. Decision deferred to PR 6
incarnation per the PR 4 framing's explicit deferral.

### 3.4 What PR 6 is NOT

- **Not the introduction of a new call site.** Two are sufficient
  for the lint's earnability; a third would be Gate 2/4 work.
- **Not the comparator.** Gate 4.
- **Not a schema bump.** v1 schema continues unchanged.
- **Not a fifth `capture_state_cycling` state.** Closed for
  extension at the spec layer.
- **Not a refactoring of either call site.** The lint validates
  what's there; it does not motivate restructuring.

---

## 4. Queued future work

### 4.1 Gate 1 closure — PR 6 only

Gate 1 sequence status:

- PR 1 (skeleton + schema + env gate) — shipped `ee019be`.
- PR 2 (topology + identity) — shipped `a33c135`.
- PR 3 (builder + writer + reader) — shipped `a9e3e47`.
- PR 4 (chat-handler integration) — shipped `614750a`.
- **PR 5 (chain-step integration) — shipped `0cd915d`.**
- **PR 6 (visual-asymmetry executable lint) — pending.**

PR 6 closes Gate 1. Gate 2/3/4 begin after Gate 1 closure.

### 4.2 Gate 2 — Seed corpus drive

Fixture-based seed prompts. Gate 2 spec drafts after Gate 1 closure
(post-PR-6). Gate 2 introduces the seed-driven probe surface,
which is structurally distinct from the runtime-driven call sites
PR 4 + PR 5 + PR 6 cover.

### 4.3 Gate 3 — Operator workstation enablement

Runtime capture enablement on the operator workstation. Out of
Gate 1 scope.

### 4.4 Gate 4 — Comparator + Layer 2 schema

The comparator implementation, Layer 2 record schema in code, and
console-script entry. Gate 4 framing inherits PR 4 + PR 5's
participation-creep grep forward-extension clause: any new corpus
module surfaces (reader is already there; comparator,
replay-analysis, historical lookup, corpus-derived heuristic
surfaces) require the participation-creep grep test to expand
with them.

### 4.5 Stray-header warning sharpness

Deferred from PR 3 UAT. Routing: PR 6 polish (if no friction) or
v1.5.x patch.

### 4.6 Python 3.13 migration

`SEED-PYTHON-3.13-MIGRATION-V1.5+.md` (planted at commit
`fe76578`). External forcing function (Flame 2027); migration is
its own phase. Out-of-scope for Gate 1.

### 4.7 No open architectural questions for PR 6 framing

PR 4 CLOSE §4.7 had three open questions for PR 5 framing to
resolve (all resolved in PR 5 framing). PR 6 has no analogous open
questions because the lint's scope is mechanically narrow:

- Input set is fixed (the two operational call sites).
- Acceptance criterion is the §5.1 canonical pattern.
- Rejection criteria are the Gate 1 §5.3 prohibited patterns.
- Implementation choice (AST walk vs. regex vs. structural matcher)
  is an incarnation finding, not a framing concern.

If a structural ambiguity surfaces during PR 6 framing drafting,
it will surface there; for now, no deferred questions exist.

---

## 5. Methodology observations surfaced during PR 5

These are durable methodology observations the room produced
during PR 5. Smaller set than PR 4's eight observations because
PR 5 inherited most of the methodology rather than producing it.

### 5.1 Correction cycles can become proactive

PR 4 surfaced five spec-review-pass corrections at incarnation
time (CLOSE §5.6: orthogonal-truth-surfaces, pr20 rename,
collapse_occurred tightening, snapshot 2 placement, wrapped-carrier
flattening). PR 5 surfaced **zero** corrections at incarnation
time. The single correction PR 5 produced (the §2.2 zero-match path
correction replacing "multi-survivor list" with "filtered list
verbatim including zero-match") was caught at framing review,
before the spec was drafted.

The pattern: the correction-cycle pattern is becoming proactive
rather than reactive. PR 4's five corrections taught the room to
read framing artifacts with the same semantic-alignment lens that
previously only fired during incarnation. PR 5 framing review
caught the equivalent of a "spec-review-pass correction" before the
spec ever drafted — the equivalent semantic drift was named at the
framing layer.

This is not a guarantee future PRs will be correction-free at
incarnation. It is a methodology observation: the lens is more
proactive, and earlier discovery is cheaper than later discovery.

### 5.2 Spec completeness produces clean incarnation

All six PR 5 integration tests passed on first run with no scratch
adjustments. Step 6's chain-step integration code worked on first
try. No bite-verification mutations needed surgical adjustment.

This is a function of two things:

1. The framing → spec → implementation rhythm gave the spec enough
   detail (field-semantics tables, exact code shapes) that the
   implementation translated mechanically.
2. The construction infrastructure inherited from PR 4 was
   sufficient — the helpers worked first time when applied to the
   chain envelope shape.

The methodology observation: a spec that produces zero incarnation-
time corrections is a spec that did its job. PR 5's spec did. PR 6
inherits the same expectation; if PR 6 incarnation surfaces a
correction-cycle, that's a signal the spec has a gap to close, not
a signal the implementation has a defect.

### 5.3 Helper duplication can be empirically tested

PR 5 spec §4.1 introduced `_ambiguity_state_for_chain_step` as a
deliberate duplication of `_ambiguity_state_for`. The duplication's
protection — preventing silent overload of field semantics across
sites — was previously a code-review claim. PR 5's
`enabled-multi_match` integration test now empirically tests it:
the assertion that `narrower_decision` carries the multi-tool list
verbatim AND `pr20_condition_met` is False AND `collapse_occurred`
is False at the chain-step surface confirms each field's
chain-step-specific semantics independently of the chat-handler
surface.

A future PR consolidating the helpers would land code that compiles
fine, passes existing chat-handler tests, but breaks the chain-
step integration's `enabled-multi_match` field-semantics
assertions. The duplication-as-protection rationale is now
empirically falsifiable.

### 5.4 Visual section separators in carrier blocks

The `── PR 5 specializations ──` separator pattern is a methodology
artifact. It does NOT disrupt the carrier byte-identicality (the
flattening pipeline ignores the separator line). It DOES preserve
the inheritance→specialization shape for future readers.

This pattern generalizes: when a downstream PR specializes an
inherited doctrine, a named visual separator inside the carrier
block makes the inheritance visible. PR 6 may or may not need its
own separator depending on whether it adds carriers (lint design
may not require new carriers; if so, no separator).

### 5.5 Forward-looking test infrastructure pays off

Three instances surfaced in PR 5:

1. PR 4's participation-creep grep wrote `_step.py` into
   `_NARROWING_SUBSYSTEM` forward-narrowing. PR 5 step 3 verified
   the test continues to bite without code change — the prophetic
   write was correct.
2. PR 5's no-dep test extended `_engine.py` + `_step.py` to the
   module-deletion list pre-step-6. Pre-step-6 these were no-ops;
   post-step-6 they made the multi-step parametrization
   meaningfully exercise the Shape A fallback.
3. PR 4's `_PERMITTED_CORPUS_IMPORTS` set already contained the
   emission paths that PR 5 step 6's import block uses. No update
   needed at PR 5.

The methodology observation: forward-looking test infrastructure
that anticipates future PRs is not premature optimization — it is
test discipline. The cost of writing `_step.py` into PR 4's grep
was zero; the value at PR 5 was non-trivial (no test code change,
test continues to bite correctly post-step-6). Reviewers writing
tests should ask "what call sites will this test apply to in
future PRs?" and write the test accordingly.

### 5.6 The `_pr4_helpers.py` rename question, resolved

PR 4 CLOSE §3.5 deferred the question: "rename `_pr4_helpers.py` to
`_pr_helpers.py` or introduce `_pr5_helpers.py`?" PR 5 spec §6.2
resolved: extend `_pr4_helpers.py` in place. Rationale:

- File names encode history, not ownership.
- Renaming creates churn across import sites for zero
  architectural gain.
- A new `_pr5_helpers.py` would fragment shared infrastructure.

The methodology observation: when a question of the form "rename or
split for clarity" arises, the default answer is "neither" unless
there's an architectural cost to keeping the original shape.
Convenience-driven renames produce churn; architecture-driven
renames produce signal.

---

## 6. Reseed protocol — what the next session does with this artifact

When the PR 6 session opens:

1. **Read this CLOSE artifact first.** It contains the durable
   PR 5 state PR 6 inherits. Skipping it means re-deriving the
   two-call-site lint input set from session history rather than
   from a stable archival document.
2. **Read `A.5.3.2-PR5-FRAMING.md` + `A.5.3.2-PR5-SPEC.md`.** The
   schema field semantics (PR 5 framing §2.2) and the helper-
   duplication binding (PR 5 spec §4.1) inform what the lint must
   protect.
3. **Read both call sites:**
   - `forge_bridge/console/handlers.py:1185-1203`.
   - `forge_bridge/console/_step.py:96-152`.
   These are the lint's input set. The lint's acceptance criteria
   derive from what's COMMON across them; the lint's rejection
   criteria derive from Gate 1 §5.3 prohibited patterns.
4. **Draft `A.5.3.2-PR6-FRAMING.md`.** Inherit the eleven carriers,
   the four-layer vocabulary, the cadence-matches-work-depth rule.
   The framing's job is to lock the lint's scope (input set, AST
   walk vs. regex vs. structural matcher, accept/reject criteria)
   before the spec drafts. Surface for review before drafting the
   spec.
5. **Draft `A.5.3.2-PR6-SPEC.md`** from the framing.
6. **Implement PR 6** per the framing → spec → step-by-step
   sequence. The lint's bite-verification scratches at production
   call sites are the load-bearing verification.
7. **Close PR 6 with `A.5.3.2-PR6-CLOSE.md`** following this
   artifact's structure.
8. **Gate 1 closes when PR 6 closes.** Gate 2 framing drafts after
   Gate 1 closure.

The cadence — framing → spec → step-0 → polish → integration —
carries unchanged.

---

## 7. Cross-references

- `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`) — surface geometry
  asymmetry; three §4.7 open questions resolved.
- `A.5.3.2-PR5-SPEC.md` (commit `42336c3`) — chain-step integration
  contract; helper-duplication binding (§4.1); allowlist extension
  (§4.2); participation-creep grep verification (§4.3); five-test
  bundle with §6.1 rejection-path empirical bite-verification.
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift; carriers travel verbatim into PR 5 unchanged.
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — chat-handler
  integration; allowlist mechanism (§4.2); participation-creep
  grep (§4.3); capture-state-cycling fixture (§5).
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state PR 5 inherited; §4.7 questions resolved in PR 5 framing.
- `A.5.3.2-GATE-1-SPEC.md` §4 (the two arbitration call sites,
  both now operational); §5.1 (visual-asymmetry pattern, code-
  review-only through PR 5; PR 6 makes it executable); §5.3
  (architecturally prohibited patterns, both inherited unchanged).
- `forge_bridge/console/handlers.py:1185-1203` — chat-handler
  integration site (PR 4 step 6); first lint input.
- `forge_bridge/console/_step.py:96-152` — chain-step integration
  site (PR 5 step 6); second lint input.
- `tests/corpus/_pr4_helpers.py` — shared PR 4 + PR 5 construction
  infrastructure; used by both PR 4 and PR 5 integration test
  bundles.
- `tests/corpus/test_pr3_discipline.py` — allowlist (now 2
  entries: handlers.py + _step.py).
- `tests/corpus/test_pr4_participation_creep.py` — narrowing
  subsystem grep (`_NARROWING_SUBSYSTEM` contains both
  `_tool_filter.py` and `_step.py`; both now exercising).
- `tests/corpus/test_pr4_no_dependency.py` — parametrized over
  single_step + multi_step_chain (PR 5 step 5).
- `tests/corpus/test_pr4_chat_handler_integration.py` — PR 4's
  five-test integration bundle.
- `tests/corpus/test_pr5_chain_step_integration.py` — PR 5's
  six-pytest-ID integration bundle.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion
  candidate for the methodology observations in §5 above.
- `SEED-PYTHON-3.13-MIGRATION-V1.5+.md` — migration trajectory,
  queued behind Gate 1.
- PR 5 step commits (origin/main):
  - `529ba12` — step 2: allowlist transition
  - `cab4e98` — step 4: helper extension
  - `b3baf71` — step 5: no-dependency check extension
  - `b9faaa2` — step 6: chain-step integration
  - `0cd915d` — step 7: chain-step integration tests

---

PR 5 closes here. PR 6 begins at the next session boundary. Gate 1
closes when PR 6 closes.
