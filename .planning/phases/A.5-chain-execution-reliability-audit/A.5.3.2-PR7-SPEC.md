# A.5.3.2 PR 7 — Spec (schema + contextvar provenance resolution)

**Status:** drafted 2026-05-09 (post-PR-7-framing session). Derived
from `A.5.3.2-PR7-FRAMING.md` (commit `1c1e061`). The framing is
the binding pre-spec contract; this spec is the implementation
contract derived from it.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants, eleven explicit exclusions.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs;
  visual-asymmetry pattern (§5.1); helper signature (§5.2);
  architecturally prohibited patterns (§5.3).
- `A.5.3.2-PR3-SPEC.md` — orthogonal-truth-surfaces (§5);
  atomic-append (§6.5); discipline grep (§10).
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — chat-handler
  integration; risk-category shift; integration-discipline
  quartet; finalized-state contract.
- `A.5.3.2-PR5-SPEC.md` (commit `42336c3`) — chain-step
  integration; helper-duplication binding; surface geometry
  asymmetry.
- `A.5.3.2-PR6-SPEC.md` — Layer 3 lint; Properties A–D;
  Rejections 1, 2, 4 (Rejection 3 as consequence); structural-
  backstop framing; observation-not-participation framing.
- `A.5.3.2-PR6-CLOSE.md` (commit `9168df7`) — Gate 1 close;
  durable archival state PR 7 inherits; truth-vs-mechanism
  distinction (§1.3); discovery-based input set discipline
  (§5.3).
- `A.5.3.2-GATE-2-FRAMING.md` (commit `ceac9b5`) — gate-level
  architecture; binding decisions Q1 / Q1.5 / Q1.6 / Q1.7;
  carrier #14; binding framing clarification on call-site-owned
  arbitration inputs; non-acquisition commitments (six items);
  schema delta (§9); PR partitioning table (§5.7).
- **`A.5.3.2-PR7-FRAMING.md`** (commit `1c1e061`) — binding
  pre-spec contract. Resolves the dispatch-provenance contextvar
  layer (§4.1), the runtime-inert source parameter (§4.2 + §5.1),
  the narrow persistence-surface ownership decision (§4.3 + §5.4),
  the `record_kind` discriminator (§4.4 + §9.2), the reader
  validation extension (§4.5 + §9.7), the no-yield context
  manager contract (§5.2), the private frozen dataclass payload
  (§5.3), the legacy-record synthesis policy (§5.5), the
  constructs-resistant-to-cleanup-pressure architectural class
  (§6), and six non-acquisition commitments (§7). Mandatory
  predecessor read.

**Successor (NOT this spec):** PR 8 spec — seed driver +
`emit_seed_expectation` public helper. PR 7 ships the persistence
seam PR 8 consumes; PR 7 does not draft the seed driver.

---

## 0. Crystallizing sentences (verbatim — load-bearing)

Nineteen sentences travel verbatim into PR 7's surface. Fourteen
are inherited carriers — the same set Gate 2 framing locks (§3.1).
One is the binding framing clarification on call-site-owned
arbitration inputs. The remaining four are PR 7-local binding
statements derived from this convergence pass: the §4.2 inert-
parameter pair (two sentences) and the §5.5 legacy-synthesis pair
(two sentences). The local pairs are not numbered carriers —
their scope is internal to the helper / reader documentation —
but their language is binding.

The sentences travel into:

1. `forge_bridge/corpus/_capture.py` module docstring (carriers
   #1–#14 + the binding framing clarification + the §4.2 inert-
   parameter pair).
2. `forge_bridge/corpus/_sources.py` module docstring (carriers
   #1–#14 + the binding framing clarification; the protected-
   property framing for `KNOWN_SOURCE_VALUES` per §4.1 of this
   spec).
3. `forge_bridge/corpus/reader.py` module docstring (carriers
   #1–#14 + the §5.5 legacy-synthesis pair).
4. Top-level docstrings of new test modules (carriers #1–#14;
   per-test-file carriers stay slim because tests are not
   production surfaces).
5. The PR 7 commit message body under "preserved invariants" —
   all nineteen sentences in their full form.

### Inherited carriers (verbatim)

The fourteen inherited carriers + the binding framing
clarification are reproduced here in the same order they land in
the source-of-truth artifacts (PR 6 spec §0 for #1–#13; Gate 2
framing §6.1 for #14).

**#1–#2 — risk-category shift (PR 4):**

> **PR 4 is the controlled introduction of observational
> side-effects into live arbitration surfaces.**

> **The risk category has shifted from persistence-substrate risk
> to participation-creep risk.**

**#3–#6 — integration-discipline quartet (PR 4):**

> **The call site is the source of the three explicit inputs.**
>
> **The integration layer passes truth.**
>
> **The integration layer never reconstructs truth.**
>
> **The builder does not discover runtime state.**

**#7 — finalized-state contract (PR 4):**

> **Capture emission occurs only after arbitration state is
> finalized for the current execution path. Capture records
> completed arbitration observations, not provisional intermediate
> state.**

**#8 — risk-inheritance + surface-geometry distinction (PR 5):**

> **PR 5 is the second call site under the integration discipline
> PR 4 established. The risk profile is inherited; the surface
> geometry is not.**

**#9 — caller's view of deployment identity (PR 5):**

> **The chain-step's deployment identity is the caller's view, not
> the global daemon registry view.**

**#10 — ambiguity-as-arbitration-outcome (PR 5):**

> **Ambiguity rejection is an arbitration outcome. Capture must
> record it. At this surface, `narrower_decision` carries the
> filtered list verbatim at narrowing finalization — including
> zero-match and multi-match rejection paths. `pr20_condition_met`
> is always False and `collapse_occurred` is False on all
> rejection paths. These semantics differ from the chat-handler
> case and must not be silently overloaded.**

**#11 — measured-not-inferred coverage (PR 5):**

> **No-dependency coverage at the chain-step surface must be
> measured, not inferred. The existing probe drives only the
> chat-handler single-step path; PR 5 owns the responsibility to
> extend coverage to the chain-step path empirically.**

**#12 — structural-backstop framing (PR 6):**

> **PR 6 is the structural backstop for the visual-asymmetry
> pattern. The lint validates shape, not content; structure, not
> interpretation. Carrier content is the room's job; field
> validation is the helper signature's job; the lint validates the
> visual asymmetry between arbitration and observation.**

**#13 — observation-not-participation framing (PR 6):**

> **The lint operates by observation, not by participation. It
> reads source files; it does not import the corpus package. The
> lint's own scope is the same one-directional observational flow
> the call sites enforce.**

**#14 — declared epistemic class vs. persisted provenance
(Gate 2):**

> **Property C governs the epistemic class declared at the
> observation boundary. KNOWN_SOURCE_VALUES governs persisted
> provenance classes after contextual annotation has been
> resolved.**

**Binding framing clarification — call-site-owned arbitration
inputs (Gate 2):**

> **Arbitration-state fields remain call-site-owned explicit
> inputs. Dispatch provenance is contextual metadata derived at
> emission time and does not participate in arbitration
> semantics.**

### PR 7-local binding statements

**§4.2 — runtime-inert source parameter (verbatim, scope-local
to `_capture.py`):**

> **The call-site source parameter is intentionally inert at
> runtime. Its purpose is structural (Property C compliance at
> the observation boundary), not operational (persisted
> provenance resolution).**

> **Future contributors must not remove the parameter or couple
> persisted provenance resolution to the declared call-site
> value.**

**§5.5 — legacy-record synthesis (verbatim, scope-local to
`reader.py`):**

> **`record_kind` synthesis exists solely for backward
> compatibility with records that predate PR 7. Writers
> introduced by PR 7 must always emit explicit `record_kind`
> values.**

> **Legacy records may be interpreted through synthesized
> defaults at read time but are not rewritten or normalized in
> place by the reader.**

A reader who encounters `_capture.py`, `_sources.py`, or
`reader.py` without reading the full spec should encounter the
inherited fourteen + binding framing clarification first. The
local binding pairs anchor the architectural class introduced in
PR 7 framing §6 (constructs intentionally resistant to cleanup
pressure): the §4.2 pair protects member #3 of the class (the
inert structural parameter); the §5.5 pair protects against
write-time normalization drift.

---

## 1. Real job + success condition

**Real job:** *"Land the persistence-and-resolution plumbing for
Gate 2. Introduce a contextvar-scoped dispatch-provenance layer
inside `emit_divergence_capture` so seed-driver code (PR 8) can
drive live arbitration without modifying any call site. Land a
governed `KNOWN_SOURCE_VALUES` constant at the persistence layer
to anchor record-ontology authority distinct from Property C's
structural authority. Add a `record_kind` discriminator to the
persistence schema. Extend the reader with validation against
both governance surfaces plus legacy-record synthesis at read
time. Ship the narrow private persistence-surface that PR 8's
expectation helper will consume — but do not invoke it from any
production call site in PR 7's own delta. Preserve Property C
literally and the Layer 3 lint structurally; the gate separation
between call-site-declared shape and persisted-record ontology
is the load-bearing claim PR 7 protects."*

PR 7's three operational responsibilities:

- **Establish the dispatch-provenance substrate.** A single
  module-private `ContextVar[_DispatchContext | None]` whose
  scope is managed exclusively by the public
  `seed_dispatch_scope(...)` context manager. Construction of
  `_DispatchContext` happens at exactly one site (the scope
  helper); persistence of its payload happens at exactly one site
  (the resolution path inside `emit_divergence_capture`).
- **Wire the resolution path.** `emit_divergence_capture` reads
  the contextvar at emission time and uses the resolved
  provenance to populate the persisted `source` and
  `fixture_id` fields. The call-site `source="runtime"` literal
  is structurally authoritative (Property C) and operationally
  inert (the helper ignores it).
- **Govern record ontology at the persistence layer.**
  `KNOWN_SOURCE_VALUES = frozenset({"runtime", "seed"})` lands
  in `forge_bridge/corpus/_sources.py`. `record_kind` lands in
  `forge_bridge/corpus/_schema.py` as a literal field.
  `forge_bridge/corpus/reader.py` extends with `record_kind`
  validation, `source` membership validation for observation
  records, and read-time legacy-record synthesis.

Plus one PR-7-internal-but-PR-8-bound deliverable: a private
helper `_persist_expectation_record(record: dict) -> None` in
`_capture.py` that PR 8's `emit_seed_expectation` will import and
invoke. PR 7 implements + tests the helper but does not invoke
it from any production call site. The helper is governed by the
non-participation guard in §6 step 8.

**Success condition:** *"PR 7 ships `_sources.py` (new),
modifications to `_capture.py` + `_schema.py` + `reader.py`, an
`_ALLOWLIST` extension in `tests/corpus/test_pr3_discipline.py`
admitting `_sources.py`, five new test modules covering the
dispatch contextvar, the record_kind schema, the reader
validation extension, the legacy-record synthesis, and the
private expectation persistence helper. The Layer 3 lint
(`tests/corpus/test_pr6_visual_asymmetry.py`) ships unchanged and
passes against the modified `_capture.py`. Existing PR 4 + PR 5
integration tests pass unchanged under all four capture states.
The 14 inherited carriers + binding framing clarification + the
two PR-7-local binding pairs travel verbatim into the relevant
docstrings + commit message body. Gate 1 close conditions are
preserved; PR 8 spec drafting can begin against the seam this
PR ships."*

**Operator-visible behavior change:** none in production paths.
The contextvar is `None` by default; `emit_divergence_capture`
behaves exactly as it did at PR 6 close when no scope is active,
modulo the new `record_kind="observation"` field on persisted
records. The `record_kind` field is purely additive at write
time and synthesized for legacy reads. PR 7 is plumbing — visible
to PR 8, invisible at the operator surface.

---

## 2. Scope

**In scope:**

- **New production module** —
  `forge_bridge/corpus/_sources.py`. Houses
  `KNOWN_SOURCE_VALUES` + governance docstring per §4.1.
- **Modified production module** —
  `forge_bridge/corpus/_capture.py`:
  - `_DispatchContext` private frozen dataclass.
  - `_dispatch_context` module-private `ContextVar`.
  - `seed_dispatch_scope(...)` public no-yield context manager.
  - Resolution path inside `emit_divergence_capture` consulting
    the contextvar at emission time.
  - Module docstring extension carrying carriers #1–#14 +
    binding framing clarification + §4.2 inert-parameter pair.
  - `_persist_expectation_record(record: dict) -> None` private
    helper for PR 8 consumption (no production call site
    invokes it in PR 7's delta).
- **Modified production module** —
  `forge_bridge/corpus/_schema.py`:
  - `record_kind: Literal["observation", "expectation"]` field
    added to the schema record shape.
  - `KNOWN_SOURCE_VALUES`-aware validation: when `record_kind`
    is `"observation"`, `source` must be a member; when
    `record_kind` is `"expectation"`, `source` field is absent.
  - Schema validation surfaces existing `SchemaValidationError`
    on violations (no new exception class).
- **Modified production module** —
  `forge_bridge/corpus/reader.py`:
  - Read-time legacy-record synthesis: lines missing
    `record_kind` are interpreted as
    `record_kind="observation"` synthetically before validation.
  - The synthesis is applied to the in-memory dict, never
    written back to the source file.
  - Module docstring extension carrying carriers #1–#14 +
    §5.5 legacy-synthesis pair.
- **Modified test discipline file** —
  `tests/corpus/test_pr3_discipline.py`:
  - `_ALLOWLIST` extends with `forge_bridge/corpus/_sources.py`.
  - No other modifications.
- **New test modules** (`tests/corpus/`):
  - `test_pr7_known_source_values.py` — governance shape.
  - `test_pr7_dispatch_context.py` — contextvar resolution.
  - `test_pr7_record_kind_schema.py` — schema round-trip.
  - `test_pr7_reader_validation.py` — reader validation
    extension.
  - `test_pr7_legacy_record_synthesis.py` — legacy synthesis +
    no-write-back.
  - `test_pr7_expectation_persistence.py` — non-participation
    guard + atomic-append on the private expectation helper.

**Inheritance from PR 6 (binding):**

> **PR 7 introduces no new validator or structural-lint surface.
> PR 6's Layer-3 enforcement remains unchanged and is inherited
> transitively.**

This sentence resolves the question of why PR 7 has no §5
("Property + rejection validators") — the layer it would govern
already ships in PR 6. The lint test
(`tests/corpus/test_pr6_visual_asymmetry.py`) runs against the
modified `_capture.py` as a regression checkpoint at the end of
step 5 (§6 step 5) and at PR 7 close (§7 condition 2); it
otherwise receives no PR 7 attention.

**Out of scope** (per framing §7 non-acquisitions):

1. **Modifying the Layer 3 lint.**
   `tests/corpus/test_pr6_visual_asymmetry.py` ships unchanged.
   Property C remains literal `source="runtime"`. The regression
   contract verifies the lint passes against the modified
   `_capture.py`; the lint itself receives no edits.
2. **Introducing the seed driver or the public expectation
   helper.** Those land in PR 8. PR 7's
   `_persist_expectation_record` is consumed by PR 8 but
   invoked from no production call site in PR 7's delta.
3. **Modifying call sites.** `handlers.py:1185` and
   `_step.py:233` (the two emit call sites) ship unchanged.
   Their `source="runtime"` literal stays exactly as it is; the
   helper's internal resolution is what changes.
4. **Modifying `divergence_capture_enabled()` or its env-gate.**
   The single env boundary remains the Gate 1 boundary. PR 7's
   contextvar layer is orthogonal to the env gate.
5. **Backfilling or rewriting legacy records.** Reader synthesis
   is read-time-only. A one-time migration script over the
   existing capture corpus is rejected at the spec layer per
   framing §5.5.
6. **Pre-authorizing a nested-scope token surface on
   `seed_dispatch_scope`.** The helper yields nothing publicly.
   Internal `ContextVar.set()` token use is implementation
   detail. If a future PR surfaces a concrete need for nested-
   scope introspection, that becomes an explicit framing/spec
   expansion event — never accidentally-carried-forward latent
   API surface.
7. **Promoting `seed_dispatch_scope`,
   `_persist_expectation_record`, or `_DispatchContext` to
   `forge_bridge.__all__`.** The framing §8.2 default holds:
   public export = authority-surface expansion = explicit
   future framing review. Spec position: all three stay corpus-
   internal in PR 7. PR 8 establishes the seed-driver consumer;
   if external need surfaces then, it becomes a PR 8 framing
   question, not a PR 7 spec one.
8. **Schema-version bump.** `_schema.SCHEMA_VERSION` does not
   increment. The `record_kind` field is additive and
   backward-tolerant; legacy records lacking it are read via
   synthesis, not version-gated rejection. A version bump would
   require operator-visible upgrade ritual that PR 7's plumbing
   shape does not warrant. Decision recorded in this spec; no
   code change.

---

## 3. The five risks → named tests

PR 7's risk topology differs from PR 6's. PR 6 was structural
backstop work — the risks were *the lint missing a deviation*
or *the lint rejecting a canonical site*. PR 7 is plumbing work
— the risks are *the substrate leaking semantics across
boundaries* and *the substrate eroding under cleanup pressure*.

Each of the five named risks maps to a named test that fires
when the risk materializes:

| # | Risk | Failure mode | Named test |
|---|---|---|---|
| 1 | **Contextvar leaks across scope boundary.** A `with seed_dispatch_scope(...):` block exits abnormally and the contextvar fails to reset, causing subsequent runtime emissions to falsely persist `source="seed"`. | Test wraps an emit call inside a scope with an exception raised mid-block; asserts post-block emit persists `source="runtime"`. | `test_pr7_dispatch_context.py::test_scope_resets_on_exception` |
| 2 | **Inert-parameter drift.** A future PR couples persisted `source` to the call-site `source` literal value (e.g., "let's just use what the caller passes"), eroding §4.2 and Property C's gate separation. | Test passes arbitrary string values to the call-site `source` parameter while the contextvar is active and inactive; asserts the persisted value is contextvar-derived in every case, regardless of the call-site value. | `test_pr7_dispatch_context.py::test_call_site_source_value_is_inert` |
| 3 | **Legacy-record corruption on read.** The reader extension inadvertently mutates the source file (e.g., normalizes legacy records during synthesis), eroding §5.5 and the archaeology-integrity property. | Test reads a legacy-format file (no `record_kind`) twice; computes file hash before and after each read; asserts hash unchanged across both reads. | `test_pr7_legacy_record_synthesis.py::test_legacy_file_unchanged_after_read` |
| 4 | **Schema discriminator collision.** A future record carries `record_kind` set to a value other than `"observation"` or `"expectation"`, and validation silently accepts it. | Test constructs records with literal `record_kind` values outside the enum; asserts `validate_capture_record` raises `SchemaValidationError` for each. | `test_pr7_record_kind_schema.py::test_unknown_record_kind_rejected` |
| 5 | **Expectation helper participates in provenance resolution.** The private `_persist_expectation_record` helper inadvertently consults the contextvar or carries observation semantics, blurring authority partitioning between observation and expectation. | Test invokes `_persist_expectation_record` inside an active `seed_dispatch_scope` and outside it; asserts the persisted expectation record's content is identical between both invocations (no contextvar consultation), and that the record carries no `source` field. | `test_pr7_expectation_persistence.py::test_helper_does_not_consult_dispatch_context` |

The five risks map one-to-one to the five carrier-grade
constraints PR 7 plumbing must protect: gate separation (#1, #2),
archaeology integrity (#3), structural ontology governance (#4),
and authority partitioning (#5). No test in this list validates
content; every test validates structural property preservation.

Risk #5 is **structurally co-named with the Step 8 non-
participation guard** (§6 step 8). The guard's binding statement
travels into `_persist_expectation_record`'s docstring and the
PR 7 commit message; the test in this row enforces it
mechanically.

---

## 4. Module surface

### 4.1 `forge_bridge/corpus/_sources.py` (new)

```python
"""forge_bridge.corpus._sources — persistence-layer source-class
governance.

PR 7 carrier sentences (verbatim, load-bearing — see
``A.5.3.2-PR7-SPEC.md`` §0):

[14 inherited carriers + binding framing clarification reproduced
verbatim from §0.]

This module defines the persistence-layer governance contract
for ``source`` values. The constant ``KNOWN_SOURCE_VALUES`` is
the single source of truth for which provenance classes are
admissible on observation records.

PROTECTED PROPERTY (truth):

  Persisted provenance classes are governed. Adding a new source
  class requires explicit framing-level review plus synchronous
  update of: this constant, reader validation, the contextvar
  resolution path inside emit_divergence_capture, and the Gate 4
  comparator's partition logic. Mergeability is contingent on all
  four updating in lockstep.

MECHANISM (this file):

  The frozenset constant + this docstring. Future additions to
  the set MUST land alongside the framing-level decision; the
  set's value is the artifact, not the protection.

This module does not import from any other ``forge_bridge.corpus``
module. The set is a leaf governance constant. The Layer 1 lint
allowlist (``tests/corpus/test_pr3_discipline.py::_ALLOWLIST``)
admits this file because it is structurally pure: a single
constant + governance docstring, no executable logic.

Carrier #14 (verbatim — see Gate 2 framing §6.1):

  Property C governs the epistemic class declared at the
  observation boundary. KNOWN_SOURCE_VALUES governs persisted
  provenance classes after contextual annotation has been
  resolved.

This carrier is the load-bearing protection against upward
collapse of record-ontology governance into the structural lint.
The lint stays structural; this constant is where ontology
lives.
"""
from __future__ import annotations

from typing import Final

KNOWN_SOURCE_VALUES: Final[frozenset[str]] = frozenset({"runtime", "seed"})
```

The module is **30–60 lines** total (most of the volume is the
carrier docstring). It has no functions, no classes, no imports
from `forge_bridge.corpus.*`. Layer 1 admission is mechanical.

### 4.2 `forge_bridge/corpus/_capture.py` (modified)

Five additions, in source-file order:

#### 4.2.1 New imports

```python
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator, Literal, Optional
```

`SchemaValidationError` is added to the existing
`from forge_bridge.corpus._schema import (...)` import block — it
is consumed by the §4.2.6 authority pre-check. The block already
imports `SCHEMA_VERSION` and `validate_capture_record` at PR 6
close; PR 7 extends that single block, not a new import.

`KNOWN_SOURCE_VALUES` is **not** imported into `_capture.py`. The
resolution path's source values come from `_DispatchContext.source`
(typed `Literal["runtime", "seed"]`) and the `"runtime"` default;
schema-side membership enforcement is `_schema.py`'s
responsibility. Importing the constant here would create a
redundant authority surface — the contextvar's literal type plus
the schema validator already cover both directions.

#### 4.2.2 `_DispatchContext` private frozen dataclass

```python
@dataclass(frozen=True)
class _DispatchContext:
    """Dispatch-provenance payload carried via contextvar.

    Private (underscore prefix) and frozen. Constructed
    exclusively by ``seed_dispatch_scope``; PR 8's seed driver
    interacts with the scope helper, never with this dataclass
    directly. Frozen to prevent accidental mutation across the
    yield point of the context manager.
    """

    source: Literal["runtime", "seed"]
    fixture_id: str
```

`fixture_id` is `str`, not `str | None`. The framing-time
correction (PR 7 framing §3 + passoff §3.3) is binding: making
it optional broadens the contract for "future flexibility"
prematurely. If a use case for an absent `fixture_id` appears,
that becomes a framing decision.

#### 4.2.3 `_dispatch_context` module-private ContextVar

```python
_dispatch_context: ContextVar[Optional[_DispatchContext]] = \
    ContextVar("forge_bridge.corpus._capture._dispatch_context", default=None)
```

The ContextVar's name (the string passed to its constructor)
includes the full module path for debugging clarity. The
variable name itself is module-private (leading underscore).

#### 4.2.4 `seed_dispatch_scope` public no-yield context manager

```python
@contextmanager
def seed_dispatch_scope(*, fixture_id: str) -> Iterator[None]:
    """Activate seed-dispatch provenance for the current scope.

    Within this context, capture emissions persist
    ``source="seed"`` and the supplied ``fixture_id`` regardless
    of the call-site ``source`` literal. Outside this context,
    the contextvar default (``None``) yields the runtime
    behavior unchanged.

    The context manager yields no public value. ``ContextVar``
    token handling is implementation-internal. If future
    nested-scope introspection becomes a concrete need, that is
    an explicit framing/spec expansion event — never
    accidentally-carried-forward latent API surface (PR 7
    framing §5.2).

    Args:
        fixture_id: REQUIRED. The seed fixture identifier the
            dispatch is operating on. Stored in the contextvar
            payload and persisted on every observation emission
            that occurs while the scope is active.

    Yields:
        ``None``. The caller drives the dispatch through the
        arbitration pipeline; this scope only sets provenance.
    """
    token = _dispatch_context.set(
        _DispatchContext(source="seed", fixture_id=fixture_id)
    )
    try:
        yield
    finally:
        _dispatch_context.reset(token)
```

The `*` keyword-only marker makes `fixture_id` positional-by-
keyword only. This matches the broader `forge_bridge.corpus`
helper convention (every public helper in `_capture.py` uses
keyword-only arguments) and prevents future contributors from
adding positional arguments accidentally.

The body matches framing §9.5 exactly — no embellishment, no
logging, no exception suppression. The scope is mechanically
dumb: set, yield, reset. Exception inside the `with` block
propagates naturally; the `finally` ensures `reset` always
runs.

#### 4.2.5 Resolution path inside `emit_divergence_capture`

The existing helper signature stays unchanged. Internal logic
gains one resolution step at the top of the `try` block:

```python
def emit_divergence_capture(
    *,
    prompt: str,
    registered_tools: list[Any],
    candidate_set_post_reachability: list[Any],
    candidate_set_post_pr14: list[Any],
    narrower_decision: list[Any],
    pr20_condition_met: bool,
    collapse_occurred: bool,
    ambiguity_state: str,
    narrower_latency_ms: float,
    source: str,  # <— UNCHANGED signature; runtime-inert per §4.2 binding
) -> None:
    """[existing docstring carrying §4.2 inert-parameter binding pair
    appended]"""
    try:
        # ── Dispatch-provenance resolution (PR 7 §4.2.5) ─────────
        # The call-site ``source`` literal is structurally
        # authoritative (Property C) and operationally inert. The
        # persisted ``source`` value is contextvar-resolved.
        ctx = _dispatch_context.get()
        if ctx is None:
            resolved_source = "runtime"
            resolved_fixture_id: Optional[str] = None
        else:
            resolved_source = ctx.source
            resolved_fixture_id = ctx.fixture_id

        record = _build_capture_record(
            prompt=prompt,
            registered_tools=registered_tools,
            candidate_set_post_reachability=candidate_set_post_reachability,
            candidate_set_post_pr14=candidate_set_post_pr14,
            narrower_decision=narrower_decision,
            pr20_condition_met=pr20_condition_met,
            collapse_occurred=collapse_occurred,
            ambiguity_state=ambiguity_state,
            narrower_latency_ms=narrower_latency_ms,
            source=resolved_source,  # <— resolved, not call-site
            fixture_id=resolved_fixture_id,  # <— new builder param
            record_kind="observation",  # <— new builder param
        )
        validate_capture_record(record)
        # [rest of writer path unchanged]
```

`_build_capture_record` gains two new keyword-only parameters
(`fixture_id` and `record_kind`). Both are explicit at the
builder boundary — the integration-discipline quartet (carriers
#3–#6) extends naturally: the resolution path is the source of
the two new explicit inputs to the builder. The builder still
does not discover runtime state (carrier #6); the resolution
path discovers it once and passes it explicitly.

The `source` argument the **call site** passes is no longer
referenced after the `ctx` resolution. The variable name is
preserved (no rename to `_unused_source` or `_source_for_lint`)
because:

- the §4.2 binding states the parameter must not be removed.
- a rename would visually undermine Property C: the lint
  matches the keyword `source` literally, and a rename here
  would force a future helper-signature change to keep the lint
  passing — exactly the cleanup-pressure-resistance failure
  mode framing §6 protects against.

The §4.2 binding-statement pair is appended to the helper's
docstring (replacing nothing; extending the existing PR 3
docstring).

#### 4.2.6 `_persist_expectation_record(record: dict) -> None` private helper

```python
def _persist_expectation_record(record: dict) -> None:
    """Persist a single expectation record to the corpus.

    PR 7 NON-PARTICIPATION GUARD (verbatim, load-bearing):

      The narrow expectation persistence helper does not
      participate in provenance resolution. It consults no
      dispatch context, performs no source rewriting, and
      carries no observational semantics.

    PR 7 AUTHORITY GUARD (load-bearing):

      ``_persist_expectation_record`` persists authored
      expectation records only. ``validate_capture_record``
      answers "is this structurally valid?"; this helper must
      additionally answer "is this the correct truth class for
      this authority surface?". Without an explicit
      ``record_kind == "expectation"`` pre-check, the helper
      would collapse authored expectation persistence and
      generic persistence routing — eroding the three-authority-
      surface partitioning Gate 2 framing establishes.

    This helper is corpus-internal. It is consumed by PR 8's
    ``emit_seed_expectation`` exclusively. PR 7 does not invoke
    it from any production call site in its own delta.

    Sequencing of validation (load-bearing):

      1. **Authority pre-check.** ``record["record_kind"] ==
         "expectation"``. Failure raises ``SchemaValidationError``
         with an authority-oriented message (not value-oriented),
         naming the helper and the truth-class violation
         explicitly. The pre-check fires BEFORE generic
         validation so a well-formed observation record passed
         to this helper is rejected at the authority boundary,
         not at a downstream structural boundary.
      2. **Generic schema validation.**
         ``validate_capture_record(record)``.
      3. **Atomic-append persistence.** Same discipline as
         ``emit_divergence_capture`` (single ``file.write(...)``
         per emission; bundled header on file creation;
         failure-invisibility per I-6).

    The helper does NOT call ``_dispatch_context.get()``. The
    helper does NOT inspect or mutate the ``source`` field on
    the record (the framing locks expectation records as having
    no ``source`` field — see §9.7). Any future modification
    that introduces dispatch-context consultation here violates
    the non-participation guard and is rejected at the spec
    layer.

    Args:
        record: A pre-built expectation record dict. PR 8's
            ``emit_seed_expectation`` is responsible for
            building the record; this helper handles persistence
            only. The record MUST carry
            ``record_kind="expectation"``; the helper rejects
            records that don't via the authority pre-check
            (``SchemaValidationError`` with authority-oriented
            error text).

    Returns:
        ``None``. Failure-invisibility per I-6: any exception
        from the authority pre-check, schema validation,
        serialization, or filesystem is caught and logged at
        WARNING; nothing propagates.
    """
    try:
        # ── Authority pre-check (PR 7 §4.2.6) ─────────────────────
        # The truth-class boundary. This helper persists authored
        # expectation records only. The pre-check answers the
        # authority question ("correct truth class for this
        # surface?"); ``validate_capture_record`` below answers the
        # structural question ("structurally valid?"). Both are
        # required; the schema validator does not enforce the
        # authority partition because both ``observation`` and
        # ``expectation`` are valid ``record_kind`` values.
        record_kind = (
            record.get("record_kind") if isinstance(record, dict) else None
        )
        if record_kind != "expectation":
            raise SchemaValidationError(
                "_persist_expectation_record persists authored "
                "expectation records only; "
                f"received record_kind={record_kind!r}"
            )

        validate_capture_record(record)

        corpus_dir = _resolve_corpus_dir()
        corpus_dir.mkdir(parents=True, exist_ok=True)

        date_part = record["captured_at"][:10]
        path = corpus_dir / f"capture-{date_part}.jsonl"

        needs_header = not (path.exists() and path.stat().st_size > 0)

        record_line = _serialize_line(record)
        if needs_header:
            header_line = _serialize_line(_make_header(record["captured_at"]))
            payload = header_line + record_line
        else:
            payload = record_line

        with path.open("a", encoding="utf-8") as f:
            f.write(payload)
            f.flush()

    except Exception as exc:  # noqa: BLE001 — I-6 failure invisibility
        try:
            logger.warning(
                "expectation persistence failed: error=%s: %s",
                type(exc).__name__,
                exc,
            )
        except Exception:  # noqa: BLE001
            pass

    return None
```

The helper structurally mirrors `emit_divergence_capture`'s
writer path — same `_resolve_corpus_dir`, same date-partitioned
file, same header-bundle-on-first-write, same single-write
discipline, same I-6 failure-invisibility wrapper. **It does not
mirror the resolution path.** That asymmetry is the protection
the non-participation guard codifies.

The helper is a sibling of `emit_divergence_capture`, not a
subordinate. Refactoring them into a shared internal writer (a
common cleanup-pressure target) is rejected per framing §6 class
member #1 (helper duplication).

### 4.3 `forge_bridge/corpus/_schema.py` (modified)

Two additions:

#### 4.3.1 `record_kind` literal in the record shape

The schema's record validator gains a `record_kind` field check.
The current `validate_capture_record` shape (at PR 6 close)
accepts a record dict and raises `SchemaValidationError` on
shape violations. PR 7 extends:

```python
_KNOWN_RECORD_KINDS: Final[frozenset[str]] = frozenset({"observation", "expectation"})

def validate_capture_record(record: dict) -> None:
    """[existing docstring extended with record_kind contract]"""
    # ... existing field validation ...

    record_kind = record.get("record_kind")
    if record_kind not in _KNOWN_RECORD_KINDS:
        raise SchemaValidationError(
            f"record_kind={record_kind!r} not in known values "
            f"{sorted(_KNOWN_RECORD_KINDS)}"
        )

    if record_kind == "observation":
        from forge_bridge.corpus._sources import KNOWN_SOURCE_VALUES
        source = record.get("source")
        if source not in KNOWN_SOURCE_VALUES:
            raise SchemaValidationError(
                f"observation record source={source!r} not in known values "
                f"{sorted(KNOWN_SOURCE_VALUES)}"
            )
    elif record_kind == "expectation":
        if "source" in record:
            raise SchemaValidationError(
                "expectation record must not carry a 'source' field; "
                f"found source={record['source']!r}"
            )
```

The import of `KNOWN_SOURCE_VALUES` is **inside the function**,
not at module top-level. The reason is **not** circular-import
avoidance — `_sources.py` is leaf governance (per §4.1 it
imports nothing from `forge_bridge.corpus.*`), so no cycle is
possible at any import order. The reason is module-top-import
minimalism: keeping `_schema.py`'s top-level import surface
unchanged from PR 6 close preserves narrower load-time coupling,
keeps the ontology dependency visible at its point of use
(inside the validator branch that consumes it), and avoids
expanding the module-top surface for a constant that only one
function references. If a second consumer of `KNOWN_SOURCE_VALUES`
appears inside `_schema.py` in a later phase, the import can be
promoted to module-top then; until then, function-local is the
correct shape.

#### 4.3.2 `_KNOWN_RECORD_KINDS` constant

The constant is defined at module level (per the snippet above)
but is **not** exported from `_schema.py`'s namespace as a
public surface. It is consumed by the validator only. Tests
that need to enumerate record kinds construct the set
explicitly or import the constant via its private name — the
constant's job is to be the validator's single source of truth,
not a public API.

`_KNOWN_RECORD_KINDS` lives in `_schema.py` (not `_sources.py`)
because it governs the schema's structural ontology, distinct
from the persistence-layer source-class governance that
`_sources.py` owns. Per Gate 2 framing §9.2: `record_kind` is
governed structurally (new values imply a new authority
surface); `KNOWN_SOURCE_VALUES` is governed persistence-side
(new values imply a new provenance class). The two governance
surfaces are physically separated to make the distinction
visible.

### 4.4 `forge_bridge/corpus/reader.py` (modified)

Two additions:

#### 4.4.1 Module docstring extension

The carriers + the §5.5 binding-statement pair land at the top
of the module docstring (before the existing PR 3 corruption-
locality contract paragraph). The existing PR 3 carriers stay
untouched.

#### 4.4.2 Read-time legacy-record synthesis

The `read_capture_file` function gains a synthesis layer
between `json.loads` and `validate_capture_record` for
non-header records:

```python
# Inside read_capture_file, in the per-line loop:

try:
    record = json.loads(line_text)
except json.JSONDecodeError as exc:
    # [existing skip-with-warning behavior unchanged]
    continue

# ── Legacy-record synthesis (PR 7 §5.5) ─────────────────────────
# Records persisted before PR 7 lack the ``record_kind`` field.
# The reader synthesizes ``record_kind="observation"`` for any
# record missing the field. The synthesis applies to the
# in-memory dict only; the source line is never rewritten.
#
# Carrier (verbatim):
#
#   ``record_kind`` synthesis exists solely for backward
#   compatibility with records that predate PR 7. Writers
#   introduced by PR 7 must always emit explicit ``record_kind``
#   values.
#
#   Legacy records may be interpreted through synthesized
#   defaults at read time but are not rewritten or normalized in
#   place by the reader.
if isinstance(record, dict) and "record_kind" not in record:
    record["record_kind"] = "observation"

try:
    validate_capture_record(record)
except SchemaValidationError as exc:
    # [existing skip-with-warning behavior unchanged]
    continue

yield record
```

The synthesis mutates the **in-memory** dict (`record`) only.
The `raw_bytes` from the file is never modified, never re-
written, never normalized. Every read of a legacy file produces
the same in-memory result and leaves the file byte-identical
(risk #3 contract; test 5 in §5).

The header validation (the schema-version block at the top of
`read_capture_file`) is **unchanged**. PR 7 does not touch
header semantics. Legacy files were written under the same
`SCHEMA_VERSION` PR 7 ships with — the schema-version field is
not bumped (per §2 out-of-scope #8).

### 4.5 `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` extension

One entry added:

```python
_ALLOWLIST: frozenset[str] = frozenset({
    # [existing entries from PR 3, PR 4, PR 5, PR 6...]
    "forge_bridge/corpus/_sources.py",  # <— PR 7
})
```

No other modifications to the discipline test. The Layer 1
allowlist's job is to admit specific files into the corpus
package; PR 7 adds one file (`_sources.py`) and admits it. The
discipline grep itself is unchanged.

### 4.6 New test modules

Six test modules, all under `tests/corpus/`:

| File | Risk addressed | Test count (est.) |
|---|---|---|
| `test_pr7_known_source_values.py` | structural ontology governance | 3 |
| `test_pr7_dispatch_context.py` | gate separation (#1, #2) | 6 |
| `test_pr7_record_kind_schema.py` | structural ontology governance (#4) | 4 |
| `test_pr7_reader_validation.py` | structural ontology governance | 5 |
| `test_pr7_legacy_record_synthesis.py` | archaeology integrity (#3) | 4 |
| `test_pr7_expectation_persistence.py` | authority partitioning (#5) | 5 |

Estimated total: **27 new tests**. Specific test functions are
enumerated in §5.

Each test module's top-level docstring carries carriers #1–#14
(slim form — citations to `_capture.py` for the full text). PR
7-local binding pairs are NOT carried in test module docstrings
(they are scope-local to their respective production module
docstrings). Test modules cite them by location.

---

## 5. Test plan

### 5.1 Test inventory (27 tests)

#### `test_pr7_known_source_values.py` (3 tests)

1. `test_constant_is_frozenset` — asserts
   `KNOWN_SOURCE_VALUES` is exactly `frozenset({"runtime", "seed"})`
   and is `Final`. Pins the value; future renames or value-
   set changes surface as a test failure (forcing framing-
   level review).
2. `test_governance_docstring_present` — asserts the module
   docstring contains the literal "PROTECTED PROPERTY (truth)"
   and "MECHANISM" structural markers. The protected-property
   framing is the truth-vs-mechanism discipline (PR 6 close
   §1.3) operationalized for `_sources.py`.
3. `test_no_corpus_imports` — asserts `_sources.py` imports
   nothing from `forge_bridge.corpus.*`. Leaf governance
   constants must remain leaves.

#### `test_pr7_dispatch_context.py` (6 tests)

1. `test_scope_inactive_persists_runtime` — emits a capture
   record outside any active scope; reads the JSONL line
   back; asserts persisted `source == "runtime"` and no
   `fixture_id` key (or `fixture_id is None`).
2. `test_scope_active_persists_seed_and_fixture_id` — emits
   a capture record inside a `seed_dispatch_scope(fixture_id="fix-001")`;
   asserts persisted `source == "seed"` and
   `fixture_id == "fix-001"`.
3. `test_call_site_source_value_is_inert` — emits four
   capture records: (a) outside scope with
   `source="runtime"`, (b) outside scope with
   `source="garbage"`, (c) inside scope with
   `source="runtime"`, (d) inside scope with
   `source="garbage"`. Asserts (a) and (b) both persist
   `source="runtime"`; (c) and (d) both persist
   `source="seed"`. The call-site value is mechanically
   ignored. **This test is the §4.2 binding pair's
   enforcement.**
4. `test_scope_resets_on_exception` — opens a scope, raises
   inside the `with` block, catches the exception, then
   emits a capture record. Asserts the post-block emit
   persists `source="runtime"` (the contextvar reset
   correctly).
5. `test_nested_scope_inner_overrides` — opens a scope with
   `fixture_id="outer"`, then a nested scope with
   `fixture_id="inner"`, emits a record inside the inner
   scope. Asserts persisted `fixture_id="inner"`. After the
   inner scope exits, emits another record inside the outer
   scope; asserts persisted `fixture_id="outer"`. Validates
   ContextVar's stack semantics work as expected.
6. `test_dispatch_context_dataclass_is_frozen` — attempts
   `_DispatchContext(source="seed", fixture_id="x").source = "runtime"`;
   asserts `FrozenInstanceError` is raised. Locks the
   frozen-dataclass contract structurally.

#### `test_pr7_record_kind_schema.py` (4 tests)

1. `test_observation_record_validates` — constructs a
   minimum-shape observation record with
   `record_kind="observation"` and `source="runtime"`;
   asserts `validate_capture_record` does not raise.
2. `test_expectation_record_validates` — constructs a
   minimum-shape expectation record with
   `record_kind="expectation"` and no `source` field;
   asserts `validate_capture_record` does not raise.
3. `test_unknown_record_kind_rejected` — for each of
   `[None, "", "obs", "expect", "unknown", 0]` set as
   `record_kind`, asserts `validate_capture_record` raises
   `SchemaValidationError`.
4. `test_observation_record_unknown_source_rejected` —
   constructs an observation record with `source="cosmic"`;
   asserts `SchemaValidationError`.

#### `test_pr7_reader_validation.py` (5 tests)

1. `test_reader_accepts_observation_record` — writes a
   header + one observation record to a temp file; reads;
   asserts one record yielded with `record_kind="observation"`.
2. `test_reader_accepts_expectation_record` — writes a
   header + one expectation record; reads; asserts one
   record yielded with `record_kind="expectation"` and no
   `source` field.
3. `test_reader_skips_unknown_record_kind` — writes a
   header + one record with `record_kind="bogus"`; reads;
   asserts zero records yielded; asserts WARNING log fired
   with the schema-validation failure prefix.
4. `test_reader_skips_observation_with_unknown_source` —
   writes a header + one observation record with
   `source="phantom"`; reads; asserts zero records yielded;
   asserts WARNING log fired.
5. `test_reader_skips_expectation_with_source_field` —
   writes a header + one expectation record that
   inadvertently carries `source="runtime"`; reads; asserts
   zero records yielded; asserts WARNING log fired.

#### `test_pr7_legacy_record_synthesis.py` (4 tests)

1. `test_legacy_record_synthesized_as_observation` —
   constructs a JSONL line representing a pre-PR-7 record
   (no `record_kind` field, `source="runtime"`); writes it
   under a valid header; reads; asserts the yielded record
   carries `record_kind="observation"` (synthesized).
2. `test_legacy_file_unchanged_after_read` — writes a
   legacy-format file; computes SHA-256 of bytes; calls
   `list(read_capture_file(path))`; computes SHA-256 again;
   asserts hashes are equal. **This is the §5.5 binding
   pair's enforcement.** Run twice (full read + partial-
   read-via-iterator-takedown) to cover both consumption
   shapes.
3. `test_legacy_record_with_unknown_source_still_skipped` —
   writes a legacy record (no `record_kind`) with
   `source="phantom"`; reads; asserts zero records yielded
   (synthesis assigns `record_kind="observation"`, then
   validator rejects on unknown source). Confirms synthesis
   doesn't bypass validation.
4. `test_mixed_legacy_and_contemporary_records` — writes a
   header + one legacy record + one contemporary record
   (with `record_kind="observation"`) + one contemporary
   record with `record_kind="expectation"`; reads; asserts
   three records yielded; asserts the legacy one carries
   the synthesized `record_kind="observation"`; asserts the
   other two carry their explicit `record_kind` values.

#### `test_pr7_expectation_persistence.py` (5 tests)

1. `test_helper_persists_expectation_record` — invokes
   `_persist_expectation_record` with a valid expectation
   record; reads the resulting JSONL file; asserts the
   record round-trips with `record_kind="expectation"` and
   no `source` field.
2. `test_helper_does_not_consult_dispatch_context` —
   invokes `_persist_expectation_record` (a) outside any
   scope and (b) inside a `seed_dispatch_scope(fixture_id="...")`;
   asserts the persisted record content is byte-identical
   between the two invocations. **This is the Step 8 non-
   participation guard's enforcement** (risk #5).
3. `test_helper_authority_pre_check_rejects_missing_record_kind` —
   invokes `_persist_expectation_record` with a record dict
   missing `record_kind`; asserts the function returns `None`
   (failure-invisibility) and asserts a WARNING log fired
   carrying the **authority-oriented** error text:
   `"_persist_expectation_record persists authored expectation
   records only; received record_kind=None"`. Asserts no
   record was written to disk (no file created or no new line
   appended). The pre-check fires here, not the schema
   validator — the test asserts the authority boundary
   activates BEFORE the schema validator, which is what
   protects authority partitioning when `record_kind` is
   absent.
4. `test_helper_authority_pre_check_rejects_observation_record` —
   constructs a **well-formed** observation record (carrying
   `record_kind="observation"`, `source="runtime"`, and all
   other required observation fields, so it would pass
   `validate_capture_record` if called directly); invokes
   `_persist_expectation_record(record)`; asserts the function
   returns `None`; asserts a WARNING log fired carrying the
   authority-oriented error text:
   `"_persist_expectation_record persists authored expectation
   records only; received record_kind='observation'"`. Asserts
   no record was written to disk. **This is the authority-
   class boundary's enforcement** — the test specifically
   targets the case where the schema would accept the record
   but the authority pre-check must reject it. Without this
   test, a future PR could remove the pre-check without
   regressing any test.
5. `test_helper_atomic_append` — invokes
   `_persist_expectation_record` three times against the
   same date-partition file; reads; asserts three records
   yielded; asserts the file has exactly one header line +
   three record lines (no orphan headers, no duplicate
   headers). Validates the bundled-header-on-first-write
   discipline applies identically to expectation
   persistence.

### 5.2 Regression contract

**RC-1: Layer 3 lint passes unchanged.**
`tests/corpus/test_pr6_visual_asymmetry.py` runs unchanged
against the modified `_capture.py`. Property C's literal
check passes because call sites are unchanged. Properties A,
B, D pass because the helper signature is unchanged at the
external boundary. **This is the regression checkpoint at
the end of §6 step 5 and again at PR 7 close.**

**RC-2: Existing observation behavior preserved.**
Records persisted via the modified `emit_divergence_capture`
with no scope active match Gate 1's record shape modulo the
new `record_kind="observation"` field. Specifically: PR 4 and
PR 5 integration tests (`tests/console/test_chat_handler.py`
and the chain-step integration tests) pass unchanged under
all four capture states (gate-on/off × scope-active/inactive,
where scope-active is structurally the same as scope-inactive
when those tests do not open a scope).

**RC-3: PR 3 discipline intact.**
`test_pr3_discipline.py` passes with the `_sources.py` entry
added to `_ALLOWLIST`. No other discipline checks regress.

**RC-4: Reader corruption-locality preserved.**
PR 3's reader contract — malformed records skip with WARNING,
never abort iteration — survives the validation extension.
The new validation rejection paths (record_kind, source)
flow through the existing `SchemaValidationError` skip-with-
WARNING branch.

### 5.3 Test count delta

- **PR 6 close baseline:** 148 corpus tests pass in forge env;
  142 in forge-bridge env (per PR 6 spec §7 step 11).
- **PR 7 delta:** +27 new tests (this spec §5.1) + 0
  modifications to existing tests (the `_ALLOWLIST` entry
  doesn't add a test, it gates the existing discipline check).
- **PR 7 close target:** 175 corpus tests pass in forge env;
  169 in forge-bridge env. Same 4 pre-existing failures
  (stdio_cleanliness ×2, typer_entrypoint ×2). Chat-handler
  tests (`tests/console/test_chat_handler.py`) — 50/50
  unchanged. PR 4 + PR 5 integration tests — unchanged.

### 5.4 What PR 7 deliberately does NOT test

- **PR 8's seed driver.** No test exercises the seed driver
  loop; PR 7 ships the seam, not the driver. Tests of the
  driver land with PR 8.
- **Comparator partition logic** (Gate 4). PR 7 lands the
  `record_kind` discriminator and the `source` ontology;
  whether comparator code partitions records correctly
  against either is Gate 4's domain. Out of scope.
- **Property C through the lint-self meta-test.** PR 6's
  meta-test (`test_lint_imports_no_corpus_modules`) runs
  unchanged; PR 7 adds no analogous meta-test for
  `_sources.py` because `_sources.py`'s purity is structural
  (it has no imports from `forge_bridge.corpus.*`) and
  that's tested by `test_no_corpus_imports` in §5.1.
- **Carrier-text byte-identicality across the nineteen
  sentences.** The flattening pipeline (introduced in PR 4)
  validates carrier text mechanically across the corpus.
  PR 7 does not duplicate that coverage.

---

## 6. Implementation sequence

The framing §7 cadence-matches-work-depth rule applies, with
one explicit elevation:

- **Light-touch review** for plumbing — `_sources.py`
  governance constant, `_DispatchContext` dataclass +
  ContextVar declaration, `seed_dispatch_scope` body, schema
  validator extension, reader synthesis layer, `_ALLOWLIST`
  entry.
- **Full three-round review** for **Step 5** (the resolution
  path inside `emit_divergence_capture`). Even though PR 7
  overall is plumbing-shaped, Step 5 is the architectural
  center of PR 7: it operationalizes carrier #14, the
  declared-vs-resolved provenance separation, and the inert-
  parameter doctrine. The cadence-matches-work-depth rule
  applies locally — Step 5 is not routine plumbing.

Eight steps. Each step changes one authority or ontology
boundary cleanly.

### Step 1 — Ontology constant

Create `forge_bridge/corpus/_sources.py` per §4.1:
- `KNOWN_SOURCE_VALUES = frozenset({"runtime", "seed"})`
- The full module docstring (carriers #1–#14 + binding
  framing clarification + protected-property framing for
  `KNOWN_SOURCE_VALUES`).
- `from __future__ import annotations` + `from typing import
  Final` only — no other imports.

**Light-touch review.** Verification: `python -c "from
forge_bridge.corpus._sources import KNOWN_SOURCE_VALUES;
print(sorted(KNOWN_SOURCE_VALUES))"` prints
`['runtime', 'seed']`.

### Step 2 — Layer 1 admission

Extend `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` per
§4.5. The Layer 1 update lands in the same commit boundary as
the file it admits. Per the framing's principle of one-
authority-or-ontology-boundary-per-step: the Layer 1 admission
boundary moves here.

**Light-touch review.** Verification: `pytest
tests/corpus/test_pr3_discipline.py` passes against the
modified allowlist (the discipline check no longer flags
`_sources.py` as unauthorized).

### Step 3 — Dispatch substrate

Add to `_capture.py`:
- Imports for `contextlib`, `contextvars`, `dataclasses`,
  `typing.Iterator`, `typing.Literal`, `typing.Optional`,
  and `KNOWN_SOURCE_VALUES`.
- `_DispatchContext` private frozen dataclass per §4.2.2.
- `_dispatch_context` ContextVar per §4.2.3.

No behavior change yet. The substrate is inert until Step 4
introduces the scope helper and Step 5 wires the resolution
path. Step 3's tests:

- `test_dispatch_context_dataclass_is_frozen` (asserts
  `FrozenInstanceError` on attribute assignment).
- (Other `_dispatch_context.py` tests gated until Step 4.)

**Light-touch review.** Verification: `pytest
tests/corpus/test_pr7_dispatch_context.py::test_dispatch_context_dataclass_is_frozen`
passes; the contextvar can be imported.

### Step 4 — Scope surface

Add `seed_dispatch_scope` public context manager per §4.2.4 to
`_capture.py`. Tests for scope-active / scope-inactive /
exception-cleanup pass against the substrate. Resolution path
is not yet wired (Step 5) — Step 4's tests assert the
contextvar's value transitions only:

- `test_scope_inactive_persists_runtime` — gated; runs end-to-
  end after Step 5 wires the persistence.
- `test_scope_resets_on_exception` — runs at Step 4 against
  the contextvar's post-block value (`_dispatch_context.get() is None`),
  not against persisted records.
- `test_nested_scope_inner_overrides` — same (asserts
  contextvar transitions, not persistence).

**Light-touch review.** Verification: `pytest
tests/corpus/test_pr7_dispatch_context.py -k 'scope_resets or
nested_scope'` passes.

### Step 5 — Provenance resolution **(FULL THREE-ROUND REVIEW)**

This is the architectural center of PR 7. Wire the resolution
path inside `emit_divergence_capture` per §4.2.5:

- Read `_dispatch_context.get()` at the top of the `try`
  block.
- Compute `resolved_source` and `resolved_fixture_id`.
- Pass both to `_build_capture_record` as new keyword-only
  arguments.
- Append the §4.2 binding-statement pair to
  `emit_divergence_capture`'s docstring.
- Update `_capture.py`'s module docstring with the inherited
  carriers + binding framing clarification + the §4.2 pair.

`_build_capture_record` gains two new keyword-only parameters
(`fixture_id`, `record_kind`). `_build_capture_record` is the
builder; it does not discover state (carrier #6); the resolution
path passes state explicitly (carrier #3).

**Why Step 5 receives full review depth:** Step 5 is the only
place in PR 7 that can accidentally collapse:
- structural declaration (the call-site `source="runtime"`
  literal),
- and operational provenance (the persisted `source` value).

A single line of code that consults the call-site `source`
parameter at this layer would re-couple the two. The §4.2
binding-statement pair is the carrier protecting against this;
the test `test_call_site_source_value_is_inert` is the
mechanical assertion.

**Step 5 regression checkpoint (immediate, mandatory):**
After Step 5 lands, run `pytest tests/corpus/test_pr6_visual_asymmetry.py`
unchanged. The Layer 3 lint must pass against the modified
`_capture.py`. If it fails, Step 5 has accidentally collapsed
Property C's structural assertion; revert and re-converge
before proceeding.

This regression checkpoint is the most important moment in
PR 7's implementation. It proves Property C remains
structurally intact while provenance semantics evolve
underneath it.

**Full three-round review.** Verification:
- Step 5 regression checkpoint passes.
- `pytest tests/corpus/test_pr7_dispatch_context.py` passes
  (full file: scope-active, scope-inactive, inert-call-site,
  exception-reset, nested-scope, frozen-dataclass).

### Step 6 — Schema emission

Add to `_capture.py`:
- `record_kind="observation"` passed to `_build_capture_record`
  in the resolution path (§4.2.5). Already present from Step 5.

Add to `_schema.py`:
- `_KNOWN_RECORD_KINDS` constant per §4.3.2.
- `validate_capture_record` extension per §4.3.1 — the
  `record_kind` membership check and the
  observation-source-membership / expectation-source-absence
  branch.

The function-local import of `KNOWN_SOURCE_VALUES` lands here
(per §4.3.1 rationale). Module-level imports in `_schema.py`
remain unchanged from PR 6 close.

`_build_capture_record` gains `record_kind` and `fixture_id`
parameters in its signature. Both are keyword-only. Tests:

- `test_pr7_record_kind_schema.py` (4 tests) runs against the
  extended validator.

**Light-touch review.** Verification: `pytest
tests/corpus/test_pr7_record_kind_schema.py` passes; `pytest
tests/corpus/test_pr7_dispatch_context.py` passes (records
emitted via `emit_divergence_capture` now carry
`record_kind="observation"`).

### Step 7 — Reader interpretation

Modify `forge_bridge/corpus/reader.py` per §4.4:
- Module docstring extension (carriers #1–#14 + §5.5
  legacy-synthesis pair).
- Read-time legacy-record synthesis between `json.loads` and
  `validate_capture_record` per §4.4.2.

The synthesis mutates the in-memory dict only. The
`raw_bytes` from the file is never modified.

Tests:
- `test_pr7_reader_validation.py` (5 tests).
- `test_pr7_legacy_record_synthesis.py` (4 tests, including
  the byte-identicality test that enforces §5.5 mechanically).

**Light-touch review.** Verification: `pytest
tests/corpus/test_pr7_reader_validation.py
tests/corpus/test_pr7_legacy_record_synthesis.py` passes.

### Step 8 — Expectation persistence surface

Add `_persist_expectation_record(record: dict) -> None`
private helper to `_capture.py` per §4.2.6. The helper:

- Runs the **authority pre-check** —
  `record["record_kind"] == "expectation"` — BEFORE generic
  schema validation. Failure raises `SchemaValidationError`
  with authority-oriented error text (not value-oriented).
- Validates the record via `validate_capture_record`.
- Resolves the corpus directory (`_resolve_corpus_dir`) —
  shared with the observation path.
- Follows the same atomic-append discipline (single
  `file.write(...)`; bundled header on first write).
- Wraps everything in I-6 failure-invisibility.

**Step 8 explicit non-participation guard (verbatim, load-
bearing — lands in `_persist_expectation_record`'s docstring):**

> **The narrow expectation persistence helper does not
> participate in provenance resolution. It consults no
> dispatch context, performs no source rewriting, and
> carries no observational semantics.**

This sentence protects authority partitioning directly. Without
it, the expectation persistence helper becomes vulnerable to
"consistency reuse" pressure — a future cleanup PR could:

- propose consulting dispatch context "for symmetry with the
  observation helper,"
- propose copying source semantics "since both helpers persist
  to the same file format,"
- propose inheriting provenance rewriting behavior "to share
  the resolution logic,"
- or propose partially collapsing authored expectation into
  observational semantics "since they look similar."

Each of these proposals would erode authority partitioning. The
non-participation guard names the protection explicitly so any
future cleanup PR has to argue against the guard (a framing-
level question), not refactor through it (a cleanup-PR
question).

PR 7 ships the helper but does not invoke it from any
production call site. The single-call-site invocation lands in
PR 8 (`emit_seed_expectation` calls
`_persist_expectation_record`). Tests:

- `test_pr7_expectation_persistence.py` (5 tests). Three are
  authority-boundary load-bearing:
  - `test_helper_does_not_consult_dispatch_context` enforces
    the non-participation guard mechanically (risk #5).
  - `test_helper_authority_pre_check_rejects_missing_record_kind`
    enforces the authority pre-check at the missing-field
    boundary.
  - `test_helper_authority_pre_check_rejects_observation_record`
    enforces the authority pre-check against a well-formed
    observation record (the schema-would-accept case the
    pre-check exists to reject).

**Light-touch review** for the writer-path mechanics
(structurally identical to `emit_divergence_capture`'s
writer). **Full three-round review** for the non-participation
guard's docstring text + the authority guard's docstring text +
the authority pre-check sequencing — both binding statements
are load-bearing and must travel verbatim, and the pre-check's
position BEFORE generic schema validation is the structural
protection against authority-class collapse.

Verification: `pytest tests/corpus/test_pr7_expectation_persistence.py`
passes.

### Final verification — full suite

Run the full corpus + console test suites after Step 8 lands.
Confirm:

- **175 corpus tests pass in forge env** (148 baseline + 27
  new file IDs).
- **169 corpus tests pass in forge-bridge env** (142 baseline
  + 27 new file IDs).
- Same 4 pre-existing failures (stdio_cleanliness ×2,
  typer_entrypoint ×2).
- Chat-handler tests (`tests/console/test_chat_handler.py`)
  — 50/50 unchanged.
- PR 4 + PR 5 integration tests under all four capture states
  pass unchanged.
- Regression checkpoint RC-1 (Layer 3 lint passes unchanged
  against the modified `_capture.py`).

### Natural pause points (per framing §7 pacing clause)

- **Between Step 4 and Step 5** — verifies the dispatch
  substrate + scope surface in isolation before the
  resolution path layers on top. A small probe (`python -c
  "from forge_bridge.corpus._capture import seed_dispatch_scope,
  _dispatch_context; ..."`) confirms the contextvar transitions
  before the resolution path is invoked.
- **Immediately after Step 5** — the regression checkpoint
  (`pytest tests/corpus/test_pr6_visual_asymmetry.py`) is a
  natural pause. If it passes, Step 5 successfully kept gate
  separation intact and the work depth payoff is realized; if
  it fails, the team converges before any further plumbing
  steps stack on top.
- **Between Step 6 and Step 7** — verifies the schema
  validation extension passes against contemporary records
  before legacy synthesis adds another interpretation layer.
- **Between Step 7 and Step 8** — verifies the reader
  validation extension is operational before the new
  expectation persistence helper introduces records to read.

### What about an inter-step polish step?

PR 4, PR 5, and PR 6 all reserved a "polish step (no-op for
this PR)" slot. PR 7 surfaces no analogous polish during spec
drafting and does not reserve one. The eight steps above are
the implementation sequence in full.

---

## 7. Phase-end conditions for PR 7

| Trigger | Response |
|---|---|
| All 27 new tests pass + Layer 3 lint passes unchanged + PR 4 + PR 5 integration tests pass under all four capture states + the nineteen sentences in §0 travel verbatim into the relevant docstrings + commit message body + no implementation step shortcuts or weakens any member of the constructs-resistant-to-cleanup-pressure class (framing §6) | PR 7 closes; PR 8 framing/spec drafting begins. |
| `test_pr6_visual_asymmetry.py` regresses against the modified `_capture.py` | Hard CI failure; gate separation has been violated. Property C's literal assertion no longer holds at one or more call sites. The aggregated failure message names which Properties/Rejections fired; review surfaces the framing-level violation and routes the offender to (a) revert the offending change, OR (b) framing amendment if the change is genuinely needed. |
| `test_call_site_source_value_is_inert` regresses on a future PR | Hard CI failure; the §4.2 binding pair has been violated. Future PR proposed coupling the persisted `source` value to the call-site `source` literal. Reject at CI; review surfaces §4.2 binding statement verbatim. |
| `test_legacy_file_unchanged_after_read` regresses on a future PR | Hard CI failure; the §5.5 binding pair has been violated. The reader has acquired a write-back mutation path. Reject at CI; review surfaces §5.5 binding statement verbatim. |
| `test_helper_does_not_consult_dispatch_context` regresses on a future PR | Hard CI failure; the Step 8 non-participation guard has been violated. `_persist_expectation_record` has acquired observation semantics. Reject at CI; review surfaces the non-participation guard verbatim. |
| `test_helper_authority_pre_check_rejects_observation_record` regresses on a future PR | Hard CI failure; the Step 8 authority guard has been violated. `_persist_expectation_record` no longer rejects well-formed observation records at the authority boundary — meaning the helper now silently routes generic capture records into the expectation persistence path, collapsing authored expectation into generic persistence. Reject at CI; review surfaces the §4.2.6 authority guard verbatim. The pre-check's position BEFORE generic schema validation is part of the contract; a regression that moves the check after the schema validator (or removes it entirely) fails this row. |
| A future PR proposes to remove the call-site `source="runtime"` literal at any emit call site | Rejected at the spec layer per §2 out-of-scope #3 + §4.2 binding pair + framing §6 class member #3. The literal is structurally authoritative (Property C); removing it erodes carrier #14's call-site-vs-persistence distinction. |
| A future PR proposes to remove `_persist_expectation_record`'s authority pre-check ("the schema validator already covers it") | Rejected at the spec layer per §4.2.6 authority guard. The schema validator answers "structurally valid?" and accepts both `observation` and `expectation` record kinds; it does NOT enforce truth-class authority partitioning. Removing the pre-check would silently collapse authored expectation persistence into generic persistence routing. Reviewer surfaces the authority guard verbatim. |
| A future PR proposes to surface a nested-scope token from `seed_dispatch_scope` | Rejected at the spec layer per framing §5.2 + §2 out-of-scope #6. Latent API surface is not accidentally carried forward; if a concrete nested-scope use case appears, it becomes a framing-level expansion event. |
| A future PR proposes to promote `seed_dispatch_scope`, `_persist_expectation_record`, or `_DispatchContext` to `forge_bridge.__all__` | Rejected at the spec layer per §2 out-of-scope #7 + framing §8.2. Public export = authority-surface expansion = explicit framing review. The decision can be revisited at PR 8 framing if the seed-driver consumer establishes external need; the question never lands inside an unrelated cleanup PR. |
| A future PR proposes a one-time migration script over the existing capture corpus to backfill `record_kind` | Rejected at the spec layer per §2 out-of-scope #5 + framing §5.5 + §4.4.2. Reader synthesis is read-time-only; legacy records are interpreted, not normalized. The temporal asymmetry is itself preserved as a property. |
| A future PR proposes to bump `SCHEMA_VERSION` to mark the `record_kind` introduction | Rejected at the spec layer per §2 out-of-scope #8. The `record_kind` field is additive and backward-tolerant via synthesis. A version bump would force operator-visible upgrade ritual that PR 7's plumbing shape does not warrant. The decision can be revisited if a future schema change introduces a backward-incompatible delta; this one does not. |
| A future PR proposes to fold `_persist_expectation_record` and `emit_divergence_capture` into a shared internal writer | Rejected at the spec layer per framing §6 class member #1 + §4.2.6. Helper duplication is a named architectural commitment; the duplication smears authority surfaces (observation and authored expectation are distinct truth classes). The shared writer would require dispatch-context consultation in the expectation path or `record_kind` branching in the writer path; both erode authority partitioning. |
| A future PR proposes to add a third `record_kind` value | Rejected at the spec layer per Gate 2 framing §9.2 + framing §4.4. `record_kind` is governed structurally — new values imply a new authority surface, not merely a new provenance class. Adding a third value requires the corresponding helper, signature, and truth claim — all framing-level decisions. |
| A future PR proposes to add a third `KNOWN_SOURCE_VALUES` entry | Rejected at the cleanup-PR layer; routed to framing review. The §4.1 protected-property framing requires synchronous update of: `KNOWN_SOURCE_VALUES`, reader validation, the contextvar resolution path, and the Gate 4 comparator's partition logic. Mergeability is contingent on all four updating in lockstep. A cleanup PR that touches only `KNOWN_SOURCE_VALUES` cannot satisfy that contract. |

---

## 8. Cross-references

- `A.5.3.2-PR7-FRAMING.md` (`1c1e061`) — binding pre-spec
  contract; §4.2 inert-parameter binding pair (this spec §0 +
  §4.2.5); §5.5 legacy-synthesis binding pair (this spec §0 +
  §4.4.2); §6 constructs-resistant-to-cleanup-pressure class
  (this spec §3 risk #5, §6 step 8, §7 phase-end conditions);
  §7 non-acquisition commitments (this spec §2 out-of-scope).
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — gate-level
  architecture; §6.1 carrier #14 (this spec §0); §6.2 binding
  framing clarification (this spec §0); §9 schema delta
  (this spec §4.3 + §4.4); §10 PR partitioning (this spec
  §1 success condition).
- `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — durable archival state;
  §1.3 truth-vs-mechanism distinction (informs `_sources.py`'s
  governance docstring shape per this spec §4.1); §1.1 Layer
  3 lint operational shape (regression-asserted in this spec
  §6 step 5 + RC-1).
- `A.5.3.2-PR6-SPEC.md` §0 — eleven inherited carriers + two
  PR 6 additive carriers (this spec §0).
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern
  (Properties A–D); preserved unchanged into PR 7.
- `A.5.3.2-GATE-1-SPEC.md` §5.2 — helper signature for
  `emit_divergence_capture(...)`; this spec §4.2.5 modifies
  the implementation but preserves the external signature.
- `A.5.3.2-PR3-SPEC.md` §5 — orthogonal-truth-surfaces;
  carrier #3 + §4.2.5 resolution-path-as-explicit-input
  discipline.
- `A.5.3.2-PR3-SPEC.md` §6.5 — atomic-append discipline;
  inherited verbatim into `_persist_expectation_record`'s
  writer path (this spec §4.2.6).
- `A.5.3.2-INSTRUMENT-CONTRACT.md` §3 — record shape; PR 7
  extends with `record_kind` per Gate 2 framing §9.2 + this
  spec §4.3.1.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` §8.4 — privacy posture;
  unchanged by PR 7 (no new fields are written from runtime
  inputs that haven't already been governed by §8.4).
- `forge_bridge/console/handlers.py:1185` — chat-handler
  observation call site; **unchanged by PR 7** (Property C
  protection).
- `forge_bridge/console/_step.py:233` — chain-step observation
  call site; **unchanged by PR 7** (Property C protection).
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  observation helper; this spec §4.2.5 adds contextvar
  resolution internally; signature unchanged from external
  view.
- `forge_bridge/corpus/_capture.py::_persist_expectation_record` —
  new private helper; consumed by PR 8's
  `emit_seed_expectation` only; not invoked from any
  production call site in PR 7's delta.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3 lint;
  **unchanged by PR 7**, regression-asserted in this spec
  §6 step 5 (immediate post-Step-5 checkpoint) and §7 close
  conditions (RC-1).
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` — Layer
  1 admission; this spec §4.5 adds one entry (`_sources.py`).
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — methodology
  seed; §2.3 (substrate maturity → property-preservation
  discipline) governs PR 7's spec drafting; framing §6
  (cleanup-pressure-resistance class) is candidate methodology
  contribution awaiting at-least-one-more-reliability-phase
  independent corroboration.

---

## Resume protocol — what the next session does with this spec

Resumption from this spec opens at **Step 1** of §6
(`_sources.py` creation). The eight steps proceed in order;
Step 5 receives full three-round review with the immediate
Layer-3-lint regression checkpoint; all other steps are
light-touch.

If a future session opens mid-implementation, the resume
protocol is:

1. `git status` to identify the in-progress step.
2. Cross-reference §6 to determine which step is incomplete.
3. Re-read the relevant subsection of §4 for the surface
   contract.
4. Verify all preceding steps' tests still pass before
   continuing.
5. If Step 5 has not yet had its regression checkpoint run,
   run it before proceeding to Step 6 — the checkpoint is
   the most important moment in PR 7's implementation and
   must not be skipped.

PR 7 spec locks here. Implementation begins at the next
session boundary.
