# A.5.3.2 — Gate 1 spec (Layer 1 capture only)

**Status:** drafted 2026-05-06. First of three sequenced gates from the
instrument contract's MVP sequencing block.

**Predecessors (binding):**
- `A.5.3.2-FRAMING.md` (commits `fe016c0` + `4d786a6`) — phase shape, objective lock, threat articulation, four-case + AMBIGUOUS classification.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` (commits `5b22c59` + `2269f2f`) — instrument shape, structural invariants, exclusions, six confirmed decisions, MVP sequencing.

**Successors (NOT this spec):**
- Gate 2 spec — seed corpus drive (`tests/corpus_seed_prompts.yaml` + fixture-driven coverage of taxonomy cells).
- Gate 3 spec — runtime capture enablement on operator workstation.
- Gate 4 spec (later) — comparator + Layer 2 implementation.

This spec sequences the Gate 1 implementation only. Gate 1 ships
**Layer 1 capture only** — no comparator, no Layer 2 schema, no LLM
round-trips, no offline pipeline. The full instrument shape is locked
in the contract; Gate 1 is the first of the four phased landings.

---

## 0. Crystallizing sentence (verbatim — load-bearing)

> **Capture is emitted after arbitration decisions are finalized and
> must not structurally participate in the arbitration pipeline.**

This sentence lands verbatim in two places:

1. **§5 of this spec** as the header of the capture-invocation
   contract.
2. **`forge_bridge/corpus/_capture.py` module header docstring** —
   the first thing a future contributor reads when they open the
   capture module.

It is the durable carrier of architectural intent. Any reader who
encounters the capture code without reading the full contract should
encounter this sentence first. It travels.

---

## 1. Scope — what Gate 1 ships

In scope:

- A new package `forge_bridge/corpus/` with the modules listed in §3.
- The `emit_divergence_capture(...)` public helper. Fire-and-forget;
  returns `None`. Failure is logged at WARNING and never propagated.
- The `divergence_capture_enabled()` env-var gate
  (`FORGE_BRIDGE_DIVERGENCE_CAPTURE=1`).
- Capture invocation at the two arbitration call sites: chat handler
  and chain-step executor.
- Layer 1 record schema (per contract §3) — builder + JSONL writer +
  schema validator.
- Topology snapshot helper (reuses existing reachability cache;
  extends to surface LLM-provider availability per contract §3).
- Identity-hash helpers (narrower version hash, registered-tools
  snapshot hash, daemon git SHA).
- A reader stub (`forge_bridge.corpus.reader`) that validates header
  records and iterates Layer 1 records — sufficient for Gate 1
  verification, expanded in later gates for analytics consumption.
- Regression tests covering: capture emission at both call sites,
  capture-failure invisibility to arbitration, schema validity of
  emitted records, identity-hash stability across runs, env-var gate
  honored in both directions.

Out of scope (explicit — defer to later gates / spec):

- Comparator implementation (Gate 4).
- Layer 2 record schema in code (the schema is contractually defined;
  Gate 4 implements the writer).
- Seed corpus content (`tests/corpus_seed_prompts.yaml` is a Gate 2
  artifact). Gate 1's regression tests use ad-hoc inline prompts.
- Console-script entry for the comparator (Gate 4).
- Analytics queries / dashboards (out of scope entirely per contract
  §11).
- Sampling / fractional capture (decision #2 — binary v0).
- Cross-provider replay routing (decision #3 cites
  `SEED-CROSS-PROVIDER-FALLBACK-V1.5` for that territory).

---

## 2. Verification (Gate 1 success criteria)

Per the contract's MVP sequencing block, Gate 1's verification is
**schema validation + required-fields completeness**:

1. Every emitted Layer 1 record passes the §3 schema validator.
2. Every required field is populated (no missing keys, no `null`
   where the contract requires a value).
3. `source` field is correct: `"fixture"` from the test fixture path,
   `"runtime"` from the env-var-gated runtime probe path. No record
   emitted with the wrong source.
4. Identity-hash fields are populated and stable across runs against
   an unchanged tree (the same daemon SHA, same `_tool_filter.py`
   contents, same registered tool set must produce identical hashes).
5. The reader stub round-trips: `read(write(record)) == record`
   modulo header records.
6. Env-var gate honors both directions: with
   `FORGE_BRIDGE_DIVERGENCE_CAPTURE` unset or `0`, no capture is
   written; with `=1`, every arbitration emits one capture.

The verification deliberately does NOT require:
- A working comparator (Gate 4).
- Real LLM reachability (Gate 3 onwards).
- A populated seed corpus (Gate 2).
- Any analytic query against the corpus.

---

## 3. Module layout

```
forge_bridge/corpus/
├── __init__.py        — public API surface
├── _capture.py        — emit_divergence_capture + record builder + writer
├── _schema.py         — schema version constant + validator
├── _topology.py       — topology snapshot helper
├── _identity.py       — narrower / tools / daemon identity hashes
└── reader.py          — Layer 1 reader (header validation + record iter)
```

### 3.1 Public API surface (`__init__.py`)

Exports only what call sites need:

```python
from forge_bridge.corpus._capture import (
    divergence_capture_enabled,
    emit_divergence_capture,
)
from forge_bridge.corpus.reader import read_capture_file

__all__ = [
    "divergence_capture_enabled",
    "emit_divergence_capture",
    "read_capture_file",
]
```

Every other symbol in the package is private (`_capture`, `_schema`,
`_topology`, `_identity` are leading-underscore modules). The reader
is public because external analytic consumers (Gate 2+ tests, the
eventual comparator) need it.

### 3.2 `_capture.py` module header

The module docstring opens with the crystallizing sentence verbatim.
Full module docstring:

```python
"""forge_bridge.corpus._capture — Layer 1 divergence corpus capture.

Capture is emitted after arbitration decisions are finalized and
must not structurally participate in the arbitration pipeline.

This module implements the runtime probe (env-var-gated) and the
test-fixture path that emits Layer 1 records per the A.5.3.2
instrument contract. The contract's structural invariants
(`A.5.3.2-INSTRUMENT-CONTRACT.md` §2.2) are enforced here:

  - I-1: append-only writer; never mutates existing records.
  - I-2: records carry observations only; no outcome labels.
  - I-3: this module is imported by daemon code paths but only
         performs disk writes — no LLM calls, no comparator logic.

See `A.5.3.2-INSTRUMENT-CONTRACT.md` §3 for the canonical record
shape and §5 for the capture-invocation contract this module
implements.
"""
```

### 3.3 `_topology.py`

Wraps the existing `_get_backend_reachability` cache from
`_tool_filter.py` and extends to surface LLM-provider availability.
Reads the LLM-router config to determine which providers are
configured (without calling them); marks `reachable: true` only when
the relevant probe has confirmed reachability within the cache TTL.

This module is the chokepoint for the contract's "topology as
first-class captured data" requirement (§3 of contract). New
backends added to the reachability filter MUST extend this module's
output; the schema validator will reject records whose topology
block doesn't match the registered backends.

### 3.4 `_identity.py`

Three functions, each returning a hex-encoded sha256 string:

- `narrower_version_hash()` — sha256 of `_tool_filter.py` source.
  Computed once at module-import time and cached; the file does not
  change at runtime within a process.
- `registered_tools_snapshot_hash(tools)` — sha256 of a normalized
  representation of the sorted list of registered tool names plus
  their argument schemas. The normalization rules (key ordering,
  whitespace, schema field selection) are documented as constants
  in this module so the algorithm is reviewable rather than implicit.
- `daemon_git_sha()` — full git sha of the running daemon's source
  tree. Read once at module-import; if the daemon is running outside
  a git checkout (unlikely but possible), returns the literal string
  `"non-git"`.

### 3.5 `reader.py`

Stub Gate 1 implementation:

- `read_capture_file(path: Path) -> Iterator[dict]` — opens the
  file, asserts the header record matches the expected
  `schema_version`, yields each subsequent record as a parsed dict.
- Schema-version mismatch raises `SchemaVersionMismatch` with the
  remediation message specified in contract §9.

Layer 2 reader functions are deferred to Gate 4.

---

## 4. The two arbitration call sites

The capture invocation lands at exactly two places:

1. `forge_bridge/console/handlers.py` — the chat handler's narrowing
   path (the existing call sequence `filter_tools_by_message` →
   `deterministic_narrow`).
2. `forge_bridge/console/_step.py` — the chain-step executor's
   narrowing path (same call sequence, in `execute_chain_step`).

Both sites get an inline capture invocation per the pattern in §5.
Both sites are covered by the regression test plan in §7.

---

## 5. Capture invocation contract

> **Capture is emitted after arbitration decisions are finalized and
> must not structurally participate in the arbitration pipeline.**

### 5.1 The visual-asymmetry pattern (binding)

The capture call must read as a **separate act** from arbitration,
not a fused operation. The canonical insertion pattern:

```python
filtered = filter_tools_by_message(tools, last_user_text)
narrowed = deterministic_narrow(filtered, last_user_text)

if divergence_capture_enabled():
    emit_divergence_capture(
        prompt=last_user_text,
        candidate_set_post_reachability=tools,
        candidate_set_post_pr14=filtered,
        narrower_decision=narrowed,
        # ... remaining contract §3 fields ...
        source="runtime",
    )
```

The blank line and the explicit conditional are part of the spec's
surface, not style preference:

- **Blank line.** Visually separates arbitration (above) from
  observation (below). A future contributor reading the call site
  perceives "first the narrower decided, then optionally we
  recorded what happened" — not "the narrower decision and the
  recording are one operation."
- **Explicit conditional.** The `if divergence_capture_enabled():`
  guard reads as observation being optional and gated. The
  alternative — `emit_divergence_capture(...)` calling
  `divergence_capture_enabled()` internally and silently no-op'ing
  when off — would visually fuse arbitration and observation,
  hiding the gate inside the helper.

**Architectural drift begins at the reading level before it appears
in behavior.** The visual asymmetry is what makes the architectural
boundary visible at the call site without requiring the reader to
go look it up. Future contributors who attempt to "tidy up" by
folding the two arbitration operations into a single call (with
capture as a side effect) are eroding the asymmetry — that is a
spec violation, not a style preference. The two regression tests
in §7 do not catch this kind of drift; review of any change to
either call site must explicitly check that the visual pattern is
preserved.

### 5.2 Helper signature

```python
def emit_divergence_capture(
    *,
    prompt: str,
    candidate_set_post_reachability: list[Any],
    candidate_set_post_pr14: list[Any],
    narrower_decision: list[Any],
    pr20_fired: bool,
    collapse_occurred: bool,
    ambiguity_state: str,
    narrower_latency_ms: float,
    source: str,
) -> None:
    """Fire-and-forget Layer 1 capture. See module docstring."""
```

Returns `None`. All failures are caught and logged at WARNING; no
exception ever propagates out of the helper. Disk-write errors,
schema-validator errors, identity-hash computation errors — every
failure mode is captured and silenced from the call site's
perspective. The contract's I-1 (append-only) makes this safe: a
failed write doesn't corrupt prior records.

For testing, `_capture.py` exposes a private
`_build_capture_record(...)` that constructs and returns the record
dict without writing it. Tests import it directly. Production code
never imports it.

### 5.3 Architecturally prohibited alternatives (named, not "alternatives we didn't pick")

The following patterns are **architecturally prohibited**, not
"options we chose against." Naming the prohibition here means future
contributors find the rationale already addressed:

**Prohibited: observer-registration patterns inside the narrowing
subsystem.** A pattern like `_tool_filter.register_observer(callback)`
where the corpus module registers itself and the narrower fires the
callback on every decision would (a) introduce a registry pattern in
`_tool_filter` that grows under contributor pressure ("just one more
observer"), (b) couple the narrower's call surface to observation
concerns it should know nothing about, and (c) hide the capture
invocation from the arbitration call site, eroding the visual
asymmetry §5.1 requires.

**The narrowing subsystem (`_tool_filter.py`) MUST NOT export an
observer/listener/callback registration API.** A future PR
proposing this pattern is rejected at the spec layer. The prohibition
is named here so the rationale travels.

**Prohibited: fused helper that performs both narrowing operations
plus capture in one call.** A helper like
`narrow_with_capture(tools, message)` that wraps
`filter_tools_by_message + deterministic_narrow + emit_divergence_capture`
would fuse arbitration and observation visually, eroding the §5.1
visual asymmetry. The two arbitration operations remain explicit
calls at each site; capture is the third explicit, gated call.

**Prohibited: capture invocation BEFORE the arbitration decision
is finalized.** Per the crystallizing sentence: emission happens
after `narrowed` is bound. Any pattern that captures partial state
during arbitration (e.g., emitting after `filter_tools_by_message`
but before `deterministic_narrow`) violates the structural
contract — capture is a record OF the decision, not an observer
INSIDE the decision pipeline.

---

## 6. Env-var gate semantics

`FORGE_BRIDGE_DIVERGENCE_CAPTURE`:

- Unset, `""`, `"0"`, `"false"`, `"no"` (case-insensitive) → disabled.
  `divergence_capture_enabled()` returns `False`. No capture written.
- `"1"`, `"true"`, `"yes"` (case-insensitive) → enabled.
  `divergence_capture_enabled()` returns `True`.
- Any other value → disabled, with a one-time WARNING logged at
  daemon startup. Avoids silent enablement on typo'd values.

The gate is read at call time, not cached, so toggling it via
SIGHUP-style env reload would take effect immediately — though no
such reload is in scope here. Daemon restart is the supported way
to flip the gate.

---

## 7. Regression test plan

Five new test files, each scoped to one contract surface:

### 7.1 `tests/corpus/test_capture_emission_chat_handler.py`

Drive the chat handler through a representative prompt with the
env var enabled. Assert:
- exactly one capture record was emitted to the test-scoped
  capture file
- the record validates against the §3 schema
- `source == "fixture"`
- `narrower_decision` matches the actual narrower output for the
  prompt
- topology block matches the test's mocked reachability state
- identity hashes are populated and non-empty

### 7.2 `tests/corpus/test_capture_emission_chain_step.py`

Same as 7.1 but driven through `execute_chain_step` instead of the
chat handler. Asserts capture parity at the second call site.

### 7.3 `tests/corpus/test_capture_failure_invisibility.py`

Mock the JSONL writer to raise on every call. Drive both arbitration
paths. Assert:
- arbitration completes successfully (the request returns a
  well-formed response)
- a WARNING was logged for each capture failure
- no exception propagated from `emit_divergence_capture`
- the live response envelope is byte-identical to the same path
  with capture disabled

This is the contract §9 failure-mode for "Layer 1 write fails" —
the regression test pins it.

### 7.4 `tests/corpus/test_env_var_gate.py`

Parametrized over the env var's accepted truthy/falsy values. With
the gate disabled, `emit_divergence_capture` is never called from
either site (assert via patch on the function); with the gate
enabled, it is called exactly once per arbitration. Also covers
the typo'd-value case (warns, treats as disabled).

### 7.5 `tests/corpus/test_identity_hash_stability.py`

Computes the three identity hashes twice in the same process. Asserts
identical results both calls. Also asserts the schema validator
rejects records whose identity block has missing or empty hashes.

This is a regression guard against the identity-hash computation
becoming non-deterministic (e.g., if a future PR adds a timestamp
into the normalized representation).

### 7.6 (Optional, recommended) `tests/corpus/test_visual_asymmetry_lint.py`

A grep-based test asserting that both call sites contain the
canonical pattern: a blank line followed by `if
divergence_capture_enabled():` followed by `emit_divergence_capture(`.
Crude but durable; catches "tidying up" PRs at CI time. Marked
optional in this spec — the visual-asymmetry contract is enforced
primarily at code-review, this test is a backstop.

---

## 8. Observability + operator notes

- A single WARNING log line per capture failure, formatted to
  surface (a) the call site (chat or chain), (b) the failure mode
  (write error, schema validation error, etc.), (c) the prompt
  prefix (first 32 chars, no full prompt — privacy posture per
  contract §8.4 and the orientation principle in §1).
- One INFO log line per daemon startup naming whether the gate is
  enabled and the corpus directory path. Operators can confirm
  state without grepping env.
- Disk-usage observation is out of scope; the contract's retention
  soft trigger (§10.4 of contract) is operator-driven, not
  automated.

---

## 9. Implementation sequence

The plan, as a sequenced PR series:

1. **PR 1 — Package skeleton.** `forge_bridge/corpus/__init__.py`,
   the four private modules with stubs, `reader.py` stub. No call
   site changes yet. Schema validator works against hand-written
   test records. (1 file under test from 7.1's perspective is
   sufficient as a smoke-level verification.)
2. **PR 2 — Identity + topology helpers.** Implement `_identity.py`
   and `_topology.py` against their existing dependencies. Test 7.5
   lands here.
3. **PR 3 — Capture builder + writer.** Implement
   `_build_capture_record` and `emit_divergence_capture`.
   Hand-driven schema-validity test lands here.
4. **PR 4 — Chat handler call site.** Apply the §5.1 pattern at
   `handlers.py`. Test 7.1 + 7.4 + 7.3-chat-half land here.
5. **PR 5 — Chain step call site.** Apply the §5.1 pattern at
   `_step.py`. Test 7.2 + 7.3-chain-half land here.
6. **PR 6 — (optional) lint backstop.** Test 7.6 if we choose to
   land it.

Each PR is mergeable independently because (a) the package surface
is non-breaking when not called, (b) the env var defaults to
disabled, and (c) the call sites' behavior is unchanged when the
gate is off.

---

## 10. Out of scope for Gate 1 — what later gates own

| Concern | Owned by |
|---------|----------|
| Seed corpus YAML content + fixture-driven coverage | Gate 2 |
| Runtime capture enablement on operator workstation | Gate 3 |
| Comparator implementation | Gate 4 |
| Layer 2 record schema in code | Gate 4 |
| Console-script entry for comparator | Gate 4 |
| Analytics queries / dashboards | out of scope entirely (contract §11) |

A future contributor whose PR changes scope from "Gate 1 closure"
to "include Gate 2 / 3 / 4 work" should be redirected here.

---

## 11. Phase-end conditions for Gate 1

| Trigger | Response |
|---------|----------|
| All §2 verification criteria pass + all §7 tests green | Gate 1 closes; Gate 2 spec drafts. |
| §7.6 visual-asymmetry lint regresses on a future PR | The PR is rejected at CI; review surfaces the §5.1 contract violation. |
| The schema validator rejects records emitted from production | Gate 1 has shipped a defect; treat as a v1.5 hotfix. The contract's I-1 means the records are still safe to retain (no corruption). |
| A future PR proposes an observer-registration pattern in `_tool_filter` | Rejected at the spec layer per §5.3. The rationale is in this spec; no further re-litigation. |
| A future PR proposes a fused `narrow_with_capture` helper | Same as above. |

---

## Cross-references

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, six confirmed
  decisions, MVP sequencing, exclusions.
- `docs/learnings/2026-05-06-interlocking-architecture.md` — the
  interlock check this spec inherits.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` § 2.2 — the
  interlock-vs-coexist character observation.
