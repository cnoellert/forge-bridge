# A.5.3.2 PR 8 — Framing (seed driver + authored-expectation helper)

**Status:** Framing-stage artifact for PR 8 of Gate 2. PR 7 closed
at `b035c87` on `origin/main`; this framing opens PR 8's
discuss-then-spec cadence. Boundary-shaped work — full three-round
review applies across the entire PR (per Gate 2 framing §5.7 + PR 7
close §3 "what PR 8 changes").

This framing's job: name the architectural boundary PR 8 establishes
(the authored-expectation surface), lock the binding decisions that
were left open at Gate 2 framing time, introduce the new carrier
sentence that protects the chat-handler-only surface scope, and
enumerate what PR 8 deliberately does NOT decide. The spec derives
from this artifact; implementation derives from the spec.

---

## 0. Crystallizing sentence — carrier #15 (verbatim, load-bearing)

Carrier #15 is introduced here at PR 8 framing time. It travels
verbatim into:

1. `forge_bridge/corpus/_seed.py` module docstring (alongside the
   inherited 14 carriers + binding framing clarification).
2. The PR 8 commit message body under "preserved invariants" /
   "new carrier introduced."
3. Top-level docstrings of new PR 8 test modules.
4. `A.5.3.2-PR9-FRAMING.md` predecessors (PR 9 inherits this
   carrier as binding context for fixture topology decisions).
5. The future chain-step-seeding framing pass (whenever drafted),
   as a binding predecessor.

**Carrier #15 — chat-handler-only seeding scope:**

> **PR 8 seeds the chat-handler observation surface only. Chain-step
> seeding is explicitly deferred because `handlers.py` and
> `_step.py` produce semantically distinct observation records.
> Cross-surface expectation semantics require a dedicated framing
> pass before implementation proceeds.**

The third clause is governance, not explanation: any future PR
proposing chain-step seeding must produce a framing artifact
defining cross-surface expectation semantics BEFORE implementation
proceeds. Implementation-first work on chain-step seeding is
rejected at the spec layer. The protection #15 carries:

A future contributor who sees PR 8's `drive_seed_fixture` driving
`chat_handler` directly may propose: *"Why not just run the same
fixtures through both `handlers.py` and `_step.py` automatically?"*
That proposal is local-defensible (it looks like a small
generalization) and architecturally dangerous (the two call sites
emit semantically distinct observation records — different
`ambiguity_state` shapes, different `narrower_decision` semantics,
different arbitration topology). The naive coupling silently
commits to a fixture-identity-spans-multiple-surfaces ontology
before the room has had room to decide whether that ontology is
correct.

Carrier #15 anchors the burden of proof: the proposal must produce
a framing artifact defining cross-surface semantics, not a code
diff coupling two call sites.

---

## 1. Predecessors (binding, in order)

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants (I-1 through I-6).
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs;
  visual-asymmetry pattern (§5.1, Properties A–D); helper signature
  (§5.2); three architecturally-prohibited patterns (§5.3).
- `A.5.3.2-PR3-SPEC.md` — persistence layer; atomic-append
  discipline (§6.5).
- `A.5.3.2-PR4-CLOSE.md` (`fab26cb`) — risk-category shift;
  integration-discipline quartet; "what PR N+1 inherits" archaeology
  shape.
- `A.5.3.2-PR5-CLOSE.md` (`b8f522e`) — surface geometry asymmetry;
  chain-step integration durable archival state.
- `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — Layer 3 lint; Gate 1
  closure; truth-vs-mechanism distinction (informs `_seed.py`
  governance docstring shape).
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — gate-level architecture;
  §3.4 three-authority-surface partitioning (PR 8 lands the third
  surface); §4.1 Model A locked (seed drives live arbitration);
  §4.4 companion records (truth-partitioning, not duplication);
  §5.3 Q1.6 companion records + dedicated expectation helper
  locked; §5.5 module siting (`_seed.py`); §5.7 PR partitioning
  (PR 8 = boundary work, full three-round); §7 six non-acquisition
  commitments; §8.1 Layer 1 extension; §8.2 Layer 2 extension;
  §8.3 Layer 3 unchanged.
- `A.5.3.2-PR7-FRAMING.md` (`1c1e061`) — §6 cleanup-pressure-
  resistance class (introduced at PR 7; PR 8 contributes members
  #7 + #8); §7 seven non-acquisition commitments (preserved into
  PR 8 plus PR 8 adds one — chain-step seeding).
- `A.5.3.2-PR7-SPEC.md` (`84392d2`) — implementation contract for
  the seam PR 8 consumes; §4.2.4 `seed_dispatch_scope`; §4.2.6
  `_persist_expectation_record`; §7 phase-end conditions (rejection
  table — PR 8 may not propose any of those mutations even
  incidentally).
- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — durable archival state PR 8
  inherits; §2 "what PR 8 inherits from PR 7" (the seam contract);
  §3 "what PR 8 changes" (this framing operationalizes that
  section); §1.2 cleanup-pressure-resistance class inventory
  (6 members at PR 7 close; PR 8 grows to 8); §5 methodology
  observations.
- `project_pr8_base_expectation_args.md` (local memory) — flagged
  expectation: `base_expectation_args` test helper lands at PR 8,
  not at incarnation-time discovery.

---

## 2. PR 8 objective

**Real job:** *"Land the seed-driver authority surface for
Gate 2. Ship `forge_bridge/corpus/_seed.py` containing two
helpers: a single `emit_seed_expectation(...)` helper that
authors a declared expectation record (semantics-not-topology
per Gate 2 §5.3), and a single `drive_seed_fixture(...)`
function that orchestrates one fixture invocation — building
the expectation, persisting it via the helper, opening
`seed_dispatch_scope`, invoking `chat_handler` directly
in-process, exiting the scope. Extend Layer 1 (`_ALLOWLIST`)
and Layer 2 (`_PERMITTED_CORPUS_IMPORTS`) per the
mechanical-extension shape Gate 2 framing §8 specifies. PR 8
seeds the chat-handler observation surface only — carrier #15
governs."*

PR 8's three operational responsibilities:

- **Author the authored-expectation surface.** A new public-from-
  corpus helper `emit_seed_expectation(...)` that captures the
  truth claim *"this is what the fixture-author declares the
  arbitration outcome should be."* Distinct signature from
  `emit_divergence_capture`. Delegates persistence to the PR 7
  seam (`_persist_expectation_record`).
- **Wire the driver.** A new public-from-corpus function
  `drive_seed_fixture(...)` that orchestrates one fixture
  invocation. The driver does NOT invoke chain-step; carrier #15
  governs.
- **Extend the structural-test discipline mechanically.**
  Layer 1 admits `_seed.py` to `_ALLOWLIST`. Layer 2 admits
  `_seed.py → {seed_dispatch_scope, _persist_expectation_record}`
  to `_PERMITTED_CORPUS_IMPORTS`. Layer 3 unchanged (no new
  `emit_divergence_capture` call sites in PR 8's delta).

Plus one PR-8-internal-but-Gate-4-bound deliverable: extending
the schema validator's `record_kind == "expectation"` branch
with required-keys-for-expectation (`fixture_id`, `prompt`,
`expected_narrow`). The PR 7 close left this as a deferred
extension (per `_schema.py:225–228` inline comment); PR 8
operationalizes it because PR 8 is the first PR to construct
expectation records.

**Success condition:** *"PR 8 ships `_seed.py` (new),
modifications to `_schema.py` (expectation-record required-keys
extension), `_ALLOWLIST` (mechanical extension),
`_PERMITTED_CORPUS_IMPORTS` (one-entry extension),
`tests/corpus/_pr3_helpers.py` (or sibling — adds
`base_expectation_args`), and a new test module
`tests/corpus/test_pr8_seed_surface.py` exercising the helper +
driver + Layer 1/2 extensions + the schema-validator extension.
The Layer 3 lint passes unchanged. PR 4 + PR 5 + PR 7
integration tests pass unchanged. PR 8 seeds `chat_handler`
only; no `_step.py:233` driver path lands. The 15 carriers + the
binding framing clarification travel verbatim into `_seed.py`
module docstring + commit message body + new test module
docstring. Full three-round review applies across the PR."*

---

## 3. Architectural inheritance

### 3.1 Gate 2 framing decisions PR 8 implements

PR 8 implements the seed-driver portion of Gate 2 framing's three-
authority-surface partitioning (§3.4):

| Surface | Gate 2 framing reference | PR | Deliverable |
|---|---|---|---|
| **Observation (call-site)** | §3.4 + §6.1 carrier #14 | PR 7 | `emit_divergence_capture` (existing) + contextvar resolution path (PR 7 §4.2.5) |
| **Dispatch provenance (operational)** | §4.3 + §5.2 Q1.5 | PR 7 | `seed_dispatch_scope` + `_DispatchContext` (PR 7 §4.2.2–§4.2.4) |
| **Authored expectation (declaration)** | §4.2 + §5.3 Q1.6 | **PR 8** | **`emit_seed_expectation` + `drive_seed_fixture` (this framing)** |

PR 8 closes the third surface. The architectural commitment Gate 2
framing §5.3 locks — *"`emit_seed_expectation` owns authored
expectation semantics, not persistence topology"* — is the
controlling discipline for PR 8's implementation.

PR 8 also operationalizes Gate 2 framing's:
- §4.1 Model A — seed drives live arbitration (`drive_seed_fixture`
  invokes `chat_handler` directly).
- §4.4 Companion records — each fixture invocation produces two
  records (one expectation, one observation) joined later by Gate 4
  on `fixture_id`.
- §5.5 Module siting — `_seed.py` is a single sibling module to
  `_capture.py`, not a subpackage.
- §5.7 PR partitioning — PR 8 ships zero fixtures; PR 9 ships
  fixtures + integration tests.
- §8.1 Layer 1 extension — `_seed.py` admitted mechanically.
- §8.2 Layer 2 extension — `_seed.py` admitted with two permitted
  symbols only.

### 3.2 Carriers PR 8 must carry verbatim

Fifteen numbered carriers + the binding framing clarification.
Fourteen are inherited from Gate 2 / PR 6 (the same set PR 7
inherited and shipped); one is new at PR 8 framing (#15, §0).
Plus the binding framing clarification (Gate 2 §6.2).

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
| **15** | **PR 8 framing §0 — chat-handler-only seeding scope** | **PR 8** |
| — | Gate 2 framing §6.2 — binding framing clarification (call-site-owned arbitration inputs) | Gate 2 |

PR 7's two PR-7-LOCAL binding pairs (§4.2 inert-parameter, §5.5
legacy-synthesis) do NOT travel into PR 8 surfaces — they remain
scope-local to `_capture.py` and `reader.py` respectively. PR 7
close §2.1 names this explicitly: PR-7-LOCAL pairs do not
regenerate.

The fifteen carriers + binding clarification travel verbatim into:

1. `forge_bridge/corpus/_seed.py` module docstring.
2. PR 8 commit message body under "preserved invariants" /
   "new carrier introduced" sections.
3. Top-level docstring of `tests/corpus/test_pr8_seed_surface.py`.

A reader who encounters `_seed.py` without reading the full spec
should encounter the fifteen + binding clarification first. The
new carrier (#15) lands AT TOP of the carrier block — most-current
PR-anchored governance text first per the relevance-by-file
ordering PR 7 close §1.5 established.

### 3.3 Three-authority-surface partitioning preserves intact

PR 7's close §1.1 established the three-authority-surface
partitioning as operational reality. PR 8 closes the partitioning's
third surface without modifying the other two:

- **Observation surface** (PR 7) — Property C + §4.2 inert-parameter
  binding pair + Layer 3 lint. **Unchanged by PR 8.**
- **Dispatch provenance surface** (PR 7) — `seed_dispatch_scope` +
  `_DispatchContext`. **Unchanged by PR 8.** PR 8 *consumes* the
  scope (the driver opens it), but does not modify it.
- **Authored expectation surface** (**PR 8**) — new helper +
  driver land in `_seed.py`. **Introduced by PR 8.**

The non-modification of the first two surfaces is mechanically
verifiable: the Layer 3 lint passes unchanged (no
`emit_divergence_capture` call sites added or modified); PR 7's
§4.2 inert-parameter test (`test_call_site_source_value_is_inert`)
passes unchanged; PR 7's §5.5 legacy-synthesis byte-identicality
test (`test_legacy_file_unchanged_after_read`) passes unchanged.

---

## 4. Architectural delta from PR 8

### 4.1 The seed driver function (`drive_seed_fixture`)

A single public-from-corpus function that orchestrates one fixture
invocation. Lives in `_seed.py`. Signature shape (kwargs locked at
§5.5; final signature in PR 8 spec):

```python
def drive_seed_fixture(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> None:
    """Drive one seed fixture through the chat-handler arbitration
    pipeline. Builds and persists the authored expectation, opens
    seed_dispatch_scope, invokes chat_handler in-process, exits the
    scope.
    
    [Carrier block including #15 lands in module docstring; the
    function's own docstring carries the chat-handler-only scope
    inline at the call site.]
    """
```

The function is fire-and-forget per I-6 (per the corpus convention).
One invocation = one fixture. The "loop over fixtures" concern is
PR 9's domain (the fixtures-and-integration PR ships the iterator
+ the first concrete fixtures).

**Carrier #15 governs the invocation path.** The driver invokes
`chat_handler` directly (in-process function call); it does NOT
invoke `_step.py:233` or any chain-step entry point. The chat
handler may itself invoke chain-step internally for multi-step
prompts, but PR 8's tests assert the driver is exercised only with
single-step prompts (no chain-step execution path fires under
PR 8 seeding).

**Why direct in-process invocation (not HTTP).** Same logic as
carriers #3–6: the integration layer passes truth, not transport.
The arbitration pipeline is the *thing being measured*. HTTP
framing is incidental — exercising it would mean threading the
fixtures through FastAPI, the rate-limit layer, the auth seed
(SEED-AUTH-V1.5), all of which are explicitly out of scope for
Gate 2. In-process invocation matches what Gate 4's comparator
regression tests will want; the symmetry is structural.

### 4.2 The `emit_seed_expectation` helper

Public-from-corpus authored-declaration helper. Lives in
`_seed.py`. Signature locked at §5.4:

```python
def emit_seed_expectation(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> None:
    """Persist an authored expectation record for a seed fixture.
    
    PR 8 SEMANTICS-NOT-TOPOLOGY GUARD (verbatim, load-bearing):
    
      emit_seed_expectation owns authored expectation semantics,
      not persistence topology. The helper expresses the
      authored-declaration truth claim; persistence is delegated
      to _persist_expectation_record (the PR 7 seam). Future
      contributors must not read this helper as the expectation
      persistence layer.
    
    [carrier block + body]
    """
```

The helper:
1. Builds the expectation record dict (4 universal keys +
   `record_kind="expectation"` + the 3 PR-8-required fields).
2. Calls `_persist_expectation_record(record)`.
3. Fire-and-forget per I-6 (the helper itself wraps in
   try/except for I-6, mirroring the discipline that
   `_persist_expectation_record` already applies internally;
   defense in depth).

**Distinct signature from `emit_divergence_capture`** (per Gate 2
framing §5.3). The signature carries no arbitration-state fields
(no `narrower_decision`, no `candidate_set_post_reachability`, no
`identity` fields). The signature carries no `source` parameter
(expectation records have no `source` field; the schema validator
rejects records that carry one).

### 4.3 The operational expectation record shape

Built by `emit_seed_expectation` (NOT by `drive_seed_fixture`).
Final shape:

```python
{
    "schema_version": SCHEMA_VERSION,
    "capture_id": _new_uuid(),
    "captured_at": _now_iso_ms(),
    "record_kind": "expectation",
    "fixture_id": fixture_id,            # PR 8 required key
    "prompt": prompt,                    # PR 8 required key
    "expected_narrow": expected_narrow,  # PR 8 required key (list[str])
}
```

**Minimum-viable required-field set** per §5.3. Optional fields
(label, expected_ambiguity_state, expectation_author, etc.) are
NOT added at PR 8. The architectural posture per §5.3 prose: a
smaller surface is the right discipline; Gate 4's comparator will
surface concrete needs at comparator-write time, and the framing
will revisit the expectation shape then if needed.

**Schema validator extension.** PR 8 extends `_schema.py`'s
`record_kind == "expectation"` branch (per the inline comment at
`_schema.py:225-228` left by PR 7 Step 5):

```python
_REQUIRED_EXPECTATION_KEYS: Final[frozenset[str]] = frozenset({
    "fixture_id",
    "prompt",
    "expected_narrow",
})

# In validate_capture_record's expectation branch:
elif record_kind == "expectation":
    if "source" in record:
        raise SchemaValidationError(
            "expectation record must not carry a 'source' field; ..."
        )
    missing_exp = _REQUIRED_EXPECTATION_KEYS - record.keys()
    if missing_exp:
        raise SchemaValidationError(
            f"expectation record missing required keys: {sorted(missing_exp)}"
        )
    # Per-field type validation:
    if not isinstance(record["fixture_id"], str) or not record["fixture_id"]:
        raise SchemaValidationError("expectation fixture_id must be a non-empty string")
    if not isinstance(record["prompt"], str) or not record["prompt"]:
        raise SchemaValidationError("expectation prompt must be a non-empty string")
    if not isinstance(record["expected_narrow"], list):
        raise SchemaValidationError("expectation expected_narrow must be a list")
    if not all(isinstance(tool, str) for tool in record["expected_narrow"]):
        raise SchemaValidationError("expectation expected_narrow entries must be strings")
```

The extension is additive — observation-record validation
unchanged. PR 7's reader tests for unknown record_kind /
expectation-with-source-field remain green.

### 4.4 Test infrastructure — `base_expectation_args`

Per `project_pr8_base_expectation_args.md` + PR 7 Step 5
precedent. The helper lands in `tests/corpus/_pr3_helpers.py`
(reusing the existing test-helper module to keep the
`base_*_args` family colocated):

```python
def base_expectation_args(**overrides: Any) -> dict[str, Any]:
    """Default-valid kwargs for emit_seed_expectation().
    
    Tests passing these kwargs to the helper get a canonical
    expectation record emission. Tests override individual keys
    to exercise specific behaviors.
    
    Sibling of base_writer_args() (observation/writer surface)
    and base_builder_args() (observation/builder surface). The
    three-helper split mirrors the three-authority-surface
    partitioning the corpus package establishes.
    """
    defaults: dict[str, Any] = {
        "fixture_id": "fix-pr8-default",
        "prompt": "list staged shots",
        "expected_narrow": ["forge_list_staged"],
    }
    defaults.update(overrides)
    return defaults
```

Flagged in framing (not at incarnation) to avoid the PR 7 Step 5
mid-implementation discovery cycle. The naming convention
(`base_expectation_args`) follows the existing family verbatim.

---

## 5. Binding decisions

### 5.1 Q1 — Pipeline invocation path locked at direct function call

The seed driver invokes `chat_handler` via direct in-process
function call. Not HTTP. Not subprocess.

**What this rejects:** HTTP-via-`httpx`-to-`:9996/api/v1/chat`,
subprocess-invocation-of-daemon, any architecture that asks the
seed driver to thread through transport-layer fidelity. The
arbitration pipeline is the thing being measured; transport is
incidental.

**Why this is right:** same logic as carriers #3–6. The integration
layer passes truth (the prompt, the fixture identity, the
expectation), not transport. Threading HTTP / FastAPI / rate-limit
/ auth into the seed driver would conflate the *thing being
measured* with the *measurement vehicle*. Gate 4's comparator will
want the same in-process invocation pattern; the symmetry is
structural.

### 5.2 Q1 refinement — Chat-handler-only surface scope locked

PR 8 seeds the chat-handler observation surface only. Carrier #15
governs (§0).

**What this rejects:** any PR 8 surface that drives `_step.py:233`
directly, any PR 8 test fixture that exercises a multi-step prompt
internally invoking chain-step execution, any PR 8 helper that
takes a "target call site" parameter, any naming convention that
implies the driver is surface-agnostic.

**Why this is right:** the two call sites emit semantically
distinct observation records. Coupling them under one fixture
model would silently commit to a cross-surface ontology before
the room has had room to decide. The ontological questions
deferred per §7.3 require a dedicated framing pass before
implementation proceeds.

### 5.3 Q2 — Expectation record shape locked at minimum viable

Required fields beyond the 4 universal + `record_kind`: exactly
three. `fixture_id` (str, non-empty), `prompt` (str, non-empty),
`expected_narrow` (list[str], possibly empty).

**What this rejects:** speculative optional fields (label,
expected_ambiguity_state, expectation_author, expected_topology,
expected_identity_hashes, etc.). The smaller the surface, the
less drift pressure.

**Why this is right:** Gate 4's comparator will surface concrete
needs at comparator-write time. Adding optional fields now means
guessing at Gate 4's policy questions in advance. Each field
added is a future drift surface; minimum-viable is the right
discipline. Optional fields can be added later via explicit
framing decision rather than carried speculatively.

### 5.4 Q3 — `emit_seed_expectation` signature locked

```python
def emit_seed_expectation(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> None:
```

Keyword-only (matches corpus convention). Fire-and-forget (returns
`None` per I-6). Three required parameters matching the three
required record fields. No optional parameters.

**What this rejects:** positional arguments; optional kwargs;
returning the persisted record dict; raising on validation
failure (failure-invisibility per I-6 is binding); accepting
arbitration-state fields ("just pass them through to the record").

**Why this is right:** the signature carries the truth claim. An
expectation record IS three fields and the universal keys; the
signature reflects that. Optional kwargs would invite the
helper-singularity smearing failure mode (different invocations
producing different authority claims).

### 5.5 Q4 — Single-function driver shape locked

```python
def drive_seed_fixture(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> None:
```

One function. One invocation = one fixture. Generic name
(`drive_seed_fixture`, not surface-explicit `drive_chat_handler_fixture`).
The chat-handler-only scope is protected by carrier #15 + the
function's docstring + the test suite, NOT by the function name.

**What this rejects:** a class wrapper for state management; a CLI
entry point; a fixture-iterator loop; a builder-style fluent API;
surface-explicit naming that would foreclose the future
chain-step-seeding framing pass's option-space (the future pass
might decide one fixture *should* span multiple surfaces, and a
surface-explicit name would force the wrong question).

**Why this is right:** PR 8 ships the one-invocation seam. PR 9
ships the loop. The generic name preserves option-space about
how the future framing pass resolves the ontological questions
(§7.3) — those questions, not the function name, are the locus of
architectural authority.

### 5.6 Q5 — Public API (`__all__`) deferred; corpus-internal at PR 8

Neither `emit_seed_expectation` nor `drive_seed_fixture` enters
`forge_bridge.__all__` at PR 8. The decision is deferred to first
concrete external consumer.

**What this rejects:** speculative `__all__` membership "because
external consumers might want it later." Each `__all__` entry is
authority-surface expansion (per PR 7 spec §7 close conditions).
Defer the public-API question to the first concrete need.

**Why this is right:** PR 9 consumers live in `tests/corpus/` (or
wherever PR 9 framing decides) and can import via
`forge_bridge.corpus._seed` directly without `__all__`. If a
concrete external consumer surfaces (a CLI command, a console
integration, etc.), revisit at the framing time that surfaces
the need. Gate 2 framing §10 explicitly defers this decision to
PR 8 spec; PR 8 framing positions it as a deferral, not as a
binding commitment to corpus-internal status forever.

---

## 6. Constructs intentionally resistant to cleanup pressure

PR 7 framing §6 introduced the class. PR 7 close §1.2 locked the
final PR 7 inventory at 6 members. PR 8 contributes 2 members,
bringing the class final inventory to 8.

### 6.1 Member #7 — Companion records as truth-partitioning

**The construct:** observation records and expectation records
are persisted as separate records in the same JSONL file,
distinguished by `record_kind`, joined later by Gate 4's
comparator on `fixture_id`.

**Local simplification pressure:** *"Merge the observation and
expectation into a single richer record per fixture. The
join-on-fixture_id is an unnecessary round-trip; one unified
record carries the full picture."* The proposal is locally
defensible — fewer records, fewer JSON serializations, fewer
join operations downstream. From inside the proposing PR's
diff, the merge looks like clean simplification with no
visible cost.

**Hidden truth collapse:** A unified "richer" record appears
mechanically simpler because it collapses authored expectation
and observed arbitration into one persistence surface. The
simplification is false: it destroys falsifiability by allowing
expectation and observation to co-author the same artifact.
Once both truths live in the same record, the record cannot
*disagree with itself* — but disagreement between expectation
and observation is exactly what Gate 4's comparator exists to
measure. The merged form is structurally incapable of
representing the divergence the comparator is built to
surface.

**Why the protection exists:** Gate 2 framing §4.4 binds the
truth partitioning explicitly. Observation records claim *"I
observed arbitration in this state"* — runtime truth.
Expectation records claim *"the fixture author declared this is
what arbitration should look like"* — authored truth. The two
claims have different epistemic origins (runtime vs. authored),
different temporal order (expectations exist *before*
execution; observations exist *after*), and different
falsifiability conditions (an observation can falsify an
expectation only when they can be juxtaposed as separate
records). Collapsing them erodes Gate 4's foundational
architecture and forecloses the comparator's measurement
surface before the comparator has been written.

**Operational placement of the protection:**
- `_seed.py` module docstring carries Gate 2 framing §4.4
  paragraphs verbatim, including the falsifiability framing.
- `emit_seed_expectation`'s docstring carries the falsifiability
  framing inline.
- The schema validator's expectation-branch rejects records
  carrying a `source` field — a unified-record proposal would
  fail validation regardless of intent.
- PR 8 commit message body names the falsifiability protection
  explicitly.

### 6.2 Member #8 — `emit_seed_expectation` as semantics-not-topology

**The construct:** `emit_seed_expectation` is a thin helper that
builds the record dict and delegates persistence to
`_persist_expectation_record`. It does NOT contain file I/O, does
NOT call `_resolve_corpus_dir`, does NOT serialize JSONL lines,
does NOT manage the bundled-header-on-first-write discipline.

**Local simplification pressure:** *"`emit_seed_expectation`
already imports `_persist_expectation_record`; let's just inline
the persistence logic into the helper for symmetry with
`emit_divergence_capture` (which contains its own writer body).
One fewer hop; cleaner symmetry between the two helpers."* The
proposal is locally defensible — symmetry between the
observation helper and the expectation helper looks like an
architectural virtue. From inside the proposing PR's diff, the
merge looks like cleanup of an inconsistency.

**Hidden truth collapse:** Inlining persistence into
`emit_seed_expectation` appears symmetrical with
`emit_divergence_capture` but silently transfers persistence-
topology authority into a semantics-scoped helper. The
separation is protected because authored expectation and
persistence topology are intentionally distinct authority
surfaces. Semantic authority answers *"what truth claim is
being made?"*; persistence authority answers *"how is the
record written to disk?"*. The inlined form blurs which
surface holds which authority. A future question — *"who owns
the atomic-append discipline for expectation records?"* —
becomes ambiguous when the answer could be either
`emit_seed_expectation` itself or some inlined sub-function.
Authority leakage degrades the comparator review surface and
the cleanup-PR rejection surface alike.

**Why the protection exists:** The asymmetry between the two
helpers is structural, not accidental. `emit_divergence_capture`
is a runtime-emission flow — semantics and persistence
coincide at the call site because the observation IS the
moment of persistence. `emit_seed_expectation` is a declaration
flow — semantics is authored upstream (the fixture-author's
expectation), persistence is a downstream concern delegated to
the seam PR 7 ships. Forcing symmetry where the underlying
flows are asymmetric collapses the three-authority-surface
partitioning Gate 2 framing's §3.4 establishes.

**Operational placement of the protection:**
- `emit_seed_expectation`'s docstring carries the semantics-not-
  topology guard verbatim, including the authority-surface
  distinction.
- `_seed.py` module docstring restates the authority-surface
  separation.
- Layer 2 (`_PERMITTED_CORPUS_IMPORTS`) enforces mechanically —
  `_seed.py` is permitted only two symbol imports from corpus
  (`seed_dispatch_scope` + `_persist_expectation_record`);
  low-level builder/writer surfaces are prohibited. A future
  PR attempting to inline persistence would either need a new
  Layer 2 admission (visible at review) or violate the existing
  one (mechanically caught).
- PR 8 commit message body names the authority-surface
  separation explicitly.

### 6.3 Class final inventory at PR 8 close

| # | Member | PR | Protection |
|---|---|---|---|
| 1 | Helper duplication (`emit_divergence_capture` + `_persist_expectation_record`) | PR 7 | Framing §6 + spec §7 close conditions |
| 2 | Visual asymmetry (Properties A–D) | PR 6 | Layer 3 lint |
| 3 | Intentionally inert structural parameters (`source="runtime"` at call sites) | PR 7 | §4.2 binding pair + `test_call_site_source_value_is_inert` |
| 4 | Always-present `fixture_id` field on observation records | PR 7 | Builder dict structure + `test_scope_inactive_persists_runtime` |
| 5 | Nested-not-unconditional synthesis form in reader | PR 7 | §5.5 binding pair + `test_mixed_legacy_and_contemporary_records` |
| 6 | Inline I-6 wrapper duplication in `_persist_expectation_record` | PR 7 | Inline pattern + Step 8 spec |
| **7** | **Companion records as truth-partitioning** | **PR 8** | **Gate 2 §4.4 + module docstring + schema validator** |
| **8** | **`emit_seed_expectation` as semantics-not-topology** | **PR 8** | **Helper docstring + Gate 2 §5.3 + Layer 2** |

Promotion to `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` remains
gated on at-least-one-more-reliability-phase independent
corroboration (per PR 7 framing §6). PR 8's two contributions
further corroborate; if a third Gate 2 PR (or a future reliability
phase) surfaces additional members under genuinely independent
conditions, promotion is unlocked.

---

## 7. Non-acquisition commitments

### 7.1 PR 8 explicitly does NOT (PR 8-specific commitments)

1. **Seed chain-step.** `forge_bridge/console/_step.py:233` is not
   driven by any PR 8 surface. Carrier #15 governs. The driver's
   test suite asserts only `chat_handler` is invoked (mechanically
   verified — see PR 8 spec for the assertion shape).

2. **Ship fixtures.** PR 8 ships ZERO concrete seed fixtures. The
   driver function is callable; PR 9 calls it with concrete
   fixtures. PR 8's tests construct minimal-shape fixture data
   inline (via `base_expectation_args`) — not as a fixture format
   or fixture-loading surface.

3. **Ship integration tests.** End-to-end tests demonstrating
   observation + expectation composition under real seeded
   execution are PR 9's domain. PR 8's tests are unit-shaped:
   helper signature validation, driver invocation path
   verification, Layer 1/2 extension verification, schema
   validator extension verification.

4. **Promote `emit_seed_expectation` or `drive_seed_fixture` to
   `forge_bridge.__all__`.** Per §5.6 deferral. Adding to
   `__all__` inside a PR 8 cleanup PR is rejected at the spec
   layer.

5. **Modify `_capture.py`, `_schema.py` source-class validation,
   or `_sources.py`.** PR 7's deliverables are locked. PR 8 only
   extends `_schema.py`'s expectation-record validator branch
   (per `_schema.py:225–228` inline comment) — and that extension
   is additive (adds required-keys check), not a modification
   of existing observation-record validation.

6. **Touch the Layer 3 lint.** `test_pr6_visual_asymmetry.py`
   ships unchanged. Layer 3's discovery walk finds calls to
   `emit_divergence_capture` only; PR 8 introduces no new
   `emit_divergence_capture` call sites, so the lint's input
   set is unchanged.

### 7.2 Inherited Gate 2 + PR 7 non-acquisition commitments

PR 8 also inherits and preserves:

- Gate 2 framing §7's six commitments (don't touch Layer 3 lint,
  don't bypass live arbitration, don't author expectation through
  observation helper, don't extend Layer 3 to expectation
  emission, don't modify env-gate, don't collapse contextual
  provenance into arbitration).
- PR 7 framing §7's seven commitments preserve unchanged.
- PR 7 spec §7's phase-end-conditions rejection table — PR 8 may
  not propose any of those mutations (refactor `_persist_expectation_record`
  + `emit_divergence_capture` into a shared writer; remove the
  authority pre-check; surface a nested-scope token from
  `seed_dispatch_scope`; promote PR 7 surfaces to `__all__`;
  backfill or rewrite legacy records; bump `SCHEMA_VERSION`;
  add a third `record_kind` value; add a third `KNOWN_SOURCE_VALUES`
  entry).

### 7.3 What PR 8 deliberately does NOT decide

Four ontological questions surface from carrier #15's chain-step
deferral. PR 8 explicitly leaves all four open. Each requires the
dedicated framing pass carrier #15 anchors:

1. **Does one expectation target one observation surface or
   multiple?** PR 8's expectation record has one `fixture_id` and
   one `expected_narrow` — implicitly single-surface. Whether a
   single fixture should produce expectations for both the
   chat-handler surface and the chain-step surface (and how
   `expected_narrow` would differ between them) is not decided.

2. **Does `fixture_id` identify a logical prompt or a specific
   arbitration surface?** PR 8's `fixture_id` is a string with no
   structural commitment. Whether two records carrying the same
   `fixture_id` against different surfaces represent "the same
   fixture exercised twice" or "two separate fixtures" is not
   decided. Gate 4 will need this answer; PR 8 does not provide
   it.

3. **Is cross-surface divergence meaningful or noise?** If a
   fixture's `expected_narrow` matches the chat-handler's actual
   narrowing decision but the chain-step's narrowing decision
   differs, is that a divergence Gate 4 should report or normal
   surface asymmetry? Not decided.

4. **Does Gate 4 compare within surfaces or across them?** The
   comparator's partition strategy — fixture-keyed joins
   vs. fixture-plus-surface-keyed joins — depends on questions
   1–3. Not decided.

These are supporting explanatory prose, not carriers. Carrier #15
is the load-bearing protection; the four questions are the
*content* of the decision deferral.

---

## 8. Layer 1 / Layer 2 / Layer 3 implications

### 8.1 Layer 1 — `_ALLOWLIST` mechanical extension

`tests/corpus/test_pr3_discipline.py::_ALLOWLIST` extends with:

- `forge_bridge/corpus/_seed.py` — the seed driver + expectation
  helper module.

Both the new file and its containing package (`forge_bridge.corpus`)
are inside `forge_bridge/corpus/`, so the locality property holds.
The allowlist semantics are unchanged: only files inside the
corpus package + the explicit allowlist may import from
`forge_bridge.corpus`.

`_sources.py` was admitted by structural location at PR 7 (per
§4.5 spec amendment); `_seed.py` is admitted similarly — by
structural location, no `_ALLOWLIST` extension is technically
needed for files inside `corpus/`. The Layer 1 test admits any
file in the `corpus/` subtree without name-based allowlist
extension.

**Action at PR 8 implementation:** verify `_seed.py` is admitted
by the existing structural-location check (mirrors PR 7 Step 2's
discipline-boundary verification). No `_ALLOWLIST` text changes
required.

### 8.2 Layer 2 — `_PERMITTED_CORPUS_IMPORTS` extension

`tests/corpus/test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS`
extends with exactly one entry:

```python
"forge_bridge.corpus._seed": frozenset({
    "seed_dispatch_scope",
    "_persist_expectation_record",
}),
```

`_seed.py` may import ONLY these two symbols from corpus. The
participation-creep posture per Gate 2 framing §8.2:

`_seed.py` is **not** permitted to import:
- `emit_divergence_capture` (the observation helper — wrong
  authority surface).
- Low-level builder/writer surfaces (`_build_capture_record`,
  `_serialize_line`, `_make_header`, `_resolve_corpus_dir`, etc.)
  — persistence topology is owned by dedicated persistence
  helpers, not by the seed driver. This is the mechanical
  enforcement of cleanup-pressure class member #8.
- Any read / analysis surfaces (`reader.py`, the future Gate 4
  comparator module).
- `_sources.py` directly (the source-class governance constant
  is consumed inside `_capture.py`'s resolution path and
  `_schema.py`'s validator; `_seed.py` neither resolves source
  values nor validates records directly).

The Layer 2 test (`test_pr4_participation_creep.py`) fires if
`_seed.py` imports any unpermitted symbol. The two-symbol
allowlist is the bright-line participation contract.

### 8.3 Layer 3 — unchanged

`test_pr6_visual_asymmetry.py` ships unchanged into PR 8. The
lint's discovery walk (`_find_emit_call_sites`) finds calls to
`emit_divergence_capture` only. PR 8 introduces zero new
`emit_divergence_capture` call sites. `emit_seed_expectation` and
`drive_seed_fixture` are not in the lint's discovery scope (per
Gate 2 framing §8.3 binding decision).

Verification: PR 8 spec includes a regression assertion that
`pytest tests/corpus/test_pr6_visual_asymmetry.py` passes 17/17
unchanged after `_seed.py` lands.

---

## 9. Phase-end conditions for PR 8

| Trigger | Response |
|---|---|
| `_seed.py` ships with two helpers (driver + expectation) + 15 carriers + binding clarification verbatim in module docstring + Layer 1 admission verified + Layer 2 extension lands with two-symbol allowlist + schema validator's expectation-branch extends with three required keys + `base_expectation_args` test helper lands + new test module passes + Layer 3 lint passes unchanged + PR 4/5/7 integration tests pass unchanged + carrier #15 travels verbatim into PR 8 commit message body | PR 8 closes; PR 9 framing/spec drafting begins. |
| `test_pr6_visual_asymmetry.py` regresses against the post-PR-8 codebase | Hard CI failure; Layer 3 lint has been touched accidentally or `_seed.py` has begun introducing `emit_divergence_capture` call sites. Reject at CI; review surfaces the structural violation. |
| PR 8 attempts to add chain-step driving | Rejected at the spec layer per carrier #15. Cross-surface expectation semantics require a dedicated framing pass before implementation proceeds. |
| PR 8 attempts to ship concrete fixtures | Rejected at the spec layer per §7.1 commitment #2. Fixtures land at PR 9; PR 8 ships the driver seam only. |
| PR 8 attempts to add `list[SeedFixture]` support, a fixture iterator, or any fixture-orchestration scaffolding to `drive_seed_fixture` | Rejected at the spec layer per §5.5 + Gate 2 framing §5.7. The one-fixture/one-call shape is carrying architectural weight — it scopes PR 8 as "ships the seam, not the loop." Fixture iteration / corpus orchestration is PR 9's domain. Premature iteration scaffolding inside PR 8 pulls PR 9 concerns downward and erodes the staircase discipline; the ergonomic gain ("while we're here, let's just add list support") is exactly the cleanup-pressure shape this row exists to reject. |
| PR 8 attempts to ship integration tests | Rejected at the spec layer per §7.1 commitment #3. End-to-end tests are PR 9's domain. |
| PR 8 attempts to promote `emit_seed_expectation` or `drive_seed_fixture` to `forge_bridge.__all__` | Rejected at the spec layer per §5.6 + §7.1 commitment #4. The public-API decision is deferred to first concrete external consumer. |
| A future PR proposes to inline `_persist_expectation_record`'s body into `emit_seed_expectation` ("for symmetry with `emit_divergence_capture`") | Rejected at the spec layer per cleanup-pressure-resistance class member #8 + Gate 2 framing §5.3 binding decision. The helpers' asymmetry is structural; collapsing it erodes the three-authority-surface partitioning. |
| A future PR proposes to merge observation and expectation records into a single richer record per fixture | Rejected at the spec layer per cleanup-pressure-resistance class member #7 + Gate 2 framing §4.4. The truth-partitioning is the comparator's foundation; merging the records erodes Gate 4's architecture. |
| A future PR proposes to rename `drive_seed_fixture` to `drive_chat_handler_fixture` (or any surface-explicit name) without a framing artifact | Rejected at the spec layer per §5.5 + carrier #15. The generic name preserves option-space about how the future chain-step-seeding framing pass resolves the ontological questions; renaming forecloses that pass's authority. |
| A future PR proposes to add a fourth required field to expectation records inside a cleanup PR | Rejected at the spec layer per §5.3 minimum-viable lock. Expectation-record shape changes require framing-level review; Gate 4 will surface concrete needs at comparator-write time. |
| A future PR proposes to drive seed fixtures via HTTP instead of in-process | Rejected at the spec layer per §5.1 + carriers #3–6. The arbitration pipeline is the thing being measured; transport is incidental. |

---

## 10. Cross-references

- `A.5.3.2-PR7-CLOSE.md` (`b035c87`) — durable archival state PR 8
  inherits; §2 "what PR 8 inherits from PR 7"; §3 "what PR 8
  changes"; §1.2 cleanup-pressure-resistance class inventory (6
  members at PR 7 close; PR 8 grows to 8 per this framing §6); §5
  methodology observations (this framing inherits the close-
  authors-inheritance / framing-consumes-inheritance discipline
  per PR 7 close §5.6).
- `A.5.3.2-PR7-FRAMING.md` (`1c1e061`) — §6 cleanup-pressure-
  resistance class (introduced at PR 7; PR 8 contributes members
  #7 + #8 per this framing §6); §7 seven non-acquisition
  commitments (preserved into PR 8 per §7.2).
- `A.5.3.2-PR7-SPEC.md` (`84392d2`) — §4.2.4 `seed_dispatch_scope`;
  §4.2.6 `_persist_expectation_record` (the two symbols `_seed.py`
  may import); §7 phase-end conditions (rejection table preserved
  into PR 8 per §7.2).
- `A.5.3.2-GATE-2-FRAMING.md` (`ceac9b5`) — §3.4 three-authority-
  surface partitioning (PR 8 closes the third surface per §3.1);
  §4.1 Model A; §4.4 companion records (this framing §6.1 names
  the protection); §5.3 Q1.6 companion records + dedicated
  expectation helper locked (this framing §6.2 names the
  protection); §5.5 module siting; §5.7 PR 8 = boundary work;
  §6.1 carrier #14; §6.2 binding framing clarification; §7 six
  non-acquisition commitments (inherited per §7.2); §8.1/§8.2/§8.3
  Layer extension specifications (operationalized per §8).
- `A.5.3.2-PR6-CLOSE.md` (`9168df7`) — §1.3 truth-vs-mechanism
  distinction (informs `_seed.py` module docstring governance
  shape); §5 methodology shape (close artifact pattern PR 8 close
  will follow).
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  unchanged by PR 8 (Layer 3 lint enforcement).
- `forge_bridge/corpus/_capture.py::seed_dispatch_scope` — consumed
  by `drive_seed_fixture` (one of two Layer 2 admitted symbols).
- `forge_bridge/corpus/_capture.py::_persist_expectation_record` —
  consumed by `emit_seed_expectation` (the other Layer 2 admitted
  symbol); the PR 7 seam.
- `forge_bridge/corpus/_schema.py::validate_capture_record` — PR 8
  extends the `record_kind == "expectation"` branch with required-
  keys check (per `_schema.py:225-228` inline comment left by
  PR 7).
- `forge_bridge/corpus/_sources.py::KNOWN_SOURCE_VALUES` — not
  directly consumed by `_seed.py` (per Layer 2 exclusion); but the
  resolution path inside `emit_divergence_capture` consults it when
  the driver opens `seed_dispatch_scope`, emitting `source="seed"`
  observation records mid-fixture-invocation.
- `forge_bridge/corpus/_seed.py` (planned, PR 8) — seed driver +
  `emit_seed_expectation`.
- `forge_bridge/console/handlers.py::chat_handler` — the single
  call site PR 8's driver invokes. PR 8 makes no modifications to
  this file.
- `forge_bridge/console/_step.py::chain_step` — NOT invoked by
  PR 8's driver. Carrier #15 governs.
- `tests/corpus/test_pr3_discipline.py::_ALLOWLIST` — Layer 1;
  unchanged at PR 8 (structural-location admission per §4.5 PR 7
  spec amendment).
- `tests/corpus/test_pr4_participation_creep.py::_PERMITTED_CORPUS_IMPORTS`
  — Layer 2; extends with one entry per §8.2.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3; unchanged
  by PR 8; regression-asserted at PR 8 close.
- `tests/corpus/_pr3_helpers.py` — extends with `base_expectation_args()`
  per §4.4.
- `tests/corpus/test_pr8_seed_surface.py` (planned, PR 8) — new
  test module exercising the helper + driver + Layer 1/2 extensions
  + schema validator extension.
- `project_pr8_base_expectation_args.md` (local memory) — flagged
  expectation; consumed at this framing per §4.4.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion-
  candidate methodology seed; PR 8's two cleanup-pressure-
  resistance class additions further corroborate; promotion
  remains gated on at-least-one-more-reliability-phase
  independent corroboration.

---

PR 8 framing locks here. PR 8 spec drafts at the next session
boundary; PR 8 implementation derives from that spec per the
boundary-work cadence (full three-round review across the entire
PR, mirroring PR 4 + PR 5's cadence).

Resumption from this framing opens at PR 8 spec drafting. The
spec articulates: module surface (§4 detail); test plan (risks →
named tests, per PR 7 spec §3 shape); implementation step
sequence (cadence-matches-work-depth — likely 4–6 steps; final
ordering at spec drafting); phase-end conditions specific to
implementation (regression contracts, count deltas, atomic-merge
discipline).
