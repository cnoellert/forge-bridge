# A.5.3.2 PR 4 — Close

**Status:** PR 4 closed at `614750a` (origin/main). Archival framing
+ continuity definition for the room as it crosses the PR 4 → PR 5
boundary.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs.
- `A.5.3.2-PR3-FRAMING.md` + `A.5.3.2-PR3-SPEC.md` — persistence
  layer (writer + reader + atomic-append discipline).
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift, four risks, integration-discipline quartet.
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — implementation
  contract.
- PR 4 step commits: `931faa8` → `614750a` (10 commits ending at
  step 7 — chat handler integration tests).

**The threshold PR 4 crossed:**

> The room stopped reviewing "feature correctness" and started
> reviewing "architectural-state preservation under integration
> pressure."

This sentence is the load-bearing carrier of the methodology shift
PR 4 produced. It travels into PR 5's framing as inherited
posture, not as something PR 5 needs to re-establish.

---

## 1. What PR 4 established

### 1.1 Observational adjacency discipline

Capture is **adjacent to** arbitration, never **participatory in**
arbitration. This is now a binding contract surface, not a
convention. The integration site at
`forge_bridge/console/handlers.py:1185-1203` reads as a separate
visual act from arbitration; the conditional gate is explicit; the
emission path returns `None` and the return value is unused.

The discipline is operationally enforced by:

- **Visual-asymmetry pattern** (Gate 1 §5.1; PR 4 framing §1.1) —
  carries verbatim into the call-site adjacent comment block at
  handlers.py:1166-1183.
- **No-dependency invariant** (PR 4 framing §1.4) — `tests/corpus/
  test_pr4_no_dependency.py` enforces that `forge_bridge.corpus`
  package absence does not break arbitration. Strongest form of
  the property: arbitration runs without corpus, so the dependency
  is structurally absent.
- **Arbitration-invariance under all capture states** (PR 4
  framing §1.2) — the four hostile-environment probes
  (`disabled / enabled / failing / recovering`) confirm operator-
  visible behavior is invariant under capture state.

### 1.2 Participation-creep framing

The risk-category shift from persistence-substrate risk to
participation-creep risk is now the durable framing for any
observational integration into a live arbitration surface. The
framing names dangerous future drifts explicitly:

- `narrow_with_capture(...)` fused helpers — prohibited.
- Reading prior corpus records to influence narrowing —
  prohibited.
- Adjusting narrower thresholds based on capture-failure rates —
  prohibited.
- Any pattern where the narrower's behavior is conditioned on
  what capture has observed — prohibited.

The participation-creep grep test at `tests/corpus/
test_pr4_participation_creep.py` is the mechanical guard. It
expands forward when new corpus modules land (per framing
§1.3 forward-extension clause).

### 1.3 Hostile-environment verification

PR 4 introduced **four hostile-environment probes** as the
integration test geometry, each exercising a distinct property:

| State | Probes |
|---|---|
| `disabled` | Pre-PR-4 baseline preserved; gate short-circuits. |
| `enabled` | Successful capture; record matches arbitration output; authority-surface invariance. |
| `failing` | I-6 failure-invisibility at integration level. |
| `recovering` | Inter-emission state independence; prior failure must not poison later arbitration. |

The fixture `capture_state_cycling` in `tests/corpus/
_pr4_helpers.py` is the canonical hostile-state definition. It is
**closed for extension** at the spec layer; growth requires spec
amendment. Adding more states (e.g., `permission_denied`,
`partial_write`) would duplicate PR 3's I-6 unit-level coverage at
the integration level without adding new architectural invariants.

### 1.4 Visual asymmetry as architectural signaling

Visual-asymmetry rules are leading indicators of architectural
state, not stylistic preferences. PR 4 surfaced this insight at
the call-site (the blank line + explicit `if
divergence_capture_enabled():` conditional) and at the test layer
(the two-block geometry for the parametrized test, the three-block
geometry for the recovering test, the visible duplication of
request #1 / request #2 in the recovering test).

Specific instances locked into PR 4 artifacts:

- Module-load-time `getLogger(__name__)` direct call asymmetric
  with module-level `logger` binding (handlers.py:99-109) — the
  asymmetry is semantically meaningful, kept visible.
- Snapshot 2 producer-surface placement: `tools_post_reachability =
  filtered_tools` BEFORE the `tools = filtered_tools` rebind
  (handlers.py:1023). Truth captured at the moment of authority,
  not from the downstream alias.
- Visible duplication in the recovering test's BLOCK A and BLOCK
  B (`tests/corpus/test_pr4_chat_handler_integration.py`). The
  visual roughness is the protection.

### 1.5 Checksum-preserved carrier text

Seven verbatim carrier sentences travel byte-identical-as-text
through framing → spec → call-site adjacent comment block →
commit message body → step 7 module docstring. The verification
mechanism (`sed -E 's/^[[:space:]]*#[[:space:]]?//' | tr '\n' ' '
| tr -s ' ' | grep -F`) validates byte-identical carrier presence
in wrapped comments. Negative-control paraphrase correctly bites
the mechanism.

The seven carriers (load-bearing):

1. **PR 4 is the controlled introduction of observational side-effects into live arbitration surfaces.**
2. **The risk category has shifted from persistence-substrate risk to participation-creep risk.**
3. **The call site is the source of the three explicit inputs.**
4. **The integration layer passes truth.**
5. **The integration layer never reconstructs truth.**
6. **The builder does not discover runtime state.**
7. **Capture emission occurs only after arbitration state is finalized for the current execution path. Capture records completed arbitration observations, not provisional intermediate state.**

These do not regenerate. PR 5 inherits them verbatim. New carriers
that emerge from PR 5 framing are additive; the existing seven do
not change.

---

## 2. What PR 5 inherits unchanged

### 2.1 Integration-discipline quartet

Carries verbatim into PR 5's call-site adjacent comment block at
`forge_bridge/console/_step.py::execute_chain_step`:

> The call site is the source of the three explicit inputs.
> The integration layer passes truth.
> The integration layer never reconstructs truth.
> The builder does not discover runtime state.

Source-of-truth invariant: PR 5's `_step.py` snapshots derive from
their producer surfaces, not downstream aliases. Same authority-
surface discipline as PR 4.

### 2.2 Shape A topology posture

Top-level guarded import. Corpus availability is resolved ONCE at
module load. The `except ImportError:` branch defines fallback
bindings when the corpus package is structurally absent.

For PR 5, the same topology applies at `_step.py` module load —
not a separate guarded import, since `_step.py` would import the
emission helpers from the SAME `forge_bridge.corpus` namespace
that `handlers.py` already binds. Implementation choice for PR 5:
either (a) re-import the helpers at `_step.py` load (same shape
A), or (b) import from `forge_bridge.console.handlers` to reuse
the fallback-bound names. Decision deferred to PR 5 framing; see
§3.4 below for context.

### 2.3 Four-layer verification vocabulary

The vocabulary the room now treats as methodology, not emergent
habit:

- **Architectural property:** what invariant matters.
- **Operational expression:** today's observable manifestation of
  the property.
- **Verification mechanism:** the assertion / helper enforcing it.
- **Bite-verification mutation:** the empirical scratch proving
  the assertion would fire.

Architectural questions are settled at topology review;
bite-verification scratches are settled empirically during
incarnation. PR 5 inherits this distinction; reviewers reading
PR 5's spec should expect the architectural property to be named
explicitly at each invariant, with the operational expression and
the verification mechanism documented at the layer they belong to.

### 2.4 Review-mode discipline (writer's-room cadence)

The three-writer pattern compounded across PR 1 → PR 4. Cadence
matches work depth:

- **Light-touch review** for integration-machinery work (PR 4
  steps 2-5 ran light-touch — they were structural plumbing).
- **Full three-round review** for participation-creep boundary
  work (PR 4 steps 6 + 7 ran full review — they crossed the
  boundary).

PR 5 inherits this. Step 6 in PR 5 (the chain-step call site
itself) and the integration test bundle warrant full three-round
review; the surrounding plumbing (allowlist update, fixture reuse)
runs light-touch.

The framing → spec → step-0 → polish → integration rhythm carries
unchanged.

### 2.5 Bite-verification expectations

Each architectural invariant in PR 5 must demonstrate
falsifiability. Five bite probes confirmed during PR 4
incarnation; PR 5's bite-verification table inherits the same
operational template:

- Scratch the production code surgically.
- Run the relevant test → expect a specific failure framing.
- Revert → expect the test to pass again.

PR 5 specifically inherits the discipline that bite-verification
scratch design lives at incarnation, not at topology. If a
particular contamination vector proves to bite weakly, the correct
response is to adjust the scratch surgically — not to reopen the
assertion helper or test geometry.

### 2.6 Construction infrastructure

`tests/corpus/_pr4_helpers.py` ships shared PR-4 hostile-
environment infrastructure that PR 5 reuses without modification:

- `CaptureState` Literal + `capture_state_cycling` fixture — same
  four states, same scoped-failing-open mechanism.
- `_make_test_tool`, `_passthrough_filter`, `_stub_chat_result` —
  generic test-construction helpers; not chat-handler-specific.
- `_drive_chat_request` — chat-handler-specific; PR 5 builds an
  analogous `_drive_chain_request` (see §3.5).
- `_assert_arbitration_invariance`,
  `_assert_arbitration_response_equivalent`,
  `_assert_no_failed_write_residue`,
  `_assert_authority_surface_invariance` — assertion helpers.
  Likely reusable by PR 5 with minor parameter adjustments for the
  chain-step return shape.

The fixture is **closed for extension** at the spec layer. PR 5
must NOT add a fifth state to `capture_state_cycling`. Spec
amendment is the only path.

---

## 3. What changes in PR 5

### 3.1 Chain-step executor surface

PR 5's call site is `forge_bridge/console/_step.py::
execute_chain_step` (lines 52-…). The function signature is
materially different from the chat handler:

```python
async def execute_chain_step(
    *,
    step_text: str,
    tools: list,
    mcp: Any,
    inherited_context: dict,
) -> dict:
```

Key differences from `chat_handler`:

- `tools` is **passed in by the caller**, not freshly fetched
  from `_mcp_server.mcp.list_tools()`. The "registered_tools"
  notion has no clean analog — PR 5 must define what the
  authority-surface for deployment-identity hashing IS at the
  chain-step layer (likely: the same `tools` list passed in,
  treated as the chain-step's view of registered tools).
- No empty-list guard at this surface — the chat handler's
  `if not tools: return _chat_error("No tools registered", 500)`
  is upstream of `execute_chain_step`.
- No reachability filter at this surface — the chat handler
  already applied `filter_tools_by_reachable_backends` before
  delegating to `_execute_chain`. Snapshot 2 (`candidate_set_
  post_reachability`) at the chain-step site **collapses with
  registered_tools** — same value. This is a real semantic
  change; PR 5 framing must surface it explicitly rather than
  silently overload the snapshot.

### 3.2 Different narrowing geometry

The chat handler's narrowing path (handlers.py:1133-1164):

```python
narrower_started = time.perf_counter()
tools = filter_tools_by_message(tools, last_user_text)
tools_filtered_count = len(tools)

tools_post_pr14 = tools

if tools_filtered_count > 1:
    narrowed = deterministic_narrow(tools, last_user_text)
    if len(narrowed) < len(tools):
        tools = narrowed
        tools_filtered_count = len(narrowed)
narrower_latency_ms = (time.perf_counter() - narrower_started) * 1000.0
```

The chain-step's narrowing path (`_step.py:85-89`):

```python
filtered = filter_tools_by_message(tools, step_text)
if len(filtered) > 1:
    narrowed = deterministic_narrow(filtered, step_text)
    if len(narrowed) < len(filtered):
        filtered = narrowed
```

Differences PR 5 must reckon with:

- **No latency instrumentation surface in `_step.py` today.** PR 5
  must add `narrower_started` / `narrower_latency_ms` if the
  chain-step capture is to carry the same `narrower.latency_ms`
  field as chat-handler captures. Architectural property: latency
  measurement decoupled from capture state, same as PR 4 §4.1.
- **No `tools_post_pr14` snapshot binding today.** The chain step
  uses `filtered` as a single mutable variable; the post-PR14
  snapshot must be added before the `if len(filtered) > 1:`
  block. Authority-surface discipline.
- **`tools_filtered_count` not tracked separately.** PR 5 may need
  to add it for the `pr20_condition_met` and `collapse_occurred`
  derivations — or may decide both fields are inapplicable to
  chain-step semantics (see §3.3).

### 3.3 Executor-specific participation-creep vectors

PR 5's call-site has its own participation-creep risk profile,
distinct from PR 4's:

- **Ambiguity is a failure mode, not a fall-through.** Chain steps
  REJECT when narrowing leaves > 1 tool (`_step.py:90-101` returns
  `tool_selection_ambiguous` error envelope). The chat handler
  falls through to LLM disambiguation. This means:
  - `pr20_condition_met` semantics are unclear at the chain-step
    layer. PR 5 framing must decide: is this field always `False`
    here? Always `True`? Removed from chain-step records?
  - `collapse_occurred` semantics — what does "collapsed multi to
    single" mean when the alternative is an error envelope? The
    field still has meaning (multi → single transition observed),
    but its arbitration significance differs.
  - **Ambiguity capture-correctness:** PR 5 must decide whether
    capture fires when ambiguity rejects. Architectural argument:
    yes — the rejection IS the arbitration outcome, and Layer 1
    must record it. Operational argument: yes, but the
    `narrower_decision` field would be empty (zero survivors after
    rejection) or the multi-tool list (ambiguous candidates).
- **`tool_selection_ambiguous` envelope is a participation
  vector.** A future contributor "improving" the error envelope to
  reach for capture-side data ("which tools have we historically
  selected for similar prompts?") would cross the participation
  boundary. The participation-creep grep at PR 4 step 3 already
  protects this — the grep verifies `_step.py` imports zero corpus
  modules except the emission path. PR 5 extends the allowlist by
  exactly one entry: `console/_step.py` joins `console/handlers.py`.
- **Caller-owned `tools` list mutation.** `_step.py`'s `tools`
  parameter is the caller's reference. The chat handler's
  `_execute_chain` (handlers.py:~1119) passes its own narrowed
  `tools` into the chain executor. Authority-surface discipline:
  the `registered_tools` snapshot at the chain-step site captures
  what the caller passed, NOT what the daemon's full registry
  looks like. PR 5 framing must name this explicitly: the
  chain-step's "deployment identity" is the caller's view, not the
  global view.

### 3.4 Shape A topology decision (re-imports vs. re-uses)

Implementation choice for PR 5's emission-path import:

- **Option (a) — Re-import the helpers at `_step.py` load** (same
  shape A as `handlers.py`). Pros: symmetric topology, identical
  fallback semantics. Cons: duplicate WARNING-on-load if both
  modules reach for the same absent corpus.
- **Option (b) — Import from `forge_bridge.console.handlers` and
  reuse the fallback-bound names.** Pros: one WARNING per process
  lifetime regardless of how many call sites exist. Cons: implicit
  cross-module dependency from `_step.py` to `handlers.py` that
  doesn't exist today.

Recommendation: option (a). The structural symmetry is worth more
than the duplicate WARNING (which fires once per call-site module
on import — an O(1) cost, not O(N) per emission). PR 5 framing
should commit to this.

### 3.5 Test bundle

PR 5 ships a sibling integration test file —
`tests/corpus/test_pr5_chain_step_integration.py` (or similar) —
with the same five-test geometry:

- 3-state parametrized invariance test (over chain-step success
  envelope shape, not chat success envelope).
- Dedicated recovering test (three-block geometry, visible
  duplication preserved).
- Dedicated latency-delta test (min-of-N, asymmetric target/
  ceiling — same thresholds as PR 4 unless chain-step semantics
  warrant adjustment, which they should not).

The construction-helper analog `_drive_chain_request` (or
equivalent) lives in `_pr4_helpers.py` (rename to
`_pr_helpers.py`?) or in a new `_pr5_helpers.py`. Decision
deferred to PR 5 framing.

`_assert_arbitration_invariance`'s contents adapt for the chain
envelope shape: chain steps return `{"result": ..., "tool":
..., "params": ...}` on success, not `{"messages": [...],
"stop_reason": ..., "request_id": ...}`. The helper's
docstring's IS-compared / IS-ignored split must be re-derived for
the chain envelope.

### 3.6 Suite arithmetic projection

If PR 5 adds 5 chain-step tests symmetric with PR 4's:

- forge (3.11): 124 → ~129 corpus tests passing.
- forge-bridge (3.12): 118 + 2 file-skipped → 118 + 3
  file-skipped (one new file collection-skipped due to jinja2
  importorskip).
- tests/console/ unchanged.

Adjust at PR 5 incarnation.

---

## 4. Queued future work

### 4.1 Visual-asymmetry linting (PR 6)

Gate 1 §5.1's visual-asymmetry pattern is a code-review-only check
through PR 4 + PR 5. PR 6 is the executable lint backstop. It
earns its keep when there are multiple call sites to compare
against the canonical pattern (PR 5 adds the second). Lint design
benefits from both PR 4 and PR 5 as input — exercised integration
surfaces, enough operational reading exposure to distinguish
structural choices from incidental ones.

### 4.2 Python 3.13 migration trajectory

`SEED-PYTHON-3.13-MIGRATION-V1.5+.md` (planted at commit
`fe76578`) tracks the broader migration. Flame 2027 is the
external forcing function; migration is its own phase.
Out-of-scope for Gate 1.

### 4.3 Gate 2 — Seed corpus drive

Fixture-based seed prompts. PR 4 + PR 5 only enable the runtime
probe at the call sites. Gate 2 spec drafts after Gate 1 closure.

### 4.4 Gate 3 — Operator workstation enablement

Runtime capture enablement on the operator workstation. Out of
Gate 1 scope.

### 4.5 Gate 4 — Comparator + Layer 2 schema

The comparator implementation, Layer 2 record schema in code, and
console-script entry. Gate 4 framing inherits PR 4's
participation-creep grep forward-extension clause: any new corpus
module surfaces (reader, comparator, replay-analysis helpers,
historical lookup helpers, corpus-derived heuristic surfaces)
require the participation-creep grep test to expand with them.

### 4.6 Stray-header-mid-file warning sharpness

Deferred from PR 3 UAT (PR 4 framing §4.2). Routing: PR 6 polish
or v1.5.x patch. Adding it to PR 5 would dilute the
participation-creep focus.

### 4.7 Unresolved observational-topology questions

For PR 5 framing to surface explicitly:

- **Is there a chain-step "deployment identity" snapshot?** The
  caller's `tools` parameter is the only candidate; whether
  hashing it as `registered_tools_snapshot_hash` produces a
  meaningful identity that's stable across chain-step invocations
  is an open question. If different chain steps see different
  `tools` lists (e.g., one step's allowed-tools subset is narrower
  than another's), the "deployment identity" varies per step,
  which contradicts PR 3 §5's framing.
- **Does ambiguity-rejection capture ship in PR 5 or Gate 4?** PR 4
  captured arbitration outcome at the chat-handler layer including
  the `narrower.decision` field reflecting the LLM-or-forced
  selection. Chain-step ambiguity rejection is an arbitration
  outcome too — but the decision is "no decision" / "rejected." PR
  5 framing must commit to whether this state ships in the
  baseline schema or is deferred.
- **Latency-budget calibration.** PR 4's 5ms target / 20ms ceiling
  was anchored to the chat-handler integration surface. Chain
  steps run at higher cadence (multi-step chains) and the latency
  budget may need re-calibration. Default: keep 5/20 unchanged
  unless empirical data during PR 5 incarnation surfaces a real
  conflict.

---

## 5. Methodology observations surfaced during PR 4

These are durable methodology observations the room produced
during PR 4. They are now inherited posture, not rediscoveries.

### 5.1 Review asymmetry collapses before runtime asymmetry

Code begins to "look integrated" before it becomes integrated.
Visual-asymmetry rules are leading indicators of architectural
state, not stylistic preferences. A reviewer who finds a test
"looks clean" should be suspicious — visual roughness (the
two-block structure, the dedicated recovering function, the
asymmetric latency framing) is the protection.

Concrete instances during PR 4:

- The blank line + explicit `if divergence_capture_enabled():`
  guard at the call site (handlers.py:1185) — not stylistic, a
  spec requirement.
- The two-block geometry of the parametrized test — invariance
  first, capture-correctness second, never interleaved.
- The three-block geometry of the recovering test — visible
  duplication of request #1 and request #2 carries semantic
  weight.

### 5.2 Byte-identicality as semantic checksum preservation

When a sentence emerges from one writer that names a failure mode
sharply, it gets preserved verbatim into spec, code, commit
messages. This is **semantic checksum preservation**, not
stylistic rigidity.

The verification mechanism — `sed -E 's/^[[:space:]]*#[[:space:]]?//' |
tr '\n' ' ' | tr -s ' ' | grep -F` — proves the property:
byte-identical carrier presence in wrapped comments. Negative-
control paraphrase correctly bites the mechanism.

### 5.3 Meaningful asymmetries should remain visible

Asymmetries that carry semantic weight should not be cosmetically
harmonized. Two examples from PR 4 step 6:

- The `getLogger(__name__)` direct call inside the `except
  ImportError:` branch (handlers.py:99-109) is asymmetric with the
  module-level `logger` binding (handlers.py:117). The asymmetry
  is semantically meaningful — the import branch executes during
  module-load before the `logger` name is bound. Comments at
  handlers.py:99-101 document this. A reader who finds the
  asymmetry "ugly" and harmonizes it (e.g., moves the `logger =
  logging.getLogger(__name__)` binding above the try/except) loses
  the load-order signal.
- The recovering test's three-block geometry is visibly heavier
  than the other states' two-block geometry. "Cleaning up" by
  factoring the duplication into a helper erases the architectural
  signal that the recovering probe is two independent arbitration
  acts, not one with retry.

### 5.4 Test geometry should mirror runtime asymmetry

The test's structural shape should match the runtime asymmetry it
probes. The recovering state is qualitatively different from the
other three (temporal contamination probe vs. nominal
correctness), so its test function is qualitatively different
(three-block vs. two-block, two invocations vs. one). Reviewer
verification: §1.2 can be verified by reading only the first
block of the parametrized test; §5.3's protected property
(inter-emission state independence) requires reading all three
blocks of the recovering test.

### 5.5 Verification mechanisms validate protected semantic properties

Verification mechanisms must validate the protected semantic
property itself, not a proxy. PR 4 step 6 surfaced this as the
wrapped-carrier flattening pipeline correction: a literal `grep`
against wrapped comments would have produced false negatives
(line wrapping breaks substring matches). The protected property
is "byte-identical-as-text presence of the carrier sentence";
the verification mechanism must validate that property directly,
not a stylistic proxy.

### 5.6 Correction-cycle pattern (now five instances; consolidating)

"Schema semantics drifting toward inferred/predicted truth at the
call site." Each correction caught the same shape — measured
truth vs. inferred interpretation — and surfaced during integration
review by reading what would be *computed* against what the schema
*claims to record*.

The five instances:

1. **PR 3 §5 orthogonal-truth-surfaces** — registered_tools must
   be a separate explicit input.
2. **PR 4 schema rename** — `pr20_fired` → `pr20_condition_met`
   (semantic mismatch).
3. **PR 4 collapse_occurred derivation tightening** — measure the
   specific multi-to-single transition.
4. **PR 4 step 6 snapshot 2 producer-surface placement** —
   `tools_post_reachability = filtered_tools` BEFORE the rebind,
   not from the downstream alias.
5. **PR 4 step 6 wrapped-carrier flattening** — verification
   mechanism must validate the protected semantic property
   itself, not a proxy.

PR 5 framing should expect the same correction shape to surface
at least once during incarnation. It is not a defect in the spec
or framing; it is a property of integration review producing
sharper semantics than topology review alone can.

### 5.7 Implementation review vs spec review (preserved)

Implementation review and spec review catch different classes of
mismatch. Spec review catches structural drift by reading
documented intent. Implementation review catches semantic drift
by reading computed behavior. Both are necessary; neither subsumes
the other. Pause-and-surface during implementation is the
discipline that closes the second gap.

The three-writer pattern operationalizes this — the third writer
often catches structural drift that this assistant misses; this
assistant often catches operational drift that the third writer's
higher-altitude reading skips.

### 5.8 The threshold

The most consequential methodology observation from PR 4. Naming
it explicitly here so it travels into PR 5 framing:

> The room stopped reviewing "feature correctness" and started
> reviewing "architectural-state preservation under integration
> pressure."

PR 4 was the inflection point. PR 1 + PR 2 + PR 3 reviewed
"does the persistence layer work?" — feature correctness. PR 4
reviewed "does the integration preserve the participation
boundary?" — architectural-state preservation under integration
pressure. The two review modes look superficially similar but
ask different questions and produce different artifacts. The
former produces test cases; the latter produces invariants,
hostile-environment probes, and bite-verification scratches.

PR 5 inherits the latter mode by default. A reviewer who attempts
to revert PR 5 to feature-correctness review (e.g., "does
`execute_chain_step` still return the right envelope when capture
is enabled?") is asking the wrong question. The right question is
"does `execute_chain_step` preserve the participation boundary
under all four hostile-environment capture states, and does its
arbitration output remain invariant under capture state?"

---

## 6. Reseed protocol — what the next session does with this artifact

When the PR 5 session opens:

1. **Read this CLOSE artifact first.** It contains the durable
   PR 4 state that PR 5 inherits. Skipping it means re-deriving
   the participation-creep framing from session history, which is
   how the integration accidentally regrows participation features.
2. **Read `A.5.3.2-PR4-FRAMING.md` §1.2 and §1.4.** The
   arbitration-invariance and no-dependency invariants carry
   forward to PR 5 unchanged.
3. **Read `forge_bridge/console/_step.py::execute_chain_step`**
   (lines 52-…). The PR 5 surface. Confirm geometry differences
   per §3 above.
4. **Draft `A.5.3.2-PR5-FRAMING.md`.** Inherit the seven carriers,
   the four-layer vocabulary, the integration-discipline quartet.
   Resolve the open questions in §4.7 (chain-step "deployment
   identity" snapshot, ambiguity-rejection capture, latency-budget
   calibration). Surface for review before drafting the spec.
5. **Draft `A.5.3.2-PR5-SPEC.md`** from the framing.
6. **Implement PR 5** per the same nine-step sequence as PR 4
   (schema rename if any, allowlist transition, participation-
   creep grep extension, helper extension, no-dependency check
   inheritance, chain-step integration, integration tests, full
   suite verification, surface for review).
7. **Close PR 5 with `A.5.3.2-PR5-CLOSE.md`** following this
   artifact's structure.

The cadence — framing → spec → step-0 → polish → integration —
carries unchanged.

---

## 7. Cross-references

- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift, four risks, integration-discipline quartet.
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — implementation
  contract.
- `A.5.3.2-GATE-1-SPEC.md` §4 (the two arbitration call sites);
  §5 (capture invocation contract); §9 (implementation sequence).
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants.
- `A.5.3.2-PR3-SPEC.md` §5 (orthogonal truth surfaces); §6.5
  (atomic-append discipline); §9 (corruption locality).
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion
  candidate for the methodology observations in §5 above.
- `SEED-PYTHON-3.13-MIGRATION-V1.5+.md` — migration trajectory,
  queued behind Gate 1.
- PR 4 step commits (origin/main):
  - `931faa8` — step 0: pr20_fired → pr20_condition_met
  - `1b07c33`, `fe76578` — pre-step-1 polish
  - `5da1bea` — step 1: cold-vs-warm topology docstring
  - `9a0d52a` — step 2: discipline grep allowlist
  - `75183cd` — step 3: participation-creep grep
  - `80ab704` — step 4: capture_state_cycling fixture
  - `ac12ca0` — step 5: no-dependency assertion
  - `3b412f8` — step 6: chat handler integration
  - `614750a` — step 7: chat handler integration tests

---

PR 4 closes here. PR 5 begins at the next session boundary.
