# S3 Capture-Flow — Seam (Orch grounding → DT/Creative redline)

**Status:** S3 seam settle, pre-build (the room ruled (b): lock the seam first — S3 is the first touch of the live chat path, resolver-blindness is migration-if-wrong). **Grounded against** `console/handlers.py` (the SSE emission) + `console/_chat_compile.py` (`CompileBranchOutcome`).

## Settled (grounded — not in dispute)

**The exposure point is pinned and minimal.** `outcome.steps` (`_chat_compile.py:27`) is exactly `compiled_graph` (`list[str]`). The `compile_complete` SSE event (`handlers.py:1209-1213`) fires **before** the regime branches — for reads AND mutations — but currently emits only `steps_count=len(outcome.steps)`. **The sole live-path touch:** add `"compiled_graph": list(outcome.steps)` to that event's data. Exposure-only — the value is already computed; no change to compile, dispatch, routing, filtering, or ratify. This is the one place "wrap vs modify" is tested, and it stays firmly on "wrap." (DT's two-shape finding confirmed: `chain_complete` carries steps as `chain[].step`; `preview_emitted` carries `chain: []`; only `outcome.steps` is uniform.)

**Resolver-blind via the transport boundary (DT's seam — endorsed).** Operator types in the Flame Console (in-Flame, has the flame API); `compile_intent` runs on `:9996` and is already desktop-blind (TF.1). So: world_state is read in-Flame; the Console POSTs **prompt-only** to `:9996/api/v1/chat`; compile stays blind exactly as today. The guarantee is structural — world_state never enters the compile call — and `compile_intent`/`run_compile_branch` stay behaviorally untouched (PLAN §7 satisfied by construction).

**Request-time snapshot (DT — endorsed).** world_state is snapshotted **before** the `:9996` call (the LLM compile takes seconds; operator focus drifts). The record's world_state must be the focus *at the prompt*, or S4 compares the graph against post-drift state.

## The one fork to settle — and a new constraint that reshapes it

DT's append-location options were (Console-side write) vs (capture endpoint). **Probe #4 established a fact that bears on it: Flame's Console Python cannot import `forge_bridge`** (we already carry inlined verbatim copies in the probes for exactly this reason). So `assemble_world_state` / `build_record` / `append_record` are **not callable from the Console**. The fork is really:

- **(A) Console-side write — INLINE forge_bridge into the Flame capture script.** world_state never crosses the wire at all (DT's strongest transport guarantee). Cost: inlined verbatim copies of assemble/build/append (copy-drift tax — a recurring cost we already pay in 4 probes; would need a sync-test), plus FS access on the Flame box.
- **(B) A read-only `:9996` capture endpoint, storage-only.** The Console POSTs the assembled record (prompt + compiled_graph + outcome + world_state) to a *separate* `POST /api/v1/context-capture` that **only validates + appends** — it never calls compile. world_state reaches `:9996` only via the storage endpoint, **provably never the compile endpoint** (different route, different code path). Cost: world_state is on the wire (for storage), and the daemon writes the corpus (single corpus location, no Flame-box FS dependency).

**Both satisfy the resolver-blind DOCTRINE** — world_state never enters `compile_intent`. They differ on the *purity claim*: (A) "world_state never crosses the wire"; (B) "world_state only ever reaches a storage endpoint, never the compile endpoint, enforced by route separation."

**Orch lean: (B), the separated storage endpoint.** The doctrine is compile-blindness, not transport-abstinence — and (B) enforces it structurally via endpoint separation (auditable: `/chat` is prompt-only, `/context-capture` is storage-only, grep-able that compile never reads the capture route). It avoids the inlining/copy-drift tax that (A) pays forever, and centralizes the corpus on the daemon (no per-Flame-box FS write). (A)'s extra purity (off-wire entirely) buys little the doctrine needs, at a standing maintenance cost. I'd take (A) only if the room weights "world_state must never transit the bridge process, even for storage" as a hard requirement — name it if so.

## Second settle-point — outcome mapping (Option-B)
Terminal SSE taxon → `OUTCOME_VALUES`: `chain_complete → chain_complete`; `chain_aborted → chain_aborted`; `compile_error → compile_error`. The mutation case: `preview_emitted` SSE — **record as `preview_emitted` (Orch lean: the observed terminal state; capture is observational, the operator does not proceed to ratify) vs `blocked_at_ratify` (DT: the Option-B semantic)**. Both are in the vocab. I lean recording the *observed* taxon (`preview_emitted`) and reserving `blocked_at_ratify` for a future S3 variant that actively attempts apply and hits the executor gap — keeps capture purely observational. Settle.

## What S3 does NOT do (the three proofs Creative wants, locked by this seam)
1. **Resolver-blind:** world_state out-of-band, never into `compile_intent` (the `/chat` POST is prompt-only; capture is a separate path).
2. **Preview-capture boundary:** capture after compiled_graph/preview exists, before ratify/apply; mutations record at preview (no executor needed — preview is built from the compiled chain; the bootstrap-gap blocks only apply, which Option-B defers).
3. **No behavior mutation:** capture only appends records — no change to routing, tool filtering, or commit/ratify. The only live-path edit is the exposure-only `compiled_graph` field.

## Ask to the room
Settle the fork (A vs B; my lean B) + the outcome-mapping label (`preview_emitted` vs `blocked_at_ratify`; my lean `preview_emitted`). Those two settle the S3 architecture; then I draft the S3 plan with the wiring fully pinned. The exposure point and the resolver-blind-via-transport seam are grounded and ready regardless.
