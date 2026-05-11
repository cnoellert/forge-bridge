# A.5.3.2 PR 10 — Framing (comparator helper + structural protection)

**Status:** PR 10 opens at `2f70cbf` (origin/main, Gate 3
framing landed). This framing locks the architectural posture
for the comparator helper and the binding decisions reached
during the Gate 3 framing → PR 10 framing convergence pass.
PR 10 is the first of two (or conditionally three) PRs
sequenced within Gate 3 per Gate 3 framing §10.

The convergence pass produced six binding decisions: module
name `_compare.py` (§5.1); pair-input pure-functional shape
(§5.2); no persistence / no async / no class / no subsystem
(§5.3); Layer 2 Option A locked — 4th walker (§5.4); test
count target 5–7 new tests at PR 10 (§5.5); PR-10-LOCAL
binding statement on the comparator's read-only mutability
invariant (§5.6).

---

## 0. Crystallizing pair — carrier #17 (active) + Gate-3-LOCAL governing sentence (corroboration substrate)

Two sentences govern PR 10 verbatim. They appear at the top
of `_compare.py`'s module docstring, the top of PR 10 test
module docstrings, and PR 10 commit message bodies under
"preserved invariants."

**Active carrier #17 (recomposition discipline):**

> **Recomposition preserves authorship. The comparator joins
> observation + expectation records by `fixture_id` at read
> time; the join produces a derived view that names each
> authority surface's contribution explicitly. Cleanup
> pressure to collapse the three-authority-surface partition
> through interpretive synthesis is rejected at the spec
> layer.**

This carrier is the architectural commitment PR 10 enacts.
Every PR 10 deliverable — the function signature, the
divergence report shape, the 4th walker's protection — is
the operational form of this carrier.

**Gate-3-LOCAL governing sentence (corroboration substrate
for candidate carrier #16):**

> **Gate 3 proves topology, not infrastructure.**

This sentence is the operational discipline PR 10
demonstrates. Every PR 10 deliverable that collapses
infrastructure-pressure back to topology — function not
subsystem, pair-input not batch-orchestration, single walker
not parametrized walker base class — is corroboration
evidence the Gate 3 close evaluation reads (per Gate 3
framing §6.1 evaluation criteria #1).

**Travel discipline at PR 10:**

The pair travels verbatim at every site. Carrier #17 appears
first (active, primary load-bearing). The Gate-3-LOCAL form
appears second with explicit *candidate carrier #16
corroboration substrate* marking — the corroboration is
discipline evidence, not a quiet promotion-by-stealth. The
asymmetric ordering matches the asymmetric carrier states
(active vs. candidate).

PR 10 is **the canonical instance** of the function-vs-
subsystem cleanup-pressure trap candidate carrier #16
exists to govern. Successful resistance of the trap during
PR 10 implementation is the load-bearing corroboration
Gate 3 close evaluates.

---

## 1. Predecessors (binding, in order)

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, six
  interlocking structural-invariant pairs.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing, three
  architecturally-prohibited patterns, helper signature,
  visual-asymmetry pattern.
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — three-authority-
  surface partition; carrier #14; binding clarification on
  call-site-owned arbitration inputs.
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — observation +
  dispatch-provenance surfaces; carrier #14;
  `_KNOWN_RECORD_KINDS` 2-element lock; cleanup-pressure-
  resistance class members #1–#6.
- `A.5.3.2-PR8-CLOSE.md` (`b102010`) — authored expectation
  surface; PR-INTERNAL three-way authority partition;
  carrier #15; members #7 + #8.
- `A.5.3.2-PR9-CLOSE.md` (`a6e42f0`) — three-fixture corpus;
  grounding-time amendment variant; cumulative architectural
  concentration; member #9; the authored/observed divergence
  proof case.
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — gate-arc synthesis;
  Gate 4 comparator's two foundational dependencies
  operationally verified.
- `A.5.3.2-GATE-3-FRAMING.md` (`2f70cbf`) — **immediate
  predecessor; the gate-level inheritance contract PR 10
  operates against.** Three inherited truths; Path B locked;
  candidate carrier #16 + Gate-3-LOCAL form; carrier #17;
  binding framing clarification on cross-surface unbinding;
  seven canonical cleanup-pressure forms; proactive scope
  guardrail.
- **Gate 3 framing → PR 10 framing convergence pass (this
  session):** six binding decisions locked (module name,
  function shape, no-persistence/no-async/no-class, Layer 2
  Option A, test count target, PR-10-LOCAL binding
  statement). The convergence pass produced one PR-LOCAL
  binding statement (§5.6) without introducing new carriers
  — PR 10 inherits Gate 3 framing's carrier set unchanged.

---

## 2. PR 10 objective

PR 10 ships the **comparator helper** — a single pair-input
pure-functional read surface in
`forge_bridge/corpus/_compare.py` that produces a structured
divergence report preserving authorship per carrier #17.

The operational shape:

- Module: `forge_bridge/corpus/_compare.py` (§5.1).
- Function: single function, pair-input — one observation
  record + one expectation record (§5.2).
- Return value: structured divergence report; shape posture
  locked (authorship preservation, pure-value semantics,
  within-surface scope); exact symbols at PR 10 spec.
- No persistence, no async, no class hierarchy, no plugin
  surface, no registry, no configuration object, no module-
  level mutable state (§5.3).
- Imports are read-only: schema constants if needed; no
  emission helpers; no writer primitives; no orchestrator
  surfaces (§4.1).
- Layer 1 allowlist extends mechanically (one new file).
- Layer 2 4th walker introduced (Option A per Gate 3 framing
  §8.2; `_COMPARE_PERMITTED_IMPORTS` value-locked frozenset;
  walker scoped to `_compare.py`).

### 2.1 Why pair-input, not batch-input

The function's authority signature names what it consumes:
one observation record + one expectation record. This is the
type-level expression of carrier #17. Pair-input forces the
caller to have already partitioned the corpus by
`record_kind` AND joined by `fixture_id` — i.e., the caller
has already operationalized the comparator's two foundational
dependencies (Gate 2 close §2.1). **The comparator does ONE
thing: compute divergence between this specific pair.**

A batch-input function with `dict[fixture_id, DivergenceReport]`
return shape is structurally closer to a subsystem:

- It orchestrates iteration (loops over fixture_ids).
- It handles the missing-companion case (what if an
  observation has no expectation, or vice versa?).
- It decides on join-failure semantics (raise? skip? null
  fields?).

Each of those is a policy decision masquerading as a
function. Carrier #16's candidate form ("Reliability work
proves topology, not infrastructure") rejects the
subsystem-shape. The Gate-3-LOCAL form ("Gate 3 proves
topology, not infrastructure") rejects it operationally at
Gate 3 scope. **PR 10 locks pair-input to corroborate.**

Join is the caller's concern. PR 11 integration tests
demonstrate the boilerplate is 3 lines:

```python
# in PR 11 test setup
records = read_capture_file(...)
by_fixture = collect_by_fixture_id(records)  # 1 line
for fixture_id, pair in by_fixture.items():
    obs = pair["observation"]
    exp = pair["expectation"]
    report = compare(obs, exp)
    ...
```

If join boilerplate appears at 4+ call sites in PR 11 + Gate 4
+ future Gate-X work, **PR 12 (conditional, per Gate 3
framing §10) introduces a small join helper.** That decision
is observation-driven (cleanup pressure surfaces) not
speculation-driven; PR 10 framing does not pre-author the
helper.

### 2.2 Why module name `_compare.py`

Sibling of existing corpus modules:

- `forge_bridge/corpus/_capture.py` — observation surface
- `forge_bridge/corpus/_seed.py` — orchestration + authored
  expectation surface
- `forge_bridge/corpus/_schema.py` — record schemas
- `forge_bridge/corpus/_sources.py` — `KNOWN_SOURCE_VALUES`
- `forge_bridge/corpus/_identity.py` — fixture identity
  helpers
- `forge_bridge/corpus/_topology.py` — topology helpers
- `forge_bridge/corpus/reader.py` — JSONL reader

`_compare.py` reads as a descriptive verb (what the module
does — compares records) without smuggling broader scope
vocabulary. Specifically rejected alternatives:

- `_correlate.py` — implies cross-surface correlation;
  smuggles ontology that Path B explicitly unbinds.
- `_diverge.py` — names the symptom (divergence) not the
  operation (comparison). Asymmetric framing.
- `_compose.py` — implies the comparator authors
  composition; misses that it's a derived-view computation.
- `_join.py` — would imply the function does the join;
  pair-input shape contradicts this.

`_compare.py` is the precise name for the operation:
"compare these two records and report what diverged."

### 2.3 Architectural success signal continuity

Per Gate 3 framing §11 criterion 11 — Gate 3 inherits PR 9's
"0 production source file modifications" architectural
success signal as a goal, not just a happy outcome. **PR 10
ships ZERO modifications to production source files outside
the new `forge_bridge/corpus/_compare.py` file.** No
modification to `_capture.py`, `_seed.py`, `_schema.py`,
`_sources.py`, `reader.py`, or any other corpus or
production module. The architectural success signal
continues if PR 10 lands without inside-out modification of
existing surfaces.

---

## 3. Architectural inheritance

### 3.1 16 active carriers + 1 candidate + binding clarifications + Gate-3-LOCAL governing sentence

Inherited from Gate 3 framing unchanged. PR 10 introduces
**no new carriers** and **one PR-10-LOCAL binding statement**
(§5.6, scope-local to PR 10 surfaces).

**Active carrier count at PR 10 framing: 16** (#1–#15 +
#17). **Candidate carrier #16** preserved. **Gate-3-LOCAL
governing sentence** active as corroboration substrate.

Carriers travel verbatim into:

- `_compare.py` module docstring (top-of-file, relevance-by-
  file ordering: carrier #17 + Gate-3-LOCAL form first).
- Comparator function docstring (carrier #17 + the proactive
  scope guardrail + PR-10-LOCAL binding statement).
- 4th walker test module docstring (carrier #17 + Gate-3-
  LOCAL form + the parallel-not-extension protection echo:
  *"Shared AST mechanics do not imply shared ontology"*).
- PR 10 commit message bodies under "preserved invariants."

The 16-active count discipline holds: PR 10 spec authors
must not write *"17 carriers"* or *"carriers #1–#17"* —
correct phrasing is *"carrier #17"* (singular) or *"16
active carriers + candidate #16"* (per Gate 3 framing §6
binding accounting). Implicit promotion of candidate #16 at
PR 10 is rejected at PR 10 spec review.

### 3.2 Three-authority-surface partition operational

Gate 2 §3.4 partition preserves unchanged at PR 10:

- Observation surface — `emit_divergence_capture` + contextvar
  resolution.
- Dispatch provenance surface — `seed_dispatch_scope` +
  `_DispatchContext`.
- Authored expectation surface — `emit_seed_expectation` +
  `drive_seed_fixture` + schema validator.

**PR 10's comparator consumes all three surfaces' outputs
(through their persisted records) but speaks on behalf of
none of them.** The comparator's authority claim is
interpretive ("these two records, jointly, diverged in the
following way") — derived from the surfaces, not authored at
any of them. Carrier #17 protects this distinction
operationally.

### 3.3 Three-walker Layer 2 partition operational

The PR 4 + PR 8 + PR 9 walkers preserve unchanged. PR 10
adds a **4th walker** (Option A per Gate 3 framing §8.2)
preserving the parallel-not-extension boundary — its
ontology is **read-only-interpretive authority**, distinct
from the three existing ontologies:

| Walker | Target | Ontology |
|---|---|---|
| PR 4 | narrowing-subsystem source files | one-directional production import flow |
| PR 8 | `_seed.py` | orchestration participation discipline (5-symbol bounded toolbox) |
| PR 9 | fixture directory modules | declarative fixture-data discipline (single-symbol gate) |
| **PR 10 (new)** | `_compare.py` | **read-only-interpretive authority** |

Each walker shares AST mechanics (`ast.walk` + import-node
traversal) but protects a distinct ontology. **"Walker
unification" cleanup proposals are rejected at the spec
layer** per Gate 2 close §1.6 + §2.4 item 5 + Gate 3 framing
§8.2.

### 3.4 Cleanup-pressure-resistance class at 9 members

Inherited unchanged. PR 10 framing does **NOT speculatively
author new members** (per Gate 3 framing §7 item 13 +
PR 10 §6). New members surface at PR 10 close based on
actual pressure encountered during implementation; framing
names likely surface candidates (§6) without authoring them.

### 3.5 Proactive scope guardrail

> **The comparator compares authored expectation records
> against observed arbitration records within a single
> operational arbitration surface.**

(NOT "logical prompts," NOT "semantic tasks," NOT "cross-
surface executions" — per Gate 3 framing §2.3.)

Travels verbatim into `_compare.py` module docstring,
comparator function docstring, and PR 10 test module
docstrings. Field names in the divergence report MUST NOT
smuggle broader scope vocabulary (e.g., `task_outcome`,
`prompt_resolution`); such field names are rejected at PR 10
spec review per Gate 3 framing §5.6.

### 3.6 Seven canonical cleanup-pressure forms — PR 10-relevant subset

Gate 3 framing §4.2 enumerated seven canonical pressure
forms. PR 10 expects to encounter three most directly:

- **Form 1 (helper merger).** *"Just have the comparator
  emit a divergence record while reading the input pair."*
  Mechanism: the comparator inlines a writer call. Rejected
  per carrier #17 + member #8 + §5.3 + §7 item 1.
- **Form 3 (persistence creep).** *"The comparator could
  write the report to a sidecar file."* Mechanism: the
  comparator gains I/O. Rejected per §5.3 + §5.6 + §7 item
  1.
- **Form 7 (walker abstraction).** *"The 4th walker shares
  ~80% AST mechanics with PR 8 + PR 9 walkers; we could
  DRY them into a parametrized base class."* Mechanism: a
  generic walker class with per-ontology subclasses.
  Rejected per §3.3 + §7 item 18.

Forms 2 (schema merger), 4 (inline emission), 5 (premature
surface normalization), 6 (speculative fixture-semantics
widening) may surface secondarily. The discipline at PR 10:
when a pressure form surfaces, register the rejection
language inline at the rejection site + at PR 10 close as
candidate class member 10+ (if the form is new) or as
operational corroboration of existing class members
#7/#8/#9.

### 3.7 Four-variant amendment-at-incarnation taxonomy

Available to PR 10 implementation without re-framing. The
**grounding-time variant** is most likely to surface at
PR 10 — the divergence report shape is documented at framing
level (§4.3 posture) but unexercised; empirical
implementation may reveal that the framing/spec extrapolation
of the shape does not match the operational topology of the
observation/expectation record fields. Implementations
should *expect* grounding-time amendments and register them
per the canonicalized discipline (separate NO-code amendment
commit per user direction at amendment convergence).

### 3.8 Step N.5 surgical cadence three-times corroborated

The pattern is available to PR 10 without re-framing. PR 10
may contribute a fourth corroboration instance if mid-flight
guidance surfaces an additive improvement to a recently-
shipped deliverable.

### 3.9 PR-INTERNAL three-way authority partition (PR 8 §4.1.5.1)

PR 8's sub-partition (authored expectation semantics /
orchestration semantics / persistence topology) preserves
unchanged. PR 10's PR-10-INTERNAL partition (read / compute
divergence / report shape) is structurally parallel but
scope-local to `_compare.py`. The two partitions compose at
two distinct module surfaces; neither subsumes the other.

### 3.10 Reseed protocol — Gate-3-LOCAL form active

The Gate-3-LOCAL governing sentence is operational at PR 10
implementation. It travels at the same sites as active
carriers (with explicit *candidate carrier #16 corroboration
substrate* marking) and serves as the operational
governance PR 10 acts on against cleanup-pressure-toward-
infrastructure. Successful resistance during PR 10
implementation contributes ≥3 of the ≥4 surface count
Gate 3 close evaluation requires for candidate carrier #16
promotion.

---

## 4. Architectural delta from PR 10

### 4.1 `_compare.py` — the interpretive read surface

New module: `forge_bridge/corpus/_compare.py`. Structurally:

- **Module-level docstring** carries (relevance-by-file
  ordering):
  1. Carrier #17 (recomposition discipline).
  2. Gate-3-LOCAL governing sentence (candidate #16
     corroboration substrate).
  3. Proactive scope guardrail (§3.5).
  4. PR-10-LOCAL binding statement (§5.6).
  5. The 16 inherited active carriers (#1–#15 + reference
     to #17 at top) — abbreviated where the carriers
     themselves are not load-bearing for `_compare.py`
     specifically (e.g., visual-asymmetry carriers govern
     emission, not interpretation; cite-by-reference).
  6. Binding framing clarifications (call-site-owned
     arbitration inputs + cross-surface unbinding).
- **Single function** (name finalized in PR 10 spec; working
  reference: `compare`).
- **No state.** No classes. No module-level constants beyond
  what the function's body needs (e.g., a private constant
  naming the two expected `record_kind` values, if validation
  uses it; otherwise none).
- **Read-only imports.** Schema constants if needed for
  validation; reader surfaces if needed for type hints; NO
  emission imports; NO writer imports; NO `_seed.py` imports;
  NO `_capture.py` imports beyond schema if relevant. The
  exact import set is finalized at PR 10 spec; the 4th
  walker (§4.4) enforces the closure.

The module is a **leaf consumer**. It is structurally
incapable of:

- Mutating its inputs (the function takes records as
  arguments; returns a new value).
- Triggering upstream emission (no emission helper imports
  available — Layer 2 walker enforces).
- Persisting state (no writer imports; no I/O).
- Holding state across calls (no module-level mutable
  state; function is pure).

These properties are protected at three layers:

1. **Type signature** — pair-input function returning a
   structured value; no `Writer` parameter, no I/O return,
   no side-effect mutator argument.
2. **Module imports** — Layer 2 4th walker (§4.4) rejects
   any import that would enable mutation, emission, or
   persistence.
3. **Function body discipline** — PR-10-LOCAL binding
   statement (§5.6) names the read-only mutability
   invariant; PR 10 tests assert it (input records are not
   modified after `compare()` returns).

### 4.2 The comparator function — pair-input shape

Function shape posture (exact symbol = PR 10 spec):

```python
def compare(
    observation_record: dict,
    expectation_record: dict,
) -> DivergenceReport:
    """
    Compare a single observation record against its companion
    expectation record. Return a structured divergence report
    naming each authority surface's contribution explicitly.

    [Carrier #17 verbatim.]
    [Gate-3-LOCAL form verbatim.]
    [Proactive scope guardrail verbatim.]
    [PR-10-LOCAL binding statement verbatim.]

    Args:
        observation_record: a dict with record_kind ==
            "observation"; the runtime observation authored
            by emit_divergence_capture under seed dispatch
            context.
        expectation_record: a dict with record_kind ==
            "expectation"; the authored expectation declared
            by emit_seed_expectation.

    Both arguments must share an identical fixture_id; the
    function validates and raises on mismatch.

    Returns:
        A structured divergence report (shape per PR 10 spec
        §X). The report preserves authorship: each claim is
        identifiable as observation-sourced or expectation-
        sourced.

    Raises:
        ValueError on record_kind mismatch, fixture_id
        mismatch, or missing required fields. (Exact
        exception type per PR 10 spec.)
    """
```

**Authority signature explicit:** the parameter names —
`observation_record` and `expectation_record` — name what
each input IS. The signature does NOT use positional-only
unnamed args, generic `record_a`/`record_b` naming, or
opaque tuples. **The type-level expression of carrier #17
starts at the function signature.**

**Validation discipline:** the function MAY validate the
following at entry:

- `observation_record["record_kind"] == "observation"`
- `expectation_record["record_kind"] == "expectation"`
- `observation_record["fixture_id"] == expectation_record["fixture_id"]`
- Both records contain the required fields the divergence
  computation reads (exact field set = PR 10 spec; at
  minimum, observation's nested `narrower.decision` and
  expectation's flat `expected_narrow`).

Validation failures raise an exception. The function does
NOT silently accept mismatched inputs, fall back to defaults,
or produce a "partial" divergence report. **Misuse is loud,
not silent.**

(Validation is a sanity check against caller misuse — NOT a
semantic claim. The validation does not author truth about
whether the records "should" diverge; it asserts the inputs
are joinable per Gate 2 close §2.1's two foundational
dependencies.)

**Binding behavioral commitment — compare as persisted:**

> **The comparator compares authored and observed records as
> persisted. It does not normalize, reorder, canonicalize,
> repair, or semantically coerce either surface before
> comparison.**

This sentence is the function-body-level binding commitment
closing cleanup-pressure form #5 (premature surface
normalization; Gate 3 framing §4.2 + this framing §3.6). Form
#5's enumeration *describes* the pressure; this commitment is
what rejects the pressure at the function body. The two
operate at different layers and travel together — Gate 3
framing §4.2 names the cleanup-pressure form; PR 10
framing §4.2 (this paragraph) names the behavioral
commitment.

**Operational rejections this commitment makes explicit:**

- The comparator does NOT sort `narrower.decision` or
  `expected_narrow` before comparing — order is meaningful
  observation/expectation; reordering masks divergence.
- The comparator does NOT lowercase tool names, strip
  whitespace, or apply any string canonicalization — those
  are surface-authorship details preserved.
- The comparator does NOT "repair" missing fields, fill
  defaults, or infer absent values — missing data is a
  validation failure (§4.2 validation discipline), not a
  silent normalization.
- The comparator does NOT compare semantically (e.g., "these
  two records mean the same thing even though they differ")
  — comparison is byte-for-byte structural on the persisted
  record contents.

**The commitment travels verbatim:**

- Into the comparator function's docstring (under
  PR-10-LOCAL binding statements or as an adjacent block).
- Into PR 10 test module docstrings.
- Into PR 10 commit message bodies.

PR 10 unit tests assert the commitment mechanically: at
least one test verifies that two records differing only in
field ordering produce a divergent report (i.e., the
comparator does not silently sort).

### 4.3 `DivergenceReport` — structured value with authorship preservation

**Structural posture (exact shape = PR 10 spec):**

- **Structured value, not opaque.** Callers can inspect the
  report's fields directly; the report is not a handle to
  internal state. Hashable / equality-comparable primitives
  preferred; nested dicts acceptable.
- **Per-surface partitioning structurally identifiable.**
  Each claim names whether it came from the observation
  surface or the expectation surface. Carrier #17 is
  satisfied by the field-naming discipline, not just by the
  function returning some structured value.
- **Within-surface scope.** No cross-surface discriminator
  field. PR 10 spec MAY include a chat-handler-scope marker
  for archaeology (e.g., `"surface": "chat_handler"`) but
  MUST NOT encode multi-surface semantics (per Gate 3
  framing §6.3 + §9.5).
- **Pure value semantics.** No opaque handles or live
  references; no callable or generator return; no I/O
  required to inspect any field.

**Two report-shape candidates the spec chooses between**
(framing leans toward (a)):

**(a) Per-surface nested dict.** Authorship preservation
structurally visible at the outermost dict shape:

```python
{
    "fixture_id": "fix-pr9-single-survivor",
    "expectation": {"expected_narrow": ["forge_ping"]},
    "observation": {"observed_narrow": ["forge_ping"]},
    "divergence": {"narrow_diverged": False},
}
```

The three top-level dict keys (`expectation`, `observation`,
`divergence`) **structurally enforce** the three authority
surfaces' partition in the report. The `divergence` key's
value is the comparator's interpretive claim; the
`expectation` and `observation` keys' values are the surface
contributions the comparator's claim is derived from. A
single dict access (`report["divergence"]`) gives the
comparator's whole verdict; another single access
(`report["expectation"]` or `report["observation"]`) gives
the surface contribution that informed it.

**(b) Flat surface-prefixed dict.** Authorship preservation
via field-name prefixing:

```python
{
    "fixture_id": "fix-pr9-single-survivor",
    "expected_narrow": ["forge_ping"],
    "observed_narrow": ["forge_ping"],
    "narrow_diverged": False,
}
```

Flatter for assertion ergonomics in tests; slightly less
structurally enforced (field names carry the partition, not
the dict structure). Per-surface fields prefixed with
`expected_` or `observed_`; comparator claims prefixed with
`*_diverged` or similar.

**(c) Dataclass.** Same posture as (a) but typed:

```python
@dataclass(frozen=True)
class DivergenceReport:
    fixture_id: str
    expectation: ExpectationSnapshot
    observation: ObservationSnapshot
    divergence: DivergenceClaim
```

Provides IDE-discoverable type information; slightly more
ceremony for tests.

**Framing default lean: (a).** Reasoning:

- Carrier #17 is satisfied at the **outer dict structure**,
  not just at field-name level — the partition is the most
  visible thing in the report.
- (b)'s field-name discipline is fragile: a future spec
  amendment could add a field with no `expected_` /
  `observed_` prefix without violating any structural test.
- (c) adds typing ceremony without adding protection
  carrier #17 requires.

PR 10 spec finalizes; PR 10 spec authors should justify in
the spec if they elect (b) or (c) over (a).

### 4.4 4th Layer 2 walker — `_COMPARE_PERMITTED_IMPORTS`

New test module: `tests/corpus/test_pr10_comparator_imports.py`
(exact name = PR 10 spec).

**Walker shape (Option A per Gate 3 framing §8.2):**

```python
_COMPARE_PERMITTED_IMPORTS: frozenset[str] = frozenset({
    # exact set finalized in PR 10 spec; framing-level
    # expectation: 0 to 2 symbols max.
    # Likely candidates if validation needs them:
    #   "forge_bridge.corpus._schema._KNOWN_RECORD_KINDS"
    #   "forge_bridge.corpus._schema._OBSERVATION_REQUIRED_KEYS"
    # If validation uses string literals, the frozenset is empty.
})
```

**Walker discipline (parallel to PR 8 + PR 9 walkers):**

- **Value-locked frozenset.** Adding a symbol requires
  explicit framing-level redline (analogous to PR 8 walker's
  5-symbol bounded toolbox lock and PR 9 walker's single-
  symbol-gate lock).
- **Walker scoped to `_compare.py` only.** No expansion of
  the target set without framing-level review.
- **Rejection message names protected property:**
  > "comparator is interpretive read-only authority;
  > emission/persistence imports are rejected at the spec
  > layer. The 4th walker preserves the three-walker
  > partition's parallel-not-extension boundary —
  > read-only-interpretive ontology is distinct from
  > production-import-topology, orchestration-participation,
  > and fixture-data-discipline ontologies."
- **Walker module docstring** carries carrier #17 + Gate-3-
  LOCAL form + closing sentence: *"Shared AST mechanics do
  not imply shared ontology"* (echoing PR 9 walker's
  protection — Gate 2 close §1.6).

**Two regression tests (analogous to PR 8 + PR 9 walker
test pattern):**

1. **`test_compare_permitted_imports_value_locked`** —
   asserts `_COMPARE_PERMITTED_IMPORTS == expected_frozenset`
   verbatim. Adding/removing symbols requires explicit test
   update + framing-level review.
2. **`test_compare_module_references_subset_of_permitted_imports`**
   — walks `_compare.py` AST; rejects any `forge_bridge.corpus.<X>`
   import outside the permitted set.

### 4.5 PR-10-LOCAL binding statement — read-only mutability invariant

Per §5.6. Travels into `_compare.py` function docstring +
PR 10 test module docstrings + PR 10 commit message bodies.
Does NOT regenerate beyond PR 10 scope per PR-N-LOCAL non-
regeneration rule (Gate 2 framing §3.1).

---

## 5. Binding decisions

### 5.1 Module name locked: `_compare.py`

Per §2.2 reasoning. Sibling of existing corpus modules.
PR 10 spec does NOT revisit. Alternative names
(`_correlate.py`, `_diverge.py`, `_compose.py`, `_join.py`)
explicitly rejected at framing per §2.2 enumeration.

### 5.2 Function shape locked: pair-input, pure-functional, structured return

Per §4.2. The shape is locked at framing; PR 10 spec
finalizes:

- Exact function symbol name (working reference: `compare`).
- Exact parameter names (working references: `observation_record`,
  `expectation_record`).
- Exact return type symbol.
- Exception type for validation failures.

PR 10 spec MAY NOT change the shape:

- NOT batch-input (corpus or list of records).
- NOT join-internal (caller does the join).
- NOT async.
- NOT a method on a class.
- NOT optional-arg with default fallback.

### 5.3 No persistence, no async, no class, no subsystem

Echoes Gate 3 framing §5.3 + §5.4 at PR 10 scope:

- **No persistence.** No third `record_kind`; no sidecar
  file; no log emission; no I/O.
- **No async.** Comparator is pure computation over loaded
  records; no concurrency benefit.
- **No class.** Function is the minimum-topology shape.
- **No subsystem.** No strategy pattern, no plugin registry,
  no configuration object.

### 5.4 Layer 2 walker: Option A locked — 4th walker

Per §4.4 + Gate 3 framing §8.2. PR 10 spec finalizes the
walker's exact test file name, frozenset contents, and
rejection message text. Option B (extend PR 4 walker target
set) explicitly rejected at framing.

### 5.5 Test count target — 5 to 7 new tests at PR 10

Framing-time estimate (exact count = PR 10 spec):

| Test category | Estimated count |
|---|---|
| 4th walker discipline tests (value-lock + subset-enforcement) | 2 |
| Comparator unit tests (one per PR 9 fixture) | 3 |
| Authorship-preservation tests | 1–2 |

**Total PR 10 framing target: 5–7 new tests.**

**Cumulative test count anchor at PR 10 close target: 212–214
forge env corpus tests** (207 PR 9 baseline + 5–7 PR 10).
Exact count locked at PR 10 spec and verified at PR 10 close.

Per `feedback_counts_are_archaeology_grade`, count
inconsistencies are rejected at PR 10 spec review. If the
spec lands at 4 or 8+ tests, the spec author must amend the
framing-time estimate range with archaeology.

### 5.6 PR-10-LOCAL binding statement — read-only mutability invariant

> **The comparator function is structurally incapable of
> mutating its inputs or producing side effects. The
> signature returns a new structured value; the inputs are
> read but never modified; no I/O is invoked; no module-
> level state is held across calls. Tests assert input
> records remain byte-identical after the function returns.**

This is the operational discipline statement protecting
carrier #17 + §5.3 at the function level. Structurally
parallel to PR 7-LOCAL pairs (scope-local to `_capture.py`
+ `reader.py`) and PR 8-LOCAL binding statements (scope-
local to `_seed.py` + `emit_seed_expectation`).

**Operational placement of PR-10-LOCAL:**

- `_compare.py` function docstring (verbatim).
- PR 10 test module docstrings (paraphrased: *"tests assert
  the comparator does not mutate its inputs and produces no
  side effects"*).
- PR 10 commit message bodies under "preserved invariants."
- At least one PR 10 unit test asserts the invariant
  mechanically (e.g., assert `deepcopy(obs) ==
  obs_after_compare`).

PR-10-LOCAL does NOT regenerate beyond PR 10 scope. PR 11 /
PR 12 / Gate 4 / future-gate work does not inherit PR-10-
LOCAL; new PR-N-LOCAL statements may be authored as their
own PR-scope discipline statements per the canonicalized
pattern.

### 5.7 No public-API change at PR 10

`forge_bridge.__all__` stays at 19 symbols. Comparator
surface is corpus-internal at PR 10 per Gate 3 framing
§5.5. If a concrete external consumer surfaces during
PR 11 / Gate 4 work, promotion to `__all__` is a framing-
level decision at that point (per PR 8 framing §5.6 Q5 +
PR 9 framing §5.6 Q6 pattern).

---

## 6. Constructs intentionally resistant to cleanup pressure

The 9 inherited cleanup-pressure-resistance class members
(Gate 2 close §1.4) preserve unchanged. PR 10 framing does
**NOT speculatively author new members** at framing time.

### 6.1 Likely surface candidates during PR 10 implementation

Per §3.6, the three PR 10-relevant cleanup pressure forms
(helper merger / persistence creep / walker abstraction) are
most likely to surface. The protections already operational
at PR 10 entry:

- Carrier #17 + member #7 + member #8 protect against
  helper merger / inline emission attempts.
- §5.3 + §5.6 + §7 item 1 protect against persistence
  creep.
- §3.3 + §7 item 18 + Gate 2 close §2.4 item 5 protect
  against walker abstraction.

### 6.2 Discipline at PR 10 implementation

**If a cleanup pressure form surfaces:**

1. **Reject inline** at the rejection site (commit body or
   in-flight discussion).
2. **Cite the protection** that rejects it (carrier #17,
   member #7/#8/#9, framing §5/§7, or three-walker
   partition).
3. **Register at PR 10 close** as either:
   - Operational corroboration of an existing class member
     (no new member; the existing member proved load-bearing
     under this specific pressure).
   - A new candidate class member 10+ (only if the pressure
     form is structurally distinct from the 7 enumerated
     forms + the existing 9 class members; cluster
     "promotion-from-precursor" archaeology with the new
     member's per-PR close protection summary).

### 6.3 Speculative authoring rejected

Per Gate 3 framing §7 item 13. **Framing does not author
new class members at framing time** even when likely surface
candidates can be predicted. The discipline gate:

- Predicted pressure ≠ encountered pressure. The predictive
  enumeration (§3.6 + §6.1) is operational arming, not
  authorial proof.
- New members register at the per-PR close based on
  archaeological evidence (the specific commit / discussion
  / line of code where the pressure surfaced + the specific
  protection that rejected it).
- Promotion of any new class member to gate-level inventory
  happens at Gate 3 close, not at PR 10 close.

---

## 7. Non-acquisition commitments

PR 10 explicitly does **NOT**:

1. **Persist divergence reports.** No third `record_kind`,
   no sidecar artifact, no comparator-authored persistence
   (§5.3).
2. **Mutate observation or expectation records.** Per §5.6
   PR-10-LOCAL binding statement.
3. **Trigger upstream emission.** `_compare.py` imports no
   emission helpers; 4th walker enforces.
4. **Batch records or orchestrate iteration.** Pair-input is
   locked (§5.2). Caller handles join.
5. **Author cross-surface comparator semantics.** Path B
   locked at Gate 3 framing §5.1 + §5.2; PR 10 inherits.
6. **Modify the PR 9 three-fixture corpus.** Per Gate 3
   framing §7 item 4.
7. **Modify the three-authority-surface partition.** Per
   Gate 3 framing §7 item 5.
8. **Modify the PR-INTERNAL three-way authority partition.**
   Per Gate 3 framing §7 item 6.
9. **Touch the Layer 3 lint** (`test_pr6_visual_asymmetry.py`).
   Comparator is not an emission surface.
10. **Modify `divergence_capture_enabled()` or its env-gate.**
    Carrier #5 protection preserves.
11. **Extend `KNOWN_SOURCE_VALUES`.** Per Gate 3 framing §7
    item 9.
12. **Extend `_KNOWN_RECORD_KINDS`.** Two-element set locked
    per PR 7 spec §7 close conditions.
13. **Modify the expectation record schema.** Three required
    keys (`fixture_id`, `prompt`, `expected_narrow`) locked.
14. **Modify `forge_bridge.__all__`.** Stays at 19 symbols
    (§5.7).
15. **Author new cleanup-pressure-resistance class members
    speculatively.** Per §6.
16. **Promote candidate carrier #16 to active.** Promotion
    gated on Gate 3 close evaluation per Gate 3 framing
    §6.1. PR 10 contributes Gate-3-LOCAL form travel as
    corroboration substrate, but does NOT promote at PR 10
    close.
17. **Ship a join helper or batch-orchestration function.**
    Per §5.2. Pair-input is locked. PR 12 may revisit if
    join boilerplate proliferates across 4+ call sites.
18. **Generalize the 4th walker into a parametrized base
    class.** Per §3.3 + Gate 2 close §1.6 + §2.4 item 5.
    Walker unification rejected.
19. **Use cross-surface vocabulary in field names or
    docstrings.** Per Gate 3 framing §5.6. Field names like
    `task_outcome`, `prompt_resolution` rejected at PR 10
    spec review.
20. **Implement a `DivergenceReport` shape that loses
    authorship.** Per carrier #17. Reducing to `{matched:
    bool}` without preserving observed-vs-expected partition
    rejected at spec layer.

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST` mechanical extension

`tests/corpus/test_pr3_discipline.py::_ALLOWLIST` extends
with one entry:

```python
# in _ALLOWLIST:
"forge_bridge/corpus/_compare.py",
```

Allowlist semantics unchanged: only files inside
`forge_bridge/corpus/` and the explicit allowlist may import
from `forge_bridge.corpus`. The comparator module is inside
the corpus package, so locality holds; the allowlist
extension is mechanical.

### 8.2 Layer 2 — 4th walker introduction (Option A)

Per §4.4 + §5.4. New test file (name finalized in PR 10
spec) + `_COMPARE_PERMITTED_IMPORTS` frozenset + 2 regression
tests.

Walker shape locked at framing:

- Frozenset value-locked (size 0–2 expected; exact contents
  = PR 10 spec).
- Walker scoped to `_compare.py` only.
- Rejection ontology: **read-only-interpretive authority**
  (emission/persistence imports rejected).
- Module docstring carries carrier #17 + Gate-3-LOCAL form +
  *"Shared AST mechanics do not imply shared ontology"*
  protection echo.

### 8.3 Layer 3 — unchanged

`test_pr6_visual_asymmetry.py` ships unchanged into PR 10.
The comparator is not an emission surface; Properties A–D do
not govern it. The lint's discovery walk (`_find_emit_call_sites`)
finds calls to `emit_divergence_capture` only and is
unaffected by `_compare.py` additions.

---

## 9. Phase-end conditions for PR 10

PR 10 closes when:

1. **The comparator surface is operational.**
   `forge_bridge/corpus/_compare.py` exists. The pair-input
   pure-functional function accepts (observation_record,
   expectation_record) and returns a structured
   `DivergenceReport` preserving authorship per carrier #17.

2. **Pair-input shape is locked at the function level.** No
   batch-input variant, no async variant, no class method
   variant ships in `_compare.py`.

3. **`DivergenceReport` shape preserves authorship.** Per-
   surface partitioning structurally identifiable; exact
   shape per PR 10 spec lands and verifies under PR 10's
   authorship-preservation tests.

4. **Layer 1 allowlist** extends mechanically;
   `test_pr3_discipline.py` passes.

5. **Layer 2 4th walker** ships per Option A:
   - `_COMPARE_PERMITTED_IMPORTS` frozenset value-locked.
   - Walker scoped to `_compare.py`.
   - Value-lock regression test passes.
   - Subset-enforcement test passes.

6. **Carrier #17 holds.** The comparator's output shape
   preserves each authority surface's authorship; no
   interpretive-synthesis collapse landed.

7. **Gate-3-LOCAL governing sentence traveled verbatim**
   through ≥3 PR 10 surfaces (`_compare.py` module docstring
   + ≥1 PR 10 test module docstring + ≥1 PR 10 commit
   message body). This contributes ≥3 of the ≥4 surface
   count Gate 3 close evaluation requires (Gate 3 framing
   §6.1 criterion 1). Remaining ≥1 surface contributed by
   PR 11.

8. **The 16 active carriers + candidate #16 Gate-3-LOCAL
   form + 2 binding framing clarifications + proactive
   scope guardrail + PR-10-LOCAL binding statement** all
   travel verbatim into `_compare.py` module docstring per
   relevance-by-file ordering.

9. **PR-10-LOCAL binding statement** (§5.6) lives in
   `_compare.py` function docstring + PR 10 test module
   docstrings + PR 10 commit message bodies. Does NOT
   regenerate beyond PR 10.

10. **Test count locks at PR 10 close target** (212–214
    forge env corpus tests; exact count = PR 10 spec; verify
    at PR 10 close).

11. **0 production source file modifications** outside the
    new `forge_bridge/corpus/_compare.py` file. Architectural
    success signal continuity from PR 9.

12. **`forge_bridge.__all__`** stays at 19 symbols.

13. **Three-authority-surface partition + PR-INTERNAL three-
    way authority partition + 9-member cleanup-pressure-
    resistance class** all preserve unchanged.

14. **Three-walker Layer 2 partition expands to four-walker
    partition** with parallel-not-extension boundary
    preserved (each walker protects a distinct ontology;
    shared AST mechanics do not imply shared ontology).

15. **Any new cleanup-pressure-resistance class members
    surfaced during PR 10** register at PR 10 close with
    explicit protection language + operational enforcement
    placement (§6.2).

16. **`A.5.3.2-PR10-CLOSE.md` artifact ships** at the PR 10
    final commit. Structure mirrors PR 9 close (per Gate 3
    framing PR 11 deliverables note — Gate 3 close ships at
    PR 11; PR 10 close ships at PR 10 final commit).

---

## 10. Cross-references

- `A.5.3.2-GATE-3-FRAMING.md` (`2f70cbf`) — **immediate
  predecessor; the gate-level inheritance contract PR 10
  operates against.** §2 objective + scope guardrail; §3
  architectural inheritance; §4 architectural delta; §5
  binding decisions; §6 carrier delta; §8.2 Layer 2 walker
  decision; §10 PR sequencing.
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — gate-arc
  synthesis; §1 cross-PR composition; §2.1 Gate 4
  comparator's two foundational dependencies (record_kind
  partition + fixture_id joinability) operationally verified
  at PR 9 Step 4 — PR 10 inherits as unblock; §2.4 non-
  revisitable decisions.
- `A.5.3.2-PR9-CLOSE.md` (`a6e42f0`) — three-fixture corpus
  PR 10 consumes; §1.1 fixture corpus + grounding traces;
  §1.3 grounding-time amendment archaeology (PR 10 expects
  to surface a similar variant when the divergence report
  shape grounds against the actual observation/expectation
  record fields); §2.4 the authored/observed divergence
  proof case (`fix_no_keyword_match` — PR 10 unit tests will
  verify the comparator surfaces this divergence as a
  structured report claim).
- `A.5.3.2-PR8-CLOSE.md` (`b102010`) — authored expectation
  surface; `emit_seed_expectation` + `drive_seed_fixture` +
  schema validator; member #7 (companion records as truth-
  partitioning) + member #8 (`emit_seed_expectation` as
  semantics-not-topology) protect against PR 10 cleanup
  pressure forms 1 + 4.
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — observation +
  dispatch-provenance surfaces; carrier #14;
  `_KNOWN_RECORD_KINDS` 2-element lock; members #1–#6
  inherited unchanged into PR 10.
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  observation helper; PR 10 reads its **output records**
  (persisted observation records via reader), not its
  helper.
- `forge_bridge/corpus/_seed.py::emit_seed_expectation` —
  expectation helper; PR 10 reads its **output records**
  (persisted expectation records via reader), not its
  helper.
- `forge_bridge/corpus/_seed.py::drive_seed_fixture` —
  fixture orchestrator; PR 10 does NOT invoke. PR 11
  integration tests invoke (via the PR 9 fixture corpus)
  and pass resulting records to PR 10's comparator.
- `forge_bridge/corpus/reader.py` — JSONL reader; PR 10
  comparator may consume the reader for type hints or
  helper functions; exact import set = PR 10 spec; 4th
  walker enforces the closure.
- `forge_bridge/corpus/_compare.py` (planned, PR 10) — the
  comparator module.
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` —
  Layer 1; extends in PR 10 (mechanical).
- `tests/corpus/test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS`
  — Layer 2 (PR 4 walker); preserves unchanged.
- `tests/corpus/test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS`
  — Layer 2 (PR 8 walker); preserves unchanged.
- `tests/corpus/test_pr9_fixture_discipline.py::_FIXTURE_PERMITTED_IMPORTS`
  — Layer 2 (PR 9 walker); preserves unchanged.
- `tests/corpus/test_pr10_comparator_imports.py` (planned,
  PR 10) — Layer 2 (4th walker, Option A); scoped to
  `_compare.py`.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3;
  ships unchanged into PR 10.
- `tests/corpus/fixtures/fix_single_survivor.py` — PR 9
  fixture; PR 10 comparator unit tests consume.
- `tests/corpus/fixtures/fix_multi_match.py` — PR 9 fixture;
  PR 10 comparator unit tests consume.
- `tests/corpus/fixtures/fix_no_keyword_match.py` — PR 9
  fixture; PR 10 comparator unit tests verify the comparator
  surfaces the authored/observed divergence (`expected_narrow
  = []` vs. `observation.narrower.decision = full-4-tool-set`)
  as a structured report claim.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion-
  candidate methodology seed; PR 10 contributes:
  - Gate-3-LOCAL governing sentence travel corroboration for
    candidate carrier #16 (≥3 of ≥4 surfaces required for
    Gate 3 close promotion evaluation per Gate 3 framing
    §6.1).
  - Potentially a fourth Step N.5 surgical cadence
    corroboration instance if mid-flight guidance surfaces.
  - Potentially candidate cleanup-pressure-resistance class
    member 10+ at PR 10 close if a new pressure form
    surfaces under genuinely independent recomposition
    conditions.

---

PR 10 framing locks here. PR 10 spec drafts at the next
session boundary; PR 10 implementation derives from that
spec per the Gate 2 cadence (PR 7 + PR 8 + PR 9 framing →
spec → implementation pattern).
