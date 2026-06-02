# C2 — Compile → Commit-Bearing Executor Chain (FRAMING)

**Companion to:** `.planning/adr/ADR-0001-chat-mutation-executor-delegation.md` (bridge half;
defers to forge-pipeline ADR-003, Door C / variant C1).
**Status:** framing — fork settled by the room; discuss-open questions below.
**Cadence:** writing-room authors framing/discuss/plan/close + docs; operator implements code.

---

## Thesis

`compile_intent()` must emit a **commit-bearing executor chain** for mutating intents — a stored
chain whose mutation step is `<executor discover-step> -> commit` — so the intent reaches the
preview / `AssentRecord` / ratify branch instead of the DI.1-blocked bare-`flame_rename_shots`
direct-dispatch path. This is the keystone that fires ADR-003 / C1 end-to-end and unblocks 26-04
(live E2E).

Today a mutating intent compiles to a **bare** mutation step (e.g. `flame_rename_shots …`), which:
- `graph_contains_commit_node(steps)` → False → falls through to the reads path
  (`_chat_compile.py:205-227`), where DI.1's `dispatch_authority` gate hard-blocks it pre-ratify.

That is why live mutation attempts abort. C2 makes the compile output take the *preview* branch
(`_chat_compile.py:182-204`) by introducing the commit node.

---

## The fork — SETTLED (decision record, not open)

The one unverified item the passoff flagged was: *does `run_compile_branch` run the executor's
`discover` at PREVIEW time (so the operator ratifies the real resolved manifest), or only store the
structural chain?* **Grounded against live source — it stores chain TEXT and builds a purely lexical
preview; discover does not run at preview.** Evidence:

- `_chat_compile.py:187-204` — the mutating branch proposes `AssentRecord(chain_steps=steps)` storing
  the raw compiled **step text**, then builds the preview from `build_preview_from_steps(steps, …)`.
  No tool call, no `run_chain_steps`.
- `build_preview_from_steps` (`_chat_compile.py:112-145`) is lexical only — per step it takes the
  first token as `tool_name`, `extract_explicit_params(step_text)` as `args_preview`, and a
  `would_mutate` flag. **Nothing resolves; there is no cardinality.**
- The discover→commit chain executes only at apply: `run_apply_branch:304` → `run_chain_steps(steps=
  record.chain_steps)`. The commit node reads `__previous_result__` as the manifest and validates it
  (`_step.py:771-783`) — i.e. the discover step runs immediately before commit, **at apply** — then
  `verify` (`_step.py:803-838`) and `apply` (`_step.py:859-866`).

### Two integrity windows (DT's reframe — the move that dissolved the disagreement)

- **Window 1** (`T_apply_discover → T_apply_verify`): protected today by `CommitNode().verify(held,
  fresh)` (`_step.py:838`). Shape A keeps this fully intact. **ADR-0001 line 64 is not regressed.**
- **Window 2** (`T_preview → T_apply`): *new* protection that manifest-ratification would add. Not a
  restored guarantee — a new one.

### Decision: **Shape A+ now, Shape B as its own named motion** (operator-ratified)

| | Shape A+ (THIS phase) | Shape B (separate motion) |
|---|---|---|
| Operator assents to | *"run this mutation capability against the current world"* (intent text + explicit params) | *"these N resolved changes"* (held manifest) |
| Preview | lexical step text; **no count claim it cannot keep** | resolved `MutationManifest`, count shown pre-assent |
| Drift protection | Window 1 only | Window 1 + Window 2 |
| Apply count | **surfaced in `apply_complete`** (uses existing `_step.py:895` `count`) | shown at preview, held + drift-checked |
| ADR-0001 | the literal deliverable ("ONE change, no new machinery") | a maturation of the ratification model |

**Why A+ and not pure A:** the only operator-experience objection either specialist reserved was
*silent-count-drift*. Grounding de-fangs it: a pure Shape-A preview **cannot display a count**
(`build_preview_from_steps` never resolves), so the "preview said 42, apply did 38, silent" scenario
is a *Shape-B artifact* — it requires a resolved number to have been shown. The residual risk under A
is the operator's own unverified mental count. `_step.py:895` already returns the resolved `count` at
apply; surfacing it in `apply_complete` ("renamed 38 shots") closes "no visibility" for a few lines —
cardinality at apply, just after assent rather than before.

**Why B is not smuggled in:** preview-time discover + manifest persistence + `AssentRecord` shape
evolution + new preview semantics are a new capability, not "one more thing." Folding it into C2
violates substrate-before-consumer / name-the-maturation-condition discipline
(`[[feedback-transitional-structure-naming]]`, `[[feedback-substrate-before-consumer-landing]]`).
B's honest title: **"upgrade chat mutation from intent-ratification to manifest-ratification."**
Its maturation condition: the room judges Window-2 drift unacceptable in production (e.g. a real
silent-count-drift incident, or an operator who reads the coarse preview as a precise count).

---

## Mechanism (grounded lean — operator implements)

Sibling of SR.1's `apply_source_routing` (`_source_route.py`): a **deterministic post-compile
transform**, not a prompt change.

1. **NEW** `forge_bridge/console/_executor_route.py` :: `apply_executor_routing(user_prompt, steps,
   tools) -> list[str]`. For each compiled step whose tool is a **bare host mutation** (authority-true),
   rewrite it into a two-node sub-chain `<executor> <same args> -> commit`, using an
   intent→executor map (rename → `forge_apply_rename`; publish → `forge_apply_publish`). **Pure
   name-swap + commit-append — no arg reshaping, no `mode` token** (Q2/Q3, grounded below). The
   discover step produces the `MutationManifest` the commit node consumes (`_step.py:771-783`); commit
   does verify+apply. **Fail-safe:** a mutating tool with no mapped executor is left unchanged → DI.1
   blocks → honest "no ratify path for this mutation yet" rather than a broken rewrite.
2. **HOOK POINT — `_chat_compile.py` *before* line 182** (`if graph_contains_commit_node(steps):`).
   This is the load-bearing difference from SR.1, which hooked *after* the commit branch at `:205`
   because it was reads-only. C2's whole purpose is to **introduce** the commit node so the chain takes
   the preview branch (`:187-204`) instead of the DI.1-blocked reads path.
3. **A+ count surface:** ensure the resolved `count` (`_step.py:895`, inside the commit result within
   `chain_body`) is exposed legibly in the `apply_complete` event. Trace whether it already rides the
   payload (then A+ is presentation only) or needs plumbing.
4. **NEW** `tests/console/test_c2_executor_routing.py` — unit cases: bare mutation → `<executor>
   discover -> commit`; reads never rewritten; mapped vs unmapped mutation (fail-safe unchanged);
   commit-bearing chain reaches the preview branch (regime `compiled_mutating_preview`). `__all__`=19.

---

## Scope boundaries

**IN (C2 / A+):** the compile-transform introducing the commit-bearing executor chain; intent→executor
map (rename, publish); apply-time `count` surface in `apply_complete`; unit tests.

**OUT → Shape B (named motion):** preview-time discover; `MutationManifest` persistence in
`AssentRecord`; Window-2 drift check; preview rendering the resolved manifest.

**OUT → other motions:** R9 timewarp capability tool (forge-pipeline); R7 session/project scope.

**CAVEAT — not a C2 deliverable; gates live E2E only:** executors `forge_apply_rename` /
`forge_apply_publish` live on forge-pipeline branch `claude/document-action-api-ZYmqX`,
**unpushed/unregistered** (the branch is ~146 commits ahead of its stale origin ref — a separate push
when the executors leave the bench). The commit node rejects an undeclared `apply_counterpart` with
`APPLY_COUNTERPART_NOT_DECLARED` (`_step.py:793-799`). So C2 lands + unit-tests **bridge-side
independent of executor availability** (substrate-before-consumer); 26-04 live E2E resumes only once
the executors are pushed, registered, and declare `apply_counterpart` correctly. Keep this strictly
separate from the integrity decision — executor availability must not muddy it.

**Door-C grounding (why the gap is specifically the unpushed executor):** the shapes match in Q3
*structurally* — bridge's `rename_shots` **is** the discover probe the forge-pipeline executor wraps
(`executors.py:170`). The executor exists to be the consumer-owned `apply_counterpart` with the right
registered name + manifest envelope (`originating_capability` / `apply_counterpart.tool` pinned to
`APPLY_RENAME_TOOL_NAME = "forge_apply_rename"`, `executors.py:49`). **Bridge probes; consumer owns the
apply boundary** — exactly ADR-003 Door C. That is why the probe is already here but the
`apply_counterpart` wrapper is not registered: the substrate/consumer split is doing its job.

---

## Discuss questions — Q1–Q4 RESOLVED (grounded), Q5 = operator's call

**Headline from the grounding pass:** the executor contract made C2 *smaller, not larger* — it removed
transform complexity instead of introducing it. Q2 collapsed the transform to "no `mode` token," Q3 to
"args unchanged," Q4 to "presentation-only." That alignment (the contract removing work rather than
imposing it) is the strongest signal the architecture fits the implementation rather than being layered
on top of it.

1. **Mutating-intent detection — RESOLVED (route by authority signal, then map).** Trigger on the
   fail-closed DI.1 gate `dispatch_authority(tool) is True` (the same read used at `_chat_compile.py:78`);
   the intent→executor map (rename → `forge_apply_rename`, publish → `forge_apply_publish`) is the
   capability check ("do we have a ratify path"). Authority-signal as trigger, map as capability —
   layered, single source of truth, no second drifting notion of "is this a mutation."
2. **discover-mode invocation — RESOLVED (default; do not inject).** `ApplyRenameInput.mode` /
   `ApplyPublishInput.mode` default to `"discover"` (forge-pipeline `executors.py:109-110, 138`), so a
   bare `forge_apply_rename <args> -> commit` lands the pre-commit step in discover by default. The commit
   node owns the other two modes explicitly — verify via override (`_step.py:803`) and apply via
   `apply_counterpart.parameter_overrides = {"mode": "apply"}` (`executors.py:85`). **Emit the bare
   executor step, no `mode` token** — injecting `mode=discover` is redundant with the default and just
   adds a token the transform would have to manage; correctness is guaranteed by the default + the commit
   node's explicit verify/apply overrides.
3. **Discover-mode arg shape — RESOLVED (identical by construction).** `forge_apply_rename`'s discover
   mode delegates straight back into bridge's own `rename_shots` / `RenameInput` (`executors.py:170`), and
   `ApplyRenameInput ≡ RenameInput` field-for-field (`sequence_name`, `prefix`, `increment`, `padding`,
   `start`, `role_overrides`, `qualifier_overrides`). Selectors are `sequence_name` + the rename
   parameterization — **not** a shot list, **not** `resolved_plan` (that is verify/apply-only,
   `executors.py:117-120`). So the args the executor's discover expects are exactly what the bridge
   rename step already carries: the transform is a pure name-swap + commit-append, no reshaping.
4. **A+ count surface — RESOLVED (presentation-only, not plumbing).** `_apply_complete_body`
   (`handlers.py:1030`) already passes `chain: outcome.chain_body`, and the resolved `count`
   (`_step.py:895`) lives inside that body; the panel template (`panel.html:160-174`) just doesn't
   surface it. A+ = lift `count` to a legible field in the apply-complete body shaper + surface it in the
   template. Does NOT touch the apply pipeline. (Exact nested path within `chain_body` to confirm at plan
   time.)
5. **Milestone placement — RESOLVED (operator-ratified).** C2 **opens a new milestone, v1.12 Mutation
   Delegation**, with the Shape B (manifest-ratification) motion as its planned **phase 2**. v1.11 SR.1
   stays closed (it was v1.11's only buildable phase). Milestone framing:
   `.planning/milestones/v1.12-MUTATION-DELEGATION-FRAMING.md`.

---

## Forward pointers

- **Shape B motion** to be opened immediately on C2 close: "upgrade chat mutation from
  intent-ratification to manifest-ratification" (Window-2 drift protection; preview-time discover;
  `AssentRecord` shape evolution).
- **26-04 live E2E** resumes as a ratify-chain rerun against the new executors once pushed/registered
  (non-autonomous, live-Flame).
- **`/gsd-secure-phase 26`** before the forge-pipeline branch merges (26-05 STRIDE DT-ratified; 26-06
  ships code).
