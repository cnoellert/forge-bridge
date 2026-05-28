---
milestone: v1.7
thread: A
phase: A.2
phase_name: Ratification + enforced apply — assent as substrate state
status: phase-framing
opened: 2026-05-28
drafted: 2026-05-28
revised:
  - 2026-05-28 (v2 — writing-room cycle absorbed: Thesis adds "what is being ratified" working position + "apply latency model" sync-apply assumption; Q-A2.0 staged_operation positioning added at top of question list as architectural pre-question constraining Q-A2.1/Q-A2.2; Q-A2.1 sharpened with pattern-vs-implementation language + Q-A2.2 coupling note; Q-A2.5 re-grounded with actual call-site count (5 sites: 1 prod + 4 tests); Q-A2.7 elevated to constitutional baseline with explicit sync-apply premise + failure-mode trade-off matrix. No architectural change to original 8 questions; structural additions reflect Creative + DT room contributions.)
  - 2026-05-28 (v3 — second writing-room cycle absorbed Creative + DT Stage 1a catches C1+C2+C3: C1 narrowed "extend-the-primitive" law from broad constitutional reading to scoped primitive-responsibility extension (does NOT prejudge Q-A2.0 or Q-A2.7); C2 specified sync-apply force as common-case-assumption (NOT design constraint; NOT decorative — design center for A.2, edge cases not forbidden); C3 expanded Q-A2.0 cascade to include Q-A2.4 (SSE taxa under staged_operation states) + Q-A2.6 (CLI surface vs forge_approve_staged MCP tool relationship) and named underlying substrate question explicitly ("new authority substrate vs specialization of existing"); added Thesis sub-section "Categories of position in this framing" per Creative's meta-frame insight that v3's job is mostly separation of laws/preferences/assumptions. No new framing-grade catches beyond Creative+DT's three.)
  - 2026-05-28 (v3.1 — third writing-room cycle absorbed Creative + DT polish-grade catches C4+C5: C4 preserved parallel-vs-supersession distinction within "new authority substrate" — high-level axis stays framing-grade, parallel-vs-supersession is discuss-grade distinction signaled explicitly; C5 promoted graph-intent identity from working position to architectural law per Creative ("constitutional position promoted to law — labeling it 'working position' would weaken the law's force"); anchored Q-A2.1..Q-A2.8 initial leans as canonical working-position examples in "Categories of position" sub-section with Q-A2.7 store-and-replay as anchor example; explicitly excluded inherited A.1 contracts from working-position category (substrate facts, not provisional reasoning). Cycle convergence observed per DT: v1→v2 = 3 load-bearing catches; v2→v3 = 3 load-bearing catches; v3→v3.1 = 2 polish catches. Healthy convergence. Close-cursor candidate for the cross-voice cadence pattern.)
type: phase-framing
derives_from:
  - .planning/phases/A.1-thread-a-chat-intent-compile-stage/THREAD-A-FRAMING.md
  - .planning/phases/A.1-thread-a-chat-intent-compile-stage/A.1-CLOSE.md
preceded_by: Phase A.1 — Chat intent-compile stage (CLOSED 2026-05-28 at 242b8e9)
grounding: A.1 substrate primitives (compile_intent / graph_contains_commit_node / run_compile_branch / CompileBranchOutcome / CompileError family) + this-session reads of graph/commit.py, graph/mutation.py, console/_engine.py, cli/main.py for ratify-surface placement + CommitNode.verify() call-site grep (5 sites total)
artifact_role: load-bearing — A.2-DISCUSS-QUESTIONS.md surfaces phase-level ambiguities against this framing; A.2-PLAN.md drafts from converged rulings
---

# A.2 — Phase framing: ratification + enforced apply

> **What this artifact is.** Phase-level framing for A.2, the second
> phase in v1.7 Thread A. Records the architectural positioning A.2
> inherits from Thread A + A.1's close, names the load-bearing scope,
> and surfaces framing-grade questions the discuss stage must resolve.
>
> **Two frontmatter axes.** `status` is lifecycle position
> (phase-framing → phase-discuss → phase-plan → phase-execution →
> phase-close); `type` is artifact category (thread-framing vs
> phase-framing vs close-cursor). A.2's `type` is phase-framing — the
> thread-level framing for Thread A lives at
> THREAD-A-FRAMING.md (co-located in A.1's directory per
> opening-phase convention).
>
> **What this artifact is not.** Not a discuss artifact (does not
> claim convergence on resolved rulings). Not a plan (does not lock
> implementation contracts). The phase plan derives from the discuss
> artifact, which derives from this framing.

## Thesis

A.1 stratified the chat path through compile-and-preview but left the
authority-transition gate stubbed. The R-A1.2 preview-only short-circuit
detects commit-node presence and emits a preview without execution;
no operator assent exists in substrate; no `commit.verify()` extension
reads what assent would record. The authority transition is half-complete
— the inferential path is now stratified through compile, but the
substrate cannot tell a ratified graph from an unratified one.

A.2 closes the loop by making **assent a substrate record**.
Compile output gets a stable identifier; operator decision records
against that identifier as a separate attributable artifact;
`commit.verify()` extends to check both drift validity (already
present) and assent validity (new). The CLI is the operator surface
this phase ships; Console and conversational affordances remain
deferred per Q5.

Per Q5's constitutional line: **the LLM never owns assent.** A.2 must
not introduce any path where model output can stand in for operator
decision. Per FC-5's check-location ruling: **the assent check lives
AT the commit primitive inside `run_chain_steps`**, not as a
pre-execute policy gate in the chat handler or any other consumer.
Enforcement via substrate composition (Q3 lineage), continued from
A.1.

### Categories of position in this framing

Per Creative meta-frame insight (Stage 1a 2026-05-28): v3 separates
position types that v2 had begun to conflate. Distinguishing them is
the bulk of what v3 changed.

- **Architectural law** — binding constitutional invariants A.2
  inherits from Thread A or establishes for A.2. Narrowly scoped
  where applicable; scope explicitly named. Surveyed in
  §"Architectural law (inherited from Thread A, binding)".
  *Examples in A.2:* the LLM never owns assent; ratification
  attaches to graph-intent identity (promoted from working position
  per Creative C5 2026-05-28); primitive-responsibility extension
  (narrowly scoped per Creative C1).
- **Working position** — initial leans on framing-grade open
  questions where the framing constraints already narrow the
  answer but the room hasn't formally ruled. Reasoned (have
  rationale), non-binding (subject to revision at discuss-stage),
  stronger than neutral options (have a direction), weaker than
  architectural law (not enforced). *Canonical example:* Q-A2.7
  store-and-replay lean. *Scope:* the initial leans on
  Q-A2.1..Q-A2.8.
- **Design center / common-case assumption** — A.2's premise about
  which case the architecture optimizes for. Does not forbid edge
  cases; orients the trade-off space. *Example in A.2:* sync-apply
  common-case assumption per Thesis sub-section below.
- **Framing-grade open question** — choices the room hasn't yet
  ruled on. Initial leans offered where the framing constraints
  already narrow the answer. Q-A2.0..Q-A2.8.

**Negative-case exclusions** (categories that look adjacent but
aren't, per Creative C5 2026-05-28):

- **Inherited A.1 contracts are NOT working positions.** A.1's
  shipped substrate primitives (compile_intent, classifier, branch
  helper, regime enumeration, preview wire shape, SSE taxa, grep
  table closure) are substrate facts — load-bearing artifacts from
  a closed phase. Not provisional reasoning subject to revision.
  Surveyed in §"What A.2 inherits from A.1 (load-bearing)".
- **Graph-intent identity is NOT a working position.** Promoted to
  architectural law per Creative C5 2026-05-28 — labeling it
  "working position" would weaken the law's force. The framing
  commits to graph-intent identity constitutionally; if discuss-stage
  contests, that's a law-grade re-positioning, not a directional
  revision.

A position's category matters because each cascades differently if
contested. A law-grade contention shifts what's constitutionally
permitted; a working-position contention shifts a directional lean;
an assumption contention shifts the design center; a framing-grade
open question is decided at discuss-stage.

### What is being ratified? (architectural law per Creative C5 2026-05-28)

A.2's architectural law: **ratification attaches to graph-intent
identity.** Previews are derived views of the ratified graph-intent;
mutation manifests are computed from graph-intent at apply time. The
substrate primitive that holds the assent record references
graph-intent-id, not preview-id or manifest-hash.

Per Creative room contribution 2026-05-28: graph-intent, mutation
manifest, and preview artifact are three distinct candidates for
"what is being ratified." Making this explicit at framing time is
preferable to discovering it half-way through A.2.

**Category promotion (v3 → v3.1):** v3 labeled this a "working
position." Per Creative C5 2026-05-28: constitutional position
should be promoted to architectural law — labeling it "working
position" would weaken the law's force. The framing commits to
graph-intent identity constitutionally; if discuss-stage contests,
that's a law-grade re-positioning, not a directional revision. Bullet
added to §"Architectural law" below.

This law implies that "graph-intent-id" throughout this framing is
the durable identifier; the preview is a derived view rendered from
the graph-intent the operator is being asked to ratify.

### Apply latency model (common-case assumption, per Creative C2 2026-05-28)

A.2 **optimizes for synchronous apply** — operator assent within the
same operator session as preview emission; apply seconds-to-minutes
after assent.

**The architecture does not forbid longer delays.** Longer-latency
cases (operator walks away, returns hours/days later) simply fall
outside A.2's design center and are not solved here. Future async
ratification work will not look like a violation of A.2; A.2 does
not pre-answer what async should do.

Per Creative C2 2026-05-28: this is explicitly a common-case
assumption, NOT a design constraint (would create hidden
architecture; pre-answer Q-A2.3 expiration policy) and NOT decorative
expected-operator-behavior (would make the assumption inert).
The assumption gives Q-A2.3 meaningful decision space: under
sync-apply design center, expiration policy is a UX choice rather
than a constitutional one.

Per DT room contribution 2026-05-28: this design-center calibration
is the load-bearing premise that the Q-A2.7 store-and-replay lean
rides on. If discuss-stage shifts the design center toward
async-tolerance, Q-A2.7's lean shifts toward re-compile.

## What A.2 inherits from A.1 (load-bearing)

A.1's close cursor + the substrate state at `242b8e9` lock several
contracts A.2 builds against:

- **`compile_intent(prompt, tools, ...) -> list[str]`** at
  `router.py:647`. Produces graph-intent as `list[str]` chain-step
  text. Same shape A.2's ratify substrate identifies.
- **`graph_contains_commit_node(steps)` substrate utility** at
  `commit.py:85`. Substrate-grounded classifier — A.2's
  graph-intent-id allocation triggers on the same condition
  (mutation chains only get graph-intent-ids; read-only chains
  execute directly).
- **`run_compile_branch(...)` / `CompileBranchOutcome` regime
  enumeration** at `_chat_compile.py:98`. Four regimes:
  `compiled_non_mutating` (regime 2), `compiled_mutating_preview`
  (regime 3), `chain_aborted`, `compile_error`. A.2 modifies regime
  3 — preview now carries a graph-intent-id; regime 3 returns
  either preview-only (no assent yet) or ratified-preview (assent
  recorded, ready for execution).
- **Preview wire shape (L4 from A.1)**: `{kind, steps[...],
  summary{total_steps, mutating_steps, requires_ratification}}`.
  A.2 extends this shape with a `graph_intent_id` field; the rest
  of the L4 contract is preserved.
- **Five SSE chat-side terminal taxa** (L9 from A.1):
  `compile_complete` / `chain_complete` / `preview_emitted` /
  `chain_aborted` / `compile_error`. A.2 may introduce a new
  intermediate or terminal taxon for the ratified-apply path —
  framing-grade question Q-A2.4 below.
- **handlers.py grep table closure (9/9 at 0)**. A.2 must
  preserve this — no resurrection of `complete_with_tools` /
  `_on_message` / `event: message` / `event: done` /
  `_OrchestrationTerminated` / `enforced_system` in the chat
  consumer.
- **Coexistence architecture** preserved: the three chat regimes
  remain as the chat-side dispatch surface; A.2 doesn't add a
  4th regime, it parameterizes regime 3 with assent-check
  semantics. `complete_with_tools` remains the legacy-agentic
  substrate primitive for non-chat callers.
- **Architectural law**: substrate self-views are first-class
  operator surfaces — derived, not reconstructed. A.2's ratify
  substrate must be a derived view, not a parallel orchestration
  layer.

## What A.2 inherits from Thread A framing

Per THREAD-A-FRAMING.md §"Phase decomposition":

> A.2 — ratification + enforced apply. The substrate ratify motion
> (assent as a substrate record on the preview artifact),
> commit.verify extended to check assent, the CLI ratify surface.
> The authority transition closes end-to-end.

Per Q5 (constitutional):

> A.2 introduces the substrate-side ratify motion + a CLI operator
> surface; Console is later; a conversational affordance, if ever, is
> only thin verbatim transport to the substrate motion, never an
> interpreted "yes."

Per FC-5 (check-location):

> `compile_intent -> preview (stable graph-intent-id) -> operator-CLI
> assent (writes substrate record against graph-intent-id) ->
> run_chain_steps invoked -> assent check happens AT THE COMMIT NODE
> inside run_chain_steps`
>
> The assent check lives AT the primitive, not in front of it. Phase
> N+'s enforcement-via-composition lineage (which Q3 explicitly cites)
> demands the interlock live at the substrate, not as a pre-execute
> policy gate.

These three are framing-binding for A.2 — discuss-stage rulings flow
from them.

## Grounding refresh — verified 2026-05-28 against main @ 242b8e9

| Site | Status |
|---|---|
| `forge_bridge/graph/commit.py:67` — `is_commit_step(text)` | ✓ unchanged from A.1 |
| `forge_bridge/graph/commit.py:85` — `graph_contains_commit_node(steps)` | ✓ A.1 D2 utility intact |
| `forge_bridge/graph/commit.py:98` — `CommitNode` class + `verify(held, fresh) -> CommitVerification` | ✓ drift-only check, NO assent record |
| `forge_bridge/graph/mutation.py:28` — `MutationManifest` 5-field frozen dataclass | ✓ NO assent field |
| `forge_bridge/console/_engine.py:14` — `run_chain_steps(*, steps, tools, mcp, request_id, client_ip, started)` | ✓ sequential, abort-on-first-error; the post-compile executor; A.2's assent check inserts inside this loop at the commit-node step |
| `forge_bridge/console/_chat_compile.py:18-25` — `CompileBranchOutcome` 4-regime enum | ✓ A.1 D3 dataclass intact |
| `forge_bridge/console/_step.py:799` — `CommitNode().verify(manifest, fresh)` | ✓ sole production call site; Q-A2.5 migration baseline |
| `forge_bridge/cli/main.py` — Typer top-level + subgroups (`doctor`, `console`, `mcp`, `flame`, `chat`, `exec`, `run`, `flame-exec`, `graph list/show`, `up`/`down`/`status`) | ✓ A.2's `fbridge ratify` (or chosen subcommand name) inserts at this surface |

**`CommitNode.verify()` call-site count: 5 total** (1 production +
4 tests at `tests/graph/test_commit.py:257/268/279/303`). Migration
cost is trivial either way; Q-A2.5 lean rides on architectural-shape
ground, not migration-cost ground.

**"Ratified" does not exist as substrate state** — confirmed by direct
read of commit.py + mutation.py. A.2 introduces it.

## Phase scope (what A.2 ships)

1. **Graph-intent-id substrate** — stable identifier emitted
   alongside regime-3 preview output. Allocation strategy is
   framing-grade open (Q-A2.1); persistence surface is
   framing-grade open (Q-A2.2). **Identity-model and storage-model
   are tightly coupled** per Creative room contribution 2026-05-28
   — Q-A2.1 + Q-A2.2 resolve TOGETHER.
2. **Assent-record substrate** — operator decision attached against
   graph-intent-id. Shape, storage, expiration semantics all
   framing-grade open (Q-A2.0 staged_operation positioning
   determines whether this is a new substrate or extension of
   existing).
3. **`CommitNode.verify()` extension** — checks both drift and assent
   validity. Signature evolution is framing-grade open (Q-A2.5).
4. **CLI ratify surface** — `fbridge ratify <graph-intent-id>` or
   chosen subcommand name (Q-A2.6); writes the assent record; exits
   with appropriate code for downstream automation.
5. **Apply flow** — how the ratified graph reaches `run_chain_steps`
   for execution. Re-compile vs store-and-replay is framing-grade
   open (Q-A2.7); Thesis common-case assumption is sync-apply.
6. **Chat surface integration** — regime-3 preview now carries the
   graph-intent-id; subsequent chat turn (or out-of-band operator
   action) may reference the graph-intent-id to apply. The chat-side
   SSE taxa for the apply path is framing-grade open (Q-A2.4).

End-to-end flow A.2 closes (under the Thesis working positions):

```
NL → compile_intent → graph-intent (list[str])
   → run_compile_branch → CompileBranchOutcome
   → regime 3 (commit-node present)
   → preview emitted WITH graph-intent-id
   → operator-CLI assent: `fbridge ratify <graph-intent-id>`
   → assent record persisted against graph-intent-id in substrate
   → next chat turn (or direct apply): regime 3 → graph-intent-id lookup
   → assent validity check
   → if valid: run_chain_steps invoked
       → at commit-node step: CommitNode.verify(held, fresh, assent=record)
       → if assent valid AND drift valid → execute the apply
       → if assent invalid OR drift invalid → CommitError taxon
   → if no assent: regime 3 short-circuits (preview-only, as A.1)
```

## Framing-grade open questions (for A.2-DISCUSS-QUESTIONS.md)

These are the load-bearing ambiguities the discuss stage must
converge on before A.2-PLAN.md drafts. Initial positioning offered
where the framing constraints already narrow the answer; remaining
options surfaced for room convergence. **Q-A2.0 is an architectural
pre-question that constrains nearly every downstream question** —
it must resolve first.

### Q-A2.0 — `staged_operation` substrate positioning

**[Architectural pre-question per Creative + DT room contributions
2026-05-28. Constrains Q-A2.1, Q-A2.2, Q-A2.3, Q-A2.4, Q-A2.6, and
Q-A2.8 — must resolve first.]**

**The underlying substrate question (Creative C3 2026-05-28):**

> The room is deciding whether **ratification is a new authority
> substrate** or **ratification is a specialization of an existing
> authority substrate**.

That distinction is the architectural axis. Naming it directly is the
v3 absorption of Creative C3; v2 circled it through the three-shape
enumeration without naming the underlying axis.

**Within "new authority substrate" (Creative C4 2026-05-28):** if the
room chooses "new authority substrate," discuss-stage must still
distinguish **parallel substrate** (shape (a) below) vs **supersession
substrate** (shape (c) below) — these are not equivalent shapes
despite both being "new authority substrate." The high-level axis
(new vs specialization) is the framing-grade question; parallel-vs-
supersession is a discuss-grade distinction within "new" that must be
explicitly signaled so it doesn't silently collapse. The two shapes
have different consequences for projekt-forge (consumer) impact,
scope size, and long-term substrate landscape.

Bridge already ships `staged_operation` substrate
(`forge_bridge/store/staged_operation.py`) with a
`proposed → approved → executed/rejected/failed` state machine + MCP
tools (`forge_list_staged` / `forge_get_staged` /
`forge_approve_staged` / `forge_reject_staged`). A.2's ratification
surface MUST position against this substrate. Three candidate shapes:

(a) **Parallel substrate** (new authority substrate) — A.2 ships its
own assent-record store; `staged_operation` remains for the MCP-side
propose-approve workflow. Two approval surfaces co-exist; consumer
chooses based on origin (chat vs MCP).

(b) **Built on top** (specialization of existing) — A.2's preview is
a `staged_operation` row with `state=proposed`; ratify writes
`state=approved`; apply triggers `state=executed/failed`. Re-uses
shipped substrate; constraint: graph-intent must fit the existing
payload shape.

(c) **Supersession** (replaces existing) — A.2's substrate becomes
the canonical approval lane; `staged_operation` deprecates for the
chat-originated path. Affects MCP tools that consumers
(projekt-forge in production) depend on.

**Writing-room lean is UNRESOLVED.** Original v1 framing implicitly
assumed (a) without naming it; per DT — "load-bearing and unstated
assumption." The room must rule explicitly.

**Independence from architectural law:** the narrowed
extend-the-primitive law (see §"Architectural law" below) applies
to method-vs-helper choices on existing typed primitives. It does
**NOT** prejudge Q-A2.0 — substrate-shape choice is a
different-kind-of-question than primitive-responsibility extension.
Per Creative C1 2026-05-28: the law narrowing is what allows
Q-A2.0 to be discussed honestly without hidden gravitational
pressure toward (b).

**Trade-off summary:**

| Shape | Risk | Reward |
|---|---|---|
| (a) Parallel | Conceptual fragmentation across substrates with similar shape; future maintenance pressure on two approval lanes | A.2 self-contained; no MCP-tool surface changes; smallest A.2 scope by surface count |
| (b) Built on top | graph-intent must fit `staged_operation` payload shape; cascade under (b) is broader than first appears (see below); subtle coupling on existing MCP tool semantics | Substrate-coherence with shipped approval pattern; no new substrate to author |
| (c) Supersession | MCP-tool consumer impact (projekt-forge); biggest scope by surface count; deprecation-migration carry | Single canonical approval lane long-term; cleanest architecture |

**Cascade implications under (b) — expanded per Creative C3 + DT 2026-05-28:**

The hidden question (specialization vs new authority substrate)
touches more downstream questions than v2 enumerated:

- **Q-A2.1 identity** collapses: graph-intent-id =
  `staged_operation` primary key
- **Q-A2.2 storage** collapses: existing `staged_operation` table
- **Q-A2.3 expiration** partial collapse: rides existing state
  machine semantics
- **Q-A2.4 SSE taxa** partial collapse: SSE events may surface
  `staged_operation` states (`proposed` / `approved` / `executed`
  / `rejected` / `failed`) directly rather than inventing new chat-side
  taxa. The L9 invariant (distinct taxa for distinct outcomes) may
  still apply, but the *naming* and *cardinality* shift toward
  the existing state machine.
- **Q-A2.6 CLI naming** partial collapse + new question:
  `fbridge ratify <id>` overlaps with the existing
  `forge_approve_staged` MCP tool. Room must position: parallel
  surfaces (CLI + MCP for same op), one is sugar for the other,
  or they target different state transitions.
- **Q-A2.8 multi-operator** rides existing substrate's
  identity-field decisions (whatever `staged_operation` carries)

**Scope estimate recalibration:** v2 implied (b) was medium-scope
and (c) was milestone-scale. Per DT C3: **(b) may also be larger than
v2 implied** — the cascade above is substantial, and graph-intent
shape may not fit `staged_operation`'s payload schema without
modification (which is its own substrate-migration question). The
shape comparison above is honest about risk; the scope ordering
across (a)/(b)/(c) is no longer obvious.

**Cascade under (c):** Q-A2.1 + Q-A2.2 designed de novo; legacy
`staged_operation` deprecates; potentially milestone-scale rather
than phase-scale A.2.

**Cascade under (a):** Q-A2.1..Q-A2.8 leans below apply as currently
framed.

**Path to resolution at discuss stage:** read `staged_operation`
table shape + the four MCP tools' contracts; test whether
graph-intent fits the existing payload shape; rule on
substrate-coherence vs. fragmentation trade-off vs. scope-blast
trade-off; reckon honestly with the expanded cascade under (b).

### Q-A2.1 — Graph-intent-id allocation strategy

**[Constrained by Q-A2.0. If Q-A2.0 lands as (b), this question
collapses to "use existing primary key."]**

Under Q-A2.0(a) parallel-substrate, how does compile output get a
stable identifier? Three candidate shapes:

(a) **UUID-v4** — random, opaque, decoupled from content. Simple;
no collision concerns; no semantic meaning. Coherent pair with
Q-A2.2(c) append-only JSONL.

(b) **Content-hash** — sha256 over the canonical chain-step text
(or canonical graph-intent representation). Same input → same id.
Natural deduplication. Coherent pair with Q-A2.2(a) new substrate
table OR content-addressed storage.

(c) **Sequence-id from substrate** — monotonic; ordered; auditable
trail. Heavier substrate dependency.

**Initial framing lean (sharpened per DT room contribution
2026-05-28):** (b) content-hash, treating content-hashing as a
**PATTERN** (compatible with phase-4b's `ContentAddressedRepo`
shape, not depending on its specific implementation). If A.2
should USE `ContentAddressedRepo` DIRECTLY (implementation
dependency on phase-4b), then phase-4b needs to be further along
than its current in-flight state before A.2 can lean on it — coupling
debt the room must price in.

**Coupling note with Q-A2.2 (per Creative room contribution
2026-05-28):** content-hash + content-addressed storage is a
coherent pair; UUID + append-only JSONL is a coherent pair;
**content-hash + append-only JSONL is the LEAST coherent
combination and needs explicit justification.** Q-A2.1 and
Q-A2.2 should be resolved TOGETHER at discuss stage, not
independently.

### Q-A2.2 — Assent-record storage substrate

**[Constrained by Q-A2.0 and tightly coupled with Q-A2.1.]**

Under Q-A2.0(a) parallel-substrate, where does the assent record
live? Three candidate shapes:

(a) **New substrate table** — `assent_record` (graph_intent_id,
decided_at, decided_by, ttl, …). Alembic migration. Single source
of truth for ratification archaeology. Coherent pair with Q-A2.1(b)
content-hash OR content-addressed storage.

(b) **Extension of existing `staged_operation` table** — collapses
into Q-A2.0(b).

(c) **JSONL append-only log** under `~/.forge-bridge/assent/`.
Similar to A.1's `graph_store` JSONL pattern (Phase 24). No new SQL
substrate; operator-grep-able archaeology. Coherent pair with
Q-A2.1(a) UUID.

**Initial framing lean (v1 was JSONL; revised per Creative coupling
catch 2026-05-28):** lean DEFERRED to Q-A2.1+Q-A2.2 joint resolution
at discuss stage. The v1 implicit lean was content-hash + JSONL —
Creative correctly identifies this as the least coherent pair. Pick
coherent: either (Q-A2.1 UUID + Q-A2.2 JSONL) for lightweight
append-only archaeology, OR (Q-A2.1 content-hash + Q-A2.2 new table
with content-hash primary key) for content-addressed substrate.

### Q-A2.3 — Expiration / drift-invalidation semantics

**[Partial collapse under Q-A2.0(b); rides existing
`staged_operation` state machine semantics in that shape.]**

Can assent expire? Does compile-drift (different graph produced from
re-compile of same prompt) invalidate prior assent?

Three candidate positions:

(a) **No expiration, drift-invalidates.** Assent against
graph-intent-id-X persists indefinitely; if a re-compile produces
graph-intent-id-Y (different content-hash under Q-A2.1(b)), the
prior assent doesn't apply.
(b) **TTL expiration, drift-invalidates.** Assent has a wall-clock
expiry (24h? configurable?); drift also invalidates.
(c) **No expiration, drift-tolerates (within bounds).** Requires
defining equivalence — risky.

**Initial framing lean:** (a) — simplest semantic; preserves the
constitutional invariant (operator decided on THIS graph, not a
different one). Under the sync-apply common-case assumption (per
Thesis), TTL isn't load-bearing for the design center. (c)
introduces interpretation of "equivalent" that risks the
LLM-owns-assent boundary.

**Re-evaluation trigger:** if the room contests the sync-apply
common-case assumption (e.g., shifts the design center toward
async-tolerance), this question may need a TTL position regardless
of drift semantics.

### Q-A2.4 — Chat-side SSE taxa for the apply path

**[Partial cascade under Q-A2.0(b) per Creative C3 + DT 2026-05-28
— if Q-A2.0(b), SSE events may surface `staged_operation` states
directly rather than inventing new chat-side taxa.]**

Does A.2 add new chat-side terminal taxa for the apply flow? A.1
shipped 5. A.2's apply path produces a new terminal outcome class.

Three candidate shapes:

(a) **Extend regime-2 `chain_complete`** — emit `chain_complete`
on ratified-apply success too. Operator can disambiguate via
the chain body content.
(b) **New terminal taxon `apply_complete`** — distinct event for
"ratified chain executed successfully."
(c) **No chat-side change** — apply happens out-of-band via CLI.

**Under Q-A2.0(b)** — a fourth shape opens:

(d) **`staged_operation`-state-mirroring taxa** — SSE events surface
the underlying state machine: `event: staged_proposed` (preview
emitted) → `event: staged_approved` (ratify recorded) →
`event: staged_executed` (apply succeeded) / `event: staged_failed`
(apply failed). The L9 invariant (distinct taxa for distinct
architectural outcomes) holds via existing state machine cardinality
rather than newly-invented taxa.

**Initial framing lean (Creative + DT concur on (b) 2026-05-28
under Q-A2.0(a)):** (b) — A.1's L9 invariant was distinct event taxa
for distinct architectural outcomes. *Ratified mutation applied* and
*non-mutating chain completed* are different authority transitions.
Per `[[feedback-description-layer-multi-register-surface]]`: distinct
registers reach distinct behaviors.

**Under Q-A2.0(b):** lean SHIFTS to (d) — substrate-coherence with
the existing state machine. Adding (b) AND (d) under (b) would
duplicate the state-machine vocabulary at the chat surface.

### Q-A2.5 — `CommitNode.verify()` signature evolution

Three candidate shapes:

(a) **Add optional `assent` kwarg** — `verify(held, fresh,
assent=None) -> CommitVerification`. When `assent` is None,
drift-only check (backward compat). When provided, both checks
fire. CommitVerification gets new fields (`assent_valid`,
`assent_record`).
(b) **New sibling method** — `verify(held, fresh)` stays drift-only;
new `verify_with_assent(held, fresh, assent)` adds assent check.
(c) **Always-required `assent` argument** — `verify(held, fresh,
assent)`; callers pass None explicitly to skip.

**Call-site grounding (per DT room contribution 2026-05-28):** 5
total call sites (`console/_step.py:799` production + 4 tests in
`test_commit.py`). Migration cost trivial either way; lean rides
on architectural-shape ground, not migration cost.

**Initial framing lean — extended-primitive (per Creative room
contribution 2026-05-28):** (a) optional `assent` kwarg.

This is the narrowly-scoped extend-the-primitive law in action
(see §"Architectural law" below). `commit.verify(...)` already owns
the authority-gate responsibility; A.2 extends that responsibility
rather than reconstructing it at a higher layer:

```python
# A.2 extension — authority lives INSIDE the primitive
verification = commit_node.verify(held, fresh, assent=assent_record)
```

The anti-pattern is reconstruction at a higher layer:

```python
# DO NOT WANT — moves authority OUT of the primitive
if ratified:
    verification = commit_node.verify(held, fresh)
```

The first carries authority inside the substrate primitive; the
second moves authority to consumer code. The sibling-method shape
(b) is a structurally-cleaner version of the anti-pattern (still
two-call composition at the consumer); (c) breaks backward compat
without architectural gain.

### Q-A2.6 — CLI surface naming

**[Partial cascade under Q-A2.0(b) per Creative C3 + DT 2026-05-28
— `fbridge ratify` overlaps with existing `forge_approve_staged`
MCP tool under that shape.]**

Where does the ratify operation sit in the `fbridge` Typer hierarchy?
Three candidate shapes:

(a) **Top-level `fbridge ratify <graph-intent-id>`** — flat; matches
`chat`, `exec`, `run`, `flame-exec` top-level pattern.
(b) **Subgroup `fbridge assent <subcommand>`** — anticipates
multiple assent operations (`grant`, `revoke`, `list`, `show`).
(c) **Subgroup under existing `fbridge graph`** — co-locates with
the existing `graph list` and `graph show` debug surface.

**Under Q-A2.0(b)** — additional positioning required:

If A.2 ships `fbridge ratify` AND `staged_operation` already exposes
`forge_approve_staged` (MCP tool), the room must position the
relationship: (i) parallel surfaces (CLI + MCP for the same
operation), (ii) one is sugar for the other (CLI delegates to the
same code path as the MCP tool, or vice versa), or (iii) they target
different state transitions in the lifecycle.

**Initial framing lean (Creative concur 2026-05-28 — don't
over-design):** (a) — top-level, single verb. Matches existing
top-level command pattern. (b) anticipates a feature surface that
may not need a subgroup until it exists; the project pattern has
been to let subcommand hierarchies emerge from real pressure
rather than reserving them early. (c) co-locates with debug-grade
surface — wrong register; ratify is operator-action, not
debug-introspection read.

**Under Q-A2.0(b):** position the CLI↔MCP relationship explicitly in
the discuss stage. The lean above is independent of that
positioning; the CLI surface shape is (a) regardless, but the
delegation pattern shifts.

### Q-A2.7 — Apply flow: re-compile vs store-and-replay

**[Constitutional-grade question per Creative room contribution
2026-05-28. The lean below is the load-bearing position for A.2's
authority-transition thesis; rides the Thesis sync-apply
common-case assumption.]**

**Independence from architectural law (per Creative C1 2026-05-28):**
the narrowed extend-the-primitive law does NOT prejudge this
question. Apply-flow choice is a substrate-shape question, not a
primitive-responsibility extension question. The room can discuss
honestly.

After assent is recorded, how does the ratified graph reach
`run_chain_steps`? Two candidate shapes:

(a) **Store-and-replay** — the preview-emit step persists the
`list[str]` chain-step text alongside the graph-intent-id. Apply
flow looks up the persisted chain by graph-intent-id and feeds it
directly to `run_chain_steps`.

(b) **Re-compile + hash gate** — apply re-runs `compile_intent` on
the original prompt; if the re-compile produces the same content-hash
(per Q-A2.1(b)) as the assented preview, assent applies and the
freshly-compiled graph runs.

**Initial framing lean — under the Thesis sync-apply common-case
assumption (Creative + DT room contribution 2026-05-28):**
(a) store-and-replay.

The authority chain Thread A is building:

```
NL → compile → graph-intent → preview → ratify
                                          ↓
                              replay exact graph-intent
                                          ↓
                                        commit
```

Not:

```
NL → compile → graph-intent → preview → ratify
                                          ↓
                                      recompile
                                          ↓
                                        execute
```

The second shape quietly hands authority back to the compiler
between assent and apply. Per Creative: *"even if the natural-language
request is identical, the compile stage is inferential. The entire
point of Thread A was to move authority away from inference at the
boundary."*

**Failure-mode comparison (per DT room contribution 2026-05-28):**

| Failure mode | Store-and-replay | Re-compile + hash gate |
|---|---|---|
| LLM sampling noise between assent + apply | impossible (no second LLM call) | UX-catastrophic — re-ratification storm on noise |
| Substrate drift (tool deleted/renamed) | caught at run-time via existing `CompileToolUnknown` taxa | caught at hash boundary before apply attempt |
| Sync apply latency (seconds-minutes; A.2 design center) | both shapes identical | both shapes identical |
| Async apply latency (hours-days; outside A.2 design center per Thesis) | safer (no LLM dependency) | substrate-drift detection more valuable |

**Re-evaluation trigger:** the Q-A2.7 lean rides the Thesis sync-apply
common-case assumption. If discuss-stage shifts the design center
toward async-tolerance, Q-A2.7's lean shifts toward (b). The trade-off
matrix above is the decisive substrate at that point.

Per Q5's constitutional line: ratification ATTACHES TO the specific
graph-intent the operator assented to. Store-and-replay binds this
constitutionally; re-compile binds it
content-hash-equality-conditionally (modulo LLM sampling). Under the
sync-apply design center, the first is structurally
operator-decided-on-this-graph; the second is statistically
operator-decided-on-this-graph.

### Q-A2.8 — Multi-operator semantics

**[Partial cascade under Q-A2.0(b) — rides existing
`staged_operation` identity-field decisions.]**

Current scope is single-operator (no auth — SEED-AUTH-V1.5 deferred).
Should A.2's assent record include a placeholder operator-identity
field for future-proofing, or stay identity-free?

Two candidate positions:

(a) **Future-proof with operator-identity field** — assent record
carries a `decided_by` field (string, currently `"local"`). When
auth lands (SEED-AUTH-V1.5), the field already exists and migration
is just population.
(b) **Identity-free now, migrate later** — assent record is
identity-free. When auth lands, alembic migration adds the field.

**Initial framing lean:** (a) — placeholder field is structurally
free (one string column / one JSONL key) and future-proofs the
substrate naturally. Per
`[[feedback-explicitly-unbound-vs-implicitly-rejected]]`: leave the
maneuverability open; reject only when architecturally prohibited.
A `decided_by="local"` placeholder is explicit deferral; absence is
implicit rejection.

## Out of scope (framing-grade)

- **Console / Web UI ratification surface.** Q5 explicit: A.2 ships
  CLI; Console is later. Wire-shape questions for Console
  ratification belong to a future phase.
- **Conversational ratification affordance.** Q5: if ever shipped,
  only as thin verbatim transport to the substrate motion. Not in
  A.2.
- **Authentication.** SEED-AUTH-V1.5; v1.6+ scope. A.2 may include
  a placeholder identity field (Q-A2.8) but does not introduce
  auth machinery.
- **Asynchronous apply latency model.** Thesis sync-apply common-case
  assumption (per Creative C2): A.2 optimizes for sync apply; does
  not forbid longer delays; does not solve async ratification
  workflows. Future async work falls outside A.2's design center,
  not in violation of A.2.
- **Multi-turn graph-intent persistence.** A.1 Gap #4 explicit out
  of scope; A.2 preserves the per-turn statelessness of
  graph-intent. The graph-intent-id substrate is per-turn but stable
  within the turn — not multi-turn accumulation.
- **Modifying exec.** Both lenses (exact / inferential) target one
  substrate. A.2 doesn't modify exec's dispatch path; the assent
  check at the commit primitive is exec-shared substrate per Q3
  composition.
- **Re-architecture of `run_chain_steps`.** A.2 inserts assent
  check at the commit-node step inside the existing executor;
  does not replace or split the executor.
- **F-D3-1 close-cursor follow-up.** Already landed at c32d786
  (PR15-omission grounded test). No A.2 carry.

## Architectural law (inherited from Thread A, binding)

Substrate self-views are first-class operator surfaces — derived, not
reconstructed. A.2 inherits and applies:

- **Ratification attaches to graph-intent identity** (promoted from
  working position per Creative C5 2026-05-28) — previews and
  manifests are derived views; the substrate primitive that holds
  the assent record references graph-intent-id, not preview-id or
  manifest-hash. Contesting this is a law-grade re-positioning, not
  a directional revision.
- **Assent record is derived substrate state** — graph-intent-id +
  decision + decided_at; not a separate orchestration layer.
- **CLI ratify surface is a derived operator surface** —
  thin shell over `assent_record` write; does not interpret intent.
- **The LLM never owns assent** (Q5 constitutional) — A.2 must
  not introduce any path where model output stands in for operator
  decision. The CLI is the operator surface; the conversational
  path (if ever) is thin verbatim transport.
- **Enforcement via substrate composition** (Q3 + Phase N+
  lineage) — assent check lives AT the commit primitive inside
  `run_chain_steps`, not as a pre-execute policy gate.
- **Primitive-responsibility extension** (narrowly scoped per
  Creative C1 2026-05-28) — *when an existing typed primitive
  already owns a responsibility, extend that primitive before
  introducing helper-layer reimplementations of the same
  responsibility*. **Scope:** applies to method-vs-helper choices
  on existing typed primitives. **Does NOT prejudge:** substrate-shape
  choices (Q-A2.0 staged_operation positioning), apply-flow
  choices (Q-A2.7 store-and-replay vs re-compile), or other
  substrate-design questions where the responsibility is being
  newly assigned rather than extended. The law applies at
  Q-A2.5 (CommitNode.verify() owns the authority-gate
  responsibility; A.2 extends it). Other questions where this law
  is sometimes superficially invoked (e.g., "extend
  staged_operation" under Q-A2.0(b), "extend compile_intent" under
  Q-A2.7(b)) are different-kind-of-questions and resolve on their
  own merits.
- **Coexistence architecture preserved** — the three chat regimes
  remain; A.2 parameterizes regime 3 with assent semantics; does
  not add a 4th regime.

## Status

**Phase framing v3.1.** Drafted 2026-05-28 against:
- Thread A framing (THREAD-A-FRAMING.md)
- A.1 close cursor (A.1-CLOSE.md)
- A.1 discuss artifact (A.1-DISCUSS-QUESTIONS.md) — particularly Q5
  + FC-5 carries
- Current main state at `242b8e9` (A.1 close commit)
- Direct grounding reads of `forge_bridge/graph/commit.py`,
  `forge_bridge/graph/mutation.py`,
  `forge_bridge/console/_engine.py`,
  `forge_bridge/console/_step.py`,
  `forge_bridge/cli/main.py`
- CommitNode.verify() call-site grep (5 total: 1 production + 4 tests)

v1 → v2 absorbed first writing-room cycle (3 load-bearing catches:
Q-A2.0 elevated; graph-intent identity named; Q-A2.7 to constitutional
baseline; Q-A2.1/Q-A2.2 coupling; extend-the-primitive promoted to
law).

v2 → v3 absorbed second writing-room cycle (3 load-bearing catches):
C1 narrowed extend-the-primitive law to scoped
primitive-responsibility-extension (does NOT prejudge Q-A2.0 or
Q-A2.7); C2 specified sync-apply force as common-case assumption
(NOT design constraint; NOT decorative); C3 expanded Q-A2.0 cascade
to include Q-A2.4 + Q-A2.6 and named underlying substrate question
explicitly (new authority substrate vs specialization of existing);
added Thesis sub-section "Categories of position in this framing"
per Creative's meta-frame insight that v3's job is mostly separation
of laws / preferences / assumptions.

v3 → v3.1 absorbed third writing-room cycle (2 polish-grade catches):
C4 preserved parallel-vs-supersession distinction within "new
authority substrate" (high-level axis stays framing-grade,
parallel-vs-supersession is discuss-grade distinction signaled
explicitly at Q-A2.0); C5 promoted graph-intent identity from working
position to architectural law per Creative ("labeling it 'working
position' would weaken the law's force"); anchored Q-A2.1..Q-A2.8
initial leans as canonical working-position examples in "Categories
of position" sub-section with Q-A2.7 store-and-replay as anchor
example; explicitly excluded inherited A.1 contracts from
working-position category (substrate facts, not provisional
reasoning).

**Cycle convergence observation (per DT close-cursor candidate
2026-05-28):**

| Cycle | Catches absorbed | Catch size |
|---|---|---|
| v1 → v2 | 3 framing-grade | Load-bearing |
| v2 → v3 | 3 framing-grade | Load-bearing |
| v3 → v3.1 | 2 polish-grade | Polish |

Catch count + size both decreasing per cycle = healthy convergence.
Three writing-room passes (DT v1 positioning → Creative absorption +
meta-frame → DT v2 catches → Creative absorption → DT v3 catches →
Creative absorption specs → DT v3.1 sign-off) is the right depth for
a framing-grade artifact of this consequence. Cross-voice cadence
functioning as designed.

**Stage 1a SIGN-OFF on v3.1 absorption specs (Creative + DT
2026-05-28).** No further cross-voice cycle needed unless v3.1 itself
introduces structural issues — which the absorption specs above
don't seem at risk of doing (both surgical edits to existing
sections, not new structural additions).

**Motion ratified:** v3.1 commits as A.2 framing-of-record.

Once committed, A.2-DISCUSS-QUESTIONS.md opens against Q-A2.0..Q-A2.8
and the room converges on grounded rulings. A.2-PLAN.md drafts in
code-handoff format from those rulings; goes to Stage 1b before
implementation handoff.
