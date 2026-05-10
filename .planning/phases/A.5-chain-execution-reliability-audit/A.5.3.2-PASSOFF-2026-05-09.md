# A.5.3.2 Session Passoff — 2026-05-09 → next session

**State at handoff:** HEAD `219d89a` on `origin/main`. Eight
commits this session: PR 7 spec landing (`84392d2`), §4.5
amendment (`0a2ad7e`), Step 1 (`0187e9d`), Step 2 (`b987d31`),
Step 3 (`6e5b82e`), Step 4 (`ea7d3fe`), §4.3 amendment
(`30d3ca9`), Step 5 (`219d89a`). All pushed clean. **Pausing
at the natural pause point between Step 5 and Step 6 per spec
§6** — Step 6 is the architectural center and deserves a fresh
context, not the tail of an already-long session.

This passoff captures conversation continuity for the writer's-
room session that opens next. It records what the durable
artifacts don't already articulate.

---

## 1. Read order for resumption

1. **`A.5.3.2-PR7-SPEC.md` §6 step 6** (commit `219d89a`,
   amended at `30d3ca9`) — the architectural-center step body.
   Provenance resolution; FULL THREE-ROUND REVIEW; mandatory
   Layer 3 lint regression checkpoint.
2. **`A.5.3.2-PR7-SPEC.md` §4.2.5** — the resolution path
   contract. Defines `resolved_source` / `resolved_fixture_id`
   computation + the `_build_capture_record` call site.
3. **`A.5.3.2-PR7-SPEC.md` §0** — the §4.2 inert-parameter
   binding pair (verbatim, scope-local to `_capture.py`) that
   must land in the module docstring + helper docstring at
   Step 6.
4. **This passoff.** Skim §3 for the process notes that don't
   appear in artifacts.
5. **On demand:** the §4.3 amendment at commit `30d3ca9` if
   any reference back to the step reorder is needed.

---

## 2. What's locked and what's not

**Locked (do not relitigate):**

- 8-step staircase. Step 6 is provenance resolution (was
  Step 5 in original spec; reordered per §4.3 amendment).
- §4.2 inert-parameter binding pair (verbatim text in spec
  §0) — travels into `_capture.py` module docstring + helper
  docstring at Step 6.
- 14 inherited carriers + binding framing clarification —
  travel into `_capture.py` module docstring at Step 6.
- Resolution path contract (spec §4.2.5): consult
  `_dispatch_context.get()` at top of try block; compute
  `resolved_source` + `resolved_fixture_id`; pass both to
  `_build_capture_record`.
- `_DispatchContext.fixture_id: str` (required, NOT
  `str | None`). Framing-time correction is binding.
- `seed_dispatch_scope` no-yield contract; ContextVar token
  handling implementation-internal.
- Property C unchanged. Call sites at `handlers.py:1185` and
  `_step.py:233` ship into Step 6 with their `source="runtime"`
  literals exactly as they are.
- Layer 3 lint (`test_pr6_visual_asymmetry.py`) ships
  unchanged. Step 6's regression checkpoint runs it against
  the modified `_capture.py`.
- Three new tests in `test_pr7_dispatch_context.py` land at
  Step 6: `test_scope_inactive_persists_runtime`,
  `test_scope_active_persists_seed_and_fixture_id`,
  `test_call_site_source_value_is_inert`. All three exercise
  end-to-end persistence (the resolution path's effect on
  the persisted record).
- `_build_capture_record` gains `fixture_id` keyword-only
  parameter at Step 6 (the `record_kind` parameter already
  landed at Step 5).
- No-ship-and-redline cadence for Step 6: surface diff,
  review, then commit.

**Open at Step 6 spec-time:**

- Exact placement of the `ctx = _dispatch_context.get()`
  resolution block inside `emit_divergence_capture`'s try
  block (top of try, before `_build_capture_record` call —
  spec §4.2.5 sketches; implementation finalizes lineation).
- Exact signature shape of `_build_capture_record`'s new
  `fixture_id` parameter: `fixture_id: Optional[str]` with
  default `None`? Or `fixture_id: str | None` keyword-only
  no-default? Lean: `Optional[str] = None` so tests bypassing
  the resolution path can omit it. (Mirror the `record_kind`
  decision pattern from Step 5: explicit at the boundary,
  with a default if the boundary tolerates one.)
- Whether the persisted record dict always includes
  `"fixture_id"` (set to None when scope inactive) or
  conditionally omits the key. Lean: always include with
  None when inactive. Schema validator is additive-tolerant
  (accepts unknown fields); explicit None preserves the
  field's structural presence and makes downstream
  consumers' logic uniform.
- Whether the schema validator should be extended to accept/
  validate `fixture_id` typing. Lean: NO. PR 7 plumbing-shaped
  scope; fixture_id semantics are PR 8's domain. Defensive
  validation can land later if needed.
- Exact body of the §4.2 inert-parameter binding pair
  appendix to `emit_divergence_capture`'s docstring (spec
  text is the verbatim source; placement within the existing
  docstring is the implementation choice).

---

## 3. Process notes from the session worth carrying forward

These are observations the artifacts don't capture explicitly.

### 3.1 Two spec-vs-reality mismatches in one session

Both with the same root cause: spec drafted from inference
about existing-file shape, not from reading the files.

- **§4.5 (`_ALLOWLIST` admission vs. import distinction)** —
  caught at Step 2 implementation, after Step 1 had already
  inherited the bad docstring claim. Spec amendment landed at
  `0a2ad7e`; Step 2 corrected the inherited docstring +
  verified the discipline boundary.
- **§4.3 (`_VALID_SOURCES` already exists in `_schema.py`)** —
  caught at Step 5 PRE-implementation (before any code
  committed to the wrong direction). Spec amendment landed at
  `30d3ca9`; reordered Step 5↔Step 6 (validator extension
  must precede resolution path); migrated 11 test usages of
  `source="fixture"` to `"runtime"`.

The hardened lesson is saved as feedback memory:
`feedback_ground_specs_in_actual_files.md`. Sibling of
`feedback_counts_are_archaeology_grade.md`. Both are about
treating factual claims (numeric counts; file-structure
assertions) with the same precision discipline.

If a third instance surfaces at Step 6+ under genuinely
independent conditions, the lesson becomes candidate
methodology contribution alongside the framing §6 cleanup-
pressure-resistance class.

### 3.2 Correction-cycle timing improved within the session

§4.5 catch happened AFTER Step 1 inherited the bad docstring.
§4.3 catch happened BEFORE Step 5 wrote any code. Same root
cause; earlier in the cadence.

The improvement is a maturity signal — the room learned to
ground BEFORE committing to a code shape. Step 6 should hold
this discipline: read the actual file state before drafting
any test or implementation that asserts shape.

### 3.3 Audit-before-mechanical-migration paid off

Before applying the 11-usage `source="fixture"` → `"runtime"`
migration, audited each usage for semantic dependency on
`"fixture"` being a distinct value. Confirmed all 11 were
mechanical-safe (the test/production provenance distinction
is structural via the construction site, not encoded in the
source field).

The audit took ~3 tool calls and prevented a class of subtle
bugs ("this test asserts the record came from a test path
specifically, not just from any valid source"). Worth holding
as a check pattern for any future "mechanical" migration that
touches semantic test fixtures.

### 3.4 base_writer_args / base_builder_args split

Surfaced during Step 5 implementation when builder tests
broke (TypeError from `_build_capture_record(**base_writer_args())`
because `record_kind` became a required keyword-only
parameter and `base_writer_args()` doesn't include it).

Resolution: split the helper. `base_writer_args()` for
`emit_divergence_capture` (writer-side, observation-only).
`base_builder_args()` layers `record_kind="observation"` for
direct `_build_capture_record` calls. The split preserves
the architectural boundary at the test layer: the builder
is record-kind-agnostic; the writer is observation-specific.

PR 8 may need an analogous `base_expectation_args` helper if
seed-driver tests construct expectation records directly.

### 3.5 Pre-commit review cadence locked for Step 6

Step 5 was light-touch but multi-file (8 modified + 2 new).
Surfaced the diff for review before commit per the agreement
"no ship-and-redline." User confirmed the cadence; Step 6
inherits it explicitly. Step 6's full-three-round-review
elevation makes this even more load-bearing — surface the
diff, the user redlines, then commit.

---

## 4. Things that might trip up tomorrow's session

- **Don't modify Property C.** The Layer 3 lint
  (`test_pr6_visual_asymmetry.py`) ships unchanged into
  Step 6. Property C's literal `source="runtime"` check
  operates on call sites — call sites stay unchanged. Any
  test failure from the lint at the regression checkpoint
  means Step 6 has accidentally collapsed structural
  declaration into operational provenance. Revert and
  re-converge.

- **Don't let the resolution path consult the call-site
  `source` value.** The §4.2 inert-parameter binding pair
  is the carrier protecting against this. The
  `test_call_site_source_value_is_inert` test is the
  mechanical assertion — passing arbitrary garbage source
  values to the call site should yield contextvar-derived
  persisted values regardless. If the test fails, the
  resolution path is reading the call-site value somewhere
  it shouldn't.

- **Don't skip the immediate Layer 3 lint regression
  checkpoint.** Spec §6 step 6 names it as the most important
  moment in PR 7's implementation. Run `pytest
  tests/corpus/test_pr6_visual_asymmetry.py` IMMEDIATELY
  after Step 6's resolution path lands. If it fails, do
  not proceed to Step 7 — converge.

- **Don't make `fixture_id` optional in `_DispatchContext`.**
  Already `str` required per Step 3 implementation; the
  framing-time correction (passoff §3.3 of the 2026-05-08
  EVE passoff) is binding. The `fixture_id` parameter on
  `_build_capture_record` may be `Optional[str]` for the
  scope-inactive case (None means absent), but the dataclass
  field stays required.

- **Don't commit Step 6 without surfacing the diff first.**
  No-ship-and-redline cadence for full-three-round-review
  steps. Step 6 is the canonical instance.

- **Don't merge Step 6's resolution path with anything else
  in one commit.** Step 6 owns one authority boundary
  (declared-vs-resolved provenance separation).

- **Don't extend the schema validator with `fixture_id`
  typing at Step 6.** PR 7 plumbing-shaped scope ends with
  the resolution path emitting records that include
  `fixture_id`. Validating the field's type/shape is PR 8's
  domain (when the seed driver actually constructs records
  with `fixture_id`).

---

## 5. Tomorrow's opening move

Open Step 6 implementation with:

1. Read `_capture.py` `emit_divergence_capture` body to
   identify the exact insertion point for the resolution
   block (top of `try` block, before `_build_capture_record`
   call).
2. Read `_build_capture_record` signature to identify the
   addition point for the new `fixture_id` parameter.
3. Read `_capture.py` module docstring to identify the
   placement of the carrier extension + §4.2 binding pair.
4. Implement:
   - Resolution block in `emit_divergence_capture`.
   - `fixture_id` parameter on `_build_capture_record`.
   - Conditional/unconditional `"fixture_id"` field in the
     record dict (per the open-question lean: always include,
     None when scope inactive).
   - Module docstring extension on `_capture.py`.
   - Helper docstring extension on `emit_divergence_capture`
     (the §4.2 binding pair).
5. Append three new tests to `test_pr7_dispatch_context.py`:
   `test_scope_inactive_persists_runtime`,
   `test_scope_active_persists_seed_and_fixture_id`,
   `test_call_site_source_value_is_inert`.
6. Run `pytest tests/corpus/` — confirm the 3 new tests pass
   (158 + 3 = 161 corpus tests).
7. **MANDATORY:** Run `pytest tests/corpus/test_pr6_visual_asymmetry.py`
   — confirm Layer 3 lint still passes against the modified
   `_capture.py`.
8. Surface the diff for review per the no-ship-and-redline
   cadence. User redlines. Commit.

The cadence opens with the same convergence shape used
throughout this session: lead with positions, refine through
writer's-room iteration, lock when stable, surface for review,
commit, push.

---

## 6. Branch / repo hygiene

- `main` is clean. HEAD `219d89a`. 8 commits ahead of where
  this session started (`401bc4c`, the 2026-05-08 EVE
  passoff).
- `AGENTS.md` remains untracked from session start; not part
  of A.5.3.2 work; ignore.
- No uncommitted changes; no stash; no in-flight worktrees.
- Memory updated:
  - `project_state_2026_05_09_eod.md` — active cursor
    (replaces `project_state_2026_05_09.md` from earlier
    today, which marked Step 1 as next; we're now past
    Step 5).
  - `feedback_ground_specs_in_actual_files.md` —
    durable lesson, sibling of
    `feedback_counts_are_archaeology_grade.md`.
- Spec amendments archived in commits `0a2ad7e` (§4.5)
  and `30d3ca9` (§4.3). Both preserve the original-vs-
  amended archaeology in spec text.

Tomorrow's session opens to a clean `main` at `219d89a`.
Resumption: `git pull` (no overnight commits expected, but
defensive), then read in §1 order.

---

## 7. Cross-references

- `A.5.3.2-PR7-SPEC.md` (`84392d2`, amended at `0a2ad7e` +
  `30d3ca9`) — implementation contract; Step 6 is the
  architectural center; FULL THREE-ROUND REVIEW; mandatory
  Layer 3 lint regression checkpoint.
- `A.5.3.2-PR7-FRAMING.md` (`1c1e061`) — pre-spec contract;
  five binding decisions; constructs-resistant-to-cleanup-
  pressure class (§6).
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — gate-level
  architecture; carrier #14 (declared-vs-resolved provenance);
  binding framing clarification (call-site-owned arbitration
  inputs).
- `A.5.3.2-PASSOFF-2026-05-08.md` (`401bc4c`) — predecessor
  passoff; locked spec drafting as the next move; this
  session executed that move + landed Steps 1-5.
- `feedback_ground_specs_in_actual_files.md` (local memory)
  — lesson hardened twice this session (§4.5 + §4.3
  amendments).
- `feedback_counts_are_archaeology_grade.md` (local memory)
  — sibling lesson saved earlier today after PR 7 spec
  arithmetic correction.

---

End of passoff. Tomorrow opens at Step 6 implementation,
surface-diff-for-review cadence, with the immediate Layer 3
lint regression checkpoint as the load-bearing moment.
