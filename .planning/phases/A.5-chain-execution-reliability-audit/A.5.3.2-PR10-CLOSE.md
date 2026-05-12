# A.5.3.2 PR 10 — Close (comparator helper + structural protection)

**Status:** Durable archival state. PR 10 is the first of two
(or conditionally three) PRs sequenced within Gate 3 per Gate 3
framing §10. The implementation arc that began at framing
commit `8ad7fe9` (2026-05-11) closes at this commit.

PR 10 ships the **comparator helper** as a single pair-input,
pure-functional read surface in `forge_bridge/corpus/_compare.py`,
governed by carrier #17's recomposition-preserves-authorship
discipline. The deliverable carries the **Gate-3-LOCAL governing
sentence** as candidate-carrier-#16 corroboration substrate
through 8 PR 10 surfaces — significantly above the ≥3 threshold
the Gate 3 close evaluation reads.

**Cross-artifact responsibility split (Gate 3 scope):**

- **PR 10 close (this artifact)** owns the PR 10 implementation
  arc, the four architectural signals named at session close,
  the candidate cleanup-pressure-resistance class member 10
  four-criterion evaluation, and the PR 11 inheritance contract
  at PR-level.
- **Gate 3 close** (ships at PR 11 final commit per Gate 3
  framing §11) will own the gate-arc synthesis across PR 10 +
  PR 11, candidate carrier #16 promotion evaluation (≥4
  surfaces), conditional PR 12 disposition, and the gate-level
  inheritance contract toward Gate 4.

No section of this artifact pre-empts Gate 3 close's gate-arc
synthesis. Where overlap surfaces, this artifact defers.

---

## 1. What PR 10 established

### 1.1 Comparator helper operational end-to-end

PR 10 ships `forge_bridge/corpus/_compare.py` (523 lines) — a
single pair-input, pure-functional read surface that consumes
one observation record + one expectation record and returns a
structured divergence report preserving each authority surface's
contribution explicitly.

| Symbol | Shape | Authority class |
|---|---|---|
| `compare_records(observation_record: dict, expectation_record: dict) -> DivergenceReport` | Pair-input, pure-functional | Interpretive read-only |
| `DivergenceReport: TypeAlias = dict[str, Any]` | Per-surface nested dict (option (a) per spec §4.1.4) | Pure value |
| `class ComparatorInputError(ValueError)` | Authority-class misuse exception (§4.1.5) | Misuse signaling |

The function body (per spec §4.1.6 reference implementation,
landed at Step 3 commit `00f4d75`) executes four authority
pre-checks raising `ComparatorInputError` on misuse, then
performs the divergence computation as **direct list equality**
on the persisted record contents. No sort, no canonicalization,
no semantic coercion — the §4.2 binding behavioral commitment
(*"compare as persisted"*) rejects each of those operations at
the function-body layer; tests 5 mechanically asserts the
sort-rejection vector.

The report's per-surface nested-dict shape **structurally
enforces** carrier #17 at the outermost dict structure: three
top-level keys (`expectation`, `observation`, `divergence`)
partition the report into the two surface contributions + the
comparator's interpretive claim. Authorship is not merely
preserved by field-name discipline — it is preserved by the
report's outer geometry.

The module is structurally incapable of:

- Mutating its inputs (test 4 mechanically asserts via
  `copy.deepcopy` defense-in-depth assertions).
- Triggering upstream emission (the 4th walker enforces zero
  corpus imports; Layer 2 closure is mechanical).
- Persisting state (no writer imports; no I/O; no module-level
  mutable state).
- Holding state across calls (the function is pure).

These properties hold at three layers: type signature (pair-
input function returning a structured value); module imports
(`_COMPARE_PERMITTED_IMPORTS = frozenset()` value-locked at
zero symbols); function body discipline (PR-10-LOCAL binding
statement asserted by test 4).

### 1.2 Four architectural signals — user-named, load-bearing for archaeology

The PR 10 implementation arc surfaced four architectural signals
the user named explicitly at session close. They are load-
bearing for the close artifact's retrospective synthesis because
they encode the **meaning** of the PR 10 outcome rather than the
mechanics.

#### Signal 1 — the §4.4 amendment sharpened Layer 1 semantics

The `_ALLOWLIST` amendment at commit `6830888` did not merely
correct a mistake. It **sharpened Layer 1 semantics** by
surfacing the actual contract — corpus-subtree auto-exclusion
+ named-integration-call-site admission — that the framing/spec
had inferred imprecisely.

The framing §8.1 + spec-original §4.4 called for a one-line
`tests/corpus/test_pr3_discipline.py::_ALLOWLIST` extension
adding `_compare.py` as a "mechanical extension." Grounding
against the actual discipline test (lines 92–96 of
`test_pr3_discipline.py`) at Step 1 implementation prep revealed
the corpus subtree is auto-excluded BEFORE the allowlist check
fires. Adding `_compare.py` to `_ALLOWLIST` would have been
mechanically inert AND semantically misleading: future
contributors would read `_compare.py` in `_ALLOWLIST` as an
integration call site like `console/handlers.py` /
`console/_step.py`, diluting the allowlist's discriminating
purpose.

The corrected reading the amendment installs:

> `_ALLOWLIST` is for files **outside** the corpus subtree that
> need to import **from** the corpus — the integration call
> sites. Corpus-internal modules are blanket-permitted by
> location and NEVER appear in `_ALLOWLIST`.

This is the kind of amendment that creates clarity rather than
just removing error. The framing inferred allowlist semantics
rather than reading the test implementation; the amendment
realigned spec language with operational topology AND produced
a sharper articulation of the discipline itself. The amendment
archaeology at spec §4.4 (full rewrite, side-by-side spec-
original / amendment-corrected table) is the durable record.

#### Signal 2 — `_COMPARE_PERMITTED_IMPORTS` survived as `frozenset()` through Step 3

The zero-symbol-gate lock survived implementation. Step 3 is
where Layer 2 locks typically erode — the architectural-center
pressure to "just import `_KNOWN_RECORD_KINDS` for validation"
or "import `_OBSERVATION_REQUIRED_KEYS` for the required-fields
pre-check" is real and predictable. The §4.1.7 amendment trigger
language was operationally arming: if the reference
implementation required corpus imports, the spec would amend.
It did not.

The reference implementation at `_compare.py:321–520` uses
**string literals** for `record_kind` equality checks
(`"observation"` / `"expectation"`) and **dict-path traversal**
for the required-fields pre-check (`observation_record.get(...)`).
No corpus-module imports were structurally necessary; the
zero-symbol-gate held vacuously against the post-Step-3
`_compare.py` and continues to hold through Step 4 + Step 5.

This is a major success signal. The framing-time prediction
(framing §4.4 + spec §4.1.7 amendment trigger language) was
operationally load-bearing rather than ornamental. The Layer 2
4th walker passes mechanically against an actual zero-corpus-
imports module body.

#### Signal 3 — 0 production source modifications outside `_compare.py` held through comparator body landing

The architectural-success-signal continuity from PR 9 → PR 10
is the clearest evidence so far that the decomposition strategy
is **real rather than aspirational**. PR 9 achieved the 0-mod
signal with test-surface-only work. PR 10 achieved it with the
comparator body landing — substantive production code that
could have plausibly required touching adjacent surfaces:

- **`_schema.py`** for `_KNOWN_RECORD_KINDS` set-membership
  validation.
- **`reader.py`** for record-shape type hints.
- **`_capture.py`** for observation-record-shape inspection.
- **`_seed.py`** for expectation-record-shape inspection.

None of those modifications were needed. The comparator's
authority-class pre-checks + dict-path traversal + fresh-list-
allocation report construction stayed self-contained within
the new module:

```
$ git diff --stat 8ad7fe9..HEAD -- forge_bridge/
 forge_bridge/corpus/_compare.py | 523 +++++++++++++++++++++++
 1 file changed, 523 insertions(+)
```

This is the architectural-success-signal continuity from PR 9 →
PR 10 the framing called out as a goal (not just a happy
outcome) per Gate 3 framing §11 criterion 11 + PR 10 spec §1.
PR 10 hit the goal.

#### Signal 4 — 8-surface Gate-3-LOCAL travel is demonstrated discipline, not accidental corroboration

8 PR 10 surfaces traveled the Gate-3-LOCAL governing sentence
verbatim with explicit *candidate carrier #16 corroboration
substrate* marking:

| # | Surface | Step | Commit |
|---|---|---|---|
| 1 | `forge_bridge/corpus/_compare.py` module docstring | Step 1 | `3b75a1b` |
| 2 | Step 1 commit body | Step 1 | `3b75a1b` |
| 3 | `tests/corpus/test_pr10_comparator_discipline.py` module docstring | Step 2 | `a4be3d7` |
| 4 | Step 2 commit body | Step 2 | `a4be3d7` |
| 5 | `tests/corpus/test_pr10_comparator.py` module docstring | Step 3 | `00f4d75` |
| 6 | Step 3 commit body | Step 3 | `00f4d75` |
| 7 | Step 4 commit body | Step 4 | `68a6a28` |
| 8 | Step 5 commit body | Step 5 | `d04753c` |

The asymmetric ordering — active carrier #17 primary, Gate-3-
LOCAL form secondary with substrate marking — preserved at
every site. PR 10 wrote *"16 active carriers + candidate #16"*
verbatim across every relevant artifact; nowhere wrote *"17
active carriers"* or *"carriers #1–#17."*

This is no longer accidental corroboration. It is a
**demonstrated travel discipline** — the framing's discipline
intent (Gate 3 framing §6.1 evaluation criterion 1) operationally
held under implementation pressure across 5 distinct file
surfaces and 4 distinct commit bodies. PR 11 contributes the
remaining ≥1 surface; the ≥4 total surface count the Gate 3
close evaluation requires (Gate 3 framing §6.1) is on the
verge of being significantly exceeded.

**Promotion to carrier #16 is NOT performed at PR 10 close.**
Per Gate 3 framing §6.1 + spec §0 + framing §3.10: promotion
evaluation happens at Gate 3 close (PR 11), reading the
≥4-surface evidence base PR 10 + PR 11 cumulatively contribute.
This artifact preserves the candidate-substrate marking
discipline; Gate 3 close performs the evaluation.

### 1.3 Default disposition held — §4.3.3 canonicalization trigger NOT fired

PR 10 spec §4.3.3 defined a conditional 6th test
(`test_compare_records_does_not_canonicalize_inputs`) that
would ship IF the §4.1.6 reference implementation introduced
pre-comparison string processing — lowercasing, whitespace
strip, Unicode normalization, list-comprehension transforms.
The trigger evaluation at Step 3 commit body (`00f4d75`) read:

> NOT triggered. The reference implementation uses direct list
> equality with no pre-comparison string processing (no
> lowercasing, no whitespace strip, no Unicode normalization,
> no list-comprehension string transforms). The canonicalization
> vector is structurally unreachable. Default disposition
> holds.

The default disposition held all the way through PR 10 close.
The conditional 6th test is NOT shipped at PR 10; the
canonicalization vector remains structurally unreachable per
the §4.1.6 reference implementation.

PR 10 closes at **5 comparator tests + 2 walker tests = 7 PR 10
named tests total** — exactly the default-disposition count
spec §5 + framing §5.5 projected. Default disposition is a
non-trivial discipline outcome: it required not introducing
even one line of string processing into the body when the
"obvious" instinct (lowercase tool names to be lenient about
casing differences) would have introduced one.

### 1.4 Test count anchor — 214 forge env collected (exact default-disposition target)

PR 10 close test count arithmetic (per spec §5.3 archaeology-
grade):

```
207 baseline   (PR 9 close §1.6 forge env collected)
+   2 PR 10 discipline tests (Step 2)
+   3 PR 10 unit tests (Step 3)
+   2 PR 10 authorship-preservation tests (Step 4)
= 214 forge env collected at PR 10 close
```

**Step 5 verification re-confirmed (and re-verified at close):**

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
214 tests collected in 0.07s
```

PR 10 ships **7 named tests** (5 comparator + 2 discipline);
named == collected (no parametrize per spec §5 + framing §5.5).
The named-equals-collected identity is structurally locked by
the per-fixture-hand-written test pattern + the absence of
parametrization across the 5 comparator tests.

**Forge-bridge env count:** 6-test gap inherited from PR 7
(`project_v1_4_x_harness_debt.md`: starlette TestClient +
asyncpg loop conflict + Project-seeding fixture gap). Target
at PR 10 close: **201 baseline + 7 new = 208 forge-bridge env
collected.** Not re-verified at PR 10 close beyond inheritance
documentation — the 6-test gap is PR 7-scope, not PR 10-scope.
**Do not conflate the two env counts.**

**Test inventory at PR 10 close:**

| # | Test | File | Step |
|---|---|---|---|
| 1 | `test_compare_permitted_imports_value_locked` | `test_pr10_comparator_discipline.py` | 2 |
| 2 | `test_compare_module_references_subset_of_permitted_imports` | `test_pr10_comparator_discipline.py` | 2 |
| 3 | `test_compare_records_single_survivor_no_divergence` | `test_pr10_comparator.py` | 3 |
| 4 | `test_compare_records_multi_match_no_divergence` | `test_pr10_comparator.py` | 3 |
| 5 | `test_compare_records_no_keyword_match_divergence` | `test_pr10_comparator.py` | 3 |
| 6 | `test_compare_records_does_not_mutate_inputs` | `test_pr10_comparator.py` | 4 |
| 7 | `test_compare_records_does_not_sort_inputs` | `test_pr10_comparator.py` | 4 |

### 1.5 Four-walker Layer 2 partition operational

At PR 10 close, **four Layer 2 AST walkers** operate against
the codebase. Each protects a distinct ontology. The
protections are partitioned, not unified:

| Walker | Target | Ontology |
|---|---|---|
| PR 4 (`test_pr4_participation_creep.py`) | narrowing-subsystem production sources | production-import-topology (one-directional flow) |
| PR 8 (`test_pr8_seed_surface.py`) | `_seed.py` | orchestration-participation (5-symbol bounded toolbox) |
| PR 9 (`test_pr9_fixture_discipline.py`) | `tests/corpus/fixtures/*.py` | declarative-fixture-data (single-symbol-gate) |
| **PR 10 (`test_pr10_comparator_discipline.py`)** | **`_compare.py`** | **read-only-interpretive authority (zero-symbol-gate)** |

The four walkers **share AST mechanics** (each uses `ast.walk`
+ import-node traversal); they **do NOT share ontology**.
Generalization would require unifying:

- Target-set semantics (production sources vs. seed-driver-
  internal vs. fixture-test vs. interpretive-read-only).
- Admission ontologies (one-directional flow vs. bounded
  toolbox vs. single-symbol-gate vs. zero-symbol-gate).
- Rejection-message shape.
- Future evolution pressure.

Per Gate 2 close §1.6 + §2.4 item 5 + PR 10 spec §4.2.1:
**"Future walker unification cleanup proposals are rejected at
the spec layer."** The closing sentence — *"Shared AST mechanics
do not imply shared ontology."* — lands at the PR 10 walker
module docstring per Step 2 commit body, echoing PR 9's
protection.

### 1.6 Read-side structural parallel to the PR-8-INTERNAL write-side partition

PR 8 spec §4.1.5.1 introduced an explicitly framing-governed
PR-INTERNAL three-way authority partition at the write side:
authored expectation semantics / orchestration semantics /
persistence topology. The partition was named at framing, spec-
declared, rejection-tested at §7, and mechanically enforced
across the `_seed.py` surface.

PR 10's `_compare.py` body, examined retrospectively, exhibits
a **structural parallel** at the read side — but as **emergent
architectural archaeology**, NOT as a framing-governed partition
of equivalent authority class to PR 8's:

| Read-side surface | Sub-shape |
|---|---|
| Authority pre-checks (`_compare.py:330–410` approx) | Misuse-signaling |
| Divergence computation (`_compare.py:410–480` approx) | Interpretive read-only |
| Report construction (`_compare.py:480–520` approx) | Pure value composition |

**Why this is a parallel, not a peer-class partition:**

- PR 8's partition was **explicitly named at framing**, spec-
  declared, rejection-tested, and mechanically enforced (§7
  rejection rows protect against collapse).
- PR 10's three-stage read-side shape was **not framing-named
  as a partition**. The §4.1.6 reference implementation produced
  the three-stage structure as a function of the operational
  task (validate inputs → compute divergence → construct
  report) — the structure is natural to the work, not a
  governance-class architectural construct.

The PR 8 write-side partition is **declared architecture with
mechanical enforcement**. The PR 10 read-side shape is
**observed architecture with archaeological value**. The
distinction matters because:

- Future PRs cannot point to "PR 10's read-side partition" as a
  named rule to invoke or extend.
- Future framings designing comparable read surfaces have a
  prior example to consider (the §4.1.6 reference implementation
  shape worked), but no inherited governance constraint.
- The shape may or may not recur at PR 11 / Gate 4 read
  surfaces; if it does, framing-level naming may then promote
  it to a peer-class partition. PR 10 close does not pre-empt
  that decision.

The pattern of authority-class sub-shapes at each authority-
surface module is becoming visible across PR 7 / PR 8 / PR 10.
PR 9 ships without one (data + one orchestration call), which
itself argues against treating this as a universal rule. The
right framing at PR 10 close is: **two governance-class
write-side partitions exist (PR 7 + PR 8); one read-side
structural parallel exists (PR 10). Promotion of the parallel
to peer-class governance is a future-framing decision.**

### 1.7 The candidate cleanup-pressure-resistance class member 10 — four-criterion evaluation

PR 10 implementation surfaced one candidate class member 10+
for explicit four-criterion evaluation at this close per the
user direction recorded at the [[project_state_2026_05_11_pr_10_implementation_closed]]
cursor.

**Discipline statement (candidate member 10):**

> **Imports land when first used. Reserved imports for
> hypothetical future cases are rejected at the spec layer,
> matching the compare-as-persisted discipline applied at the
> import-set surface.**

**Manifested at two distinct sites during PR 10:**

1. **§4.1.2 amendment at spec drafting time.** The original
   draft of `_compare.py` carried `import copy  # noqa: F401 —
   reserved for future fresh-allocation cases`. User direction
   rejected the speculative-reserved import from the production
   module: reserved imports conflict with the §4.2 binding
   behavioral commitment + the PR-10-LOCAL binding statement
   (the function does what its signature claims; no held-back
   capability). The amendment landed at spec §4.1.2 before
   Step 1 implementation; the production module never carried
   the speculative import.
2. **Step 3 imports discipline at `test_pr10_comparator.py`
   (commit `00f4d75`).** Spec §4.3.1's final-state imports
   inventory listed `import copy` + `import pytest` +
   `ComparatorInputError` + `DivergenceReport`. Step 3
   implementation rejected the speculative imports per the
   same discipline: imports land when used, not when listed.
   `import copy` was added at Step 4 (`68a6a28`) when test 4
   first deepcopy'd inputs; `import pytest`,
   `ComparatorInputError`, and `DivergenceReport` remain
   un-imported at PR 10 close because the default-disposition
   5 tests never use them.

#### Four-criterion evaluation (per user direction)

The user direction (verbatim) for the close-time evaluation
named four criteria:

> * was there genuine cleanup pressure?
> * did the protection prevent a real erosion path?
> * did it recur independently?
> * did it require active enforcement rather than passive
>   preference?

**Criterion 1 — genuine cleanup pressure?** **YES.** The
"reserve imports for future use" pattern is a recurring
designer instinct — speculative provisioning for cases the
designer can imagine but the spec does not require. The
framing-level draft of `_compare.py` carried the speculative
`import copy` as deliberate ergonomic provisioning, NOT as
oversight. The Step 3 test imports recurrence (independent
of the spec-level amendment) confirms the pressure surfaces
empirically.

**Criterion 2 — did protection prevent a real erosion path?**
**YES.** Without the user's §4.1.2 intervention, the
production module would have shipped with `import copy  #
noqa: F401`, establishing a precedent for speculative imports
in future corpus modules. The precedent would have been
load-bearing: the next corpus module would have read the PR 10
shape as authorizing speculative imports; the pattern would
have proliferated by quiet imitation. The intervention
prevented the precedent from forming AND established the
discipline statement that operates at PR 10 close.

**Criterion 3 — did it recur independently?** **YES.** Two
distinct manifestation sites at two distinct surfaces:

- The spec amendment (`6830888` — production module surface).
- The Step 3 imports discipline (`00f4d75` — test module
  surface).

Independence verified: the Step 3 discipline was applied to a
different file (`test_pr10_comparator.py`) under the same
rationale but without re-invocation of the §4.1.2 user
intervention. The discipline was operative at Step 3
implementation prep AS DISCIPLINE — installed, internalized,
and applied without re-derivation.

**Criterion 4 — did it require active enforcement rather than
passive preference?** **YES.** The user actively intervened
to reject the §4.1.2 draft (passive preference would have
allowed the speculative import to ship). The Step 3 commit
body explicitly notes the deviation from spec §4.3.1's import
list with the same rationale as §4.1.2 — the discipline
required explicit articulation at the deviation site, NOT
silent omission. Test 4 (`import copy`) and Step 5 (no further
imports added) confirmed the boundary: imports added when
mechanically needed; nothing added speculatively.

#### Disposition: PROMOTE to numbered class member 10

All four criteria are met. The candidate qualifies for
promotion to numbered cleanup-pressure-resistance class
member 10.

**Promotion-from-precursor archaeology:**

The closest existing class member is **none** — member 10 is
genuinely new. The closest existing **cleanup-pressure form**
(unnumbered, enumerated at Gate 3 framing §4.2 + framing §3.6)
is **form #5 (premature surface normalization)**. Both reject
designing-for-hypothetical-future-cases:

- Form #5 operates at the **data comparison surface** —
  rejects "lowercase tool names before comparison; future
  case-insensitive comparison might want it."
- Member 10 operates at the **import-set surface** — rejects
  "reserve `import copy` for future fresh-allocation cases."

The two are **structural siblings** but **distinct members**.
Form #5 is a cleanup-pressure form (enumerated, not promoted);
member 10 is a class member (numbered, durable). The class
member status is warranted because:

- The protection mechanism is distinct (compare-as-persisted
  applied at the import-set surface vs. compare-as-persisted
  applied at the comparison surface).
- The operational placement is distinct (§4.1.2 spec amendment
  discipline + Step-N imports discipline at test modules vs.
  §4.2 binding behavioral commitment at function body).
- The recurrence at two distinct sites during PR 10 satisfies
  the "recurred independently" criterion the class member
  threshold requires.

Member 10's relationship to form #5 is archaeology, not
identity. The two travel under a common "compare-as-persisted"
generalization, but they protect different operational
surfaces; future contributors should read both.

**Member 10 protection (verbatim, scope-local to PR 10 surface
+ available as discipline at any subsequent corpus module
authoring):**

> **Imports land when first used. Reserved imports for
> hypothetical future cases are rejected at the spec layer,
> matching the compare-as-persisted discipline applied at the
> import-set surface.**

**Operational placement of the protection:**

- Spec §4.1.2 amendment archaeology (the production-module
  rejection).
- Step 3 imports discipline at `test_pr10_comparator.py` (the
  test-module rejection).
- Step 5 commit body cleanup-pressure-resistance archaeology
  section.
- This close artifact §1.7.

**Class final inventory at PR 10 close (10 members):**

| # | Member | PR | Protection |
|---|---|---|---|
| 1 | Helper duplication | PR 7 | Framing §6 + spec §7 close conditions |
| 2 | Visual asymmetry / Properties A–D | PR 6 | Layer 3 lint |
| 3 | Intentionally inert structural parameters | PR 7 | §4.2 binding pair + test enforcement |
| 4 | Always-present `fixture_id` field on observation records | PR 7 | Builder dict structure + test enforcement |
| 5 | Nested-not-unconditional synthesis form in reader | PR 7 | §5.5 binding pair + test enforcement |
| 6 | Inline I-6 wrapper duplication in `_persist_expectation_record` | PR 7 | Inline pattern + Step 8 spec |
| 7 | Companion records as truth-partitioning | PR 8 | `_seed.py` docstring + framing §6.1 + schema validator branch rejection |
| 8 | `emit_seed_expectation` as semantics-not-topology | PR 8 | `_seed.py` + helper docstrings + framing §6.2 + Layer 2 `_SEED_PERMITTED_IMPORTS` value-lock |
| 9 | Fixture-surface-data-discipline | PR 9 | Fixture module docstrings + framing §6.1 + Layer 2 `_FIXTURE_PERMITTED_IMPORTS` value-lock + PR 9 walker |
| **10** | **Speculative-reserved-imports rejection (import-set compare-as-persisted)** | **PR 10** | **Spec §4.1.2 amendment + Step-N imports discipline + framing §3.6 form #5 sibling archaeology** |

The class is now demonstrably populatable across **four
reliability phases (PR 6 + PR 7 + PR 8 + PR 9 + PR 10)** under
genuinely independent conditions. Promotion of the **class
itself** to `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` is
strengthened by the fourth independent populating PR, but the
gate-level promotion decision lives at Gate 3 close — this
artifact contributes the per-PR archaeology, not the
methodology-promotion verdict.

#### What did NOT surface as cleanup pressure during PR 10

The framing-time enumeration at framing §3.6 named three most-
likely-to-surface forms:

- **Form 1 (helper merger)** — "Just have the comparator emit
  a divergence record while reading the input pair." Did NOT
  surface. The pair-input pure-functional shape + the §5.3
  no-persistence lock + member #8 protection held without
  test.
- **Form 3 (persistence creep)** — "The comparator could write
  the report to a sidecar file." Did NOT surface. The §5.3 +
  §5.6 + Layer 2 walker zero-symbol-gate held without test.
- **Form 7 (walker abstraction)** — "The 4th walker shares
  ~80% AST mechanics with PR 8 + PR 9; DRY into a parametrized
  base class." Did NOT surface. The Step 2 walker landed as a
  parallel implementation; the Gate 2 close §2.4 item 5 +
  framing §3.3 protection held without test.

**The absence of surfacing is itself archaeological evidence
that the framing-level protections held without operational
test.** The framing's predictive enumeration was operational
arming, not authorial proof. The three protections were on
watch; PR 10's zero-symbol-gate + zero-prod-mod-outside-
`_compare.py` + pair-input lock are evidence that the
protections shaped decisions even when no overt pressure arose.

This is a structural observation worth preserving: **at PR 10,
framing-time pressure prediction was load-bearing through
absence rather than through rejection.** The implementation
arc shaped itself around the predicted-pressure topology
without needing to reject any specific pressure event.

### 1.8 Cumulative architectural concentration — Step 3 as architectural-center

Unlike PR 9's cumulative concentration across Steps 3 + 4
(framing/joinability proof centers, complementary), PR 10's
architectural concentration sits **singularly at Step 3**:

- **Step 3 (`00f4d75`)** — **Architectural-center.** Lands the
  comparator body (per §4.1.6 reference implementation) + the
  3 unit tests (one per PR 9 fixture). Bundled atomic commit:
  the tests need the implemented body; the body without tests
  is unprovable. Full three-round review applied (Gate 2
  framing §5.7 integration-work elevation; PR 10's
  architectural-center is the carrier #17 operational landing).
  ~100 lines of function body + ~430 lines of test surface.

Step 4 (authorship-preservation tests) and Step 5 (verification)
build on Step 3 but do not constitute additional architectural
centers. Step 3's discipline + the carrier #17 operational
landing carry the architectural weight.

The PR 9 cumulative-concentration framing remains the right
framing for **multi-step proof surfaces** (Gate 4 comparator-
unblock proof at PR 9 Steps 3 + 4). The PR 10 single-center
framing is the right framing when the architectural commitment
lands at one atomic boundary (the comparator body + its 3
fixture-driven unit tests). Both framings are operationally
correct at their respective PRs; neither generalizes
prescriptively to future PRs.

---

## 2. What PR 11 / Gate 3 inherits from PR 10

### 2.1 The comparator helper as consumption surface

`forge_bridge/corpus/_compare.py` ships as a stable consumption
surface:

- `compare_records(observation_record, expectation_record) ->
  DivergenceReport` — single function, pair-input, pure-
  functional.
- `DivergenceReport: TypeAlias = dict[str, Any]` — per-surface
  nested dict shape per spec §4.1.4 option (a).
- `class ComparatorInputError(ValueError)` — authority-class
  misuse exception.

The surface is **immutable at PR 10 close** within Gate 3
scope:

**What PR 11 / Gate 3 must NOT do:**

- Modify `compare_records` signature (no batch-input variant,
  no async variant, no class method variant; pair-input lock
  preserves).
- Modify `DivergenceReport` shape (per-surface nested dict
  partition preserves; field-name discipline preserves).
- Add a third `record_kind` value (`KNOWN_SOURCE_VALUES` + the
  two-element observation/expectation lock preserve).
- Inline a writer call into `compare_records` (carrier #17 +
  member #8 + §5.3 reject; cleanup-pressure form 1 protection
  active).
- Add I/O to the comparator (cleanup-pressure form 3 protection
  active; PR-10-LOCAL invariant asserts via test 4).
- Promote `compare_records`, `DivergenceReport`, or
  `ComparatorInputError` to `forge_bridge.__all__` at PR 11
  (corpus-internal scope at PR 10 per spec §5.7; promotion is
  a framing-level decision per the PR 8 framing §5.6 Q5 +
  PR 9 framing §5.6 Q6 pattern, NOT a PR 11 implementation
  decision).

**What PR 11 may consume:**

- Call `compare_records` against pairs of records read from
  capture JSONL (the comparator is the read surface PR 11
  integration tests will exercise).
- Inspect `DivergenceReport` field-by-field for assertion
  ergonomics (the report's nested dict shape is structurally
  visible to callers; no opaque handles).
- Catch `ComparatorInputError` to verify misuse-signaling
  pre-checks (the four authority pre-checks are mechanically
  testable from PR 11's test surface).

### 2.2 The four-walker Layer 2 partition

PR 4 + PR 8 + PR 9 + PR 10 walkers operate against the codebase
at PR 10 close. PR 11 inherits all four walkers + the
parallel-not-extension boundary:

- **`_COMPARE_PERMITTED_IMPORTS`** value-locked at 0 symbols.
  Any admission of a first symbol requires explicit framing-
  level review per PR 10 spec §4.1.7 amendment trigger
  language.
- **PR 10 walker** scoped to `_compare.py` only. Any expansion
  of the target set (e.g., to include PR 11 integration tests
  or future comparator helper modules) requires framing-level
  review.
- **Parallel-not-extension boundary** preserves intact (four
  distinct ontologies; shared AST mechanics do not imply
  shared ontology). Future "walker unification" proposals
  rejected at the spec layer per Gate 2 close §1.6 + §2.4
  item 5 + PR 10 spec §4.2.1.

### 2.3 Carrier #17 + Gate-3-LOCAL governing sentence

PR 10 ships carrier #17 (active) at the top of `_compare.py`
module docstring per relevance-by-file ordering. The Gate-3-
LOCAL governing sentence carries the *candidate carrier #16
corroboration substrate* marking at 8 PR 10 surfaces.

PR 11 inherits:

- **Carrier #17 verbatim travel** at PR 11 surfaces (consuming
  the comparator + writing integration tests against the PR 9
  fixture corpus + PR 10 comparator).
- **Gate-3-LOCAL governing sentence verbatim travel** with
  candidate-substrate marking at PR 11 surfaces (≥1 PR 11
  surface contributes to the ≥4 total Gate 3 close evaluates).
- **The 16-active-carriers + candidate-#16 accounting
  discipline.** PR 11 must NOT write "17 active carriers" or
  "carriers #1–#17"; correct phrasing is "16 active carriers
  + candidate #16" (per Gate 3 framing §6 binding accounting +
  PR 10 framing §3.1).

### 2.4 The §4.2 binding behavioral commitment + the four operational rejections

The "compare as persisted" commitment + its four operational
rejections (sort / canonicalize / repair / semantic) preserve
intact at PR 10 close:

> **The comparator compares authored and observed records as
> persisted. It does not normalize, reorder, canonicalize,
> repair, or semantically coerce either surface before
> comparison.**

PR 11 must NOT:

- Modify `_compare.py` to introduce any pre-comparison string
  processing (would fire the §4.3.3 trigger that PR 10's
  default disposition kept unfired).
- Wrap `compare_records` in a normalization layer at any
  PR 11 surface (the "compare as persisted" commitment is
  load-bearing — a normalization layer at the caller would
  defeat the commitment by silently sorting/lowercasing the
  inputs before invocation).
- Add a "lenient" variant of `compare_records` at PR 11 (the
  pair-input shape + carrier #17 reject lenient-mode
  proliferation).

### 2.5 The PR-10-LOCAL read-only mutability invariant

PR-10-LOCAL ships scope-local to PR 10 surfaces per the PR-N-
LOCAL non-regeneration rule:

> **The comparator function is structurally incapable of
> mutating its inputs or producing side effects. The signature
> returns a new structured value; the inputs are read but
> never modified; no I/O is invoked; no module-level state is
> held across calls. Tests assert input records remain
> byte-identical after the function returns.**

The invariant is **non-regenerating** beyond PR 10. PR 11 /
PR 12 / Gate 4 work does not inherit PR-10-LOCAL; new PR-N-
LOCAL statements may be authored at framing level as their
own PR-scope discipline statements per the canonicalized
pattern. The invariant continues to apply to the comparator
function itself (the implementation is what it is; test 4
mechanically asserts it forever); the statement itself does
not regenerate as a discipline carrier into PR 11 test
modules.

### 2.6 The candidate cleanup-pressure-resistance class member 10

Member 10's **promotion to the numbered class** is finalized
at this close per §1.7. The protection statement is available
as discipline at any subsequent corpus module authoring:

> **Imports land when first used. Reserved imports for
> hypothetical future cases are rejected at the spec layer,
> matching the compare-as-persisted discipline applied at the
> import-set surface.**

PR 11 inherits the discipline. Specifically: PR 11 integration
tests should follow the same imports-land-when-used pattern at
their test module(s). Any speculative-reserved imports in PR 11
test modules surface as a member-10-violation check at PR 11
implementation prep.

### 2.7 The 7-commit PR 10 chain as reseed reference

PR 10 ships as a 7-commit chain (spec + amendment + 5 steps;
§4 enumerates). PR 11 should:

- Read this close artifact §1 + §2 + §4 for the durable
  archival state.
- Read the spec amendment commit (`6830888`) for the §4.4
  amendment archaeology (sharpened Layer 1 semantics).
- Read the Step 3 commit body (`00f4d75`) for the
  architectural-center reference implementation rationale.
- Read the Step 5 commit body (`d04753c`) for the full PR 10
  verification archaeology + the eight-surface Gate-3-LOCAL
  travel inventory.
- Defer to **Gate 3 close** (ships at PR 11 final commit) for
  gate-arc synthesis, candidate carrier #16 promotion
  evaluation, conditional PR 12 disposition.

---

## 3. What PR 11 / Gate 3 changes

PR 11 is not yet framed. Gate 3 framing §10 sequencing names
PR 11 as the second of two (or conditionally three) PRs within
Gate 3.

### 3.1 Deferred to PR 11 framing

PR 11's scope is undefined at PR 10 close. Likely Gate 3 work
surfaces will include (NOT binding; speculative):

- **End-to-end integration tests** consuming PR 9 fixtures +
  PR 10 comparator. The PR 9 integration test infrastructure
  (`_apply_pr9_patches`, `_PR9_REACHABLE_TOOLS`, `_read_records`)
  is reusable per PR 9 close §2.2; PR 11 may build on it.
- **PR 11 contributes the remaining ≥1 surface** for the ≥4
  total Gate-3-LOCAL surface count Gate 3 close evaluates
  (PR 10 contributed 8; PR 11 needs only 1 for the ≥4
  threshold to be substantively exceeded).
- **Conditional join helper at PR 12** if PR 11 surfaces
  evidence that join boilerplate appears at 4+ call sites in
  Gate 3 + Gate 4 + future-gate work (per PR 10 framing §2.1).
  PR 12 disposition is a Gate 3 close decision, NOT a PR 11
  implementation decision.

Gate 3 close §2 (ships at PR 11 final commit) will carry the
full Gate 4 inheritance contract at gate-level. This section
defers to Gate 3 close for the gate-level inheritance contract.

### 3.2 What does NOT change at PR 11 / Gate 3

Regardless of PR 11's specific deliverables, the following
PR 10 outcomes are **permanent archaeology**:

- **The three PR 9 fixtures + the PR 10 comparator helper**
  ship as stable archaeology. Any modification requires
  framing-level review.
- **The four-walker partition** preserves intact (PR 4 / PR 8
  / PR 9 / PR 10; parallel-not-extension).
- **The corrected `_ALLOWLIST` semantics** (per §4.4 amendment)
  preserve operational; no future PR may add `_compare.py` or
  any other corpus-subtree file to `_ALLOWLIST`.
- **The 16 active carriers + candidate #16 accounting discipline**
  preserves intact. PR 11 must NOT write "17 active carriers"
  or "carriers #1–#17"; promotion of candidate #16 is gated on
  Gate 3 close evaluation.
- **PR 7-LOCAL pairs + PR 8-LOCAL binding statements + PR 9
  fixture-data discipline + PR-10-LOCAL** continue NOT to
  regenerate beyond their scope-local placement.
- **The PR-8-INTERNAL three-way authority partition** (write-
  side §4.1.5.1) preserves intact as framing-governed
  architecture. The PR 10 read-side structural parallel (§1.6)
  preserves as emergent architectural archaeology; not peer-
  class governance.
- **The cleanup-pressure-resistance class** at 10 members is
  the durable inventory at PR 10 close. Future PRs may add
  members; existing 10 members are unchanged.
- **`forge_bridge.__all__`** stays at 19 symbols. Comparator
  surface (`compare_records`, `DivergenceReport`,
  `ComparatorInputError`) remains corpus-internal at PR 10
  per spec §5.7.
- **0 production source modifications outside `_compare.py`**
  remains the PR 10 closure signal validating PR 7 + PR 8 +
  PR 9 decomposition; future Gate 3 + Gate 4 surfaces inherit
  the validation.

---

## 4. Step-by-step archaeology — 7-commit PR 10 chain

PR 10's implementation arc is 7 commits, beginning at framing
commit `8ad7fe9` (2026-05-11; logged in PR 10 framing landing
artifact, not in this chain) and closing at this commit + the
close-artifact commit (next).

| # | Commit | Type | Step | Lines | Cumulative |
|---|---|---|---|---|---|
| 1 | `54d0ab9` | Spec | (pre-step) | +2780 | 2780 |
| 2 | `6830888` | Spec amendment 2026-05-11 (grounding-time variant; earlier catch than PR 9) | (pre-Step-1) | +152 net | 2932 |
| 3 | `3b75a1b` | Step 1 — `_compare.py` skeleton (single-file) | Step 1 | +417 | 3349 |
| 4 | `a4be3d7` | Step 2 — 4th Layer 2 walker (`test_pr10_comparator_discipline.py`) | Step 2 | +340 | 3689 |
| 5 | `00f4d75` | Step 3 — architectural-center (comparator body + 3 unit tests) | Step 3 | +430 net (+106 prod / +324 test) | 4119 |
| 6 | `68a6a28` | Step 4 — 2 authorship-preservation tests (mutation + sort rejection) | Step 4 | +141 (test only) | 4260 |
| 7 | `d04753c` | Step 5 — final verification (empty; archaeology in body) | Step 5 | 0 | 4260 |

**Step archaeology — methodology contributions per commit:**

- **Spec** (`54d0ab9`) — Six symbol-level decisions finalized
  + spec §0 17-sentence carrier travel inventory + Step 1–5
  atomic boundaries + 13-item Step 5 verification checklist.
- **Spec amendment** (`6830888`) — **Grounding-time variant of
  the amendment-at-incarnation cluster, earlier catch than
  PR 9.** PR 9 §4.7 amendment fired at Step 2 implementation
  post-Step-1 commit (`627b104`); PR 10 §4.4 amendment fired
  at Step 1 implementation **prep** (read-before-implement
  before any modification landed). The earlier catch is the
  `feedback_ground_specs_in_actual_files` discipline operating
  at the right cadence. The amendment realigned spec language
  with `_ALLOWLIST`'s operational topology and produced a
  sharpened articulation of the discipline (Signal 1 above).
  See §5.1 for the variant taxonomy update.
- **Step 1** (`3b75a1b`) — `_compare.py` skeleton: module
  docstring (full 17-sentence carrier travel per spec §4.1.1
  relevance-by-file ordering) + `DivergenceReport` TypeAlias
  + `ComparatorInputError` class + `compare_records` function
  signature with `NotImplementedError` body pending Step 3.
  417 lines; bulk is the carrier-travel docstring infrastructure.
  Architectural success signal verified at Step 1: exactly one
  production source file addition; zero modifications elsewhere.
- **Step 2** (`a4be3d7`) — 4th Layer 2 walker. New test module
  `test_pr10_comparator_discipline.py` (340 lines) with
  `_COMPARE_PERMITTED_IMPORTS: frozenset[str] = frozenset()`
  zero-symbol-gate + walker scoped to `_compare.py` + 2
  regression tests (value-lock + subset-enforcement). The
  four-walker Layer 2 partition becomes operational at Step 2;
  the parallel-not-extension boundary preserves intact across
  PR 4 + PR 8 + PR 9 + PR 10. Walker passes vacuously against
  Step 1's zero-corpus-imports `_compare.py` skeleton.
- **Step 3** (`00f4d75`) — **Architectural-center.** Bundled
  atomic commit: comparator body (per §4.1.6 reference
  implementation; ~100 lines) + 3 unit tests in
  `test_pr10_comparator.py` (one per PR 9 fixture; ~320 lines
  including 2 builder helpers + module docstring). Full
  three-round review applied per Gate 2 framing §5.7
  integration-work elevation. The §4.3.3 canonicalization
  trigger evaluated **NOT triggered**: the reference
  implementation uses direct list equality with zero
  pre-comparison string processing; default disposition
  locks. Carrier #17 operational landing.
- **Step 4** (`68a6a28`) — 2 authorship-preservation tests
  (mutation invariant + sort rejection). Test 4 uses
  `copy.deepcopy` defense-in-depth to assert PR-10-LOCAL; test
  5 asserts the §4.2 binding behavioral commitment's sort-
  rejection vector mechanically. `import copy` lands at Step 4
  per the member 10 imports-land-when-used discipline. PR 10
  contribution at end of Step 4: 5 comparator tests + 2 walker
  tests = 7 named tests; **214 forge env collected** (exact
  default-disposition target).
- **Step 5** (`d04753c`) — Final verification. Empty commit;
  13-item verification checklist + 17-sentence carrier
  travel + Gate-3-LOCAL 8-surface travel inventory +
  architectural success signal verification + spec amendment
  archaeology + cleanup-pressure-resistance archaeology +
  PR 10 commit chain summary in commit body. No new code.
  The Step 5 commit body is the durable archaeology source
  for the PR 10 implementation arc (alongside this close
  artifact).

**Step N.5 surgical cadence:** **NOT triggered at PR 10.**
Unlike PR 9 (which corroborated the pattern twice within a
single PR arc — Step 2.5 + Step 5.5), PR 10 did not surface
mid-flight guidance requiring surgical N.5 commits. The
pattern is available; PR 10 simply did not need it. The 3-
times-corroborated promotion status from PR 9 close §5.2
preserves intact (PR 8 Step 4.5 + PR 9 Step 2.5 + PR 9
Step 5.5); PR 10 adds no fourth corroboration.

---

## 5. Methodology observations surfaced during PR 10

### 5.1 The grounding-time amendment variant — earlier catch than PR 9

PR 10 contributes a **second instance** to PR 9's grounding-
time amendment variant (PR 9 close §5.1). The earlier catch
relative to PR 9 is the methodology contribution:

| PR | Amendment | Catch point | Catch cadence |
|---|---|---|---|
| PR 9 | §4.7 amendment 2026-05-11 (`2c7a2ca`) | Step 2 implementation post-Step-1 (`627b104`) | Surfaced at empirical inspection of `_tool_filter.py` during fixture authoring |
| **PR 10** | **§4.4 amendment 2026-05-11 (`6830888`)** | **Step 1 implementation PREP (before any modification landed)** | **Surfaced at read-before-implement of `test_pr3_discipline.py:92–96`** |

The PR 10 earlier catch is the `feedback_ground_specs_in_actual_files`
discipline operating at the right cadence. PR 9's catch
required the framing/spec to be partially implemented before
the empirical misalignment surfaced; PR 10's catch surfaced at
the read-before-implement step BEFORE any modification entered
the codebase.

**Methodological observation:** the discipline matures by the
catch point getting earlier. The first PR's grounding-time
amendment catches at Step 2 implementation; the second PR's
grounding-time amendment catches at Step 1 prep. Future
reliability phases reading existing test/source surfaces
empirically at framing/spec drafting time can plausibly catch
grounding-time amendments at the framing stage (before any
spec text drafts) — but the catch cadence is not
prescriptively predictable, and the discipline gate is
read-before-extrapolate at every framing/spec assertion.

**The variant's four-variant taxonomy continues unchanged:**

1. Drafting-time amendments (PR 7 + PR 8 spec §4.5).
2. Implementation-time amendments (PR 8 §1.3 cluster #5–#7).
3. Verification-time amendments (PR 8 Step 4.5).
4. **Grounding-time amendments (PR 9 §4.7 + PR 10 §4.4)** —
   now 2-instance corroborated.

Gate 2 close §5 + Gate 3 close will own the cross-PR taxonomy
inventory. This section names PR 10's specific contribution
(the earlier catch within the grounding-time variant) and
defers to Gate 3 close for the gate-level synthesis.

### 5.2 Cumulative-architectural-concentration framing — single-center vs. multi-step

PR 9 close §5.3 canonicalized the cumulative-architectural-
concentration framing for **multi-step proof surfaces** (PR 9
Steps 3 + 4 = Gate 4 comparator-unblock proof surface). PR 10
contributes a contrast case: a **single-center architectural
concentration** at Step 3 (per §1.8 above).

**Methodological observation:** the cumulative-concentration
framing is the right framing when a PR's architectural
commitment requires multiple atomic boundaries to land
(framing/joinability; substrate/binding; collect/synthesize).
The single-center framing is the right framing when the
architectural commitment lands at one atomic boundary (the
comparator body + its 3 fixture-driven unit tests).

**Both framings are operationally correct at their respective
PRs.** Neither generalizes prescriptively. Future PR framings
should evaluate per-PR whether the architectural concentration
is single-center or multi-step based on the work's structural
shape, not by analogy to prior PRs.

The two framings travel together as an emerging taxonomy:

- **Single-center** (PR 10 Step 3) — one atomic boundary
  carries the architectural commitment.
- **Cumulative multi-step** (PR 9 Steps 3 + 4) — multiple
  atomic boundaries compose into a proof surface.

Gate 3 close + future Gate-level synthesis may promote this
to a named methodology distinction; PR 10 close registers the
contrast without promoting.

### 5.3 Framing-time pressure prediction as load-bearing through absence — candidate methodology observation

PR 10 framing §3.6 enumerated three most-likely-to-surface
cleanup-pressure forms (helper merger / persistence creep /
walker abstraction). **None of the three actually surfaced
during PR 10 implementation.**

**Candidate methodology observation (first corroborated
instance):** the predictive enumeration was operational arming
— the protections were on watch — and the implementation arc
shaped itself around the predicted-pressure topology without
needing to reject any specific pressure event. PR 10 exhibits
framing-time pressure prediction as load-bearing through
**absence** rather than through **rejection**.

This is a structural contrast with PR 7 and PR 8, where
framing-time enumeration was load-bearing through **rejection**
at specific commit-body sites:

- PR 8 cluster #5–#7 amendments rejected helper-merger /
  inline-emission pressure at specific implementation-time
  surfaces.
- PR 7 §4.5 amendments rejected drafting-time pressure
  similarly.

**Posture: candidate, not canonicalized.** The PR 10 instance
is the **first corroborated occurrence** of the absence-as-
load-bearing pattern. A single instance is not yet enough to
canonicalize the observation as methodology. Promotion to a
named pattern requires:

- At least one additional independent corroborating PR where
  framing-time enumeration predicts pressure that does NOT
  subsequently surface during implementation.
- Evidence that the absence is **shaped by** the framing-level
  protection (the framing was the cause), distinct from
  absence due to unrelated factors (the framing happened to
  enumerate forms that the implementation happened not to
  need).

**Why this distinction matters:** PR 10's success signal was
not *"we rejected creep during implementation"* — it was
*"the framing predicted the pressure precisely enough that
the creep never materialized."* That is materially different
from the earlier cleanup-pressure cases at PR 7 + PR 8, and
worth preserving as candidate observation. But generalizing
from one instance to a methodology law would be premature.

The candidate observation is registered in this artifact for
future archaeology. Gate 3 close + future reliability phase
framings may revisit when an independent corroborating
instance surfaces.

### 5.4 Pointer to Gate 3 close — full cross-PR synthesis

PR 10 close §5 names PR 10's specific methodology
contributions:

- The grounding-time amendment's **earlier catch** within the
  variant (§5.1).
- The **single-center vs. cumulative multi-step**
  architectural-concentration contrast (§5.2).
- **Framing-time pressure prediction load-bearing through
  absence** (§5.3).

The complete cross-PR synthesis lives at Gate 3 close (ships
at PR 11 final commit). Gate 3 close will own:

- Complete 4-variant amendment-at-incarnation taxonomy with
  PR-of-origin noted per variant (PR 7 + PR 8 + PR 9 + PR 10).
- Complete cleanup-pressure-resistance class final inventory
  (now at 10 members per §1.7).
- Step N.5 surgical cadence corroboration status (3-times
  corroborated at Gate 2 close; PR 10 adds zero).
- Four-walker Layer 2 partition with all four ontologies.
- Candidate carrier #16 promotion evaluation (≥4 surfaces
  evidence base; PR 10 contributed 8; PR 11 needs ≥1 more).
- Single-center vs. multi-step architectural-concentration
  taxonomy promotion candidacy.
- Framing-time-pressure-prediction-through-absence promotion
  candidacy.

Future phase architects read **Gate 3 close**, not PR 10
close, for the cross-PR methodology synthesis.

---

## 6. Mechanical checkpoints

### 6.1 Test count anchor verification (Step 5 item 7)

```
$ python -m pytest tests/corpus/ --collect-only -q | tail -1
214 tests collected in 0.07s
```

Forge env collected: **214** ✓ (anchor matches spec §5.3
arithmetic: 207 baseline + 7 PR 10 new = 214; **exact
default-disposition target**).

Forge-bridge env not re-verified at PR 10 close; 6-test gap
inherited from PR 7 per `project_v1_4_x_harness_debt.md`.
Target at PR 10 close: 201 baseline + 7 new = 208 forge-bridge
env. Inheritance documented only.

### 6.2 PR 10 suite regression (Step 5 item 1)

```
$ python -m pytest tests/corpus/test_pr10_*.py
========================= 7 passed, 1 warning in 0.02s =========================
```

PR 10 suite: **7/7** ✓ (5 comparator + 2 walker).

### 6.3 Public API anchor (Step 5 item 9)

```
$ python -c "import forge_bridge; print(len(forge_bridge.__all__))"
19
```

`forge_bridge.__all__` count at PR 10 close: **19** ✓.

`compare_records`, `DivergenceReport`, `ComparatorInputError`
all NOT in `__all__` (comparator surface corpus-internal at
PR 10 per spec §5.7). PR 8's
`test_pr8_helpers_remain_corpus_internal` continues to enforce
mechanically.

### 6.4 PR 7 + PR 8 + PR 9 regression sweep (Step 5 item 2)

Step 5 commit body item 2: "PR 7 + PR 8 + PR 9 suites: 59/59
passed unchanged."

PR 4 + PR 5 integration tests (Step 5 commit body item 5):
13/13 passed unchanged.

PR 6 Layer 3 lint (Step 5 commit body item 3): 17/17 passed
unchanged. Zero new `emit_divergence_capture` call sites at
PR 10; lint's discovery walk input set unchanged.

PR 4 walker (Step 5 commit body item 4): 1/1 passed unchanged.
Parallel-not-extension Layer 2 boundary preserved.

PR 3 discipline (Step 5 commit body item 6): 1/1 passed
unchanged. Per §4.4 amendment 2026-05-11, no allowlist
modification needed; corpus-subtree auto-exclusion handles
`_compare.py`.

### 6.5 Production source modifications (architectural success signal)

```
$ git diff --stat 8ad7fe9..HEAD -- forge_bridge/
 forge_bridge/corpus/_compare.py | 523 +++++++++++++++++++++++
 1 file changed, 523 insertions(+)
```

**Exactly one production source file added** (`_compare.py`,
523 lines) ✓. **Zero modifications** to `_capture.py`,
`_seed.py`, `_schema.py`, `_sources.py`, `_identity.py`,
`_topology.py`, `reader.py`, or any other production source.

Architectural success signal continuity from PR 9 preserved
per Gate 3 framing §11 criterion 11 + spec §1 + spec §9
condition 11.

### 6.6 Layer 2 four-walker partition (Step 5 item 13)

All four walkers operational at PR 10 close:

- PR 4 walker (`test_pr4_participation_creep.py`) — production-
  import-topology — 1/1 passing.
- PR 8 walker (`test_pr8_seed_surface.py`) — orchestration-
  participation — 5/5 passing.
- PR 9 walker (`test_pr9_fixture_discipline.py`) — declarative-
  fixture-data — 2/2 passing.
- **PR 10 walker (`test_pr10_comparator_discipline.py`) —
  read-only-interpretive authority — 2/2 passing.**

`_COMPARE_PERMITTED_IMPORTS = frozenset()` at zero symbols ✓.
Walker target set: `forge_bridge/corpus/_compare.py` only ✓.
Parallel-not-extension boundary preserved across all four
walkers ✓.

### 6.7 Gate-3-LOCAL travel verification (Step 5 item 11)

Gate-3-LOCAL governing sentence ("Gate 3 proves topology, not
infrastructure.") traveled verbatim through **8 PR 10 surfaces**
with explicit *candidate carrier #16 corroboration substrate*
marking (per §1.2 Signal 4 table).

≥3 threshold required for Gate 3 close evaluation: **significantly
exceeded.** PR 11 contributes the remaining ≥1 surface for the
≥4 total surface count Gate 3 close reads.

### 6.8 Carrier travel verification (Step 5 item 10)

Carrier #17 + Gate-3-LOCAL form land at all 3 PR 10 source
surfaces (per spec §0 site list):

- `forge_bridge/corpus/_compare.py` module docstring ✓.
- `tests/corpus/test_pr10_comparator_discipline.py` module
  docstring ✓.
- `tests/corpus/test_pr10_comparator.py` module docstring ✓.

Proactive scope guardrail lands at `_compare.py` +
`test_pr10_comparator.py` per spec §0 site #4 contract; the
discipline test module does not require it per the
abbreviation discipline at §0 site #3.

§4.2 binding behavioral commitment + PR-10-LOCAL travel
verbatim at `_compare.py` module docstring + function
docstring + paraphrased at `test_pr10_comparator.py` module
docstring per spec §0 site #4 contract ✓.

---

## 7. Reseed protocol — what the next session does with this artifact

When PR 11 framing session opens:

1. **Read this PR 10 close artifact first.** §1 + §2 + §4 are
   the load-bearing sections.

2. **Read the spec amendment commit body** (`6830888`) for the
   §4.4 amendment archaeology (sharpened Layer 1 semantics;
   the corpus-subtree auto-exclusion + named-integration-call-
   site admission contract).

3. **Read the Step 3 commit body** (`00f4d75`) for the
   architectural-center reference implementation rationale.
   The §4.3.3 canonicalization trigger evaluation lives here.

4. **Read the Step 5 commit body** (`d04753c`) for the full
   PR 10 verification archaeology including the 8-surface
   Gate-3-LOCAL travel inventory + the spec amendment
   archaeology + the cleanup-pressure-resistance archaeology.

5. **Re-read project memories:**
   - `project_state_2026_05_11_pr_10_implementation_closed.md`
     — supersede with PR-10-closed cursor at next session
     opening.
   - `feedback_ground_specs_in_actual_files.md` — applies to
     PR 11 framing as it did to PR 10. PR 10's §4.4 amendment
     earlier catch is the discipline operating at the right
     cadence.
   - `feedback_counts_are_archaeology_grade.md` — applies to
     PR 11 framing's test count anchors.
   - `feedback_cursor_before_retrospective_synthesis.md` — the
     cursor written between PR 10 implementation close and
     this close artifact validated this discipline.
   - `feedback_strong_recos_technical.md` — applies to PR 11
     framing decisions outside user's pipeline expertise.

6. **Gate-3-LOCAL governing sentence (verbatim,
   framing-artifact-scoped):**

   > **Gate 3 proves topology, not infrastructure.**

   Candidate carrier #16 promotion remains deferred to Gate 3
   close (ships at PR 11 final commit). PR 10 contributed 8
   surfaces of corroboration substrate; PR 11 needs only ≥1
   additional surface for the ≥4 total Gate 3 close evaluates.
   PR 11 must continue using *"16 active carriers + candidate
   #16"* phrasing verbatim; no implicit promotion at PR 11.

7. **Begin PR 11 framing.** PR 11's specific deliverables are
   undefined at PR 10 close; likely surfaces include end-to-end
   integration tests consuming PR 9 fixtures + PR 10 comparator,
   and the architectural-success-signal continuity check (if
   PR 11 ships as test-surface-only work, the 0-prod-mod
   signal continues; if PR 11 surfaces a genuine production
   need, the framing names + justifies it).

8. **Surface the framing for review** before drafting a PR 11
   spec.

9. **The cadence — framing → spec → spec-amendments-at-
   incarnation → steps → verification-amendments-if-surfaced
   → close — carries unchanged** with the four-variant
   amendment cluster (drafting-time / implementation-time /
   verification-time / grounding-time, now 2-instance
   corroborated) explicitly available to PR 11 framing as
   canonicalized methodology.

10. **The Step N.5 surgical cadence is available** for mid-
    flight cleanup commits (3-times corroborated at Gate 2
    close + PR 10 added zero; if PR 11 surfaces mid-flight
    guidance, the surgical N.5 pattern is the canonical
    response).

11. **At PR 11 close, the Gate 3 close artifact
    (`A.5.3.2-GATE-3-CLOSE.md`) ships at the same commit** per
    Gate 3 framing §11. Gate 3 close owns the candidate
    carrier #16 promotion evaluation, conditional PR 12
    disposition, gate-arc synthesis across PR 10 + PR 11, and
    the gate-level inheritance contract toward Gate 4.

---

## 8. Cross-references

- **`A.5.3.2-PR10-FRAMING.md`** (`8ad7fe9`) — binding pre-spec
  contract; §0 carrier #17 + Gate-3-LOCAL governing sentence;
  §3.6 seven canonical cleanup-pressure forms PR 10-relevant
  subset; §5 binding decisions; §6 cleanup-pressure-resistance
  framing-time prediction.
- **`A.5.3.2-PR10-SPEC.md`** (`54d0ab9` + amendment `6830888`)
  — implementation contract; §0 17-sentence carrier travel
  inventory; §4.1.6 reference implementation; §4.4 amendment
  2026-05-11 archaeology (grounding-time variant earlier catch);
  §6 Step 5 13-item verification checklist.
- **`A.5.3.2-GATE-3-FRAMING.md`** (`2f70cbf`) — gate-level
  inheritance contract PR 10 operates against; §6.1
  promotion-evaluation criteria for candidate carrier #16
  (PR 10 contributed 8 surfaces of evidence); §11 Gate 3
  close criteria.
- **`A.5.3.2-PR9-CLOSE.md`** (`a6e42f0`) — durable PR 9
  archival state PR 10 inherited; §1.1 three-fixture corpus
  (PR 10 comparator unit tests consume); §1.3 grounding-time
  amendment variant canonical entry (PR 10 contributes second
  instance + earlier catch); §1.7 architectural success
  signal continuity goal; §2.4 authored/observed divergence
  proof case (PR 10 test 3 verifies as structured
  DivergenceReport claim).
- **`A.5.3.2-GATE-2-CLOSE.md`** (`a6e42f0`) — gate-arc
  synthesis; §2.1 Gate 4 comparator's two foundational
  dependencies (record_kind partition + fixture_id
  joinability) operationally verified at PR 9 Step 4 — PR 10
  consumed as unblock; §1.6 + §2.4 item 5 four-walker
  parallel-not-extension boundary preserved.
- **`A.5.3.2-PR8-CLOSE.md`** (`b102010`) — authored expectation
  surface PR 10 reads from (via persisted records); member #7
  (companion records as truth-partitioning) + member #8
  (`emit_seed_expectation` as semantics-not-topology) protect
  against PR 10 cleanup pressure forms 1 + 4 (load-bearing
  through absence).
- **`A.5.3.2-PR7-CLOSE.md`** (`b035c87`) — observation +
  dispatch-provenance surfaces PR 10 reads from (via persisted
  records); carrier #14; `_KNOWN_RECORD_KINDS` 2-element lock
  PR 10 inherits unchanged.
- **`forge_bridge/corpus/_compare.py`** (PR 10 new, 523 lines)
  — the comparator module; `compare_records` function;
  `DivergenceReport` TypeAlias; `ComparatorInputError` class.
- **`forge_bridge/corpus/_capture.py::emit_divergence_capture`**
  — observation helper; PR 10 reads its **output records**
  (persisted observation records via reader), not its helper.
- **`forge_bridge/corpus/_seed.py::emit_seed_expectation`** —
  expectation helper; PR 10 reads its **output records**
  (persisted expectation records via reader), not its helper.
- **`forge_bridge/corpus/_seed.py::drive_seed_fixture`** —
  fixture orchestrator; PR 10 does NOT invoke. PR 11
  integration tests invoke (via the PR 9 fixture corpus) and
  pass resulting records to PR 10's `compare_records`.
- **`tests/corpus/test_pr10_comparator_discipline.py`** (PR 10
  new, 340 lines) — 4th Layer 2 walker;
  `_COMPARE_PERMITTED_IMPORTS = frozenset()`; 2 regression
  tests.
- **`tests/corpus/test_pr10_comparator.py`** (PR 10 new, 459
  lines) — 5 comparator tests (3 unit + 2 authorship-
  preservation); 2 builder helpers.
- **`tests/corpus/test_pr3_discipline.py::_ALLOWLIST`** —
  Layer 1; **NOT modified at PR 10** per §4.4 amendment 2026-
  05-11 (corpus-subtree auto-exclusion at lines 92–96 handles
  `_compare.py` blanket-style). The allowlist's actual purpose
  (integration call sites outside the corpus subtree) is now
  explicit in the spec amendment archaeology.
- **`tests/corpus/test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS`**
  — Layer 2 (PR 4 walker); preserves unchanged.
- **`tests/corpus/test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS`**
  — Layer 2 (PR 8 walker); preserves unchanged.
- **`tests/corpus/test_pr9_fixture_discipline.py::_FIXTURE_PERMITTED_IMPORTS`**
  — Layer 2 (PR 9 walker); preserves unchanged.
- **`tests/corpus/test_pr6_visual_asymmetry.py`** — Layer 3;
  ships unchanged into PR 10 (zero new
  `emit_divergence_capture` call sites; discovery walk input
  set unchanged).
- **`tests/corpus/fixtures/fix_single_survivor.py`** — PR 9
  fixture; PR 10 test 3 consumes.
- **`tests/corpus/fixtures/fix_multi_match.py`** — PR 9
  fixture; PR 10 test 4 consumes; order-preservation
  verification through `compare_records`.
- **`tests/corpus/fixtures/fix_no_keyword_match.py`** — PR 9
  fixture; PR 10 test 5 consumes; authored/observed divergence
  surfaces as structured `DivergenceReport` claim per
  carrier #17.
- **PR 10 7-commit chain** (`54d0ab9` → `d04753c`) per §4
  table.
- **Local memory updates this session:**
  - New cursor at next session opening:
    `project_state_2026_05_11_pr_10_closed.md` (will supersede
    `project_state_2026_05_11_pr_10_implementation_closed.md`).
  - `feedback_cursor_before_retrospective_synthesis.md`
    validated by the cursor cut between Step 5 commit and
    this close artifact.
  - `feedback_ground_specs_in_actual_files.md` strongly
    corroborated at PR 10 §4.4 amendment (earlier catch than
    PR 9).
- **`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`** —
  promotion-candidate methodology seed; PR 10 contributes:
  - Grounding-time amendment variant 2-instance corroboration
    (earlier catch).
  - Single-center vs. cumulative multi-step architectural-
    concentration contrast (§5.2; new at PR 10).
  - Framing-time pressure prediction load-bearing through
    absence (§5.3; **candidate observation, first corroborated
    instance — requires additional independent repetition
    before promotion to named methodology**).
  - Cleanup-pressure-resistance class fourth-PR populating
    (10 members; class promotion strengthened).
  - Gate-3-LOCAL governing sentence 8-surface travel
    corroboration for candidate carrier #16 (≥3 threshold
    significantly exceeded; PR 11 needs ≥1 more for ≥4 total).

---

End of PR 10 close. The implementation arc that began at
framing (`8ad7fe9`) closes here. The 7-commit chain ships the
comparator helper (523 lines, one file) + the 4th Layer 2
walker (340 lines, one file) + the 5 comparator tests + 2
authorship-preservation tests (459 lines, one file) + the
grounding-time amendment earlier catch (sharpened Layer 1
semantics) + the single-center architectural-concentration
contrast + the framing-time-pressure-prediction-through-absence
methodology + the candidate cleanup-pressure-resistance class
member 10 promotion + 0 production source modifications
outside `_compare.py` as the architectural-success-signal
continuity from PR 9.

The Gate-3-LOCAL governing sentence — *"Gate 3 proves topology,
not infrastructure."* — traveled through 8 PR 10 surfaces with
explicit *candidate carrier #16 corroboration substrate*
marking. The asymmetric ordering (active carrier #17 primary,
Gate-3-LOCAL form secondary with substrate marking) preserved
verbatim at every site. PR 11 contributes the remaining ≥1
surface; Gate 3 close (PR 11 final commit) performs the
promotion evaluation against the ≥4 total surface count.

PR 10 governs by one inherited active carrier:

> **Recomposition preserves authorship. The comparator joins
> observation + expectation records by `fixture_id` at read
> time; the join produces a derived view that names each
> authority surface's contribution explicitly. Cleanup pressure
> to collapse the three-authority-surface partition through
> interpretive synthesis is rejected at the spec layer.**

Carrier #17 is the architectural commitment PR 10 enacted at
the comparator's signature, the divergence report's outer
geometry, and the 4th walker's read-only-interpretive
authority ontology. The recomposition discipline holds.

**Gate 3 advances. PR 11 framing is next.**
