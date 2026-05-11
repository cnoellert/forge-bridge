# A.5.3.2 PR 9 — Framing (fixture corpus + end-to-end integration)

**Status:** Framing-stage artifact for PR 9 of Gate 2. PR 8 closed
at `b102010` on local `main` (origin synced at `ce330b3`); this
framing opens PR 9's discuss-then-spec cadence. Integration-shaped
work — full three-round review applies across the entire PR
(per Gate 2 framing §5.7 + PR 8 close §3 "what PR 9 changes").

PR 9 is the final PR of Gate 2. PR 9 close lands at the same
commit that lands `A.5.3.2-GATE-2-CLOSE.md` (per Gate 2 framing
§11.6 + PR 8 close §7 step 11).

This framing's job: name the architectural boundary PR 9
establishes (the fixture-data surface + the end-to-end
integration test surface), lock the binding decisions that were
left open at PR 8 close, introduce the new Layer 2 discipline
that protects the fixture surface against scope-creep, and
enumerate what PR 9 deliberately does NOT do. The spec derives
from this artifact; implementation derives from the spec.

---

## 0. Crystallizing sentence — PR 9 governs by one framing-level claim

PR 9 ships **one framing-level governing sentence**. Unlike PR 8's
carrier #15 (which carries verbatim into production source
modules), the governing sentence is framing-artifact-scoped — it
governs the rejection surface PR 9's spec + commits + non-
acquisition commitments live against, but does NOT travel
verbatim into production source. Promotion to a numbered carrier
(#16) is deferred to spec-time review; if spec articulation
surfaces a need to carry it verbatim into fixture module
docstrings or commit message bodies, the promotion lands then.

**PR 9 governing sentence:**

> **PR 9 proves topology, not infrastructure.**

The sentence is short by design. It is the rejection key for an
entire category of speculative scope:

- No fixture loader abstraction.
- No fixture CLI.
- No fixture registry / factory / generator.
- No parametrization framework over fixtures.
- No comparator stub.
- No expectation-schema expansion.
- No generated fixtures.
- No chain-step fixture coverage.
- No non-Python fixture formats.

Each of these is a category of scope a future PR could
locally-defend as *"trivial generalization."* The governing
sentence is the rejection-burden carrier: anyone proposing the
generalization must produce a framing-level reframing of PR 9's
purpose, not a code diff.

The protection mirrors carrier #15's third-clause governance
shape (PR 8 §0): chain-step seeding requires a dedicated framing
pass; infrastructure expansion at PR 9 requires a dedicated
framing pass. The proposing surface is framing, not
implementation.

**What "topology" means here:**

PR 9 proves that the four architectural artifacts PR 7 + PR 8
ship — `seed_dispatch_scope`, `_persist_expectation_record`,
`emit_seed_expectation`, `drive_seed_fixture` — compose
end-to-end against real arbitration with real persisted records,
under three operational outcome shapes (single-survivor /
multi-match / zero-match narrowing), with the resulting records
demonstrably partitionable by `record_kind` and joinable by
`fixture_id`. The proof is mechanical (tests pass) and
archaeological (records inspectable in the corpus JSONL file).

**What "topology" does NOT mean here:**

PR 9 does NOT prove that the architecture is *useful* — that's
Gate 4's deliverable (the comparator decides what counts as
useful divergence). PR 9 does NOT prove that the fixture surface
scales — that's PR 10+ work. PR 9 does NOT prove that the
arbitration outcomes are *correct* — narrowing decisions are
themselves arbitration outputs; PR 9 records what arbitration
decides without grading the decision.

---

## 1. Predecessors (binding, in order)

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants (I-1 through I-6).
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing; visual-asymmetry
  pattern; helper signature.
- `A.5.3.2-PR3-SPEC.md` — persistence layer; atomic-append
  discipline.
- `A.5.3.2-PR4-CLOSE.md` (`fab26cb`) — risk-category shift;
  integration-discipline quartet; PR 4 walker shape (the
  ontology PR 9's walker is explicitly **NOT** an extension of).
- `A.5.3.2-PR5-CLOSE.md` (`b8f522e`) — surface geometry
  asymmetry; chain-step integration durable archival state.
- `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — Layer 3 lint; Gate 1
  closure; truth-vs-mechanism distinction.
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — §3.4 three-authority-
  surface partitioning; §4.1 Model A; §4.4 companion records;
  §5.7 PR partitioning (**PR 9 = first fixtures + end-to-end
  integration**); §10 PR 9 deliverables; §11 Gate 2 close criteria.
- `A.5.3.2-PR7-FRAMING.md` (`1c1e061`) — §6 cleanup-pressure-
  resistance class introduction; §7 non-acquisition commitments.
- `A.5.3.2-PR7-SPEC.md` (`84392d2`) — `seed_dispatch_scope`,
  `_persist_expectation_record`, `KNOWN_SOURCE_VALUES`,
  `_KNOWN_RECORD_KINDS`; §7 phase-end rejection table.
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — durable PR 7 archival
  state; ontology constants.
- `A.5.3.2-PR8-FRAMING.md` (`23f2a20`) — §0 carrier #15
  (chat-handler-only seeding scope); §3.3 three-authority-surface
  partitioning preserved; §5 Q1–Q5 binding decisions (Q1
  in-process, Q1.5 chat-handler-only, Q2 minimum-viable record
  shape, Q3 signature lock, Q4 single-function driver, Q5
  `__all__` deferred); §6 members #7 + #8; §7 non-acquisition
  commitments.
- `A.5.3.2-PR8-SPEC.md` (`85c5bc1`) — implementation contract;
  §0 18 verbatim sentences; §4.1.5.1 PR-INTERNAL three-way
  authority partition; §4.5 four spec amendments at drafting;
  §7 phase-end conditions (rejection table — PR 9 may not propose
  any of those mutations even incidentally).
- `A.5.3.2-PR8-CLOSE.md` (`b102010`) — durable archival state
  PR 9 inherits; §2 "what PR 9 inherits from PR 8" (the 18
  verbatim sentences + the `emit_seed_expectation` seam + the
  `drive_seed_fixture` orchestration surface + the schema
  validator's expectation branch + the three-way authority
  partition + the 8-member cleanup-pressure-resistance class
  inventory); §3 "what PR 9 changes" (this framing
  operationalizes that section); §7 11-step reseed protocol.
- `project_state_2026_05_11_pr8_closed.md` (local memory) — PR 8
  closed cursor; current session opens from this cursor.
- `feedback_ground_specs_in_actual_files.md` — applies to PR 9
  framing as it did to PR 8: assertions about `_seed.py`'s
  surface, fixture module shapes, walker patterns must read the
  actual files before drafting.
- `feedback_inline_authority_boundary_guards.md` — applies to PR 9
  fixture-module surfaces if the fixture data crosses an
  authority boundary (it doesn't structurally; it transacts only
  with `drive_seed_fixture`).

---

## 2. PR 9 objective

**Real job:** *"Land the fixture-data surface for Gate 2. Ship a
small, deliberate corpus of seed fixtures under
`tests/corpus/fixtures/`, each a Python module containing a
single top-level constant dict. Ship a small, deliberate set of
end-to-end integration tests in `tests/corpus/` that import each
fixture module, invoke `drive_seed_fixture(**FIXTURE)`, and
assert the resulting persisted records demonstrate
`record_kind`-partitionability and `fixture_id`-joinability under
three narrowing-outcome shapes (single-survivor, multi-match,
zero-match). Land a new parallel Layer 2 discipline —
`_FIXTURE_PERMITTED_IMPORTS` frozenset + a new AST walker — that
mechanically enforces fixture modules import only the single
orchestration surface (`drive_seed_fixture`). PR 9 closes
Gate 2; the Gate 2 close artifact lands at the same commit."*

PR 9's three operational responsibilities:

- **Author the fixture-data surface.** A new directory
  `tests/corpus/fixtures/` containing three fixture modules, each
  exposing one top-level `FIXTURE` constant dict carrying the three
  PR-8-locked keys (`fixture_id`, `prompt`, `expected_narrow`).
  Each fixture module's docstring carries the inherited
  carriers per the relevance-by-file ordering principle.
- **Author the integration test surface.** Five named tests in a
  new test module `tests/corpus/test_pr9_fixture_integration.py`:
  three end-to-end drives (one per fixture) + two
  partition/joinability property tests. Each test independently
  invokes `drive_seed_fixture` against one fixture; no
  parametrization framework; no test-to-test ordering coupling.
- **Author the Layer 2 fixture discipline.** A new test module
  `tests/corpus/test_pr9_fixture_discipline.py` containing
  `_FIXTURE_PERMITTED_IMPORTS` (value-locked frozenset, 1 symbol:
  `forge_bridge.corpus._seed.drive_seed_fixture`) + a new AST
  walker scoped to `tests/corpus/fixtures/*.py`. The walker is
  **explicitly NOT an extension** of
  `tests/corpus/test_pr4_participation_creep.py` — different
  ontology (PR 4 walker protects production import topology; PR 9
  walker protects declarative-fixture-data discipline).

**Success condition:** *"PR 9 ships `tests/corpus/fixtures/`
(new directory with `__init__.py` + 3 fixture modules),
`tests/corpus/test_pr9_fixture_integration.py` (new, 5 named
tests), `tests/corpus/test_pr9_fixture_discipline.py` (new,
contains `_FIXTURE_PERMITTED_IMPORTS` + walker + Layer 2
discipline tests). Zero modifications to `_seed.py`,
`_capture.py`, `_schema.py`, `_sources.py`, or any other
production source file. Zero modifications to PR 4 / PR 6 / PR 7
/ PR 8 test surfaces. The Layer 3 lint passes unchanged. The
15 carriers + binding framing clarification + carrier #15 + the
governing sentence travel into PR 9 fixture module docstrings
+ integration test module docstring + commit message bodies per
the relevance-by-file ordering principle. Full three-round review
applies across the PR. A `A.5.3.2-PR9-CLOSE.md` artifact + a
`A.5.3.2-GATE-2-CLOSE.md` artifact land at PR 9 close."*

---

## 3. Architectural inheritance

### 3.1 PR 8 decisions PR 9 implements

PR 9 consumes — but does NOT modify — the four artifacts PR 7 +
PR 8 produced:

| Surface | Source PR | PR 9 transaction |
|---|---|---|
| `seed_dispatch_scope` | PR 7 (`_capture.py`) | Consumed indirectly via `drive_seed_fixture` |
| `_persist_expectation_record` | PR 7 (`_capture.py`) | Consumed indirectly via `emit_seed_expectation` |
| `emit_seed_expectation` | PR 8 (`_seed.py`) | Consumed indirectly via `drive_seed_fixture` |
| `drive_seed_fixture` | PR 8 (`_seed.py`) | **Consumed directly — the only PR 9 entry surface** |

PR 9 fixtures transact with **`drive_seed_fixture` only**. The
other three surfaces are mechanically unreachable from PR 9
fixture modules (per Layer 2 fixture discipline §4.3 + §8.2).

PR 9 also operationalizes Gate 2 framing's:

- §4.4 Companion records — each fixture invocation produces two
  records (one expectation, one observation) joined by Gate 4's
  comparator on `fixture_id`. PR 9 demonstrates the joinability
  mechanically without shipping a comparator.
- §5.7 PR partitioning — PR 9 ships fixtures + integration tests.
- §10 PR 9 deliverables — "minimum that exercises observation +
  expectation distinguishability and provenance partitioning
  end-to-end."
- §11 Gate 2 close criteria — PR 9 close ships Gate 2 close
  artifact.

### 3.2 Carriers PR 9 must carry verbatim

Fifteen numbered carriers + the binding framing clarification.
All inherited; no new carrier introduced at PR 9 framing time.

| # | Source | Anchored at |
|---|---|---|
| 1–2 | PR 4 framing — risk-category shift | PR 4 |
| 3–6 | PR 4 framing — integration-discipline quartet | PR 4 |
| 7 | PR 4 framing — finalized-state contract | PR 4 |
| 8 | PR 5 framing — risk-inheritance + surface-geometry distinction | PR 5 |
| 9 | PR 5 framing — caller's view of deployment identity | PR 5 |
| 10 | PR 5 framing — ambiguity-as-arbitration-outcome | PR 5 |
| 11 | PR 5 framing — measured-not-inferred coverage | PR 5 |
| 12 | PR 6 framing — structural-backstop framing | PR 6 |
| 13 | PR 6 framing — observation-not-participation framing | PR 6 |
| 14 | Gate 2 framing §6.1 — declared epistemic class vs. persisted provenance | Gate 2 |
| 15 | PR 8 framing §0 — chat-handler-only seeding scope | PR 8 |
| — | Gate 2 framing §6.2 — binding framing clarification | Gate 2 |

The PR-7-LOCAL pairs (§4.2 inert-parameter, §5.5 legacy-
synthesis) do NOT travel into PR 9 surfaces — they remain
scope-local to `_capture.py` and `reader.py`. The PR-8-LOCAL
binding statements (member #7 truth-partitioning, member #8
semantics-not-topology) do NOT travel verbatim into PR 9 surfaces
either — they remain scope-local to `_seed.py` +
`emit_seed_expectation` per PR 8 spec §0's PR-N-LOCAL non-
regeneration rule. PR 8 close §2.1 names this explicitly.

The fifteen carriers + binding clarification travel verbatim into:

1. Each fixture module's docstring under
   `tests/corpus/fixtures/`. The carrier block uses relevance-by-
   file ordering: carrier #15 (chat-handler-only seeding scope)
   lands AT TOP because each fixture is structurally scoped to
   the chat-handler observation surface — the most-current PR-
   anchored governance text first per PR 7 close §1.5 + PR 8
   close §1.5.
2. `tests/corpus/test_pr9_fixture_integration.py` top-level
   docstring.
3. `tests/corpus/test_pr9_fixture_discipline.py` top-level
   docstring.
4. PR 9 commit message bodies under "preserved invariants" /
   "carriers inherited verbatim" sections.

The relevance-by-file ordering principle is now operational
across three PRs (PR 7 close §1.5 introduced it; PR 8 close §1.5
generalized it to NEW modules; PR 9 extends it to fixture
modules — each fixture's relevance ordering is identical because
all three fixtures live at the same authority surface).

### 3.3 Three-authority-surface partitioning preserves intact

PR 8's close §1.1 established the PR-INTERNAL three-way authority
partition as operational reality. PR 9 transacts with the
partition at exactly one of its three surfaces:

- **Authored expectation semantics** (PR 8) — `emit_seed_expectation`.
  **Unchanged by PR 9.** Reached only via `drive_seed_fixture`.
- **Orchestration semantics** (PR 8) — `drive_seed_fixture`.
  **Unchanged by PR 9.** **The single PR 9 entry surface.**
- **Persistence topology** (PR 7) — `_persist_expectation_record`.
  **Unchanged by PR 9.** Reached only via `emit_seed_expectation`
  (which is reached only via `drive_seed_fixture`).

The non-modification of all three surfaces is mechanically
verifiable: PR 9 ships zero production source file changes; PR 8
spec §7's rejection table protects against collapses (PR 9 may
not propose any of those mutations even incidentally — see §7.2
inherited commitments).

The Gate 2 §3.4 three-authority-surface partition (call-site
shape vs. dispatch provenance vs. persisted-record ontology)
also preserves intact. PR 9 does not write to any of those
surfaces; PR 9 consumes the result of all three composing under
real seeded arbitration.

---

## 4. Architectural delta from PR 9

### 4.1 The fixture corpus directory + module shape

**Directory:** `tests/corpus/fixtures/`. New at PR 9.

**Contents:**

```
tests/corpus/fixtures/
├── __init__.py                  (empty package init)
├── fix_single_survivor.py       (FIXTURE constant + module docstring)
├── fix_multi_match.py           (FIXTURE constant + module docstring)
└── fix_zero_match.py            (FIXTURE constant + module docstring)
```

**Module shape (each fixture module):**

```python
"""Module docstring carries inherited carriers per relevance-by-
file ordering. Carrier #15 lands at top.

[15 carriers verbatim, in relevance order]

[binding framing clarification verbatim]
"""

FIXTURE: dict = {
    "fixture_id": "<unique stable identifier>",
    "prompt": "<single-step prompt text>",
    "expected_narrow": [<list of tool names>],
}
```

Each fixture module is data + a single top-level constant. No
imports beyond `__future__` annotations + `typing` types (if any).
No functions. No classes. No constants beyond `FIXTURE`. No
docstrings beyond the module docstring.

The `_FIXTURE_PERMITTED_IMPORTS` discipline enforces mechanically:
fixture modules may import `forge_bridge.corpus._seed.drive_seed_fixture`
and nothing else from `forge_bridge.corpus`. In practice, fixture
modules will not import the symbol — they are pure data — but the
admission exists because the alternative (a frozenset of zero
elements) would also reject the `drive_seed_fixture` import in the
hypothetical PR 10+ case where a fixture module might benefit
from inlining its driver invocation. Naming the symbol explicitly
is the design choice: the surface is the orchestration call;
nothing else is permitted.

**Fixture identifiers:**

Each `fixture_id` is a stable, unique string. Naming convention
locked at framing:

- `fix-pr9-single-survivor`
- `fix-pr9-multi-match`
- `fix-pr9-zero-match`

The `pr9` segment marks the PR of origin; PR 10+ fixtures use
their own PR-anchored segments. The narrowing-outcome segment
names the structural test scope.

**What this rejects:**

- Programmatic fixture identifier generation
  (`uuid.uuid4()`, `f"fix-{n}"`, hash-derived ids).
- Inheritance across fixture modules (no shared base class, no
  mixin, no template pattern).
- Cross-fixture imports (no `from fix_single_survivor import ...`).
- Helper functions in fixture modules (no `def make_fixture(...)`).
- Multi-`FIXTURE` modules (one fixture per module — discoverability
  + grep-resolvability prefer the 1:1 mapping).

### 4.2 The integration test surface — 5 named tests, no parametrization

**Module:** `tests/corpus/test_pr9_fixture_integration.py`. New at PR 9.

**Test list:**

| # | Name | Fixture | Property under test |
|---|---|---|---|
| 1 | `test_fixture_runs_end_to_end_single_survivor` | `fix-pr9-single-survivor` | Drive produces expectation + observation; both persist; both readable. |
| 2 | `test_fixture_runs_end_to_end_multi_match` | `fix-pr9-multi-match` | Drive produces expectation + observation; observation reflects multi-match ambiguity-rejection arbitration outcome. |
| 3 | `test_fixture_runs_end_to_end_zero_match` | `fix-pr9-zero-match` | Drive produces expectation + observation; observation reflects zero-match ambiguity-rejection arbitration outcome. |
| 4 | `test_observation_and_expectation_distinguishable_by_record_kind` | `fix-pr9-single-survivor` | The two persisted records have distinct `record_kind` values (`"observation"` vs. `"expectation"`); the schema validator accepts both. |
| 5 | `test_records_join_on_fixture_id` | `fix-pr9-single-survivor` | The expectation record and the observation record share the same `fixture_id`; a `fixture_id`-keyed join over the corpus reader's output reunites them. |

**Why exactly 5 tests, exactly this partition:**

- **Tests 1–3** cover the three narrowing-outcome shapes carrier
  #10 names (single-survivor / multi-match / zero-match). Each is
  its own test. No parametrization. Future contributors
  diagnosing a single-outcome regression land directly at the
  test function via grep.
- **Test 4** is a Gate 4 unblock proof. Gate 4's comparator
  depends on `record_kind` discriminator correctness; if test 4
  fails, Gate 4 cannot be written against a stable foundation.
  Independent of "the pipeline ran" — it tests record-kind
  partitionability specifically.
- **Test 5** is a Gate 4 unblock proof. Gate 4's comparator's
  join key is `fixture_id`; if test 5 fails, Gate 4 cannot be
  written against a stable foundation. Independent of test 4 —
  partition (record_kind) and join (fixture_id) are orthogonal
  Gate 4 dependencies; both must hold for the comparator to
  exist.

**What this rejects:**

- `@pytest.mark.parametrize` over fixtures (each test names its
  fixture in the function name).
- `pytest.fixture(params=...)` generating multiple test instances
  from a fixture parameter set.
- A test base class with subclass-per-fixture-outcome.
- A test factory function generating test functions.
- Test ordering dependencies (each test is independent;
  invocation order is irrelevant to outcome).
- Shared state between tests (each test gets a clean rate-limit
  slate via the PR 8 `clean_rate_limit_state` fixture).

**Why no parametrization:**

The governing sentence rejects fixture-management infrastructure.
Parametrize over fixtures IS a fixture-management abstraction —
it programmatically iterates a fixture-set. A future contributor
seeing `@pytest.mark.parametrize("fixture", [single_survivor,
multi_match, zero_match])` would reasonably propose extending it
to a fixture-discovery decorator that walks `tests/corpus/fixtures/`
automatically. That extension surfaces the loader abstraction
through the back door. Closing it at framing is structurally
cheaper than rejecting it at PR 10+ framing time.

### 4.3 The Layer 2 fixture discipline — new parallel frozenset + walker

**Module:** `tests/corpus/test_pr9_fixture_discipline.py`. New at PR 9.

**Contents:**

```python
"""Module docstring carries inherited carriers + Layer 2
fixture discipline rationale.

[carriers]

_FIXTURE_PERMITTED_IMPORTS is the parallel Layer 2 frozenset
scoped to fixture modules under tests/corpus/fixtures/. It is
NOT an extension of test_pr4_participation_creep.py's PR 4
walker — the two walkers protect distinct ontologies.

PR 4 walker (test_pr4_participation_creep.py) protects
PRODUCTION import topology: the narrowing-subsystem may not
acquire corpus dependencies (one-directional flow). The PR 4
walker walks PRODUCTION source files and rejects forbidden
production-to-corpus imports.

PR 9 walker (this file) protects DECLARATIVE FIXTURE-DATA
discipline: fixture modules under tests/corpus/fixtures/ are
data + one orchestration call only. The PR 9 walker walks
fixture modules (declared TEST source, not production) and
rejects any corpus import other than drive_seed_fixture.

The two walkers share AST mechanics (ImportFrom traversal,
fully-qualified dotted reference extraction) but they are NOT
the same walker generalized. Generalization would require
unifying their target-set semantics + their admission
ontologies, which collapses two protections into one rejection
surface. Each walker stays local to its ontology.

Shared AST mechanics do not imply shared ontology.
"""

_FIXTURE_PERMITTED_IMPORTS: frozenset[str] = frozenset({
    "forge_bridge.corpus._seed.drive_seed_fixture",
})

def _fixture_corpus_references(source: str) -> list[str]:
    """Extract every fully-qualified `forge_bridge.corpus.<X>`
    reference imported by `source`. Mirrors the AST mechanics of
    test_pr8_seed_surface.py::_corpus_references — scoped to
    a different target-set and a different protected ontology.
    """
    ...

def test_fixture_permitted_imports_locked_at_one_symbol():
    """Value lock: exactly one element, exactly drive_seed_fixture."""
    ...

def test_fixture_modules_references_subset_of_permitted_imports():
    """Mechanical walker: each tests/corpus/fixtures/*.py file's
    corpus references are a subset of _FIXTURE_PERMITTED_IMPORTS.
    """
    ...
```

**Discipline tests (in addition to the 5 named integration tests
of §4.2):**

| # | Name | Property under test |
|---|---|---|
| A | `test_fixture_permitted_imports_locked_at_one_symbol` | Frozenset value lock; exact set match against the expected single-element frozenset. |
| B | `test_fixture_modules_references_subset_of_permitted_imports` | Walker: every fixture module under `tests/corpus/fixtures/*.py` has its corpus imports as a subset of `_FIXTURE_PERMITTED_IMPORTS`. |

The discipline tests are PR 9 Layer 2 infrastructure tests; they
are NOT among the 5 named integration tests. They are the
mechanical enforcement of member #9 (§6.1).

**Why a parallel frozenset, not an extension of `_SEED_PERMITTED_IMPORTS`:**

`_SEED_PERMITTED_IMPORTS` is scoped to `forge_bridge/corpus/_seed.py`.
It admits 5 symbols that `_seed.py` itself imports
(`seed_dispatch_scope`, `_persist_expectation_record`,
`_now_iso_ms`, `_new_uuid`, `SCHEMA_VERSION`). Extending it to
also cover fixture imports would conflate two distinct ontologies:

- `_seed.py`'s own admission set is about an *authoring surface
  with multiple dependencies*. `_SEED_PERMITTED_IMPORTS` is a
  *bounded toolbox*.
- Fixture modules' admission set is about a *data surface with
  one orchestration call only*. `_FIXTURE_PERMITTED_IMPORTS` is a
  *single-symbol gate*.

The two ontologies have different growth pressures (PR 8's PR-8-
LOCAL participation discipline allowed `_SEED_PERMITTED_IMPORTS`
to be a 5-element set; the fixture-data discipline forbids
*any* growth past the single orchestration symbol). Merging them
forces them to share growth pressure; separating them keeps the
fixture-data discipline tight forever.

**Why a parallel walker, not an extension of the PR 4 walker:**

The PR 4 walker (`tests/corpus/test_pr4_participation_creep.py`)
walks **production source files** and protects
**production-to-corpus import topology** (one-directional flow:
corpus may not be imported by the narrowing subsystem). The PR 4
walker's target set is production modules; its rejection rule is
"production may not depend on corpus."

The PR 9 walker walks **fixture modules** (declared test source)
and protects **fixture-data discipline** (one orchestration call
only). The PR 9 walker's target set is fixture modules; its
rejection rule is "fixtures may not import anything but
`drive_seed_fixture`."

Sharing the AST mechanics (both use `ast.walk` + `ImportFrom`
traversal) does NOT make them the same walker. Generalization
would require unifying:

- Target-set semantics (production vs. fixture-test).
- Admission ontologies (one-directional flow vs. single-symbol-
  gate).
- Rejection-message shape (production-creep rejection vs.
  fixture-data-discipline rejection).
- Future evolution pressure (PR 4 walker may admit more production
  modules; PR 9 walker MUST NOT admit more symbols).

A unified walker collapses two protections into one rejection
surface; future PRs would have to relax both protections together
or invent ad-hoc partitioning at the unified surface. Keeping the
walkers separate keeps the protections local to their ontologies
and the cleanup-pressure surface narrow.

The PR 8 walker (`tests/corpus/test_pr8_seed_surface.py::_corpus_references`)
is the closest ontological cousin: it walks a single source file
and enforces a per-symbol admission set. The PR 9 walker
generalizes the PR 8 pattern to a directory glob — but the
admission set semantics (single-symbol-gate) differ.

---

## 5. Binding decisions

### 5.1 Q1 — Fixture format locked at Python module + top-level dict constant

Each fixture is a Python module under `tests/corpus/fixtures/`
exposing a single top-level constant `FIXTURE: dict`. The dict
carries exactly the three PR-8-locked keys (`fixture_id`,
`prompt`, `expected_narrow`).

**What this rejects:** JSON / YAML / TOML / CSV fixture files;
auto-generated fixture files; multi-fixture modules; fixture
modules containing functions, classes, or non-`FIXTURE` constants;
fixture modules importing anything from `forge_bridge.corpus`
beyond `drive_seed_fixture`; speculative optional fields beyond
the three PR-8-locked keys (per Q5 below).

**Why this is right:** Python modules preserve comments, module
docstrings, carrier inheritance, and grep archaeology — the same
shape every other corpus artifact uses. No parse layer, no new
dependency, no fixture-loader infrastructure. The
relevance-by-file ordering principle (carriers at top per
relevance) carries naturally because fixture modules are Python.
Per the governing sentence: PR 9 proves topology, not infrastructure.

### 5.2 Q2 — Fixture invocation locked at direct test-module import + pytest collection

Each integration test imports its specific fixture module
directly and invokes `drive_seed_fixture(**FIXTURE)`. pytest's
test collection mechanism IS the loader; no separate loader
abstraction lands.

**What this rejects:** A `load_fixture_corpus()` function; a
`@fixture` decorator-based collection; a fixture registry; a
fixture discovery walker (the PR 9 Layer 2 walker enforces
discipline, NOT discovery — it walks fixtures to validate, not to
collect); a CLI entry point invoking fixtures; a daemon hook
running fixtures on schedule; a `parametrize`-over-fixtures
pattern.

**Why this is right:** the integration tests ARE the consumer
surface. A loader is speculative infrastructure when its only
consumer is the tests that would otherwise import the modules
directly. PR 10+ may surface a CLI or daemon-hook need; the
fixture-module shape supports that without restructuring (the
hypothetical CLI would import the same modules pytest does). Per
the governing sentence: PR 9 proves topology, not infrastructure.

### 5.3 Q3 — Fixture count locked at exactly 3

Three fixtures: `fix-pr9-single-survivor`, `fix-pr9-multi-match`,
`fix-pr9-zero-match`. One per narrowing-outcome shape.

**What this rejects:** fewer fixtures (1 covers happy path only
— fails to demonstrate the carrier #10 ambiguity-rejection
semantics end-to-end); more fixtures (each additional fixture is
either a redundant shape variation or a speculative coverage
expansion; both fall under the infrastructure-not-topology
rejection); fixture variants exercising the same outcome
(e.g., two single-survivor fixtures with different prompts —
speculative coverage).

**Why this is right:** carrier #10 names three narrowing
outcomes; one fixture per outcome is the minimum-viable
demonstration. The Gate 4 comparator will eventually surface
concrete coverage needs (e.g., narrowing-with-no-disambiguating-
parameter vs. narrowing-with-conflicting-parameters); those
fixture additions land at the framing pass that introduces the
Gate 4 comparator. PR 9's job is topology proof, not coverage
breadth.

### 5.4 Q4 — Layer 2 fixture discipline locked at parallel frozenset + parallel walker

A new constant `_FIXTURE_PERMITTED_IMPORTS` (value-locked
frozenset, 1 symbol: `forge_bridge.corpus._seed.drive_seed_fixture`)
+ a new AST walker live in
`tests/corpus/test_pr9_fixture_discipline.py`. The walker targets
`tests/corpus/fixtures/*.py`. Explicitly NOT an extension of
`tests/corpus/test_pr4_participation_creep.py` (PR 4 walker
protects production import topology; PR 9 walker protects
declarative fixture-data discipline).

**What this rejects:** extending `_SEED_PERMITTED_IMPORTS` to
also admit fixture imports (conflates two ontologies); a
unified walker abstraction (collapses two protections into one
rejection surface); admitting any second symbol to
`_FIXTURE_PERMITTED_IMPORTS` (the single-symbol-gate IS the
discipline).

**Why this is right:** the fixture surface ontology is distinct
from the seed-driver-internal participation discipline ontology
AND from the production-import-topology ontology. Parallel
constants + parallel walkers keep the three protections local to
their ontologies. Future PRs cannot relax the fixture-data
discipline by relaxing the seed-driver discipline (or vice
versa). Per member #9 protection (§6.1).

### 5.5 Q5 — Expectation record extension locked at NO extension

The three PR-8-locked required keys (`fixture_id`, `prompt`,
`expected_narrow`) remain the only required keys at PR 9 close.
No new required keys. No new optional keys.

**What this rejects:** adding metadata fields
(`fixture_source`, `created_at_iso`,
`expected_tools_seed_corpus_version`) — bookkeeping that erodes
member #7 (companion records as truth-partitioning); adding
arbitration-context fields (`expected_decision`,
`expected_candidates_after_narrowing`) — Gate-4 anticipation that
preempts the comparator's framing-time choice surface; bumping
`SCHEMA_VERSION` (rejected at PR 7 spec §7); adding a third
`_KNOWN_RECORD_KINDS` value (rejected at PR 7 spec §7).

**Why this is right:** PR 9 is a consumption + orchestration
proof PR, not a schema-expansion PR. §3 risk #4 (schema
discriminator drift) protects against speculative additions.
Member #7's protection (companion records as truth-partitioning)
specifically rejects additive metadata that erodes the
authored-truth-vs-observed-truth partition. Gate 4's framing pass
will surface concrete needs at comparator-write time; adding
fields now means guessing at Gate 4's policy questions in
advance. If PR 9 integration tests surface a concrete missing
field, register it as a spec amendment at incarnation per the
PR 7 + PR 8 amendment cluster methodology — but at framing time,
zero extension.

### 5.6 Q6 — `__all__` deferral preserved (per PR 8 Q5)

Neither `emit_seed_expectation` nor `drive_seed_fixture` enters
`forge_bridge.__all__` at PR 9. The decision remains deferred to
first concrete external consumer.

**What this rejects:** speculative `__all__` membership "because
PR 9 fixtures use these"; PR 9 fixtures live in `tests/corpus/`
and import via `forge_bridge.corpus._seed` directly — no
`__all__` membership required for test-side consumers.

**Why this is right:** PR 9 fixtures are the same kind of
consumer PR 8's tests are (internal tests, not external API
consumers). The PR 8 Q5 deferral rationale carries unchanged.
`forge_bridge.__all__` stays at 19 symbols.

---

## 6. Constructs intentionally resistant to cleanup pressure

PR 7 framing §6 introduced the class. PR 7 close §1.2 locked the
PR 7 inventory at 6 members. PR 8 framing §6 + close §1.2
contributed members #7 + #8 (final inventory at PR 8 close: 8
members). PR 9 framing contributes one new member, bringing the
class final inventory at PR 9 close to **9 members** subject to
PR 9 corroboration.

### 6.1 Member #9 — Fixture-surface-data-discipline

**The construct:** Fixtures under `tests/corpus/fixtures/` are
**data + one orchestration call only**. Each fixture module
exposes exactly one top-level constant (`FIXTURE: dict`); the
module contains no functions, no classes, no constants beyond
`FIXTURE`, no imports beyond `forge_bridge.corpus._seed.drive_seed_fixture`
(in the hypothetical case where a fixture module wants to inline
its driver invocation — currently fixture modules import
nothing, but the admission exists for the orchestration symbol).
Integration tests invoke `drive_seed_fixture(**FIXTURE)`
directly; no loader abstraction lands.

**Local simplification pressure:** *"Fixtures keep duplicating
the same three-key dict shape. Let's add a `make_fixture(fixture_id,
prompt, expected_narrow)` helper that returns the dict — cleaner,
less duplication, easier to keep schema-consistent."* The
proposal is locally defensible — three lines of repetition per
fixture module looks like a code smell. From inside the proposing
PR's diff, the helper looks like trivial DRY.

**Hidden truth collapse:** A `make_fixture(...)` helper appears
symmetrical with `base_expectation_args(...)` (the PR 8 test
helper) but silently transfers fixture-construction authority
from declarative data into procedural code. The two cases are
NOT symmetrical: `base_expectation_args` is a TEST-INPUT helper
producing default-valid kwargs for testing `emit_seed_expectation`'s
signature contract; fixtures are FIXTURE-DATA artifacts producing
arbitration inputs. The collapse erodes three load-bearing
properties:

- **Grep archaeology.** A fixture module with a single
  declarative `FIXTURE` dict is grep-resolvable in one
  step: `grep -A 5 "FIXTURE" tests/corpus/fixtures/fix_*.py`
  surfaces every fixture's full contents. A `make_fixture(...)`
  helper requires reading the helper definition + each call site
  to reconstruct the data.
- **Carrier travel discipline.** Module docstrings carry the
  inherited carriers per the relevance-by-file ordering principle.
  A helper-based shape moves the carriers' load-bearing position
  from "above the data" to "above the helper" — which lives in
  one file, not three. The relevance-by-file ordering breaks:
  three fixtures sharing one carrier block is one indirection
  removed from the grep landing site.
- **Single-symbol-gate Layer 2 discipline.** The
  `_FIXTURE_PERMITTED_IMPORTS` frozenset's value-lock at exactly
  one symbol (`drive_seed_fixture`) is mechanically enforced. A
  `make_fixture(...)` helper would require admitting `make_fixture`
  to the frozenset — which forces growth pressure on the
  discipline, which is exactly what the value-lock protects
  against.

The cleanup pressure looks like DRY; the protected property is
the declarative-not-procedural fixture-data ontology.

**Why the protection exists:** Per the governing sentence (PR 9
proves topology, not infrastructure), fixtures are data
artifacts. A fixture-construction helper is a form of fixture
infrastructure. Topology proof requires fixtures readable as
data; infrastructure smears the proof's surface into procedural
code paths. PR 10+ may add fixture-management infrastructure
when a concrete external consumer surfaces; PR 9 declines the
infrastructure surface to keep the topology proof clean.

**Operational placement of the protection:**

- Each fixture module's docstring carries the fixture-surface-
  data-discipline framing inline (one paragraph at the bottom of
  the carrier block, naming member #9 protection).
- `tests/corpus/test_pr9_fixture_discipline.py` module docstring
  carries the discipline's Layer 2 mechanical-enforcement
  rationale.
- `_FIXTURE_PERMITTED_IMPORTS` value-lock test enforces the
  single-symbol-gate mechanically.
- The PR 9 walker enforces the import-discipline mechanically.
- PR 9 commit message body names the protection explicitly.
- A future PR proposing `make_fixture(...)` either needs to
  admit the helper to `_FIXTURE_PERMITTED_IMPORTS` (visible at
  review — value-lock change requires explicit redline) or
  violate the existing admission (mechanically caught by the
  walker).

### 6.2 Class final inventory at PR 9 close

| # | Member | PR | Protection |
|---|---|---|---|
| 1 | Helper duplication (`emit_divergence_capture` + `_persist_expectation_record`) | PR 7 | Framing §6 + spec §7 close conditions |
| 2 | Visual asymmetry (Properties A–D) | PR 6 | Layer 3 lint |
| 3 | Intentionally inert structural parameters (`source="runtime"` at call sites) | PR 7 | §4.2 binding pair + `test_call_site_source_value_is_inert` |
| 4 | Always-present `fixture_id` field on observation records | PR 7 | Builder dict structure + `test_scope_inactive_persists_runtime` |
| 5 | Nested-not-unconditional synthesis form in reader | PR 7 | §5.5 binding pair + `test_mixed_legacy_and_contemporary_records` |
| 6 | Inline I-6 wrapper duplication in `_persist_expectation_record` | PR 7 | Inline pattern + Step 8 spec |
| 7 | Companion records as truth-partitioning | PR 8 | `_seed.py` docstring + framing §6.1 + schema-validator expectation-branch rejection of `source` field |
| 8 | `emit_seed_expectation` as semantics-not-topology | PR 8 | `_seed.py` + `emit_seed_expectation` docstrings + framing §6.2 + Layer 2 `_SEED_PERMITTED_IMPORTS` value-lock |
| **9** | **Fixture-surface-data-discipline** | **PR 9** | **Fixture module docstrings + framing §6.1 + Layer 2 `_FIXTURE_PERMITTED_IMPORTS` value-lock + PR 9 walker** |

Member #9 is candidate methodology contribution. Promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` is gated on at
least one more reliability phase surfacing a class member under
genuinely independent conditions (the Gate 1 + Gate 2 corroboration
discipline). PR 9's contribution provides a third population of
the class (after PR 7's 6 + PR 8's 2); the discipline is now
populatable across three reliability phases — strong corroboration,
but a fourth phase under fresh conditions remains the promotion
gate.

---

## 7. Non-acquisition commitments

### 7.1 PR 9 explicitly does NOT (PR 9-specific commitments)

1. **Drive `_step.py:233`.** Carrier #15 governs. PR 9 fixtures
   exercise `chat_handler` only via `drive_seed_fixture`. No PR 9
   surface invokes `_step.py:233` directly or indirectly. A future
   PR proposing chain-step fixture coverage must produce the
   dedicated framing pass carrier #15 anchors.

2. **Ship a Gate 4 comparator stub.** Gate 2 §11.3 explicitly:
   *"Gate 2 ships no comparator artifact, stub or otherwise."*
   PR 9 demonstrates `record_kind`-partitionability +
   `fixture_id`-joinability mechanically (tests 4 + 5 of §4.2)
   WITHOUT shipping a `compare_fixture_records(...)` function or
   any comparator helper. The mechanical proofs unblock Gate 4
   framing; the comparator itself is Gate 4's deliverable.

3. **Ship a fixture loader / CLI / daemon hook.** Per the
   governing sentence + Q2 binding decision. The integration
   tests ARE the fixture consumer surface at PR 9. PR 10+ may
   surface a loader / CLI / daemon-hook need; at PR 9, the
   surface is rejected.

4. **Ship a fixture registry / factory / generator /
   parametrization framework.** Per the governing sentence + Q1
   binding decision. Each fixture is a Python module with one
   top-level `FIXTURE` dict; no programmatic fixture management
   abstraction lands.

5. **Ship non-Python fixture formats.** Per the governing
   sentence + Q1 binding decision. No JSON, YAML, TOML, CSV
   fixture files.

6. **Extend the expectation record schema.** Per Q5 binding
   decision + member #7 protection + §3 risk #4. The 3 PR-8-
   locked required keys remain the only required keys at PR 9
   close.

7. **Promote `emit_seed_expectation` or `drive_seed_fixture` to
   `forge_bridge.__all__`.** Per Q6 binding decision + PR 8 Q5
   deferral. PR 9 fixtures consume via `forge_bridge.corpus._seed`
   import path; no `__all__` membership required.

8. **Modify any production source file.** Zero changes to
   `_seed.py`, `_capture.py`, `_schema.py`, `_sources.py`,
   `console/handlers.py`, or any other production source. PR 9
   is purely test-surface additions.

9. **Modify the PR 4, PR 6, PR 7, or PR 8 test surfaces.**
   `test_pr4_participation_creep.py` is NOT extended; PR 9 ships
   a new walker in a new file with distinct ontology.
   `test_pr6_visual_asymmetry.py` ships unchanged (Layer 3 lint
   input set unchanged). PR 7 + PR 8 test modules ship unchanged.

10. **Generate fixtures programmatically.** No
    `fixtures = [make_fixture(...) for ...]` patterns. No
    fixture-discovery walkers (the PR 9 walker validates fixture
    modules, but does not enumerate them as inputs to tests —
    tests import fixture modules by name).

11. **Couple integration tests to ordering.** Each test is
    independent. No fixture-emitted state survives across tests
    (the PR 8 `clean_rate_limit_state` fixture grounds each
    test's rate-limit slate; corpus JSONL persistence is
    date-partitioned but PR 9 tests read records by `fixture_id`
    match, not by file ordering).

12. **Touch the Layer 3 lint.** `test_pr6_visual_asymmetry.py`
    ships unchanged. Layer 3's discovery walk finds calls to
    `emit_divergence_capture` only; PR 9 introduces no new
    `emit_divergence_capture` call sites, so the lint's input
    set is unchanged.

### 7.2 Inherited Gate 2 + PR 7 + PR 8 non-acquisition commitments

PR 9 also inherits and preserves:

- **Gate 2 framing §7's six commitments** (don't touch Layer 3
  lint, don't bypass live arbitration, don't author expectation
  through observation helper, don't extend Layer 3 to expectation
  emission, don't modify env-gate, don't collapse contextual
  provenance into arbitration).
- **PR 7 framing §7's seven commitments** preserve unchanged.
- **PR 7 spec §7's phase-end-conditions rejection table** — PR 9
  may not propose any of those mutations (refactor
  `_persist_expectation_record` + `emit_divergence_capture` into
  a shared writer; remove the authority pre-check; surface a
  nested-scope token from `seed_dispatch_scope`; promote PR 7
  surfaces to `__all__`; backfill or rewrite legacy records;
  bump `SCHEMA_VERSION`; add a third `_KNOWN_RECORD_KINDS`
  value; add a third `KNOWN_SOURCE_VALUES` entry).
- **PR 8 framing §7's nine commitments** preserve unchanged.
- **PR 8 spec §7's phase-end-conditions rejection table** — PR 9
  may not propose any of those mutations (inline
  `_persist_expectation_record` into `emit_seed_expectation`;
  collapse helper/driver authority partition; drive `_step.py:233`
  from `drive_seed_fixture`; promote `emit_seed_expectation` or
  `drive_seed_fixture` to `__all__`; add a third value to
  `KNOWN_SOURCE_VALUES` or `_KNOWN_RECORD_KINDS`; refactor
  `emit_divergence_capture` + `_persist_expectation_record` into
  a shared internal writer).

### 7.3 What PR 9 deliberately does NOT decide

Several ontological questions surface from carrier #15's chain-
step deferral + the §7.3 PR 8 framing list. PR 9 explicitly leaves
all four open. Each requires the dedicated framing pass carrier
#15 anchors:

1. **Does one expectation target one observation surface or
   multiple?** Unchanged from PR 8 §7.3. PR 9's fixtures all
   target chat-handler (one surface); the question of multi-
   surface expectation records remains open.

2. **Does `fixture_id` identify a logical prompt or a specific
   arbitration surface?** Unchanged from PR 8 §7.3. PR 9's
   `fixture_id` values are PR-9-anchored strings without
   surface-encoding.

3. **Is cross-surface divergence meaningful or noise?**
   Unchanged from PR 8 §7.3. PR 9 does not exercise cross-surface
   semantics.

4. **Does Gate 4 compare within surfaces or across them?**
   Unchanged from PR 8 §7.3. PR 9 does not write the comparator.

PR 9 additionally does NOT decide:

5. **Does fixture-data discipline scale past 3 fixtures?** PR 9
   ships 3 fixtures; whether the data-discipline holds at 30 or
   300 fixtures is not exercised. PR 10+ growth may surface a
   need to relax the discipline (e.g., a per-fixture-family
   directory partition); that surfaces at PR 10+ framing time.

6. **Does the Layer 2 fixture walker need to handle import-as
   syntax (`import forge_bridge.corpus._seed as fb_seed`)?** PR 9
   fixtures do not use `import-as`; the walker's AST traversal
   handles `ImportFrom` only at PR 9. If PR 10+ surfaces an
   `import-as` need, the walker extends at that time. PR 9's
   walker semantics: explicit single-symbol `from ... import ...`
   admission only.

These are supporting explanatory prose, not carriers. The
governing sentence is the load-bearing protection; the six
questions are the *content* of the decision deferral.

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — no extension at PR 9

`_ALLOWLIST` is unchanged at PR 9. PR 9 ships no new production
source files; the `_ALLOWLIST` (which governs the production
source surface, not the test surface) sees no new admission
need.

The new test modules (`test_pr9_fixture_integration.py`,
`test_pr9_fixture_discipline.py`) and the new fixture modules
(under `tests/corpus/fixtures/`) live under `tests/` — outside
`_ALLOWLIST`'s scope entirely.

### 8.2 Layer 2 — new parallel `_FIXTURE_PERMITTED_IMPORTS` frozenset + new walker

PR 9 introduces a **parallel** Layer 2 surface in a new test
module. The relationship to existing Layer 2 surfaces:

| Layer 2 surface | Source | Scope | PR 9 transaction |
|---|---|---|---|
| `_PERMITTED_CORPUS_IMPORTS` | PR 4 (`test_pr4_participation_creep.py`) | Production-to-corpus import topology | Unchanged. PR 9 ships no production source. |
| `_SEED_PERMITTED_IMPORTS` | PR 8 (`test_pr8_seed_surface.py`) | `_seed.py`'s own corpus-internal imports (5 symbols) | Unchanged. PR 9 does not modify `_seed.py`. |
| **`_FIXTURE_PERMITTED_IMPORTS`** | **PR 9 (`test_pr9_fixture_discipline.py`)** | **Fixture modules' corpus imports (1 symbol)** | **Introduced by PR 9.** |

The three surfaces share AST mechanics (each uses `ast.walk` +
`ImportFrom` traversal) but they protect three distinct
ontologies:

- **`_PERMITTED_CORPUS_IMPORTS`** protects PRODUCTION import
  topology (one-directional: corpus not imported by narrowing
  subsystem).
- **`_SEED_PERMITTED_IMPORTS`** protects the SEED-DRIVER-INTERNAL
  toolbox (bounded set of corpus symbols `_seed.py` may import).
- **`_FIXTURE_PERMITTED_IMPORTS`** protects the FIXTURE-DATA
  surface (single-symbol-gate: fixtures may import only
  `drive_seed_fixture`).

The three surfaces stay structurally separate. Unification would
collapse three protections into one rejection surface — the
generalization pressure that member #9 protects against (per
§6.1).

### 8.3 Layer 3 — unchanged

`test_pr6_visual_asymmetry.py` ships unchanged at PR 9. Layer 3's
discovery walk finds calls to `emit_divergence_capture` only; PR 9
introduces no new `emit_divergence_capture` call sites, so the
lint's input set is unchanged.

The Layer 3 lint passes against the modified `_capture.py` (PR 7's
modifications), against `_seed.py` (PR 8's additions — no
`emit_divergence_capture` calls land there), and against PR 9's
new test modules + fixture modules (no `emit_divergence_capture`
calls land there either). Mechanical verification: `pytest
tests/corpus/test_pr6_visual_asymmetry.py` passes unchanged at
PR 9 close.

---

## 9. Phase-end conditions for PR 9 + Gate 2 close criteria

PR 9 closes when:

1. **Three fixture modules land** under `tests/corpus/fixtures/`:
   `fix_single_survivor.py`, `fix_multi_match.py`,
   `fix_zero_match.py`. Each contains exactly one top-level
   `FIXTURE: dict` carrying exactly the three PR-8-locked keys.
   Each module's docstring carries the 15 inherited carriers +
   binding framing clarification per the relevance-by-file
   ordering principle. Each module imports nothing from
   `forge_bridge.corpus`.

2. **Two new test modules land:**
   - `tests/corpus/test_pr9_fixture_integration.py` — 5 named
     integration tests per §4.2. Each test independently invokes
     `drive_seed_fixture(**FIXTURE)` against one fixture; each
     test asserts the expected persisted record properties.
   - `tests/corpus/test_pr9_fixture_discipline.py` — contains
     `_FIXTURE_PERMITTED_IMPORTS` (value-locked frozenset, 1
     symbol) + the AST walker scoped to
     `tests/corpus/fixtures/*.py` + 2 named Layer 2 discipline
     tests (frozenset value-lock + walker subset-enforcement).

3. **Zero production source file modifications.** No changes to
   `_seed.py`, `_capture.py`, `_schema.py`, `_sources.py`,
   `console/handlers.py`, or any other production source.

4. **Zero modifications to PR 4, PR 6, PR 7, PR 8 test modules.**
   `test_pr4_participation_creep.py`,
   `test_pr6_visual_asymmetry.py`,
   `test_pr7_*.py` (all PR 7 modules),
   `test_pr8_seed_surface.py` ship unchanged.

5. **All existing tests pass unchanged + PR 9's named contribution lands.**
   - PR 4 + PR 5 + PR 6 + PR 7 + PR 8 integration tests pass
     unchanged.
   - PR 9 adds **7 named tests** total:
     - 5 integration tests in
       `tests/corpus/test_pr9_fixture_integration.py` (§4.2).
     - 2 discipline tests in
       `tests/corpus/test_pr9_fixture_discipline.py` (§4.3).
   - **Test count arithmetic anchor:** 200 baseline collected
     count at PR 8 close (per PR 8 close §1.6: 175 pre-PR-8 +
     25 PR 8 collected = 200 forge-env scoped) + 7 new (PR 9
     ships zero parametrize per Q3, so named == collected for
     PR 9's contribution) = **207 target forge-env collected
     count at PR 9 close**.
   - Forge-bridge env collected count remains gapped per
     `project_v1_4_x_harness_debt.md` (the 6-test gap inherited
     from PR 7 due to `starlette` TestClient + asyncpg loop
     conflict + Project-seeding fixture gap). PR 9 close §6
     documents both env counts explicitly; do not conflate.
   - Named-vs-collected distinction is archaeology-grade per
     PR 8 close §1.6. PR 9 spec §5 should report named
     projections (7); PR 9 close §6 should report both named
     (7) and collected (7 — identical at PR 9 due to no
     parametrize) actual counts plus the full-corpus 207
     anchor verification.

6. **The 15 carriers + binding framing clarification travel
   verbatim** into the 3 fixture module docstrings + 2 new test
   module docstrings + PR 9 commit message bodies, per the
   relevance-by-file ordering principle.

7. **The governing sentence** ("PR 9 proves topology, not
   infrastructure.") appears in:
   - The PR 9 spec §0.
   - PR 9 commit message bodies (close artifact + at least one
     implementation commit body).
   - Optionally in fixture module docstrings (spec-time decision).

8. **Cleanup-pressure-resistance class** reaches 9 members at
   PR 9 close per §6.1.

9. **PR 9 close artifact** (`A.5.3.2-PR9-CLOSE.md`) ships at the
   PR 9 close commit, mirroring PR 8 close structure (§1–§8 +
   reseed protocol if PR 10+ work continues).

### Gate 2 close criteria (deliverable at PR 9 close commit)

PR 9 close is also Gate 2 close. The Gate 2 close artifact
(`A.5.3.2-GATE-2-CLOSE.md`) ships at the same commit as
`A.5.3.2-PR9-CLOSE.md`, per Gate 2 framing §11.6 + PR 8 close
§7 step 11.

Gate 2 closes when:

1. **The two Gate-2 authority surfaces** (observation + authored
   expectation) operate end-to-end under real seeded execution.
   Interpretive authority remains Gate 4's deliverable; Gate 2
   ships no comparator.
2. **First fixtures run end-to-end** demonstrating observation +
   expectation persistence + reader validation. PR 9's three
   fixtures + three e2e tests satisfy this criterion.
3. **Gate 4 is unblocked** for comparator articulation:
   `KNOWN_SOURCE_VALUES` + `_KNOWN_RECORD_KINDS` schema in place
   (PR 7); comparator dependency named (Gate 2 framing §9.4 +
   PR 7 + PR 8 + PR 9 close artifacts). PR 9 tests 4 + 5 (§4.2)
   mechanically verify the comparator's two dependencies
   (`record_kind` partition + `fixture_id` join) WITHOUT shipping
   the comparator.
4. **Layer 1 + Layer 2 extensions** are mechanically verified.
   Layer 3 unchanged + still green.
5. **The 15 carriers travel verbatim** into all Gate 2 production
   modules + test docstrings + commit messages. PR 9 close
   verifies this for the PR 9-introduced files.
6. **A `A.5.3.2-GATE-2-CLOSE.md` artifact** ships at the PR 9
   close commit, following the PR 6 close artifact's structure
   (predecessors, what Gate 2 established, what Gate 3 / Gate 4
   inherits, methodology observations, cross-references).

---

## 10. Cross-references

- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — §10 PR 9 deliverables;
  §11 Gate 2 close criteria. Authoritative on what PR 9 + Gate 2
  close must demonstrate.
- `A.5.3.2-PR8-FRAMING.md` (`23f2a20`) — §0 carrier #15; §5 Q1–Q5
  binding decisions; §6 members #7 + #8; §7 non-acquisition
  commitments. Structural template this framing mirrors.
- `A.5.3.2-PR8-SPEC.md` (`85c5bc1`) — §0 18 verbatim sentences;
  §4.1.5.1 three-way authority partition; §7 phase-end conditions
  rejection table (PR 9 may not propose any of those mutations).
- `A.5.3.2-PR8-CLOSE.md` (`b102010`) — §2 what PR 9 inherits;
  §3 what PR 9 changes; §1.2 8-member cleanup-pressure class
  inventory (PR 9 contributes member #9 → 9-member final
  inventory at PR 9 close); §7 11-step reseed protocol (this
  framing executes steps 1–7).
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — §2 what PR 8 inherited
  (durable PR 7 archival state still applies at PR 9).
- `forge_bridge/corpus/_seed.py` — the four PR 7 + PR 8 surfaces
  PR 9 transacts with (`drive_seed_fixture` directly;
  `emit_seed_expectation`, `seed_dispatch_scope`,
  `_persist_expectation_record` indirectly).
- `tests/corpus/_pr3_helpers.py::base_expectation_args` — PR 8
  helper; NOT consumed by PR 9 (PR 8's helper is for testing
  `emit_seed_expectation`'s signature; PR 9 fixtures construct
  data directly).
- `tests/corpus/test_pr4_participation_creep.py` — PR 4 walker;
  PR 9 walker is **explicitly NOT** an extension of this module.
- `tests/corpus/test_pr8_seed_surface.py` — PR 8 walker; PR 9
  walker generalizes the AST mechanics pattern to a directory
  glob target, but with distinct admission ontology.

---

End of PR 9 framing. The framing locks the binding decisions
PR 8 close §3 left open (fixture corpus shape, loader shape,
integration test surface, Layer 2 discipline extension,
expectation record extension, non-acquisition commitments,
binding decisions, cleanup-pressure class additions). The
governing sentence — "PR 9 proves topology, not infrastructure."
— is the framing-artifact rejection key for the entire category
of speculative scope that locally-defensible cleanup pressure
would otherwise smuggle in.

PR 9 spec derives from this framing per the cadence (close §7
step 9). Spec amendments at incarnation are normal per the PR 7
+ PR 8 amendment cluster methodology; register them as NO-code
commits.

PR 9 is the final PR of Gate 2. PR 9 close + Gate 2 close land
at the same commit. The 9-member cleanup-pressure-resistance
class final inventory + the seven amendments at incarnation from
PR 7 + PR 8 + any PR 9 contributions are durable archaeology the
Gate 3 / Gate 4 framing passes inherit.
