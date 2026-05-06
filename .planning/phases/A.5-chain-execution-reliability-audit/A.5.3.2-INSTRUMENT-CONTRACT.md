# A.5.3.2 — Instrument contract

**Status:** landed 2026-05-06 after redline. This contract gates the
A.5.3.2 spec; the spec must not draft without conformance to this
document. Amendments require explicit re-review against the framing
(`A.5.3.2-FRAMING.md`) and the invariants enumerated below.

**Predecessor:** `A.5.3.2-FRAMING.md` (binding scope contract, commits
`fe016c0` + `4d786a6`).

**This document is a contract**, not an implementation plan. It locks
the instrument's shape — what it is, what it isn't, what it must
preserve, what it must NOT capture — before any code is written.
Implementation choices (file paths, exact APIs, async-task plumbing)
that don't change the contract are out of scope here.

---

## 1. Purpose

Build the **divergence corpus** — the primary deliverable of A.5.3.2 —
that lets us answer two questions with evidence rather than intuition:

- For which prompt families does the deterministic narrower diverge
  from what the LLM-as-planner would have chosen?
- Within those divergence cases, which classification (`LLM_DECLINED`,
  `DIFFERENT_TOOL`, `MULTI_TOOL`, `AMBIGUOUS`) — and which topology
  states — make the narrower's choice harmful, and which make it
  benign?

The instrument exists to answer those questions; everything in this
contract serves that purpose. If a proposed feature doesn't directly
support it, the feature belongs in a different artifact.

### Orientation principles (read these before designing or extending)

Two framing principles travel with this instrument. Future readers
should encounter them before forming opinions about scope, location,
or extension:

**Principle 1. Corpus data is operationally sensitive substrate, not
engineering telemetry.** The records this instrument captures are
not "logs we look at when something breaks." They carry verbatim
operator prompts, the candidate sets the system saw, the topology
state at decision time. They feed decisions about how the production
arbitration layer behaves. Treat the corpus directory, the runtime
probe's storage path, and the comparator's outputs with the same
posture you would apply to a production database — versioned schema,
controlled retention, intentional access paths, no casual rewriting.
A future contributor who treats this as engineering telemetry (free
to truncate, free to reshape, free to mix with other diagnostic
streams) is misreading what the corpus is for.

**Principle 2. Logical ownership ≠ runtime co-location.** The
comparator code lives in the `forge_bridge` package (logical
ownership: it's part of this project, versioned with it, tested
against it). Comparator invocations run in a separate OS process
from the daemon (runtime isolation: I-3 in §2.2). These are
independent decisions; the package-with-process-isolation answer is
correct precisely because they don't have to move together.

This principle generalizes beyond the comparator. Future
architectural choices should distinguish "who owns this logic?"
(versioning, testing, dependency tree) from "where does this logic
execute?" (process boundaries, resource isolation, failure
containment). Conflating them produces either monoliths-by-default
(everything ends up in-daemon because that's where the package is)
or fragmented-ownership-by-default (everything gets spun out to
separate repos to enforce process isolation). Neither is the right
answer in general; the right answer is per-decision and depends on
the specific failure-containment vs. coordination tradeoff.

### Dual-protection framing

The boundary the instrument observes runs in **both** directions, and
the contract protects both equally:

- **Narrower protected from becoming planner.** The capture layer is
  forbidden from making LLM calls, deriving semantic intent, or
  storing reasoning artifacts. The instrument cannot itself become a
  vector for the boundary-blur the framing forbids.
- **Planner protected from being constrained by historical narrowing.**
  The comparator queries the LLM against the unfiltered post-
  reachability candidate set — never the narrowed set — so the LLM's
  behavior in the corpus reflects what the planner would have done
  unconstrained, not what it does given the narrower's pre-decision.
  Without this, the corpus would systematically underestimate
  divergence (the LLM would learn to match the narrower because that's
  what its inputs make available).

Both directions are the boundary. Either being violated invalidates
the corpus.

### Threat articulation — the failure mode this contract structurally prevents

A future contributor, reviewing the divergence corpus, may notice that
the SAME_TOOL classification fires often and the DIFFERENT_TOOL
classification fires rarely. They may then propose: "tune the narrower
to maximize SAME_TOOL frequency" — i.e., treat **planner-agreement
frequency as an optimization target**.

That is the dominant failure mode this contract exists to prevent.
Tuning toward planner-agreement frequency turns the narrower into a
deterministic shadow of the LLM, which:

- Re-introduces the boundary blur the framing forbids (the narrower
  starts approximating planner reasoning by training-against-LLM
  proxy).
- Produces silently-wrong determinism: in the cases where the LLM
  would have correctly declined or escalated (`LLM_DECLINED`,
  `MULTI_TOOL`), the narrower trained on agreement frequency will
  collapse confidently to whatever the LLM's most-frequent first-tool
  was — which is the high-cost failure mode (state corruption) the
  Objective C asymmetry warns against.
- Loses the asymmetric-cost discipline: agreement frequency is a
  symmetric metric. It treats wrong determinism and wrong escalation
  as equivalent costs. The framing explicitly rejects that.

The corpus is for **classification of divergence patterns**, not
**minimization of divergence count**. Keep that distinction load-
bearing. The structural protections in §2 (invariants) and §8
(exclusions) exist to make the planner-agreement-frequency tuning
attempt difficult to even draft — not just discouraged.

---

## 2. Architecture — two-layer split with structural invariants

The instrument is split into two layers with a strict boundary
between them. The split is the load-bearing design decision.

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1 — Capture (runtime-cheap, observational, online)    │
│                                                              │
│   Captured at the moment of arbitration:                    │
│     - prompt                                                │
│     - source ("fixture" | "runtime")                        │
│     - candidate set (post-reachability, post-PR14)          │
│     - topology snapshot (all probed backends + LLM provider)│
│     - identity (narrower hash, tools-list hash, daemon SHA) │
│     - narrower decision                                     │
│     - PR20 fired? collapse occurred? ambiguity state        │
│     - narrower latency                                      │
│     - capture_id (UUID), captured_at (ISO timestamp)        │
│     - schema_version                                        │
│                                                              │
│   Storage: ~/.forge-bridge/corpus/capture-YYYY-MM-DD.jsonl  │
│   APPEND-ONLY. IMMUTABLE per record. NO outcome labels.     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │  (offline pipeline, separate process)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2 — Comparator (offline, batch, regenerable)          │
│                                                              │
│   Runs in a SEPARATE PROCESS — never in-daemon.             │
│   Reads Layer 1 records (read-only). For each, calls the    │
│   LLM via complete_with_tools against the unfiltered post-  │
│   reachability candidate set, records:                      │
│     - LLM-selected tool(s)                                  │
│     - LLM declined tool usage?                              │
│     - LLM latency                                           │
│     - comparator_model (e.g. "qwen2.5-coder:32b@sha256:...")│
│     - comparator_run_id, comparator_run_at                  │
│     - system_prompt_fingerprint                             │
│     - divergence_classification (REQUIRED, five-case)       │
│     - prompt_classification (interpretive)                  │
│                                                              │
│   Storage: ~/.forge-bridge/corpus/compare-RUN-ID.jsonl      │
│   References Layer 1 by capture_id. Regenerable from        │
│   Layer 1 + a model snapshot (see §2.3 replay limits).      │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Why split

Three reasons; all three must hold or the split is wrong:

1. **The runtime path makes zero LLM calls.** Capture is lightweight;
   the operator's chat session never blocks on the comparator. A
   misbehaving comparator (LLM down, slow, hung) cannot affect the
   live system.
2. **Layer 1 never goes stale.** Model swaps regenerate Layer 2;
   Layer 1 stays valid forever (modulo schema_version migrations,
   which are explicit).
3. **The boundary discipline is structurally enforced.** The capture
   layer cannot accidentally call the planner mid-arbitration because
   the capture layer has no LLM dependency at all. The comparator can
   only run offline. The shapes can't blur.

### 2.2 Structural invariants — protections that cannot be relaxed

The following invariants are part of the contract surface. Violating
any of them is a contract amendment, not a spec decision:

**I-1. Layer 1 is append-only and immutable per record.** Once a Layer
1 record is written, it is never:

- enriched with comparator output retroactively
- annotated with outcome labels
- merged with Layer 2 fields
- mutated to incorporate downstream analysis
- rewritten when the schema evolves (migrations write new files;
  old files stay as-is)

The append-only invariant is what makes Layer 1 a faithful
observational record. Any merge-back from Layer 2 corrupts the
boundary the split exists to protect. If a future contributor
proposes "let's just inline the divergence_classification into
Layer 1 for convenience," the answer is no.

**I-2. Layer 1 carries observations only — no outcome labeling.**
Layer 1 records WHAT happened (prompt, candidate set, narrower
decision, topology). Layer 1 does NOT record interpretations of
those events (this divergence was harmful, this prompt was
ambiguous, this classification, this category). Outcome labeling
lives in Layer 2 or in higher analytic layers; Layer 1 stays an
unannotated record of fact.

This is why the previous draft's `prompt_classification_initial`
field has been removed from Layer 1 and moved to Layer 2:
classification is interpretive.

**I-3. The comparator runs in a separate process, never in-daemon.**
Even in batch mode (e.g., a comparator run kicked off from a console
script while the daemon is up), the comparator process is its own
OS process. The daemon process never imports comparator code paths,
never performs comparison work, never holds Layer 2 state. This
prevents the ergonomic temptation of "just make the comparator a
daemon background task" — which would re-introduce the live-
correlation failure mode (§8.8) under a different name.

### 2.3 Replay determinism — what is reproducible vs what is not

The instrument promises **bounded reproducibility**, not global
determinism. This echoes the envelope-vs-behavior framing in
`SEED-CROSS-PROVIDER-FALLBACK-V1.5.md`:

| Property | Reproducible? | Why |
|----------|---------------|-----|
| Layer 1 record content given the same prompt + topology + narrower version | **Yes** | Capture is purely deterministic (lexical narrower + observed topology). Two runs with identical inputs produce identical Layer 1 records modulo timestamps and uuids. |
| Layer 2 envelope shape given the same Layer 1 + model snapshot | **Yes** | The comparator's output shape (fields, types, divergence_classification computation rule) is deterministic. |
| Layer 2 LLM-side content (selected_tools, declined_tool_usage) given the same model snapshot + sampling config | **Bounded** | Greedy sampling (temperature=0) is the default and produces identical content for identical inputs in well-behaved models. Higher temperatures explicitly accept variance. Model-vendor behavior changes between versions; the digest in `comparator_model` is what makes drift detectable. |
| Layer 2 LLM-side content across different models | **No** | Different models legitimately disagree. Side-by-side comparison is the answer, not normalization. |
| Behavior of the system end-to-end during the original capture | **No** | The instrument captures what the narrower decided and what the topology was; it does not capture what the LLM would have done in the original session (that's exactly the comparator's job, not the captor's). |

A future contributor proposing "the corpus should be globally
deterministic across model swaps" should be redirected here — that
proposal misunderstands what determinism the instrument is asserting.
The instrument is a comparison harness for non-deterministic planners
against deterministic narrowers; the comparison ITSELF is well-
defined; the planner inside it never will be.

### 2.4 What this means in practice

If a future contributor proposes "capture the LLM's choice
synchronously so we can correlate it with the narrower's choice in
real time," the answer is no — that proposal blurs the layers and
re-introduces every problem the split exists to prevent. See §8.8
for the explicit prohibition.

---

## 3. Layer 1 — Capture record schema

Canonical JSON shape per record (one per JSONL line). All fields
listed below are **required** unless marked OPTIONAL. Adding a new
required field is a `schema_version` bump.

```json
{
  "schema_version": "1",
  "capture_id": "<uuid4>",
  "captured_at": "<iso8601 utc>",
  "source": "fixture",
  "prompt": "<verbatim user message>",
  "candidate_set": {
    "post_reachability": ["forge_list_staged", "forge_get_staged", ...],
    "post_pr14_filter":  ["forge_list_staged", "forge_get_staged"]
  },
  "topology": {
    "probed_at": "<iso8601 utc>",
    "backends": {
      "flame_bridge": {"reachable": false, "host": "127.0.0.1", "port": 9999},
      "ollama_local": {"reachable": true,  "host": "127.0.0.1", "port": 11434},
      "anthropic":    {"reachable": true,  "configured": true}
    }
  },
  "identity": {
    "narrower_version_hash": "<sha256 of _tool_filter.py contents>",
    "registered_tools_snapshot_hash": "<sha256 of sorted tool names + arg-schemas>",
    "daemon_git_sha": "<full git sha of running daemon>"
  },
  "narrower": {
    "decision": ["forge_list_staged"],
    "pr20_fired": true,
    "collapse_occurred": true,
    "ambiguity_state": "single_survivor",
    "latency_ms": 0.42
  }
}
```

**Notes on shape:**

- `source` is one of `"fixture"` or `"runtime"`. **REQUIRED on every
  record.** Comparator analyses must be source-aware: threshold
  decisions about narrower behavior are evaluated against `runtime`
  data; `fixture` data is for coverage and regression. Mixing the
  two without explicit separation produces noise. The comparator
  must surface the source split in any aggregate summary.
- `candidate_set` records BOTH the post-reachability and the
  post-PR14 list. The split lets us answer "did the reachability
  filter prune the natural-home tool?" (the A.5.3.1 root cause) on
  every record without reconstructing.
- `topology` is **first-class captured data**, not a side note. It
  records every probed backend's reachability state plus LLM provider
  availability at arbitration time. This is required for replay
  validity: a Layer 2 regeneration that ignores topology would call
  the LLM against a candidate set the original session did not see.
  Future backends added to the reachability filter MUST extend this
  field; new keys are non-breaking schema additions.
- `identity` carries three drift-detection fingerprints:
  - `narrower_version_hash` — sha256 of `_tool_filter.py` contents
    at capture time. Detects "Layer 1 captured against narrower
    version A, comparator running against version B" drift.
  - `registered_tools_snapshot_hash` — sha256 of the sorted list of
    registered tool names plus their argument schemas. Detects
    "the registered tool set changed between capture and replay"
    drift.
  - `daemon_git_sha` — full git sha of the running daemon's source
    tree. Coarsest signal, useful as a tie-breaker when the more
    specific hashes are inconclusive.
- `narrower.decision` is a list, not a string — multi-survivor and
  zero-survivor cases must be representable.
- `narrower.ambiguity_state` is one of `single_survivor`,
  `multi_survivor`, `zero_survivor`. Lifted to a top-level field
  rather than derived from `decision.length` so analytic queries
  don't have to special-case empty lists.
- **No `prompt_classification` field** in Layer 1 (per I-2 above —
  outcome labeling moves to Layer 2).
- **No `narrower_internals` field** (per §8.2 exclusion). Per-rule
  overlap counts are reconstructable; storing them locks the corpus
  to today's narrower.

---

## 4. Layer 2 — Comparator record schema

```json
{
  "schema_version": "1",
  "capture_id": "<uuid4 — references Layer 1>",
  "comparator_run_id": "<uuid4>",
  "comparator_run_at": "<iso8601 utc>",
  "comparator_model": "qwen2.5-coder:32b@<digest>",
  "comparator_sampling": {
    "temperature": 0.0,
    "max_tokens": 4096
  },
  "system_prompt_fingerprint": "sha256:<hex>:v<n>",
  "llm": {
    "selected_tools": ["forge_list_projects"],
    "declined_tool_usage": false,
    "latency_ms": 1820
  },
  "divergence_classification": "DIFFERENT_TOOL",
  "prompt_classification": "ambiguous_operational"
}
```

**Notes on shape:**

- `divergence_classification` is the framing's REQUIRED output shape,
  extended with the `AMBIGUOUS` bucket per §5. Five values total.
- `comparator_model` includes a digest because "qwen2.5-coder:32b" is
  a moving target across Ollama updates.
- `comparator_sampling.temperature` defaults to 0.0 (greedy) for
  bounded reproducibility. Nonzero temperature is allowed but must be
  recorded; analyses that compare across temperatures are explicit
  (and cross-temperature comparisons should be expected to surface as
  AMBIGUOUS more often).
- `system_prompt_fingerprint` records the system prompt active at
  comparator-run time as `sha256:<hex>:v<n>` — hash plus a short
  version tag. The CONTENT is deliberately not stored (§8.3); the
  fingerprint detects drift between runs.
- `prompt_classification` is the interpretive label. Comparator
  applies it; downstream analytic layers may further refine. Layer 1
  remains observation-only (I-2).
- Layer 2 records reference Layer 1 by `capture_id`. A given Layer 1
  record can have multiple Layer 2 records (one per comparator run /
  model). This is the side-by-side model comparison path.

---

## 5. Required output shape — divergence classification

Per `A.5.3.2-FRAMING.md` § "Divergence classification — required
output shape," extended with the `AMBIGUOUS` bucket per redline:

| Value | Computed when | Operational signal |
|-------|---------------|--------------------|
| `LLM_DECLINED` | `llm.declined_tool_usage == true` (regardless of narrower decision) | Strongest hijacking evidence — the narrower's collapse, if any, would have been wrong by definition. |
| `SAME_TOOL` | narrower collapsed to one tool AND `llm.selected_tools == narrower.decision` (single tool, equal) | Confident determinism is correct in this case. PR20 doing its job. |
| `DIFFERENT_TOOL` | narrower collapsed to one tool AND llm picked exactly one tool AND they differ | The canonical hijacking case. |
| `MULTI_TOOL` | `llm.selected_tools.length > 1` (regardless of narrower) | Over-eager collapse case. Multi-intent prompts being narrowed into single-step execution. |
| `AMBIGUOUS` | None of the above can be cleanly determined: malformed LLM response, partial-overlap multi-tool sets the buckets above don't cover, comparator timeout mid-decision, or any case where forcing a fit produces noise | Honest acknowledgment that not every record classifies cleanly. Forced fit corrupts analysis. |

A precedence rule for cases where multiple categorizations could
arguably apply:

1. `AMBIGUOUS` wins when classification confidence is genuinely low.
   Better to surface it than to shoehorn.
2. `LLM_DECLINED` wins over the remaining three.
3. `MULTI_TOOL` wins over `DIFFERENT_TOOL` and `SAME_TOOL`.
4. `DIFFERENT_TOOL` and `SAME_TOOL` are mutually exclusive at the
   single-tool case.

The narrower's ambiguous-state cases (`multi_survivor`,
`zero_survivor`) are NOT re-classified into divergence buckets;
they're already separately queryable via Layer 1's `ambiguity_state`
field.

> **Note for framing alignment:** the framing document specifies
> "REQUIRED four-case output." This contract extends with `AMBIGUOUS`
> as the honest fifth bucket — the four operational classes remain
> the analysis targets; `AMBIGUOUS` is what we do with records that
> resist categorical analysis. Both documents are consistent on the
> operational analysis surface (four categories); the contract
> additionally specifies what the classifier does with cases that
> don't fit. The framing should be amended to acknowledge this in
> the same landing pass.

---

## 6. Integration points

### 6a. Test fixture (`tests/_corpus_fixture.py`)

A pytest fixture wrapping `execute_chain_step` and the chat handler's
narrowing path. Used by:

- A new `tests/test_a5_3_2_corpus_seed_prompts.py` that drives a
  curated list of prompts (seed corpus) covering every prompt-family
  cell in the initial taxonomy, with topology pinned by mock.
- Future per-divergence regression tests that consume specific
  capture records as fixtures.

The fixture writes Layer 1 records with `source: "fixture"` to a
test-scoped directory, NOT to `~/.forge-bridge/corpus/`. Tests do not
pollute the runtime corpus.

### 6b. Runtime opt-in probe

Gated by env var: `FORGE_BRIDGE_DIVERGENCE_CAPTURE=1`. Off by default.
When on:

- The narrower path writes a Layer 1 record (with `source: "runtime"`)
  after every arbitration decision.
- Records go to `~/.forge-bridge/corpus/capture-YYYY-MM-DD.jsonl`
  (append-only, one file per UTC day).
- Failure to write must NOT propagate. A logged warning is the only
  failure mode; the live request continues unaffected.

### 6c. Comparator process

The comparator is a **separate process** (per I-3). It runs as a
console script (e.g., `forge-bridge-divergence-compare`) or
equivalent module entry. It is NEVER imported into the daemon, and
the daemon NEVER spawns the comparator as a managed sub-process —
the operator runs the comparator manually or via cron.

Reads Layer 1 records (file or directory), calls the LLM for each,
writes Layer 2 records. Resumable on partial failure. Idempotent
per `(capture_id, comparator_model, comparator_run_id)`.

CLI flags (illustrative, not binding):
- `--input <path>` — Layer 1 file or directory
- `--output <path>` — Layer 2 destination
- `--model <name>` — override default
- `--limit <n>` — cap for partial runs
- `--filter <expr>` — JMESPath / jq-style filter against Layer 1
- `--source <fixture|runtime>` — source-segmented run

**Comparator analysis must be source-aware.** Aggregate summaries
must surface the `runtime` vs `fixture` split. Threshold judgments
about narrower behavior (e.g., "DIFFERENT_TOOL fires N% of the
time") must cite the source segment they're computed against —
mixing fixture and runtime in a single threshold produces noise.

---

## 7. Storage format — JSONL

Both layers are JSONL (JSON-lines). Append-only. One record per line.
Each file's first line is a header record:

```json
{"_header": true, "schema_version": "1", "created_at": "...", "format": "forge-bridge-divergence-corpus-v1"}
```

Why JSONL:

- Streamable — analytic queries don't need to load whole corpus.
- Append-only — no concurrent-write coordination beyond OS file locks.
- Tooling-rich — `jq`, `fx`, `grep`, plain `python -c` all work.
- Schema-versioned per record — schema migrations are explicit (and
  produce new files; never rewrite old records — see I-1).

The corpus directory layout:

```
~/.forge-bridge/corpus/
├── capture-2026-05-06.jsonl       (Layer 1, written by runtime probe)
├── capture-2026-05-07.jsonl
├── compare-<run_uuid>.jsonl       (Layer 2, written by comparator)
└── compare-<run_uuid>.jsonl
```

A small reader module (`forge_bridge.corpus.reader`) wraps file
parsing, schema-version dispatch, and joining Layer 1 + Layer 2.
Consumers (analytics, regression tests) use the reader, never
re-parse the format.

---

## 8. EXPLICIT EXCLUSIONS — what this instrument deliberately does not capture

Per A.5.3.2-FRAMING § "Discipline binding for the contract." This
section is the structural protection against scope-by-accretion.
Each exclusion states **what** and **why**.

### 8.1 Raw LLM token streams or prose final answers

**Why:** The instrument's purpose is arbitration analysis, not model
quality evaluation. Storing token streams would (a) bloat the corpus,
(b) drag in sampling non-determinism that has nothing to do with
arbitration, and (c) tempt future contributors to derive analytics
from text content — which is implicit reasoning logic in the
instrument itself.

The LLM's tool selection is the decision; the prose is downstream of
the decision and adds noise.

### 8.2 Internal narrower scoring (per-rule overlap counts)

**Why:** The narrower's per-rule scoring is reconstructable from the
captured candidate set + prompt + the public narrower function. Storing
it locks the corpus to today's narrower implementation; if Rule N is
restructured, old records reference dead state.

The replay constraint is "feed Layer 1 prompt + candidate_set back
through the current narrower"; that's the supported reconstruction
path.

### 8.3 System-prompt content

**Why:** The corpus must replay against a fixed system prompt
(whichever was active at capture). Storing the system-prompt text
invites comparing-across-versions analytics that are noise — we want
to discover divergences caused by narrower changes, not divergences
caused by prompt-template edits.

What we DO store: a `system_prompt_fingerprint` field (sha256 hash +
short version tag) on Layer 2 records. Drift between fingerprints
across runs is a signal; the content itself is not.

### 8.4 Operator identity / IP / session ID

**Why:** The corpus is about prompts and decisions, not about
who-said-what. Privacy + scope-creep protection. The runtime probe
must not capture identity even when present in the request envelope.

If a future phase legitimately needs operator-segmented analytics,
that is a different instrument with its own contract — not an
addition to this one.

### 8.5 Conversation history beyond the current arbitrating turn

**Why:** Capture the prompt that triggered narrowing, not the rolling
context. Multi-turn analytics is a different instrument's job; mixing
it in here would let "narrowing was correct given prior turn"
reasoning leak into the corpus, which is the conversational-
interpretation that the boundary discipline forbids.

What we DO capture: the single prompt that was passed to the
narrower. If multi-turn arbitration becomes a question, plant a seed.

### 8.6 Performance metrics beyond the documented timing fields

**Why:** Performance is a different concern. No memory profiling, no
GC stats, no event-loop traces. Mixing them into the arbitration
corpus blurs purpose; analytic queries become "filter for arbitration
+ exclude perf noise" instead of being purely arbitration-shaped.

What we DO capture: `narrower.latency_ms` and `llm.latency_ms`. Just
those two. Anything else is a different instrument.

### 8.7 Cross-record deltas / pre-computed comparisons

**Why:** Each record stands alone. "This run vs last run" analytics
happen in the analytics layer, not by storing pre-computed deltas in
records. Storing deltas creates ordering dependencies between records
that the JSONL format does not enforce.

### 8.8 Live correlation between Layer 1 and Layer 2

**Architecturally prohibited because it collapses observation into
participation.**

This is the most important exclusion in the document. The two-layer
split is the load-bearing design decision; live correlation is not
merely "out of scope" — it is the contract violation that turns the
instrument from an observational record into an active arbitration
participant.

The instrument MUST NOT support a "real-time mode" where Layer 2 is
generated synchronously inside the arbitration path. The capture
layer never makes LLM calls. The comparator runs in a separate
process (I-3). The two layers communicate only via the immutable
Layer 1 file (I-1).

A proposal in this direction is rejected at the contract layer.
Re-negotiation requires a contract amendment with explicit reasoning
about why the boundary should be relaxed — and the answer should
remain no.

### 8.9 Automatic heuristic synthesis from corpus data

**Why:** The comparator may identify patterns. The comparator may
NOT generate narrowing rules. There is no auto-tuning loop in this
instrument's contract.

This is the structural protection against the planner-agreement-
frequency optimization risk named in §1's threat articulation. If a
future tool wants to read the corpus and propose narrower changes,
that proposal goes through the same human-review pathway as any
other change to `_tool_filter.py` — never through an automatic
synthesis pipeline that derives heuristics from corpus statistics.

The comparator's outputs are evidence for human decisions, not
direct inputs to the narrower's behavior.

### 8.10 Retroactive enrichment of Layer 1

**Why:** Reinforces I-1 from §2.2 at the discipline-contract layer.
Layer 1 records are written once, immutable thereafter. The
instrument MUST NOT support an "annotate Layer 1 with comparator
results for convenience" feature. Schema migrations write new files;
old files are never rewritten. Comparator output lives in Layer 2,
referenced by `capture_id`, never merged back.

### 8.11 Outcome labeling in Layer 1

**Why:** Reinforces I-2 from §2.2 at the discipline-contract layer.
Layer 1 stays observational. Classification, divergence categorization,
harm assessment — all of these are interpretive judgments that live
in Layer 2 or higher. A future contributor proposing "let's compute
prompt_classification at capture time so it's pre-baked" is asking
to violate the observation/interpretation boundary; the answer is
no, and the field stays in Layer 2.

---

## 9. Failure modes and handling

| Failure | Handling |
|---------|----------|
| Layer 1 write fails (disk full, permission, etc.) | Logged warning at WARNING level. Live request unaffected. |
| Layer 1 record is malformed when read by the comparator | Skip record; log; continue. The comparator emits a `skipped/<reason>` summary at end of run. |
| LLM unreachable during comparator run | Comparator logs and skips that record; the resumable-run feature picks it up on the next invocation. |
| LLM response unparseable / partial / mid-stream timeout | Layer 2 record is written with `divergence_classification = "AMBIGUOUS"` and a structured `comparator_diagnostic` field naming the failure mode. The record is part of the corpus; AMBIGUOUS is a valid output. |
| Identity hash mismatch between Layer 1 and the running comparator's environment | Comparator logs at WARNING and proceeds. The Layer 2 record carries the mismatch detail; analyses can filter on it. Hard-fail would lose data; soft-warn surfaces drift without dropping records. |
| Schema version mismatch in reader | Hard error with a remediation message: "schema_version=N records require reader version M; upgrade or filter." |
| Comparator model unavailable (Ollama doesn't have it pulled) | Hard error before any records are processed; no partial Layer 2 file is written. |

---

## 10. Confirmed decisions

Each of the six bounded questions raised during contract review is
confirmed below. The contract structure does not change; these
decisions parameterize the spec.

1. **Initial seed corpus.** Checked-in, under
   `tests/corpus_seed_prompts.yaml`. Explicit and reviewable beats
   factory-generated for a starting seed; the YAML can be amended
   in normal PRs as the taxonomy refines.

2. **Runtime probe deployment surface.** Binary on/off via
   `FORGE_BRIDGE_DIVERGENCE_CAPTURE=1`. No sampling in v0. Revisit
   if corpus growth becomes unwieldy at probe-on-real-workload scale.

3. **Comparator honors `sensitive=True` routing.** Yes — the
   comparator's choice must reflect what the LLM would have done in
   the same routing context. A `sensitive=True` capture replays
   against local Ollama; a `sensitive=False` capture replays against
   whatever the cloud configuration was at capture time (recorded
   via `topology.backends.anthropic.configured` in Layer 1). Cross-
   provider replays are explicitly out of scope here — that
   territory belongs to `SEED-CROSS-PROVIDER-FALLBACK-V1.5`.

4. **Corpus retention soft trigger.** Revisit at **~1000 records OR
   30 days of probe-on use, whichever first**. Until then, no
   automatic deletion; operator may prune manually. The trigger is a
   soft prompt to re-evaluate retention policy, not an automatic-
   delete rule. Threshold values reconsidered when the trigger fires
   based on actual corpus shape and operator experience.

5. **Layer 2 regeneration semantics on model change.** Side-by-side.
   When the comparator default model changes, both old and new
   Layer 2 records persist (referenced by distinct `comparator_run_id`
   and `comparator_model` fields against the same `capture_id`). The
   side-by-side comparison is itself evidence about the system's
   arbitration sensitivity to model choice — discarding it would
   throw away a load-bearing diagnostic signal.

6. **Comparator location.** `forge_bridge/corpus/comparator.py` with
   a console-script entry. Logical ownership stays in the package
   (versioned, tested, dep-tree shared); runtime invocation remains
   in a separate process per I-3. See Principle 2 in §1: package-
   location is independent of process-boundary.

### MVP sequencing (parameterizes the spec, not the contract)

The full instrument shape is locked above. The implementation lands
in three sequenced gates, each with its own verification:

**Gate 1 — Layer 1 capture only.**
Ship the runtime probe and the test fixture. No comparator. No
Layer 2 schema implementation, no LLM round-trips, no offline
pipeline. **Verification:** schema validation against the §3
contract, required-fields completeness on every emitted record,
source-field correctness (fixture vs runtime), identity-hash
emission. The corpus directory grows with `capture-*.jsonl` files
that conform to the schema; nothing in `compare-*.jsonl` yet.

**Gate 2 — Seed corpus drive.**
Use the test fixture to drive the checked-in seed prompts (decision
#1). The corpus has its first deliberately-curated body of records,
covering every prompt-family cell from the framing's initial
taxonomy with topology pinned by mock. Still no comparator.
**Verification:** every taxonomy cell has at least one captured
record; analytics sanity (a `jq` one-liner can group by
prompt-family and ambiguity_state).

**Gate 3 — First runtime capture run.**
Enable the runtime probe in operator-workstation deployment
(`FORGE_BRIDGE_DIVERGENCE_CAPTURE=1`). Real prompts begin landing in
Layer 1. The seed corpus and runtime corpus are now segregable via
the `source` field. Comparator implementation is the next phase
(Gate 4, separate spec).

This sequencing serves Objective C explicitly: the corpus exists
before any heuristic tuning could be proposed, and the comparator
(the part that requires the LLM) ships only after Layer 1 is proven
sound. A future contributor proposing "let's also implement the
comparator in v0" should be redirected here — the spec sequencing
is part of the structural protection against
"observation-and-classification first" being interpreted as a
suggestion rather than a constraint.

---

## 11. What this contract does NOT cover (deferred to spec)

- Exact module layout / file paths beyond §6's outline
- Async-task plumbing for the runtime probe (the contract requires
  "non-blocking, capture-only"; the spec picks the implementation)
- Comparator CLI argument parsing
- Pytest fixture API surface
- Reader module's exact public API
- Analytics queries / dashboards (out of scope entirely; corpus is
  the artifact, analyses live elsewhere)
- Identity-hash computation algorithm details (sha256 of normalized
  source, sha256 of sorted-tools-with-arg-schemas — exact
  normalization rules are spec-level)

These belong in the spec, not the contract. The contract's job is
ensuring the spec can't drift from the framing.
