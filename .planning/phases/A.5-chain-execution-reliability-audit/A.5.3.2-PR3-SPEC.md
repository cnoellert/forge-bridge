# A.5.3.2 PR 3 — Spec (capture builder + writer + reader)

**Status:** drafted 2026-05-07. Derived from `A.5.3.2-PR3-FRAMING.md`
(commit `68cb24d`). The framing is the binding pre-spec contract; this
spec is the implementation contract derived from it.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, six confirmed
  decisions, structural invariants.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs.
- `A.5.3.2-PR3-FRAMING.md` — PR 3 pressure profile, real job, success
  condition, five preserved constraints carried verbatim.
- `A.5.3.2 PR 1` (commit `ee019be`) — package skeleton + schema + env
  gate.
- `A.5.3.2 PR 2` (commit `a33c135`) — topology snapshot + identity
  hashes.

**Successor (NOT this spec):** PR 4 (chat-handler call site) and PR 5
(chain-step call site). Call-site integration remains future work;
this spec ships only the persistence layer.

---

## 0. Crystallizing sentences (verbatim — load-bearing)

Six sentences travel verbatim from this spec into the writer
module's docstring, the reader module's docstring, and the eventual
PR 3 commit message. They are the durable carriers of architectural
intent for PR 3, grouped by the architectural layer each governs.

**From the framing — phase-level architectural intent:**

> **Preserve Layer 1 truthfulness while introducing persistence.**

> **Once persistence exists, future interpretation layers begin
> inheriting authority from it automatically. That is why PR 3 is
> dangerous: not because it writes data, but because it creates
> institutional memory.**

**From §5 of this spec — orthogonal-truth-surfaces framing
(builder/writer signature constraint):**

> **The registered tool set is deployment identity, not runtime
> topology. Candidate sets are topology-sensitive operational
> subsets and are therefore insufficient inputs for
> deployment-stable identity hashing.**

> **The builder receives all three as explicit inputs. The builder
> does not discover them.**

**From §6.5 of this spec — persistence-layer architectural
property:**

> **Corpus existence implies at least one truthful persisted
> capture.**

> **The architecture should not introduce corruption windows larger
> than the platform already imposes.**

**From §9 of this spec — corruption-locality carrier (verbatim,
user framing 2026-05-07):**

> **Otherwise persistence silently becomes fragility.**

A reader who encounters the writer code without reading the full
spec should encounter these sentences first. The framing pair
establishes the pressure profile that determines scope; the §5 pair
establishes the input-parameter discipline (deployment vs. runtime
vs. arbitration as orthogonal truth surfaces); the §6.5 pair
establishes the architectural ceiling for the persistence layer
(not WAL semantics, not transactional durability — just "no
self-introduced corruption windows"); the §9 sentence is the
read-side complement that completes the writer/reader symmetry.

---

## 1. Real job + success condition (verbatim from framing)

**Real job:** *"Preserve Layer 1 truthfulness while introducing
persistence."* The writer is incidental to the job. The job is
preserving truthfulness across the persistence boundary that PR 3
introduces.

**Success condition:** *"Truthful records now persist. Nothing
more."*

That is the entire success condition. Not "the corpus is
observable," not "the corpus is queryable," not "the corpus is
useful." Just: truthful records persist.

---

## 2. Scope

In scope:

- **Capture builder (`_build_capture_record`)** — turns the call
  site's arguments into a Layer 1 record dict, including topology
  snapshot (PR 2) and identity hashes (PR 2). Private helper, exposed
  for testing only.
- **JSONL writer (`emit_divergence_capture`)** — fills the PR 1 stub.
  Validates → serializes → appends → flushes → returns. Nothing else.
- **Reader (`read_capture_file`)** — fills the PR 1 stub. Opens a
  Layer 1 file, validates the header record's `schema_version`,
  yields each subsequent record as a parsed dict. Skips malformed
  records with a WARNING; never aborts iteration.
- **On-disk format** — header record + record-per-line per contract
  §7. File path + naming per contract §7.
- **Regression tests** — seven invariants, the round-trip
  verification, the failure-invisibility matrix (write side), the
  corruption-locality matrix (read side), and the discipline grep
  test.

Out of scope (defer to later PRs / gates / discard entirely):

- **Call-site integration** — PR 4 (chat handler) and PR 5 (chain
  step). The asymmetry — writer real but uncalled — is the
  load-bearing PR 3 property (see §10).
- **Replay tooling, filtering, comparisons, dashboards, drift
  analysis, prompt tagging, summaries** — framing constraint 5; resist
  all of it. Those are Gate 4 / later phases / out of scope entirely.
- **Deduplication, normalization, compaction, indexing of any kind** —
  framing constraint 1. The writer is mechanically dumb.
- **Migration tooling for `schema_version` bumps** — defer until
  needed. Per contract §7, schema migrations write new files; PR 3
  ships no migration logic.
- **Layer 2 schema in code, comparator implementation, console-script
  entry** — Gate 4 (separate spec).
- **Sampling / fractional capture** — confirmed decision #2 in the
  contract; binary v0 only.

If the spec begins drifting toward "and let's also add X" where X is
on the resist-all-of-it list, **stop and re-scope.** That drift is
the named PR 3 failure mode (framing § "PR 3 still must not become
'the corpus system'").

---

## 3. The seven invariants — table with named test coverage

The four PR 2 invariants carry forward to PR 3 unchanged. PR 3 adds
three new invariants — two write-side (I-5, I-6) and one read-side
(I-7) — that make the existing four operational rather than
conceptual.

| # | Invariant | Source | Named test (this PR unless noted) |
|---|-----------|--------|-----------------------------------|
| **I-1** | **Descriptive, not evaluative.** Capture: reachable/unreachable, configured/available, identity/version, routing state. Do not capture: healthy, preferred, recommended, fallback-worthy. Evaluative fields propagate semantic weight that belongs in Layer 2. | PR 2 | `test_writer_emits_no_evaluative_fields` (PR 3) — asserts the emitted record dict has no key drawn from the evaluative-field denylist. PR 2's `test_pr2_topology.py` checks already cover the topology block; PR 3 extends the check to the full record. |
| **I-2** | **Observational, not semantic.** Identity hashes record state snapshots. Do not invent: compatibility grades, equivalence classes, drift scoring. Those are derived judgments for Layer 2's classifier. | PR 2 | `test_writer_emits_no_semantic_fields` (PR 3) — asserts the record has no key drawn from the semantic-field denylist. Companion to I-1's test. |
| **I-3** | **No lazy runtime side effects (in the writer).** The writer must not initialize providers, warm clients, allocate transports, touch arbitration state, spawn background tasks, or mutate caches into warm-state preparation. Capture observes existing state; capture never causes state. | PR 2-extended | `test_writer_no_lazy_side_effects` (PR 3) — asserts that calling `emit_divergence_capture` does not: open network sockets (`asyncio.open_connection`, `httpx`/`asyncpg` connection counts unchanged), spawn `asyncio.create_task`, mutate `forge_bridge.console._tool_filter._cache`, instantiate the LLM router. PR 2 covered topology + identity helpers; PR 3 covers the writer itself. |
| **I-4** | **Loud asymmetry preserved.** The persistence layer ships callable but uncalled — no production import path leads to it. The visual asymmetry (capture is a separate act from arbitration) lives at the call site, but the structural asymmetry (no production import) lives at the package boundary. | PR 2-extended | `test_zero_production_imports_outside_corpus` (PR 3) — grep-based: walks `forge_bridge/` excluding `forge_bridge/corpus/` and asserts zero matches for `from forge_bridge.corpus` / `import forge_bridge.corpus`. Same property held in PR 1 + PR 2; PR 3 preserves it through the writer becoming real. See §10. |
| **I-5** | **Append-only executable.** No rewrite path, no mutation path, no update API, no merge behavior, no overwrite semantics. The append-only invariant becomes operational rather than philosophical. | PR 3 (write) | `test_writer_uses_append_mode_only` — assert the writer opens files only with `mode="a"`/`"ab"`; `r+`, `w`, `w+`, `a+` never appear. `test_writer_no_mutation_api` — assert `forge_bridge.corpus._capture` exposes no public function whose name contains `update`/`mutate`/`rewrite`/`merge`/`overwrite`/`replace`. `test_writer_emit_appends_each_call` — emit N records, read back, assert N records present in input order; nothing was overwritten. |
| **I-6** | **Failure-invisibility under persistence failure.** Arbitration must remain unaffected if: disk full, invalid path, permission denied, serialization failure, partial write, lock contention, malformed runtime state. **Observation failure cannot become arbitration failure.** | PR 3 (write) | `test_failure_invisibility[<mode>]` — parametrized over the seven failure modes named in framing constraint 3. For each mode: mock the failure, call `emit_divergence_capture`, assert (a) returns `None`, (b) raises no exception, (c) logs at WARNING with structured detail, (d) the live arbitration return value (when integrated, simulated here via direct call) is unaffected. See §8. |
| **I-7** | **Reader corruption locality.** Malformed or partial records should: fail locally, remain individually skippable, never invalidate the corpus globally. A corrupted line must not poison earlier records, later records, corpus loading, or replay iteration. *"Otherwise persistence silently becomes fragility."* — verbatim from user framing 2026-05-07. The writer-side complement (§6.5 atomic-append discipline) minimizes corruption opportunity; I-7 localizes corruption that the platform nonetheless imposes. | PR 3 (read) | `test_reader_corruption_locality[<mode>]` — parametrized over malformation modes (truncated JSON, invalid UTF-8, schema-validation failure, empty/whitespace line). The canonical pattern: write valid line + malformed line + valid line; assert the reader yields exactly two records (lines 1 and 3), logs WARNING for the malformed line, and never raises during iteration. See §9. |

**Round-trip cross-cutting test (does not map to a single invariant
but is the strongest verification of writer/reader coupling):**

`test_round_trip` — for each of N representative records (built via
`_build_capture_record`), write to a fresh file via
`emit_divergence_capture`, read back via `read_capture_file`,
assert the yielded dict is byte-equal to the input dict. This test
is the operational verification that I-5 (append-only executable)
and the reader's parser agree on the on-disk format. See §4 for why
this test is the load-bearing reason writer + reader ship together.

---

## 4. Single-PR rationale — writer + reader together

Gate 1 spec §9 originally sequenced PR 3 as "capture builder +
writer," with the reader's real implementation absorbed into a later
step. The PR 3 framing pulled the reader forward into PR 3 scope.
This section documents why.

**Why the split was considered:**

- The writer is the dangerous half — it creates institutional memory
  (framing §"The architectural shift"). The reader is the safe half:
  read-only, no persistence consequences.
- Splitting would let the writer get focused review attention without
  reader-shape distractions.
- A staged landing reduces per-PR risk surface.

**Why the split was rejected:**

1. **Round-trip is the contract.** `read(write(record)) == record` is
   the strongest single verification that the writer's serialization
   and the reader's parser agree on the on-disk format. Splitting
   the writer and reader across PRs means PR 3's tests can only
   assert on bytes written to disk — necessary but insufficient. The
   coupling is precisely what we need to test, and the strongest
   test requires both halves.
2. **JSONL is a coupled format.** The header record's shape, the
   per-line encoding (UTF-8 + `\n`), the trailing-newline convention,
   the schema-version dispatch — every one of these is a writer/reader
   contract. Designing them in lockstep with round-trip as the
   verification produces cleaner contracts than designing the writer
   in isolation and discovering reader-side incompatibilities later.
3. **SchemaVersionMismatch + corruption-locality are reader-side
   properties that belong in PR 3.** The Gate 1 spec specifies that
   schema-version mismatch raises a structured error per contract §9.
   The user-added I-7 (corruption locality) is a reader-side property.
   Both are part of the persistence contract, and the persistence
   contract is what PR 3 ships. Deferring them to a later PR means
   PR 3 ships incomplete persistence.
4. **The reader is small.** ~50 lines: open file, parse header, yield
   records, skip malformed, log on warn. Pulling it forward costs
   little review attention. The writer remains the dominant review
   target.
5. **The framing already names the reader as in-scope.** "Reader
   implementation in `forge_bridge/corpus/reader.py` — replaces the
   PR 1 stub with a real implementation that opens Layer 1 files,
   validates the header, yields records." The decision was made at
   framing time; this section documents the rationale.

**Decision:** writer + reader land in a single PR (this PR 3). The
round-trip test is the load-bearing verification of the coupling.
A future contributor reviewing this PR who asks "should this have
been two PRs?" should be redirected here — the answer is no, and the
rationale is recorded.

---

## 5. Module surface

### Three orthogonal truth surfaces (binding architectural framing)

The builder + writer signatures derive from a load-bearing
architectural constraint surfaced 2026-05-07 during PR 3
implementation pacing:

> **The registered tool set is deployment identity, not runtime
> topology. Candidate sets are topology-sensitive operational
> subsets and are therefore insufficient inputs for
> deployment-stable identity hashing.**

The Layer 1 architecture maintains **three orthogonal truth
surfaces**, each with its own input parameter to the builder:

| Surface | What it fingerprints | Builder input |
|---------|---------------------|---------------|
| **Identity** | Deployment truth — *"what tools exist in the registry"* | `registered_tools` |
| **Topology** | Runtime truth — *"what tools were reachable at this moment"* | `candidate_set_post_reachability` (and the topology block via `snapshot_topology()`) |
| **Arbitration** | Decision truth — *"which tool the narrower selected" / "which tool the planner would have chosen"* | `candidate_set_post_pr14`, `narrower_decision`, `pr20_fired`, `collapse_occurred`, `ambiguity_state` |

These surfaces are **deliberately separate**. Recombining them
would conflate identity drift with topology drift in the resulting
hash — exactly the failure mode the orthogonality exists to
prevent. If a future PR proposes to "simplify" by recombining
`registered_tools` with `candidate_set_post_reachability`, that
proposal is redirected here. **The parameters are deliberately
separate because they fingerprint orthogonal truths. This is not
redundancy. It is semantic boundary preservation.**

**The builder receives all three as explicit inputs. The builder
does not discover them.** Pulling any of these from runtime state
inside the builder would weaken purity, introduce hidden coupling,
and move observation toward participation — that is explicitly
prohibited by the Layer 1 architecture (I-3: no lazy runtime side
effects). The call sites (PR 4 + PR 5) hold the truth; they pass
it explicitly through.

This framing lands verbatim in the writer module's docstring as a
fifth carrier sentence (alongside the §0 framing pair and the §6.5
persistence-layer pair).

### 5.1 `_build_capture_record` (private, exposed for testing)

```python
def _build_capture_record(
    *,
    prompt: str,
    registered_tools: list[Any],          # ← deployment identity (§5)
    candidate_set_post_reachability: list[Any],  # ← runtime topology (§5)
    candidate_set_post_pr14: list[Any],   # ← arbitration input (§5)
    narrower_decision: list[Any],         # ← arbitration output (§5)
    pr20_fired: bool,
    collapse_occurred: bool,
    ambiguity_state: str,
    narrower_latency_ms: float,
    source: str,
    # Test-injection seams; production uses defaults.
    now: Callable[[], str] | None = None,
    new_uuid: Callable[[], str] | None = None,
) -> dict:
    """Build a Layer 1 record dict per contract §3. Pure function;
    no I/O, no side effects.

    See §5 (this spec) for why ``registered_tools`` is a separate
    parameter from the candidate sets — they fingerprint orthogonal
    truth surfaces (identity vs. topology). Recombining them is
    prohibited per §5; see §14 phase-end conditions.

    Production callers do not provide ``now`` / ``new_uuid``. Tests
    inject deterministic values to make assertions on full record
    content stable.
    """
```

The builder calls into PR 2's existing helpers:

- `_topology.snapshot_topology()` for the `topology` block (runtime
  truth).
- `_identity.narrower_version_hash()` for `narrower_version_hash`
  (the narrower's source code is its own identity).
- `_identity.registered_tools_snapshot_hash(registered_tools)` for
  `registered_tools_snapshot_hash` — **passed `registered_tools`
  from the builder's parameter, NOT a candidate set** (§5
  orthogonality).
- `_identity.daemon_git_sha()` for `daemon_git_sha`.

**The builder is pure.** No file I/O. No exceptions propagated out
(any internal error from the topology / identity helpers surfaces
through the writer's failure-invisibility wrapper, not the builder).

The builder is exported from `_capture.py` only as the
leading-underscore name; tests import it directly. Production code
never imports it.

### 5.2 `emit_divergence_capture` (public, fills PR 1 stub)

Signature **deviates from PR 1's stub** by adding the
`registered_tools` parameter — a correctness fix per §5
(orthogonal-truth-surfaces framing). PR 1's signature was a
placeholder that under-specified the identity-hash input source;
PR 3 makes it explicit.

```python
def emit_divergence_capture(
    *,
    prompt: str,
    registered_tools: list[Any],          # ← NEW in PR 3 (§5)
    candidate_set_post_reachability: list[Any],
    candidate_set_post_pr14: list[Any],
    narrower_decision: list[Any],
    pr20_fired: bool,
    collapse_occurred: bool,
    ambiguity_state: str,
    narrower_latency_ms: float,
    source: str,
) -> None:
```

Returns `None`. Fire-and-forget.

**Implementation steps (in order, no others):**

1. Build the record via `_build_capture_record(...)`.
2. Validate via `_schema.validate_capture_record(record)` — raises
   `SchemaValidationError` on any contract §3 violation. The
   validator is from PR 1.
3. Resolve the corpus directory (see §6.1).
4. Resolve the file path for today's UTC date.
5. Determine whether the file already contains a header (see §6.4).
6. Concatenate the bytes to write (header + `\n` + record + `\n` if
   no header present; record + `\n` otherwise) into a single string.
7. Open the file in append mode, perform exactly one `file.write(...)`
   call with the concatenated string (see §6.5 atomic-append
   discipline), flush, close.
8. Return `None`.

The single-syscall write at step 7 is binding, not a stylistic
preference. See §6.5 for the architectural rationale and the
prohibitions on splitting the write into JSON-emission +
newline-emission, or header-write + record-write.

**Every step inside the function body is wrapped in a single
`try` / `except Exception` block.** Any exception — schema validation,
filesystem error, encoding failure, lock contention, anything — is
caught, logged at WARNING with structured detail (call site, failure
mode, prompt prefix per contract §8.4 privacy posture), and
swallowed. The function returns `None` regardless. **Observation
failure cannot become arbitration failure** (I-6).

### 5.3 `read_capture_file` (public, fills PR 1 stub)

Signature is unchanged from PR 1's stub:

```python
def read_capture_file(path: Path) -> Iterator[dict]:
    """Open a Layer 1 capture file and yield each non-header record
    as a parsed dict. Skip malformed lines with a WARNING; never
    abort iteration mid-file.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        SchemaVersionMismatch: if the header record's
            ``schema_version`` does not match the reader's expected
            version. The remediation message is the one specified
            in instrument-contract §9.
    """
```

**Implementation behavior:**

1. Open the file in text mode, UTF-8 encoding, errors=`"strict"` for
   the header read; errors=`"strict"` per-line for record reads (see
   §9 for malformed-line handling).
2. Read the first non-empty line as the header record. Parse as JSON.
3. Assert `header["_header"] is True` and
   `header["schema_version"] == SCHEMA_VERSION`. If either fails,
   raise `SchemaVersionMismatch` with the contract §9 remediation
   message.
4. For each subsequent line:
   - Skip blank/whitespace-only lines silently (no warning).
   - Attempt to decode + parse + validate. On any per-line failure
     (decode error, JSON parse error, schema validation error),
     log a WARNING naming the line number and failure mode, then
     continue to the next line.
   - On success, `yield` the parsed dict.

The reader is a generator. Consumers iterate; the file is closed
when the generator is exhausted or garbage-collected. (`with open(...)`
inside the generator function ensures cleanup on iteration end.)

`SchemaVersionMismatch` is added to `_schema.py` and exported from
the package's public API (it is a reader-side error consumers may
need to handle). The error message is:

> `schema_version=N records require reader version M; upgrade or filter.`

with N and M filled in.

---

## 6. On-disk format

### 6.1 Corpus directory resolution

Resolution order (first match wins):

1. `FORGE_BRIDGE_CORPUS_DIR` env var (override; used by tests).
2. Default: `~/.forge-bridge/corpus/` (per contract §7).

The directory is created with `parents=True, exist_ok=True` on first
emission. Creation failure is one of the I-6 failure modes; the
WARNING surfaces it.

**Note on env var precedence:** the runtime probe and the test
fixture path both honor `FORGE_BRIDGE_CORPUS_DIR`. This is the
single override surface; no path argument is added to
`emit_divergence_capture` (the helper signature stays
fire-and-forget per the framing's mechanical-dumbness constraint).

### 6.2 File naming

Per contract §7: `capture-YYYY-MM-DD.jsonl`. UTC date.

Date is computed from `captured_at` (which is generated by the
builder at record-build time). Records emitted at 23:59:59 UTC and
00:00:01 UTC land in different files; this is the intended
date-based rotation.

### 6.3 File contents

First non-empty line of every Layer 1 file is the header record:

```json
{"_header": true, "schema_version": "1", "created_at": "<iso8601 utc>", "format": "forge-bridge-divergence-corpus-v1"}
```

Subsequent lines are Layer 1 records per contract §3, one per line,
JSON-encoded with `ensure_ascii=False` (contract §3 prompts may
contain non-ASCII), `separators=(",", ":")` (compact), no trailing
whitespace, terminated by `\n`.

### 6.4 File-handle lifecycle (per emission)

The writer **opens, writes, flushes, and closes on every emission.**
No process-global file handle. No connection pool. No buffering
beyond what the OS provides.

Rationale:

- Crash-loss is bounded to the in-flight call. A daemon crash
  between emissions loses zero records; mid-emission loses at most
  the current record.
- O_APPEND mode + close-after-write minimizes corruption windows
  across processes (single-daemon model means this is theoretical,
  but the property is free).
- No "file got rotated under us" handling needed — every emission
  resolves the path freshly. Date rollover at 00:00 UTC is handled
  by the path resolution, not by file-handle bookkeeping.

**Header-write decision (per emission):** check `path.exists()` and
`path.stat().st_size > 0`. If the file is missing or empty, the
writer concatenates the header line + the record line and writes
them in a **single** `file.write(...)` call (see §6.5). Otherwise,
the writer writes the record line alone in a single call. This
handles daemon-restart-mid-day (existing file gets appended to
without a duplicate header) and fresh-day-first-write (new file
gets a fresh header bundled with its first truthful record).

The TOCTOU window between `stat()` and `open(mode="a")` is
acceptable: in single-daemon deployment the only writer is this
process; if the file is concurrently created by another process
between the two calls, the worst case is a duplicate header line on
one boundary, which the reader's `_header: true` filter handles
gracefully (subsequent header lines are skipped as malformed-non-
header records via I-7's corruption-locality path).

### 6.5 Atomic-append discipline at the line boundary

The writer minimizes structural opportunities for partial-record
persistence by enforcing single-syscall writes at the line boundary.

**Per-record write.** The serialized record + trailing `\n` are
concatenated into a single string and written in one
`file.write(...)` call. Splitting the write into separate
JSON-emission and newline-emission steps is **prohibited**.

**Header + first record.** When the writer creates a new file
(header not yet present), the header line + first record line are
concatenated into a single string and written in one
`file.write(...)` call. The header-then-record-as-two-writes pattern
is **prohibited** because it creates a window where the file
contains a header but no records, and a mid-window crash loses the
record being captured.

**Rationale.** Full transactional guarantees would overreach at this
layer — we are not building a write-ahead log. The
atomic-append-at-line-boundary property is sufficient: each record
either exists or does not exist, and partial records are not
introduced through normal operation.

This complements I-7's reader-side corruption locality:

- the writer minimizes corruption opportunity
- the reader localizes unavoidable corruption (filesystem-level
  partial writes that survive flush, OS-level write failures that
  make it past the single-syscall boundary, hardware-level bit
  errors)

**The writer never attempts** partial-record recovery, in-place
repair, continuation writes, or seek-and-reconstruct behavior. If a
write fails, the record is considered lost. Recovery semantics
belong outside Layer 1 persistence.

**Carrier invariant (verbatim — load-bearing, lands in module
docstring + commit message):**

> **Corpus existence implies at least one truthful persisted
> capture.**

The header + first-record bundling rule preserves this invariant.
Without it, the implementation naturally drifts toward
`write(header)` followed by `write(record)`, which creates a
transient impossible state: corpus initialized, zero truthful
captures persisted. Bundling them eliminates that state.

The boundary the §6.5 discipline enforces is **not** transactional
guarantees, **not** WAL semantics, **not** durability engineering.
Only:

> **The architecture should not introduce corruption windows larger
> than the platform already imposes.**

This is an architectural property, not an implementation detail —
which is why it lands in the spec rather than in code review. A
future PR proposing to "split the writes for clarity" or "add a
small repair routine for half-written lines" is a §6.5 contract
violation, not a style preference. See §14 for the phase-end
conditions that name these proposals as rejected at the spec layer.

---

## 7. Append-only execution discipline (I-5)

The framing's constraint 2 — *"append-only discipline must become
executable, not philosophical"* — has three operational requirements:

**7.1 Symbol-level: no public mutation API.**

`forge_bridge.corpus.__init__` exports only the names already
specified in Gate 1 spec §3.1:

```python
__all__ = [
    "divergence_capture_enabled",
    "emit_divergence_capture",
    "read_capture_file",
    "SchemaValidationError",
    "SchemaVersionMismatch",  # NEW in PR 3
    "SCHEMA_VERSION",
]
```

No `update_capture_record`, `mutate_capture_file`, `rewrite_corpus`,
`merge_captures`, `overwrite_capture`, `replace_capture` — none. A
future PR proposing such a function is rejected at the spec layer.
The `test_writer_no_mutation_api` test enforces this with an
introspection assertion against `_capture.py`'s module symbols.

**7.2 File-mode-level: append-only file access.**

The writer opens files only with `mode="a"` (text append). `r+`,
`w`, `w+`, `a+` (which permits read-back) never appear. The reader
opens files only with `mode="r"`. Test
`test_writer_uses_append_mode_only` asserts this via source grep on
`_capture.py` and `reader.py`.

**7.3 Behavioral: emit appends, never overwrites.**

Test `test_writer_emit_appends_each_call`: emit N records to a
fresh file, read back, assert N records present in emit order. Then
emit M more records to the same file, read back, assert N + M
records in original order. Nothing was overwritten; nothing was
deduplicated.

---

## 8. Failure-invisibility contract (I-6) — write side

The framing's constraint 3 names seven failure modes that must not
propagate out of the writer. Each gets an individual test under the
parametrized `test_failure_invisibility[<mode>]`:

| Mode | Mock | Assertion |
|------|------|-----------|
| **disk full** | mock `Path.open` to return a file-like whose `write()` raises `OSError(errno.ENOSPC, ...)` | returns `None`; WARNING logged with `errno=ENOSPC`; no exception |
| **invalid path** | set `FORGE_BRIDGE_CORPUS_DIR` to a path under a file (not a directory), so `mkdir(parents=True)` fails | returns `None`; WARNING logged with the path-resolution failure; no exception |
| **permission denied** | mock `Path.open` to raise `PermissionError` | returns `None`; WARNING logged with `errno=EACCES`; no exception |
| **serialization failure** | inject a record argument containing an unserializable object (e.g., a `bytes` payload) — the schema validator should reject it; if a path bypasses the validator, `json.dumps` raises | returns `None`; WARNING logged naming the validator/serializer error; no exception |
| **partial write** | mock the file's `write()` to write half the bytes and raise `OSError(errno.EIO, ...)` | returns `None`; WARNING logged; no exception. The file may contain a half-line; this is acceptable per I-7 (the reader's corruption-locality test covers the read side). |
| **lock contention** | the writer doesn't take explicit locks (per §6.4), but `flock`-style EAGAIN can surface from underlying filesystems (NFS); mock `Path.open` to raise `BlockingIOError` | returns `None`; WARNING logged; no exception |
| **malformed runtime state** | mock `_topology.snapshot_topology()` to return a malformed dict that fails schema validation | returns `None`; WARNING logged naming the validator error; no exception |

For each mode, the test additionally asserts:

- The function returns `None` (not raises, not returns truthy).
- A single WARNING was logged (no log spam — one warning per
  failure, per call).
- The WARNING message includes (a) the call-site marker (passed
  through `source` parameter), (b) the failure-mode classification
  (e.g., `"capture write failed: disk full"`), (c) the prompt
  prefix (first 32 chars only — contract §8.4 privacy posture).

**The privacy-posture detail is binding, not stylistic.** A future
PR that logs the full prompt for "easier debugging" violates
contract §8.4 (operator identity / verbatim content not part of
operational telemetry).

---

## 9. Reader corruption locality (I-7) — read side

> *"Malformed or partial records should: fail locally, remain
> individually skippable, never invalidate the corpus globally.
> A corrupted line should not poison earlier records, later records,
> corpus loading, replay iteration. Otherwise persistence silently
> becomes fragility."*
>
> — verbatim, user framing 2026-05-07

This sentence lands verbatim in three places:

1. **§9 of this spec** (here).
2. **`forge_bridge/corpus/reader.py` module docstring** —
   immediately following the existing PR 1 stub docstring.
3. **The PR 3 commit message** — alongside the framing's
   institutional-memory carrier sentence.

It is the durable carrier of the corruption-locality contract; it
travels.

### 9.1 The canonical test pattern

Three lines on disk:

1. Valid record (passes schema validation).
2. Malformed line (one of the modes below).
3. Valid record (passes schema validation).

The reader must produce, in order:

1. Readable first record (line 1's parsed dict).
2. Isolated failure or skip (a logged WARNING; no yield).
3. Readable third record (line 3's parsed dict).

`list(read_capture_file(path))` returns exactly two records. The
WARNING was logged exactly once. No exception was raised during
iteration.

### 9.2 Malformation modes (parametrized)

| Mode | Construction | Reader behavior |
|------|--------------|-----------------|
| **truncated JSON** | A record line cut off mid-string: `{"schema_version":"1","capture_id":"abc",`<EOL> | `json.JSONDecodeError` caught; WARNING logged; iteration continues |
| **invalid UTF-8** | A line containing bytes `0xC3 0x28` (invalid UTF-8 sequence) | `UnicodeDecodeError` caught at the line read; WARNING logged; iteration continues |
| **schema-validation failure** | A well-formed JSON dict that fails `validate_capture_record` (e.g., missing required field) | `SchemaValidationError` caught; WARNING logged; iteration continues |
| **empty / whitespace-only line** | `""` or `"   \n"` | Skipped silently — no warning, no yield. Empty lines are normal in pasted/edited JSONL files. |
| **stray header in middle of file** | A `{"_header": true, ...}` record appearing on a non-first line | Treated as malformed (it doesn't pass `validate_capture_record` — the validator rejects records with `_header` set). WARNING logged; iteration continues. |

The reader logs at WARNING with structured detail: line number,
failure mode, the first 32 bytes of the line (privacy posture per
contract §8.4 — never the full line, since malformed runtime
records may contain prompt fragments).

### 9.3 What the reader does NOT do

- **Does not yield a malformed-sentinel record.** The contract §9
  failure-mode says "Skip record; log; continue." Yielding a
  sentinel is option (b) of three considered designs; option (a)
  (skip + log) is what the contract specifies. A future PR proposing
  a `MalformedRecord` sentinel is redirected to a contract amendment.
- **Does not expose a skip count.** Per contract §9, the comparator
  (Gate 4) emits a `skipped/<reason>` summary at end of run by
  wrapping the reader. PR 3's reader is the skip-mechanism;
  summary-construction is a Gate 4 concern.
- **Does not attempt repair.** No "extract whatever fields are
  parseable from a malformed record." The reader's job is yielding
  well-formed records; partially-formed records are observation
  failures, not partial successes.

---

## 10. Discipline-test verification (I-4) — zero production imports

Through PR 1 and PR 2, the `forge_bridge.corpus` package has been
real but uncalled — zero production imports of the package outside
the package itself. PR 3 preserves this property even as
`emit_divergence_capture` becomes a real function.

**The structural asymmetry is the load-bearing PR 3 property.** Ship
the persistence layer. Do not yet introduce institutional memory
into the running daemon. The two arbitration call sites land in
PR 4 (chat handler) and PR 5 (chain step). Until then, the writer
is real but uncalled.

### 10.1 The test

`tests/corpus/test_pr3_discipline.py::test_zero_production_imports_outside_corpus`:

```python
def test_zero_production_imports_outside_corpus():
    """Verify discipline asymmetry: forge_bridge.corpus is callable
    after PR 3 (emit_divergence_capture and read_capture_file are
    real implementations) — but no production code path imports it.

    The two arbitration call sites land in PR 4 (chat handler) and
    PR 5 (chain step). Until then, the writer is real but uncalled.
    That asymmetry is the load-bearing PR 3 property: ship the
    persistence layer without yet introducing institutional memory
    into the running daemon.

    Same property held in PR 1 and PR 2; PR 3 preserves it.
    """
    package_root = Path(forge_bridge.__file__).parent
    corpus_subtree = package_root / "corpus"
    forbidden = ("from forge_bridge.corpus", "import forge_bridge.corpus")

    offenders: list[tuple[Path, int, str]] = []
    for py in package_root.rglob("*.py"):
        if corpus_subtree in py.parents or py == corpus_subtree:
            continue  # the package may import itself
        for lineno, line in enumerate(py.read_text().splitlines(), 1):
            for needle in forbidden:
                if needle in line:
                    offenders.append((py.relative_to(package_root), lineno, line.strip()))

    assert offenders == [], (
        "PR 3 discipline violated: forge_bridge.corpus is imported "
        "by production code path(s). Call-site integration belongs "
        "in PR 4 (chat handler) or PR 5 (chain step), not PR 3.\n"
        "Offenders:\n" + "\n".join(f"  {p}:{n}: {l}" for p, n, l in offenders)
    )
```

The test mirrors the structural pattern PR 1 and PR 2 verified at
commit time (their commit messages each named "Zero production
imports of forge_bridge.corpus outside the package itself" as a
verified discipline check). PR 3 promotes the discipline check from
commit-time prose to executable test, because the asymmetry is more
fragile after the writer becomes real — the temptation to "just wire
up the chat handler quickly while we're here" is highest at the
moment the writer first works.

### 10.2 What this test does NOT do

- **Does not lint for `forge_bridge.corpus.*` strings in
  comments/docstrings.** Documentation references are encouraged.
  The test matches the literal `from`/`import` syntax only.
- **Does not lint test files.** `tests/corpus/` imports the package
  freely. The exclusion is "production code path" — code under
  `forge_bridge/` outside `forge_bridge/corpus/`.

### 10.3 When this test starts failing

The test starts failing the moment PR 4 lands, by design. PR 4's
chat-handler integration will add `from forge_bridge.corpus import
divergence_capture_enabled, emit_divergence_capture` to
`forge_bridge/console/handlers.py` — and at that point the
discipline asymmetry is intentionally relaxed.

PR 4's spec must explicitly allowlist `handlers.py` in this test
(or replace the test with a call-site-aware version). The Gate 1
spec §9 sequencing already names PR 4's responsibility for this
allowlist. PR 3's job is to leave the test green.

---

## 11. Regression test plan (named tests)

All tests live under `tests/corpus/` per the existing PR 1 + PR 2
convention. Each named test below is a separate file or a separate
function depending on coverage scope.

### 11.1 New test files

**`tests/corpus/test_pr3_builder.py`** — `_build_capture_record`
unit tests:

- `test_builder_returns_schema_valid_record` — emits a record;
  asserts `validate_capture_record(record) is None` (no exception).
- `test_builder_populates_topology_block` — asserts the topology
  block matches `_topology.snapshot_topology()`'s contract §3
  shape.
- `test_builder_populates_identity_block` — asserts the identity
  block contains all three hashes from PR 2.
- `test_builder_is_pure` — asserts no file I/O, no network, no
  cache mutation during builder execution.
- `test_builder_deterministic_with_injected_clock_uuid` — round-
  trip test of test injection seams.
- `test_builder_keeps_identity_separate_from_candidate_sets` (§5
  orthogonality) — emit two records with the **same**
  `registered_tools` but **different**
  `candidate_set_post_reachability` (e.g., one with flame-bridge
  reachable, one without). The
  `identity.registered_tools_snapshot_hash` must be **identical**
  across both records. This is the regression guard against future
  "simplification" PRs that recombine identity and topology
  signal surfaces.
- `test_builder_uses_registered_tools_not_candidate_set_for_identity`
  (§5 orthogonality) — emit a record where `registered_tools` and
  `candidate_set_post_reachability` differ (registered set is a
  superset of post-reachability — a backend was unreachable). The
  identity hash must equal
  `registered_tools_snapshot_hash(registered_tools)`, **not**
  `registered_tools_snapshot_hash(candidate_set_post_reachability)`.

**`tests/corpus/test_pr3_writer.py`** — `emit_divergence_capture`
behavior tests:

- `test_writer_uses_append_mode_only` (I-5).
- `test_writer_no_mutation_api` (I-5).
- `test_writer_emit_appends_each_call` (I-5).
- `test_writer_writes_header_on_first_emission` (§6.4).
- `test_writer_skips_header_on_subsequent_emissions` (§6.4).
- `test_writer_creates_corpus_directory_if_missing` (§6.1).
- `test_writer_honors_corpus_dir_env_var` (§6.1).
- `test_writer_no_lazy_side_effects` (I-3).
- `test_writer_emits_no_evaluative_fields` (I-1).
- `test_writer_emits_no_semantic_fields` (I-2).
- `test_writer_returns_none_on_success` (signature contract).
- `test_writer_logs_no_warning_on_success` (no log spam).
- `test_writer_log_message_redacts_full_prompt` (contract §8.4).

Atomic-append discipline tests (§6.5):

- `test_writer_single_write_call_per_record` (§6.5) — patches the
  file object's `write` method; emit one record to an existing
  (header-present) file; assert `write` was called exactly once
  and the call's argument ends with `\n`.
- `test_writer_bundles_header_with_first_record` (§6.5) — patches
  the file object's `write` method; emit one record to a fresh
  (header-absent) file; assert `write` was called exactly once and
  the single argument contains both the header JSON (with
  `_header: true`) and the record JSON, separated by `\n`,
  terminated by `\n`. The carrier invariant — *"corpus existence
  implies at least one truthful persisted capture"* — is what this
  test pins.
- `test_writer_no_seek_or_truncate_or_continuation` (§6.5) —
  source-grep on `_capture.py` asserting zero matches for
  `.seek(`, `.truncate(`, `.tell(`. The writer never repositions
  the file pointer, never truncates, never reads its own write
  position.
- `test_writer_record_lost_on_write_failure` (§6.5) — when
  `write()` raises mid-call, the file does not gain a partial
  record (only whatever the OS-level partial-write happened to
  flush). The writer makes no attempt to retry, repair, or
  continue. Pairs with the I-6 partial-write failure-invisibility
  test in §8 — that one verifies arbitration is unaffected; this
  one verifies the writer makes no recovery attempt.

**`tests/corpus/test_pr3_failure_invisibility.py`** —
parametrized over the seven I-6 failure modes (see §8). One
assertion bundle per mode.

**`tests/corpus/test_pr3_reader.py`** — `read_capture_file`
behavior tests:

- `test_reader_yields_records_in_file_order` — round-trip half.
- `test_reader_skips_blank_lines_silently` (I-7).
- `test_reader_raises_schema_version_mismatch_on_bad_header`
  (Gate 1 spec §3.5 + contract §9).
- `test_reader_raises_file_not_found_on_missing_path` (signature
  contract).
- `test_reader_closes_file_on_iteration_end` (file-handle
  hygiene).

**`tests/corpus/test_pr3_corruption_locality.py`** — parametrized
over the I-7 malformation modes (see §9.2). The canonical
valid-malformed-valid pattern is the test body for each mode.

**`tests/corpus/test_pr3_round_trip.py`** — the load-bearing
writer/reader coupling test:

- `test_round_trip_single_record` — emit, read, assert dict equal.
- `test_round_trip_many_records` — emit N, read N, assert order
  + content match.
- `test_round_trip_across_daemon_restart_simulation` — emit, drop
  process state, reopen file via reader, assert content stable.
- `test_round_trip_with_unicode_prompt` — non-ASCII content
  survives the writer's `ensure_ascii=False` choice.

**`tests/corpus/test_pr3_discipline.py`** — the I-4 discipline
test (see §10).

### 11.2 PR 1 + PR 2 tests that should stay green

All 39 PR 1 tests + 31 PR 2 tests must continue to pass without
modification. The two notable existing-test interactions:

- `tests/corpus/test_pr1_skeleton.py::test_emit_stub_raises` —
  this test currently asserts `emit_divergence_capture` raises
  `NotImplementedError`. PR 3 removes this test (the stub becomes
  real). The removal is part of this PR.
- `tests/corpus/test_pr1_skeleton.py::test_reader_stub_raises` —
  same: removed in PR 3.

The four pre-existing failures unrelated to A.5 (stdio_cleanliness
×2, typer_entrypoint ×2) remain the same set — PR 3 introduces no
new pre-existing failures.

### 11.3 Test count delta

PR 1 added 39 tests. PR 2 added 31. PR 3 should add roughly:

- builder: ~5 + 2 orthogonality (§5) = ~7
- writer: ~13 + 4 atomic-append (§6.5) = ~17
- failure-invisibility: ~7 (one per mode)
- reader: ~5
- corruption-locality: ~5 (one per mode)
- round-trip: ~4
- discipline: ~1

Total: ~46. Minus the 2 PR 1 stub tests removed = ~44 net adds.

Final count: 1582 + ~44 = ~1626 passing tests. Same 4 pre-existing
failures.

---

## 12. Implementation notes — decisions to confirm

The spec pins these decisions; they're flagged here so a reviewer
can redirect before implementation begins:

1. **One `try` / `except Exception` block wrapping the writer body.**
   Alternative: per-step granular handling. The single-block design
   is simpler and matches the framing's mechanical-dumbness
   constraint; per-step granularity invites "this error gets handled
   differently" reasoning that drifts toward classification (I-2
   violation in the writer).

2. **Reader skips empty lines silently.** Alternative: warn on
   every empty line. Empty lines are normal in human-edited JSONL
   files; warning would create log spam without operational signal.

3. **Reader skips a stray header-mid-file as malformed.** Alternative:
   raise on stray header (the file is corrupted, treat hard). The
   skip-with-warning behavior follows contract §9 ("Skip record;
   log; continue") consistently — including for headers that should
   not appear mid-file.

4. **Test injection of `now` / `new_uuid` via builder kwargs.**
   Alternative: `unittest.mock.patch` of `datetime.now` / `uuid.uuid4`.
   Kwarg injection makes the seam visible in the function signature;
   patching is invisible at the call site. The visible-seam pattern
   is the same one PR 1 used for `_warned_invalid_values` (the
   fixture-based explicit-request pattern).

5. **No sub-second-precision `captured_at`.** ISO 8601 with
   millisecond precision (e.g., `2026-05-07T14:32:11.123Z`).
   Microsecond precision is not analytically useful for arbitration
   timing (which is captured separately as `narrower.latency_ms`).

6. **`ensure_ascii=False` on the writer.** Prompts may contain
   non-ASCII content (operator names, project codes, file paths in
   non-Latin scripts). Storing them as raw UTF-8 (rather than escaped
   ASCII) preserves grep-ability — one of JSONL's truthfulness
   properties per framing constraint 4.

If a reviewer redirects on any of these, this section gets amended
before the spec is treated as final.

---

## 13. Out of scope for PR 3 — what later PRs / gates own

| Concern | Owned by |
|---------|----------|
| Chat-handler call site (`handlers.py` integration) | PR 4 |
| Chain-step call site (`_step.py` integration) | PR 5 |
| Visual-asymmetry lint (Gate 1 spec §7.6) | PR 6 (optional) |
| Seed corpus YAML content + fixture-driven coverage | Gate 2 |
| Runtime capture enablement on operator workstation | Gate 3 |
| Comparator implementation | Gate 4 |
| Layer 2 record schema in code | Gate 4 |
| Console-script entry for comparator | Gate 4 |
| Schema migration tooling (rewriting old files) | not implemented; per I-1, migrations write new files |
| Analytics queries / dashboards | out of scope entirely (contract §11) |
| Sampling / fractional capture | out of scope (contract §10 decision #2) |
| Cross-provider replay routing | out of scope (`SEED-CROSS-PROVIDER-FALLBACK-V1.5`) |

A future contributor whose PR changes scope from "PR 3 closure" to
"include Gate 2 / 3 / 4 work" should be redirected here.

---

## 14. Phase-end conditions for PR 3

| Trigger | Response |
|---------|----------|
| All seven invariants' named tests pass + round-trip + discipline + atomic-append tests green | PR 3 closes; PR 4 spec drafts. |
| `test_zero_production_imports_outside_corpus` regresses on a future PR (before PR 4) | The PR is rejected at CI; review surfaces the §10 contract violation. |
| The schema validator rejects records emitted by the writer in production | PR 3 has shipped a defect; treat as v1.5 hotfix. The contract's I-1 means the records on disk are still safe to retain (no corruption beyond the affected emissions). |
| A future PR proposes a `MalformedRecord` sentinel return from the reader | Rejected at the spec layer per §9.3. |
| A future PR proposes a `update_capture_record` or `merge_captures` helper | Rejected at the spec layer per §7.1. |
| A future PR proposes a process-global file handle for performance | Rejected at the spec layer per §6.4. The crash-loss-bounding property is load-bearing. |
| The round-trip test regresses (writer + reader fall out of agreement) | Hard CI failure; the writer/reader coupling is the load-bearing PR 3 contract. |
| A future PR proposes splitting the single-syscall write into separate JSON-emission and newline-emission steps ("for clarity" / "to make tests easier") | Rejected at the spec layer per §6.5. The single-syscall property is the architectural ceiling, not a stylistic preference. |
| A future PR proposes the `write(header)` followed by `write(record)` two-step pattern on fresh-file creation | Rejected at the spec layer per §6.5. Bundling preserves the *"corpus existence implies at least one truthful persisted capture"* invariant; the two-write pattern creates the transient impossible state the bundling rule exists to prevent. |
| A future PR proposes partial-record recovery, in-place repair, continuation writes, or seek-and-reconstruct behavior in the writer | Rejected at the spec layer per §6.5. Recovery semantics belong outside Layer 1 persistence; "if a write fails, the record is considered lost" is binding. |
| A future PR proposes adding a write-ahead log, transactional persistence, or fsync-per-write durability to the writer | Rejected at the spec layer per §6.5. The boundary is "no corruption windows larger than the platform imposes" — not WAL semantics, not durability engineering. Proposals that overreach the architectural ceiling are out of scope. |
| A future PR proposes "simplifying" the builder/writer signature by recombining `registered_tools` with `candidate_set_post_reachability` (e.g., dropping the `registered_tools` parameter and deriving identity from the post-reachability set) | Rejected at the spec layer per §5 (orthogonal-truth-surfaces framing). *"The registered tool set is deployment identity, not runtime topology. Candidate sets are topology-sensitive operational subsets and are therefore insufficient inputs for deployment-stable identity hashing."* The parameters are deliberately separate because they fingerprint orthogonal truths. This is not redundancy; it is semantic boundary preservation. |
| A future PR proposes having the builder read `registered_tools` from a runtime registry (e.g., importing the MCP server's tool list inside the builder) | Rejected at the spec layer per §5. *"The builder receives all three as explicit inputs. The builder does not discover them."* Pulling registry state from inside the builder weakens purity, introduces hidden coupling, and moves observation toward participation — explicitly prohibited by I-3 (no lazy runtime side effects). |

---

## 15. Cross-references

- `A.5.3.2-PR3-FRAMING.md` (commit `68cb24d`) — this spec's binding
  pre-spec contract.
- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — six confirmed decisions, §3
  record schema, §7 storage format, §9 failure modes.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs.
- `forge_bridge/corpus/_capture.py` (commit `ee019be`, PR 1) —
  existing stub for `emit_divergence_capture`; this spec fills it.
- `forge_bridge/corpus/_schema.py` (commit `ee019be`, PR 1) — the
  schema validator the writer calls.
- `forge_bridge/corpus/_topology.py` (commit `a33c135`, PR 2) — the
  topology snapshot the builder calls.
- `forge_bridge/corpus/_identity.py` (commit `a33c135`, PR 2) — the
  identity hash helpers the builder calls.
- `forge_bridge/corpus/reader.py` (commit `ee019be`, PR 1) —
  existing stub for `read_capture_file`; this spec fills it.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` § 2.3 (commit
  `214aa28`) — property-preservation discipline; the verbatim
  carrier sentences in §0, §5, §6.5, and §9 are an instance. The
  six travelers for PR 3 land in the writer module's docstring
  (§0 + §5 + §6.5 sentences), the reader module's docstring
  (§9 sentence), and the PR 3 commit message:

  1. *"Preserve Layer 1 truthfulness while introducing
     persistence."* (framing — §0)
  2. *"Once persistence exists, future interpretation layers begin
     inheriting authority from it automatically. That is why PR 3
     is dangerous: not because it writes data, but because it
     creates institutional memory."* (framing — §0)
  3. *"The registered tool set is deployment identity, not runtime
     topology. Candidate sets are topology-sensitive operational
     subsets and are therefore insufficient inputs for
     deployment-stable identity hashing."* (orthogonal truth
     surfaces — §5)
  4. *"The builder receives all three as explicit inputs. The
     builder does not discover them."* (orthogonal truth surfaces
     — §5)
  5. *"Corpus existence implies at least one truthful persisted
     capture."* (atomic-append discipline — §6.5)
  6. *"The architecture should not introduce corruption windows
     larger than the platform already imposes."* (atomic-append
     discipline — §6.5)
  7. *"Otherwise persistence silently becomes fragility."*
     (corruption locality — §9)

  (The numbering above shows seven entries because the §0 framing
  is two sentences forming one architectural pair; the count of
  carrier sentences is six pairs/singles or seven individual
  sentences depending on how you count. All travel byte-identical
  to the targets enumerated above.)

---

## Resume protocol — what the next session does with this spec

1. **Read the framing first** (`A.5.3.2-PR3-FRAMING.md`). The
   pressure profile is the load-bearing context.
2. **Read this spec.** Confirm the seven invariants, the single-PR
   rationale, and the implementation-notes decisions in §12.
3. **Surface for review** before any code is written. Per the
   established discipline, the spec is reviewed; deviations re-open
   the artifact for explicit re-review, not absorbed silently.
4. **Implement** against the named tests in §11. The round-trip
   test is the load-bearing verification.
5. **Run the discipline test** (§10) before committing. The grep
   must produce zero matches.
6. **Commit** with the framing's two crystallizing sentences in the
   commit message body, alongside the I-7 corruption-locality
   verbatim sentence.

Do not begin drafting the spec without re-reading the framing. The
pressure-profile shift is the load-bearing context; losing it is
how the writer accidentally grows interpretation features.
