# Rung C — envelope authority for orchestrator-originated generation (#31 framing)

Opens the framing cycle on **#31** (rung C — live planner/origination, mutating surface). Input = the **4-lens converged lean on #66** (authority guardian / orchestration maintainer / operator-workflow / minimalist-skeptic + redline), grounded here against live seams. Supersedes the rung-C section of [`LIVE-GENERATION-JOIN-RUNGS.md`](LIVE-GENERATION-JOIN-RUNGS.md) on the authority mechanism (see "What changed" below); the rest of that doc (rung A/B/D, contract ruling) still holds.

This is the first time bridge would **autonomously originate costly, mutating operations** — the substrate-not-producer line crossed deliberately. Frame the primitive, not the endpoint.

---

## The re-open trigger has fired

The rungs doc set rung C's re-open trigger as: *"a scheduled artist workflow needs bridge-as-producer AND mid-mutation atomicity is resolved."* The **storyboard loop (#66)** is that workflow — bridge originates stills + video (real spend) and *decides* to re-generate on QC failure. The first conjunct fires. The second (atomicity) does **not** yet — carried below as a live blocker, not waved through.

## What changed since the rungs doc (the structural finding)

The rungs-doc rung-C plan assumed origination would **ride the chat-compile mutating-preview / `AssentRecord` spine** ("ratify before any backend invoke; authorizes a spend envelope, not per-call"). The #66 convergence found that spine **cannot carry an autonomous QC-branching loop**, and the grounding confirms the mechanism:

- `AssentRecord` (`forge_bridge/core/assent.py:26`) persists an **immutable `chain_steps` list** at proposal time; ratify replays *that exact, fully-known chain* (`console/_chat_compile.py:346` → `run_chain_steps(steps=record.chain_steps, …)`). Ratify-authority = "replay this known plan."
- `CommitNode.verify` (`forge_bridge/graph/commit.py:116`) compares the **held (ratified) `resolved_plan`** against the **fresh plan computed at apply time**, item-by-item; any mismatch → `drift_count > 0` → caller raises `PLAN_STATE_DRIFT` (`console/_step.py`). The guard **structurally assumes the plan is fully known at preview time.**
- An autonomous loop branches on **QC measurements that do not exist at preview** (the still isn't rendered yet; the re-author depends on the verdict). Its makes are *not* in any ratified `chain_steps`. Replaying it either trips `PLAN_STATE_DRIFT` or, if forced through, **corrodes the guard** — the guard's whole job is to reject exactly this divergence.

**Conclusion (grounded):** replay-authority ≠ origination-authority. Reusing `AssentRecord` chain-replay for the loop is rejected on mechanism, not taste. Rung C needs a **new authorization primitive**, sibling to `AssentRecord`, not a stretch of it.

---

## Converged lean (carried from #66, to be ratified/redlined here)

**A human-ratified, bounded generation envelope/grant** — never per-make, never chain-replay.

1. **Shape.** A new authorization primitive (working name `GenerationGrant`) that authorizes *a bounded class of future originations* rather than one known chain. Bounded by **hard ceilings**: per-make spend, per-beat retries, total spend. Every make emits an audit event tied to the grant.
2. **Breach behavior.** Ceiling breach / retry-exhaustion → **halt + escalate to a human**; stuck beats park into the existing `StageNode` review terminus (`forge_bridge/graph/stage.py:72` — the PR-#65 human-review-only parking lot, no downstream action on approval).
3. **Loop substrate.** When built, an **extension of the existing orchestration `GraphEngine` event machine** (`orchestration/engine.py` + `dispatcher.py` + `worker.py:GenerationPoller` + `event_consumer.py`) — already an async submit→poll→terminal machine with a `paused` / `awaiting_decision` block (`event_consumer.py:144`). QC-reauthor = that block flipped from human-decided to bridge-decided *within the grant's ceilings*. **Rejected:** a `while`-node in the chat chain engine (`console/_engine.py:run_chain_steps` is linear / abort-on-first-error / request-scoped — confirmed); generalizing `foreach` (`graph/foreach.py` is synchronous iteration over a materialized list — the still doesn't exist until an async poll terminates); a bespoke loop engine (the GraphEngine already *is* the machine).
4. **QC note typing.** A **typed `qc_correction` reference** (same currency as the caption), never a free-text scalar in the intent string. Vision *authors* the verdict+reason (a measurement); bridge *routes* it typed (auditable); generators' `author_prompt` *consumes* it. Bridge authors no prose.
   - **Generators' consumer side is DONE** (#66 generators read): the driver consumes any `context` reference today (`forge-generators 18ea217`) and now **splits refs by params key** (`486115f`) — `caption`/`description`/`text` → *"Ground the prompt in this reference context:"*; `correction`/`revision_note`/`qc_correction`/`correction_note` → *"Revise the prompt to address this feedback:"*. Both can co-occur (caption grounds, correction directs); correction keys take precedence on a single ref; liberal key-matching. So **whatever canonical key bridge settles on, generators already frames it correctly.**
   - **Grounding nuance corrected:** the note does not need a new `InvocationEnvelope` field — it rides as a **`context` reference** (the #27 reference-inventory currency), and the Explore sweep's "`author_prompt` not in `InvocationEnvelope`" is consistent with that (it's a reference, not an envelope field). Bridge's remaining Q3 work is therefore narrow: **(i) pick the canonical key for the QC-correction reference** (generators offered to narrow its liberal set to one if bridge names it), and **(ii) carry that reference typed through bridge's routing** (not as a free-text scalar in the intent string). No generators dependency remains on Q3.

---

## Settled decisions (DT-grounded ratification, 2026-06-15)

The #66 convergence left these "decided by the #31 framing." Redlined (skeptic / DT-grounding / authority-guardian), grounded against live code, and ratified. Each ruling carries its **load-bearing reason** — the thing that survives further poking.

**D1 — RATIFIED: separate `GenerationGrant` entity, not extended assent.**
The skeptic's real alternative was "one `assent_record` table with a `kind` discriminator + ceilings field," not "extend chain-replay." It dies on **mechanism, not ergonomics**: `AssentRecordRepo(ContentAddressedRepo[AssentRecord])` (`store/assent_record_repo.py:75`) is a **content-addressed immutable store** — `ContentAddressedRepo.update()`/`delete()` raise `ImmutableArtifactError` (`store/content_addressed_repo.py:129,133`); only `status` moves, via a special `_transition`; `chain_steps` is never in `attribute_updates`. A grant needs **mutable running state** — spent-counters incrementing per make, halt-state flipping — which would hit `ImmutableArtifactError` on every spend. *Immutability is the reason; field-overlap is secondary and nearly moot.* New sibling entity + repo + audit discipline. (This is the orchestrator-originated-mutation precedent — framed deliberately as the #31 re-open.)

**D2 — RATIFIED: bind the run; mint via the existing preview→ratify gesture; no dedicated affordance.**
- *Enforcement* binds the **GraphEngine run/lifecycle id**, checked at the **single `driver.submit(envelope)` edge** (`orchestration/dispatcher.py:203`). Grounded: `dispatch_plan(run_id: uuid.UUID, …)` already treats `run_id` as first-class and presence-enforced — refuses `dispatch_missing_run_id` when sync steps lack a run (`:123-128`) — and `DispatchResult(status="refused", refusal_code=…)` (`:35-38`) is the existing shape to model a ceiling-breach halt on. **"Enforced" means "checked at `:203`"** — anything checked only in the loop's own code is bypassable, and bypassable = theater.
- *Creation*: the human mints the grant through the **one** authority gesture the substrate is built on — preview→ratify (preview shows the envelope + ceilings; ratify mints a `GenerationGrant`, not a replayed chain). The grant never touches `graph_intent_id`/`plan_id` — the fusion seam dissolves. **The one new code seam:** the ratify handler **branches on what's being ratified** — chain-intent → `AssentRecord` replay (existing); generation-grant proposal → `GenerationGrant` mint (new). Shared gesture, divergent minted entity, one small branch.

**D3 — CONFIRMED: general by shape, specific by policy; shape pinned concrete.**
Hard-coding "storyboard" into an *authority* table is how you get three half-baked assent mechanisms — but generality must not drift into "extensible-for-everyone." The general shape (substrate): `{authorized originator-class, typed bounded ceilings, spent-counters, halt-state, audit-link}`. The loop supplies ceiling *values* + run shape (producer). Guardrail: **no `originator_type` enum pre-seeded with speculative values** — orchestrator-run is the sole originator until a second real one arrives (then add it, with a real case in hand). Explicitly unbound, not implicitly anticipating everyone.

**D4 — RATIFIED: downgrade the atomicity gate; the three substrate conditions are a single hard gate.**
Atomicity is confirmed **unsolved on main** (no rollback/compensation in the apply path; `run_chain_steps` is linear/abort-on-first-error). But it is the **wrong primitive** for this loop:
- The loop's **unit of commitment is the make**, not the run — each make commits a discrete `DBOrchGenerationArtifact`; the submit→poll→terminal machine already owns per-make half-completion. Beats 1–2 being "done" when beat 3 fails is *correct*, not a violation; transactional rollback across beats would **destroy legitimately-completed artifacts**.
- **The decisive reason: external generation spend is irreversible.** You cannot roll back GPU-seconds spent at vision/generators. For the dimension that matters — spend — rollback is a *category error*; **accounting is the only coherent semantics.** So atomicity does not categorically gate this loop. The real requirement becomes a grant property: *halt/escalate must account for spend-incurred-before-halt.*

**Substrate-not-producer sign-off (RATIFIED as a hard gate, not a checklist):** the grant is substrate-preserving **only with all three, shipped together** — (a) concrete ceilings shown at ratify time, (b) halt-on-breach + escalate **enforced at the dispatch chokepoint (`dispatcher.py:203`)**, (c) per-make audit against the grant. A grant minted by a human-looking ratify that enforces nothing is **strictly worse than no grant** — it launders unbounded autonomous spend behind an authority gesture (a plausible lie about authority; the doctrine is *honest failure > plausible lie*, *assent stays the operator's*). **Partial ships nothing** — e.g. ceilings shown but not checked at `:203` is the theater failure and must be blocked, not shipped as v0.

**D5 — DECIDED: canonical QC-correction key is `qc_correction`.** (Posted to generators on #66; their consumer side already frames it. Independent of D1–D4.)

### Design-time seam to pin before code (the one remaining open)
**grant ↔ run cardinality.** Coherent iff **one storyboard loop == one GraphEngine run** (run = loop lifecycle, makes = submits within it); `dispatch_plan` taking a multi-step plan under one `run_id` suggests this holds → grant:run **1:1**, ceilings per-run, each `submit()` decrements (`grant.run_id` column). If a loop spans multiple `dispatch_plan` calls (multiple runs), it becomes **1:many** → "the run carries a `grant_id`; `submit()` checks the grant the run points at" (`run.grant_id` lookup). Pin this at design start — it's the difference between a column and a lookup.

---

## Buildable now, no new primitive required (the de-risking entry)

Defer the autonomous paid loop behind D1–D4 + vision shipping its QC/caption/beat contract (forge-vision#1). **But the manual-QC, free-Ollama, single-beat slice is buildable + valuable today** and needs *no* new authority primitive:

`author_prompt` (free) → render → **human types the QC note** (standing in for stubbed vision) → re-author → render → approve → video.

Runs live with zero vision dependency, under **existing per-make human-driven authority** (no new primitive at N=1), proves the envelope/ceiling/review UX before money/vision, and seeds a **human-written QC-note corpus** to validate vision's later captions. Honest (human visibly in the QC seat = the vision stub), not a lying demo. This is the recommended next *build* move whenever momentum is wanted — it does not wait on this framing to close.

**Generators confirms no blocker on this slice** (#66 read): the human types the note → bridge wraps it as a correction reference → generators frames it as a revision directive, **from day one**. The only bridge-side prerequisite is D5 (name the canonical key); everything else in the slice is bridge's manual-QC wiring + the GraphEngine single-beat path.

---

## Dispositions

### Settled (grounded)
- Reuse of `AssentRecord` chain-replay for the loop — **rejected on mechanism** (`PLAN_STATE_DRIFT` / fully-known-chain). Rung C needs a new primitive.
- Loop substrate — the `GraphEngine` event machine, not the chat chain engine, not `foreach`, not a bespoke engine.
- QC note — typed `qc_correction` ref; bridge routes, never authors.
- **D1** separate `GenerationGrant` entity (load-bearing: CAR-immutability conflict — grant needs mutable running state).
- **D2** bind the GraphEngine run; enforce at `dispatcher.py:203`; mint via the existing preview→ratify gesture (handler branches); no dedicated affordance.
- **D3** general-by-shape / specific-by-policy; pinned shape, no speculative `originator_type` enum.
- **D4** atomicity gate downgraded (irreversible spend → accounting, not rollback); substrate sign-off = single hard 3-condition gate, all-or-nothing, enforced at `:203`.
- **D5** canonical key `qc_correction` (posted to generators on #66).

### Design-time open (pin before code)
- **grant ↔ run cardinality** — 1:1 (`grant.run_id` column) vs 1:many (`run.grant_id` lookup). See section above.

### Cross-repo status (storyboard loop)
- **Generators — Q3 consumer side DONE** (`18ea217` + `486115f`); no remaining dependency. Key named (`qc_correction`).
- **Vision — open:** QC/caption/beat contract not yet scoped (forge-vision#1). Gates the *autonomous* loop, not the manual slice. *(Separately, forge-vision#2 — `forge_assess_drift` readOnlyHint — gates the routing-real slice-1 UAT, unrelated to this loop.)*
- **Bridge — framing now decided (D1–D5);** remaining = the manual-slice build + (when triggers clear) the grant build.

### Gated builds (re-open triggers)
- Autonomous paid loop — pending (a) vision ships QC/caption/beat contract (forge-vision#1) **and** (b) the `GenerationGrant` is built to the D1–D4 contract (all three substrate conditions enforced at `:203`). *(Atomicity is no longer a gate — D4. Generators gate: cleared. Framing gate: cleared.)*
- Manual-QC free-Ollama slice — **buildable now**, no remaining gate (D5 answered).
