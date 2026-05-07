# A.5.3.2 PR 3 — Framing (registered, not yet drafted)

**Status:** framing registered 2026-05-06 during passoff. **NO spec
drafted, NO code written.** This artifact exists so the next session
opens to the right pressure profile before any drafting begins.

**Predecessors:**
- `A.5.3.2-FRAMING.md` — phase shape + objective lock
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape + invariants
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 implementation sequencing
- `A.5.3.2 PR 1` (commit `ee019be`) — package skeleton + schema + env gate
- `A.5.3.2 PR 2` (commit `a33c135`) — topology snapshot + identity hashes

This document is **binding framing** for PR 3. The eventual PR 3
spec must derive from it; the implementation must derive from the
spec. Deviations re-open this artifact for explicit re-review, not
absorbed silently into spec drafting.

---

## The pressure profile changes here

PR 3 is the first genuinely dangerous phase in the sequence. **Not
because it is technically harder than PR 2, but because this is
where truthful observation first becomes persistent reality.**

That changes the pressure profile entirely.

Up through PR 2, the architecture could still remain "conceptually
pure" because nothing survived process lifetime. PR 3 changes that.

Now the system will begin producing artifacts that:
- persist
- accumulate
- become inspectable
- become tempting to analyze
- become tempting to optimize against

---

## Real job (verbatim)

PR 3's real job is **not** "implement the writer."

Its real job is:

> **"Preserve Layer 1 truthfulness while introducing persistence."**

That is the important framing. The writer is incidental to the job.
The job is preserving truthfulness across the persistence boundary
that PR 3 introduces.

---

## Success condition (verbatim)

> **Truthful records now persist. Nothing more.**

That is the entire success condition. Not "the corpus is observable,"
not "the corpus is queryable," not "the corpus is useful." Just:
truthful records persist.

---

## Preserved constraints (verbatim — these properties become PR 3's invariants)

### 1. Persistence must remain mechanically dumb

The writer should:
- validate
- serialize
- append
- flush
- return

Nothing else.

No:
- deduplication
- normalization
- summarization
- enrichment
- compaction
- replay indexing
- interpretation metadata

Those are future-layer concerns.

### 2. Append-only discipline must become executable, not philosophical

PR 1 / PR 2 established the invariant conceptually. PR 3 must now
enforce it operationally.

Meaning:
- no rewrite path
- no mutation path
- no update API
- no merge behavior
- no overwrite semantics

Append-only behavior should be tested explicitly.

### 3. Capture failure invisibility must hold under persistence failure

This is probably the most important PR 3 property.

Arbitration must remain unaffected if:
- disk full
- invalid path
- permission denied
- serialization failure
- partial write
- lock contention
- malformed runtime state

Observation failure cannot become arbitration failure.

### 4. Persistence format should optimize for truthfulness first, convenience second

JSONL still appears correct because append-only truth systems
benefit from:
- inspectability
- replayability
- corruption locality
- grepability
- partial recovery

before they benefit from storage optimization.

### 5. PR 3 still must not become "the corpus system"

The pressure for:
- replay tooling
- filtering
- comparisons
- dashboards
- drift analysis
- prompt tagging
- summaries

will begin immediately once persistence exists.

**Resist all of it.**

Each item above belongs to a later phase or to the comparator
(Gate 4). PR 3's scope is the writer + the reader, the minimum
needed for "truthful records now persist."

---

## The architectural shift (verbatim — this is the load-bearing framing)

The critical shift PR 3 introduces:

> **Once persistence exists, future interpretation layers begin
> inheriting authority from it automatically.**

That means Layer 1 persistence must remain:
- boring
- passive
- literal
- append-only
- structurally honest

Because every later layer will quietly trust it as ground truth.

> **That is why PR 3 is dangerous: not because it writes data, but
> because it creates institutional memory.**

The institutional-memory framing is the carrier sentence for this
phase. It belongs in the eventual PR 3 commit message and in the
writer module's docstring, alongside the crystallizing sentence
already established for the capture-invocation contract.

---

## Scope (binding for the spec)

In scope:
- Capture builder (`_build_capture_record`) — turns the call-site's
  arguments into a Layer 1 record dict, including topology snapshot
  (PR 2) and identity hashes (PR 2).
- JSONL writer — validate, serialize, append, flush, return. Nothing
  else.
- Reader implementation in `forge_bridge/corpus/reader.py` — replaces
  the PR 1 stub with a real implementation that opens Layer 1 files,
  validates the header, yields records.
- `emit_divergence_capture` becomes a real function (the PR 1
  NotImplementedError stub is replaced).
- Regression tests for: append-only discipline (no mutation paths
  exist), capture-failure invisibility (every failure mode listed in
  constraint 3, individually), schema validation rejection at write
  time, reader round-trip (`read(write(record)) == record`).

Out of scope (defer to later gates / phases / discard entirely):
- Replay tooling
- Filtering
- Comparisons
- Dashboards
- Drift analysis
- Prompt tagging
- Summaries
- Deduplication
- Normalization
- Compaction
- Indexing of any kind
- Migration tooling for schema_version bumps (defer until needed;
  the contract specifies that schema migrations write new files
  rather than rewrite — PR 3 should not implement migration logic)
- Call-site integration (still PR 4 + PR 5)

If the spec begins drifting toward "and let's also add X" where X is
on the resist-all-of-it list above, **stop and re-scope**. That
drift is the named PR 3 failure mode.

---

## Discipline carries from PR 1 and PR 2

The same discipline pattern that landed PR 1 and PR 2 applies:

- Surface before staging.
- Preserve asymmetry — PR 3 does not include call-site integration;
  PR 4 + PR 5 are still future.
- Preserve passivity — the writer is invoked by the call site (in
  PR 4 + PR 5), not by anything in PR 3 itself.
- Usefulness remains deferred — PR 3 ships persistence, not
  observability tooling.

The four PR 2 invariants (descriptive-not-evaluative;
observational-not-semantic; no-lazy-side-effects; loud-asymmetry)
**carry forward to PR 3 unchanged**. PR 3 adds two more invariants
(append-only executable; failure-invisibility under persistence
failure) that make the existing four operational rather than
conceptual.

---

## Recognition pattern (cross-reference SEED-RELIABILITY-PHASE-METHODOLOGY 2.3)

This framing artifact is itself an instance of the property-
preservation discipline named in the reliability-character seed
(observation 2.3, commit `214aa28`). The user-supplied prose for the
five preserved constraints, the success condition, and the
institutional-memory framing land here verbatim because they will
land verbatim again in the spec, the writer module's docstring, the
test module's docstring, and the PR 3 commit message.

The repetition is the property crystallizing into the codebase
before the code exists.

---

## Next session resume point

When the next session opens:

1. **Read this document first** before drafting anything.
2. Draft the PR 3 spec (`A.5.3.2-PR3-SPEC.md`) from this framing.
   The spec sequences the implementation in PRs (likely a single
   PR 3, but optionally split if the writer + reader want different
   review attention).
3. Surface the spec for review per the established discipline.
4. Then implement.

Do not begin drafting the spec without re-reading this document.
The pressure profile shift is the load-bearing context; losing it
is how the writer accidentally grows interpretation features.
