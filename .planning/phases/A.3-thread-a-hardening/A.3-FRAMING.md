---
milestone: v1.7
thread: A
phase: A.3
phase_name: Hardening — operational integrity of the authority chain
status: phase-framing
opened: 2026-05-29
drafted: 2026-05-29
revised:
  - 2026-05-29 (v3 — second cross-voice cycle absorbed. Path X selected over Path Y per DT lean + Creative anchor: tighten anti-scope + tighten leans rather than widen anti-scope. Two framing-grade boundary-policing catches (B1 + B2) both surfaced independently by DT cycle-2 sweep AND Creative cycle-2 anticipated filter ("Does auth-hook language remain hook-shaped, or does it start acquiring lifecycle, storage, identity, or workflow assumptions?"). Self-referential discipline working as designed: the boundary-policing meta-frame anchored in Thesis per Creative cycle-1 caught two of the framing's own leans. B1 Q-A3.3 auth-seed integration: writing-room lean shifts from (a) optional kwarg hook on AssentRecordRepo.ratify() to (i) documentation-only — A.3 documents the future SEED-AUTH-V1.5 integration shape; ships NO code path; NO signature change to A.2-shipped substrate. The (a)/(c) variants are preserved as room-contestable options but called out as architectural extension, not pure hardening. B2 Q-A3.5 audit ergonomics: writing-room lean shifts from (b) MCP tool / HTTP endpoint to (i) Python helpers in forge_bridge.console.helpers — operator REPL / scripts only; NO MCP tool registration, NO HTTP endpoint, NO new wire surface, NO Pydantic schema, NO sanitization at read boundary. The (b)/(c) variants preserved as room-contestable but called out as substrate extension. Q-A3.0(c) lean PRESERVED but with narrowed-sub-scope qualifier — under tightened Q-A3.3 + Q-A3.5, the difference between (c) and (b) shrinks to "Sub-scope 3 = documentation only." Room may rule (b) at discuss-stage if Sub-scope 3 docs ride with Sub-scope 2's doc deliverable. Meta-observation: the v1+v2 leans on Q-A3.3 + Q-A3.5 created architecture under the cover of "operational hardening" — exactly the failure mode Creative's discipline-scaffold meta-frame names. Path X absorption restores honest hardening shape. Cycle-2 catch count 2 (lower than A.2 cycle-2's 3) but catch SIZE structural — Q-A3.3 + Q-A3.5 leans shifted via discipline. Cycle-3 expected very small if Path X absorption is clean.)
  - 2026-05-29 (v2 — first cross-voice cycle absorbed. Framing-grade catches: F1 Thesis "architecturally complete" replaced with "architecturally sufficient" per [[feedback-operational-maturity-not-completeness]] — victory-lap voice inverts the methodology stack's maturity signature; F2 Q-A3.5(c) audit-event subscription gains explicit Q5-watch flag — (c) is constitutional ONLY for non-LLM consumers; LLM consumers that interpret event streams into ratification-shaped output violate Q5; F3 new sub-section under §"What A.3 inherits from A.2" enumerates R-A2.1..R-A2.8 with one-line preservation notes (R-A2.7 store-and-replay gets the load-bearing treatment — A.3 observability MAY surface chain content read-only; MUST NOT introduce "verify-this-still-applies" or "preview-the-apply" patterns that bridge into recompile semantics). Polish-grade catches: P1 Q-A3.7 reframed from "A.3 closes Thread A" to "A.3 carries Thread A toward closure" — A.3 SIGNALS at close cursor; Thread A framing or v1.7 milestone RULES; layer-ownership corrected; P2 Q-A3.4 mcp_http supervision folded under Sub-scope 2 with explicit "observability of supervision state, not supervision itself" qualifier; P3 Q-A3.0 gains "Path to resolution at discuss stage" sub-bullet per A.2-FRAMING Q-A2.0 precedent; P4 implementation-arc archaeology line expanded with concrete D5 + D7 implications for A.3 (substrate-before-consumer pattern validation + httpx.AsyncClient/ASGITransport test-infrastructure shape). Plus: Creative verbatim phrase anchored in Thesis as boundary-policing meta-frame ("the strongest version of A.3 is probably the one that proves A.1+A.2 were sufficient rather than the one that creates a third architectural layer above them"). Cycle-2 watch surface per Creative: boundary-policing — hardening proposals quietly crossing from observability into architecture, from hooks into scaffolding, from closure into expansion. Cross-voice cadence 3→3→2 trajectory expected per A.2-FRAMING precedent.)
type: phase-framing
derives_from:
  - .planning/phases/A.1-thread-a-chat-intent-compile-stage/THREAD-A-FRAMING.md
  - .planning/phases/A.2-thread-a-ratification-enforced-apply/A.2-CLOSE.md
preceded_by: Phase A.2 — Ratification + enforced apply (CLOSED 2026-05-29 at bebf24a)
grounding: A.2 shipped substrate (AssentRecord / AssentRecordRepo / 4 assent.* event types / CommitNode.verify assent extension / fbridge ratify CLI / event: apply_complete) + this-session reads of forge_bridge/cli/runtime_doctor.py (6-row doctor pattern), A.2-CLOSE.md "Carried Forward" list, operator-reported deployment-state observations (mcp_http not listening + Flame bridge dispatch failure during fbridge doctor --json)
artifact_role: load-bearing — A.3-DISCUSS-QUESTIONS.md surfaces phase-level ambiguities against this framing; A.3-PLAN.md drafts from converged rulings
---

# A.3 — Phase framing: hardening — operational integrity of the authority chain

> **What this artifact is.** Phase-level framing for A.3, the third
> phase in v1.7 Thread A. Records the architectural positioning A.3
> inherits from Thread A + A.2's close, names the load-bearing scope
> (operational hardening, NOT new substrate), and surfaces
> framing-grade questions the discuss stage must resolve.
>
> **Two frontmatter axes.** `status` is lifecycle position
> (phase-framing → phase-discuss → phase-plan → phase-execution →
> phase-close); `type` is artifact category (thread-framing vs
> phase-framing vs close-cursor). A.3's `type` is phase-framing —
> the thread-level framing for Thread A lives at
> THREAD-A-FRAMING.md (co-located in A.1's directory per
> opening-phase convention).
>
> **What this artifact is not.** Not a discuss artifact (does not
> claim convergence on resolved rulings). Not a plan (does not lock
> implementation contracts). The phase plan derives from the discuss
> artifact, which derives from this framing.

## Thesis

A.1 + A.2 closed the inferential-authority chain end-to-end: NL →
compile → graph-intent → preview → ratify → apply. The substrate
exists; the operator surface exists; the audit trail exists. What
A.2 shipped is **architecturally sufficient** for the sync-apply
common-case A.2 designed for — the authority chain's substrate
surface is closed for that scope. Per
`[[feedback-operational-maturity-not-completeness]]`: this artifact
uses operational-maturity-sufficient-for-handoff language, NOT
architecture-is-now-complete language; victory-lap voice inverts
the methodology stack's own maturity signature.

What A.2 shipped is **operationally fresh**. The substrate has been
exercised against the test DB end-to-end (A.2 D9) and against a
discrete CLI surface, but the production authority chain has not
yet been:
- exercised against a live Flame project under operator UAT
- observed across a series of operator-initiated mutation cycles
- recovered cleanly from the failure modes the L8 envelope
  enumerates
- surfaced through operator observability (doctor rows, audit-event
  consumers, structured logs at production density)
- integrated with auth identity (deferred per SEED-AUTH-V1.5)

A.3's thesis: **operational hardening of what A.1+A.2 architecturally
closed.** The authority chain stays exactly as A.2 shipped it; A.3
ensures the closure is observable, recoverable, and operationally
trustworthy in production.

A.3 ships NO new substrate primitives. A.3 ships NO new architectural
rulings. The framing-grade questions below are operational scope
decisions, not architectural ones. Per
`[[feedback-anti-scope-discipline-under-pressure]]`: when
operational pressure surfaces during A.3 (e.g., "should we also
rebuild this?"), the answer is NO — A.3 hardens what shipped; it
does not reopen A.2's substrate.

**Boundary-policing meta-frame** (Creative cycle-1, 2026-05-29):
*"The strongest version of A.3 is probably the one that proves
A.1+A.2 were sufficient rather than the one that creates a third
architectural layer above them."* The discipline scaffold: A.3
proves sufficiency by hardening; it does NOT prove sufficiency by
extending. Hardening proposals that quietly cross from
observability into architecture, from hooks into scaffolding, from
closure into expansion ARE the failure modes A.3 must avoid. Each
Q-A3.x lean below is tested against the filter: *"Does this improve
operational trustworthiness of A.2, or does it quietly introduce a
new architecture?"* If the latter, the proposal belongs in a
different phase (or a different thread / milestone).

### Categories of position in this framing

Inherited from A.2-FRAMING.md v3.1's category discipline (Creative
meta-frame, 2026-05-28):

- **Architectural law** — binding constitutional invariants A.3
  inherits from Thread A + A.2. NOT reopened by A.3.
- **Working position** — initial leans on framing-grade open
  questions where the framing constraints already narrow the
  answer. Reasoned (have rationale), non-binding (subject to
  revision at discuss-stage), stronger than neutral options
  (have a direction), weaker than architectural law.
- **Design center / common-case assumption** — A.3's premise
  about what operational shape it optimizes for. Does not forbid
  edge cases; orients the trade-off space.
- **Framing-grade open question** — choices the room hasn't yet
  ruled on. Initial leans offered where the framing constraints
  already narrow the answer. Q-A3.0..Q-A3.7.

**Negative-case exclusions:**
- **A.2 substrate is NOT reopened by A.3.** AssentRecord shape,
  AssentRecordRepo state machine, 4 assent.* event types,
  CommitNode.verify(assent=...) signature, fbridge ratify CLI,
  event: apply_complete SSE taxon — all preserved verbatim. A.3
  does not modify any A.2-shipped contract.
- **A.1 substrate is NOT reopened by A.3.** compile_intent,
  CompileError family, graph_contains_commit_node,
  _chat_compile.py regime enum + run_compile_branch, 5 A.1
  chat-side terminal taxa — all preserved.
- **Thread A architectural laws are NOT reopened by A.3.**
  Surveyed in §"Architectural law" below.

### Operational design center (common-case assumption)

A.3 **optimizes for single-operator dev/UAT operational shape** —
one workstation, one operator, one daemon, sync-apply common case
(inherited from A.2). The architecture does not forbid
multi-operator or multi-daemon shapes; those simply fall outside
A.3's design center and are not solved here. SEED-AUTH-V1.5 (when
shipped) will reach those shapes; A.3 prepares the integration
surface but does not solve multi-operator semantics.

Per `[[feedback-distinct-success-criteria-per-adjacent-layer]]`:
the operational hardening success criteria stay attached to the
operational-shape layer. Architectural success (A.2's authority
chain works correctly) is INHERITED, not redefined. UX wins
(better doctor output, cleaner failure envelopes) ride as
ADDITIONAL, not laundered into authority-chain success.

## What A.3 inherits from A.2 (load-bearing)

A.2's close cursor at `5e78f62` and the substrate state at
`bebf24a` lock several contracts A.3 builds against:

- **`AssentRecord` core dataclass** — 8 typed attributes per
  L1-A.2 (graph_intent_id, chain_steps, status, decided_by,
  decided_at, applied_at, apply_result, apply_failure_reason).
  Unchanged by A.3.
- **`AssentRecordRepo` state machine** — proposed → ratified →
  applied | failed. 4 transitions in `_ALLOWED_TRANSITIONS`; 4
  corresponding event types. Unchanged by A.3.
- **4 `assent.*` audit events** — assent.proposed /
  assent.ratified / assent.applied / assent.failed. Wire shape
  per L6-A.2. Unchanged by A.3. **A.3 may add consumer-side
  ergonomics over this event surface (Q-A3.5) without modifying
  the event shape.**
- **`CommitNode.verify(held, fresh, assent=None)` signature** —
  optional assent kwarg, dual validity signals
  (`matched` + `assent_valid`). 5 call sites (1 prod at
  `_step.py:799` + 4 tests at `test_commit.py:259/268/279/303`).
  Unchanged by A.3.
- **`fbridge ratify <graph_intent_id>` CLI surface** — top-level
  subcommand, atomic ratify+apply, exit codes 0/1/2. Unchanged
  by A.3. **A.3 may add observability flags (Q-A3.4) without
  modifying core semantics.**
- **`event: apply_complete` SSE terminal taxon** — 6th chat-side
  terminal taxon. Unchanged by A.3.
- **R-A2.0(a) parallel-substrate ruling** — `staged_operation`
  + `assent_record` coexist as distinct constitutive substrates.
  Bridge is bookkeeper for the former; bridge is executor for
  the latter. Unchanged by A.3. **A.3 explicitly does NOT
  reopen this ruling; consolidation (if ever) is a future-phase
  motion.**
- **Sync-apply common-case assumption** — design center for the
  authority chain. Preserved by A.3 verbatim.
- **3 chat regimes coexistence architecture** — preserved.

### A.2 framing rulings (inherited verbatim, NOT reopened)

Per Stage 1a F3 absorption: A.2's discuss-stage rulings
R-A2.1..R-A2.8 are load-bearing for A.3's substrate-preservation
discipline. Enumerated explicitly so plan-stage drift is mechanically
preventable.

- **R-A2.1** — graph_intent_id is the first 12 characters of
  sha256-hex over canonical JSON of `{"chain_steps": list[str]}`.
  A.3 observability surfaces graph_intent_id verbatim as the
  operator-facing identifier; does NOT re-derive identity from
  alternative content (e.g., re-canonicalizing under a different
  scheme).
- **R-A2.2** — `assent_record` substrate is a
  `ContentAddressedRepo` subclass with the chain_steps body
  immutable post-insert. A.3 does NOT mutate chain_steps; does NOT
  introduce a "graph-intent versioning" pattern that would relax
  the immutability discipline.
- **R-A2.3** — No expiration on assent records; drift-invalidates
  at apply time. A.3 does NOT introduce TTL semantics; does NOT
  add periodic-cleanup-of-stale-pending-records workflows. (The
  doctor-row count of pending records per Q-A3.2 is observability;
  cleanup is operations, not A.3.)
- **R-A2.4** — `event: apply_complete` is the 6th chat-side
  terminal taxon; failure-side taxa reuse `event: chain_aborted`
  (existing) for drift_invalid / chain_aborted classes; new
  `event: error` for record-not-found / illegal-state. A.3 does
  NOT introduce a 7th chat-side terminal taxon for ratification
  state.
- **R-A2.5** — `CommitNode.verify(held, fresh, assent=None)`
  optional-kwarg extends primitive at the substrate level
  (extend-the-primitive law). A.3 does NOT re-implement
  authority-gate logic at higher consumer layers; does NOT add a
  pre-execute policy gate elsewhere.
- **R-A2.6** — `fbridge ratify` is the top-level CLI subcommand
  for the authority-attached substrate; `forge_approve_staged`
  remains the parallel surface for `staged_operation`. A.3 may
  add observability flags to `fbridge ratify` (e.g., `--show-chain`)
  but does NOT add semantic flags that modify the ratify operation
  (e.g., `--force-apply-without-verify`).
- **R-A2.7** — **STORE-AND-REPLAY (constitutional, load-bearing
  for A.3).** Apply path runs the EXACT chain the operator
  decided on; no re-compile, no re-validation against fresh
  substrate state. A.3 observability MAY surface chain content
  read-only (Console doctor-row preview; CLI `--show-chain`); A.3
  MUST NOT introduce "verify-this-still-applies" or
  "preview-the-apply-result" or "dry-run-the-apply" patterns that
  bridge into recompile semantics. The constitutional positioning:
  the operator's authority binds to the specific graph-intent
  they assented to, not to a freshly-derived equivalent. A.3
  hardening must preserve this BIND, not loosen it under
  operational pressure.
- **R-A2.8** — `decided_by` is a free-string placeholder; SEED-
  AUTH-V1.5 will populate from authenticated identity when auth
  lands. A.3 may add the validation hook surface per Q-A3.3 lean
  but does NOT shift `decided_by` semantics; does NOT validate
  against any authority before SEED-AUTH-V1.5.

## What A.3 inherits from Thread A framing

Per THREAD-A-FRAMING.md §"Phase decomposition":

> A.3 — hardening. Surfaced once A.1/A.2 land.

The thread-level framing intentionally left A.3's specific scope
under-specified, to be surfaced empirically AFTER A.1/A.2 shipped.
Now that A.2 has shipped (2026-05-29 at `bebf24a`), this framing
surfaces the scope candidates based on:
- A.2-CLOSE.md "Carried Forward" list (4 items)
- Operator deployment-state observations (mcp_http supervision)
- A.2 implementation-arc archaeology (2 defects caught) — per
  Stage 1a P4 absorption, the defects inform A.3 specifically:
  - **D5 missing-adoption catch** validates the
    `[[substrate-before-consumer-landing]]` pattern at
    implementation time (substrate-first tests caught the gap
    pre-commit). A.3's substrate-shape preservation discipline
    rides this pattern — A.3 ships consumers (doctor row,
    convenience query surface, validation hook) ON TOP of A.2's
    immutable substrate; substrate-first test patterns apply.
  - **D7 TestClient + asyncpg cross-event-loop conflict** was
    resolved with `httpx.AsyncClient(transport=ASGITransport(app=...))`.
    A.3 UAT test infrastructure (Sub-scope 1) should adopt the
    same pattern to avoid the conflict the
    `[[project-v1-4-x-harness-debt]]` memory documents. Per the
    A.2 amendment to that memory: the pattern is now operational
    discipline within the project.
- The phase decomposition's implicit positioning (NOT new
  architecture)

Per Q5 (constitutional, inherited from Thread A):

> The LLM never owns assent.

A.3 must preserve this verbatim. Operational hardening that
weakens Q5 (e.g., letting the model summarize ratification state
in a way that could be interpreted as decision-making) is
prohibited.

Per FC-5 (check-location, inherited from A.2):

> The assent check lives AT the commit primitive inside
> `run_chain_steps`, not as a pre-execute policy gate.

A.3 must preserve this. Operational observability that surfaces
assent state to operators is fine; operational logic that
re-enforces or shortcuts the substrate check is prohibited.

These two are framing-binding for A.3 — discuss-stage rulings
flow from them.

## Grounding refresh — verified 2026-05-29 against main @ bebf24a

| Site | Status |
|---|---|
| `forge_bridge/core/assent.py` — `AssentRecord` dataclass | ✓ shipped per L1-A.2 |
| `forge_bridge/store/assent_record_repo.py:89-92` — `_TRANSITION_EVENTS` map (4 assent.* event types) | ✓ shipped per L6-A.2 |
| `forge_bridge/store/migrations/versions/0009_assent_record.py` — entity_type extension 20 → 21 | ✓ shipped per L11-A.2 |
| `forge_bridge/graph/commit.py:36` — `ASSENT_INVALID` CommitError code constant | ✓ shipped per L5-A.2 |
| `forge_bridge/graph/commit.py:103-104` — `assent_valid` + `assent_record` fields on CommitVerification | ✓ shipped per L5-A.2 |
| `forge_bridge/graph/commit.py:148-149` — verify body assent-check | ✓ shipped per L5-A.2 |
| `forge_bridge/console/_step.py` — assent_record propagation in commit-step branch | ✓ shipped per D5-A.2 |
| `forge_bridge/console/_engine.py:run_chain_steps` — optional assent_record kwarg | ✓ shipped per D5-A.2 |
| `forge_bridge/console/_chat_compile.py` — regime-3 graph_intent_id allocation + AssentRecord propose | ✓ shipped per D6-A.2 |
| `forge_bridge/console/handlers.py` — POST /api/v1/ratify + apply dispatch + event: apply_complete | ✓ shipped per D7-A.2 |
| `forge_bridge/cli/main.py` — `fbridge ratify` top-level subcommand | ✓ shipped per D8-A.2 |
| `forge_bridge/cli/runtime_doctor.py:48-55` — 6 doctor checks (console / install_provenance / mcp_http / flame_bridge / state_ws / graph_store) | ✓ A.3 candidate row addition site (Q-A3.2) |
| A.2-CLOSE.md §"Carried Forward" — 4 items: auth deferred / chat conversational ratification / drift-invalidation live smoke / A.3 opens | ✓ A.3 candidate scope items (Q-A3.6) |
| Operator deployment observation 2026-05-29 — mcp_http not listening + Flame bridge dispatch failure during `fbridge doctor --json`; console + state_ws running | ✓ A.3 candidate scope item (Q-A3.4); runtime-environment-state per DT |

## Phase scope (what A.3 ships — under writing-room thesis lean)

Three sub-scopes (all operational, NONE architectural):

1. **Live-smoke + UAT catalog** — production exercise of the
   authority chain against a real Flame project. Drift-invalidation
   live smoke (A.2 carry-forward). Recovery testing against the L8
   failure-class envelope. UAT runbook for operators. Q-A3.1
   decides A.3-shipping vs A.3-supplying scope.
2. **Operational observability** — Console doctor-row for
   ratification surface state (pending records, recent ratifications,
   recent applies/failures). Audit-event consumer ergonomics over
   the 4 assent.* events. Operator-facing structured logs at
   production density. **Observability of supervision state**
   (Q-A3.4 — the mcp_http partial-stack observation surfaces in the
   doctor row; supervision itself is NOT A.3 scope). Q-A3.2 +
   Q-A3.5 + Q-A3.4 decide specifics.

   **Sub-scope discipline per Stage 1a P2 absorption:** Sub-scope 2
   covers *observability of supervision state*, NOT *supervision
   itself*. Surfacing whether mcp_http is listening is observability;
   restarting mcp_http when it isn't is supervision. The first is
   A.3 scope (under Q-A3.4(b) lean); the second is operations or a
   later phase. Per Creative cycle-1: *"surfacing is hardening;
   solving is architecture."*
3. **Auth-seed integration prep** — `decided_by` field validation
   hook surface. Not full auth (SEED-AUTH-V1.5 is the milestone for
   that), but the integration surface so SEED-AUTH plugs in
   cleanly without modifying A.2's substrate. Q-A3.3 decides
   specifics.

End-to-end operational flow A.3 hardens (under the Thesis working
position):

```
Day-2 operator workflow (no architectural change from A.2):
  - NL chat turn → preview emitted with graph_intent_id X (observable
    via Console doctor-row pending-record count + assent.proposed
    event in audit log)
  - fbridge ratify X (observable via assent.ratified event + doctor
    row recent-ratification count + structured log line)
  - Apply runs (observable via assent.applied or assent.failed
    event + doctor row recent-apply count + apply_complete SSE)
  - Failure path (drift_invalid / chain_aborted / assent_invalid)
    surfaces with structured envelope + operator-actionable next
    step
  - Audit trail queryable via existing event-bus consumer pattern
    (events table; potentially extended ergonomics per Q-A3.5)
```

This is the operational shape A.3 makes trustworthy. The
substrate underneath is exactly what A.2 shipped.

## Framing-grade open questions (for A.3-DISCUSS-QUESTIONS.md)

These are the load-bearing ambiguities the discuss stage must
converge on before A.3-PLAN.md drafts. Initial positioning offered
where the framing constraints already narrow the answer; remaining
options surfaced for room convergence. **Q-A3.0 is the
architectural pre-question that constrains the others** — it
must resolve first.

### Q-A3.0 — A.3 scope shape (pre-question)

**[Cascade-driver per A.2 framing's Q-A2.0 pattern. Must resolve
first; constrains Q-A3.1..Q-A3.7.]**

How broad is A.3's scope? Four candidate shapes:

(a) **Narrow operational hardening only** — Sub-scope 1
(live-smoke + UAT catalog) only. A.3 ships UAT runbook + live
smokes; observability + auth-seed prep defer to later phases.
Smallest scope; closest to "hardening" verbatim from Thread A
framing.

(b) **Hardening + observability** — Sub-scopes 1 + 2. A.3 ships
UAT runbook + observability extensions. Auth-seed prep defers to
SEED-AUTH-V1.5 milestone.

(c) **Hardening + observability + auth-seed prep** — Sub-scopes
1 + 2 + 3. Writing-room thesis lean above. A.3 ships full
operational closure of the authority chain pre-auth.

(d) **Some other decomposition** — room rules.

**Writing-room lean (v3, narrowed per Q-A3.3 + Q-A3.5
absorptions):** (c) — full operational closure pre-auth, with
sub-scopes tightened per cycle-2 absorptions:

- **Sub-scope 1 (UAT catalog)** — unchanged from v1.
- **Sub-scope 2 (operational observability)** — narrowed: Q-A3.2
  doctor row + Q-A3.5(d) Python helpers + Q-A3.4(b) supervision
  observability. **NO new MCP tool. NO new HTTP endpoint. NO new
  wire surface.** Per Q-A3.5 v3 lean shift.
- **Sub-scope 3 (auth-seed integration)** — narrowed: Q-A3.3(d)
  documentation-only. **NO signature change to A.2-shipped
  substrate. NO hook. NO scaffolding.** Per Q-A3.3 v3 lean shift.

**Under the narrowed (c)**, the difference between (c) and (b) is
small — Sub-scope 3 becomes pure documentation that could
plausibly ride with Sub-scope 2's doc deliverable (`docs/RATIFICATION.md`
amendments). The room may rule (b) at discuss-stage and absorb
Sub-scope 3 docs into the existing doc work; the framing
preserves (c) as the writing-room's slight preference for
explicit deferral marking but acknowledges (b) is now plausible.

Rationale (v3): the v1+v2 lean for (c) rested on three sub-scopes
each shipping operator surfaces. Cycle-2 absorption tightened
Sub-scopes 2 + 3 such that they no longer extend substrate; what
remains is hardening-shaped (doctor row, Python helpers, docs).
The architectural integrity of "A.3 ships NO new substrate
primitives" is preserved under (c) post-tightening; v1+v2 only
honored the claim in the loosest reading.

**Independence from architectural law:** the inherited Thread A
+ A.2 laws bind A.3 regardless of which scope shape lands. The
choice between (a)/(b)/(c)/(d) is scope-size, not
architectural-direction.

**Cascade implications:**
- Under (a) — Q-A3.1 expands (UAT catalog is the entire phase);
  Q-A3.2 + Q-A3.3 + Q-A3.4 + Q-A3.5 defer
- Under (b) — Q-A3.1 + Q-A3.2 + Q-A3.4 + Q-A3.5 land in A.3; Q-A3.3
  defers
- Under (c) — All Q-A3.1..Q-A3.5 land in A.3
- Under any — Q-A3.6 (A.2 carry-forward processing) + Q-A3.7
  (Thread A closure marker) are scope-shape-independent

**Path to resolution at discuss stage** (per Stage 1a P3
absorption, A.2-FRAMING Q-A2.0 precedent): read A.2-CLOSE.md
"Carried Forward" list; read `runtime_doctor.py:48-55` (verify
the current 6-row pattern + check the row dict shape for the
7th-row addition cost); enumerate UAT runbook candidate items
against the L8 failure envelope per L8 carve-out 6; assess
operator-shipping cost per sub-scope (Sub-scope 1 alone vs
+ Sub-scope 2 vs + Sub-scope 3); rule on scope size against the
operational design center (single-operator dev/UAT shape);
verify the boundary-policing meta-frame holds — any sub-scope
that quietly introduces architecture rather than hardening
observability is candidate for deferral to a future phase.

### Q-A3.1 — UAT catalog: A.3 ships vs A.3 supplies

The drift-invalidation live smoke is named in A.2-CLOSE.md as a
UAT item. Other UAT items: full chain exercise against live Flame;
recovery from each L8 failure class; multi-cycle ratification.

Three candidate shapes:

(a) **A.3 supplies the catalog only** — A.3-PLAN.md enumerates
the UAT runbook items; A.3 implementation ships test infrastructure
(fixtures, helpers, smoke-test entry points) sufficient for
operator UAT. The UAT execution is operator-side, post-A.3.

(b) **A.3 ships the catalog AND runs it** — A.3 implementation
includes operator UAT against a live Flame project. A.3 close
cursor includes UAT results. Operationally heaviest; clearest
signal that the chain works in production.

(c) **A.3 supplies the catalog + runs a sub-set** — A.3 ships
infrastructure + runs the drift-invalidation smoke (the named
A.2 carry-forward) but defers full multi-cycle UAT to operator
post-A.3.

**Writing-room lean:** (c) — catalog supply + drift smoke
execution. Drift-invalidation is the highest-value UAT item per
A.2 carry-forward; full multi-cycle UAT is operator workflow
that doesn't need to gate A.3 close.

### Q-A3.2 — Console doctor-row addition

Does A.3 add a 7th doctor row for ratification surface state?
Current rows (verified at `runtime_doctor.py:48-55`): console /
install_provenance / mcp_http / flame_bridge / state_ws /
graph_store.

Three candidate shapes:

(a) **New `ratification` row** — surfaces pending AssentRecord
count, recent ratifications (24h window?), recent applies +
failures. Tri-state ok / loaded / fail matches the existing
`graph_store` row pattern.

(b) **Extend `postgres` row** — fold ratification state into the
existing postgres health check. Smaller surface; less
operationally discoverable.

(c) **No doctor extension** — `fbridge ratify` itself surfaces
state via `--list-pending` flag or similar; doctor stays unchanged.

**Writing-room lean:** (a) — new dedicated row. Matches the
`graph_store` precedent (Phase 24); operationally discoverable;
distinct from `postgres` row semantics (which is DB health, not
substrate state). Plus the tri-state pattern (ok / loaded / fail)
maps naturally to the assent_record lifecycle.

### Q-A3.3 — Auth-seed integration shape

Should A.3 ship the SEED-AUTH-V1.5 integration shape, and if so,
at what depth (documentation / hook surface / scaffolding)?

Four candidate shapes (v3 expanded per Stage 1a B1 absorption —
v1+v2 leaned (a) which DT cycle-2 + Creative cycle-2 surfaced as
architectural extension under the cover of "hardening"):

(a) **Validation hook surface** — A.3 introduces an optional
identity-resolution hook in `AssentRecordRepo.ratify(actor=...)`.
Default: free-string passthrough. When SEED-AUTH-V1.5 lands, the
hook is implemented to validate against authenticated identity.
A.3 ships the hook surface only, not the validation logic.
**Caveat (per cycle-2 absorption):** this IS a signature change
to A.2-shipped `AssentRecordRepo.ratify()`. Even with safe
default, it adds a new architectural surface (the integration
point SEED-AUTH-V1.5 plugs into). The framing's "NO new substrate
primitives" claim is honored only in the loosest reading (no new
state machine, no new entity type) — not architecturally-strict
(method signatures count as substrate contract).

(b) **No A.3 work on auth integration** — `decided_by` stays
free-string; auth integration is SEED-AUTH-V1.5's job entirely.
SEED-AUTH-V1.5 introduces validation when it lands; A.3 doesn't
pre-stage. Smallest A.3 scope; cleanest anti-scope.

(c) **Validation hook + identity-resolution scaffolding** — A.3
introduces both the hook AND an unauthenticated default identity
resolver (e.g., reads `$USER` env var) that future SEED-AUTH-V1.5
replaces. Largest A.3 scope; most premature; strongest "scaffolding
where architecture starts sneaking back in" per Creative cycle-1
discipline note.

(d) **Documentation-only** — A.3 documents the existence of the
SEED-AUTH-V1.5 integration deferral, NOT its shape (e.g., "the
placeholder field `decided_by` remains free-string until
SEED-AUTH-V1.5 lands; A.3 makes no claim about where identity
validation will live, how identities bind, or what the eventual
integration boundary will be — those are SEED-AUTH-V1.5 framing
decisions"). NO signature change. NO hook. NO architectural
prescription. Pure doc surface in `docs/RATIFICATION.md` +
A.3-CLOSE that preserves the placeholder and names the future
milestone; the integration's shape is SEED-AUTH-V1.5's framing
decision, not A.3's.

**Writing-room lean (v3, per Stage 1a B1 absorption):** (d) —
documentation-only. Honors the Thesis "NO new substrate primitives"
claim verbatim; preserves the placeholder-field deferral per
`[[feedback-explicitly-unbound-vs-implicitly-rejected]]` (A.2 R-A2.8
already shipped the placeholder; A.3 documents the next escalation
without coding it); matches Creative cycle-1 discipline
("Scaffolding is where architecture starts sneaking back in through
the side door") + DT cycle-2 catch (signature change IS
architectural extension). Documentation IS a form of operational
hardening — operators know what to expect when auth lands; the
deferral is surfaced explicitly.

**Cascade implications:**
- Under (d) — A.3 ships docs only; no code-level changes to
  A.2-shipped substrate; Thesis anti-scope intact.
- Under (a) — A.3 signature-extends `AssentRecordRepo.ratify()`;
  Thesis anti-scope softens to "NO new state machines / entity
  types"; loses clean discipline scaffold.
- Under (b) — A.3 makes no statement on auth integration; SEED-
  AUTH-V1.5 phase will surface its own integration shape; smallest
  A.3 scope; arguably misses operator-knowledge-of-future-shape
  hardening value.
- Under (c) — A.3 over-builds; most premature; risks committing
  to a default-identity-resolver shape SEED-AUTH-V1.5 may reject.

**Cycle-2 archaeology preserved** (per the discipline of recording
within-arc room contributions): v1+v2 leaned (a). Cycle-2 DT B1 +
Creative anticipated-filter both surfaced (a) as architectural
extension. v3 shifts lean to (d) per Path X — tighten anti-scope.
The (a) option remains contestable at discuss-stage if the room
prefers integration-surface creation as A.3 scope.

### Q-A3.4 — Operational supervision posture (mcp_http reliability)

Operator deployment observation 2026-05-29: `mcp_http not
listening` + Flame bridge dispatch failure during
`fbridge doctor --json`. Console + state_ws running. The daemon
stack was partial.

Three candidate shapes:

(a) **A.3 addresses daemon supervision** — extends
`install-bootstrap.sh` / systemd / launchd posture; adds
auto-restart for mcp_http; surfaces supervision state through
the doctor row addition (Q-A3.2). Operationally heaviest; bridges
into deployment-as-code territory.

(b) **A.3 surfaces but does not address** — the doctor row
addition (Q-A3.2) surfaces mcp_http partial-stack states more
clearly; A.3 does not change the supervision posture; A.3 docs
include "if mcp_http is not listening, restart with X" as
operator runbook. Operations-not-architecture.

(c) **Not A.3 scope** — daemon supervision is operations debt
independent of Thread A; A.3 stays focused on the authority chain;
supervision lands in a separate operational phase if needed.

**Writing-room lean:** (b) — surface but don't address. Matches
the operational-design-center scope (A.3 hardens what A.1+A.2
shipped; supervision is a separate operations concern). The
doctor row addition (under Q-A3.2) makes partial-stack states
visible; the supervision fix itself is operator workflow or a
later phase.

### Q-A3.5 — Audit-event consumer ergonomics

A.2 shipped 4 `assent.*` event types emitted via the EventRepo
shared-session pattern. Consumers querying for "recent
ratifications" or "failed applies in last 24h" go through the
existing events table.

Four candidate shapes (v3 expanded per Stage 1a B2 absorption —
v1+v2 leaned (b) which DT cycle-2 + Creative cycle-2
anticipated-filter both surfaced as new-substrate-primitive
introduction under the cover of "operational closure"):

(a) **No A.3 ergonomics** — consumers use existing
`forge_get_events` MCP tool patterns. Audit event consumption is
"plain SQL against the events table" via the already-shipped
substrate. Cleanest anti-scope; trades operator UX cost for
substrate-anti-scope honesty.

(b) **Convenience query surface (MCP tool / HTTP endpoint)** —
A.3 adds a small MCP tool or HTTP endpoint that surfaces common
audit queries. **Caveat (per cycle-2 absorption):** this IS new
substrate primitive introduction. MCP tool requires tool registry
registration, Pydantic input schema, sanitization at the read
boundary (per shared `_sanitize_patterns.py` infrastructure), tool
description (rhetorical-position surface per
`[[feedback-rhetorical-position-as-architectural-control-surface]]`),
provenance fields. HTTP endpoint requires router registration,
body validation, rate-limit pattern adoption, response envelope
shape. The Thesis "NO new substrate primitives" claim is
contradicted directly.

(c) **Audit-event subscription** — A.3 introduces a streaming
subscription pattern (SSE? WebSocket?) for assent.* events.
Larger scope; bridges into the operational dashboard territory.

(d) **Python helpers** — A.3 ships a small `forge_bridge.console.helpers`
module with functions like `recent_ratifications(window=...)`,
`pending_assent_records()`, `recent_failed_applies()`. Operators
import from Python REPL or scripts. **NO new MCP tool. NO new
HTTP endpoint. NO new wire surface. NO Pydantic schema. NO
sanitization gates. NO rate-limit infrastructure.** Just helper
functions over the existing events table.

**Q5-watch on (c)** (per Stage 1a F2 absorption): (c) is
constitutional ONLY if the consumer architecture is non-LLM.
Streaming subscription is Q5-safe for non-LLM consumers (operator
dashboard, projekt-forge, doctor tooling, audit-log shippers).
Q5-violation if the consumer is an LLM that interprets event
streams into ratification-decision-shaped output (e.g., a chat
regime that "summarizes recent ratifications" in conversational
output, or any path where model output is conditioned on assent
state). Per
`[[feedback-explicitly-unbound-vs-implicitly-rejected]]`: (c) is
**conditionally-available**, NOT implicitly-rejected. If the room
rules (c), discuss-stage must lock the consumer-shape constraint
explicitly — non-LLM consumer is the constitutional precondition.

**Writing-room lean (v3, per Stage 1a B2 absorption):** (d) —
Python helpers in `forge_bridge.console.helpers`. Honors the
Thesis "NO new substrate primitives" claim by avoiding the
MCP-tool / HTTP-endpoint substrate-extension shape; preserves
operator-facing convenience (operators get `recent_ratifications()`
in their REPL); is genuinely hardening-shaped (operational
trustworthiness improves; no new architectural surface).

**Cascade implications:**
- Under (d) — A.3 ships internal Python helpers; existing
  `forge_get_events` MCP tool stays the canonical wire surface;
  Thesis anti-scope intact.
- Under (b) — A.3 adds MCP tool OR HTTP endpoint; Thesis anti-scope
  softens to "NO new state machines / entity types"; loses clean
  discipline scaffold; gains better operator UX vs (d).
- Under (a) — A.3 doesn't address ergonomics; operators query
  via existing `forge_get_events`; smallest A.3 scope; arguably
  too primitive for day-2 workflow.
- Under (c) — substrate extension PLUS streaming surface
  introduction; furthest from anti-scope; Q5-watch gate above.

**Cycle-1 + cycle-2 archaeology preserved:** Creative cycle-1
endorsed (b) as "operational closure rather than expansion." DT
cycle-2 + Creative cycle-2 anticipated-filter caught (b) as
substrate extension. v3 lean shifts to (d) per Path X — the
discipline-scaffold meta-frame Creative anchored in cycle-1
applied to its own cycle-1 endorsement. (b) remains contestable at
discuss-stage if the room prefers operator-UX over substrate
anti-scope cleanliness.

### Q-A3.6 — A.2 carry-forward processing

A.2-CLOSE.md carries forward 4 items:

| # | Item | A.3 candidate disposition |
|---|---|---|
| 1 | Authentication still deferred — `actor` is free string pending the auth seed | A.3 ships auth-seed integration hook surface per Q-A3.3(a) lean |
| 2 | Chat conversational ratification remains out of scope | DEFERRED to post-A.3 / future phase per Q5 constitutional |
| 3 | Drift-invalidation live smoke remains a UAT item | A.3 ships smoke per Q-A3.1(c) lean |
| 4 | A.3 hardening opens after this close cursor | Self-referential — A.3 itself |

The question: are these dispositions correct, or should the room
reshape them? Working position above; room rules.

**Writing-room lean** (under Q-A3.0(c) scope shape): items 1 + 3
land in A.3; item 2 defers; item 4 is self-referential. Under
Q-A3.0(b) (no auth-seed prep), item 1 also defers.

### Q-A3.7 — Does A.3 carry Thread A toward closure?

**[Layer-ownership note per Stage 1a P1 absorption: A.3 cannot
RULE on Thread A closure unilaterally — Thread A framing or the
v1.7 milestone framing is the layer that closes Thread A. A.3
SIGNALS at close cursor whether the authority-chain work the
thread was scoped for is complete; the higher framing layer
RULES on whether Thread A formally closes.]**

Three candidate shapes:

(a) **A.3 carries Thread A toward closure** — the authority
chain is architecturally sufficient (not "complete" per F1
absorption) with A.2; A.3 hardens it operationally; A.3-CLOSE
SIGNALS Thread A's authority-chain work as done; Thread A
framing (or v1.7 milestone framing) RULES on formal closure.
Future work (SEED-AUTH-V1.5, Console ratification, multi-turn
graph-intent persistence) opens as separate threads / milestones
per the constitutional Q5 + Thread A out-of-scope items.

(b) **A.3 carries Thread A toward A.4+** — A.3 ships hardening
as enumerated; A.3-CLOSE explicitly signals additional Thread A
scope (which operator UAT surfaces); A.4+ opens within Thread A
for the additional scope.

(c) **A.3 is mid-thread** — Thread A explicitly multi-phase
beyond A.3; A.3 ships hardening as a checkpoint; A.4 + A.5 +
... already-implied. Thread A framing or v1.7 milestone framing
must be updated to reflect this if the room rules (c).

**Writing-room lean:** (a) — A.3 carries Thread A toward closure.
The Q5 constitutional positioning explicitly defers Console + chat
conversational ratification to future phases; SEED-AUTH-V1.5 is
its own milestone surface. Thread A's authority-chain work is
captured by A.1+A.2+A.3 under this scope; future motions on the
broader authority surface open as new threads / milestones, not
as A.4+.

**Layer discipline reminder** (per
`[[feedback-distinct-success-criteria-per-adjacent-layer]]`):
A.3's authority is over A.3-shaped decisions; Thread A closure is
Thread-A-shaped. A.3 framing can express a working position on
the closure question (this is what the lean does), but the
formal rule lives at the Thread A framing layer.

## Out of scope (framing-grade)

- **A.2 substrate redefinition.** R-A2.0(a) parallel-substrate
  ruling stays; AssentRecord shape stays; AssentRecordRepo state
  machine stays; assent.* events stay; CommitNode.verify signature
  stays. A.3 does NOT reopen any A.2-shipped contract.
- **Console / Web UI ratification surface.** Q5 explicit:
  Console is later. A.3 may add a Console doctor-row (per Q-A3.2)
  but does NOT add a ratification UI surface.
- **Conversational ratification affordance.** Q5: if ever shipped,
  only as thin verbatim transport. Not in A.3.
- **Full authentication.** SEED-AUTH-V1.5 is a separate milestone.
  A.3 may ship an auth-seed integration hook (per Q-A3.3) but
  does NOT implement authentication.
- **v1.4.x test-harness debt.** Independent backlog per
  `[[project-v1-4-x-harness-debt]]` memory; A.3's D7 corroboration
  (the httpx.AsyncClient + ASGITransport pattern) does NOT
  retroactively fix the 26 silently-skipped staged-tests.
- **Phase-4b orchestration substrate.** Parallel track; A.3 does
  not touch orch_* artifacts.
- **Multi-turn graph-intent persistence.** Thread A out-of-scope;
  A.3 preserves per-turn statelessness.
- **New chat regimes.** Coexistence architecture preserved.
- **Daemon supervision automation** under Q-A3.4(a). Writing-room
  lean is Q-A3.4(b) — surface but don't address. (a) is
  explicitly possible if the room rules so.

## Architectural law (inherited from Thread A + A.2, binding)

Substrate self-views are first-class operator surfaces — derived,
not reconstructed. A.3 inherits and preserves:

- **Ratification attaches to graph-intent identity** (A.2
  architectural law). A.3 does NOT reattach ratification to
  ratification-event identity, or to operator identity, or to any
  other identifier. The graph-intent-id IS the ratification anchor.
- **Bridge as executor for assent_record substrate** (R-A2.0(a)
  constitutive identity). A.3 does NOT shift assent_record toward
  bridge-as-bookkeeper semantics; consumer-side propose-side
  patterns are NOT introduced for assent_record.
- **The LLM never owns assent** (Q5 constitutional). A.3 operational
  observability MUST NOT include model-summarized ratification
  state. Observer-only surfaces stay structural (counts, statuses,
  IDs), not interpretive.
- **Enforcement via substrate composition** (Q3 + FC-5 lineage) —
  assent check lives AT the commit primitive inside
  `run_chain_steps`. A.3 operational logic does NOT re-enforce or
  shortcut this check at higher layers.
- **Coexistence architecture preserved** — three chat regimes
  remain; A.3 adds no 4th regime; does not parameterize regime
  3 further beyond A.2's modifications.
- **Sync-apply common-case assumption** (A.2 design center).
  A.3 operational hardening optimizes for sync-apply; does not
  re-open the design-center question.

## Status

**Phase framing v3 — cross-voice cycle 2 absorbed via Path X +
cycle-3 path-a inline cleanup absorbed; sign-off territory.** v2 → v3 absorbed 2 framing-grade boundary-
policing catches (B1 + B2) via tighten-anti-scope path. Both
catches surfaced INDEPENDENTLY by DT cycle-2 sweep AND Creative
cycle-2 anticipated filter — strong two-voice corroboration of
the same failure family.

**Meta-observation (self-referential discipline working as
designed):** the boundary-policing meta-frame anchored in Thesis
at v2 per Creative cycle-1 ("Does this improve operational
trustworthiness of A.2, or does it quietly introduce a new
architecture?") CAUGHT TWO OF THE FRAMING'S OWN LEANS at v2
(Q-A3.3(a) hook surface + Q-A3.5(b) MCP/HTTP endpoint). The
meta-frame is operational, not aspirational — the framing's own
discipline tested its own leans and surfaced failures honestly.
Per Creative cycle-2 close-frame anticipation
(*"the remaining risk surface concentrated almost entirely around
exception pressure and scope creep rather than structural
coherence"*), the catch surface matched the prediction precisely.

**v2 → v3 absorption summary:**

| Catch | Class | Disposition |
|---|---|---|
| B1 | DT framing-grade boundary-policing (Creative anticipated-filter corroboration) | Q-A3.3 writing-room lean shifts from (a) optional kwarg hook on `AssentRecordRepo.ratify()` to (d) documentation-only. A.3 ships NO code path for SEED-AUTH-V1.5 integration; ships docs of the future integration shape in `docs/RATIFICATION.md`. The (a) variant preserved as room-contestable but called out as architectural extension. |
| B2 | DT framing-grade boundary-policing (Creative anticipated-filter corroboration) | Q-A3.5 writing-room lean shifts from (b) MCP tool / HTTP endpoint to (d) Python helpers in `forge_bridge.console.helpers`. Operators get convenience via REPL/scripts; NO new MCP tool, NO new HTTP endpoint, NO new wire surface. The (b) variant preserved as room-contestable. |
| Q-A3.0(c) narrowing | B1 + B2 cascade | (c) lean preserved but sub-scopes tightened: Sub-scope 2 narrows to doctor row + Python helpers + observability-of-supervision-state; Sub-scope 3 narrows to documentation-only. Under narrowed (c), the difference between (c) and (b) is small (Sub-scope 3 = pure docs). Room may rule (b) at discuss-stage. |
| Path X selected | Architectural choice | Tighten anti-scope + tighten leans (Path X) over widen anti-scope (Path Y). Preserves Creative's discipline-scaffold meta-frame ("strongest A.3 proves A.1+A.2 were sufficient rather than extending them"); Path Y would water down the meta-frame under operational pressure. |

**Catch trajectory updated:**

| Cycle | Catches | Class | Shape |
|---|---|---|---|
| v1 → v2 | 7 | 3 framing + 4 polish | Architectural-coherence + inherited-constraint-precision |
| v2 → v3 | 2 | 2 framing + 0 polish | Boundary-policing (anti-scope vs leans tension) |
| v3 → v3 final | 3 | 0 framing + 3 polish | Cycle-3 path-a inline: C-cycle3-1 prescriptive prose in Q-A3.3(d) example narrowed to deferral-shape; C-cycle3-2 Q5-watch duplicate at Q-A3.5(c) removed (DT-named original target); + bonus operator-surfaced §Status "Phase framing v2" prose paragraph duplicate removed (sibling shape; same failure family as C-cycle3-2) |

7 → 2 → 2 trajectory. Comparable to A.2-FRAMING's 3 → 3 → 2 →
polish trajectory in convergence shape. Cycle-3 catches were
path-a editorial (narrowing existing text, no new text), per
DT path-a recommendation + operator ratification. No formal
cycle 4 required.

**A.3-CLOSE methodology carry-forward candidates** (per
Creative cycle-3 close-frame, identified during cycle-3 review):

| # | Candidate | Class | Evidence span |
|---|---|---|---|
| 1 | **Architectural-leakage failure family across 3 surface manifestations** | Cross-instance methodology candidate; promotion-grade evidence at A.3-CLOSE if implementation arc surfaces a 4th instance | B1 signatures (Q-A3.3(a) hook on `AssentRecordRepo.ratify()`); B2 surfaces (Q-A3.5(b) MCP/HTTP endpoint); C-cycle3-1 explanatory prose (Q-A3.3(d) example sentence prescribed SEED-AUTH-V1.5 shape). Creative: "Same failure family, three different manifestations. That's stronger evidence than three unrelated catches." |
| 2 | **Self-referential vulnerability mapping as cycle-N review discipline** | Distinct from substrate-shape grounding discipline; promotion candidate at A.3-CLOSE if implementation cycles corroborate. **Scope bound (per DT cycle-3 verification):** discipline catches WHAT IT NAMES, not what it doesn't name — bonus operator-surfaced §Status paragraph duplicate at cycle 3 was NOT anticipated by the framing's vulnerability map, slightly bounding the discipline's reach. | The framing's boundary-policing meta-frame (anchored in Thesis at v2 per Creative cycle-1) CAUGHT TWO of its own leans at cycle 2 (B1 + B2). DT cycle-2 anticipation table predicted 3 of 4 surfaces correctly. Creative: "The framing is beginning to model its own failure modes while it is being written... self-referential vulnerability mapping constrains review effort against likely failure locations" — different discipline class than substrate-grounding (which constrains correctness against reality). |
| 3 | **Editing-pressure failure pattern** (replacement content lands more reliably than superseded content gets removed) | Within-project 3rd instance; **PROMOTION-READY at A.3-CLOSE** | (1st) A.2-PLAN cycle-3 M-cycle3-1 duplicate v1→v2 absorption table; (2nd) A.3-FRAMING cycle-3 §Status "Phase framing v2" prose paragraph duplicate (operator-surfaced bonus); (3rd) A.3-FRAMING cycle-3 Q-A3.5(c) Q5-watch paragraph duplicate (DT-named original C-cycle3-2). 3 instances across 2 artifacts within a single milestone arc. Creative cycle-3: *"when sections become active absorption targets across multiple cycles, replacement content lands more reliably than superseded content gets removed."* Mechanical proof discipline (grep-based duplicate detection) is the catch surface — per `[[feedback-failure-shape-stability-as-disposition-evidence]]`, failure-shape stability across instances is the load-bearing evidence. |

**v1 → v2 absorption summary (preserved for archaeology):**

| Catch | Class | Disposition |
|---|---|---|
| F1 | DT framing-grade | Thesis "architecturally complete" → "architecturally sufficient" per `[[feedback-operational-maturity-not-completeness]]`. Victory-lap voice corrected. |
| F2 | DT framing-grade | Q-A3.5(c) audit-event subscription gains explicit Q5-watch flag. Constitutional ONLY for non-LLM consumers; LLM consumers that interpret event streams into ratification-shaped output violate Q5. Conditionally-available per `[[feedback-explicitly-unbound-vs-implicitly-rejected]]`, NOT implicitly-rejected. |
| F3 | DT framing-grade | New sub-section under §"What A.3 inherits from A.2" enumerates R-A2.1..R-A2.8 with one-line preservation notes. R-A2.7 store-and-replay gets load-bearing treatment — A.3 observability MAY surface chain content read-only; MUST NOT introduce "verify-this-still-applies" or "preview-the-apply" or "dry-run-the-apply" patterns. |
| P1 | DT polish (Creative concur) | Q-A3.7 reframed from "A.3 closes Thread A" to "A.3 carries Thread A toward closure". A.3 SIGNALS at close cursor; Thread A framing or v1.7 milestone framing RULES. Layer-ownership corrected per `[[feedback-distinct-success-criteria-per-adjacent-layer]]`. |
| P2 | DT polish | Q-A3.4 mcp_http supervision folded under Sub-scope 2 with explicit "observability of supervision state, not supervision itself" qualifier. Surfacing is hardening; solving is architecture (Creative cycle-1 verbatim). |
| P3 | DT polish | Q-A3.0 gains "Path to resolution at discuss stage" sub-bullet per A.2-FRAMING Q-A2.0 precedent — names what to read first to ground the scope decision. |
| P4 | DT polish | §inheritance archaeology line expanded — concrete D5 + D7 implications named for A.3 (substrate-before-consumer pattern validation + httpx.AsyncClient/ASGITransport test-infrastructure shape). |
| Creative verbatim addition | Creative cycle-1 meta-frame | Boundary-policing meta-frame anchored in Thesis: *"The strongest version of A.3 is probably the one that proves A.1+A.2 were sufficient rather than the one that creates a third architectural layer above them."* Discipline scaffold: A.3 proves sufficiency by hardening, NOT by extending. |

**v2 drafted 2026-05-29 against:**
- Thread A framing (THREAD-A-FRAMING.md)
- A.2 close cursor (A.2-CLOSE.md)
- A.2-PLAN.md §Status methodology candidates (lines 2336-2384)
- Current main state at `bebf24a` (A.2 implementation arc close +
  PR22 mechanical-test gate fix)
- Operator deployment-state observation 2026-05-29 (mcp_http +
  Flame bridge during `fbridge doctor --json`)
- Direct grounding reads of `forge_bridge/cli/runtime_doctor.py`
  (6-row doctor pattern) +
  `forge_bridge/store/assent_record_repo.py:89-92`
  (4 assent.* event types) + `forge_bridge/graph/commit.py:36`
  (ASSENT_INVALID code constant)

**Methodology discipline** (carry from A.2 cycle archaeology):

This A.3 framing v1 is the writing-room's first opening of A.3
scope. Per the A.2 cycle's catch trajectories:
- Framing v1 → v2 typically absorbs 3 framing-grade catches
  (cross-voice cycle 1)
- v2 → v3 typically absorbs 2-3 catches (cycle 2)
- v3 → v3.x typically absorbs polish catches (cycle 3)

Per the substrate-shape grounding discipline now memorialized at
[[substrate-shape-grounding-at-plan-stage]]: the framing is
intentionally architecture-grade, not substrate-shape-grade. Plan
stage will require direct file reads of any surface A.3 modifies
(doctor rows, ratify CLI flags, assent_record query surfaces);
that's a plan-stage discipline, not framing-stage.

**Motion:** v3 final form is A.3-FRAMING-of-record. Operator
ratification pending; once ratified, A.3-DISCUSS-QUESTIONS.md
opens against the 8 framing-grade Qs (Q-A3.0..Q-A3.7) with v3
leans as initial positions.

**Cycle-3 archaeology** (preserved for A.3-CLOSE methodology
synthesis): per DT cycle-3 path-a verdict + Creative cycle-3
concurrence + operator ratification, two editorial absorptions
(C-cycle3-1 prescriptive prose + C-cycle3-2 duplicate paragraph)
landed inline without a formal cycle 4. Per DT cycle-2 close-frame
(*"cycle-3 expected very small if Path X absorption is clean"*) +
Creative cycle-2 close-frame (*"converging, with the remaining
risk surface concentrated almost entirely around exception
pressure and scope creep rather than structural coherence"*):
cycle-3 catch profile matched expectation precisely (2 catches,
both editorial, no structural). Possible cycle-3 surfaces that
DID NOT fire (worth recording as anti-evidence for future
prediction calibration):

- Whether v3's Q-A3.3(d) doc-only lean cleanly captures the
  future-integration shape without prescribing implementation
  (the documentation could itself sneak architectural assumptions)
- Whether v3's Q-A3.5(d) Python-helpers lean honestly avoids
  substrate extension — the boundary between "helper module" and
  "new substrate primitive" is subjectively defensible but
  testable at plan stage via grep-table-style verification
- Whether the narrowed Q-A3.0(c) lean is genuinely distinguishable
  from Q-A3.0(b) post-tightening, or whether the writing-room
  preference for (c) over (b) is now archaeology-grade only
- Whether the meta-observation about self-referential discipline
  (Status above) is overstated — the meta-frame caught two leans
  but that doesn't prove the meta-frame catches ALL similar
  catches

- DT-anticipated boundary-policing on Q-A3.2 doctor row addition
  (read as "honest hardening" by both voices at cycle 3 — follows
  the established 6-row pattern cleanly; no architectural
  extension beyond the existing observability surface)
- Creative-anticipated drift on Sub-scope 2 "observability of
  supervision state, not supervision itself" qualifier (held
  under cycle-3 scrutiny — the qualifier did its job)
- Q-A3.7 layer-ownership reframe (P1 absorption) — uncontested
  at cycle 3; the A.3 SIGNALS / Thread A framing RULES distinction
  is operationally clean

**Cross-voice cadence convergence pattern** per A.2 framing
precedent: 3 → 3 → 2 → polish. A.3-FRAMING tracked 7 → 2 → 2
(polish) — same convergence shape. Sign-off territory reached.

Once converged + ratified, A.3-DISCUSS-QUESTIONS.md opens against
Q-A3.0..Q-A3.7 and the room converges on grounded rulings.
A.3-PLAN.md drafts in code-handoff format from those rulings;
plan stage will require fresh substrate-shape grounding reads per
[[substrate-shape-grounding-at-plan-stage]] for any surface A.3
modifies.
