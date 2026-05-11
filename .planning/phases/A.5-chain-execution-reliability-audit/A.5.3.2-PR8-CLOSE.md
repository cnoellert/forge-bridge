# A.5.3.2 PR 8 — Close (Gate 2 mid-flight; PR 9 inherits)

**Status:** PR 8 closed at commit `1fd9846` on `origin/main`
(Step 5 final verification — verification-only, empty commit).
Gate 2 remains mid-flight; PR 9 (fixtures + integration tests
consuming `drive_seed_fixture`) is the next deliverable per
Gate 2 framing §5.7. Archival framing + continuity definition
for the room as it crosses the PR 7 → PR 8 → PR 9 boundary
inside Gate 2.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs.
- `A.5.3.2-PR3-SPEC.md` — persistence layer.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — risk-category shift;
  integration-discipline quartet.
- `A.5.3.2-PR5-CLOSE.md` (commit `b8f522e`) — surface geometry
  asymmetry; chain-step integration durable archival state.
- `A.5.3.2-PR6-CLOSE.md` (commit `9168df7`) — Layer 3 lint;
  Gate 1 closure; truth-vs-mechanism distinction; durable
  archival state Gate 2 inherits.
- `A.5.3.2-GATE-2-FRAMING.md` (commit `ceac9b5`) — gate-level
  architecture; §3.4 three-authority-surface partitioning;
  §6.1 carrier #14; §6.2 binding framing clarification; §9
  schema delta; §10 PR partitioning.
- `A.5.3.2-PR7-FRAMING.md` (commit `1c1e061`) — pre-spec binding
  contract; §6 cleanup-pressure-resistance class (introduced).
- `A.5.3.2-PR7-SPEC.md` (commit `84392d2`) — implementation
  contract; 19 verbatim sentences; 8-step staircase; 27 tests.
- `A.5.3.2-PR7-CLOSE.md` (commit `b035c87`) — durable archival
  state PR 8 inherited; §1.1 three-authority-surface partitioning
  operationalized; §1.2 cleanup-pressure-resistance class
  6-member inventory; §2 inheritance contract (`_persist_expectation_record`
  seam + `seed_dispatch_scope` operational surface +
  `KNOWN_SOURCE_VALUES` + `_KNOWN_RECORD_KINDS` ontology
  constants).
- `A.5.3.2-PR8-FRAMING.md` (commit `23f2a20`) — pre-spec binding
  contract; §6 cleanup-pressure-resistance class members #7 + #8
  introduced; carrier #15 introduced; Q1–Q4 binding decisions
  (in-process, no-streaming, sync-driver, Path E sync→async
  bridge).
- `A.5.3.2-PR8-SPEC.md` (commit `85c5bc1`) — implementation
  contract; 18 verbatim sentences; 5-step sequence; 14 named
  tests (25 collected); §4.1.5.1 PR-INTERNAL three-way
  authority partition; §4.5 four spec amendments at drafting.
- PR 8 step commits: `0cc389d` → `1fd9846` (6 implementation
  commits ending at Step 5 final verification; one
  `f300b2d` session passoff commit between Step 4 and Step 4.5).

**The threshold PR 8 confirmed:**

> A PR-internal three-way authority partition is structurally
> mechanically protected when each authority surface has a
> distinct symbol, a distinct docstring binding statement, and
> at least one test that fires mechanically when the partition
> erodes laterally or downward.

This sentence — implicit in PR 8 framing's introduction of
member #8 (semantics-not-topology) alongside Gate 2 framing's
§3.4 three-authority-surface partitioning — exits PR 8 as
operational reality. Three symbols, three docstring binding
statements, three test classes (plus three §7 rejection rows
covering the symmetric collapse modes):

- `emit_seed_expectation` (authored-expectation-semantics
  surface) — minimal authority-pure signature (`fixture_id`,
  `prompt`, `expected_narrow`); semantics-not-topology guard in
  docstring; tests 5–7 enforce.
- `drive_seed_fixture` (orchestration-semantics surface) —
  orchestrates expectation persistence + scope + invocation;
  carrier #15 + orchestration-not-authoring guard in docstring;
  tests 8–11 enforce.
- `_persist_expectation_record` (persistence-topology surface,
  PR 7 seam, unchanged) — sibling-not-subordinate to
  `emit_divergence_capture`; non-participation guard + authority
  pre-check in docstring; PR 7 tests 14–17 enforce; PR 8 test 6
  (`test_emit_seed_expectation_persists_via_seam`) adds
  consumer-side regression.

The PR-INTERNAL partition (§4.1.5.1) sub-partitions Gate 2
framing's §3.4 third gate-level surface (authored expectation)
into three PR-8-internal authority surfaces. The richer
partition surfaces collapse-rejection opportunities that the
binary partition would have missed.

---

## 1. What PR 8 established

### 1.1 The PR-internal three-way authority partition, made operational

PR 7 closed by mechanically protecting three GATE-level authority
surfaces. PR 8 extends the discipline INSIDE Gate 2: the third
gate-level surface (authored expectation) sub-partitions into
three PR-8-internal authority surfaces, each structurally
non-collapsible.

| PR-8-internal surface | Symbol | Guard | Mechanical test |
|---|---|---|---|
| **Authored expectation semantics** | `emit_seed_expectation` | Member #8 protection (semantics-not-topology) verbatim in docstring; signature is keyword-only `fixture_id`/`prompt`/`expected_narrow` — no `source` parameter; no `_resolve_corpus_dir` / `_make_header` / `_serialize_line` call | `test_emit_seed_expectation_signature_is_authority_pure` + `test_emit_seed_expectation_persists_via_seam` + `test_emit_seed_expectation_failure_invisibility` |
| **Orchestration semantics** | `drive_seed_fixture` | Carrier #15 verbatim in docstring (chat-handler-only scope); orchestration-not-authoring guard in docstring; function body delegates expectation construction to `emit_seed_expectation` (does NOT build the record dict directly) | `test_driver_does_not_invoke_chain_step` + `test_driver_emits_expectation_through_helper` + `test_driver_opens_scope_around_chat_handler` + `test_driver_invokes_chat_handler_in_process` |
| **Persistence topology** | `_persist_expectation_record` (PR 7 seam) | Non-participation guard + authority pre-check (PR 7); PR 8 introduces zero new arbitration-surface call sites | PR 7's `test_pr7_expectation_persistence.py` 5 tests unchanged; PR 8 `test_emit_seed_expectation_persists_via_seam` adds consumer-side regression |

The three surfaces share file space (`_seed.py` houses the
first two; `_capture.py` houses the third) but do not share
internal logic. The asymmetry is structural: the
authored-expectation surface builds a 7-key dict and delegates;
the orchestration surface delegates BOTH the authored-expectation
emission AND the in-process invocation; the persistence-topology
surface is the only one that touches `_resolve_corpus_dir` or
file I/O.

PR 8's §4.1.5.1 partition ships verbatim into `_seed.py`'s
module docstring (lines 162-182 post-Step-4.5). Three §7
phase-end rejection rows enforce against collapse across any
two surfaces:

1. Cannot inline `_persist_expectation_record` into
   `emit_seed_expectation` (collapses persistence-topology
   INTO authored-expectation).
2. Cannot inline expectation construction into
   `drive_seed_fixture` (collapses authored-expectation INTO
   orchestration).
3. Cannot factor `drive_seed_fixture` into a shared internal
   with chain-step seeding (collapses orchestration across the
   chat-handler/chain-step surface boundary — carrier #15
   protects).

### 1.2 The cleanup-pressure-resistance class — final inventory at PR 8 close

PR 7 framing §6 introduced the architectural class. PR 7
implementation populated members #1–#6. PR 8 framing §6 added
members #7 + #8. PR 8 implementation operationalized them at
three placement sites each. Final inventory at PR 8 close:

1. **Helper duplication.** `emit_divergence_capture` +
   `_persist_expectation_record`. Sibling, not subordinate. No
   shared internal writer. (PR 7.)
2. **Visual asymmetry.** The load-bearing visual pattern
   (Properties A–D, validated by the Layer 3 lint) at every
   emit call site. (PR 6.)
3. **Intentionally inert structural parameters.** The call-site
   `source="runtime"` literal. (PR 7.)
4. **Always-present `fixture_id` field on observation records.**
   The builder dict carries `"fixture_id": None` when no scope
   is active. (PR 7.)
5. **Nested-not-unconditional synthesis form in the reader.**
   Reader synthesis: `fixture_id` synthesis is NESTED inside
   the `record_kind not in record` branch. (PR 7.)
6. **Inline I-6 wrapper duplication in
   `_persist_expectation_record`.** No shared
   `_log_persistence_warning` helper extracted. (PR 7.)
7. **Companion records as truth-partitioning.** Observation
   records and expectation records are persisted as SEPARATE
   records in the same date-partitioned JSONL file,
   distinguished by `record_kind`, joined later by Gate 4's
   comparator on `fixture_id`. The schema validator's
   expectation-branch rejection of records carrying a `source`
   field is the mechanical persistence-boundary guard; this
   class member names the rejection as a falsifiability
   protection, not merely a structural rule. (PR 8 — member #7
   protection verbatim in `_seed.py` module docstring +
   spec §0 + framing §6.1.)
8. **`emit_seed_expectation` as semantics-not-topology.**
   The helper builds the expectation record dict and delegates
   persistence to `_persist_expectation_record` (the PR 7 seam).
   It does NOT call `_resolve_corpus_dir`, `_make_header`,
   `_serialize_line`, or any direct file I/O surface. The
   PR-8-local participation discipline test
   (`_SEED_PERMITTED_IMPORTS` frozenset + AST walker) enforces
   mechanically. (PR 8 — member #8 protection verbatim in both
   `_seed.py` module docstring AND `emit_seed_expectation`'s
   docstring + spec §0 + framing §6.2.)

Each member carries inline documentation (in the source)
naming its protection. Members #7 + #8 follow PR 7's pattern:
verbatim binding statement at the operational placement site
+ "Operationally" prose articulating the mechanism. The class
is candidate methodology contribution — promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` is gated on at
least one more reliability phase surfacing a member of the
class under genuinely independent conditions. PR 8's
contribution provides corroboration of PR 7's framing-time
introduction; the class as a discipline is now demonstrably
populatable across two reliability phases.

### 1.3 The seven amendments at incarnation — PR 8's dominant methodology contribution

PR 7 produced two spec amendments at incarnation (the §4.5
admission-vs-import correction + the §4.3 `_VALID_SOURCES`
discovery + Step 5↔6 reorder). PR 8 produced SEVEN:

- **Four spec-drafting-time amendments** captured in spec §4.5
  (drafted into the spec before Step 1 began, but discovered
  during the spec-drafting pass itself — they read like
  amendments because they amend the framing-time projection
  with what the actual codebase + spec surfaces revealed).
- **Three implementation-time amendments** captured in commit
  bodies only — surfaced after spec was locked, during Steps 2,
  4, and Step 4.5 verification.

Each amendment is a methodology candidate for
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` promotion. The
inventory:

**Spec amendments (drafting-time, in spec §4.5):**

1. **§4.5.1 — enforcement topology grounded in actual test
   surface.** Sibling of PR 7 §4.5 `_ALLOWLIST` lesson. The
   spec drafted from framing initially proposed Layer 2 (PR 4
   participation creep) enforcement extension; the actual
   `test_pr4_participation_creep.py` surface revealed that PR 4
   tests were structurally orthogonal to PR 8's
   discipline-scope. The amendment landed PR-8-local
   participation discipline at the new
   `test_pr8_seed_surface.py` module rather than extending PR 4.
   Principle: *"the discipline test surface must be grounded in
   the actual test surface, not the framing-time projection;
   spec drafters must read the test surface before naming
   enforcement placement."*

2. **§4.5.2 — participation contract is semantic, not cardinal.**
   The spec drafted from framing initially named
   `_SEED_PERMITTED_IMPORTS` as a "5-symbol limit." The
   amendment reframed: 5 is the artifact of admission decisions
   made at framing review, NOT the binding constraint. The
   bright line is rejection of persistence-topology authority,
   not enforcement of an exact symbol count. Principle:
   *"admission decisions must be framing-level; cardinal symbol
   counts in tests are artifacts of those decisions, not the
   decisions themselves. Test code carries the artifact;
   docstrings + framing carry the contract."*

3. **§4.5.3 — exception surface vs. generalized discipline.**
   The corpus → console import direction surfaced in §4.1.4
   when `_invoke_chat_handler_in_process` required
   `from forge_bridge.console.handlers import chat_handler`.
   The amendment named this as an EXCEPTION SURFACE (function-
   scoped import inside the orchestration helper) rather than
   a generalized relaxation of the corpus discipline. Other
   corpus modules may NOT acquire console imports without
   framing-level review. Principle: *"new authority surfaces
   may require new import directions; these are exception
   surfaces named at framing time, not generalized relaxations
   of the surrounding discipline."*

4. **§4.5.4 — Path E: sync→async bridge as architectural seam.**
   The Q4 framing lock kept `drive_seed_fixture` synchronous
   (consumer-visible). The Q1 framing lock chose in-process
   invocation. The collision requires a sync→async bridge.
   The spec amendment named this bridge "Path E" and named
   `_invoke_chat_handler_in_process` as carrying FOUR
   architectural seam roles (sync→async bridge,
   request-envelope reconstruction, corpus → console exception
   seam, carrier #15 enforcement seam). Principle: *"structural
   seams carrying multiple architectural roles must be named
   explicitly at framing/spec time; the name (Path E) is the
   reviewer's lookup for any future modification of the seam."*

**Step-level amendments (implementation-time, in commit bodies):**

5. **Step 2 (`5d8bef7`) — absence assertions obsoleted by
   additive extensions.** The schema validator's
   `record_kind == "expectation"` branch extension (additive)
   broke PR 7 helpers' absence assertions because the absence-
   of-X behavior had a new dimension. Five surgical updates
   (3 helpers + 2 test bodies) restored the protected property
   under the new shape. Principle: *"absence assertions in
   regression tests are obsoleted by additive extensions of
   the schema; the protected property survives, but its
   mechanical expression must be reframed. Schema extensions
   are not behavior-preserving for absence-style tests; they
   are behavior-preserving for presence-style tests."*

6. **Step 4 (`76959c1`) — Python import asymmetry under reload
   + teardown patterns.** `test_pr4_no_dependency` uses
   `importlib.import_module` + `monkeypatch.delitem` to force-
   reload modules; the teardown restores `sys.modules` to the
   ORIGINAL but parent-package attributes (e.g.,
   `forge_bridge.console.handlers`) are NOT restored.
   `from X import Y` resolves via `sys.modules` → ORIGINAL;
   string-form `monkeypatch.setattr("X.Y")` resolves via
   parent-package attribute → NEW. Resolution: defensive
   autouse fixture
   `_sync_console_package_attrs_with_sys_modules` in
   `tests/corpus/conftest.py`. Principle: *"Python's import
   machinery is asymmetric across sys.modules manipulation +
   parent-package attribute access; defensive autouse re-sync
   fixtures at the test-directory layer are the minimal fix.
   Test isolation issues caused by upstream test teardown
   patterns are infrastructure-layer fixes, not production-code
   fixes."*

7. **Step 4.5 (`9785d69`) — Step-1 scaffold prose describing
   future-state must be amended at the step that lands the
   corresponding body.** Verbatim-travel verification at Step 5
   surfaced stale "SKELETON / NotImplementedError" prose in
   both `_seed.py` (lines 19-23) and `test_pr8_seed_surface.py`
   (lines 55-59). The prose described Step-1 state but was
   never amended at Steps 3+4 when bodies landed. Surgical
   removal (~12 lines across 2 files); zero verbatim-travel
   disruption; zero behavior change. Principle: *"implementation
   step closure includes amending any future-state prose that
   step's body has now operationalized — not just the bodies +
   signatures themselves. Trailing scaffold prose at PR close
   is a verification-time drift hazard."*

**The "implementation-time amendment hygiene" cluster.**
Amendments #5–#7 share a common root: state described in
code/tests/docs at one step rots when a LATER step modifies
the described surface. Amendment #5 is schema extension
breaking absence assertions; #6 is reload patterns breaking
import attribute consistency; #7 is bodies landing while
scaffold prose remains. Three independent failure modes;
common methodological pattern: implementation step closure
must include "what previously-correct claims has this step
now made stale?"

This cluster IS the dominant methodology contribution from
PR 8. The total candidate set (PR 7 + PR 8 combined) is now
~10 observations. Promotion gate per PR 7 framing §6:
at-least-one-more-reliability-phase independent corroboration
required. Register as candidates at PR 8 close; defer
promotion. PR 9 will be the corroboration check on PR 8's
amendments specifically — particularly amendments #5–#7 as a
cluster.

### 1.4 Eighteen verbatim sentences + carrier #15 + member #7 + member #8

PR 8 ships 18 verbatim sentences into the seed-driver module's
docstrings + commit message bodies. The taxonomy:

- **Fourteen inherited carriers** (#1–#14 from PR 4 + PR 5 +
  PR 6 + Gate 2). These travel into `_seed.py` module
  docstring + `test_pr8_seed_surface.py` module docstring
  (the latter BY REFERENCE per spec §0 travel site #4
  guidance). Carriers #1–#14 also travel into the PR 8
  commit message bodies (Step 5 verification commit `1fd9846`
  carries them in full).
- **Binding framing clarification** (Gate 2 framing §6.2):
  *Arbitration-state fields remain call-site-owned explicit
  inputs. Dispatch provenance is contextual metadata derived
  at emission time and does not participate in arbitration
  semantics.* (Travels alongside the carriers.)
- **New carrier #15** (PR 8, framing §0): *PR 8 seeds the
  chat-handler observation surface only. Chain-step seeding
  is explicitly deferred because handlers.py and _step.py
  produce semantically distinct observation records.
  Cross-surface expectation semantics require a dedicated
  framing pass before implementation proceeds.* The third
  clause is governance — implementation-first chain-step
  seeding is rejected at the spec layer (spec §7).
- **Member #7 protection** (PR-8-local, scope `_seed.py` +
  `emit_seed_expectation`): *A unified "richer" record
  appears mechanically simpler because it collapses authored
  expectation and observed arbitration into one persistence
  surface. The simplification is false: it destroys
  falsifiability by allowing expectation and observation to
  co-author the same artifact.*
- **Member #8 protection** (PR-8-local, scope `_seed.py` +
  `emit_seed_expectation`): *Inlining persistence into
  emit_seed_expectation appears symmetrical with
  emit_divergence_capture but silently transfers persistence-
  topology authority into a semantics-scoped helper. The
  separation is protected because authored expectation and
  persistence topology are intentionally distinct authority
  surfaces.*

The 18 sentences land at four placement sites:

1. **`forge_bridge/corpus/_seed.py` module docstring** (lines
   1-200 post-Step-4.5) — carrier #15 at TOP (per the
   relevance-by-file ordering established at PR 7 close
   §1.5), then inherited carriers #1–#14 in numbered order,
   then binding clarification, then member #7 + #8 with
   operational prose. The three-way authority partition
   section (lines 162-182) carries spec §4.1.5.1's
   architectural framing.
2. **`emit_seed_expectation` docstring** (lines 227-275) —
   member #8 verbatim as the helper's authority guard +
   operational rationale (lines 233-238 verbatim block).
3. **`drive_seed_fixture` docstring** (lines 436-492) —
   carrier #15 verbatim (lines 449-457) + orchestration-
   not-authoring guard (lines 467-471) at the orchestration
   surface.
4. **`tests/corpus/test_pr8_seed_surface.py` module
   docstring** (lines 1-57 post-Step-4.5) — carriers carried
   BY REFERENCE at lines 35-53 per spec §0 travel site #4:
   *"per-test-file carrier blocks stay slim — test names and
   module name carry the contract; the docstring carries
   inherited governance by reference."*

PR-7-LOCAL pairs (§4.2 inert-parameter, §5.5
legacy-synthesis) do NOT travel into PR 8 — they remain
scope-local to `_capture.py` and `reader.py` respectively
per PR 7 close §2.1's explicit non-regeneration rule.

### 1.5 Carrier #15 at TOP — extending the relevance-by-file ordering principle

PR 7 close §1.5 established the relevance-by-file ordering
principle: per-file carrier placement is justified by what
the file's job is. `_capture.py` placed PR 7 carriers AFTER
PR 3 carriers (PR 3 persistence framing is foundational);
`reader.py` placed PR 7 carriers AT TOP (PR 7's §5.5
legacy-synthesis pair was most relevant to read-time
interpretation).

PR 8 extends the principle to a NEW file (`_seed.py`):

- Carrier #15 lands AT THE VERY TOP of the carrier block. The
  rationale (per spec §0): *"a reader who encounters _seed.py
  without reading the full spec should encounter carrier #15
  first (the chat-handler-only scope governance), then the
  inherited carriers + binding framing clarification, then
  the two PR 8-local protections."*
- Carriers #1–#14 land in their inherited numbered order
  AFTER carrier #15.
- The binding framing clarification + PR 8-local member #7 +
  member #8 protections land AFTER the inherited carriers.

The placement order reflects the architectural ordering: the
NEW file's governance (carrier #15) is most relevant to a
reader landing in `_seed.py` for the first time; the
INHERITED governance is reference material; the PR-8-LOCAL
protections are the architectural-defense material that
operationalizes the new authority surface.

The principle generalizes: in any new module, the most-current
PR-anchored governance text lands first (most relevant);
inherited governance follows; module-local protections close
the carrier block.

### 1.6 14 named tests in 1 file / 25 collected (parametrize expansion)

PR 7 added 27 new pytest IDs across FIVE new test files. PR 8
adds 14 named tests in ONE new file. The shape contrast:

| | PR 7 | PR 8 |
|---|---|---|
| New test files | 5 | 1 |
| Named tests | 27 | 14 |
| Collected cases | 27 | 25 |
| Parametrize expansion | none | 11 (test_expectation_record_requires_three_keys × 3 + test_expectation_record_field_types_validated × 10 — minus 2 named-test bases collapsing into parametrize) |
| Risk coverage | 5 risks across 8 steps | 6 risks across 5 steps |

The single-file consolidation is intentional. PR 8's new module
(`_seed.py`) is a single authority surface with three internal
sub-partitions (§1.1). The 14 named tests live alongside the
two participation discipline tests (tests 12 + 13 — they fire
on `_seed.py` import-shape drift) in the same module. The
schema-extension tests (1–4) test `_schema.py` extension
indirectly (via the constant + validator under the new branch),
but live in the seed-surface module because the extension is
PR-8-bound consumer surface.

Final counts (forge env, Python 3.11):
- **200 corpus tests pass** (175 PR 7 baseline + 25 PR 8 cases). ✓
- Layer 3 lint passes unchanged — 17/17 against the unchanged
  `_capture.py`. ✓
- PR 4 + PR 5 integration tests pass unchanged under all four
  capture states — 14/14. ✓
- PR 7 regression suite passes unchanged — 27/27 across the
  6 PR 7 modules. ✓
- chat-handler tests pass unchanged — 50/50. ✓
- `forge_bridge.__all__` unchanged at 19 symbols; PR 8 helpers
  correctly excluded. ✓

**Test count divergence from spec §5.3 projection (189):** The
divergence is parametrize expansion at Step 2 (the spec named
`test_expectation_record_requires_three_keys` and
`test_expectation_record_field_types_validated` as single
tests; pytest parametrize expanded them to 3 + 10 cases
respectively, adding 11 collected cases on top of the 14
named-test base + 11 + 2 = 25 collected total). Named-test
count matches spec §5.1 exactly. PR 9 framing baseline
projections should use the named-test count (14); pytest run
verification should use the collected count (25). This is
archaeology-grade fact, recorded for forward use.

### 1.7 `_SEED_PERMITTED_IMPORTS` as semantic-not-cardinal participation contract

PR 7 framed the participation discipline via Layer 1
(`_ALLOWLIST` of file names in `test_pr3_discipline.py`).
PR 8 extends the discipline via Layer 2 — a PR-8-LOCAL
participation contract enforced by a frozenset of permitted
import-paths PLUS an AST walker that checks `_seed.py`'s
actual imports against the frozenset:

```python
_SEED_PERMITTED_IMPORTS: frozenset[str] = frozenset({
    # Authority surfaces (2):
    "forge_bridge.corpus._capture.seed_dispatch_scope",
    "forge_bridge.corpus._capture._persist_expectation_record",
    # Universal-key utilities (3):
    "forge_bridge.corpus._capture._now_iso_ms",
    "forge_bridge.corpus._capture._new_uuid",
    "forge_bridge.corpus._schema.SCHEMA_VERSION",
})
```

The 5-symbol set is the ARTIFACT of admission decisions made at
framing review, not the binding constraint. Per spec §4.5.2:
*"the participation contract is semantic, not cardinal."*

What the discipline rejects:
- Persistence-topology authority symbols: `_build_capture_record`,
  `_resolve_corpus_dir`, `_make_header`, `_serialize_line`,
  direct file I/O.
- Arbitration-surface authority symbols: anything that would
  let `_seed.py` participate in narrowing or tool dispatch.

What the discipline ALLOWS via universal-key utilities:
- Time + UUID generation (`_now_iso_ms`, `_new_uuid`) — these
  are infrastructure, not authority-bearing.
- Schema version constant (`SCHEMA_VERSION`) — same.

A future PR adding a sibling universal-key utility (e.g., a
deterministic-ID generator at PR 9) routes through framing
review to confirm the addition belongs in the universal-keys
class and not in the persistence-topology class. The
admission decision is framing-level; the
`_SEED_PERMITTED_IMPORTS` test value here is the artifact of
that decision.

**This is the second canonical instance of the truth-vs-
mechanism distinction PR 6 introduced** — the frozenset is the
mechanism; the property is "the seed-driver module participates
in authority surfaces named at framing time, never in
persistence-topology or arbitration-surface symbols." The
discipline generalizes; future authority surfaces (Gate 4
comparator, hypothetical Gate 5 reporters) will reuse the
pattern.

### 1.8 Path E: sync→async bridge as architectural seam

The Q1 framing lock chose in-process chat-handler invocation
(test isolation; no socket overhead; deterministic). The Q4
framing lock kept `drive_seed_fixture` synchronous (consumer-
visible signature is `def drive_seed_fixture(...) -> None`).
The collision requires a sync → async bridge inside the
driver body.

Spec §4.5.4 named this bridge **Path E** and named
`_invoke_chat_handler_in_process` as the seam-carrier with
FOUR architectural roles:

1. **Sync → async bridge.** The sync driver reaches the async
   handler via `asyncio.run` invoking this helper.
2. **Request-envelope reconstruction seam.** A minimal
   Starlette `Request` is constructed inside the helper (ASGI
   scope dict + injected body bytes). The reconstruction wraps
   truth in the chat-handler protocol envelope; it does NOT
   reconstruct arbitration truth (carrier #6 preserved — the
   envelope IS the chat-handler arbitration surface).
3. **Corpus → console exception seam.** The function-scoped
   `from forge_bridge.console.handlers import chat_handler`
   lives inside the helper. The exception's effective scope is
   the helper's invocation, NOT `_seed.py`'s import time.
4. **Carrier #15 enforcement seam.** The chat-handler-only
   scope is the helper's single concern; tests patch this
   helper's target (`forge_bridge.console.handlers.chat_handler`,
   the SOURCE namespace per the patch-target architectural
   choice) to assert chain-step is never invoked during seeded
   driver executions.

The four roles are intentionally distinct — collapsing any two
would erode a named architectural property:

- Collapse role 1 into role 4 → driver becomes async; carrier
  #15's mechanical enforcement breaks because the patch surface
  shifts.
- Collapse role 2 into the driver → the request reconstruction
  pollutes the orchestration surface; the orchestration
  authority class blurs into protocol-wrapping authority.
- Collapse role 3 into module scope → the corpus → console
  exception scope generalizes; spec §4.5.3's exception-surface
  property erodes.

The "Path E" name is the reviewer's lookup for any future
modification of the seam. A future PR proposing to modify
`_invoke_chat_handler_in_process` must address each of the
four roles explicitly.

---

## 2. What PR 9 inherits from PR 8

### 2.1 The 18 verbatim sentences

Fourteen inherited carriers + binding framing clarification +
new carrier #15 + two PR-8-LOCAL protections travel into PR 9
unchanged. PR 9's deliverable is fixtures + integration tests
consuming `drive_seed_fixture`; the verbatim sentences travel
into:

- PR 9 fixture module's module docstring (the carrier block
  follows the relevance-by-file ordering principle PR 7 close
  §1.5 established + PR 8 close §1.5 extended).
- PR 9 commit message bodies (per spec §0 travel site #5,
  preserved across PR 8 → PR 9 boundary).

PR 9 will likely introduce additional carriers (the fixtures
surface is structurally distinct from the seed-driver authority
surface). PR 9 framing names those at framing time.

**The PR-8-LOCAL protections (members #7 + #8) DO NOT
regenerate** — they remain scope-local to `_seed.py` +
`emit_seed_expectation` per spec §0's PR-N-LOCAL non-
regeneration rule. PR 9 may inherit the protections by
reference if its fixtures surface the same architectural risks,
but verbatim travel is scope-bounded.

### 2.2 The `emit_seed_expectation` seam

The single most consequential PR-9-bound artifact PR 8 ships.
The helper:

- Lives in `_seed.py` as a public-from-corpus helper (not in
  `forge_bridge.__all__`, but importable from
  `forge_bridge.corpus._seed`).
- Takes three keyword-only arguments (`fixture_id`, `prompt`,
  `expected_narrow`).
- Builds a 7-key expectation record dict (4 universal keys +
  3 PR-8-required keys).
- Persists via `_persist_expectation_record` (the PR 7 seam).
- Wraps everything in I-6 failure-invisibility (defense in
  depth — `_persist_expectation_record` already wraps
  internally).

PR 9's fixtures will invoke `emit_seed_expectation` via
`drive_seed_fixture` (the orchestration surface), NOT directly.
The driver delegation is the load-bearing protection; PR 9
fixtures construct `(fixture_id, prompt, expected_narrow)`
tuples and hand them to `drive_seed_fixture`.

**What PR 9 must NOT do:**

- Couple `emit_seed_expectation` to `_dispatch_context` or any
  arbitration-state input (per member #8 protection +
  signature lock).
- Inline `_persist_expectation_record` into `emit_seed_expectation`
  (per member #8 protection — semantics-not-topology).
- Promote `emit_seed_expectation` or `drive_seed_fixture` to
  `forge_bridge.__all__` (per spec §7 phase-end rejection row;
  the public-export question may be revisited at PR 9 framing
  if a CLI consumer establishes external need).
- Refactor `drive_seed_fixture` to internally build the
  expectation record (per orchestration-not-authoring guard
  + member #8 + §4.1.5.1 partition).

### 2.3 The `drive_seed_fixture` orchestration surface

The sync driver that orchestrates one seed fixture's execution:
expectation persistence → scope activation → in-process chat-
handler invocation → scope exit. The driver yields nothing;
its consumer is interested in the EMISSION SIDE-EFFECT
(observation record persisted inside chat_handler's body
BEFORE the response is built), not the chat_handler response
itself.

PR 9 fixtures will invoke `drive_seed_fixture` per fixture (per
carrier #15's chat-handler-only scope; per Q1's in-process
choice; per Q4's sync-driver choice). The driver is the
operational seam between fixture loading (PR 9) and chat-
handler invocation (production).

The driver's docstring carries carrier #15 verbatim AND the
orchestration-not-authoring guard. Future contributors landing
mid-driver via grep see both protections.

**What PR 9 must NOT do:**

- Propose driving `_step.py:233` from `drive_seed_fixture`
  (per carrier #15 + spec §7; requires a NEW framing pass
  defining cross-surface expectation semantics BEFORE
  proposing implementation).
- Bypass `drive_seed_fixture` and call `emit_seed_expectation`
  + `seed_dispatch_scope` + chat_handler directly (collapses
  the orchestration authority surface).

### 2.4 The expectation record schema — additive extension

The PR 8 schema extension added an `expectation` branch to
`validate_capture_record`:

- 3 required keys (`fixture_id`, `prompt`, `expected_narrow`)
  beyond the 4 universal keys + `record_kind`.
- 4 per-field type validations (`str` / `str` / `list[str]`).
- The preserved no-source check (PR 7's contribution; member #7
  enforces persistence-boundary truth-partitioning).

PR 9 may extend the expectation record with additional
operational fields IF a framing-level decision authorizes the
extension. The minimum-viable shape (3 required keys) was
locked at PR 8 framing §5.3 Q2 explicitly — Q2's binding
decision: *"`fixture_id`, `prompt`, `expected_narrow` are the
minimum-viable; additional fields are PR 9+ decisions."*

The schema validator's `record_kind == "expectation"` branch is
the mechanical guard. Adding a 4th required field requires:
- Updating `_REQUIRED_EXPECTATION_KEYS` in `_schema.py`.
- Updating `emit_seed_expectation`'s signature + body.
- Updating `base_expectation_args` in `_pr3_helpers.py`.
- Adding parametrized type-validation tests for the new field.

PR 9 framing must explicitly state whether expectation records
extend, and if so, name the new fields + their type-validation
requirements.

### 2.5 The PR-8-INTERNAL three-way authority partition

PR 9 inherits the §4.1.5.1 partition unchanged. The three
authority surfaces are:

- Authored expectation semantics → `emit_seed_expectation`
- Orchestration semantics → `drive_seed_fixture`
- Persistence topology → `_persist_expectation_record`
  (PR 7 seam)

PR 9 fixtures will TRANSACT with `drive_seed_fixture` only —
the orchestration surface is the consumer-facing boundary. The
other two surfaces are corpus-internal; PR 9 imports them at
its peril (PR-9-LOCAL participation discipline may extend the
`_SEED_PERMITTED_IMPORTS` pattern to PR 9 fixture modules at
framing time).

The three §7 rejection rows (PR 8 close §1.1) enforce against
collapse. PR 9 may not propose ANY of those collapses.

### 2.6 Test infrastructure additions

PR 8 ships three new test infrastructure pieces:

1. **`base_expectation_args()`** in `tests/corpus/_pr3_helpers.py`
   — the third helper joining `base_writer_args()` /
   `base_builder_args()` (PR 7 contributions). Builds default-
   valid kwargs for `emit_seed_expectation`. PR 9 fixtures may
   consume directly.

2. **`clean_rate_limit_state`** fixture in
   `tests/corpus/conftest.py` — grounds against
   `forge_bridge.console.handlers._reset_for_tests()`. Ensures
   each PR-8 driver test gets a fresh rate-limit slate. PR 9
   integration tests will likely consume directly.

3. **`_sync_console_package_attrs_with_sys_modules`** autouse
   fixture in `tests/corpus/conftest.py` (the 6th amendment's
   resolution) — defensive autouse re-sync after upstream
   reload patterns. Operates silently and unconditionally;
   PR 9 tests inherit transparently.

PR 9 may need additional helpers (e.g., `await_request_json`
was introduced at Step 4 inline in `test_pr8_seed_surface.py`
— if PR 9 needs an analog, the framing should flag whether it
moves to a shared helper or stays in-module).

### 2.7 Surface-before-implementation discipline

The PR 3 → PR 4 → PR 5 → PR 6 → PR 7 → PR 8 cadence carries
unchanged into PR 9:

- Framing artifact (registered, surfaced for review).
- Spec derived from framing (surfaced for review).
- Spec amendments at incarnation registered as NO-code commits
  if mismatches surface.
- Implementation derived from spec, with cadence-matches-work-
  depth review.
- Surface-diff-for-review at every commit regardless of depth.
- Atomic merge.

PR 9 drafts framing after the PR 8 close commit lands.

PR 8 introduces a new variant: **verification-time amendments**
(the Step 4.5 pattern). PR 9 should expect verbatim-travel
verification at its own Step 5 to potentially surface
implementation-time amendments analogous to PR 8's 5th–7th.

---

## 3. What PR 9 changes

### 3.1 Introduces fixture corpus + fixture loader

PR 9's primary deliverable is a corpus of seed fixtures
(file-based, per Gate 2 framing) + a loader that hands tuples
to `drive_seed_fixture`. The exact format — JSON? YAML?
Python dicts? — is PR 9 framing work. What's locked from PR 8
is the driver-invocation pattern:

```python
for fixture in load_fixture_corpus():
    drive_seed_fixture(
        fixture_id=fixture["fixture_id"],
        prompt=fixture["prompt"],
        expected_narrow=fixture["expected_narrow"],
    )
```

This is illustrative, not binding — PR 9 framing locks the
actual shape. The structural commitments PR 8 makes are:

- The fixture loader invokes `drive_seed_fixture` per fixture
  (one-at-a-time scoped invocation, per carrier #15 + Q1
  in-process choice).
- The fixture loader does NOT bypass `drive_seed_fixture` and
  call `emit_seed_expectation` directly (collapses the
  orchestration partition).
- The fixture loader does NOT add chain-step invocation (per
  carrier #15 + §7 rejection row).

### 3.2 May extend expectation record with operational fields

Per §2.4, PR 9 may extend if framing authorizes. The most
likely extensions surface in PR 9 framing:

- Metadata fields (e.g., `fixture_source`, `created_at_iso`,
  `expected_tools_seed_corpus_version`) — these are bookkeeping,
  not arbitration-state.
- Optional arbitration-context fields (e.g., `expected_decision`,
  `expected_candidates_after_narrowing`) — these would deepen
  the comparator's check surface at Gate 4.

PR 9 framing must explicitly justify each new field against
the spec §3 risks (particularly risk #4 — schema discriminator
drift) and against the cleanup-pressure-resistance class
(particularly member #7 — companion records as truth-
partitioning).

### 3.3 Integration tests consuming `drive_seed_fixture`

PR 8 ships unit tests of `drive_seed_fixture` (tests 8–11). PR 9
ships integration tests — running drives against the actual
fixture corpus + asserting the EMISSION SIDE-EFFECTS (observation
records persisted; companion expectation records persisted;
both joinable by `fixture_id`).

The integration tests are the operational corroboration of the
Gate 2 deliverable. Without them, the seed driver is unit-tested
but not end-to-end verified.

### 3.4 What does NOT change

- v1 schema continues unchanged (additive extension at PR 8;
  no version bump per spec §7 close conditions).
- The 14 inherited carriers + binding framing clarification +
  new carrier #15 travel verbatim into PR 9 module docstrings.
- The PR-8-LOCAL protections (members #7 + #8) do NOT
  regenerate but travel by reference if PR 9 surfaces the same
  architectural risks.
- The §4.2 + §5.5 PR-7-LOCAL pairs do NOT regenerate.
- The three-layer structural-test discipline (Layer 1
  `_ALLOWLIST` + Layer 2 participation + Layer 3 visual-asymmetry
  lint) carries.
- The cadence-matches-work-depth review rule carries.
- The PR-INTERNAL three-way authority partition carries
  unchanged.
- The cleanup-pressure-resistance class 8-member final
  inventory carries — PR 9 may add members if a structural
  commitment surfaces, but the existing 8 members are
  unchanged.
- `forge_bridge.__all__` stays at 19 symbols (per spec §7
  rejection row; CLI surface considerations are PR 9+ framing).

---

## 4. Step-by-step verification archaeology

Per spec §6 (amended by Step 4.5), PR 8 implemented a 5-step
sequence plus one verification-surfaced amendment commit.
Each step's verification observations:

| Step | Commit | Review depth | What landed | Verification |
|---|---|---|---|---|
| 1 | `0cc389d` | Full three-round | `_seed.py` skeleton (full module docstring + 5 imports + 3 NotImplementedError stubs) + `_SEED_PERMITTED_IMPORTS` + AST walker + tests 12 + 13 | `pytest tests/corpus/test_pr3_discipline.py` passes with `_seed.py` present (`_ALLOWLIST` admits by structural location); tests 12 + 13 pass against the skeleton; Layer 1 discipline boundary verified |
| 2 | `5d8bef7` | Full three-round | `_schema.py` expectation-branch extension (`_REQUIRED_EXPECTATION_KEYS` + 6-check branch) + 4 schema tests / 15 parametrized cases | 4 tests / 15 cases pass; PR 7's `test_pr7_record_kind_schema.py` 4 tests unchanged; **5th amendment surfaced**: PR 7 test helpers anchored on pre-extension shape required 5 surgical updates (3 helpers + 2 test bodies) — absence assertions reframed under the additive extension |
| 3 | `7a299bd` | **Full three-round (architectural-center #1)** | `emit_seed_expectation` body (7-key record + seam delegate + I-6 wrap) + `base_expectation_args` helper + 3 helper tests | 3 tests pass; PR 7's `test_pr7_expectation_persistence.py` 5 tests unchanged (regression: consumer-side helper does not modify the seam); patch-target architectural choice documented — module-scoped imports → patch CONSUMER namespace; function-scoped imports → patch SOURCE namespace |
| 4 | `76959c1` | **Full three-round (architectural-center #2)** | `drive_seed_fixture` body + `_invoke_chat_handler_in_process` async helper (Path E) + `clean_rate_limit_state` fixture + 4 driver tests + `__all__` drift guard | 4 driver tests + 1 `__all__` test pass; full PR 8 surface module passes (25 collected at this step); **6th amendment surfaced**: `test_pr4_no_dependency` reload teardown pattern leaves stale parent-package attributes — defensive autouse fixture `_sync_console_package_attrs_with_sys_modules` resolves; production code unchanged |
| 4.5 | `9785d69` | Light-touch (verification-surfaced) | Stale Step-1 scaffold prose cleanup (`_seed.py` lines 19-23 + `test_pr8_seed_surface.py` lines 55-59 + line 61 anachronistic Step-1 reference) | 200/200 corpus tests pass unchanged; net 14 deletions / 2 insertions; **7th amendment surfaced**: Step-1 scaffold prose describing future-state must be amended at the step that lands the body — sibling of amendments 5 + 6 in the "implementation-time amendment hygiene" cluster |
| 5 | `1fd9846` | Light-touch (verification-only) | NO code; empty commit registering verification archaeology + the 18 verbatim sentences + the 7 amendments + the 8-item verification checklist results | All 8 checklist items pass; verbatim travel verified clean post-Step-4.5; close artifact lands next as a distinct subsequent commit per spec §6 closing prose |

**The architectural-center moments — Step 3 + Step 4.**

PR 7 designated ONE step (Step 6) as architectural-center +
full three-round review. PR 8 designated TWO co-equal centers
(Step 3 helper + Step 4 driver) per spec §6 + framing §5.7.
Both received full review depth; both landed cleanly with all
named protections operational.

Step 3 was the moment cleanup-pressure class member #8
(semantics-not-topology) became OPERATIONAL: the helper's
keyword-only authority-pure signature + the delegation-to-seam
body shape + the docstring binding statement combined to make
the protection mechanically enforceable.

Step 4 was the moment cleanup-pressure class member #7
(companion records as truth-partitioning) AND carrier #15
(chat-handler-only scope) became OPERATIONAL: the driver's
expectation-persistence-then-scope-then-invocation ordering +
Path E sync→async bridge + tests 8 + 9 + 10 + 11 combined to
make both protections mechanically enforceable.

**The verification-surfaced amendment — Step 4.5.**

Step 4.5 is a new variant in the methodology. PR 7's amendments
both surfaced at IMPLEMENTATION time (pre-Step or mid-Step
grounding pass). PR 8's amendments 1–6 surfaced at SPEC-DRAFTING
or implementation time. Amendment 7 surfaced at VERIFICATION
time — the verbatim-travel cross-check (spec §6 Step 5 item 8)
read the four placement sites and surfaced stale scaffold prose
adjacent to (but not within) the verbatim blocks.

The Step 4.5 commit's resolution: surgical removal as a
DISTINCT commit BEFORE the Step 5 verification commit. The
Step 5 commit then lands clean as verification-only. The
deviation from the locked 5-step cadence is justified by the
fact that Step 5 verification is what surfaced the drift;
absorbing the fix into Step 5 would have collapsed two distinct
authority classes (verification archaeology vs. drift
remediation).

The methodology generalizes: **Step 5 verification may surface
drift even when implementation steps closed cleanly. The
resolution is a surgical pre-Step-5 cleanup commit, NOT
folding the fix into Step 5.**

**The light-touch-still-warrants-redline pattern — Step 4.5.**

Even at light-touch depth, Step 4.5's pre-commit surface-diff
caught the §6 "Step 1" anachronism on line 61 of the test
module (originally "§6 Step 1" → updated to "§6"). Without the
surface-diff pass, the line-61 fix would have been missed and
the scaffold-cleanup commit itself would have shipped an
incomplete diff.

The PR 7 close §5.3 observation continues to hold: light-touch
review depth ≠ skip pre-commit redline.

---

## 5. Methodology observations surfaced during PR 8

PR 7 produced six methodology observations. PR 8 produces SEVEN
(see §1.3 for the full inventory). Each is a candidate for
promotion to `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md`.

The PR 8 contribution is dominated by **the implementation-
time amendment hygiene cluster** (amendments #5–#7 in §1.3 —
schema extension breaking absence assertions; reload patterns
breaking import attribute consistency; bodies landing while
scaffold prose remains). Three independent failure modes;
common methodological pattern.

### 5.1 The implementation-time amendment hygiene cluster

Three failure modes share the root pattern: state described in
code/tests/docs at one step rots when a LATER step modifies
the described surface.

- **Amendment #5 (Step 2):** schema extension obsoletes
  absence-assertion regression tests.
- **Amendment #6 (Step 4):** test reload patterns leave stale
  parent-package attributes, breaking string-form patch
  targets.
- **Amendment #7 (Step 4.5):** Step-1 scaffold prose remains
  in the source after Steps 3+4 land the bodies the prose
  described as pending.

**The methodology observation:** implementation step closure
must include "what previously-correct claims has this step now
made stale?" — across three independent surfaces (test
assertions, test infrastructure, source docstrings). The
sibling lessons are independent in their mechanics but unified
in their root cause: the implementer's local frame at step N
does not include the global rotation of what step N just
falsified about earlier steps' code.

Promotion: register as cluster candidate at PR 8 close; defer
to corroboration check during PR 9 (a fourth implementation-
time amendment of similar shape during PR 9 would unlock
promotion).

The cluster designation identifies the shared amendment-hygiene
pattern across amendments #5–#7 and does not supersede the
individual promotion candidacies. Each underlying amendment
(#5, #6, #7) remains a candidate in its own right per §1.3
+ §8; the cluster is a higher-order methodological pattern
that travels alongside, not in place of, the individual
candidacies.

### 5.2 Verification-time amendments are a new variant — Step 4.5 pattern

PR 7's amendments both surfaced before implementation closed
(pre-Step-5 grounding pass). PR 8's amendment 7 surfaced
DURING verification archaeology itself (spec §6 Step 5 item 8
verbatim-travel cross-check).

**The methodology observation:** Step 5 verification is not
just a checkbox pass — it can surface non-verbatim-travel
drift adjacent to the verified blocks. The resolution pattern:
surgical pre-Step-5 cleanup commit, NOT folding into Step 5
itself.

This generalizes PR 7 close §5.1's "spec amendments at
incarnation are normal" observation to include
verification-time amendments as a third sub-class (joining
drafting-time spec amendments + implementation-time step
amendments).

### 5.3 Three-way authority partitions are first-class architecture

PR 7's three GATE-level authority surfaces were a binary-then-
trinary partition pattern (PR 4 observation surface →
PR 5 + PR 7 added two more). PR 8 introduced a PR-INTERNAL
three-way sub-partition of one of those three (§4.1.5.1).

**The methodology observation:** when a single named authority
surface starts taking on multiple internal authority concerns,
look for the three-way (or N-way) partition explicitly. The
richer partition surfaces collapse-rejection opportunities
that the binary-or-implicit partition would have missed.

PR 8 §7 contains 3 rejection rows for the 3 collapse modes of
the §4.1.5.1 partition. PR 7's §7 had 1 rejection row for the
helper-duplication collapse. The N-way pattern multiplies
collapse-mode coverage with N rejection rows, not N choose 2.

### 5.4 The patch-target architectural choice is structurally determined

Step 3 surfaced and documented:
- Module-scoped imports → patch CONSUMER namespace.
- Function-scoped imports → patch SOURCE namespace.

Step 4 added a wrinkle (the 6th amendment): even the
consumer-vs-source distinction isn't complete; Python's import
machinery has a `sys.modules`-vs-parent-package-attribute
asymmetry that surfaces under reload patterns. The defensive
autouse fixture is the minimal repair.

**The methodology observation:** test-patch targets are not a
stylistic choice — they're structurally determined by how
Python resolves the lookup. Tests that get this wrong silently
pass (no interception fires; protection erodes invisibly).
Future authority surfaces using function-scoped imports
(exception surfaces per §4.5.3) must consciously align test
patch targets to the SOURCE namespace.

This is candidate for SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+
under a new heading "test infrastructure under Python
import-machinery asymmetries."

### 5.5 The participation contract as semantic-not-cardinal

Spec §4.5.2 named this explicitly: the participation contract
is semantic (rejection of persistence-topology authority), not
cardinal (5-symbol limit). The frozenset value is the artifact
of admission decisions made at framing review, not the binding
constraint.

**The methodology observation:** test constants that LOOK like
constraints (frozensets, allowlists, counts) need explicit
disambiguation in their docstring: are they the contract, or
the artifact of the contract? If the artifact, future
admission decisions route through framing — the test value
updates as a consequence, not as a primary act.

This sibling-lessons with PR 7's `_ALLOWLIST` (admission-by-
structural-location, not name extension). Both PR 7 and PR 8
have surfaced framing-time admission discipline as a recurring
pattern. Promotion candidate as cluster.

### 5.6 The relevance-by-file ordering principle generalizes to NEW modules

PR 7 close §1.5 established the principle for existing files
(`_capture.py` keeps PR 3 carriers first; `reader.py` puts
PR 7 carriers first). PR 8 close §1.5 extends to NEW files:
carrier #15 (PR 8 new carrier) lands AT THE VERY TOP of
`_seed.py`'s carrier block; inherited carriers follow;
PR-8-LOCAL protections close.

**The methodology observation:** in any new module, the
ordering principle holds: most-current PR-anchored governance
text first; inherited governance follows; module-local
protections close the carrier block. This is a stable
methodology pattern across two reliability phases (PR 7
extended to existing files; PR 8 extended to new files).

### 5.7 Close-authors-inheritance / framing-consumes-inheritance — corroborated again

PR 4 → PR 5 → PR 6 → PR 7 close artifacts each authored the
inheritance section. PR 7 close §5.6 framed this as a stable
methodology pattern. PR 8 close (this artifact) provides
independent corroboration: PR 8 framing did not re-derive what
inherits from PR 7 by reading session history — it consumed
PR 7 close §2 directly.

**The methodology observation:** the close → framing cadence
is now corroborated across SIX phase boundaries. Promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` is overdetermined
on the corroboration side; the question is when to formalize
the methodology document itself.

Open question for v1.6+: should the methodology document
itself be drafted at PR 9 close (Gate 2 closure) or at the
v1.5 milestone close? The candidate set is now large enough
(~10 observations from PR 7 + PR 8) that the document is
write-ready; the question is whether more reliability phases
add more candidates first.

---

## 6. Mechanical checkpoints across PR 8's 5 steps + Step 4.5

PR 8 did not run operator-driven bite-verification scratches in
the PR 6 style. PR 8's architectural class is "authority
boundary at a new module + additive schema extension"; the
mechanical guards in the source serve as the verification
surface. The mechanical checkpoints across the 5 steps + 0.5:

| Checkpoint | When | What it verified | Result |
|---|---|---|---|
| Step 1 → Step 2 | Post-Step-1 | `_seed.py` skeleton present + `_ALLOWLIST` admits by structural location + participation discipline tests fire against the skeleton | ✓ Discipline boundary held without `_ALLOWLIST` extension (per §4.5.1 amendment) |
| Step 2 → Step 3 | Post-Step-2 | Schema validator's expectation branch operational before `emit_seed_expectation` exercises it | ✓ 4 schema tests / 15 parametrized cases pass; PR 7 `test_pr7_record_kind_schema.py` unchanged; failure-mode ambiguity (schema vs. helper) split |
| Step 3 → Step 4 | Post-Step-3 | Authored expectation helper operational (3 tests + PR 7 expectation-persistence regression) before driver wraps it | ✓ Helper docstring carries member #8 verbatim; participation discipline test 13 passes — `_seed.py` imports match `_SEED_PERMITTED_IMPORTS` exactly (5 symbols) |
| Step 4 immediately-after | Post-Step-4 | **Full PR 8 surface module green (4 driver + 1 `__all__` drift + previous 9 = 14 named tests / 25 collected)** + verbatim travel placements sanity-checked | ✓ **25/25 PR 8 cases**; carrier #15 + member #7 + member #8 all operational at three placement sites each |
| Step 4 → Step 4.5 | Mid-verification | Verbatim-travel verification surfaced stale scaffold prose adjacent to (not within) verified blocks | ✓ Drift identified at `_seed.py:19-23` + `test_pr8_seed_surface.py:55-59,61`; surgical pre-Step-5 cleanup commit lands |
| Step 4.5 → Step 5 | Post-Step-4.5 | Full corpus suite unchanged after docstring drift fix | ✓ 200/200 corpus tests pass in 0.97s (forge env); 14 deletions / 2 insertions; zero verbatim-travel disruption |
| Step 5 (PR 8 close prep) | Final | 200 corpus / 50 console / 17 lint / 14 integration / `__all__` == 19 all green | ✓ All 8 verification checklist items pass; Step 5 commit is empty (no code), carries archaeology |

**The Step 4 immediately-after checkpoint was the architectural-
center mechanical guard.** Both Step 3 + Step 4 designations
as co-equal architectural centers meant that Step 4's
immediate-after checkpoint had to confirm BOTH:
1. The Step 3 helper protection (member #8 / semantics-not-
   topology) survived Step 4's driver wrap.
2. The Step 4 driver protections (member #7 / companion
   records; carrier #15 / chat-handler-only) became operational.

The 25/25 cases pass against the full PR 8 surface module is
the single most important verification observation in PR 8's
archaeology — it confirms BOTH architectural-center landings
in one pass.

**No scratch landed in main.** No bite-verification mutation
was applied to production code paths. The guards in the source
itself are the verification surface — every guard's absence
regresses a named test.

---

## 7. Reseed protocol — what the PR 9 framing session does with this artifact

When the PR 9 framing session opens:

1. **Read this CLOSE artifact first.** It contains the durable
   PR 8 state PR 9 inherits — particularly §2 (what PR 9
   inherits), §3 (what PR 9 changes), and §1.2 (cleanup-
   pressure-resistance class final inventory, now 8 members).
   Skipping it means re-deriving the §4.1.5.1 three-way
   authority partition + the `drive_seed_fixture` orchestration
   contract from session history rather than from a stable
   archival document.

2. **Read `A.5.3.2-PR8-FRAMING.md`** (`23f2a20`). PR 8
   framing's §6 cleanup-pressure-resistance class members
   #7 + #8 + Q1–Q4 binding decisions + §3 carrier #15 +
   non-acquisition commitments continue to govern PR 9.

3. **Read `A.5.3.2-PR8-SPEC.md`** §4.1.5.1 (PR-INTERNAL
   three-way authority partition) + §6 Step 4 + §7 phase-end
   conditions. §7 contains the "future PR rejection" table —
   PR 9 may not propose any of those mutations (inline
   `_persist_expectation_record`, collapse helper/driver,
   drive `_step.py:233`, promote helpers to `__all__`, etc.)
   even incidentally.

4. **Read `A.5.3.2-GATE-2-FRAMING.md`** §3.4 three-authority-
   surface partitioning + §5.7 PR partitioning (PR 9 as
   fixtures + integration tests). Gate 2's framing is what
   PR 9 closes IF PR 9 closes Gate 2; otherwise Gate 2
   continues into PR 10+.

5. **Read PR 7 close artifact** (`b035c87`) §2 (what PR 8
   inherited) for inheritance continuity check. PR 7 close §2
   still applies — PR 7's seam + scope + ontology constants
   carry into PR 9 unchanged.

6. **Re-read project memories:**
   - `project_state_2026_05_11_pr8_steps_1_4_shipped.md`
     (superseded by THIS close — update cursor).
   - `feedback_ground_specs_in_actual_files.md` — applies to
     PR 9 framing as it does to PR 8.
   - `feedback_inline_authority_boundary_guards.md` — applies
     to PR 9 fixture surfaces with authority boundaries.
   - `project_pr8_base_expectation_args.md` — now closed by PR 8
     Step 3; remove or supersede.

7. **Draft `A.5.3.2-PR9-FRAMING.md`.** PR 9's framing must
   articulate:
   - The fixture corpus shape (file format; loading semantics;
     directory layout).
   - The fixture loader's structural shape (single entry point?
     CLI? hook into existing daemon?).
   - The integration test surface (how many fixtures? coverage
     across narrowing outcomes? rejection paths?).
   - The relationship between PR 9 fixture modules and the
     Layer 2 participation discipline (does PR 9 extend
     `_SEED_PERMITTED_IMPORTS` to fixture surfaces? a parallel
     `_FIXTURE_PERMITTED_IMPORTS` frozenset?).
   - Whether expectation records extend with operational fields
     (if so, justified against §3 risks + member #7 protection).
   - The non-acquisition commitments PR 9 makes (what PR 9
     does NOT do, in PR 7/8 framing §7 style).
   - The binding decisions PR 9 ships (in PR 7/8 framing §5
     style).
   - The cleanup-pressure-resistance class members PR 9 adds
     (if any; the class is at 8 members at PR 8 close).

8. **Surface the framing for review** before drafting the
   spec. PR 7 + PR 8's discipline holds.

9. **Draft `A.5.3.2-PR9-SPEC.md`** from the locked framing.
   Spec amendments at incarnation are normal (per PR 7 §5.1 +
   PR 8 §1.3 methodology); register them as NO-code commits.

10. **Implement** against the spec per the cadence-matches-
    work-depth review rule. Surface-diff-for-review at every
    commit regardless of review depth (per PR 7 §5.3 + PR 8
    §4.5 methodology). Expect verbatim-travel verification at
    Step 5 to surface potential drift (per PR 8 §1.3 amendment
    #7 / §5.2 methodology).

11. **Close PR 9 with `A.5.3.2-PR9-CLOSE.md`** following this
    artifact's structure. If PR 9 closes Gate 2 (per Gate 2
    framing §10 PR partitioning), the close includes a Gate 2
    closure section in PR 6 CLOSE §6 style. The 8-member
    cleanup-pressure-resistance class final inventory + the
    7-amendment methodology candidate set from PR 8 + PR 7 +
    any PR 9 additions get the formal close.

The cadence — framing → spec → spec-amendments-at-incarnation
→ steps → verification-amendments-if-surfaced → close —
carries unchanged with one new variant (verification-time
amendments, per §5.2).

---

## 8. Cross-references

- `A.5.3.2-PR8-FRAMING.md` (commit `23f2a20`) — pre-spec
  binding contract; §3 carrier #15 (introduced); §6
  cleanup-pressure-resistance class members #7 + #8
  (introduced); §5 four binding decisions (Q1–Q4: in-process,
  no-streaming, sync-driver, Path E); §7 non-acquisition
  commitments.
- `A.5.3.2-PR8-SPEC.md` (commit `85c5bc1`) — implementation
  contract; 18 verbatim sentences (§0); 14 named tests / 25
  collected (§5.1); 5-step sequence (§6); §4.1.5.1
  PR-INTERNAL three-way authority partition; §4.5 four spec
  amendments at drafting (§4.5.1–§4.5.4); §7 phase-end
  conditions (rejection table for future PR proposals).
- `A.5.3.2-PR7-CLOSE.md` (commit `b035c87`) — durable archival
  state PR 8 inherited; §1.1 three-authority-surface
  partitioning (this CLOSE §1.1 sub-partitions one of those
  three); §1.2 cleanup-pressure-resistance class 6-member
  inventory (this CLOSE §1.2 extends to 8); §1.5
  relevance-by-file ordering (this CLOSE §1.5 extends to new
  modules); §5 methodology shape (this CLOSE §5 follows).
- `A.5.3.2-GATE-2-FRAMING.md` (commit `ceac9b5`) — gate-level
  architecture; §3.4 three-authority-surface partitioning
  (this CLOSE §1.1 implements PR-INTERNAL sub-partition of
  the third surface); §5.7 PR partitioning (PR 9 as
  fixtures + integration); §6.1 carrier #14 (preserved
  through PR 8); §6.2 binding framing clarification
  (preserved through PR 8); §9 schema delta (PR 8 ships the
  expectation-branch extension).
- `A.5.3.2-PR6-CLOSE.md` (commit `9168df7`) — durable archival
  state PR 7 inherited; §1.3 truth-vs-mechanism distinction
  (this CLOSE §1.7 second canonical instance for
  `_SEED_PERMITTED_IMPORTS`); §1.1 Layer 3 lint operational
  shape (regression-asserted at PR 8 close 17/17 unchanged).
- `A.5.3.2-PR5-CLOSE.md` (commit `b8f522e`) — durable archival
  state PR 6 inherited; reviewed for inheritance continuity.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state PR 5 inherited; "What PR N+1 inherits" section
  established (this CLOSE §2 follows).
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern
  (Properties A–D); preserved unchanged through PR 8 (Layer 3
  lint passes 17/17 against unchanged `_capture.py`).
- `A.5.3.2-INSTRUMENT-CONTRACT.md` §3 — record shape; PR 8
  extends the expectation branch with 3 required keys per
  Gate 2 framing §9.2.
- `forge_bridge/corpus/_seed.py` — PR 8's new module
  (532 lines pre-Step-4.5; 526 lines post-Step-4.5);
  authored-expectation surface + orchestration surface; member
  #7 + member #8 verbatim in module docstring; Path E
  sync→async bridge inside `_invoke_chat_handler_in_process`.
- `forge_bridge/corpus/_seed.py::emit_seed_expectation` —
  PR 8 §4.1.3; keyword-only authority-pure signature
  (`fixture_id`, `prompt`, `expected_narrow`); 7-key record
  builder + seam delegate + I-6 wrap.
- `forge_bridge/corpus/_seed.py::drive_seed_fixture` —
  PR 8 §4.1.5; sync orchestration surface;
  expectation-persistence → `seed_dispatch_scope` →
  in-process chat-handler invocation → scope exit.
- `forge_bridge/corpus/_seed.py::_invoke_chat_handler_in_process` —
  PR 8 §4.1.4; private async helper carrying four
  architectural seam roles (Path E sync→async bridge +
  request-envelope reconstruction + corpus → console exception
  seam + carrier #15 enforcement seam).
- `forge_bridge/corpus/_schema.py` — extended at PR 8 Step 2;
  added `_REQUIRED_EXPECTATION_KEYS` constant + 6-check
  expectation branch; no-source check preserved (member #7
  persistence-boundary guard).
- `forge_bridge/corpus/_capture.py` — UNCHANGED at PR 8 close;
  `_persist_expectation_record` consumed unchanged;
  `seed_dispatch_scope` consumed unchanged.
- `tests/corpus/test_pr8_seed_surface.py` — PR 8's new test
  module (~1074 lines post-Step-4.5); 14 named tests / 25
  collected cases; `_SEED_PERMITTED_IMPORTS` frozenset +
  `_corpus_references` AST walker; module docstring carries
  18 verbatim entries by-reference per spec §0 travel site #4.
- `tests/corpus/_pr3_helpers.py::base_expectation_args` —
  PR 8 §4.3; third test infrastructure helper joining
  `base_writer_args` + `base_builder_args` (PR 7
  contributions); default-valid kwargs for
  `emit_seed_expectation`.
- `tests/corpus/conftest.py::clean_rate_limit_state` —
  PR 8 §4.6; per-test rate-limit reset fixture; grounds against
  `forge_bridge.console.handlers._reset_for_tests()`.
- `tests/corpus/conftest.py::_sync_console_package_attrs_with_sys_modules` —
  PR 8 Step 4 6th-amendment resolution; defensive autouse
  fixture for Python import-machinery asymmetry under reload
  patterns.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3 lint;
  **unchanged by PR 8**, regression-asserted at every PR 8
  step (17/17 unchanged throughout).
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` —
  unchanged at PR 8 close per spec §4.5.1; `_seed.py`
  admitted by structural location (in `corpus/` subtree).
- `tests/corpus/test_pr4_no_dependency.py` + Step 4 reload
  patterns — the 6th-amendment-surfacing test; behavior
  unchanged at PR 8 close; the autouse fixture quietly
  restores parent-package attributes after teardown.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion
  candidates from this CLOSE §1.3 + §5:
  - §1.3 amendment #1 (§4.5.1 — enforcement topology
    grounded in actual test surface).
  - §1.3 amendment #2 (§4.5.2 — participation contract is
    semantic, not cardinal).
  - §1.3 amendment #3 (§4.5.3 — exception surface vs.
    generalized discipline).
  - §1.3 amendment #4 (§4.5.4 — Path E sync→async bridge as
    architectural seam).
  - §1.3 amendment #5 (Step 2 — absence assertions obsoleted
    by additive extensions).
  - §1.3 amendment #6 (Step 4 — Python import asymmetry under
    reload + teardown patterns).
  - §1.3 amendment #7 (Step 4.5 — Step-1 scaffold prose
    requires step-closure amendment).
  - §5.1 implementation-time amendment hygiene cluster
    (amendments #5–#7 as a unified pattern).
  - §5.2 verification-time amendments — Step 4.5 pattern.
  - §5.3 three-way authority partitions as first-class
    architecture.
  - §5.4 patch-target architectural choice (structurally
    determined; consumer vs. source).
  - §5.5 participation contract as semantic-not-cardinal
    (sibling of PR 7 `_ALLOWLIST` admission discipline).
  - §5.6 relevance-by-file ordering extended to new modules.
  - §5.7 close-authors-inheritance / framing-consumes-
    inheritance — corroborated across 6 phase boundaries.
- `project_state_2026_05_11_pr8_steps_1_4_shipped.md` (local
  memory) — superseded by THIS close; cursor updates to
  PR-8-CLOSED state.
- PR 8 commit chain (origin/main):
  - `23f2a20` — PR 8 framing registered (NO spec, NO code).
  - `35dfb9e` — Session passoff 2026-05-10.
  - `85c5bc1` — PR 8 spec registered (NO code).
  - `0cc389d` — Step 1: `_seed.py` skeleton + Layer 2
    participation discipline.
  - `5d8bef7` — Step 2: schema validator expectation-branch
    extension (5th amendment).
  - `7a299bd` — Step 3: `emit_seed_expectation` body
    (architectural-center #1; member #8 operational).
  - `76959c1` — Step 4: `drive_seed_fixture` body + Path E +
    `clean_rate_limit_state` fixture (architectural-center #2;
    member #7 + carrier #15 operational; 6th amendment via
    test infrastructure conftest).
  - `f300b2d` — Session passoff 2026-05-11 (mid-PR-8).
  - `9785d69` — Step 4.5: scaffold prose cleanup (7th
    amendment; verification-time surface).
  - `1fd9846` — Step 5: final verification (NO code; empty
    commit; 18 verbatim sentences + 7 amendments + 8-item
    checklist results in commit body).
  - **THIS COMMIT** — PR 8 close artifact registered.

---

PR 8 closes here. **Gate 2 continues into PR 9** (fixture
corpus + fixture loader + integration tests consuming
`drive_seed_fixture`). The next session opens at PR 9 framing
per §7 reseed protocol.
