# A.5.3.2 PR 6 — Close (Gate 1 closed)

**Status:** PR 6 closed at this commit. **Gate 1 closes here.**
Archival framing + continuity definition for the room as it
crosses the Gate 1 → Gate 2 boundary.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs.
- `A.5.3.2-PR3-SPEC.md` — persistence layer.
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift; integration-discipline quartet.
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — chat-handler
  integration contract.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state PR 5 inherited.
- `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`) — surface geometry
  asymmetry.
- `A.5.3.2-PR5-SPEC.md` (commit `42336c3`) — chain-step
  integration contract.
- `A.5.3.2-PR5-CLOSE.md` (commit `b8f522e`) — durable archival
  state PR 6 inherited.
- `A.5.3.2-PR6-FRAMING.md` (commit `2142ab6`) — visual-asymmetry
  executable lint backstop; five binding decisions
  (discovery-based input, Property D visual grammar lock,
  NARROWING_FUNCTION_NAMES maintenance surface, Layer-3-only
  scope, hybrid AST + text validation).
- `A.5.3.2-PR6-SPEC.md` (commit `630e646`) — implementation
  contract; 17 tests, 12-step sequence.
- PR 6 step commits: `a7b0672` → `b423429` (8 commits ending at
  step 9 — lint-self meta-test).

**The threshold PR 6 confirmed:**

> The room continued reviewing "architectural-state preservation
> under integration pressure" — without re-establishing it.

This sentence — first articulated by PR 4 CLOSE §5.8, exercised
by PR 5 — carries through PR 6 unchanged. PR 6 introduced no new
behavior, no new call site, no new architectural commitment. PR 6
mechanically locked in the existing commitments via Layer 3 of
the structural-test discipline.

---

## 1. What PR 6 established

### 1.1 Layer 3 of the structural-test discipline

The forge-bridge structural-test discipline now reads as three
non-redundant, non-overlapping layers:

| Layer | Test | Drift class caught | Question |
|---|---|---|---|
| 1 | `test_pr3_discipline.py` | Topology drift | Which files may import `forge_bridge.corpus`? |
| 2 | `test_pr4_participation_creep.py` | Symbol / import drift | Within those files, which corpus symbols may be imported? |
| 3 | **`test_pr6_visual_asymmetry.py`** | **Semantic-shape drift** | **At those import sites, how must the imported emission path be invoked?** |

PR 6 ships Layer 3. The visual-asymmetry pattern (Gate 1 §5.1)
transitions from a code-review-only check enforced by reviewer
attention into mechanically enforced CI.

The non-overlap discipline is binding: PR 6 owns Layer 3 only.
Cross-module fused-helper drift is caught at Layers 1 + 2; PR 6
does NOT acquire module-graph traversal, dependency-flow
analysis, or cross-file fusion detection responsibilities. The
"Rejection 3" (fused helpers per Gate 1 §5.3) is a named
*consequence* of Properties A-D + Rejections 1, 2, 4 holding —
not a standalone analysis pass.

### 1.2 Four properties + four rejections (with Rejection 3 as consequence)

The lint validates four acceptance properties at every discovered
call site:

- **Property A** — guarded invocation. The call's enclosing
  statement is `if divergence_capture_enabled():` at function-
  scope level.
- **Property B** — single-statement body. The if block contains
  exactly one statement: the emit call.
- **Property C** — keyword-only invocation with `source="runtime"`.
- **Property D** — visual grammar (separator → carrier block →
  guard → emission), with D.1 blank-line lock (0 or 1 permitted),
  D.2 separator placement lock (`# ──` opens the block), D.3
  shape-preserving flexibility vocabulary.

And rejects four named deviations:

- **Rejection 1** — gate inside helper (Property A's converse).
- **Rejection 2** — pre-finalization emission (narrowing call
  appears AFTER emission within the same function).
- **Rejection 3** — fused helpers (consequence of A-D + 1, 2, 4).
- **Rejection 4** — branch-state gating (guard combined with
  branch state via boolean operator).

Each failure carries a `failure_id` that synthetic-source
rejection tests assert against — making the lint mechanically
falsifiable without locking on incidental formatting (line
numbers, exact failure-message text).

### 1.3 The NARROWING_FUNCTION_NAMES maintenance surface

The lint introduces the first explicit *truth-vs-mechanism*
distinction in forge-bridge's structural tests:

```python
NARROWING_FUNCTION_NAMES: frozenset[str] = frozenset({
    "filter_tools_by_message",
    "deterministic_narrow",
})
```

The constant is the **operational mechanism** for identifying
narrowing operations. The **protected property** is the truth:

> No additional narrowing operation may occur downstream of
> finalized arbitration capture.

A future PR renaming `filter_tools_by_message` → (e.g.)
`filter_by_message_intent` without updating this constant would
silently disable Rejection 2 enforcement while leaving the lint
structurally green. The constant's update is part of any
narrowing-rename mergeability contract; reviewers reading a
narrowing-rename PR must verify this set updates synchronously.

The failure-message text for Rejection 2 quotes the protected
property verbatim — NOT the constant's contents. The lint's
failure messages explain *what* the lint protects, not *how* it
detects.

### 1.4 Discovery captures ownership at the discovery surface

`_find_emit_call_sites(tree)` returns
`list[tuple[FunctionDef | AsyncFunctionDef, ast.Call]]`. A
NodeVisitor maintains a function stack; the innermost enclosing
function is captured at the moment each emit call is identified.
Ownership is attached at the discovery surface, not reconstructed
later via downstream parent-walk inference.

This aligns with the PR 4/5 moment-of-authority lineage:
structural truth lives at the discovery point, not in inference
helpers that reconstruct it after the fact. A future spec
drafting that refactors discovery into a hardcoded "known-good
set" of file paths merges the candidate-vs-approved-topology
questions and loses drift visibility — the framing §3.2 binding
choice protects against this.

### 1.5 Hybrid AST + text introspection

The lint uses AST for structural shape (guard, body, keyword
args, narrowing-call detection) and text introspection for the
visual pattern (blank lines, comment-block opener). Pure AST
cannot represent comments + blank lines — Python's AST drops
them. Pure regex is brittle for multi-line structural shape.

The hybrid is justified by a load-bearing distinction the
framing introduced:

> The visual pattern is load-bearing, not decorative.

The erosion mode the lint exists to prevent is **semantic
preservation without visual preservation** — a refactor that
compiles, passes runtime tests, and preserves the executable
behavior of capture emission while collapsing the comment block
or removing the separator. Pure AST validation would permit this
erosion.

### 1.6 Two PR 6 carrier sentences

Two additive carriers travel verbatim into the lint module
docstring + commit message bodies:

> **PR 6 is the structural backstop for the visual-asymmetry
> pattern. The lint validates shape, not content; structure, not
> interpretation. Carrier content is the room's job; field
> validation is the helper signature's job; the lint validates
> the visual asymmetry between arbitration and observation.**

> **The lint operates by observation, not by participation. It
> reads source files; it does not import the corpus package. The
> lint's own scope is the same one-directional observational flow
> the call sites enforce.**

Eleven inherited carriers (7 from PR 4, 4 from PR 5) travel
unchanged alongside these.

### 1.7 17 tests at zero modification cost

PR 6 added 17 new pytest IDs:

- 1 production-tree umbrella test.
- 1 helper-internal check (gate-inside-helper at the helper
  layer).
- 1 lint-self meta-test (no `forge_bridge.corpus` imports).
- 10 synthetic-source rejection tests (one per `failure_id`).
- 2 synthetic-source acceptance tests (D.1 zero-blank-lines +
  D.3 internal section breaks — shape-preserving flexibility).
- 2 real-source regression tests (handlers.py + _step.py
  current shape locked as canonical).

**Zero modifications to existing test files.** Layer 1 + Layer 2
+ no-dependency + integration bundles all unchanged.

Final counts (forge env, Python 3.11):
- **148 corpus tests pass** (131 baseline + 17 new). ✓
- **50 chat-handler tests pass** (50/50 unchanged). ✓

### 1.8 Step 9 — lint-self meta-test correction surfaced at incarnation

PR 5 CLOSE §5.1 named the methodology pattern: "correction cycles
can become proactive." PR 5 surfaced zero corrections at
incarnation; PR 6 surfaced exactly one — the lint-self meta-test
text-grep approach (spec §6.5.3) trips on the lint's OWN string
literals (the `forbidden = ("from forge_bridge.corpus", ...)`
tuple references the literal strings the grep is searching for).

The correction was caught at first run, before commit: switched
to AST walk (`ast.ImportFrom` / `ast.Import` node detection), which
walks past string literals and docstrings and only sees actual
import statements.

This shift mirrors the production lint's hybrid-AST-+-text
discipline: use AST where STRUCTURE matters, text where visual
layout matters. The meta-test cares about IMPORT STRUCTURE (does
an actual `ImportFrom` or `Import` node target
`forge_bridge.corpus`?), not visual layout — so AST is the right
tool.

The methodology observation: spec-drafted text-grep approaches
that work for PRODUCTION code (where the lint reads other files)
do NOT necessarily work for SELF-INSPECTION (where the lint reads
itself). Future structural tests that introspect their own source
should default to AST walk, not text grep, for this reason.

---

## 2. What Gate 2 inherits from PR 6

### 2.1 The 13 carrier sentences

Eleven inherited from PR 4 + PR 5 plus two additive PR 6 carriers
travel into Gate 2 unchanged. Gate 2's seed corpus drive surface
will likely introduce additional carriers (the seed-driven probe
is structurally distinct from the runtime-driven call sites the
lint validates), but PR 6's carriers do not regenerate.

### 2.2 The lint's input set extends automatically

Gate 2 may introduce additional emit call sites (the seed corpus
drive surface, if it lands separate emit invocations rather than
sharing handlers.py / _step.py). PR 6's discovery-based input set
captures these automatically — `_find_emit_call_sites` walks the
tree, so a third or fourth call site is validated against the
canonical pattern without lint modification.

A new call site that does NOT match the canonical pattern fires
the umbrella test with the specific `failure_id` pointing the
operator at exactly which property failed. Routing per spec §8
phase-end conditions: revert OR spec amendment.

### 2.3 The three-layer structural-test discipline

Gate 2 inherits the layered discipline:

- **Layer 1** — file-level allowlist. Gate 2's seed corpus
  surface (if it imports the emission path) will need to be
  added to `test_pr3_discipline.py::_ALLOWLIST`.
- **Layer 2** — import-symbol allowlist. Gate 2 modules that
  import corpus must NOT reach for read/analysis surfaces beyond
  the emission path. The participation-creep grep
  (`_NARROWING_SUBSYSTEM`) extends forward-narrowing per the
  framing's clause.
- **Layer 3** — call-site shape. Gate 2 call sites inherit the
  canonical visual-asymmetry pattern; the lint validates
  automatically.

If Gate 2 introduces a corpus-read module (`comparator`,
`replay_analysis`, `historical_lookup`), all three layers extend
forward-narrowing. PR 6 itself does not extend.

### 2.4 The maintenance-surface discipline

`NARROWING_FUNCTION_NAMES` is the load-bearing example of the
truth-vs-mechanism distinction. Future structural tests that
depend on identifying SPECIFIC named functions in the codebase
should follow the same pattern:

- Define an explicit named constant.
- Document the protected property at the constant's definition
  site, distinct from the constant's contents.
- Lock the constant's update as part of any rename's
  mergeability contract.
- Quote the protected property in failure messages, not the
  constant's contents.

This pattern surfaces explicitly here so Gate 2 + Gate 4 spec
drafting inherits it without re-derivation.

### 2.5 Surface-before-implementation discipline

The PR 3 + PR 4 + PR 5 + PR 6 cadence carries unchanged into
Gate 2:

- Framing artifact (registered, surfaced for review).
- Spec derived from framing (surfaced for review).
- Implementation derived from spec, with cadence-matches-work-
  depth review (light-touch for plumbing, full three-round for
  boundary work).
- Atomic merge.

Gate 2's framing drafts after this commit.

---

## 3. What Gate 2 changes

### 3.1 Seed corpus drive surface

Gate 2 introduces fixture-based seed prompts that drive the
arbitration pipeline with deterministic inputs. The structural
shape differs from runtime call sites (the seed surface knows
what its inputs are; it doesn't have to capture them as
"observed runtime state"). Gate 2 framing will articulate the
structural difference explicitly — Gate 1's framing is binding
for Gate 1 only.

### 3.2 Layer 2 record schema (deferred to Gate 4)

The Layer 2 record schema in code, the comparator implementation,
and the console-script entry are Gate 4 work. Gate 2 ships seed
inputs; Gate 4 ships the comparator that consumes Layer 1 +
Layer 2 records and surfaces divergence.

### 3.3 What does NOT change

- v1 schema continues unchanged.
- The 11 + 2 = 13 carriers travel verbatim.
- The three-layer structural-test discipline carries.
- The four-layer verification vocabulary
  (architectural property / operational expression /
  verification mechanism / bite-verification mutation) carries.
- The cadence-matches-work-depth review rule carries.

---

## 4. Bite-verification observations (operator-driven; step 10)

Per spec §7 step 10, four scratches were applied at production
call sites + reverted. Each scratch confirmed the lint fires the
expected `failure_id` and passes when reverted. **No scratch
landed in main.**

| Scratch | Site | Mutation | Expected fire | Observed fire | Reverted clean? |
|---|---|---|---|---|---|
| 1 | handlers.py:1185 | Removed `if divergence_capture_enabled():` wrapper around emit call | `property_a` | `property_a` ✓ | ✓ |
| 2 | handlers.py:1204 (post-emission) | Added `tools = filter_tools_by_message(tools, last_user_text)` after the canonical block | `rejection_2` | `rejection_2` ✓ | ✓ |
| 3 | handlers.py:117 (module-level) | Defined `_narrow_and_capture` helper containing internal guarded emit (no carrier block above the guard inside the helper) | `property_d_block_missing` (at the helper's emit site, not at chat_handler) | `property_d_block_missing` at line 124 of helper ✓ | ✓ |
| 4 | _step.py:233 | Modified guard to `if divergence_capture_enabled() and len(filtered) == 1:` | `rejection_4` | `rejection_4` ✓ | ✓ |

The umbrella test (`test_visual_asymmetry_at_all_call_sites`)
caught scratch 3 in addition to the focused regression test —
demonstrating that the umbrella's full-tree discovery surfaces
violations regardless of which file the offender lives in. The
failure-message preludes (the two PR 6 carrier sentences) appear
verbatim in the umbrella's CI output, giving operators the
lint's posture before per-call-site failure details.

**Methodology observation:** scratch 3 (fused helper) confirmed
the framing §4.2 Rejection 3 + §5 layering argument empirically.
The lint did NOT need a dedicated co-location detector — the
existing local-shape properties (Property D in particular) fire
naturally on the fused-helper scenario. The fused helper's
emission site has no carrier block above its guard;
property_d_block_missing fires; the operator sees the failure
without the lint owning a "find every function that calls both X
and Y" walk.

---

## 5. Methodology observations surfaced during PR 6

PR 5 CLOSE §5 produced six methodology observations. PR 6
produces fewer (six PRs deep into the gate, the methodology has
stabilized) but four are worth surfacing for promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`.

### 5.1 The truth-vs-mechanism distinction generalizes

PR 6's `NARROWING_FUNCTION_NAMES` is the first explicit
codification of a pattern that has been implicit since PR 3:

> A test that names specific functions/files/strings is asserting
> *that something exists at a name*; the protected property is
> *what that something does*. The two are distinct, and conflating
> them is a silent-erosion vector.

Examples in retrospect:
- `test_pr3_discipline.py::_ALLOWLIST` is the operational
  mechanism; the property is "files outside the allowlist do
  NOT import corpus."
- `test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS`
  is the operational mechanism; the property is "narrowing
  modules import only the emission path."
- `_NARROWING_SUBSYSTEM` is the operational mechanism; the
  property is "the narrowing subsystem does not reach for
  corpus-read surfaces."

PR 6 made this distinction explicit at the comment-block layer
of the constant's definition. Future structural tests should
follow this discipline: name the property in the comment block;
name the mechanism in the constant; lock synchronized updates
on rename.

### 5.2 Hybrid AST + text introspection generalizes

PR 6's hybrid validation pattern (AST for structural shape, text
for visual shape) is a methodology pattern that applies wherever
a test cares about BOTH structural correctness AND visual
correctness. The lint-self meta-test correction at step 9
demonstrated the pattern's reach: when a structural test inspects
its OWN source, AST walk (which sees imports as nodes, not as
strings) is the right tool; text grep would trip on the test's
own string literals.

The generalized pattern: when a test asks "does X structurally
exist?" use AST. When it asks "does X visually exist with the
right shape?" use text introspection. When both — hybrid.

### 5.3 Discovery-based input sets resist forward-narrowing rot

PR 6's `_find_emit_call_sites` discovery walk is more durable
than a hardcoded `_CALL_SITES = (...)` tuple would be. A
discovery-based approach captures the population of candidates
in the tree at every test run; a hardcoded tuple captures it at
spec-drafting time and then drifts.

The framing §3.2 binding choice — discovery, not hardcoded paths
— is a methodology pattern that generalizes:

> When a structural test asks "where does X appear?", prefer
> discovery (walk the tree, find X) over enumeration (list the
> places X is allowed to appear). Discovery surfaces unsanctioned
> instances; enumeration only validates known instances.

The Layer 1 allowlist is enumeration (it lists permitted import
sites). The Layer 3 lint is discovery (it finds wherever the
emission helper is invoked). Both are valid; both serve different
purposes; the framing §3.2 decomposition of the three questions
makes the role of each explicit.

### 5.4 Layer-3-only scope discipline holds under bite-verification

The framing §4.2 Rejection 3 + §5 layering argument was made at
framing time as a forward-looking commitment: PR 6 owns Layer 3
only; cross-module fused-helper drift is caught at Layers 1 + 2.

Bite-verification scratch 3 empirically confirmed this: the
fused-helper scenario fired Property D (a Layer-3 local-shape
check) without the lint needing a cross-file analysis pass. The
framing's commitment was load-bearing AND mechanically supported
by the existing local-shape properties.

The methodology observation: when a framing makes a
non-acquisition commitment ("PR 6 does NOT acquire X"), the
spec must demonstrate that the existing mechanisms cover X.
Bite-verification at the close stage confirms or refutes the
framing's claim. PR 6 confirms.

---

## 6. Gate 1 closure

**Gate 1 sequence status:**

- PR 1 (skeleton + schema + env gate) — shipped `ee019be`.
- PR 2 (topology + identity) — shipped `a33c135`.
- PR 3 (builder + writer + reader) — shipped `a9e3e47`.
- PR 4 (chat-handler integration) — shipped `614750a`.
- PR 5 (chain-step integration) — shipped `0cd915d`.
- **PR 6 (visual-asymmetry executable lint backstop) — shipped at this commit.**

**Gate 1 closes.** The room has shipped:

- A persistence layer (PR 3) — capture builder + writer + reader.
- Two operational call sites (PR 4 + PR 5) — chat-handler +
  chain-step integration under the visual-asymmetry pattern.
- A structural-test discipline at three layers (PR 3 + PR 4 +
  PR 6) that mechanically protects the integration from drift.
- A bounded-asymmetry mechanism (allowlist) that surfaces every
  call-site addition for explicit review.
- A participation-creep grep that prevents corpus-read surfaces
  from leaking into arbitration code paths.
- A four-layer verification vocabulary (architectural property /
  operational expression / verification mechanism / bite-
  verification mutation) that travels through all six PRs.

**The capture corpus is now operational** under
`FORGE_BRIDGE_DIVERGENCE_CAPTURE=1`. Gate 1's deliverable is
shipped; Gate 2 begins at the next session boundary.

---

## 7. Reseed protocol — what the next session does with this artifact

When the Gate 2 framing session opens:

1. **Read this CLOSE artifact first.** It contains the durable
   PR 6 + Gate 1 state Gate 2 inherits. Skipping it means re-
   deriving the three-layer discipline + the truth-vs-mechanism
   pattern from session history rather than from a stable
   archival document.

2. **Read `A.5.3.2-PR6-FRAMING.md` + `A.5.3.2-PR6-SPEC.md`.**
   The Layer-3-only scope discipline (framing §4.2 Rejection 3 +
   §5; spec §8 phase-end conditions) and the discovery-based
   input set (framing §3.2) carry into Gate 2 as binding
   posture.

3. **Draft `A.5.3.2-GATE-2-FRAMING.md`** (or equivalent — Gate 2
   may use a different artifact name). Gate 2's seed corpus
   drive surface is structurally distinct from runtime call
   sites; Gate 2 framing must articulate the difference
   explicitly, including:
   - The seed surface's relationship to the canonical visual-
     asymmetry pattern (does seed code use the same Properties
     A-D shape, or a structurally distinct shape with its own
     Layer-3 lint?).
   - The seed corpus's `source` enum value (PR 3 schema)
     — `source="seed"` vs. `source="runtime"`.
   - The reachability between seed records and runtime records
     in the corpus (do they coexist in the same JSONL? distinct
     directories? distinct schema variants?).

4. **Surface the framing for review** before drafting the spec.

5. **Implement** against the spec per the cadence.

6. **Close Gate 2 with `A.5.3.2-GATE-2-CLOSE.md`** following
   this artifact's structure.

The cadence — framing → spec → step-0 → polish → integration —
carries unchanged.

---

## 8. Cross-references

- `A.5.3.2-PR6-FRAMING.md` (commit `2142ab6`) — five binding
  decisions (discovery-based input set; Property D visual
  grammar; NARROWING_FUNCTION_NAMES maintenance surface; Layer-3-
  only scope; hybrid AST + text validation).
- `A.5.3.2-PR6-SPEC.md` (commit `630e646`) — implementation
  contract; 17 tests; 12-step sequence; failure-message contract.
- `A.5.3.2-PR5-CLOSE.md` (commit `b8f522e`) — durable archival
  state PR 6 inherited; methodology observations from PR 5.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state PR 5 inherited; reviewed for inheritance continuity.
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern
  (binding for Properties A-D acceptance criteria).
- `A.5.3.2-GATE-1-SPEC.md` §5.2 — helper signature.
- `A.5.3.2-GATE-1-SPEC.md` §5.3 — three architecturally-
  prohibited patterns (binding for Rejections 1, 2, 3; PR 5 spec
  §4.1 added Rejection 4).
- `forge_bridge/console/handlers.py:1166-1203` — chat-handler
  integration site (PR 4 step 6); first lint regression input.
- `forge_bridge/console/_step.py:188-247` — chain-step
  integration site (PR 5 step 6); second lint regression input.
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  helper definition; subject to the helper-internal check.
- `tests/corpus/test_pr3_discipline.py` — Layer 1 (file-level
  allowlist).
- `tests/corpus/test_pr4_participation_creep.py` — Layer 2
  (import-symbol allowlist).
- `tests/corpus/test_pr6_visual_asymmetry.py` — **Layer 3
  (call-site shape; PR 6 created this file).**
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion
  candidate for the four §5 methodology observations:
  truth-vs-mechanism distinction (§5.1), hybrid AST + text
  introspection (§5.2), discovery-based input sets (§5.3),
  Layer-3-only scope discipline (§5.4).
- `SEED-PYTHON-3.13-MIGRATION-V1.5+.md` — migration trajectory,
  no longer queued behind Gate 1 (Gate 1 closed; Python 3.13
  migration unblocks at its own scheduling).
- PR 6 step commits (origin/main):
  - `2142ab6` — PR 6 framing registered (NO spec, NO code).
  - `630e646` — PR 6 spec (NO code).
  - `a7b0672` — step 2: lint module skeleton.
  - `8894cad` — step 3: AST + text helpers (full bodies).
  - `ddff67e` — step 4: validation logic.
  - `cbdb98e` — step 5: synthetic-source rejection + acceptance
    tests.
  - `59f1eae` — step 6: real-source regression tests.
  - `991bd22` — step 7: helper-internal check.
  - `d347c8e` — step 8: production-tree umbrella test.
  - `b423429` — step 9: lint-self meta-test (with AST-walk
    correction surfaced at incarnation).

---

PR 6 closes here. **Gate 1 closes here.** Gate 2 begins at the
next session boundary.
