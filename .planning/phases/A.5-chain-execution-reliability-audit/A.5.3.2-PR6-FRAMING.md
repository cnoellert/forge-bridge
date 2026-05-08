# A.5.3.2 PR 6 — Framing (registered, not yet drafted)

**Status:** framing draft surfaced for review during the post-PR-5
reseed pass. **NO spec drafted, NO code written.** This artifact
exists so the spec session opens to the right pressure profile —
and so the implementation-approach commitments (lint discovery
mechanism, AST-vs-text validation level, carrier-content-out-of-
scope discipline) travel into the spec as resolved framing rather
than latent ambiguities surfacing mid-incarnation.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants, eleven explicit exclusions.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs;
  visual-asymmetry pattern (§5.1); architecturally prohibited
  patterns (§5.3).
- `A.5.3.2 PR 1` (commit `ee019be`) — package skeleton.
- `A.5.3.2 PR 2` (commit `a33c135`) — topology + identity.
- `A.5.3.2 PR 3` (commit `a9e3e47`) — capture builder + writer +
  reader; persistence layer ships callable but uncalled.
- `A.5.3.2-PR3-SPEC.md` — orthogonal-truth-surfaces (§5);
  atomic-append (§6.5); discipline grep (§10).
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift; integration-discipline quartet.
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — chat-handler
  integration contract.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state PR 5 inherited; integration-discipline quartet documented.
- `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`) — surface geometry
  asymmetry; three §4.7 open questions resolved.
- `A.5.3.2-PR5-SPEC.md` (commit `42336c3`) — chain-step
  integration contract; helper-duplication binding.
- **`A.5.3.2-PR5-CLOSE.md`** (commit `b8f522e`) — durable archival
  state PR 6 inherits. **Mandatory predecessor read.** §1 lists
  what PR 5 established; §2 lists what PR 6 inherits unchanged;
  §3 lists what changes; §4.7 names that PR 6 has no analogous
  open questions because the lint's scope is mechanically narrow.

This document is **binding framing** for PR 6. The eventual PR 6
spec must derive from it; the implementation must derive from the
spec. Deviations re-open this artifact for explicit re-review, not
absorbed silently into spec drafting.

---

## 0. The opening framing (verbatim — load-bearing)

> **PR 6 is the structural backstop for the visual-asymmetry
> pattern. The lint validates shape, not content; structure, not
> interpretation. Carrier content is the room's job; field
> validation is the helper signature's job; the lint validates the
> visual asymmetry between arbitration and observation.**

> **The lint operates by observation, not by participation. It
> reads source files; it does not import the corpus package. The
> lint's own scope is the same one-directional observational flow
> the call sites enforce.**

These two sentences travel verbatim from this framing into the
eventual PR 6 spec, the lint module's docstring at
`tests/corpus/test_pr6_visual_asymmetry.py`, the lint's failure
messages where applicable, and the PR 6 commit message body. They
are PR 6's additive carrier sentences. They are additive, not
substitutive — the eleven carriers inherited from PR 4 + PR 5
travel unchanged into the lint's documentation alongside these.

PR 6's framing is smaller than PR 4's and smaller than PR 5's.
PR 4 introduced the integration discipline; PR 5 extended it to a
second call site. PR 6 introduces no new behavior, no new call
site, no new schema field, no new architectural commitment. PR 6
mechanically locks in the existing commitments by transitioning a
code-review-only check into an executable test. The risk profile is
narrower than the prior two PRs because the operational surface is
test infrastructure, not production code.

What PR 6 must articulate explicitly is the **lint's scope and
posture** — three implementation-approach decisions (discovery
mechanism, validation level, carrier-content-out-of-scope), the
acceptance/rejection criteria, and the bite-verification
mechanism. Each is named here so the spec inherits a resolved
framing rather than re-deriving the semantics from first principles.

---

## 1. What PR 6 inherits unchanged

CLOSE §2 is the canonical statement; this section is a pointer,
not a re-derivation.

- **Eleven carrier sentences** (CLOSE §2.1) — seven from PR 4 +
  four from PR 5. They travel verbatim into the lint module's
  docstring and the PR 6 commit message body. The lint validates
  the call-site shape that the carriers articulate, so the
  carriers function as the operational *intent* the structural
  shape is enforcing. The lint does NOT validate carrier text
  presence or correctness — that is enforced separately via the
  byte-identical-as-text flattening pipeline (PR 4 step 6).
- **Two operational call sites as the lint's input set** (CLOSE
  §2.2):
  - `forge_bridge/console/handlers.py:1185-1203` (PR 4 step 6).
  - `forge_bridge/console/_step.py:96-152` (PR 5 step 6).
- **Construction infrastructure** (CLOSE §2.3) — `_pr4_helpers.py`
  is closed for extension by PR 6 unless the lint's bite-
  verification scratches require it (they likely do not; a lint
  that reads source files needs no integration helpers).
- **Bounded-asymmetry mechanism — allowlist** (CLOSE §2.4) —
  `test_pr3_discipline.py::_ALLOWLIST` contains both call-site
  files and stays at two entries. **PR 6 does NOT add to this
  list.** The lint is a test-side mechanism, not a production
  code path that imports corpus.
- **Participation-creep grep** (CLOSE §2.5) — exercises both
  `_tool_filter.py` and `_step.py` post-step-6. PR 6 does not
  modify the grep test; the grep test continues to bite at the
  import level while PR 6 extends mechanical enforcement at the
  call-site shape level.
- **Review-mode discipline** (CLOSE §2.6) — full three-round
  review for the lint design + bite-verification scratches; light-
  touch review for surrounding plumbing.
- **Bite-verification expectations** (CLOSE §2.7) — each
  architectural invariant in PR 6 must demonstrate falsifiability
  via surgical scratch + expected-failure framing + revert. For
  the visual-asymmetry lint specifically: scratch a real call
  site (remove the blank line; fold the conditional into the
  helper; collapse the comment block; gate emission on a branch
  state) → expect lint to fire → revert → expect lint to pass.
- **Latency budget posture** (CLOSE §2.8) — 5ms target / 20ms
  ceiling per emission, inherited unchanged. PR 6's lint runs at
  test time, not at runtime, so the budget does not directly
  apply — but the latency-delta tests in both PR 4 and PR 5
  integration bundles exercise the budget continuously, and PR 6
  must not break them.
- **Four-layer verification vocabulary** (PR 5 framing §1) —
  architectural property / operational expression / verification
  mechanism / bite-verification mutation. The lint *is* a
  verification mechanism for the visual-asymmetry architectural
  property; bite-verification mutations apply to it directly.
- **Surface-before-implementation discipline** (PR 4 + PR 5
  framing §6) — framing → spec → implementation, with the
  framing surfacing for review before the spec drafts.

---

## 2. What changes at this surface

PR 6 introduces no new architectural behavior. It introduces a
**verification mechanism** — the lint — that mechanically validates
existing architectural commitments. The "what changes" is
therefore narrow:

### 2.1 The visual-asymmetry pattern transitions from code-review-only to executable

Through PR 5, the §5.1 pattern was enforced by reviewer attention
during three-round review. PR 6 transitions enforcement to
mechanical CI. The pattern itself does not change; the enforcement
discipline does.

**Architectural property (carries unchanged):** *capture is
adjacent to arbitration, never participatory.*

**Operational expression (carries unchanged):** the canonical
shape per Gate 1 §5.1 — blank line + carrier comment block +
explicit `if divergence_capture_enabled():` guard + emission call
with all keyword args + `source="runtime"`.

**Verification mechanism (NEW — what PR 6 ships):** an executable
test that walks the production tree, identifies every call to
`emit_divergence_capture(...)`, and asserts each call site
matches the canonical shape.

**Bite-verification mutation (NEW — what PR 6 demonstrates):**
surgical scratches at production call sites that the lint must
fire on, then revert.

### 2.2 The lint's scope is mechanical, not interpretive

PR 4 framing §1.1 named the deferral rationale: *"PR 4 is still
discovering the stable integration reading shape. Locking visual
structure into executable lint too early risks freezing accidental
formatting rather than codifying intentional structure."*

By PR 6, two operational call sites give the lint the input
diversity it needs to distinguish structural from incidental. The
lint's design must:

- **Accept the canonical pattern** at both existing call sites
  AND any future call site that matches it (forward-narrowing
  per CLOSE §3.1).
- **Reject the three Gate 1 §5.3 prohibited deviations:**
  - Folding the gate inside the helper (`emit_divergence_capture`
    silently no-op'ing when disabled).
  - Pre-finalization emission (capturing partial state mid-
    arbitration before `narrowed`/`filtered` is bound).
  - Fused helpers (`narrow_with_capture(...)`-style fusions of
    arbitration + observation).
- **Reject branch-state-conditional emission** — capture is
  gated on `divergence_capture_enabled()`, NOT on success/failure
  branches (this is the chain-step-specific clarification PR 5
  spec §4.1 named explicitly: capture is arbitration-aware, not
  branch-aware).

The lint must NOT validate:

- **Carrier sentence text content.** Per CLOSE §3.2: "the lint
  must NOT validate carrier content (that's the room's job, not
  the test's). The lint validates structural shape; carrier
  content is validated separately via the byte-identical-as-text
  flattening pipeline."
- **Field count, field names, or field order in the emission
  call.** That is the helper signature's job (Gate 1 §5.2).
  Future schema additions will surface there; the lint should
  not double-encode the schema.
- **Specific indentation widths, blank-line counts beyond "at
  least one", or comment-line widths.** The lint validates
  STRUCTURE — the presence and ordering of named structural
  elements — not formatting widths. Locking widths would freeze
  incidental shape and trip on legitimate refactors.
- **Variable names of the snapshot variables** (`registered_tools`,
  `tools_post_pr14`, etc.). The helper's keyword arg names are
  contractual; the local variable names assigned to those keywords
  are call-site-specific (they differ between handlers.py and
  _step.py — `tools` vs. `filtered`, `last_user_text` vs.
  `step_text`). The lint's structural shape must accommodate this
  variation.

### 2.3 The lint joins the existing two-layer structural-test discipline

The forge-bridge structural-test discipline now reads as three
layers:

| Layer | Test | Drift class caught | Question it answers |
|---|---|---|---|
| 1 — file-level allowlist | `test_pr3_discipline.py` | **Topology drift** | *Which files may import `forge_bridge.corpus`?* |
| 2 — import-symbol allowlist | `test_pr4_participation_creep.py` | **Symbol / import drift** | *Within those files, which corpus symbols may be imported?* |
| 3 — call-site shape | **`test_pr6_visual_asymmetry.py`** (NEW) | **Semantic-shape drift** | *At those import sites, how must the imported emission path be invoked?* |

Each layer protects a distinct property. Layer 1 catches new
files reaching for corpus (topology drift). Layer 2 catches
existing allowlisted files reaching for corpus-read surfaces
beyond the emission path (symbol drift). Layer 3 catches the
canonical visual-asymmetry shape eroding within the allowlisted
file at the call site itself (semantic-shape drift).

**The three layers are non-redundant.** A future PR proposing to
collapse layer 3 into layer 1/2 ("we already check imports, isn't
that enough?") is rejected at the spec layer. Layer 1/2 catch
import-graph drift; layer 3 catches in-function call-site drift.
A fused helper inside `handlers.py` would pass layers 1 + 2 (the
file is on the allowlist; the imports are permitted) and fail
layer 3 (the canonical shape is broken).

**The three layers are also non-overlapping.** PR 6's scope is
**local canonical-shape validation only** — it does NOT acquire
global-coupling-analysis responsibilities. Cross-module fused-
helper drift is caught at Layers 1 + 2 (a fused helper imported
from a non-allowlisted module fires Layer 1; a fused helper
importing forbidden corpus surfaces fires Layer 2). PR 6 owns
**Layer 3 only**. A spec drafting that creeps PR 6 into module-
graph traversal, dependency-flow analysis, or cross-file fusion
detection is overscope; the existing layers already cover those
drifts and adding redundant coverage is itself a participation-
creep risk for the lint.

This methodology observation surfaces explicitly here so the spec
documents the three-layer design AND the non-overlap discipline.

### 2.4 The lint is the room's mechanical memory

PR 4 + PR 5 used reviewer attention to enforce the visual-
asymmetry pattern during three-round review. That enforcement was
load-bearing: the pattern would have eroded under contributor
pressure without it. The lint transfers this enforcement from
human attention to mechanical CI.

**Architectural property:** the room's structural commitments are
preserved across reviewer turnover and time.

**Why this matters:** A reviewer reading PR 4 + PR 5 with full
context recognizes the canonical shape. A reviewer joining the
project six months later, looking at a PR that "tidies up" the
call site, has no inherited context — they see a refactor, not a
discipline violation. The lint is the room's mechanical memory:
the shape is preserved whether or not any individual reviewer
remembers why it matters.

This framing of the lint — as mechanical memory, not as a
formatting check — is load-bearing for the spec's tone. The lint
fires with a failure message that explains *why the shape
matters*, not just *what's wrong with the shape*. Failure messages
quote relevant carrier sentences.

---

## 3. The lint's input set

### 3.1 Current call sites (closed at two)

The lint validates exactly the two operational call sites that
PR 4 + PR 5 shipped:

- `forge_bridge/console/handlers.py:1185-1203` — chat-handler
  integration site.
- `forge_bridge/console/_step.py:96-152` — chain-step integration
  site.

PR 6 does NOT introduce a third call site (CLOSE §3.4: "Not the
introduction of a new call site. Two are sufficient for the
lint's earnability; a third would be Gate 2/4 work").

### 3.2 Discovery mechanism (binding choice — Q1 resolved)

**The lint discovers call sites; it does not hardcode file paths.**

Rationale: hardcoded paths would freeze the lint's input set at
two entries. A future Gate 2/4 call site would require both the
new call site AND a manual lint-input update. The risk: a
contributor adds a third call site, forgets to update the lint's
hardcoded list, and the new site escapes mechanical validation.

Discovery-based input set inverts this: every `emit_divergence_capture(`
call in the production tree IS in the lint's input set, regardless
of its file location. A future call site is automatically
validated; if the new site does not match the canonical shape,
the lint fires.

**Operational expression:** walk `forge_bridge/` (the production
tree, NOT `tests/` or `forge_bridge/corpus/`). Parse each `.py`
file. Identify every `Call(func=Name('emit_divergence_capture'))`
node. For each, validate the surrounding canonical pattern.

**Discovery answers a different question than the allowlist.**
The discovery mechanism finds **candidate call sites** —
locations in the source tree where the emission helper is
*actually called*. It does NOT define **approved topology** —
the set of locations where calls are *permitted to exist*. The
two questions decompose cleanly across the three layers:

- **Layer 1 (allowlist)** — *where may imports exist?* (Approved
  topology.)
- **Layer 3 (discovery)** — *where do calls actually exist?*
  (Observed candidate set.)
- **Layer 3 (shape validation)** — *does each discovered call
  obey the canonical doctrine?* (Per-site verdict.)

A future spec drafting that collapses discovery into a hardcoded
"known-good set" merges these questions and loses drift
visibility — the lint would no longer surface a new call site
that bypasses the canonical pattern; it would only validate
*previously sanctioned* sites. Discovery's value is precisely
that it surfaces unsanctioned sites for validation.

**Why this preserves the §1.3 Gate 1 forward-extension clause:**
When future PRs land additional emission sites (Gate 2 seed
corpus drive, Gate 4 corpus-derived surfaces if any), the lint
inherits validation of those sites without modification. The
allowlist (`test_pr3_discipline.py::_ALLOWLIST`) gets a new entry
per site; the lint's input set grows automatically because
discovery walks the tree.

**Alternative rejected:** hardcoded `_CALL_SITES = ("handlers.py",
"_step.py")` with a forward-extension clause requiring update at
each new call site. Rejected because it duplicates allowlist
maintenance and creates a drift vector.

**Carrier sentence (additive — verbatim into spec + lint module
docstring + commit message):**

> The lint operates by observation, not by participation. It
> reads source files; it does not import the corpus package. The
> lint's own scope is the same one-directional observational flow
> the call sites enforce.

**Architectural protection:** the lint must NOT
`from forge_bridge.corpus import ...`. If it did, it would join
the allowlist and inherit the participation-creep grep's
restrictions. The lint reads source files via `pathlib.Path` +
`ast.parse`; it does not import what it validates.

---

## 4. The lint's scope (acceptance / rejection criteria)

### 4.1 Acceptance: the canonical shape

For each `emit_divergence_capture(...)` call discovered in the
production tree, the lint validates four structural properties:

**Property A — Guarded invocation.** The call's enclosing
statement is `if divergence_capture_enabled():` at the
function-scope level (NOT nested inside another if/loop/try).

**Property B — Single-statement body.** The `if` block's body
contains exactly one statement: the `emit_divergence_capture`
call (with any surrounding pure-comment lines tolerated).

**Property C — Keyword-only invocation with `source="runtime"`.**
Every argument is a keyword argument (no positional); the
`source` keyword is present and equals the literal string
`"runtime"` (matches Gate 1 §5.2 helper signature; PR 3 schema).

**Property D — Adjacent comment block (visual grammar locked).**
The visual grammar at the call site is:

> separator → carrier block → guard → emission

Each arrow denotes immediate adjacency, with bounded blank-line
tolerance at one specific seam. The lint validates the four
elements appear in this order with the specified adjacency
discipline. The lint does NOT validate the comment text content.

**D.1 Blank-line semantics (locked).**

- **0 or 1 blank line** is permitted between the closing line of
  the carrier comment block and the `if divergence_capture_enabled():`
  guard.
- **2 or more blank lines** fail validation.

The protected property is *visual adjacency / asymmetry
preservation*. Locking "exactly one blank line" would elevate
formatting trivia into invariant status; permitting arbitrary
spacing would erode adjacency entirely. The "0 or 1" range
preserves the adjacency semantics while accommodating both the
current sites' use of one blank line AND a future legitimate
refactor that lands the guard immediately after the comment
block (zero blank lines).

**D.2 Separator placement (locked).**

The `# ──` separator MUST be the **opening line** of the
observational comment block. Presence elsewhere in the block (or
nearby in the file) is insufficient.

The separator is not decorative — it visually announces entry
into observational asymmetry space. Allowing the separator to
appear anywhere in or near the block would reduce the doctrine
to "somewhere nearby there exists a separator" instead of
preserving the current visual grammar. The separator's specific
position carries the meaning *"observation begins here, distinct
from arbitration above"*; that meaning evaporates if the
separator can drift within the block.

The lint enforces:

- The first line of the comment block (the line immediately
  above any blank-line gap before the `if` guard) starts with
  `# ──`.
- Subsequent lines of the comment block are pure-comment lines
  (`#` prefix); the `# ──` may appear on subsequent lines as
  internal section breaks (e.g., `── PR 5 specializations ──`)
  without violation, but the *opening* line must carry the
  separator.

**D.3 Shape-preserving vs shape-eroding flexibility (vocabulary).**

The framing distinguishes two flexibility classes:

- **Shape-preserving flexibility** — variation that does not
  alter the visual grammar's meaning. Examples: 0-vs-1 blank
  lines (D.1); presence-or-absence of internal `── PR N
  specializations ──` section breaks within the carrier block;
  variable-name differences across call sites (`tools` vs.
  `filtered`, `last_user_text` vs. `step_text`).
- **Shape-eroding flexibility** — variation that alters or
  obscures the visual grammar. Examples: arbitrary blank-line
  counts (2+); separator appearing mid-block instead of as the
  opening line; the carrier block split into two non-contiguous
  pieces; the guard moved before the comment block.

The lint permits shape-preserving flexibility and rejects shape-
eroding flexibility. This vocabulary travels into the spec so
incarnation-level decisions about what to validate are routed
through the right framing question: *"is this variation shape-
preserving or shape-eroding?"*

These four properties together encode the canonical pattern. They
allow the call-site-specific differences PR 4 vs. PR 5 surface
(different prompt-source variable, different snapshot variable
names, presence/absence of `── PR N specializations ──` internal
section breaks in the carrier block, 0-or-1 blank lines before
the guard) without locking incidental formatting.

### 4.2 Rejection: the three Gate 1 §5.3 prohibited patterns + branch-state gating

The lint rejects four structural deviations:

**Rejection 1 — Gate inside helper.** Any pattern where
`emit_divergence_capture` is called WITHOUT being wrapped in
`if divergence_capture_enabled():`. This catches the silent-
no-op-on-disabled pattern. Implementation: any
`emit_divergence_capture(...)` call whose enclosing statement is
NOT a guarded `if divergence_capture_enabled():` block fires the
lint.

**Rejection 2 — Pre-finalization emission.** Per Gate 1 §5.3:
"capture invocation BEFORE the arbitration decision is finalized
... violates the structural contract — capture is a record OF the
decision, not an observer INSIDE the decision pipeline."

**Protected property (load-bearing — the truth):**

> No additional narrowing operation may occur downstream of
> finalized arbitration capture.

**Mechanism (today's operational expression — NOT the truth):**

The lint enforces the protected property via a *negative*
condition: within the same function as the emission call, no
narrowing function call appears AFTER the `if
divergence_capture_enabled():` block. Narrowing operations are
identified by name match against an explicit maintenance
surface:

```python
NARROWING_FUNCTION_NAMES: frozenset[str] = frozenset({
    "filter_tools_by_message",
    "deterministic_narrow",
})
```

**The maintenance surface is NOT the truth itself.** It is the
current operational expression for *identifying* narrowing
operations. The truth is the protected property above. The
spec must:

- Define `NARROWING_FUNCTION_NAMES` (or equivalent) as an
  explicit named constant in the lint module.
- Document — at the constant's definition site, in the lint
  module docstring, and in the lint's failure messages — that
  the constant IS the operational mechanism, NOT the protected
  property.
- Document explicitly that **renaming or refactoring narrowing
  implementations REQUIRES a synchronized update to
  `NARROWING_FUNCTION_NAMES`**. A future PR that renames
  `filter_tools_by_message` to `filter_by_message_intent` (or
  similar) without updating this constant would silently disable
  the rejection-2 enforcement while leaving the lint
  structurally green. The constant's update is part of the
  rename's mergeability contract.

**Why this distinction is load-bearing:**

A future contributor reading only the constant could conclude
"the rule is: these two function names must not appear after
emission." That is the *mechanism*, not the *property*. The
property is *no narrowing after capture*; the mechanism is
*these names are how we observe narrowing today*. Conflating
the two means the lint becomes vulnerable to silent erosion via
rename — the names drift, the constant doesn't update, the lint
keeps passing while the property is no longer enforced.

The spec's failure-message text for rejection 2 must quote the
**protected property**, not the constant's contents. The
constant is *how* the lint detects; the property is *what* the
lint protects.

**The lint does NOT enforce a strong positive** ("narrowing must
come before"); a strong-positive form would couple the lint to
the specific shape of the arbitration pipeline (which functions
must run in which order). The negative property (*no narrowing
after emission*) is mechanically narrow and resists drift —
provided the maintenance surface stays current.

**Rejection 3 — Fused helpers (Layer 3 scope only).**

Per Gate 1 §5.3: a helper like `narrow_with_capture(tools,
message)` that wraps narrowing and emission in one call.

**Cross-module fused-helper drift is NOT PR 6's responsibility.**
A fused helper imported from a non-allowlisted module fires
Layer 1 (`test_pr3_discipline.py`); a fused helper importing
forbidden corpus surfaces fires Layer 2
(`test_pr4_participation_creep.py`). The existing two-layer
mechanism already covers cross-module fusion drift.

**PR 6 only validates local canonical shape.** Layer 3's
contribution to the fused-helper prohibition is the in-function
shape check: within a single function, the canonical pattern IS
narrowing-then-blank-line-then-comment-block-then-guarded-emission.
Properties A-D and Rejections 1, 2, 4 collectively enforce this
shape; Rejection 3 does NOT introduce *additional* analysis
beyond what those properties already enforce. The named
"Rejection 3" is the *consequence* of Properties A-D + Rejection
2 holding — not a separate analysis pass.

If a contributor lands `narrow_and_capture(tools, message)`
somewhere:

- If the helper lives in a non-allowlisted module → Layer 1
  fires.
- If the helper imports forbidden corpus surfaces → Layer 2
  fires.
- If the helper lives within `handlers.py` or `_step.py` itself
  and the call site invokes it → the call site no longer
  matches Properties A-D (no `if divergence_capture_enabled():`
  guard at the call site; no carrier block) → Rejection 1 +
  Property D fire.

**Spec scope discipline:** PR 6 must NOT acquire module-graph
traversal, dependency-flow analysis, or cross-file fusion
detection responsibilities. The existing layers cover those
drifts; adding redundant coverage in Layer 3 is itself a
participation-creep risk for the lint. If a spec drafting begins
sketching a "find every function that calls both X and Y across
the entire codebase" walk, **stop and re-scope.**

**Rejection 4 — Branch-state gating.** Per PR 5 spec §4.1
arbitration-aware-not-branch-aware: emission is gated on
`divergence_capture_enabled()`, NOT on success/failure branches.
The lint detects this by validating that the `if
divergence_capture_enabled():` block's test expression is
*exactly* a call to `divergence_capture_enabled()`, with no
boolean operator combining it with branch state. Patterns like
`if divergence_capture_enabled() and len(filtered) == 1:` fire
the lint.

### 4.3 Validation level (binding choice — Q2 resolved)

**Hybrid AST + text introspection.**

- **AST validates structural shape:**
  - Locate `Call(func=Name('emit_divergence_capture'))` nodes.
  - Validate the parent statement is `If(test=Call(func=Name('divergence_capture_enabled')))`.
  - Validate the `If.body` is exactly one expression statement.
  - Validate the call's args are all keyword args with `source="runtime"`.
  - Validate negative properties (rejection 2 narrowing-after, rejection 4 boolean-test combination).

- **Text introspection validates the visual pattern:**
  - The line preceding the `if` line has at most one blank line.
  - Before that, a contiguous run of comment lines starting with
    `# ──`.
  - The lint reads `source.splitlines()` to inspect blank lines
    and comment markers; AST cannot represent these because the
    Python AST drops comments and blank lines.

**Why hybrid, not pure AST or pure regex:** AST is precise for
structural shape but blind to visual structure (comments + blank
lines). Regex is precise for visual structure but brittle for
multi-line structural shape. Hybrid uses each for what it does
best.

**The visual pattern is load-bearing, not decorative.** The
visual asymmetry between arbitration and observation is what the
canonical pattern protects; preserving the asymmetry's *executable
semantics* (gate, helper signature, finalized state) without
preserving its *visual shape* (separator, comment block,
adjacency) is the specific erosion mode PR 6 exists to prevent.

Name this erosion mode explicitly:

> **Semantic preservation without visual preservation.**

A future PR could land a refactor that compiles, passes runtime
tests, and preserves the executable behavior of capture emission
— while collapsing the comment block, removing the separator,
fusing the guard into a one-liner, or otherwise erasing the
visual signal that observation is asymmetric to arbitration. Pure
AST validation would permit this erosion: the AST sees the
guarded call structure but cannot see the comment block above
it. The visual signal is what allows future readers to
recognize the call site's *meaning*, not just its mechanics.

The hybrid model exists specifically because preserving
executable semantics alone is insufficient. The lint validates
both layers because *the architectural commitment is both
layers* — call-site behavior AND call-site readability are the
canonical pattern, not one or the other.

**Rejected alternatives:**

- **Pure regex.** Would match nominal patterns but fail under
  legitimate refactors (e.g., line-broken arguments, comment-
  block reformatting). Brittle.
- **Pure AST.** Cannot validate property D (comment block before
  the if). Would force the lint to either skip property D
  (eroding the visual asymmetry) or rebuild a comment-aware AST
  (heavyweight).
- **Third-party tools (libcst, parso).** Would introduce a new
  dependency for one test. Out of scope for v1.5 Legibility (no
  new external libraries per CLAUDE.md). The Python stdlib `ast`
  + `tokenize` modules are sufficient.

**Implementation hint (not binding):** `ast.parse()` for the
structural walk; `tokenize.tokenize()` if comment-token positions
are needed; or simpler `source.splitlines()` line-by-line text
introspection paired with AST line numbers
(`ast.AST.lineno` is well-defined). The simplest sufficient
mechanism wins; spec drafting picks one explicitly.

### 4.4 Helper-internal check (carry-forward — Q4 resolved)

The lint extends to a small co-located check: `emit_divergence_capture`
itself, defined in `forge_bridge/corpus/_capture.py`, must NOT
internally call `divergence_capture_enabled()` to silently no-op.
This is the gate-inside-helper prohibition (Gate 1 §5.3 first
prohibited pattern) at the helper-internal layer.

Implementation: parse `forge_bridge/corpus/_capture.py`; locate
the `emit_divergence_capture` function definition; assert no
`Call(func=Name('divergence_capture_enabled'))` inside its body.

This is a single-file additional check, structurally narrow, and
preserves the gate's location at the call site rather than inside
the helper. Naming it explicitly here so the spec implements it
without re-deriving why.

### 4.5 Stray-header sharpness (deferral assessment at incarnation — Q5)

Per PR 4 framing §4.2 + PR 5 CLOSE §3.3: the reader's
`validate_capture_record` rejection of a stray header appearing
mid-file produces a generic "missing required top-level keys"
WARNING. Sharpening to "stray header mid-file" would improve
operator legibility.

PR 6 may absorb this if the lint design surfaces no friction;
otherwise it routes to v1.5.x patch. **Decision deferred to
incarnation.** The framing's preference: defer unless the lint
incarnation surfaces a natural place to land it (e.g., if the
lint already touches `_reader.py` for some reason). If the lint
stays in `tests/corpus/test_pr6_visual_asymmetry.py` with no
production touch, the stray-header sharpness is not in scope and
routes to v1.5.x patch.

---

## 5. The bite-verification scratches

The lint's falsifiability is demonstrated through surgical
scratches at production call sites + revert. Each rejection
criterion has a corresponding scratch that fires the lint:

| Rejection | Scratch at production call site | Expected lint fire (the actual properties that fail) |
|---|---|---|
| 1 — Gate inside helper | Remove `if divergence_capture_enabled():` wrapper around the `emit_divergence_capture(...)` call at handlers.py:1185 | **Rejection 1 / Property A:** "emit_divergence_capture call is not guarded by `if divergence_capture_enabled():` at handlers.py:1186" |
| 2 — Pre-finalization | Move the entire `if divergence_capture_enabled(): ...` block from handlers.py:1185-1203 to BEFORE line 1134 (`tools = filter_tools_by_message(...)`) | **Rejection 2:** "Protected property violated: no additional narrowing operation may occur downstream of finalized arbitration capture. `filter_tools_by_message` (in NARROWING_FUNCTION_NAMES) called at line N after emission at line M, in handlers.py" |
| 3 — Fused helper | Replace the call-site code at handlers.py:1185-1203 with a call to a new `narrow_and_capture(tools, last_user_text)` helper (defined locally within `handlers.py` so Layer 1 + Layer 2 do not pre-empt the scratch). The fused helper internally contains the narrowing operations and the `if divergence_capture_enabled(): emit_divergence_capture(...)` call. | **The actual properties that fire (NOT a separate co-location check):** Inside the new helper, the `emit_divergence_capture` call is still discovered, but Property D fails (no `# ──`-led carrier comment block immediately above the guard) AND Rejection 1 may fire if the scratch eliminates the guard inside the helper too. At the *original* call site, the entire canonical pattern is now absent (no guard, no comment block, no emission call) — Property D fires there as well via the now-orphaned reading: there is no longer ANY canonical pattern at the call site that motivated the carrier sentences. **Human-readable summary** for the close artifact: *"the canonical local shape is no longer present at handlers.py because narrowing and emission have been fused into a helper" — but this summary is a description of the Rejection 1 + Property D failures, not a separate lint check.* |
| 4 — Branch-state gating | Change `if divergence_capture_enabled():` at _step.py:233 to `if divergence_capture_enabled() and len(filtered) == 1:` | **Rejection 4 / Property A:** "emit_divergence_capture guard's test expression is not exactly `divergence_capture_enabled()` at _step.py:233 — guard combines `divergence_capture_enabled()` with branch state via boolean operator" |

All four scratches must fire the lint when applied; all four must
pass when reverted. This is the falsifiability mechanism.

**Scratch 3 alignment with §4.2 Rejection 3 framing:** the
scratch demonstrates that fused-helper drift IS caught by the
lint without the lint owning a dedicated co-location pass. The
existing local-shape properties (A-D + Rejections 1, 2, 4) fire
naturally on the fused-helper scenario. The bite-verification
table makes this alignment visible: Rejection 3's scratch row
points to *which other properties fire*, not to a "Rejection 3
check" that does not exist as a standalone analysis pass.

If a spec drafting begins introducing a fifth structural check
to "specifically catch fused helpers" — distinct from Properties
A-D + Rejections 1, 2, 4 — that is overscope per §4.2 Rejection
3's Layer-3-only scope discipline. The fused-helper prohibition
is a *named architectural commitment*; the lint's enforcement of
it is a *consequence* of the local-shape checks holding.

**Scratches are surgical and reverted before commit.** The PR 6
implementation log may record bite-verification observations
(commit message body or PR 6 close artifact), but no scratch
lands in main. This mirrors the PR 4 + PR 5 bite-verification
discipline.

---

## 6. The participation-creep grep's invariance to PR 6

The participation-creep grep (`test_pr4_participation_creep.py`)
walks `_NARROWING_SUBSYSTEM` (`_tool_filter.py` + `_step.py`) and
asserts no corpus imports outside `_PERMITTED_CORPUS_IMPORTS`.

**PR 6 does NOT modify this test.** The lint's enforcement is
*shape-level*, not *import-level*. The grep continues to bite at
the import boundary; the lint bites at the call-site boundary.
Both are needed; neither subsumes the other.

If a future PR introduces a corpus-read module
(`forge_bridge.corpus.comparator`, `replay_analysis`,
`historical_lookup`), the grep's `_NARROWING_SUBSYSTEM` extends
forward-narrowing per PR 4 framing §1.3. The lint may or may not
need extension depending on whether the new corpus-read module
introduces new call-site shapes. That assessment is Gate 2/4's
spec problem, not PR 6's.

---

## 7. Surface-before-implementation discipline (carries from PR 3 + PR 4 + PR 5)

The discipline carries through PR 6 unchanged:

1. **This framing artifact** (registered now, this commit, after
   user review).
2. **PR 6 spec** (`A.5.3.2-PR6-SPEC.md`) — drafted from this
   framing in the next session segment. Surfaces for review
   before any code lands.
3. **Implementation** — derived from the spec. Each step
   surfaces for review before staging per the cadence-matches-
   work-depth rule (CLOSE §2.6): light-touch for plumbing
   (helper additions if any, docstring updates); full three-
   round for the lint design itself + the bite-verification
   scratches.
4. **Atomic merge** — PR 6 ships as one coherent landing.
   Implementation pacing may vary; review pacing may vary; merge
   cadence does not. PR 6's mergeability contract: lint module
   + helper-internal check + bite-verification commit message
   notation land together or not at all.

The user's pacing clause from PR 3 + PR 4 + PR 5 still applies:
pausing at structural seams (lint scope, AST validation shape,
bite-verification scratches) is explicitly acceptable. Partial
surfacing is review-only, not mergeable.

---

## 8. What PR 6 is NOT (per CLOSE §3.4 + this framing)

- **Not the introduction of capture into arbitration.** PR 4 was.
  PR 5 was the second call site. PR 6 ships the structural
  backstop for the pattern PR 4 + PR 5 established.
- **Not a third call site.** Two are sufficient for the lint's
  earnability per CLOSE §3.4. A third would be Gate 2/4 work.
- **Not the comparator.** Gate 4.
- **Not a schema bump.** v1 schema continues unchanged. Field
  semantics differences between call sites (PR 5 framing §2.2
  table) are documented at the call sites and validated by the
  helper signature; the lint does not encode field semantics.
- **Not a fifth `capture_state_cycling` state.** Closed for
  extension at the spec layer (PR 5 framing §1).
- **Not a refactoring of either call site.** The lint validates
  what's there; it does not motivate restructuring. If
  incarnation surfaces a place where the canonical pattern would
  read more clearly with a small adjustment, that adjustment is
  out-of-scope and routes to a separate v1.5.x patch.
- **Not a carrier-content validator.** Carrier text presence and
  byte-identicality are validated by the flattening pipeline
  (PR 4 step 6); the lint validates structural shape.
- **Not a field-count or field-name validator.** That is the
  helper signature's job (Gate 1 §5.2). The lint validates only
  `source="runtime"` because that is *structural* (PR 3 schema
  enum), not *content*.
- **Not a test infrastructure refactor.** `_pr4_helpers.py`
  remains untouched unless the lint design surfaces a concrete
  need (it likely does not). The naming question PR 5 spec §6.2
  resolved (extend in place, do not rename) carries unchanged.

---

## 9. Resume protocol

When the next session opens (spec-drafting session):

1. **Read this framing first** before drafting anything. The
   three implementation-approach commitments (discovery-based
   input set §3.2, hybrid AST + text validation §4.3, helper-
   internal check §4.4) are the load-bearing context; skipping
   them is how the lint accidentally collapses scope.
2. **Draft `A.5.3.2-PR6-SPEC.md`** from this framing. The spec
   sequences the implementation across the same nine-step cadence
   inherited from PR 4 + PR 5, adapted to PR 6's narrower scope:
   - Step 0 — schema decision: no bump (recorded for symmetry).
   - Step 1 — polish step (reserved; likely no-op).
   - Step 2 — lint module skeleton (file + docstring + carrier
     sentences inherited verbatim from PR 4 + PR 5).
   - Step 3 — discovery walk (AST traversal of `forge_bridge/`,
     locate emission call sites).
   - Step 4 — acceptance criteria (Properties A-D).
   - Step 5 — rejection criteria (Rejections 1-4).
   - Step 6 — helper-internal check (no gate inside emit
     helper).
   - Step 7 — bite-verification scratches + revert (each
     rejection criterion demonstrated, then reverted).
   - Step 8 — full suite verification.
   - Step 9 — close + reseed for Gate 2.
3. **Surface the spec for review** per the established
   discipline.
4. **Then implement** against the spec.
5. **Commit** with the framing's two opening sentences in the
   commit message body alongside the eleven inherited carriers.

Do not begin drafting the spec without re-reading this framing.
The hybrid AST + text validation choice (§4.3) is the most likely
site of silent drift if the framing is short-circuited — a
spec-drafting session that defaults to "use regex" would break
the framing's binding choice without explicit re-review.

---

## 10. Open questions (for spec or incarnation, not framing)

PR 5 framing inherited three open questions from PR 4 CLOSE §4.7
and resolved them in framing. PR 6 framing inherits zero open
questions from PR 5 CLOSE §4.7 because the lint's scope is
mechanically narrow (CLOSE §4.7: "Input set is fixed (the two
operational call sites). Acceptance criterion is the §5.1
canonical pattern. Rejection criteria are the Gate 1 §5.3
prohibited patterns. Implementation choice (AST walk vs. regex
vs. structural matcher) is an incarnation finding, not a framing
concern.").

This framing resolves the implementation-choice question (Q2:
hybrid AST + text introspection) at framing time rather than
deferring it to incarnation, on the rationale that the framing is
a small structural commitment that benefits from being made
explicit before the spec drafts. The remaining incarnation-time
decisions are mechanical:

- **Q-incarnation-1:** `ast.parse()` only, or paired with
  `tokenize.tokenize()`? The simpler sufficient mechanism wins.
- **Q-incarnation-2:** Stray-header sharpness absorbed (§4.5) or
  routed to v1.5.x? Decided at incarnation per surface friction.
- **Q-incarnation-3:** Lint failure messages quote which carrier
  sentences? The framing's preference is to quote the relevant
  Gate 1 §5.3 prohibition for each rejection criterion plus the
  appropriate PR 5 CLOSE §1 establishing language; specific
  selection is incarnation polish.

If a structural ambiguity surfaces during PR 6 spec drafting,
it surfaces there; for now, no deferred questions exist that
would motivate spec-level deferral.

---

## 11. Cross-references

- `A.5.3.2-PR5-CLOSE.md` (commit `b8f522e`) — durable archival
  state PR 6 inherits. §1 lists what PR 5 established; §2 lists
  what PR 6 inherits unchanged; §3 lists what changes; §4 lists
  queued future work; §4.7 names that PR 6 has no open questions;
  §5 lists the methodology observations from PR 5.
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern
  (binding for the lint's acceptance criteria).
- `A.5.3.2-GATE-1-SPEC.md` §5.2 — helper signature (binding for
  the lint's structural validation; the lint does NOT re-validate
  fields beyond `source="runtime"`).
- `A.5.3.2-GATE-1-SPEC.md` §5.3 — three architecturally-
  prohibited patterns (binding for the lint's rejection
  criteria 1-3; PR 5 spec §4.1 adds rejection 4).
- `A.5.3.2-PR4-FRAMING.md` §1.1 — visual-asymmetry deferral
  rationale ("locking visual structure into executable lint too
  early risks freezing accidental formatting"); the rationale's
  expiry condition (two operational call sites give input
  diversity) is now satisfied.
- `A.5.3.2-PR4-FRAMING.md` §3 — integration-discipline quartet;
  travels into the lint's documentation as inherited posture.
- `A.5.3.2-PR4-SPEC.md` §0 — finalized-state contract; binding
  for the lint's rejection 2 (pre-finalization emission).
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state PR 5 inherited; reviewed for inheritance continuity.
- `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`) — surface geometry
  asymmetry; PR 5's four additive carriers travel into the lint's
  documentation alongside PR 4's seven.
- `A.5.3.2-PR5-SPEC.md` §4.1 — arbitration-aware-not-branch-
  aware framing; binding for the lint's rejection 4.
- `A.5.3.2-PR5-SPEC.md` §6.2 — `_pr4_helpers.py` rename question
  resolved (extend in place, do not rename); carries to PR 6.
- `forge_bridge/console/handlers.py:1166-1203` — chat-handler
  integration site; first lint input.
- `forge_bridge/console/_step.py:188-247` — chain-step integration
  site; second lint input.
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  helper definition; subject to the §4.4 helper-internal check.
- `tests/corpus/test_pr3_discipline.py` — Layer 1 (file-level
  allowlist).
- `tests/corpus/test_pr4_participation_creep.py` — Layer 2
  (import-symbol allowlist).
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3 (call-
  site shape; **PR 6 creates this file**).
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion
  candidate for the three-layer structural-test discipline
  observation in §2.3.
- `SEED-PYTHON-3.13-MIGRATION-V1.5+.md` — migration trajectory,
  queued behind Gate 1.
