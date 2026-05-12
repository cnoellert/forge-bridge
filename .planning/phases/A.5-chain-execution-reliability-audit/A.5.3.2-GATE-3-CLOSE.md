# A.5.3.2 Gate 3 — Close (recomposition gate-arc synthesis)

**Status:** Durable archival state. Gate 3 ships the comparator
helper (PR 10) + the end-to-end recomposition arc (PR 11) +
the architectural-sufficiency-signal continuity across three
consecutive reliability PRs (PR 9 + PR 10 + PR 11). Gate 3
closes the recomposition phase of the decomposition →
recomposition arc that PR 6/Gate 1 began and Gate 2 advanced.

This artifact ships at the **same final commit** as PR 11
close (`A.5.3.2-PR11-CLOSE.md`) per Gate 3 framing §11 + PR 11
framing §11 + Gate 2 close 2026-05-11 (`a6e42f0`) precedent.
**Two artifacts at one commit.** Responsibility split (per
PR 11 framing §11):

- **PR 11 close** owns PR 11-scoped archaeology
  (implementation arc, recomposition-through-existing-seams
  operational evidence, architectural sufficiency signal
  validation at PR 11 scope, §5.3 second-instance ABSENCE
  outcome, PR-11-LOCAL discipline archaeology).
- **Gate 3 close (this artifact)** owns gate-arc synthesis
  across PR 10 + PR 11, candidate carrier #16 promotion
  evaluation, conditional PR 12 disposition, cross-PR
  methodology promotion candidacies, gate-level inheritance
  contract toward Gate 4, the four §7.3 ontological
  questions handoff.

Where overlap surfaces, PR 11 close defers to this artifact at
gate scope.

---

## 1. What Gate 3 established

### 1.1 The comparator helper + the recomposition arc — two deliverables, one architectural commitment

Gate 3 shipped **two architectural deliverables** at PR
boundaries:

| PR | Deliverable | Surface |
|---|---|---|
| PR 10 | Comparator helper (`compare_records`) | `forge_bridge/corpus/_compare.py` (523 lines, single new production file) |
| PR 11 | End-to-end recomposition arc | `tests/corpus/test_pr11_recomposition_arc.py` (313 lines, single new test file) |

Together they implement one architectural commitment per
**newly-active carrier #16** (promoted at this close per §1.6):

> **Reliability work proves topology, not infrastructure.**

PR 10 proved the comparator could ship as **topology** (pair-
input pure-functional read surface) rather than
**infrastructure** (subsystem with strategies / plugin
registry / configuration). PR 11 proved the recomposition arc
could operate end-to-end through **existing seams** without
requiring any production source modification — i.e., the
substrate (PR 7+8+9) + the comparator (PR 10) are **sufficient
topology** for the end-to-end use case.

### 1.2 Three-PR architectural sufficiency escalation

Gate 3 demonstrates the Gate 2 + Gate 3 decomposition strategy
was sufficient through a **three-PR qualitative evidence
escalation**:

| PR | Production diff | Validation strength |
|---|---|---|
| PR 9 | 0 prod mods (test-surface-only fixture authoring) | Substrate surfaces sufficient for fixture authoring + integration tests against existing surfaces |
| PR 10 | Exactly 1 new file (`_compare.py`, 523 lines), 0 mods elsewhere | New read-side surface composable without modifying existing surfaces |
| PR 11 | 0 prod mods (test-surface-only end-to-end recomposition) | Full recomposition arc traversable without modifying ANY production surface — decomposition strategy operationally validated by end-to-end exercise |

The escalation registers as **the strongest cross-PR evidence
to date** that the decomposition strategy was sufficient. The
pattern travels into Gate 4 inheritance (§2.3) as the
validation criterion template for future Gate-X reliability
work.

**Note on PR 10's "exactly 1 new file":** PR 10 is the
deliberate exception — Gate 3's purpose required a new
production surface (the comparator). The 1-new-file outcome
is itself architectural-sufficiency evidence: even when
production additions are necessary, the addition stays
self-contained (no modifications to adjacent surfaces). PR 9
+ PR 11 demonstrate the surrounding case (0 additions, 0
modifications); PR 10 demonstrates the bounded case.

### 1.3 Three-authority-surface partition + PR 10 read-side structural parallel — preserved unchanged

Gate 2 §3.4 partition preserved unchanged across Gate 3:

- **Observation surface** — `emit_divergence_capture` +
  contextvar resolution (PR 4/PR 7).
- **Dispatch provenance surface** — `seed_dispatch_scope` +
  `_DispatchContext` (PR 7).
- **Authored expectation surface** — `emit_seed_expectation`
  + `drive_seed_fixture` + schema validator (PR 8).

PR 10 introduced an **emergent architectural parallel** at the
read side (per PR 10 close §1.6): `_compare.py`'s body
exhibits a three-stage structure (authority pre-checks →
divergence computation → report construction) that is
structurally parallel to PR 8's write-side §4.1.5.1 PR-INTERNAL
three-way authority partition.

**The PR 10 read-side parallel preserves as emergent
architectural archaeology**, NOT peer-class governance. PR 11
inherited the parallel unchanged; PR 11 framing + spec +
implementation did NOT promote the parallel to declared
governance. The user's redline at PR 10 close §1.6 — that
peer-class promotion requires framing-level decision, not
retrospective synthesis — held throughout Gate 3.

**Gate 3 close registers the read-side parallel as:**

> **Observed architecture with archaeological value, NOT
> declared governance with mechanical enforcement.**

If a future Gate-X phase recomposes additional read-side
surfaces, framing-level naming may then promote the parallel
to peer-class partition. Gate 3 close does NOT pre-empt that
decision.

### 1.4 Four-walker Layer 2 partition operational

PR 4 + PR 8 + PR 9 + PR 10 walkers operate against the
codebase at Gate 3 close. Each walker protects a distinct
ontology; parallel-not-extension boundary preserved:

| Walker | Target | Ontology | Population |
|---|---|---|---|
| PR 4 (`test_pr4_participation_creep.py`) | Narrowing-subsystem production sources | Production-import-topology (one-directional flow) | 1 test |
| PR 8 (`test_pr8_seed_surface.py`) | `_seed.py` | Orchestration-participation (5-symbol bounded toolbox) | 5 tests |
| PR 9 (`test_pr9_fixture_discipline.py`) | `tests/corpus/fixtures/*.py` | Declarative-fixture-data (single-symbol-gate) | 2 tests |
| **PR 10 (`test_pr10_comparator_discipline.py`)** | **`_compare.py`** | **Read-only-interpretive-authority (zero-symbol-gate)** | **2 tests** |

PR 11 added no fifth walker. The four-walker partition is
the Gate 3 close gate-level inventory; PR 12 (if promoted)
or Gate 4 / future-gate work may add walkers IF new authority
surfaces require admission-ontology protection. The four
walkers share AST mechanics; they do NOT share ontology.

**Closing sentence (verbatim at every walker's module
docstring):** *"Shared AST mechanics do not imply shared
ontology."*

Future "walker unification" cleanup proposals are rejected at
the spec layer per PR 10 spec §4.2.1 + PR 11 framing §3.3 +
this §1.4. The protection is operational discipline, not just
documentation.

### 1.5 Cleanup-pressure-resistance class final inventory — 10 members

The cleanup-pressure-resistance class at Gate 3 close: **10
members** (unchanged from PR 10 close §1.7). PR 11 surfaced
**no new candidate members** (per PR 11 close §1.8). The
class is now populatable across **five reliability phases**
(PR 6 + PR 7 + PR 8 + PR 9 + PR 10):

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
| 10 | Speculative-reserved-imports rejection (import-set compare-as-persisted) | PR 10 | Spec §4.1.2 amendment + Step-N imports discipline + framing §3.6 form #5 sibling archaeology |

**Class promotion evaluation at Gate 3 close:**

Per Gate 3 framing §6.1: "three reliability phases corroborate
the class's populatability; promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` candidacy remains
gated on a fourth phase populating under genuinely independent
conditions."

**Status: PROMOTE the class to named methodology.** The
five-phase populating significantly exceeds the four-phase
bar. Each member's protection has been operationally enforced
across independent PRs:
- PR 6 (member 2): Layer 3 lint at structural-backstop scope.
- PR 7 (members 1, 3, 4, 5, 6): five members from substrate
  authoring work.
- PR 8 (members 7, 8): two members from boundary work.
- PR 9 (member 9): one member from consumption-surface work.
- PR 10 (member 10): one member from recomposition surface
  work.

Five-phase populating + ten-member inventory + operational
enforcement at every member's protection placement = the
class promotes to `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`
named methodology candidate.

Gate 4 framing inherits the class as **promoted-class**
methodology; future Gate-X PRs evaluate their own
cleanup-pressure-resistance class member candidacies against
the same four-criterion standard (genuine cleanup pressure /
prevented real erosion / recurred independently / required
active enforcement).

### 1.6 **PROMOTION** — candidate carrier #16 → active carrier #16

**Gate 3 framing §6.1 promotion evaluation criteria:**

| # | Criterion | Status at Gate 3 close |
|---|---|---|
| 1 | Gate-3-LOCAL form traveled verbatim through ≥4 Gate 3 surfaces (comparator module docstring + ≥1 test module docstring + ≥1 commit message body + ≥1 PR-level artifact body) | **MET: 12 surfaces** (PR 10's 8 + PR 11's 4; per PR 10 close §1.2 Signal 4 + PR 11 close §1.5) — significantly exceeds threshold (3x over) |
| 2 | No counter-example surfaced during Gate 3 implementation (no architectural deliverable required infrastructure-shape: subsystem / strategy / plugin registry / configuration object) | **MET** — PR 10 shipped as pair-input pure-functional read surface; PR 11 introduced ZERO new abstractions; zero seam-collapse pressure surfaced operationally |
| 3 | The generalized form holds without exception language — Gate 3 close can write *"Reliability work proves topology, not infrastructure"* without carving out Gate-3-specific circumstances | **MET** — the form applies to PR 9 substrate (topology), PR 10 comparator (topology not subsystem), PR 11 recomposition (topology traversal not new infrastructure) without per-PR carving |

**All three criteria MET. Gate 3 close PROMOTES candidate
carrier #16 to active carrier #16:**

> **Carrier #16 (active, promoted at Gate 3 close 2026-05-11):**
>
> **Reliability work proves topology, not infrastructure.**

**Active carrier count at Gate 3 close: 17** (#1–#15 from
prior PRs + #16 newly promoted + #17 introduced at Gate 3
framing). Phrasing discipline at Gate 4 + future-gate work:
"**17 active carriers**" (NOT "16 active + candidate #16"
anymore — candidate #16's status is now retired; the active
form is the canonical reference).

**Why promotion is earned (not declared):**

The candidacy preserved across Gate 3 framing → PR 10
framing → PR 10 spec → PR 10 implementation (8 surfaces) →
PR 11 framing → PR 11 spec → PR 11 implementation (4 surfaces)
without ever being implicitly promoted. The asymmetric
ordering (carrier #17 primary + Gate-3-LOCAL form secondary
with substrate marking) preserved verbatim at every site.
PR 10 + PR 11 surfaces consistently wrote "16 active carriers
+ candidate #16" — never "17 active carriers." The discipline
held under operational implementation pressure, NOT just at
framing-time declaration.

Per Gate 3 framing §6.1 + cursor §"Why candidate, not
promoted": "The candidate matures and promotes at Gate 3
close. The evaluation IS the discipline, not the prediction.
Promotion is earned, not assumed." Gate 3 close performs the
evaluation explicitly + finds all three criteria met + makes
the promotion call.

**Operational placement of newly-active carrier #16:**

Future Gate-X reliability work inherits **17 active carriers**
verbatim. Gate 4 framing's §3.1 carrier inheritance section
will list carrier #16 alongside #1-#15 + #17. New PRs'
framing/spec/implementation artifacts must travel #16 verbatim
in carrier blocks. The previous "candidate carrier #16
corroboration substrate" marking is now obsolete; the form
travels as active carrier with no substrate marking
qualifier.

**Gate-X-LOCAL governing sentence forms remain available** as
PR/gate-scoped discipline carriers. Future gates may introduce
their own Gate-X-LOCAL forms (e.g., "Gate 4 proves X, not Y")
under the canonicalized methodology pattern, but the
generalized active carrier #16 governs as gate-overarching
discipline.

### 1.7 §5.3 candidate methodology observation — second-instance evaluation

PR 10 close §5.3 registered as first-corroborated-instance
candidate methodology observation:

> Framing-time pressure prediction operates load-bearing
> through absence rather than rejection.

PR 11 contributed **second-instance ABSENCE outcome** (per
PR 11 close §1.6 + framing §6.4 asymmetric weighting). Both
PR 10 + PR 11 predicted cleanup-pressure forms at framing
time; none surfaced during implementation.

**Two-instance evidence summary:**

| Instance | PR | Predicted forms (framing) | Surfaced? | Outcome |
|---|---|---|---|---|
| 1 | PR 10 | Helper merger / persistence creep / walker abstraction | None | ABSENCE |
| 2 | PR 11 | Helper merger / premature surface normalization / fixture widening / recomposition smoothing | None | ABSENCE |

**Gate 3 close evaluation: STRENGTHEN candidacy + defer
naming pending third-instance corroboration.**

Per PR 11 framing §6.4: absence STRENGTHENS candidacy
(cause-not-coincidence). Both instances strengthen the
candidacy. But two-instance is at the bar; promotion to
named methodology — matching the cleanup-pressure-resistance
class's three-reliability-phase bar — requires one additional
corroborating instance under independent conditions.

**Status: strong-candidate-methodology pending Gate 4 or
future-gate third-instance corroboration.**

If Gate 4 implementation encounters predicted-but-absent
cleanup-pressure forms (the framing predicts; implementation
doesn't surface them), the three-instance bar is met and the
methodology promotes at Gate 4 close. If Gate 4 implementation
surfaces predicted forms (rejection outcome), the candidacy
preserves at two-instance status without invalidation per the
asymmetric weighting framing.

**Candidate phrasing (per cursor §"Methodology corroborations"
+ framing §5.3 + PR 11 close §1.6):**

> **(candidate methodology observation, two-instance
> corroborated, awaiting third-instance promotion)**
>
> **Framing-time pressure prediction operates load-bearing
> through absence rather than rejection. Predicted cleanup-
> pressure forms that do NOT surface during implementation
> are evidence the framing-level protections shaped decisions
> as cause, not coincidence — particularly when framing
> elevates predicted-pressure-resistant goals to named-
> discipline status.**

The candidate registers in `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`
as **strong-candidate** pending third-instance corroboration.

### 1.8 Three-PR amendment-at-incarnation catch-point migration — candidate methodology

PR 9 + PR 10 + PR 11 collectively produced a **three-instance
catch-point migration progression** for grounding-time
amendments (per PR 11 close §1.2 + §5.1):

| PR | Catch point | Discipline state |
|---|---|---|
| PR 9 | Step 2 implementation post-Step-1 | Grounding-discipline at implementation surface |
| PR 10 | Step 1 implementation prep (read-before-implement) | Grounding-discipline at implementation-prep surface (earlier catch) |
| PR 11 | Framing/spec drafting time (six grounded reads at framing→spec convergence) | Grounding-discipline at framing-spec drafting time (zero incarnation amendments) |

The progression encodes **maturation of
`feedback_ground_specs_in_actual_files`** discipline. The catch
point migrates earlier across PRs, ultimately to before any
spec text drafts that could later require amendment.

**Gate 3 close evaluation: STRONG-CANDIDATE methodology;
register but defer naming.**

Three-instance corroboration meets the typical bar, but the
progression is **descriptive** (catch point migrates earlier)
rather than **prescriptive** (here is the discipline future
PRs should adopt). The prescriptive form requires
interpretation — is this generalizable to all reliability
phases, or is it specific to A.5.3.2's three-PR arc?

Plausible prescriptive forms:

1. *"Grounding discipline matures by catch-point migration;
   adopt the earliest-feasible catch point at each phase."*
2. *"`feedback_ground_specs_in_actual_files` is operationally
   strongest at framing/spec drafting time (before incarnation
   surfaces could require amendment)."*
3. *"Framing→spec convergence is the canonical grounded-read
   discipline boundary."*

Gate 3 close does NOT pre-empt naming. The candidate registers
in `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` as
**strong-candidate** pending:

- Gate 4 corroboration that the migration continues (catch
  point migrates further OR holds at framing/spec drafting
  time as terminal).
- OR future-gate work explicitly adopting the migration
  pattern at framing-time.

Either corroboration strengthens the candidate toward
promotion as named methodology.

### 1.9 Conditional PR 12 disposition — **DEFER**

PR 11 framing §5.5 established the conditional PR 12 trigger
criterion:

> **PR 12 (conditional join helper) triggers if join
> boilerplate repeats at ≥4 call sites AND if preserving
> decomposition (i.e., requiring callers to perform the join
> explicitly) becomes harder to defend than abstracting it.**

**Evaluation at Gate 3 close:**

| Clause | Evidence | Status |
|---|---|---|
| ≥4 call sites | PR 11 contributed 3 call sites (each test = 1); Gate 4 framing may project +2-3 additional → in reach but not yet decisive | NOT YET MET (3 sites < 4) |
| Qualitative second clause: preserving decomposition harder than abstracting | PR 11 ABSENCE outcome — no recomposition-smoothing pressure surfaced; PR-11-LOCAL discipline operated cleanly; call-site awkwardness (4-5 lines per call site) accepted as evidence the decomposition held | NOT MET (current evidence: decomposition preservation is NOT harder than abstraction at this scale) |

Both clauses point to defer. The framing default lean
(framing §5.5: "framing default lean: defer") + PR 11 ABSENCE
outcome (corroborates the lean) + the qualitative judgment at
3-call-site evidence (preserving decomposition remains
defensible) converge on the same disposition.

**Gate 3 close disposition: PR 12 DEFER.**

The conditional PR 12 stays as conditional Gate-3-or-later-
gate work pending Gate 4 framing's projection of additional
join call sites:

- If Gate 4 projects ≥1 additional join site (making cumulative
  ≥4): re-evaluate the qualitative second clause at Gate 4
  framing time.
- If Gate 4 surfaces operational evidence that preserving
  decomposition becomes harder than abstracting (e.g., the
  4-5 line boilerplate grows or proliferates across surface
  classes): promote the PR 12 join helper at that point.
- Otherwise: PR 12 stays conditional indefinitely, or
  graduates to **rejected** if Gate 4 + future-gate evidence
  confirms decomposition preservation remains defensible.

**Conditional PR 12 contract for Gate 4:**

> If Gate 4 framing projects join-site proliferation OR
> surfaces operational evidence that preserving decomposition
> becomes harder than abstracting, **propose PR 12 framing at
> Gate 4 framing time** — author the join helper at framing-
> level decision, NOT as an in-flight implementation
> abstraction. If Gate 4 evidence does not surface the
> trigger, the conditional preserves; Gate 5 / future-gate
> work may re-evaluate.

### 1.10 Recomposition-through-existing-seams as first-instance candidate methodology

PR 11 framing §2.1 + §2.2 introduced **recomposition-through-
existing-seams** as the governing posture for PR 11. The
operational placement at PR 11 close (§1.4):

> **PR 11 traverses the decomposition seams established by
> Gate 2 + Gate 3 substrate work without erasing them.
> Call-site awkwardness during recomposition is acceptable
> evidence that the decomposition boundaries held.**

The discipline operated cleanly at PR 11 (per PR 11 close
§1.4 + §1.8 — zero recomposition-smoothing pressure
surfaced). **First-instance evidence** at Gate 3 scope.

**Gate 3 close evaluation: STRONG-CANDIDATE methodology;
register as first instance pending corroboration.**

The recomposition-through-existing-seams discipline is a
**recomposition-scope methodology** — it applies when a phase
is exercising existing decomposition seams via end-to-end
traversal. The candidate phrasing:

> **(candidate methodology, one-instance corroborated)**
>
> **Recomposition through existing seams is the correct
> shape when a phase exercises decomposition substrate end-
> to-end. Successful recomposition is evidence the
> decomposition was real; it is NOT justification for
> collapsing seams back into orchestration helpers.**

The methodology is structurally distinct from carrier #16's
generalized form (which governs ALL reliability work) and
from carrier #17's recomposition-preserves-authorship form
(which governs the comparator surface specifically). The
candidate's scope is the **recomposition phase pattern** at
gate or phase level.

**Registration:** `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`
candidate, awaiting corroboration when a future Gate-X phase
recomposes additional decomposition seams (e.g., chain-step
seeding per carrier #15's third clause framing pass).

### 1.11 0-prod-mod-as-architectural-sufficiency-signal — three-instance candidate methodology

The 0-production-source-modifications discipline elevated to
**named architectural sufficiency signal** at PR 11 (per
framing §5.2 + close §1.3) operates at gate-overarching scope
when applied as **gate-level validation criterion**.

**Three-instance evidence escalation across Gate 2 + Gate 3:**

| PR | Production diff | Validation strength |
|---|---|---|
| PR 9 | 0 prod mods | Substrate sufficient for test-surface-only fixture authoring |
| PR 10 | 1 new file (`_compare.py`, 523 lines) | New surface composable without modifying existing |
| PR 11 | 0 prod mods | End-to-end recomposition arc traversable without modifying production |

Three instances of qualitative evidence-escalation under
genuinely independent conditions (substrate / isolated
addition / end-to-end traversal). The candidate methodology:

> **(candidate methodology, three-instance corroborated under
> qualitative-evidence-escalation)**
>
> **When a reliability phase frames 0-production-source-
> modifications as named architectural sufficiency signal
> (NOT just clean diff hygiene), and the phase ships against
> the signal, the outcome registers as cumulative validation
> evidence that the decomposition strategy was sufficient.
> The signal travels operationally — at commit messages, at
> close artifacts, at gate-level inheritance — preserving
> the architectural meaning across reliability work
> archaeology.**

**Gate 3 close evaluation: STRONG-CANDIDATE methodology;
register for promotion at Gate 4 corroboration.**

Three-instance corroboration meets the typical bar. The
prescriptive form is straightforward: framings name 0-prod-
mod as architectural sufficiency signal when the substrate
work it validates is decomposition-strategy-bearing. If Gate
4 framing similarly names the signal AND Gate 4 implementation
ships against it (or against a justified-deviation
archaeology), the methodology promotes at Gate 4 close.

**Registration:** `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`
strong-candidate, near promotion threshold.

### 1.12 Step N.5 surgical cadence — three-times corroborated (Gate 2) + zero-times-at-Gate-3

Step N.5 surgical cadence corroboration count at Gate 3 close:

- PR 8 Step 4.5 (first instance, Gate 2; per PR 8 close §5.2).
- PR 9 Step 2.5 (second instance, Gate 2; per PR 9 close
  §1.2 + §5.2).
- PR 9 Step 5.5 (third instance, Gate 2; per PR 9 close §1.2
  + §5.2).
- PR 10: zero corroborations (per PR 10 close §4 archaeology).
- PR 11: zero corroborations (per PR 11 close §4 archaeology).

**Cumulative across Gate 2 + Gate 3: 3 instances** (all from
Gate 2). The 3-times-corroborated status established at Gate
2 close §5 preserves intact through Gate 3 close. The pattern
is operationally available to Gate 4 + future-gate work
without re-framing.

**Gate 3 close evaluation: methodology continues as-is.** The
Step N.5 cadence is canonicalized methodology; Gate 3's
zero-corroborations is reportable archaeology (no mid-flight
guidance surfaced requiring surgical commits), NOT
falsification of the methodology.

### 1.13 Four-variant amendment-at-incarnation taxonomy — complete cross-PR inventory

At Gate 3 close, the four-variant amendment-at-incarnation
cluster is fully populated across Gate 2 + Gate 3:

| Variant | First-instance PR | Subsequent instances | Total |
|---|---|---|---|
| Drafting-time | PR 7 spec §4.5 | PR 8 spec §4.5 | 2 |
| Implementation-time | PR 8 §1.3 (cluster #5–#7) | None at Gate 3 | 3 (cluster) |
| Verification-time | PR 8 Step 4.5 | PR 11 zero (the cleanest arc — no verification-time drift surfaced) | 1 |
| Grounding-time | PR 9 §4.7 amendment 2026-05-11 | PR 10 §4.4 amendment 2026-05-11 (earlier catch) | 2 |

PR 11 added **zero** instances to any variant — the **first
reliability PR to ship clean across all four variants** (per
PR 11 close §1.2). The cleanest arc is itself
methodologically meaningful: when discipline operates at
framing/spec drafting time (per §1.8 above), the variants
have no surface to fire at.

**Gate 3 close evaluation: four-variant taxonomy preserves
as canonicalized methodology.** Promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` carries
forward; Gate 4 + future-gate framings continue to apply
the taxonomy as-is. PR 11's zero-amendment outcome is
**candidate methodology** (per §1.8) for naming the
framing/spec-drafting-time terminal-catch-point.

---

## 2. What Gate 4 inherits from Gate 3

### 2.1 The validated comparator + the recomposition arc

`forge_bridge/corpus/_compare.py` (PR 10) is the **validated
read-side substrate**. PR 11 operationally exercised the
comparator end-to-end against all three PR 9 fixtures; the
divergence-report-shape + the four authority pre-checks + the
fresh-list-allocation discipline + the §4.2 binding behavioral
commitment ("compare as persisted") all hold under three
distinct narrowing-outcome conditions (no-divergence single-
survivor; no-divergence multi-match; intentional divergence
no-keyword-match).

Gate 4 inherits the comparator as:

- **Stable consumption surface** — `compare_records(observation,
  expectation) -> DivergenceReport` per PR 10 §4.1.6
  reference implementation.
- **Joinability assumed** — Gate 4 callers join records by
  `fixture_id` (Gate 2 close §2.1 foundational dependency).
- **Pair-input lock preserved** — no batch-input variant
  (PR 10 framing §5.2 + PR 11 §7 item 11 non-acquisition
  commitment).
- **Within-surface scope** — chat-handler arbitration surface
  only (per binding framing clarification on cross-surface
  unbinding; Gate 3 framing §6.3).

### 2.2 The recomposition arc as consumption pattern

PR 11's three integration tests ship as the **canonical
recomposition-arc test pattern** for Gate 4:

```python
# Canonical pattern — preserved across Gate 4 fixture-driven
# recomposition tests if/when they ship.
corpus_dir = _apply_pr9_patches(monkeypatch, tmp_path)
drive_seed_fixture(**FIXTURE)
records = _read_records(corpus_dir)
matching = [r for r in records if r.get("fixture_id") == FIXTURE["fixture_id"]]
observation = next(r for r in matching if r["record_kind"] == "observation")
expectation = next(r for r in matching if r["record_kind"] == "expectation")
report = compare_records(observation_record=observation, expectation_record=expectation)
# Four-key DivergenceReport assertions.
```

Gate 4 may reuse the pattern verbatim. Underscored-private PR 9
imports remain test-internal archaeology surfaces per PR 11
spec §4.1.2 framing.

### 2.3 The three-PR architectural sufficiency signal as validation template

Gate 4 framing inherits the **template** PR 9 + PR 10 + PR 11
established:

1. Framing names architectural sufficiency signal as goal
   (NOT just "clean diff hygiene").
2. Spec encodes the signal as a regression contract.
3. Implementation respects the signal at each commit
   (verified at each Step verification).
4. Close artifact documents the signal as architectural
   archaeology.

If Gate 4's architectural commitment is decomposition-
strategy-bearing (i.e., not just feature work), Gate 4 framing
should adopt the template. If Gate 4 has a justified
deviation (a real production need surfaces), framing names
+ justifies explicitly per PR 11 spec §5.2 deviation
protocol.

### 2.4 17 active carriers + carrier #17 + Gate 4-specific candidate carriers

Gate 4 inherits **17 active carriers**:

- Carriers #1–#15 (PR 4 + PR 5 + PR 6 + PR 8 lineage; canonical
  sources `forge_bridge/corpus/_capture.py:6-135` +
  `forge_bridge/corpus/_seed.py:19-135`).
- **Carrier #16 (newly promoted at Gate 3 close)**:
  *"Reliability work proves topology, not infrastructure."*
- Carrier #17 (introduced at Gate 3 framing):
  *"Recomposition preserves authorship..."* (full form per
  Gate 3 framing §6.2).

**Phrasing discipline at Gate 4:** "**17 active carriers**"
(no candidate-substrate marking; candidate #16's status is
retired post-promotion).

Gate 4 framing may introduce new candidate carriers under
similar maturation discipline. The carrier-#16 promotion
trace at Gate 3 close (§1.6 above) is the canonical example:
candidate → operational corroboration → close-time evaluation
→ promotion or preservation.

### 2.5 Four-walker Layer 2 partition operational

PR 4 + PR 8 + PR 9 + PR 10 walkers preserve unchanged at
Gate 3 close. Gate 4 inherits the four-walker partition as
**non-revisitable architecture**:

- Future "walker unification" cleanup proposals rejected
  at the spec layer (per §1.4 + PR 10 spec §4.2.1).
- New walkers may be added IF Gate 4 surfaces a NEW authority
  surface requiring admission-ontology protection. Each new
  walker preserves the parallel-not-extension boundary;
  shared AST mechanics ≠ shared ontology.

### 2.6 Three-authority-surface partition + PR-INTERNAL three-way authority partition + PR 10 read-side structural parallel

- **Three-authority-surface partition** (Gate 2 §3.4):
  observation / dispatch provenance / authored expectation —
  preserved as **non-revisitable governance** (per Gate 2
  close §2.4 item 1).
- **PR-INTERNAL three-way authority partition (PR 8 write-
  side §4.1.5.1)**: authored expectation semantics /
  orchestration semantics / persistence topology — preserved
  intact.
- **PR 10 read-side structural parallel** (per §1.3 + PR 10
  close §1.6): authority pre-checks / divergence computation
  / report construction — preserved as **emergent
  archaeology**, NOT peer-class governance. Future Gate-X
  promotion to peer-class requires framing-level decision.

### 2.7 Cleanup-pressure-resistance class (10 members, promoted-class)

The 10-member class is promoted-class methodology at Gate 3
close (per §1.5). Gate 4 inherits the class as:

- **Promoted methodology** in `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`.
- **10-member inventory** unchanged unless Gate 4 surfaces a
  new candidate member meeting the four-criterion standard.
- **Per-member protection** operationally enforced; cleanup
  PRs proposing to erode any member's protection rejected
  at the spec layer.

### 2.8 §5.3 + recomposition-through-existing-seams + 0-prod-mod-as-architectural-sufficiency strong-candidate methodologies

Three candidate methodologies registered at Gate 3 close
(per §1.7 + §1.10 + §1.11):

1. **Framing-time pressure prediction through absence**
   (§1.7) — two-instance corroborated; awaiting third-
   instance promotion at Gate 4 or future-gate.
2. **Recomposition through existing seams** (§1.10) — first-
   instance corroborated; awaiting Gate-X corroboration.
3. **0-prod-mod-as-architectural-sufficiency-signal** (§1.11)
   — three-instance corroborated; near promotion threshold.

Gate 4 framing/spec/implementation may explicitly invoke any
of these as candidate methodology references. If Gate 4
operationally corroborates any, Gate 4 close evaluates
promotion to named methodology.

### 2.9 The four §7.3 ontological questions remain open

Gate 2 close §7.3 + Gate 3 framing §2.3 (Path B locked)
deferred the four ontological questions about cross-surface
fixture identity to Gate 4 or beyond. Gate 3 close inherits
the questions unchanged + hands forward to Gate 4 (per §6
below):

1. Does one expectation target one observation surface or
   multiple?
2. Does `fixture_id` identify a logical prompt or a specific
   arbitration surface?
3. Is cross-surface divergence meaningful or noise?
4. Does Gate 4 compare within surfaces or across them?

**Carrier #15's third clause remains binding**: cross-surface
expectation semantics require a dedicated framing pass before
implementation proceeds. Gate 4 framing decides whether to
address the four questions (Path A) or defer further (Path B
continued).

---

## 3. What Gate 4 / future-gate work must NOT do

Gate 3 close ships the following decisions as **non-revisitable
at gate scope** (extending Gate 2 close §2.4):

1. **All Gate 2 close §2.4 items (1–10) remain non-revisitable.**
   Three-authority-surface partition; `forge_bridge.__all__` at
   19 symbols; `KNOWN_SOURCE_VALUES` + `_KNOWN_RECORD_KINDS`
   2-element locks; expectation record schema (3 required
   keys); four-walker Layer 2 partition (extended from
   three-walker at Gate 2); carrier #10's chat-handler-surface
   topology; cleanup-pressure-resistance class members #1–#9
   protections; amendment-at-incarnation four-variant
   taxonomy; Step N.5 surgical cadence; PR 9 0-prod-mod as
   validation signal.

2. **Comparator surface (`compare_records` +
   `DivergenceReport` + `ComparatorInputError`)** preserves
   as PR 10 spec §4.1.6 reference implementation. Pair-input
   shape locked; no batch-input variant; no async; no class
   method; no I/O.

3. **Comparator stays corpus-internal at Gate 3 close.**
   `forge_bridge.__all__` at 19 symbols. Promotion to public
   API requires framing-level decision at first concrete
   external consumer (deferred per PR 10 spec §5.7).

4. **§4.2 binding behavioral commitment ("compare as
   persisted")** at function-body layer preserves. Future
   PRs must not introduce pre-comparison normalization
   (sort / canonicalize / repair / semantic coercion) at the
   comparator OR at caller-side wrapping that defeats the
   commitment.

5. **Cleanup-pressure-resistance class member #10**
   (speculative-reserved-imports rejection) protection
   preserves. Future corpus modules must follow imports-land-
   when-used discipline; no speculative-reserved imports at
   the import-set surface.

6. **Newly-active carrier #16** (*"Reliability work proves
   topology, not infrastructure"*) governs ALL reliability
   work at and beyond Gate 4. Phrasing discipline: "**17
   active carriers**" (NOT "16 + candidate #16" anymore).

7. **Carrier #17** (recomposition preserves authorship)
   governs recomposition surfaces. Future cleanup pressure
   to collapse the three-authority-surface partition through
   interpretive synthesis is rejected at the spec layer.

8. **Binding framing clarification on cross-surface
   unbinding** preserves. Cross-surface comparator semantics
   are intentionally unbound; Path A (addressing the four
   §7.3 ontological questions) is Gate 4's optional
   surfacing decision.

9. **PR 10 read-side structural parallel** preserves as
   **emergent archaeology**, NOT peer-class governance.
   Promotion to peer-class requires framing-level decision.

10. **Recomposition-through-existing-seams discipline**
    (per §1.10 + PR-11-LOCAL precedent): future-gate
    recomposition phases must traverse decomposition seams
    explicitly; introducing production abstractions whose
    primary purpose is "making recomposition cleaner" is
    rejected at the spec layer.

11. **Architectural sufficiency signal target** (per §1.11):
    when a reliability phase frames 0-prod-mod as named
    architectural sufficiency signal, the target is goal
    not constraint; justified deviations register as
    archaeology, not silent additions.

12. **Conditional PR 12 disposition** preserves as
    conditional (per §1.9). Gate 4 framing evaluates;
    promotion / defer / reject is Gate 4 close scope.

13. **The carrier-#16 promotion-trace archaeology** at this
    close §1.6 is the canonical example of "promotion is
    earned, not declared." Future candidate-carrier
    promotions follow the same discipline: candidacy-with-
    substrate-marking → corroborated travel through specified
    surfaces → close-time evaluation against explicit criteria
    → promotion or preservation.

---

## 4. Per-PR archaeology summary

### 4.1 PR 10 — comparator helper (`cf2b7ee`)

**Implementation arc: 7 commits** (spec + amendment + 5 steps;
`54d0ab9` → `d04753c`).

**Deliverable:** `forge_bridge/corpus/_compare.py` (523 lines,
single new production file); 2 new test modules (517 total
lines).

**Key contributions:**
- `compare_records(observation, expectation) -> DivergenceReport`
  pair-input pure-functional read surface.
- Cleanup-pressure-resistance class member 10 (speculative-
  reserved-imports rejection at import-set surface).
- Four-walker Layer 2 partition (added 4th walker; zero-symbol-
  gate value-lock).
- Single-center architectural concentration at Step 3.
- 8 Gate-3-LOCAL governing sentence travel surfaces.
- Grounding-time amendment §4.4 at Step 1 prep (earlier catch
  than PR 9).
- Read-side structural parallel to PR-8-INTERNAL write-side
  partition (emergent archaeology, NOT peer-class governance).
- §5.3 candidate methodology observation first instance
  (ABSENCE outcome).

**See:** `A.5.3.2-PR10-CLOSE.md` (`cf2b7ee`) for full PR 10
archaeology.

### 4.2 PR 11 — end-to-end recomposition arc (this commit)

**Implementation arc: 4 commits** (spec + 3 steps;
`6a5df95` → `ae69fba`).

**Deliverable:** `tests/corpus/test_pr11_recomposition_arc.py`
(313 lines, single new test file); zero production source
modifications.

**Key contributions:**
- 3 recomposition arc integration tests (one per PR 9 fixture
  outcome class).
- ZERO spec amendments at any incarnation surface (the
  cleanest A.5.3.2 PR arc).
- 4 Gate-3-LOCAL governing sentence travel surfaces.
- PR-11-LOCAL traverses-not-erases-seams discipline operational.
- §5.3 candidate methodology observation second-instance
  ABSENCE outcome.
- 0-prod-mod-as-architectural-sufficiency continuity from
  PR 9 + PR 10 (three-PR escalation completed).
- Recomposition-through-existing-seams first-instance
  candidate methodology.

**See:** `A.5.3.2-PR11-CLOSE.md` (this commit) for full PR 11
archaeology.

### 4.3 Cumulative Gate 3 statistics

| Metric | Value |
|---|---|
| PR commits (PR 10 + PR 11) | 11 (7 + 4) |
| Total Gate 3 commits (incl. framing + close) | 13 |
| Production source files added | 1 (`_compare.py`) |
| Production source modifications elsewhere | 0 |
| Test source files added | 3 (PR 10's 2 + PR 11's 1) |
| Test surface lines added (cumulative across Gate 3) | ~1130 (PR 10's ~800 + PR 11's 313 + small fixture adjustments) |
| Cleanup-pressure-resistance class additions | 1 (member 10) |
| Layer 2 walkers added | 1 (PR 10) |
| Gate-3-LOCAL travel surfaces | 12 (8 + 4) |
| Test count at gate close (forge env) | 217 (210 baseline pre-PR-10 + 7 PR 10 + 3 PR 11 — wait, baseline was 207 pre-PR-10; 207 + 7 = 214 at PR 10 close; 214 + 3 = 217 at PR 11 close = Gate 3 close) |
| Spec amendments at incarnation (PR 10 + PR 11) | 1 (PR 10 §4.4 only; PR 11 had zero) |
| Step N.5 surgical commits | 0 (Gate 3 added zero corroborations) |
| Active carriers at gate close | 17 (15 inherited + #16 promoted + #17 introduced) |

---

## 5. Cross-PR methodology synthesis

### 5.1 The PR 10 + PR 11 architectural complement

PR 10 + PR 11 form an **architectural complement** at Gate 3
scope:

- **PR 10 = the substrate** (the comparator IS the new
  architecture).
- **PR 11 = the proof** (the recomposition arc IS the
  architecture's operational validation).

Neither PR alone closes the gate. Gate 3's architectural
commitment requires both: the comparator without the
recomposition proof is unexercised infrastructure; the
recomposition arc without the comparator is impossible.

This complement maps to **carrier #16 at gate scope**:
PR 10 proved the comparator is topology (NOT subsystem); PR 11
proved the topology is sufficient (NO infrastructure
extensions needed).

The complement is **the gate-arc shape** future Gate-X
reliability work may inherit when shipping decomposition →
recomposition arcs: framing names the substrate + the proof
together as paired deliverables at distinct PRs.

### 5.2 Single-center vs. cumulative multi-step concentration — Gate 3 contrasts continue

PR 10 close §1.8 established the **single-center
architectural-concentration** framing for PR 10 (Step 3 is
the single architectural-center). PR 11 close §4 implicitly
continues the framing: PR 11's Step 2 is the single
architectural-center (the three tests bundled in one atomic
commit per spec §6.2).

Contrast with PR 9's **cumulative multi-step concentration**
(Steps 3 + 4 = Gate 4 comparator-unblock proof surface; per
PR 9 close §1.8). The two framings are operationally distinct:

- **Single-center**: the architectural commitment lands at
  one atomic boundary (PR 10 Step 3; PR 11 Step 2).
- **Cumulative multi-step**: the architectural commitment
  spans multiple atomic boundaries (PR 9 Steps 3 + 4).

Both framings are correct at their respective PRs. Neither
generalizes prescriptively; future framings evaluate per-PR
whether the architectural concentration is single-center or
multi-step based on the work's structural shape.

Gate 3 close **registers the contrast as continuing emerging
taxonomy** (per PR 10 close §5.2). Promotion to named
methodology distinction is gated on future-gate corroboration
(when another single-center or multi-step PR ships under
genuinely independent conditions).

### 5.3 Carrier-#16 promotion trace as canonical example

The carrier-#16 promotion at this close §1.6 is the **canonical
example** of the maturation discipline at gate scope:

1. **Candidacy declared at framing time** (per Gate 3 framing
   §6.1) with explicit substrate marking ("Gate-3-LOCAL form
   = candidate carrier #16 corroboration substrate").
2. **Travel discipline preserved across implementation** —
   asymmetric ordering at every site (active primary + candidate
   secondary with substrate marking); phrasing discipline
   enforced ("16 active + candidate #16" verbatim).
3. **Close-time evaluation against explicit criteria** (§1.6
   table: criterion 1 surface count; criterion 2 counter-
   example absence; criterion 3 form generalization).
4. **Promotion or preservation** — Gate 3 close promotes.

Future candidate-carrier promotions at Gate 4 or beyond
follow the same trace. The discipline is operational, not
just documentation: **promotion is earned through travel
discipline + corroborated evidence**, not through declaration.

### 5.4 Pointer to `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`

Gate 3 close registers the following methodology promotions /
candidacies (consolidated from §1.5–§1.13):

| Methodology | Status at Gate 3 close | Promotion criteria |
|---|---|---|
| Cleanup-pressure-resistance class | **PROMOTED** | Five-phase populating (PR 6+7+8+9+10) significantly exceeds four-phase bar |
| Carrier #16 (`Reliability work proves topology, not infrastructure`) | **PROMOTED** | All three §6.1 criteria met; 12-surface evidence base |
| §5.3 framing-time-pressure-prediction-through-absence | Strong-candidate | Two-instance ABSENCE; awaiting third-instance corroboration |
| Three-PR amendment-at-incarnation catch-point migration | Strong-candidate | Three-instance descriptive progression; awaiting prescriptive form interpretation |
| Recomposition-through-existing-seams | First-instance candidate | One operational instance; awaiting Gate-X corroboration |
| 0-prod-mod-as-architectural-sufficiency-signal | Strong-candidate | Three-instance qualitative-evidence escalation; near promotion threshold |
| Step N.5 surgical cadence | Canonicalized methodology | 3-times-corroborated at Gate 2; available at Gate 4+ |
| Four-variant amendment-at-incarnation taxonomy | Canonicalized methodology | Established at Gate 2 close; PR 11 zero-instance archaeology preserved |
| Single-center vs. cumulative multi-step architectural concentration | Emerging taxonomy | Two-PR contrast (PR 9 vs. PR 10 + PR 11); awaiting third-instance interpretation |

`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` carries the
authoritative inventory. Future phase architects read the
seed file for the cross-gate methodology inheritance contract.

---

## 6. Four §7.3 ontological questions — handoff to Gate 4

Per Gate 2 close §7.3 + Gate 3 framing §2.3 (Path B locked
at Gate 3): the four ontological questions about cross-surface
fixture identity remain **open at Gate 3 close**:

1. **Does one expectation target one observation surface or
   multiple?** Open. Gate 3 stayed within chat-handler-only
   scope per Path B.

2. **Does `fixture_id` identify a logical prompt or a specific
   arbitration surface?** Open. PR 9 fixture_ids ("fix-pr9-
   single-survivor" etc.) are PR-9-anchored strings without
   surface-encoding; semantically interpretable either way.

3. **Is cross-surface divergence meaningful or noise?** Open.
   PR 11 exercised within-surface divergence (authored
   `expected_narrow=[]` vs. observed full-reachable-set) — the
   cross-surface variant remains unexercised.

4. **Does Gate 4 compare within surfaces or across them?**
   Open. The comparator pair-input shape locks within-surface
   per call; cross-surface composition is a caller-pattern
   decision NOT yet operationally exercised.

**Carrier #15's third clause remains binding** at Gate 4
inheritance:

> **Cross-surface expectation semantics require a dedicated
> framing pass before implementation proceeds.**

Any Gate 4 PR proposing chain-step seeding OR cross-surface
fixture identity OR cross-surface comparator semantics
**without a dedicated framing pass first** is rejected at
the spec layer.

**Gate 4 framing decides** whether to address the four
questions (Path A) or defer further (Path B continued). PR 11
close + this Gate 3 close do NOT prescribe a path. The
discipline is unchanged from Gate 2 close §7.3.

---

## 7. Reseed protocol — Gate 4 framing opening move

When Gate 4 framing session opens:

1. **Read this Gate 3 close artifact first.** §1 establishes
   what Gate 3 delivered (with carrier-#16 promotion at §1.6);
   §2 + §3 establish Gate 4 inheritance + non-revisitable
   decisions; §6 hands forward the four §7.3 ontological
   questions.

2. **Read PR 11 close artifact** (`A.5.3.2-PR11-CLOSE.md`,
   this commit) — sibling artifact. §1 + §2 + §4 are the
   load-bearing sections for the PR 11-scoped archaeology
   Gate 4 may reference.

3. **Read PR 10 close artifact** (`A.5.3.2-PR10-CLOSE.md`,
   `cf2b7ee`) — durable PR 10 archival state. §1 four
   architectural signals; §2 inheritance contract; §1.6
   read-side structural parallel (preserved at Gate 3 close
   as emergent archaeology).

4. **Read Gate 3 framing** (`A.5.3.2-GATE-3-FRAMING.md`,
   `2f70cbf`) for the gate-level inheritance contract Gate 3
   operated against. §6.1 candidate carrier #16 promotion
   criteria (now satisfied) + §6.3 binding framing
   clarification on cross-surface unbinding (preserved
   at Gate 4 inheritance).

5. **Re-read project memories:**
   - `project_state_2026_05_11_pr_11_implementation_closed.md`
     — supersede with Gate-3-CLOSED cursor at next session
     opening.
   - `feedback_cursor_before_retrospective_synthesis.md` —
     three-times-validated this session arc; applies at any
     major archaeology boundary.
   - `feedback_ground_specs_in_actual_files.md` — maturation
     to framing/spec-drafting-time discipline at PR 11 is the
     terminal-catch-point archaeology.
   - `feedback_counts_are_archaeology_grade.md` — applies to
     Gate 4 framing's test count anchors.
   - `feedback_writers_room_lead_with_views.md` — applies to
     Gate 4 framing decisions.
   - `feedback_deferral_first_class_governance.md` — applies
     to the four §7.3 ontological questions handoff at Gate 4.

6. **Newly-active carrier #16 governs Gate 4 reliability
   work:**

   > **Reliability work proves topology, not infrastructure.**

   Phrasing discipline at Gate 4: "**17 active carriers**"
   (NOT "16 active + candidate #16"). The promotion is
   complete; Gate 4 inherits #16 as active.

7. **Begin Gate 4 framing.** Gate 4's specific deliverables
   are undefined at Gate 3 close; the four §7.3 ontological
   questions are the canonical surfacing decision. Plausible
   Gate 4 surfaces include:
   - Cross-surface fixture identity framing pass (Path A from
     Gate 3 framing §2.3 unbinding clarification).
   - Chain-step seeding implementation (if cross-surface
     framing precedes).
   - Conditional PR 12 promotion (if join boilerplate
     proliferation surfaces; per §1.9).
   - Additional cleanup-pressure-resistance class members
     IF a new pressure form surfaces under independent
     conditions.

8. **Surface the framing for review** before drafting a Gate 4
   spec.

9. **The cadence carries unchanged:**
   - Framing → spec → spec-amendments-at-incarnation → steps
     → verification-amendments-if-surfaced → close.
   - Four-variant amendment-at-incarnation cluster + Step
     N.5 surgical cadence available without re-framing.
   - PR-N-LOCAL non-regeneration discipline preserved.
   - Test-internal archaeology surfaces (NOT public APIs)
     framing available if Gate 4 imports PR 11 helpers.

10. **The discipline carries unchanged.** Promotion is earned,
    not declared. Speculative authoring of new cleanup-pressure-
    resistance class members at framing time is rejected.
    Counts are archaeology-grade. Ground specs in actual
    files. Lead with views at structural seams.

---

## 8. Cross-references

- **`A.5.3.2-PR11-CLOSE.md`** (this commit) — sibling
  artifact; PR 11-scoped archaeology Gate 3 close synthesizes
  at gate scope.
- **`A.5.3.2-PR10-CLOSE.md`** (`cf2b7ee`) — durable PR 10
  archival state Gate 3 close synthesizes at gate scope; §1
  four architectural signals; §1.6 read-side structural
  parallel preserved as emergent archaeology.
- **`A.5.3.2-PR11-FRAMING.md`** (`97c3fb4`) — PR 11 binding
  pre-spec contract; §0 governing pair; §5.2 0-prod-mod
  elevated to architectural sufficiency signal; §6.4
  asymmetric weighting framing for §5.3 candidate
  observation; §11 same-commit Gate 3 close convergence
  responsibility split.
- **`A.5.3.2-PR11-SPEC.md`** (`6a5df95`) — PR 11
  implementation contract; §4.1 per-file derivation; §6
  atomic step decomposition (3 steps + close).
- **`A.5.3.2-PR10-FRAMING.md`** (`8ad7fe9`) — PR 10 binding
  pre-spec contract; pair-input lock; Layer 2 Option A;
  carrier #17 operational landing posture.
- **`A.5.3.2-PR10-SPEC.md`** (`54d0ab9` + amendment
  `6830888`) — PR 10 implementation contract; §4.1.6
  reference implementation; §4.4 amendment archaeology
  (sharpened Layer 1 semantics).
- **`A.5.3.2-GATE-3-FRAMING.md`** (`2f70cbf`) — gate-level
  inheritance contract; §6.1 candidate carrier #16
  promotion criteria (now satisfied per §1.6 above); §6.3
  binding framing clarification on cross-surface unbinding;
  §10 PR sequencing; §11 Gate 3 close criteria.
- **`A.5.3.2-GATE-2-CLOSE.md`** (`a6e42f0`) — gate-arc
  synthesis precedent; §2.4 non-revisitable decisions
  (extended at this §3 above); §7.3 four ontological
  questions (handed forward at §6 above).
- **`A.5.3.2-GATE-2-FRAMING.md`** (`ceac9b5`) — three-
  authority-surface partition (§3.4; preserved at Gate 3
  close); call-site-owned arbitration inputs binding
  framing clarification (preserved).
- **`A.5.3.2-PR9-CLOSE.md`** (`a6e42f0`) — three-fixture
  corpus Gate 3 consumed; integration test infrastructure
  PR 11 imported as test-internal archaeology surfaces.
- **`A.5.3.2-PR8-CLOSE.md`** (`b102010`) — PR-INTERNAL
  three-way authority partition (write-side §4.1.5.1)
  preserved at Gate 3 close; member #7 + member #8
  preserved.
- **`A.5.3.2-PR7-CLOSE.md`** (`b035c87`) — observation +
  dispatch-provenance surfaces Gate 3 consumed; members
  #1–#6 preserved.
- **`A.5.3.2-FRAMING.md`** — phase shape, objective lock.
- **`A.5.3.2-INSTRUMENT-CONTRACT.md`** — instrument shape,
  six interlocking structural-invariant pairs.
- **`A.5.3.2-GATE-1-SPEC.md`** — Gate 1 sequencing, three
  architecturally-prohibited patterns, helper signature,
  visual-asymmetry pattern.
- **`forge_bridge/corpus/_compare.py`** — PR 10 comparator
  module; carrier #17 + active #16 + Gate-3-LOCAL form
  carried verbatim.
- **`tests/corpus/test_pr11_recomposition_arc.py`** — PR 11
  recomposition arc test module.
- **`tests/corpus/test_pr10_comparator.py` +
  `test_pr10_comparator_discipline.py`** — PR 10 comparator
  test modules.
- **`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`** —
  promotion-candidate methodology seed; Gate 3 close
  promotes:
  - Cleanup-pressure-resistance class (10 members; five-
    phase populating).
  - Carrier #16 (`Reliability work proves topology, not
    infrastructure`).
  Strong-candidate registrations:
  - §5.3 framing-time-pressure-prediction-through-absence
    (two-instance ABSENCE).
  - Three-PR amendment-at-incarnation catch-point migration
    (three-instance descriptive progression).
  - 0-prod-mod-as-architectural-sufficiency-signal (three-
    instance qualitative-evidence escalation).
  First-instance candidacy:
  - Recomposition-through-existing-seams (PR 11 first
    instance).
  Emerging taxonomy:
  - Single-center vs. cumulative multi-step architectural
    concentration (PR 9 vs. PR 10 + PR 11 contrast).
- **Local memory updates this session arc:**
  - PR-11-implementation-closed cursor written pre-synthesis
    per `feedback_cursor_before_retrospective_synthesis`
    (third validation this session arc).
  - MEMORY.md index updated.
  - Push at implementation-arc boundary (origin/main parity
    at `ae69fba` before close-artifact drafting).
  - Gate-3-CLOSED cursor to be written at next session
    opening per cursor protocol.
- **Gate 3 commit chain (PR 10 + PR 11):**
  - `8ad7fe9` PR 10 framing.
  - `54d0ab9` PR 10 spec.
  - `6830888` PR 10 spec amendment 2026-05-11.
  - `3b75a1b` PR 10 Step 1.
  - `a4be3d7` PR 10 Step 2.
  - `00f4d75` PR 10 Step 3.
  - `68a6a28` PR 10 Step 4.
  - `d04753c` PR 10 Step 5 (final verification).
  - `cf2b7ee` PR 10 close artifact.
  - `97c3fb4` PR 11 framing.
  - `6a5df95` PR 11 spec.
  - `2c65746` PR 11 Step 1.
  - `1b81436` PR 11 Step 2.
  - `ae69fba` PR 11 Step 3 (final verification).
  - **THIS COMMIT** — PR 11 close + Gate 3 close (two
    artifacts at one commit).

---

End of Gate 3 close. The recomposition phase of the
decomposition → recomposition arc that PR 6/Gate 1 began and
Gate 2 advanced closes here. Gate 3 ships the comparator
helper (PR 10) + the end-to-end recomposition arc (PR 11) +
the three-PR architectural sufficiency escalation as the
operational validation that the Gate 2 + Gate 3 decomposition
strategy was sufficient.

**Carrier #16 promotes at this close.** The generalized form
governs all reliability work going forward:

> **Reliability work proves topology, not infrastructure.**

The cleanup-pressure-resistance class promotes at this close.
Five-phase populating + ten-member inventory + four-criterion
discipline = named methodology in `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`.

Three strong-candidate methodologies + one first-instance
candidate + one emerging taxonomy register for Gate 4 +
future-gate corroboration. The four §7.3 ontological questions
hand forward unchanged; Gate 4 framing decides Path A or
Path B continuation.

Gate 4 inherits a validated comparator + a corroborated
recomposition demonstration + an architecturally-sufficient
decomposition strategy + 17 active carriers + a four-walker
Layer 2 partition + a 10-member promoted-class cleanup-
pressure-resistance inventory + the cross-PR methodology
landscape.

**The decomposition was real. The recomposition preserves it.
Gate 4 advances.**
