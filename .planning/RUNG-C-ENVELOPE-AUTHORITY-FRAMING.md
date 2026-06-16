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

### Design-time seam — RESOLVED: grant ↔ run = **1:many**, `run.grant_id` (DT + Creative converged, 2026-06-16)

The framing above *leaned 1:1* on the reading "one storyboard loop == one GraphEngine run, makes = submits within it." Grounding overturns the lean: **cardinality is forced by the substrate, not chosen.** DT verified all five citations; Creative ratified the synthesis. The ruling and the `run.grant_id` direction are adopted; the enforcement model is amended (three items below).

**Forced to 1:many — the substrate cannot host a loop inside one run:**

| Grounded fact | Source |
|---|---|
| `dispatch_plan` submits **one** generation step per call (one make = one dispatch) | `dispatcher.py:165` (single step), `:203` (single submit) |
| Run lifecycle is a **forward-only DAG, no back-edge**; only legal edge from `audit` is `→promotion` | `engine.py:28-37` |
| `approve_remediation` is validated (requires `paused`) against the transition guard → **cannot re-enter `execution`** | `engine.py:333`, `:358-360` |
| Pipeline-run entity is **content-addressed immutable** | `orch_pipeline_run_repo.py:11` (`ContentAddressedRepo` subclass) |
| `source_run_id` + `run_kind` exist to **mint a derived run** | `orch_entity_views.py:103,111` |

Immutable runs + forward-only DAG ⇒ a QC/remediation loop cannot live inside one run; it is necessarily a **chain of derived runs** (`source_run_id` → parent). The grant — the **sole mutable** authorization/accounting entity (D1: CAR-immutability forces spend-counters/halt-state off the immutable artifacts) — spans the chain. So grant is the "one," runs are the "many" → **1:many**, and the link rides the immutable run's content as **`run.grant_id`** (set once at creation; no CAR conflict). `grant.run_id` is rejected — it would pin the grant to a single run, contradicting the chain.

**Point-3 mechanism correction (confirmed by DT + Creative):** Point 3 above says QC-reauthor is "the `awaiting_decision` block flipped from human-decided to bridge-decided *within one run*." The engine cannot re-enter `execution` and runs are immutable, so the bridge-decided flip **mints a derived remediation run** (`source_run_id` → original, same `grant_id`) — it does not resume the original run. The grant is what makes the derived run *authorized*.

**Enforcement amendments — the story was conceptually ahead of the code; these align it:**

1. **The gate is a committed CAS txn placed *immediately before* `submit`, not "at `:203`."** `:203` is `await driver.submit(envelope)` — the irreversible external spend itself; a check at/after it has already spent. The shape:
   ```
   resolve run_id → run.grant_id → grant
   CAS:  UPDATE generation_grant SET spent = spent + :cost
          WHERE id = :grant_id AND spent + :cost <= ceiling   -- own committed txn
   commit
   submit to backend                                          -- only if CAS succeeded
   ```
   *Positive surprise (stronger than the original framing):* the dispatcher already owns a `session_factory` and opens short-lived **committed per-op transactions** (`:140-151`, `:229-231`), not the engine's "caller owns the transaction" convention — so the atomic CAS is genuinely available as its own committed guard txn. The standing worry (a long-lived caller txn defeating the row guard) does not apply here. This is the over-spend protection across **concurrent beat submits**.

2. **Generation dispatch MUST require a valid `run_id`, or fail closed — this is design, not implementation detail.** Today `run_id: uuid.UUID | None = None` (`dispatcher.py:117`); a generation step can dispatch with `run_id=None`, which has **no run→grant resolution path and escapes the chokepoint entirely**. "Every make crosses the grant gate" is true only once generation dispatch without a `run_id` fails closed. This is the one live structural bypass the 1:many design must close.

3. **Derived-run creation must propagate `grant_id` from its source, validated at creation.** `run.grant_id` is set-once, so the remediation-run minter must inherit it: **`source_run_id` present ⇒ `grant_id` present**, and `child.grant_id == parent.grant_id`. Otherwise a remediation run minted grant-less slips the chokepoint via the same run-present-but-grant-absent hole as (2).

**Converged build contract (DT + Creative):** (1) adopt grant↔run **1:many**; (2) store as **`run.grant_id`**; (3) grant = sole mutable authorization/accounting entity spanning a chain of immutable runs; (4) atomic spend **CAS in a dedicated committed txn immediately before backend submit**; (5) **generation dispatch requires a valid `run_id` or fails closed**; (6) **derived runs inherit their source's `grant_id`, validated at creation.** The cardinality ruling survives the review unchanged; the enforcement model becomes precise and structurally bypass-free.

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
- **D6 — RATIFIED (DT + Creative converged, 2026-06-16): grant ↔ run = 1:many, `run.grant_id`.** Forced by the substrate (immutable content-addressed runs + forward-only no-back-edge DAG → a QC loop is a chain of derived runs). Enforcement amended: CAS in a committed guard txn *immediately before* `submit` (not at/after `:203`); generation dispatch must require a valid `run_id` or fail closed (closes a live bypass — `dispatcher.py:117` currently nullable); derived runs inherit their source's `grant_id`, validated at creation. See the resolved-seam section above for the full build contract.

### Cross-repo status (storyboard loop)
- **Generators — Q3 consumer side DONE** (`18ea217` + `486115f`); no remaining dependency. Key named (`qc_correction`).
- **Vision — open:** QC/caption/beat contract not yet scoped (forge-vision#1). Gates the *autonomous* loop, not the manual slice. *(Separately, forge-vision#2 — `forge_assess_drift` readOnlyHint — gates the routing-real slice-1 UAT, unrelated to this loop.)*
- **Bridge — framing now decided (D1–D5);** remaining = the manual-slice build + (when triggers clear) the grant build.

### Gated builds (re-open triggers)
- Autonomous paid loop — pending (a) vision ships QC/caption/beat contract (forge-vision#1) **and** (b) the `GenerationGrant` is built to the D1–D4 contract (all three substrate conditions enforced at `:203`). *(Atomicity is no longer a gate — D4. Generators gate: cleared. Framing gate: cleared.)*
- Manual-QC free-Ollama slice — **buildable now**, no remaining gate (D5 answered).
