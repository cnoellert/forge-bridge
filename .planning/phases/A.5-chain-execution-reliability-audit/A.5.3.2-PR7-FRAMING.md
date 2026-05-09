# A.5.3.2 PR 7 — Framing (schema + contextvar provenance resolution)

**Status:** PR 7 opens at `ceac9b5` (origin/main, Gate 2 framing
locked). This framing establishes the implementation contract
for PR 7's plumbing-shaped landing: the dispatch-provenance
contextvar layer, the persistence schema delta, and the narrow
persistence-surface that PR 8's expectation helpers will consume.
It precedes spec drafting.

---

## 1. Predecessors (binding, in order)

- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — gate-level
  architectural posture; binding decisions Q1 / Q1.5 / Q1.6 /
  Q1.7; carrier #14 + binding framing clarification on call-site-
  owned arbitration inputs; non-acquisition commitments (six
  items).
- `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — Gate 1 close; durable
  archival state PR 7 inherits; the truth-vs-mechanism
  discipline (§1.3); discovery-based input set discipline
  (§5.3).
- **Gate 2 → PR 7 convergence pass (this session):** five
  positions converged through writer's-room iteration. The pass
  produced two binding-statement pairs (§4.2 inert-parameter
  discipline; §5.5 legacy-record synthesis) and the **constructs
  intentionally resistant to cleanup pressure** architectural
  class (§6).

---

## 2. PR 7 objective

PR 7 ships the **persistence-and-resolution plumbing** for
Gate 2:

- A dedicated `KNOWN_SOURCE_VALUES` governance module at the
  persistence/schema layer (`forge_bridge/corpus/_sources.py`).
- A contextvar-scoped dispatch-provenance resolution layer
  inside `emit_divergence_capture`, with a public
  `seed_dispatch_scope` context manager + private
  `_DispatchContext` payload.
- A `record_kind` discriminator at the persistence schema
  layer, distinguishing observation records from expectation
  records.
- Reader validation extensions covering both governance
  surfaces, plus legacy-record synthesis for records persisted
  before the schema bump.
- A narrow persistence-surface that expectation helpers (PR 8)
  will consume.

PR 7 introduces **no new authority surfaces.** Observation
authority remains singular at `emit_divergence_capture`. The
expectation authority surface lands in PR 8. PR 7's work is
plumbing — but plumbing that protects three carrier-grade
properties: gate separation (carrier #14), helper-singularity
(carriers from PR 4–6), and the inert-parameter discipline
established in this convergence pass (§4.2 / §5.1).

---

## 3. Architectural inheritance

### 3.1 Gate 2 framing decisions PR 7 implements

| Gate 2 lock | PR 7 deliverable |
|---|---|
| **Q1** (Model A — seed as driver) | Contextvar resolution path enables seed runs to drive live arbitration without modifying call sites. |
| **Q1.5** (contextvars-scoped dispatch) | `_DispatchContext` dataclass + single `_dispatch_context` ContextVar + `seed_dispatch_scope` context manager. |
| **Q1.6** (companion records + dedicated helper) | Narrow persistence-surface lands here for PR 8's `emit_seed_expectation` to consume. |
| **Q1.7** (Property C unchanged; KNOWN_SOURCE_VALUES at persistence layer) | `_sources.py` + `KNOWN_SOURCE_VALUES` constant + governance docstring. |

### 3.2 Carriers PR 7 must carry verbatim

All 14 carriers + the binding framing clarification on
call-site-owned arbitration inputs travel into PR 7's:
- module docstrings of any production module touched
  (`_sources.py`, `_capture.py`).
- top-level docstrings of any test module added.
- commit message body under "preserved invariants."

Carrier #14 is particularly load-bearing for PR 7 because PR 7
is where it physically incarnates: the contextvar resolution
path inside `emit_divergence_capture` is the *only* surface
where call-site declaration becomes resolved record provenance.
Carrier #14 must appear verbatim in `_capture.py`'s module
docstring.

### 3.3 Layer separation PR 7 preserves

PR 7 does not modify the Layer 3 lint. Property C remains
literally `source="runtime"`. Gate 2 framing's gate separation
(§3.4) is the binding constraint on PR 7: the lint sees declared
shape, persistence sees resolved provenance, and PR 7's
resolution path is the *only* bridge.

---

## 4. Architectural delta from PR 7

### 4.1 The dispatch-provenance contextvar layer

PR 7 introduces `forge_bridge.corpus._capture._dispatch_context`,
a single `ContextVar[_DispatchContext | None]` whose scope is
managed exclusively by the public `seed_dispatch_scope(...)`
context manager. The contextvar's payload is a private frozen
dataclass:

```python
@dataclass(frozen=True)
class _DispatchContext:
    source: Literal["runtime", "seed"]
    fixture_id: str
```

The dataclass is private (underscore-prefixed). Seed driver code
(PR 8) interacts only through `seed_dispatch_scope`, never by
constructing `_DispatchContext` directly. This preserves the
bounded-surface property: dispatch state is constructed at
exactly one site (the scope helper), persisted by exactly one
site (the resolution path inside `emit_divergence_capture`), and
inspected by exactly one site (the resolution path again).

### 4.2 The runtime-inert source parameter

The call-site `source="runtime"` literal at every emit call site
is **structurally authoritative** (Property C of the Layer 3
lint asserts it) and **operationally inert** (the helper's
runtime logic ignores it). The persisted `source` value is
derived exclusively from the contextvar, defaulting to
`"runtime"` when no scope is active.

> **The call-site source parameter is intentionally inert at
> runtime. Its purpose is structural (Property C compliance at
> the observation boundary), not operational (persisted
> provenance resolution).**

> **Future contributors must not remove the parameter or couple
> persisted provenance resolution to the declared call-site
> value.**

These two binding statements travel verbatim into `_capture.py`'s
module docstring + the commit message body. They are not
numbered carriers (their scope is internal to the helper's
documentation) but their language is binding.

### 4.3 The narrow persistence-surface for expectation records

PR 7 introduces a dedicated persistence helper that PR 8's
`emit_seed_expectation` will consume. The framing-level
commitment:

- The helper handles JSONL persistence for **expectation
  records only**.
- It does not handle observation records (those persist through
  `emit_divergence_capture`'s existing path).
- It is colocated with the existing observation-persistence
  path in `_capture.py` for spatial cohesion of the persistence
  layer.
- It is intentionally **narrow** — PR 8's seed driver imports it
  exclusively, never accessing builders or low-level writers
  directly. (Gate 2 framing §8.2 is the binding constraint.)

The helper's exact name + signature is finalized in PR 7 spec.

### 4.4 The record_kind discriminator

The persistence schema gains a
`record_kind: Literal["observation", "expectation"]` field.
Observation records (written by `emit_divergence_capture`)
always carry `record_kind="observation"`. Expectation records
(written by the narrow persistence-surface introduced here,
consumed by PR 8) always carry `record_kind="expectation"`.

`record_kind` is governed structurally (Gate 2 framing §9.2):
new values imply a new authority surface, not merely a new
provenance class.

### 4.5 Reader validation extension

PR 3's reader gains validation logic per Gate 2 framing §9.3 +
§5.5 of this framing:
- `record_kind` must be a known value (one of `"observation"`,
  `"expectation"`).
- For `record_kind == "observation"`, `source` must be a member
  of `KNOWN_SOURCE_VALUES`.
- For `record_kind == "expectation"`, no `source` field is
  expected.
- Legacy records (missing `record_kind`) are interpreted
  synthetically at read time per §5.5, never rewritten in place.

---

## 5. Binding decisions

### 5.1 Runtime-inert source parameter (§4.2 detail)

The call-site `source` parameter is intentionally inert at
runtime. Removing it or coupling its value to persistence
resolution erodes the gate separation. Its purpose is:

- **Structural** — satisfies Property C of the Layer 3 lint,
  which asserts literal `source="runtime"` at every discovered
  call site. Property C is the carrier of the declared-vs-
  resolved distinction at the call-site layer (Carrier #14).
- **Not operational** — the helper's runtime logic ignores it.
  The persisted source field is contextvar-resolved.

This is the first explicit member of the **constructs
intentionally resistant to cleanup pressure** class (§6).

### 5.2 Dispatch-scope helper — no-yield context manager

`seed_dispatch_scope(...)` is a context manager that yields no
public value:

```python
with seed_dispatch_scope(fixture_id="..."):
    # caller dispatches fixture through arbitration pipeline
    ...
```

The helper's `__enter__` sets the contextvar; `__exit__` resets
it via the token returned from `ContextVar.set()` (internal
implementation detail, not exposed). **No nested-scope token
surface is pre-authorized.** If a future PR surfaces a concrete
need for nested-scope introspection, that becomes an explicit
framing/spec expansion event — never accidentally-carried-
forward latent API surface.

### 5.3 Dispatch context payload — private frozen dataclass

`_DispatchContext` is private (underscore-prefixed),
`@dataclass(frozen=True)`, single-contextvar owned. Seed driver
code interacts through `seed_dispatch_scope` exclusively.
Direct construction is structurally prohibited (private name +
frozen instance).

What this protects:
- atomic provenance state (single dataclass, not a family of
  peer fields).
- bounded surface area (one contextvar, not a proliferation of
  peers).
- narrow §8.2 permitted-imports surface for `_seed.py` (PR 8 has
  no reason to import `_DispatchContext` because it cannot
  construct one).

### 5.4 Persistence-surface ownership — PR 7

The narrow persistence-surface that expectation helpers consume
lands in PR 7. PR 8 consumes it; PR 8 does not extend it.

What this protects: PR 7 is plumbing-shaped (schema + persistence
+ resolution); PR 8 is purely surface work (driver + expectation
helper). Splitting persistence across PRs would smear the
cadence-matches-work-depth review rule.

### 5.5 Legacy-record synthesis — backward-compat only

Records persisted before PR 7 (the operational capture corpus
under `FORGE_BRIDGE_DIVERGENCE_CAPTURE=1` since PR 4 + PR 5) do
not have a `record_kind` field. PR 7 introduces the field. The
reader's policy:

> **`record_kind` synthesis exists solely for backward
> compatibility with records that predate PR 7. Writers
> introduced by PR 7 must always emit explicit `record_kind`
> values.**

> **Legacy records may be interpreted through synthesized
> defaults at read time but are not rewritten or normalized in
> place by the reader.**

These two binding statements travel verbatim into the reader
module's docstring + the commit message body.

What this protects:
- archaeology integrity — the existing capture corpus is
  operational; records are not silently rewritten.
- the structural distinction `record_kind` introduces —
  synthesis is a read-time interpretation, not a write-time
  normalization. The temporal asymmetry between legacy and
  contemporary records is itself preserved.

---

## 6. Constructs intentionally resistant to cleanup pressure

A new architectural class surfaces explicitly with PR 7. Members
are constructs whose presence might appear redundant or
removable to a future contributor doing a "cleanup pass," but
whose removal would erode the architecture.

**Initial members:**

1. **Helper duplication.** `emit_divergence_capture` +
   `emit_seed_expectation` (PR 8) could be unified into one
   helper with kwargs distinguishing observation from
   expectation. They are deliberately separate. Removing the
   duplication smears authority surfaces — observation and
   authored declaration are distinct truth classes (Gate 2
   framing §4.2).

2. **Visual asymmetry.** The load-bearing visual pattern
   (Properties A–D, validated by the Layer 3 lint) at every
   emit call site could be flattened into a more compact form.
   It is deliberately preserved. Removing the asymmetry erodes
   the structural backstop PR 6 shipped.

3. **Intentionally inert structural parameters.** The call-site
   `source="runtime"` literal at every emit call site could be
   removed since the helper ignores it at runtime. It is
   deliberately retained. Removing it breaks Property C and
   erodes carrier #14's call-site-vs-persistence distinction.

PR 7 adds member #3 to the class explicitly. The class is
itself a discipline: each member must carry inline documentation
explaining why it appears redundant and why its removal would
erode the architecture. Future PRs adding members follow the
same pattern — name the construct, name the protection,
document the cleanup-pressure resistance.

**Why this class matters.** The architecture is now explicitly
protecting itself against *cleanup drift*, not merely
implementation error. A construct that erodes silently because
it "looked redundant" is a different failure mode from a
construct that erodes because someone implemented it wrong.
Cleanup drift is patient — a future PR titled "remove redundant
param" looks locally defensible, and the redundancy looks real
from inside the cleanup PR's diff. The named class is the
structural defense: a construct in the class cannot be removed
without first naming the protection it carries and arguing
the protection is no longer needed (a framing-level question,
not a cleanup-PR question).

This observation is candidate methodology contribution from
PR 7's framing pass — promotion to
`SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` is gated on at
least one more reliability phase surfacing a member of the
class under genuinely independent conditions.

---

## 7. Non-acquisition commitments

PR 7 explicitly does **not**:

1. **Touch the Layer 3 lint.** `test_pr6_visual_asymmetry.py`
   ships unchanged. Property C remains `source="runtime"`
   literal. PR 7 verifies the lint passes against the modified
   `_capture.py` as a regression check; it does not modify the
   lint.

2. **Introduce the seed driver or expectation helper.** Those
   land in PR 8. PR 7's narrow persistence-surface is consumed
   by PR 8 but not invoked from any production call site in
   PR 7's own delta.

3. **Modify call sites.** `handlers.py:1185` and `_step.py:233`
   (the two emit call sites) ship unchanged. Their
   `source="runtime"` literal stays exactly as it is; the
   helper's internal resolution is what changes.

4. **Modify `divergence_capture_enabled()` or its env-gate.**
   The single env boundary remains the Gate 1 boundary. PR 7's
   contextvar layer is orthogonal to the env gate.

5. **Backfill or rewrite legacy records.** Reader synthesis is
   read-time interpretation only; legacy records are not
   normalized in place (§5.5).

6. **Pre-authorize nested-scope token surface on
   `seed_dispatch_scope`.** The helper yields nothing publicly.
   Internal `ContextVar.set()` token use is implementation
   detail (§5.2).

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST` extension

`tests/corpus/test_pr3_discipline.py::_ALLOWLIST` extends with
one entry:

- `forge_bridge/corpus/_sources.py`

`_seed.py` extension is deferred to PR 8 (where the file lands).

### 8.2 Layer 2 — `_PERMITTED_CORPUS_IMPORTS` not yet extended

PR 7 adds no new permitted-imports entries. The seed driver's
permitted imports land with the driver in PR 8.

PR 7 does add new exports from `_capture.py` — the
`seed_dispatch_scope` context manager + the narrow
persistence-surface helper. These are exported from
`forge_bridge.corpus._capture`, not from a new module, so
existing Layer 2 entries permitting `_capture.py` imports do not
need extension. Whether they enter `forge_bridge.__all__` is a
public-API decision deferred to PR 7 spec — likely they remain
corpus-internal until PR 8 establishes the seed-driver consumer.

### 8.3 Layer 3 — unchanged

`test_pr6_visual_asymmetry.py` ships unchanged into PR 7. PR 7's
regression contract verifies the lint passes against the
modified `_capture.py`. Property C's literal check passes
because call sites are unchanged.

---

## 9. Schema / persistence delta

### 9.1 KNOWN_SOURCE_VALUES (governance contract per Gate 2 framing §9.1)

```python
# forge_bridge/corpus/_sources.py

# PROTECTED PROPERTY (truth):
# Persisted provenance classes are governed. Adding a new source
# class requires explicit framing-level review plus synchronous
# update of: this constant, reader validation, the contextvar
# resolution path inside emit_divergence_capture, and the Gate 4
# comparator's partition logic. Mergeability is contingent on all
# four updating in lockstep.
#
# MECHANISM:
KNOWN_SOURCE_VALUES: frozenset[str] = frozenset({"runtime", "seed"})
```

### 9.2 record_kind discriminator (governance per Gate 2 framing §9.2)

```python
# Persistence schema
record_kind: Literal["observation", "expectation"]
```

`record_kind` is governed **structurally** — new values imply a
new authority surface (not merely a new provenance class).
Adding a third `record_kind` requires the corresponding helper,
signature, and truth claim — all framing-level decisions.

### 9.3 _DispatchContext (the contextvar payload)

```python
# forge_bridge/corpus/_capture.py

@dataclass(frozen=True)
class _DispatchContext:
    source: Literal["runtime", "seed"]
    fixture_id: str
```

Private (underscore prefix). Frozen. Constructed only by
`seed_dispatch_scope`.

### 9.4 The contextvar

```python
# forge_bridge/corpus/_capture.py

_dispatch_context: ContextVar[_DispatchContext | None] = \
    ContextVar("_dispatch_context", default=None)
```

Single contextvar. Module-private.

### 9.5 seed_dispatch_scope (the public scope helper)

Public exact-name binding: `seed_dispatch_scope`. Context
manager. Yields nothing publicly. Sets the contextvar on entry,
resets on exit via `ContextVar.set()` token (implementation-
internal). Shape lock:

```python
@contextmanager
def seed_dispatch_scope(*, fixture_id: str) -> Iterator[None]:
    """Activate seed-dispatch provenance for the current scope."""
    token = _dispatch_context.set(
        _DispatchContext(source="seed", fixture_id=fixture_id)
    )
    try:
        yield
    finally:
        _dispatch_context.reset(token)
```

(Exact body lands in PR 7 implementation; framing locks the
shape and the no-yield contract.)

### 9.6 Resolution path inside emit_divergence_capture

The helper consults `_dispatch_context.get()` at emission time:

- Scope inactive (returns `None`) → persisted `source="runtime"`,
  no `fixture_id` populated.
- Scope active → persisted `source` from the dispatch context,
  `fixture_id` from the dispatch context.

The call-site `source="runtime"` literal value is **ignored** at
runtime. It exists exclusively for Layer 3 Property C's
structural assertion.

### 9.7 Reader validation extension

Per Gate 2 framing §9.3 + §5.5 of this framing:

- `record_kind` validation against the literal enum.
- `source` validation against `KNOWN_SOURCE_VALUES` for
  observation records.
- No `source` field expected on expectation records.
- Legacy records (missing `record_kind`) interpreted as
  `record_kind="observation"` synthetically at read time; not
  rewritten in place.

---

## 10. Implementation surface — files touched

| File | Change kind | Scope |
|---|---|---|
| `forge_bridge/corpus/_sources.py` | NEW | `KNOWN_SOURCE_VALUES` + governance docstring + protected-property docstring |
| `forge_bridge/corpus/_capture.py` | MODIFY | `_DispatchContext` dataclass; `_dispatch_context` ContextVar; `seed_dispatch_scope` public helper; narrow persistence-surface for expectation records; resolution path inside `emit_divergence_capture` |
| `forge_bridge/corpus/<reader-module>` | MODIFY | `record_kind` field on the record schema; reader validation extension; legacy-record synthesis |
| `tests/corpus/test_pr3_discipline.py` | MODIFY | `_ALLOWLIST` extension for `_sources.py` |
| `tests/corpus/test_pr7_*.py` | NEW | PR 7-specific structural + behavioral tests (§11) |

PR 7 spec finalizes:
- exact location of the narrow persistence-surface for
  expectations (within `_capture.py` or a colocated module).
- exact reader-module path (PR 3's reader location).
- whether `seed_dispatch_scope` enters `forge_bridge.__all__`
  or stays corpus-internal.
- exact name of the narrow persistence-surface helper.

---

## 11. Test surface

### 11.1 New tests PR 7 ships

- **`test_known_source_values.py`** — validates the governance
  docstring + frozenset shape; future renames or value
  additions surface here.
- **`test_dispatch_context.py`** — contextvar resolution under
  all four scope states. Asserts:
  - scope inactive → persisted `source="runtime"`, no
    `fixture_id`.
  - scope active → persisted `source` from dispatch context,
    `fixture_id` from dispatch context.
  - call-site `source` value semantically inert (passing
    arbitrary strings yields contextvar-derived persisted
    value; this test is itself the inert-parameter contract's
    enforcement).
  - exception inside scope cleanly resets the contextvar.
- **`test_record_kind_schema.py`** — round-trip of both
  `record_kind` values.
- **`test_reader_validation.py`** — tolerates missing
  `record_kind`; rejects unknown `record_kind`; rejects unknown
  `source`; no `source` expected on expectation records.
- **`test_legacy_record_synthesis.py`** — legacy record (no
  `record_kind`) interpreted as observation; legacy record not
  rewritten in place (read does not mutate the source file).

### 11.2 Regression assertions

- **Layer 3 lint passes unchanged.** `test_pr6_visual_asymmetry.py`
  runs unchanged against the modified `_capture.py`. Property C's
  literal check passes because call sites are unchanged.
- **Existing observation behavior preserved.** Records persisted
  via the modified `emit_divergence_capture` (with no scope
  active) match Gate 1's record shape modulo the new
  `record_kind="observation"` field.

---

## 12. Phase-end / PR-end conditions

PR 7 closes when:

1. All deliverables in §10 land and pass tests in §11.
2. Layer 3 lint passes unchanged (regression contract).
3. The 14 carriers + the binding framing clarification + the
   §4.2 inert-parameter binding statements + the §5.5
   legacy-synthesis binding statements travel verbatim into the
   relevant module docstrings + test docstrings + commit
   message bodies.
4. The narrow persistence-surface is in place and ready for
   PR 8 to consume (validated by PR 8's spec drafting; PR 7's
   own surface area does not yet invoke it from production
   code).
5. A `A.5.3.2-PR7-CLOSE.md` artifact ships at PR 7's final
   commit, following the PR 6 close artifact's structure
   (predecessors, what PR 7 established, what PR 8 inherits,
   methodology observations including the §6 cleanup-pressure
   class as a candidate, cross-references).

---

## 13. Cross-references

- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — gate-level
  architecture; §3.4 gate separation; §5.4 Q1.7 lock; §6.1
  carrier #14; §9 schema delta; §10 PR 7 row of the
  partitioning table.
- `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — durable archival state;
  §1.3 truth-vs-mechanism distinction (informs `_sources.py`'s
  governance docstring shape); §1.1 Layer 3 lint operational
  shape; §5.3 discovery-based input set discipline.
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern
  (Properties A–D); preserved unchanged into PR 7.
- `A.5.3.2-GATE-1-SPEC.md` §5.2 — helper signature for
  `emit_divergence_capture(...)`; PR 7 modifies the
  implementation but preserves the external signature.
- `forge_bridge/console/handlers.py:1185` — chat-handler
  observation call site; **unchanged by PR 7** (Property C
  protection).
- `forge_bridge/console/_step.py:233` — chain-step observation
  call site; **unchanged by PR 7** (Property C protection).
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  observation helper; PR 7 adds contextvar resolution
  internally; signature unchanged from external view.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3 lint;
  **unchanged by PR 7**, regression-asserted in §11.2.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — §2.3
  (substrate maturity → property-preservation discipline)
  governed PR 7's framing pass; §6 of this artifact is
  candidate methodology contribution (constructs intentionally
  resistant to cleanup pressure).

---

PR 7 framing locks here. PR 7 spec drafts at the next session
boundary; implementation derives from spec per the Gate 1
cadence (cadence-matches-work-depth: plumbing-shaped, light-
touch review).
