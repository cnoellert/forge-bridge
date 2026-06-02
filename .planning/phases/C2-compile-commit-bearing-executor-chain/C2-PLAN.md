# C2 — Compile → Commit-Bearing Executor Chain (PLAN)

**Milestone:** v1.12 Mutation Delegation (phase 1).
**Framing:** `C2-FRAMING.md` (this dir). **ADR:** `.planning/adr/ADR-0001-…`.
**Shape:** A+ (intent-ratification + apply-time count surface). Shape B = phase 2, not this plan.
**Handoff model:** writing-room authors plan; operator implements code (paths + instructions below).
**Invariants:** `forge_bridge.__all__` stays **19**; no new external libraries; ruff clean; reads-side
behavior byte-unchanged (C2 only touches the *mutating* compile branch + the apply-complete body shaper).

---

## Mechanism recap (grounded)

A bare `flame_rename_shots …` step is rewritten, by a deterministic post-compile pass, into
`forge_apply_rename <same args> -> commit`, so `graph_contains_commit_node` becomes True and the chain
takes the preview/`AssentRecord`/ratify branch (`_chat_compile.py:187-204`) instead of the DI.1-blocked
reads path (`:205-227`). For rename, pure name-swap + commit-append: no `mode` token (executor defaults
discover, forge-pipeline `executors.py:109-110`), no arg reshaping — `ApplyRenameInput ≡ RenameInput`
field-for-field, discover delegates straight into bridge's `rename_shots` (`executors.py:170`).
**This "no arg reshaping" property is rename-proven, not map-general** — it is exactly what publish
*lacks* (G2), which is why C2's map is rename-only.

**C2 runs before SR.1's routing, on the mutation branch; SR.1 stays on the reads branch.** Order in
`run_compile_branch`: compile → **[C2 hook]** → `graph_contains_commit_node`? → (yes) preview / (no)
`apply_source_routing` → reads. A step is either a mutation (C2 → executor+commit) or a read (SR.1 may
reroute). No overlap.

---

## Pre-flight groundings — DT-resolved at plan-check

- **G1 — executor `readOnlyHint` — CONFIRMED SAFE (two ways).** The executors register via
  `register_tools(mcp, [apply_rename, apply_publish], prefix="forge_", source="builtin")`
  (forge-pipeline `forge_flame/server/mcp.py:33-54`) with no explicit `annotations`. The consuming bridge
  registry (`registry.py:122-130`) does `setdefault("readOnlyHint", False)` on the builtin path → executors
  register **`readOnlyHint=False`** → `dispatch_authority` returns True (mutating, `_authority.py:13-20`) →
  the strip-guard (`_chat_compile.py:78`) keeps C2's commit. The only dangerous value is an explicit
  `True`, which nothing in the registration path sets. Bonus: registered `forge_apply_rename` ==
  `APPLY_RENAME_TOOL_NAME` == `apply_counterpart.tool` (`executors.py:48`), so the apply-time
  `APPLY_COUNTERPART_NOT_DECLARED` check lines up. **NB:** this confirms the annotation *today* — Finding 1
  (T1) enforces it *every time*, per `[[feedback-baseline-drift-invalidates-controls]]`.
- **G2 — publish — FAILS clean parity → EXCLUDED from C2.** `ApplyPublishInput`
  `{sequence_name, scope, roles}` (`executors.py:129-149`) shares only `sequence_name` with the bridge
  bare `PublishSequence` `{sequence_name, preset_path, output_directory, foreground}`
  (`publish.py:57-78`), and publish's discover does **not** delegate to a typed bridge tool — it runs raw
  inline probes mirroring the staged proposer (`executors.py:287-345`). No field-for-field parity → a
  publish rewrite would violate the rename-proven "no reshaping" property, and the bare publish tool is
  itself unconfirmed (candidates: `publish_sequence` / `forge_publish_pipeline` /
  `forge_stage_publish_shots`). **Publish becomes its own future motion** with its own grounding (likely a
  mini-design, since discover mirrors the proposer). `_EXECUTOR_MAP` ships rename-only.
- **G3 — `count` path in `chain_body` — RESOLVED (grounded).** `chain_body` (= `run_chain_steps` return,
  `_engine.py:99-104`) carries `chain: [{"step", "result"}, …]`; the commit step's `result` is the
  `{"type": "commit_applied", …, "count": N}` dict (`_step.py:889-897`). Extract by type-keyed lookup —
  full `_commit_count` helper specified in T3.

---

## Tasks

### T1 — NEW `forge_bridge/console/_executor_route.py`

`apply_executor_routing(steps: list[str], tools: list) -> list[str]` — sibling of
`_source_route.apply_source_routing`. **No `user_prompt` param** (the rewrite is tool-driven via
authority + map, not prompt-driven — dropping the unused param keeps the signature honest; note the
deliberate divergence from SR.1's signature).

Logic, per step (preserve order):
1. `first_token = step.split(maxsplit=1)[0]`.
2. Resolve the tool object by name in `tools`. If absent → passthrough.
3. Rewrite **iff** all hold (else passthrough — fail-safe):
   - `dispatch_authority(tool) is True` (bare tool is mutating; reuse `_authority.dispatch_authority`),
   - `first_token in _EXECUTOR_MAP`,
   - the mapped executor name **is present in the tool surface** (registered; see T2/Finding 2 for *which*
     surface),
   - **`dispatch_authority(mapped_executor_tool) is True` (Finding 1 — the executor itself reads as
     mutating).** This is the lock-required amendment: without it, a mis-declared `readOnlyHint=True`
     executor passes the registered gate, gets rewritten to `forge_apply_rename -> commit`, and then the
     strip-guard (`_chat_compile.py:183`) reads the executor step as a *read* → strips the commit → routes
     the mutation as a bare read. That is G1's exact failure mode, but reachable at runtime past the gate
     where G1's one-time grounding can't see it. Adding this clause converts silent-defeat → fail-safe
     passthrough (honest DI.1 block). `[[feedback-baseline-drift-invalidates-controls]]`.

   *Graceful degradation:* any clause failing → leave bare → DI.1 blocks → C2 is inert on a stock bridge,
   active once the consumer registers a correctly-hinted executor (substrate-before-consumer).
4. On rewrite: emit `f"{executor_name} {rest}"` (rest = `step.split(maxsplit=1)[1]` if present, else just
   the executor name), then append a separate `"commit"` step.

```python
_EXECUTOR_MAP = {
    "flame_rename_shots": "forge_apply_rename",
}
# publish EXCLUDED from C2 (G2: no arg parity, bare tool unconfirmed) — its own future motion.
```

**Scope boundary:** single mutation step per chain. If >1 mutating step survives the filter, leave the
chain unchanged (fail-safe) — multi-mutation ratification (one AssentRecord, N executor+commit pairs) is
out of C2 scope; note it for a later motion.

### T2 — HOOK `forge_bridge/console/_chat_compile.py`

One line, **before** `if graph_contains_commit_node(steps):` at `:182` (i.e. immediately after the
`compile_intent` try/except returns `steps`, ~`:181`):

```python
steps = apply_executor_routing(steps, execution_tools or tools)
```

Add the import. Mirror SR.1's `execution_tools or tools` choice (`:205-206`). **The hook surface is
benign** (DT, traced to the bottom): the strip-guard `_strip_commit_for_exact_read_graph` returns `None`
(→ keep commit → mutating-preview) on *both* the mutating-step case and the not-found / multi-match case
(`len(matches) != 1`, `:78`), so an executor in `execution_tools` but absent from narrowed `tools` still
reaches preview — no compile-time preview-vs-apply split. (And for an actual "rename …" message the
executor is in the narrowed set anyway, matching the "rename" token — the same fact Finding 1 relies on.)
**G1 confirms the strip-guard keeps C2's commit; Finding 1 (T1) enforces it durably.** The original
"surface inconsistency" worry was mis-located at this seam → relocated to T5.

### T3 — A+ count surface (data field + phrased confirmation)

Creative's contract: **`count` is data, the sentence is confirmation — surface both.**
`_apply_complete_body` (`handlers.py:1030-1038`) already passes `chain: outcome.chain_body`; lift the
resolved `count` to a top-level field, and present a phrased confirmation to the operator.

**G3 — RESOLVED (grounded).** `outcome.chain_body` is the `run_chain_steps` return
(`_engine.py:99-104`): `{"status", "request_id", "chain": [...], "error"}`. Each `chain` entry is
`{"step": <text>, "result": <step result>}` (`:83-86`); the commit step's result is the
`{"type": "commit_applied", …, "count": N}` dict (`_step.py:889-897`). So extract by **type-keyed
lookup** (robust to position / multi-step), not `[-1]`:

```python
def _commit_count(chain_body):
    if not isinstance(chain_body, dict):
        return None
    for entry in chain_body.get("chain", []) or []:
        result = entry.get("result")
        if isinstance(result, dict) and result.get("type") == "commit_applied":
            return result.get("count")
    return None

def _apply_complete_body(outcome, transport):
    body = { … existing … }
    count = _commit_count(outcome.chain_body)
    if count is not None:
        body["count"] = count                        # data
    return body
```

In `panel.html` (alongside the existing `:160-174` apply-complete `<dd>` rows), render the confirmation
sentence from `count` — e.g. *"Renamed 38 shots."* (when `count` present) so the operator reads a result,
not a field. Presentation only — does not touch the apply pipeline.

### T4 — Tests `tests/console/test_c2_executor_routing.py`

Unit (pure `apply_executor_routing`):
1. bare `flame_rename_shots …` + executor registered + `readOnlyHint!=True` → `["forge_apply_rename …",
   "commit"]`.
2. read step (`forge_get_shot …`, `readOnlyHint=True`) → unchanged.
3. mapped-but-executor-not-registered → unchanged (graceful degradation).
4. unmapped mutating tool → unchanged (fail-safe).
5. >1 mutating step → unchanged (scope boundary).
6. **Finding 1:** bare `flame_rename_shots …` + executor registered but `readOnlyHint=True`
   (mis-declared) → **unchanged** (fail-safe passthrough; the mapped-executor mutating clause rejects it).

Branch-level (via `run_compile_branch` with a fake `session_factory` + executor in the tool surface):
7. rename intent → regime `compiled_mutating_preview`, preview has a `commit` step, `AssentRecord`
   proposed. (Guards the strip-guard interaction end-to-end.)

A+:
8. `_apply_complete_body` exposes `count` when chain_body carries a commit result, and the panel renders
   the phrased confirmation.

Invariants: `test_public_api`/`__all__`==19 still green; `ruff check` clean.

### T5 — Align in-chat `apply <id>` replay onto the reachable surface (relocated Finding 2)

**Independent of the T1/T2 core mechanism; MEDIUM; not a C2 acceptance blocker.** Pre-existing defect that
C2 *exposes* (it is the first producer of stored executor-bearing chains): the in-chat `apply <id>` grammar
replays through a tool surface narrowed on the *command text*, not the reachable surface.

- `/api/v1/ratify` → `run_apply_branch` (`handlers.py:1343-1345`) already uses the full reachable surface
  (`filter_tools_by_reachable_backends(mcp.list_tools())`). **Correct** — this is `fbridge ratify`,
  `POST /api/v1/ratify`, and the CA.1 Console ratify button. C2's acceptance rides this path; it is clean.
- In-chat `apply <id>` (`handlers.py:1080` SSE, `:1889` JSON) passes `tools=tools` — message-narrowed
  against the literal `"apply <hex>"`. The narrower (`_tool_filter.py:292-356`) returns only the
  *apply*-named tools (non-empty `other_matches` suppresses the full-list fallback `:355`), then
  `deterministic_narrow` (`:1728`) can collapse to the wrong apply-tool — and a `tools_filtered_count==1`
  could trip PR20 forced-execution (`:1794`), force-calling an apply tool on the text "apply <id>" instead
  of replaying the ratified chain. The executor usually survives (it matches "apply"), but by token
  accident, not guarantee.

**Fix (trivial):** replay must never be message-narrowed. Pass the reachable surface like `/ratify` does —
`:1080` already has `execution_tools` in scope (a `_chat_sse_response` param); `:1889` has
`tools_post_reachability` in scope. Use those instead of `tools` at both apply-grammar callsites; all three
apply entries then align on one surface. Add a test that the in-chat `apply <id>` path resolves the stored
executor chain (not an apply-named tool forced off the command text).

*Scope note (operator's call):* shippable as C2 T5 (cheap, on the apply path C2 newly exercises) or split
to a fast-follow. Lean: keep in C2 — it's the path an operator hits right after a C2 preview.

---

## Verification (goal-backward)

- A rename intent through `/api/v1/chat` no longer aborts at the DI.1 gate; it emits `preview_emitted`
  with a `commit`-bearing chain + `graph_intent_id`. **(Bridge-side; executor need not be live — with no
  registered executor it degrades to the honest block, which is also correct.)**
- `fbridge ratify <id>` / `POST /api/v1/ratify` replays discover→verify→apply; `apply_complete` carries
  `count`. **(Requires the registered executor — the 26-04 live-E2E gap; not a C2 acceptance blocker.)**
- Reads-side regression check: a sampling of read intents compile + execute byte-identically (C2 hook is
  a no-op on read-only chains).

---

## What this plan does NOT do

- No preview-time discover, no manifest persistence, no Window-2 drift check → **Shape B (phase 2).**
- No executor implementation/registration → **forge-pipeline** (`claude/document-action-api-ZYmqX`,
  unpushed). C2's acceptance is bridge-side; live E2E (26-04) resumes when executors land.
- **No publish** (G2: no arg parity, bare tool unconfirmed) → **its own future motion** with own grounding.
- No multi-mutation chains, no R9 timewarp, no R7 session scope.
- Degradation-message wording recorded as **UX debt** (not expanded in C2). Finding 1's fail-safe lands the
  operator on the same DI.1 block as the unregistered case, so any future wording fix covers both
  unregistered and mis-declared uniformly.

---

## Plan-check disposition (DT + Creative, folded)

- **G1 — CONFIRMED SAFE** (DT, two-way grounding). Keystone holds.
- **G2 — publish EXCLUDED**, becomes its own motion. Both voices: scope *reduced* by grounding = converging
  on the real shape, not accumulating speculative capability.
- **Finding 1 (HIGH) — ADOPTED** into T1 (required before lock by both DT and Creative): the rewrite
  conjunction now asserts the *mapped executor* reads as mutating, turning G1's one-time fact into a
  continuously-enforced boundary invariant.
- **"No reshaping" invariant — scoped to rename** in prose (contradiction dissolved with publish removed).
- **Finding 2 (MEDIUM) — RELOCATED + cleared at the C2 hook (DT, traced to the bottom).** The hook-surface
  worry was mis-located: the strip-guard is robust to the `execution_tools ⊇ tools` mismatch (returns
  `None` on the not-found path too → preview still reached), so the C2 hook is benign. The real exposure is
  a *pre-existing* in-chat `apply <id>` replay narrowing on command text (`handlers.py:1080/:1889`), which
  C2 is merely the first to exercise. Captured as **T5** (trivial 2-callsite surface alignment, independent
  of T1/T2). **Not a C2 acceptance blocker** — canonical ratify (`:1345`) is already correct.
- **Recorded debt (not C2):** degradation-message wording; publish path.

Both reviewers: **lockable once the three required-before-lock amendments land** (Finding 1, publish
removed, invariant rescoped) — all three folded; Finding 2 traced + relocated to T5. **Plan LOCKED.**
