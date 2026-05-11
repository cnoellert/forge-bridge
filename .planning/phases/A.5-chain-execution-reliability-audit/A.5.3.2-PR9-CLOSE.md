# A.5.3.2 PR 9 — Close (fixture corpus + end-to-end integration)

**Status:** Durable archival state. PR 9 closes Gate 2's third
and final PR. The implementation arc that began at framing
commit `5628817` (2026-05-11) closes at this commit. PR 9 ships
purely as test-surface additions — **0 production source file
modifications** — operationalizing the PR 7 + PR 8 decomposition
strategy as a consumption surface.

This artifact mirrors PR 8 close (`b102010`) structure §1-§8 +
reseed protocol. **The Gate 2 close artifact
(`A.5.3.2-GATE-2-CLOSE.md`) ships at the same commit as this
artifact** per Gate 2 framing §11.6 + PR 8 close §7 step 11.

**Cross-artifact responsibility split (per close convergence):**

- **PR 9 close (this artifact)** owns:
  - 10-commit PR 9 archaeology (§4)
  - Grounding-time amendment as PR 9's specific contribution
    (§1.3 + §5.1)
  - Fixture corpus grounding trace (§1.1)
  - Step N.5 surgical pattern corroboration at PR 9 (§5.2)
  - Cumulative-architectural-concentration framing for Steps
    3 + 4 (§5.3)
  - PR 10 / Gate 3 PR-level inheritance contract (§2)
- **Gate 2 close** owns:
  - Gate-arc synthesis across PR 7 + PR 8 + PR 9
  - Complete 4-variant amendment taxonomy with PR-of-origin
  - Promotion-candidate inventory (full)
  - Gate 3 inheritance contract at gate-level
  - The four §7.3 ontological questions handoff

No section of this artifact duplicates Gate 2 close's gate-level
synthesis. Where overlap surfaces, this artifact defers to
Gate 2 close.

---

## 1. What PR 9 established

### 1.1 Three-fixture corpus operational end-to-end

PR 9 ships a hand-grounded, deliberately small seed-fixture
corpus consumed end-to-end through the real `chat_handler`
arbitration pipeline. Three fixture modules under
`tests/corpus/fixtures/`, each one Python module + one
top-level `FIXTURE: dict` constant:

| Module | Prompt | Expected narrowing outcome | Grounded trace |
|---|---|---|---|
| `fix_single_survivor.py` | `"ping forge"` | `["forge_ping"]` (PR21 collapse) | PR14 (2) → PR21 collapse to 1; pr20_condition_met=True; collapse_occurred=True |
| `fix_multi_match.py` | `"list"` | `["forge_list_projects", "flame_list_libraries"]` (no collapse) | PR14 (2) → PR21 no reduction (tie at overlap=1); pr20_condition_met=False; collapse_occurred=False |
| `fix_no_keyword_match.py` | `"what time is it"` | `[]` (aspirational author claim) | PR14 fallback (4) → PR21 no reduction (max-overlap=0); observed = full controlled set; divergence intentional |

Each prompt was **empirically grounded** at Step 2 against
direct invocation of `filter_tools_by_message` +
`deterministic_narrow` against the controlled 4-tool reachable
set. The trace archaeology lives at Step 2 commit body
(`50a7caf`) verbatim. Per
`feedback_ground_specs_in_actual_files.md`: no fixture content
is inferred from documentation; all is grounded against live
code surfaces.

The corpus is **data + one orchestration call only** per
member #9 protection (fixture-surface-data-discipline; framing
§6.1). Each fixture module ships:

- Module docstring carrying 15 inherited carriers + binding
  framing clarification per relevance-by-file ordering
  (carrier #15 at top).
- One top-level `FIXTURE: dict` constant carrying exactly the
  3 PR-8-locked keys (`fixture_id`, `prompt`,
  `expected_narrow`).
- Zero imports beyond `__future__` annotations.
- Zero functions, zero classes, zero non-FIXTURE constants.

Mechanical enforcement: the PR 9 Layer 2 walker
(`tests/corpus/test_pr9_fixture_discipline.py::_fixture_corpus_references`)
walks `tests/corpus/fixtures/*.py` (excluding `__init__.py`)
and rejects any forbidden corpus import. The single-symbol-gate
`_FIXTURE_PERMITTED_IMPORTS` frozenset admits exactly one
symbol (`forge_bridge.corpus._seed.drive_seed_fixture`).

**The fixture corpus is not a fixture-management framework.**
No registry, no factory, no generator, no parametrization. Each
fixture is named explicitly + consumed explicitly by its
matching integration test. Per the governing sentence: PR 9
proves topology, not infrastructure.

### 1.2 Step N.5 surgical pattern corroborated twice within PR 9

The Step N.5 surgical commit pattern originated in PR 8 Step
4.5 (scaffold prose cleanup; PR 8 close §5.2) as a
verification-time amendment cadence. PR 9 corroborates the
pattern **twice within a single PR arc**:

- **Step 2.5 (`94022de`)** — Surgical authored/observed
  divergence framing addition to `fix_no_keyword_match.py`.
  Triggered by Step 3 guidance item 2 (user direction to add
  explicit "authored/observed divergence" coined-phrase
  paragraph). 18-line additive insertion; preserved pre-existing
  prose; added user-coined wording as grep-discoverable
  archaeology.
- **Step 5.5 (`d598bf6`)** — Surgical Step 5 amendment
  (standalone verification item 11 + architectural-concentration
  wording refinement). Triggered by Step 5 addition guidance
  (user direction to surface no-keyword-match divergence as
  discrete archaeology + reframe Steps 3+4 as cumulative-
  complementary not hierarchical). Empty commit; archaeology
  in commit body.

The methodology generalizes (per PR 7 §4.5 + PR 8 §1.3 + PR 8
close §5.2 amendment cluster hygiene): when mid-flight
guidance surfaces an additive improvement to a recently-
shipped deliverable, register the improvement as a surgical
N.5 commit BEFORE the next major deliverable lands.

The pattern is now **3-times corroborated** (PR 8 Step 4.5 +
PR 9 Step 2.5 + PR 9 Step 5.5). Promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` candidacy
strengthens. The complete promotion inventory lives at Gate 2
close §5; this section names PR 9's two corroborations.

### 1.3 Grounding-time amendment as PR 9's specific methodology contribution

PR 9's dominant methodology contribution is the **grounding-time
amendment variant** — the 4th canonicalized variant of the
amendment-at-incarnation cluster.

**The variant:** Surfaced when implementation begins consuming
a previously-only-described substrate empirically. The
framing/spec may have extrapolated structural assumptions about
the substrate's behavior; empirical inspection of the live code
surface reveals the extrapolation does not hold. The amendment
realigns spec with operational topology.

**PR 9's instance:** Spec amendment 2026-05-11 (commit
`2c7a2ca`). At Step 2 grounding, empirical inspection of
`forge_bridge/console/_tool_filter.py::filter_tools_by_message`
revealed that the chat-handler narrowing pipeline cannot
produce `narrower_decision == []`. The PR14 "no capability
loss" fallback (lines 320-321) returns the full reachable tool
set verbatim when no keyword matches; the empty-list outcome
is structurally unreachable at the chat-handler surface.

The framing/spec extrapolated chain-step "zero-match" semantics
onto the chat-handler surface. Carrier #10's own warning
sentence was the load-bearing signal the framing/spec missed:

> Ambiguity rejection is an arbitration outcome. Capture must
> record it. At this surface, `narrower_decision` carries the
> filtered list verbatim at narrowing finalization — including
> zero-match and multi-match rejection paths.
> `pr20_condition_met` is always False and `collapse_occurred`
> is False on all rejection paths. **These semantics differ
> from the chat-handler case and must not be silently
> overloaded.**

The framing/spec honored carrier #10's verbatim travel but
missed the carrier's own boundary clause. The grounding-time
amendment renamed `fix_zero_match.py` → `fix_no_keyword_match.py`
+ corrected the chat-handler narrowing-outcome topology + added
spec §4.7 archaeology + spec §4.5 monkeypatch strategy
subsection.

**The variant's distinguishing properties:**

- Surfaces at Step 2 / Step 3 boundaries (where implementation
  first consumes substrate empirically).
- Realigns spec with operational topology (NOT design intent).
- Registered as **separate NO-code amendment commit** per user
  direction at amendment convergence (not folded into the
  implementation step that surfaces it).
- Preserves the load-bearing claim of the original
  framing/spec where the claim is correct; corrects ONLY where
  empirical grounding shows misalignment.

**Methodological pattern:** The variant joins drafting-time
amendments (PR 7 + PR 8) + implementation-time amendments
(PR 8 cluster #5–#7) + verification-time amendments (PR 8 Step
4.5). The complete 4-variant amendment taxonomy lives at
**Gate 2 close §5** with PR-of-origin noted per variant;
PR 9 close defers to Gate 2 close for the complete taxonomy.

### 1.4 Member #9 — fixture-surface-data-discipline; class final inventory at 9 members

PR 7 framing §6 introduced the cleanup-pressure-resistance
class as an architectural class. PR 7 populated members #1–#6
at framing + implementation. PR 8 contributed members #7 + #8
(framing §6 + close §1.2). **PR 9 contributes member #9.**

**Member #9 protection (verbatim, scope-local to PR 9 fixture
surface):**

Fixtures under `tests/corpus/fixtures/` are **data + one
orchestration call only**. Each fixture module exposes exactly
one top-level constant (`FIXTURE: dict`); the module contains
no functions, no classes, no constants beyond `FIXTURE`, no
imports beyond `__future__` annotations.

**Operational placement of the protection:**

- `_FIXTURE_PERMITTED_IMPORTS` value-locked frozenset at 1
  symbol (`forge_bridge.corpus._seed.drive_seed_fixture`).
- `_fixture_corpus_references` AST walker scoped to
  `tests/corpus/fixtures/*.py` (excluding `__init__.py`).
- `test_fixture_permitted_imports_locked_at_one_symbol` — value
  lock regression.
- `test_fixture_modules_references_subset_of_permitted_imports`
  — walker subset-enforcement.
- PR 9 walker's docstring carries the parallel-not-extension
  rationale + the closing sentence: *"Shared AST mechanics do
  not imply shared ontology."*

**Three protected properties** (per framing §6.1):

1. **Grep archaeology** — 1:1 module-to-fixture mapping;
   `grep -A 5 "FIXTURE =" tests/corpus/fixtures/fix_*.py`
   surfaces every fixture's full data in one step.
2. **Carrier travel discipline** — relevance-by-file ordering
   applies per-module; carriers verbatim per fixture.
3. **Single-symbol-gate Layer 2 discipline** — admission to
   `_FIXTURE_PERMITTED_IMPORTS` requires explicit framing-level
   redline.

**Class final inventory at PR 9 close (9 members):**

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
| **9** | **Fixture-surface-data-discipline** | **PR 9** | **Fixture module docstrings + framing §6.1 + Layer 2 `_FIXTURE_PERMITTED_IMPORTS` value-lock + PR 9 walker** |

The class is now demonstrably populatable across **three
reliability phases**. Promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` candidacy remains
gated on a **fourth phase populating the class under genuinely
independent conditions**. Gate 2 close §5 carries the full
promotion-candidate inventory.

### 1.5 Three-walker Layer 2 partition operational at PR 9 close

At PR 9 close, **three Layer 2 AST walkers** operate against
the codebase. Each protects a distinct ontology. The
protections are partitioned, not unified:

- **PR 4 walker** (`tests/corpus/test_pr4_participation_creep.py`)
  — protects **production import topology**: the narrowing-
  subsystem may not acquire corpus dependencies (one-directional
  flow). Target set: production source files. Rejection rule:
  one-directional flow.
- **PR 8 walker** (`tests/corpus/test_pr8_seed_surface.py`,
  `_corpus_references` + `_SEED_PERMITTED_IMPORTS`) — protects
  **orchestration participation discipline**: `_seed.py`'s own
  corpus-internal imports stay within the 5-symbol bounded
  toolbox (semantics-not-cardinal per PR 8 close §1.7). Target
  set: `_seed.py`. Rejection rule: persistence-topology
  authority cannot leak into the seed-driver-internal scope.
- **PR 9 walker** (`tests/corpus/test_pr9_fixture_discipline.py`,
  `_fixture_corpus_references` + `_FIXTURE_PERMITTED_IMPORTS`)
  — protects **declarative fixture-data discipline**: fixture
  modules import nothing from the corpus beyond the single
  orchestration symbol. Target set: fixture directory glob.
  Rejection rule: single-symbol-gate.

The walkers **share AST mechanics** (each uses `ast.walk` +
import-node traversal); they **do NOT share ontology**.
Generalization would require unifying:

- Target-set semantics (production vs. seed-driver-internal vs.
  fixture-test).
- Admission ontologies (one-directional flow vs. bounded
  toolbox vs. single-symbol-gate).
- Rejection-message shape.
- Future evolution pressure.

…which collapses three protections into one rejection surface.
Per spec §4.6 + §7 future-PR rejection table: **"Future walker
unification cleanup proposals are rejected at the spec layer."**
The closing sentence — *"Shared AST mechanics do not imply
shared ontology."* — lands as carrier-equivalent prose in the
PR 9 discipline test module docstring.

### 1.6 Test count anchor reached — 207 forge env collected

PR 9 close test count arithmetic (per spec §5.3):

```
200 baseline (PR 8 close §1.6 forge env collected)
+   2 PR 9 discipline tests (Step 1)
+   3 PR 9 e2e integration tests (Step 3)
+   2 PR 9 property tests (Step 4)
= 207 forge env collected at PR 9 close
```

**Step 5 verification re-confirmed:** `pytest tests/corpus/` →
207 passed.

PR 9 ships **7 named tests** (5 integration + 2 discipline);
named == collected (no parametrize per framing Q3). The named
== collected identity is structurally locked by member #9
(no parametrization framework over fixtures) + spec §5.3
(test count anchor).

**Forge-bridge env count:** 6-test gap inherited from PR 7
(`project_v1_4_x_harness_debt.md`: starlette TestClient +
asyncpg loop conflict + Project-seeding fixture gap). Target
at PR 9 close: 194 baseline + 7 new = **201 forge-bridge env
collected**. Not re-verified at PR 9 close beyond inheritance
documentation — the 6-test gap is PR 7-scope, not PR 9-scope.
**Do not conflate the two env counts.**

### 1.7 Zero production source file modifications — architectural success signal

PR 9 ships **0 modifications to production source files**:

```
$ git diff --stat b102010..d598bf6 -- forge_bridge/
(empty)
```

Verified by inspection across all 10 PR 9 commits. The 0-prod-
mod outcome is **not merely a scope constraint** — it is the
architectural validation signal for the PR 7 + PR 8
decomposition strategy (per spec §1 Architectural Success
Signal):

- **Fixtures are consumers, not modifiers.** Each fixture
  module transacts with `drive_seed_fixture` as a pure
  consumer; no fixture content required reaching into
  `_seed.py`, `_capture.py`, `_schema.py`, or any other
  production module.
- **Orchestration topology proved sufficient.** The
  `drive_seed_fixture` surface — single function, three
  kwargs, one orchestration call — drove three distinct
  narrowing-outcome shapes (single-survivor / multi-match /
  no-keyword-match) end-to-end. No additional orchestration
  parameter, no scope-extension helper surfaces, no
  driver-shape modification.
- **Gate 2 advances entirely from the outside-in.** PR 7
  established substrate; PR 8 established boundary; PR 9
  establishes consumption. Substrate → boundary → consumption;
  no inside-out modification at any point.

The architectural success signal is **load-bearing for Gate 3
+ Gate 4 framing**. Future reliability phases consuming this
substrate empirically inherit the corroboration. The
decomposition strategy is **validated by closure**, not just
by design intent.

### 1.8 Cumulative architectural concentration — Steps 3 + 4 as complementary proof centers

PR 9's architectural concentration is **cumulative across Steps
3 + 4**, NOT hierarchical (#1, #2):

- **Step 3 (`6f6a809`)** — **Arbitration grounding center.**
  Lands the three end-to-end integration tests; demonstrates
  PR 7 substrate + PR 8 surfaces compose against the REAL
  `chat_handler` arbitration pipeline (PR14 + PR21 + emission).
  The grounding is the proof that the orchestration topology
  works under real seeded execution.
- **Step 4 (`87cf08e`)** — **Partition/joinability proof
  center.** Lands the two Gate 4 unblock proof tests;
  demonstrates the comparator's two foundational dependencies
  (record_kind partition correctness + fixture_id joinability)
  hold mechanically WITHOUT shipping the comparator itself.

Together, Steps 3 + 4 form the **Gate 4 comparator-unblock
proof surface** — the cumulative architectural concentration
PR 9 contributes to Gate 2 closure.

**Phrasings to use** at the close artifact + future archaeology:

- *"Gate 4 comparator-unblock proof surface operational"*
- *"Gate 4 unblock conditions operationally verified"*

**Phrasings to AVOID** (per Step 5.5 wording refinement):

- "the architectural center" (singular; misrepresents
  cumulative concentration).
- "architectural-center #1" / "architectural-center #2"
  (implies hierarchical ordering when the structure is
  complementary).

The wording refinement is registered at Step 5.5 (`d598bf6`)
commit body; this section is the canonical statement of the
framing.

---

## 2. What PR 10 / Gate 3 inherits from PR 9

### 2.1 The three-fixture corpus

`tests/corpus/fixtures/` ships as a stable consumption surface:

- `fix_single_survivor.py` — canonical PR14+PR21 collapse
  exercise.
- `fix_multi_match.py` — multi-match ambiguity-rejection
  exercise.
- `fix_no_keyword_match.py` — PR14 fallback + authored/observed
  divergence proof.

Each fixture is **immutable at PR 9 close**. Future PRs may
add additional fixtures (PR 10+ scope), but the three PR 9
fixtures are **load-bearing archaeology** — Gate 4 framing +
comparator authoring will reference them as the canonical
seed corpus.

**What PR 10 / Gate 3 must NOT do:**

- Modify the three PR 9 fixture modules' `FIXTURE` constants
  (the grounded prompts + outcomes are archaeology-grade).
- Delete any of the three fixtures.
- Add a fourth fixture inside PR 9 / Gate 2 scope (PR 10+
  fixtures require framing-level naming of the new narrowing-
  outcome shape exercised + the Gate 4 comparator dependency
  justified).

### 2.2 The integration test infrastructure

`tests/corpus/test_pr9_fixture_integration.py` ships as
reusable consumption infrastructure for future seed-corpus
tests:

- **`_PR9_REACHABLE_TOOLS`** — module-scope constant declaring
  the 4-tool controlled reachable set. Lives at module scope
  (NOT conftest.py) per Step 3 guidance — controlled set is
  module-local arbitration grounding, NOT reusable suite
  infrastructure.
- **`_apply_pr9_patches`** — standard 5-monkeypatch suite for
  reachable-tool topology constraining (no chat_handler
  mocking). Reused at tests 1, 2, 3 (Step 3) + 4, 5 (Step 4).
- **`_read_records`** — corpus JSONL reader helper (mirrors
  PR 4 `_read_records` pattern; local copy to keep
  test-resident scope).
- **`_make_patched_invoke`** — factory producing a per-test
  replacement for `_invoke_chat_handler_in_process` that
  injects `scope["app"]` with stub LLM router. PR 8's
  `_invoke_chat_handler_in_process` omitted scope["app"]
  because PR 8 tests mocked chat_handler entirely; PR 9 was
  the first phase to drive REAL chat_handler end-to-end.

**What PR 10 / Gate 3 may reuse:**

- The patching strategy verbatim (PR 10 fixtures consuming
  `drive_seed_fixture` against the same controlled set inherit
  the strategy).
- The `_read_records` helper for corpus inspection.

**What PR 10 / Gate 3 must NOT do:**

- Promote `_PR9_REACHABLE_TOOLS` to conftest.py (per Step 3
  guidance — the controlled set's scope is module-local).
- Generalize `_apply_pr9_patches` into a reusable fixture-
  management abstraction (would erode member #9 protection +
  the governing sentence's "no infrastructure" rejection key).
- Mock `chat_handler` itself in any new integration test
  (mocking collapses the arbitration surface under test; per
  spec §4.5 + §4.7 + amendment-convergence user direction).

### 2.3 The §4.7 amendment's corrected chat-handler topology

PR 9 spec §4.7 amendment 2026-05-11 canonicalized the chat-
handler-surface narrowing-outcome topology:

- **(a) Single survivor** — PR14 yields exactly 1 candidate
  OR PR21 collapses >1 to 1.
- **(b) Multi-match ambiguity** — PR14 yields >1; PR21 cannot
  collapse.
- **(c) No-keyword-match full-capability fallback** — prompt
  keywords match zero tools; PR14 returns the full reachable
  set verbatim ("no capability loss").

**Outcome (c) is NOT zero-survivor narrowing.** The empty-list
narrowing decision is **mechanically unreachable** at the
chat-handler surface per `_tool_filter.py:320-321`.

PR 10 / Gate 3 inherit the corrected topology unchanged. Any
future fixture or test asserting `narrower_decision == []` at
the chat-handler surface is **rejected at the spec layer** per
§4.7 amendment archaeology.

Carrier #10's verbatim text remains preserved unchanged at
spec §0 line 133 — the carrier is correct as written; the
misapplication was at the spec layer's extrapolation, not at
the carrier itself.

### 2.4 The authored/observed divergence proof case

`fix_no_keyword_match.py` operationalizes the canonical
authored/observed divergence case — the **Gate 4 comparator-
unblock proof case demonstrating that authored expectation and
observed arbitration outcome remain independently representable
through the companion-record topology** (per Step 5.5 item 11
verification + Step 2.5 surgical framing).

The fixture's `expected_narrow = []` is the fixture-author's
**aspirational claim**; the observation's
`narrower.decision = [full 4-tool set]` is arbitration's
**actual outcome**. The divergence is **intentional and
operationally valuable** — it is the proof case Gate 4's
comparator will exercise.

PR 10 / Gate 3 must preserve this divergence framing
**unchanged**:

- Do NOT "fix" the divergence by aligning `expected_narrow`
  with `observation.narrower.decision`.
- Do NOT remove the empty-list aspirational claim.
- Do NOT amend `fix_no_keyword_match.py`'s authored/observed
  divergence framing paragraph (lines 161-177 of the fixture
  module).

If Gate 4's comparator requires additional divergence-shape
fixtures (e.g., partial-match divergence; surface-asymmetry
divergence), they land as PR 10+ framing decisions, NOT
modifications to the PR 9 fixtures.

### 2.5 The Layer 2 fixture discipline

The PR 9 walker + frozenset constitute a parallel Layer 2
discipline. Future PRs inherit:

- **`_FIXTURE_PERMITTED_IMPORTS`** value-locked at 1 symbol.
  Any admission of a second symbol requires explicit framing-
  level review per member #9 protection.
- **PR 9 walker** scoped to fixture directory glob. Any
  expansion of the target set (e.g., to include integration
  tests or production source) requires framing-level review.
- **Parallel-not-extension boundary** with the PR 4 + PR 8
  walkers (three distinct ontologies; shared AST mechanics
  do not imply shared ontology). Future "walker unification"
  proposals rejected at the spec layer.

### 2.6 The 10-commit PR 9 chain as reseed reference

PR 9 ships as a 10-commit chain (commits §4 enumerates).
Future PRs inheriting from PR 9 should:

- Read this close artifact §1 + §2 + §4 for the durable
  archival state.
- Read the spec amendment commit (`2c7a2ca`) for the §4.7
  amendment archaeology.
- Read the Step 2 commit body (`50a7caf`) for the grounded
  arbitration trace.
- Read the Step 5.5 commit body (`d598bf6`) for the verification
  surface refinement + cumulative-concentration framing.
- Defer to **Gate 2 close** for gate-arc synthesis, complete
  amendment taxonomy, promotion-candidate inventory.

---

## 3. What PR 10 / Gate 3 changes

PR 10 is not yet framed. Gate 3 framing pass is the next major
deliverable after Gate 2 close. This section names what is
**known to change** versus what is **deferred** to Gate 3
framing.

### 3.1 Deferred to Gate 3 framing

PR 10's scope is undefined at PR 9 close. Likely Gate 3 work
surfaces will include (NOT binding; speculative):

- The Gate 4 comparator itself (`compare_fixture_records`
  helper or similar) — comparator deliverable per Gate 2
  framing §11.3 explicitly: *"Gate 2 ships no comparator
  artifact, stub or otherwise."* Comparator authoring is Gate 4
  or Gate 3 framing decision.
- Cross-surface fixture identity (the four §7.3 ontological
  questions PR 8 framing left open + PR 9 framing §7.3 carried
  forward). Requires a dedicated framing pass per carrier #15's
  third clause governance.
- Chain-step seeding (currently rejected at spec layer per
  carrier #15). Requires a dedicated framing pass before
  implementation proceeds.
- Additional fixture-corpus expansion if Gate 4 comparator
  surfaces concrete coverage needs.

Gate 2 close §2 carries the **full Gate 3 inheritance contract**
including what comparator needs, what carrier set hands
forward, what remains undecided. This section defers to Gate 2
close for the gate-level inheritance contract.

### 3.2 What does NOT change at PR 10 / Gate 3

Regardless of Gate 3's specific deliverables, the following
PR 9 outcomes are **permanent archaeology**:

- **The three PR 9 fixtures** ship as stable archaeology. Any
  modification requires framing-level review.
- **The corrected chat-handler topology** (per §4.7
  amendment) remains operational; no future PR may extrapolate
  chain-step semantics onto chat-handler surface.
- **The 15 inherited carriers** continue to travel verbatim
  across all future Gate 2 production modules + test
  docstrings + commit messages.
- **PR 7-LOCAL pairs + PR 8-LOCAL binding statements + PR 9
  fixture-data discipline** continue NOT to regenerate beyond
  their scope-local placement.
- **The PR-INTERNAL three-way authority partition** (PR 8
  spec §4.1.5.1) preserves intact.
- **The three-walker partition** preserves intact (PR 4 / PR 8
  / PR 9; parallel-not-extension).
- **The cleanup-pressure-resistance class** at 9 members is
  the durable inventory at PR 9 close. Future PRs may add
  members; existing 9 members are unchanged.
- **`forge_bridge.__all__`** stays at 19 symbols.
- **0 production source modifications** as the PR 9 closure
  signal validates PR 7 + PR 8 decomposition; future Gate 2
  surfaces (if any) inherit the validation.

---

## 4. Step-by-step archaeology — 10-commit PR 9 chain

PR 9's implementation arc is 10 commits, beginning at framing
commit `5628817` (2026-05-11) and closing at PR 9 close +
Gate 2 close (this commit). The arc mirrors PR 8's 8-commit
shape with two methodology variants PR 9 introduces (grounding-
time amendment + Step N.5 surgical pattern twice corroborated):

| # | Commit | Type | Step | Lines | Cumulative |
|---|---|---|---|---|---|
| 1 | `5628817` | Framing | (pre-step) | +1222 | 1222 |
| 2 | `f8ccf0f` | Spec | (pre-step) | +1918 | 3140 |
| 3 | `627b104` | Step 1 — fixture dir + discipline scaffolding + placeholder | Step 1 | +329 | 3469 |
| 4 | `2c7a2ca` | Spec amendment 2026-05-11 (grounding-time variant) | (pre-Step-2) | +546/-67 | 3948 |
| 5 | `50a7caf` | Step 2 — three fixture modules with grounded arbitration traces | Step 2 | +481/-40 | 4389 |
| 6 | `94022de` | Step 2.5 — surgical authored/observed divergence framing | Step 2.5 | +18 | 4407 |
| 7 | `6f6a809` | Step 3 — three e2e integration tests (arbitration grounding center) | Step 3 | +641 | 5048 |
| 8 | `87cf08e` | Step 4 — two Gate 4 unblock proof tests (partition/joinability proof center) | Step 4 | +179 | 5227 |
| 9 | `159ccd2` | Step 5 — final verification (empty; archaeology in body) | Step 5 | 0 | 5227 |
| 10 | `d598bf6` | Step 5.5 — surgical Step 5 amendment | Step 5.5 | 0 | 5227 |

**Step archaeology — methodology contributions per commit:**

- **Step 1** (`627b104`) — Operationalizes member #9 protection
  via the placeholder-and-replace pattern. The discipline test
  module + frozenset + walker + placeholder fixture ship as
  one atomic Step 1 construct, preserving four properties
  (ontology + walker mechanics + fixture topology +
  parallel-not-extension rationale).
- **Spec amendment** (`2c7a2ca`) — Grounding-time variant of
  the amendment-at-incarnation cluster. Separates the
  pre-existing structural extrapolation correction from the
  Step 2 implementation work; surfaces as separate NO-code
  commit per amendment-convergence user direction.
- **Step 2** (`50a7caf`) — Three fixture modules with grounded
  arbitration traces. Each prompt empirically verified against
  direct `filter_tools_by_message` + `deterministic_narrow`
  invocation; commit body records the verified arbitration
  trace archaeology per `feedback_counts_are_archaeology_grade.md`.
- **Step 2.5** (`94022de`) — Surgical authored/observed
  divergence framing addition. First Step N.5 corroboration
  within PR 9 (PR 8 Step 4.5 was the prior precedent). 18-line
  additive insertion; user-coined "authored/observed
  divergence" phrase introduced for grep-discoverable
  archaeology.
- **Step 3** (`6f6a809`) — Arbitration grounding center.
  Three e2e integration tests landed; first PR in the
  A.5.3.2 arc to drive the REAL `chat_handler` end-to-end
  (PR 8 mocked `chat_handler` with `benign_chat_handler`).
  Test infrastructure (`_PR9_REACHABLE_TOOLS` + `_apply_pr9_patches`
  + `_make_patched_invoke`) lands. Grounding-time discoveries
  surfaced: nested record-field path (`observation.narrower.*`);
  PR20 short-circuit fires on `"ping forge"`.
- **Step 4** (`87cf08e`) — Partition/joinability proof center.
  Two Gate 4 unblock proof tests landed; infrastructure reuse
  from Step 3 (`_apply_pr9_patches` + `_PR9_REACHABLE_TOOLS`
  + `_read_records`). Orthogonality verified — tests 4 + 5
  independent of tests 1-3 via independent fixture drives.
- **Step 5** (`159ccd2`) — Final verification. Empty commit;
  10-item verification checklist + 15 carriers + binding
  framing clarification + PR 9 governing sentence + member #9
  protection summary in commit body.
- **Step 5.5** (`d598bf6`) — Surgical Step 5 amendment. Second
  Step N.5 corroboration within PR 9. Empty commit; item 11
  standalone verification (no-keyword-match divergence) +
  cumulative-architectural-concentration wording refinement
  (Steps 3 + 4 as complementary proof centers, not
  hierarchical #1/#2).

**Cumulative architectural concentration applied across the
table** (per Step 5.5 refinement):

- Steps 3 + 4 are co-equal complementary proof centers, NOT
  hierarchical (#1, #2) positions.
- The phrasings in the table reflect this:
  - Step 3 = "arbitration grounding center"
  - Step 4 = "partition/joinability proof center"
- Together they form the **Gate 4 comparator-unblock proof
  surface** — the load-bearing architectural concentration
  PR 9 contributes.

---

## 5. Methodology observations surfaced during PR 9

### 5.1 The grounding-time amendment variant — PR 9's specific contribution

PR 9 contributes **one new variant** to the amendment-at-
incarnation cluster: **grounding-time amendments**.

**Definition:** Surfaced when Step 2 / Step 3 implementation
begins consuming a previously-only-described substrate
empirically. The framing/spec may have extrapolated structural
assumptions about the substrate's behavior; empirical
inspection of the live code surface reveals the extrapolation
does not hold. The amendment realigns spec with operational
topology.

**PR 9's instance:** Spec amendment 2026-05-11 (commit
`2c7a2ca`). The `_tool_filter.py::filter_tools_by_message`
"no capability loss" fallback was the operational topology;
the spec extrapolated a chain-step-derived "zero-match" outcome
that the chat-handler surface cannot produce.

**Variant properties:**

- Surfaces at Step 2 / Step 3 boundaries.
- Realigns spec with operational topology (NOT design intent).
- Registered as separate NO-code amendment commit per
  amendment-convergence user direction.
- Preserves the load-bearing claim where correct; corrects
  ONLY at empirical-misalignment sites.

**Methodology cluster status:** The grounding-time variant
joins three pre-existing variants:

1. Drafting-time amendments (PR 7 + PR 8 spec §4.5).
2. Implementation-time amendments (PR 8 §1.3 cluster #5-#7).
3. Verification-time amendments (PR 8 Step 4.5).
4. **Grounding-time amendments (PR 9 §4.7 amendment 2026-05-11)** — NEW.

**The complete 4-variant taxonomy lives at Gate 2 close §5**
with PR-of-origin noted per variant. PR 9 close §5 contributes
the grounding-time entry and defers to Gate 2 close for the
complete taxonomy.

### 5.2 Step N.5 surgical cadence — twice corroborated within PR 9

The Step N.5 surgical commit pattern was introduced at PR 8
Step 4.5 (scaffold prose cleanup; PR 8 close §5.2). PR 9
corroborates the pattern **twice within a single PR arc**:

- **Step 2.5** (`94022de`) — Mid-flight guidance-triggered
  cleanup. Authored/observed divergence framing addition.
- **Step 5.5** (`d598bf6`) — Post-verification-step guidance-
  triggered cleanup. Standalone verification item 11 +
  wording refinement.

**Cadence properties** (corroborated three times across PR 8
+ PR 9):

- Triggered by mid-flight user guidance surfacing an additive
  improvement to a recently-shipped deliverable.
- Registered as surgical N.5 commit BEFORE the next major
  deliverable lands.
- Preserves the step boundary's "distinct atomic boundary"
  discipline.
- May be empty (Step 5.5) or small (Step 2.5 18 lines).

**Promotion status:** The pattern is now 3-times corroborated
(PR 8 Step 4.5 + PR 9 Step 2.5 + PR 9 Step 5.5). Strong
candidate for methodology promotion. Gate 2 close §5 carries
the full promotion-candidate inventory; PR 9 close defers.

### 5.3 Cumulative-architectural-concentration framing — Steps 3 + 4 as complementary proof centers

PR 9's architectural concentration is **cumulative across
Steps 3 + 4**, NOT hierarchical (#1, #2). The Step 5.5 wording
refinement canonicalized the framing:

- **Step 3 = arbitration grounding center.** Demonstrates
  PR 7 substrate + PR 8 surfaces compose against the REAL
  `chat_handler` arbitration pipeline.
- **Step 4 = partition/joinability proof center.** Demonstrates
  the comparator's two foundational dependencies hold
  mechanically WITHOUT shipping the comparator.

Together they form the **Gate 4 comparator-unblock proof
surface**.

**Methodology contribution:** The framing distinguishes
*proof centers spanning multiple steps* from *single-step
architectural centers*. Future reliability phases consuming
multi-step proofs should adopt the cumulative-concentration
framing rather than the hierarchical "#N center" framing.

**Preferred phrasings** (per Step 5.5):

- "Gate 4 comparator-unblock proof surface operational"
- "Gate 4 unblock conditions operationally verified"
- "[Step 3 + Step 4] form the [proof surface name]"

**Phrasings to AVOID:**

- "the architectural center" (singular; misrepresents
  cumulative structure).
- "architectural-center #1" / "architectural-center #2"
  (implies hierarchical ordering).

### 5.4 Pointer to Gate 2 close §5 — complete amendment taxonomy + promotion-candidate inventory

PR 9 close §5 names the grounding-time variant as PR 9's
contribution + names the Step N.5 corroboration count + names
the cumulative-architectural-concentration framing. The
**complete archive** lives at Gate 2 close §5:

- **Complete 4-variant amendment taxonomy** with PR-of-origin
  noted per variant.
- **Complete cleanup-pressure-resistance class** at 9 members
  with full protection descriptions.
- **Complete Step N.5 surgical cadence corroboration** with
  3-instance count and promotion candidacy.
- **Three-walker Layer 2 partition** with all three walker
  ontologies + the parallel-not-extension rationale.
- **Cumulative-architectural-concentration framing** at gate
  scope.
- **Promotion-candidate inventory** for
  `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — which
  methodology contributions are candidates for promotion and
  which require a fourth corroborating phase.

Future phase architects read **Gate 2 close**, not PR 9 close,
for the cross-PR methodology synthesis.

---

## 6. Mechanical checkpoints

### 6.1 Test count anchor verification (Step 5 item 6)

```
$ python -m pytest tests/corpus/
207 passed in 0.99s
```

Forge env collected: **207** ✓ (anchor matches spec §5.3
arithmetic: 200 baseline + 7 PR 9 new = 207).

Forge-bridge env not re-verified at PR 9 close; 6-test gap
inherited from PR 7 per `project_v1_4_x_harness_debt.md`.

### 6.2 Public API anchor (Step 5 item 8)

```
$ python -c "import forge_bridge; print(len(forge_bridge.__all__))"
19
```

`forge_bridge.__all__` count at PR 9 close: **19** ✓.

PR 8's `test_pr8_helpers_remain_corpus_internal` continues to
enforce mechanically. PR 9 added zero new exports.

### 6.3 Layer 3 lint regression (Step 5 item 3)

```
$ python -m pytest tests/corpus/test_pr6_visual_asymmetry.py
17 passed in 0.14s
```

PR 6 Layer 3 lint: **17/17** ✓ unchanged across PR 9.

PR 9 introduced zero new `emit_divergence_capture` call sites;
lint's discovery walk input set unchanged.

### 6.4 PR 4 walker regression (Step 5 item 4)

```
$ python -m pytest tests/corpus/test_pr4_participation_creep.py
1 passed in 0.02s
```

PR 4 walker: **PASS** ✓ unchanged.

Parallel-not-extension boundary preserved — PR 4 walker target
set is production source files; PR 9 walker target set is
fixture modules. Distinct ontologies; shared AST mechanics.

### 6.5 Production source modifications (architectural success signal)

```
$ git diff --stat b102010..d598bf6 -- forge_bridge/
(empty)
```

**0 production source modifications** ✓ across all 10 PR 9
commits.

### 6.6 Carrier travel verification (Step 5 item 9)

Carrier #15 lands at TOP of each fixture module's docstring
per relevance-by-file ordering:

- `fix_single_survivor.py` — line 7 (6 lines below docstring
  top).
- `fix_multi_match.py` — line 7 (6 lines below docstring top).
- `fix_no_keyword_match.py` — line 15 (14 lines below
  docstring top; §4.7 amendment archaeology paragraph lands
  FIRST per most-current-PR-anchored governance principle).

15 inherited carriers + binding framing clarification travel
verbatim across all three fixture modules. Slim per-test-file
pattern (carriers by reference) in
`test_pr9_fixture_integration.py` + `test_pr9_fixture_discipline.py`
per PR 8 spec §0 travel sites #4.

### 6.7 Governing sentence verification (Step 5 item 10)

"PR 9 proves topology, not infrastructure." appears at:

- Spec §0 (line 201).
- Framing §0 (canonical placement).
- All three fixture module docstrings.
- Both new test module docstrings.
- Spec amendment commit (`2c7a2ca`) body.
- Step 2.5 + Step 5 + Step 5.5 commit bodies.
- This close artifact (§7 below).

Promotion to carrier #16 remains **DEFERRED** per spec §0.
Travel pattern (8+ surfaces) provides corroboration evidence
for Gate 4 framing or a future reliability phase to revisit
the promotion question.

---

## 7. Reseed protocol — what the next session does with this artifact

When Gate 3 framing session opens:

1. **Read this PR 9 close artifact first.** §1 + §2 + §4 are
   the load-bearing sections.

2. **Read Gate 2 close artifact** (`A.5.3.2-GATE-2-CLOSE.md`)
   — ships at the same commit as this artifact. Gate 2 close
   §1 (what Gate 2 established as a whole) + §2 (Gate 3
   inheritance contract) are required reading for Gate 3
   framing.

3. **Read the §4.7 spec amendment commit** (`2c7a2ca`) — the
   grounding-time amendment archaeology that produced
   `fix_no_keyword_match.py`. Carrier #10's verbatim text at
   spec §0 line 133 remains the source-of-truth carrier; the
   amendment realigned spec with chat-handler operational
   topology.

4. **Read Step 2 commit body** (`50a7caf`) for the verified
   arbitration traces per fixture. These traces are
   archaeology-grade per `feedback_counts_are_archaeology_grade.md`.

5. **Re-read project memories:**
   - `project_state_2026_05_11_pr8_closed.md` — supersede with
     PR-9-closed cursor at next session.
   - `feedback_ground_specs_in_actual_files.md` — applies to
     Gate 3 framing as it did to PR 9.
   - `feedback_counts_are_archaeology_grade.md` — applies to
     Gate 3 framing's test count anchors.
   - `feedback_strong_recos_technical.md` — applies to Gate 3
     framing decisions outside user's pipeline expertise.

6. **PR 9 governing sentence (verbatim, framing-artifact-scoped):**

   > **PR 9 proves topology, not infrastructure.**

   Carrier #16 promotion remains deferred. Gate 3 framing or a
   future reliability phase may revisit the promotion question
   with the 8-surface travel-pattern corroboration this
   artifact records.

7. **Begin Gate 3 framing.** Gate 3's specific deliverables
   are undefined at PR 9 close; likely surfaces include the
   Gate 4 comparator + the cross-surface fixture-identity
   framing pass. Gate 2 close §2 carries the full Gate 3
   inheritance contract.

8. **Surface the framing for review** before drafting a Gate 3
   spec.

9. **The cadence — framing → spec → spec-amendments-at-
   incarnation → steps → verification-amendments-if-surfaced →
   close — carries unchanged** with the four-variant amendment
   cluster (drafting-time / implementation-time / verification-
   time / grounding-time) explicitly available to Gate 3
   framing as canonicalized methodology.

10. **The Step N.5 surgical cadence is available** for mid-
    flight cleanup commits. Use the pattern if guidance
    surfaces an additive improvement to a recently-shipped
    deliverable.

---

## 8. Cross-references

- **`A.5.3.2-GATE-2-CLOSE.md`** (this commit) — ships at the
  same commit as this artifact per Gate 2 framing §11.6. Gate
  2 close owns gate-arc synthesis, complete amendment
  taxonomy, promotion-candidate inventory.
- **`A.5.3.2-PR9-FRAMING.md`** (`5628817`) — binding pre-spec
  contract; §0 governing sentence; §6.1 member #9
  (fixture-surface-data-discipline); §11 mirror amendment
  archaeology.
- **`A.5.3.2-PR9-SPEC.md`** (`f8ccf0f` + amendment `2c7a2ca`)
  — implementation contract; §0 16 verbatim sentences; §4.7
  amendment 2026-05-11 archaeology (grounding-time variant
  canonical entry).
- **`A.5.3.2-PR8-CLOSE.md`** (`b102010`) — durable PR 8
  archival state PR 9 inherited; §2 (what PR 9 inherited)
  + §3 (what PR 9 changed) + §7 11-step reseed protocol
  (this PR 9 close artifact closes the protocol).
- **`A.5.3.2-PR8-SPEC.md`** (`85c5bc1`) — §0 18 verbatim
  sentences (PR 9 spec §0 mirrors 16); §4.1.5.1 three-way
  authority partition preserved at PR 9; §7 phase-end
  conditions rejection table (PR 9 did not propose any of
  those mutations).
- **`A.5.3.2-GATE-2-FRAMING.md`** (`ceac9b5`) — §3.4
  three-authority-surface partition; §5.7 PR 9 = first
  fixtures + end-to-end integration; §10 PR 9 deliverables;
  §11 Gate 2 close criteria; §11.6 Gate 2 close ships at
  PR 9 close commit.
- **`A.5.3.2-PR7-CLOSE.md`** (`b035c87`) — durable PR 7
  archival state continues to apply at PR 9.
- **`forge_bridge/corpus/_seed.py`** — the four PR 7 + PR 8
  surfaces PR 9 transacted with (`drive_seed_fixture`
  directly; `emit_seed_expectation`, `seed_dispatch_scope`,
  `_persist_expectation_record` indirectly).
- **`forge_bridge/console/_tool_filter.py:258-407`** — the
  PR14 + PR21 narrowing pipeline the spec amendment 2026-05-11
  grounded against. `_tool_filter.py:320-321` is the
  "no capability loss" fallback that surfaced the structural
  finding.
- **`tests/corpus/fixtures/*.py`** — the three PR 9 fixture
  modules (data + module docstring carrying carriers).
- **`tests/corpus/test_pr9_fixture_integration.py`** — 5 e2e +
  property integration tests + test infrastructure.
- **`tests/corpus/test_pr9_fixture_discipline.py`** — PR 9
  Layer 2 walker + frozenset + 2 discipline tests + three-
  walker partition rationale.
- **`tests/corpus/test_pr4_participation_creep.py`** — PR 4
  walker; PR 9 walker is EXPLICITLY NOT an extension.
- **`tests/corpus/test_pr8_seed_surface.py`** — PR 8 walker;
  PR 9 walker generalizes AST mechanics pattern with distinct
  admission ontology.
- **PR 9 10-commit chain** (`5628817` → `d598bf6`) per §4
  table.
- **Local memory updates this session:**
  - New cursor at next session opening:
    `project_state_2026_05_11_pr9_closed_gate_2_closed.md`
    (will supersede `project_state_2026_05_11_pr8_closed.md`).
  - `feedback_ground_specs_in_actual_files.md` strongly
    corroborated this PR; the §4.7 amendment surfaced
    because the methodology was applied.
  - Step 2 grounded-trace archaeology persists in commit
    `50a7caf` body.

---

End of PR 9 close. The implementation arc that began at framing
(`5628817`) closes here. The 10-commit chain ships the three-
fixture corpus + the integration test infrastructure + the
Layer 2 fixture discipline + the grounding-time amendment + the
two Step N.5 corroborations + 0 production source modifications
as the validation signal for PR 7 + PR 8 decomposition.

The cumulative architectural concentration across Steps 3 + 4 —
the **Gate 4 comparator-unblock proof surface** — is the
load-bearing contribution PR 9 makes to Gate 2 closure. The
proof surface is operational; Gate 4 framing inherits an
unblocked path.

PR 9 governs by one framing-artifact-scoped sentence:

> **PR 9 proves topology, not infrastructure.**

The sentence travels through 10+ surfaces (1 spec + 1 framing +
3 fixtures + 2 test modules + 4 commit bodies). Promotion to
carrier #16 remains deferred to Gate 3 framing or a future
reliability phase with corroborating evidence.

**Gate 2 close artifact (`A.5.3.2-GATE-2-CLOSE.md`) ships at
the same commit as this artifact.** Gate 2 close owns the
gate-arc synthesis across PR 7 + PR 8 + PR 9 that no individual
PR close captures. Future phase architects read Gate 2 close
for cross-PR methodology synthesis.
