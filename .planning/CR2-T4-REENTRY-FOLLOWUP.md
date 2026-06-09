# CR.2 Follow-up — T4 Next-Turn Re-entry Does Not Resolve (grounding + fix shape)

**For:** DT (confirm root cause + fix site) → code (apply).
**Status:** live-reproduced on portofino 2026-06-08, post-restart onto `1f069b9`. CR.2 prompt
emission + CR.1b narration verified working; **T4 reply-consumption does not resolve.**
**Scope:** one task's wiring. CR.2 design is intact — do **not** re-open §1–§9.

---

## Symptom (live, 3 reply forms — all fail to resolve)

Turn 1 "what shots are in the project?" → `200 clarification_needed` (referent, "Found 7 projects.
Which one?", real candidates). ✅ Then turn 2, replaying the server's **own** assistant message +
a user reply:

| Reply | Result |
|---|---|
| `013_13_13_2026_2_1_portofino` (exact full name) | `200`, 0.8s, **re-clarifies** (loops) |
| `013_13` (unique prefix) | `400 chain_aborted` — `CHAIN_STEP_FAILED` step 1 |
| `portofino` (unique substring) | `400 chain_aborted` — `CHAIN_STEP_FAILED` step 1 |

> **⚠ Repro correction (2026-06-08, captured per DT's "capture before assume"):** an *earlier* run
> showed `portofino → 504 compile_budget_exceeded` (30s). **That was a transient — not reproduced.**
> The **stable** behavior is the table above: exact-full-name **re-clarifies**; prefix/substring
> route into a **spurious 2-step chain** `forge_manifest_read → format_result` that fails on a
> missing `format` field (full capture below). None resolve.

In every case the conversation **fails to resolve** — the operator who answers the question gets
re-asked or errored. Continuity is half-restored: the system asks, but cannot consume the answer.

## Root cause (grounded — primary)

`recovery_params_from_messages` is correct and unit-green (`test_conversational_recovery.py:79`
resolves `"013_13"`). It **is** called — `handlers.py:1699`:

```
recovery_params = recovery_params_from_messages(messages, last_user_text)
```

But its **only application site** is inside the PR20/28 forced-single-tool branch,
`handlers.py:1853-1864`:

```
if ( tools_filtered_count == 1
     and tools_filtered_count < tools_available_count
     and not _APPLY_GRAMMAR.match(last_user_text.strip()) ):
    user_params = { **recovery_params, **resolved_params, **extract_explicit_params(last_user_text) }
    return await _execute_forced_tool(... user_params=user_params)
```

The gate requires the **current message** to narrow the registry to exactly one tool. But on a
recovery turn, `last_user_text` is the **bare referent reply** ("portofino") — it carries **no
tool-selection signal**, so `filter_tools_by_message(tools, "portofino")` (`:1762`) does not narrow
to 1, `tools_filtered_count == 1` is false, the branch is skipped, and **`recovery_params` is
computed then dropped.** The reply then flows to the LLM dispatch path and compiles the bare word →
30s timeout.

**The structural error:** the recovery reply is being used to *select the tool*, when its only job
is to *supply the missing referent*. The tool selection lives in the **prior** user turn (the
ambiguous query that triggered the clarification); the reply must re-run **that** intent with the
resolved param injected — not be filtered as if it were a fresh query.

> **DT confirmation + sharpening (2026-06-08):** the dead gate is real, and `recovery_params` is
> *already in the merge* (`:1861`) — the plumbing isn't missing, **the gate never fires.** Also: the
> earlier idea that `resolve_query_entities` might catch a bare name is killed — it resolves
> filter/if/select predicates + convention-normalized names, not a bare name against a candidate list.

## ⚠ The dead gate is NECESSARY but NOT SUFFICIENT (captured 2026-06-08)

The live repro **refutes** "param dropped → falls to a single fresh compile." Prefix/substring
replies never reach the `:1853` gate at all — they are **mis-routed upstream** into the chain path.
Full capture for reply `013_13`:

```
chain: [ { step: "forge_manifest_read", result: {data:{tools:[...synth tools...]}} } ]
error: CHAIN_STEP_FAILED step_index=1 →
  ToolError: format_result — "params.format Field required [missing]"
```

`parse_chain` (`handlers.py:1719-1720`) runs **before** the `:1762` filter and the `:1853` recovery
gate. So a recovery reply that lands in the chain path (or whose effective text is assembled from
message history) executes a spurious `forge_manifest_read → format_result` chain and dies — the dead
gate is downstream and never reached. **Exact-full-name takes yet another path** (fast re-clarify).

**Implication for the fix (this is the load-bearing change to the note):** recovery detection must
happen **EARLY** — when `recovery_params` is non-empty, short-circuit *before* `parse_chain`
(`:1719`) and before the `:1762` filter — not by "letting the `:1853` gate fire naturally," because
for prefix/substring replies that gate is unreachable. **First task for DT/code: instrument the
actual routing of a recovery reply** (where does `013_13` enter the chain path? is the effective
query assembled from message history?) — the static dead-gate read is correct but incomplete; the
live path has at least one more interceptor.


## Root cause (grounded — secondary: tool re-entry unimplemented)

`recovery_params_from_messages` only handles `clarification.get("kind") != "referent": continue`
(`_recovery.py:157`). `tool_clarification` emits a `resolve_hint{key:"tool"}` (`_recovery.py:114`),
but **no reader consumes a tool-choice reply.** So tool-ambiguity recovery can never round-trip
either — separate from the referent gap above, lower priority (tool ambiguity is rarer), but name
it so it is not rediscovered.

## Why the suite missed it

`test_conversational_recovery.py` tests the **matcher function** in isolation (candidate set in
hand → id). It does not exercise the **handler apply-path**: does a two-turn conversation actually
re-run the original intent with the resolved param? That end-to-end assertion is the missing
coverage — the Phase-8 lesson (unit tests that call the function directly mask whether the
production call path is wired). The live re-probe is what surfaced it.

## Fix shape (for code — design principle, not a prescriptive diff)

**Principle:** when `recovery_params` resolves (non-empty), recovery **short-circuits before**
tool-filtering on the reply. It reconstructs the effective dispatch as *(prior intent's
tool-selection) + (resolved referent param)* and executes — the reply supplies only the param.

Recommended shape (confirm against the routing trace first — see the necessary-but-not-sufficient
section):
1. Compute `recovery_params` (already at `:1699`). If **non-empty**, branch **EARLY** — ahead of
   `parse_chain` (`:1719`), the `:1762` tool-filter, **and** the `:1853` gate. *(DT initially preferred
   "let the `:1853` gate fire naturally" off the prior-intent text — the smaller change — but the live
   repro shows prefix/substring replies get mis-routed into the chain path **before** `:1853`, so the
   short-circuit must be earlier than the gate, not at it.)*
2. Recover the **prior** user-intent text (the turn before the clarification — already in `messages`,
   which the reader walks; **no new persisted state**, addressing DT's point that `resolve_hint`
   carries only `{key, accepted_reply}` and the prior tool isn't persisted) and drive tool selection
   (`filter_tools_by_message` / `deterministic_narrow`) off **that**, with `recovery_params` as caller
   params.
3. Dispatch through the existing `_execute_forced_tool` path. No new tool, no LLM, no fuzzy match.

**Guards the fix must keep (all already true — do not regress):**
- Deterministic only — no LLM anywhere in re-entry (`_name_resolve.py` stays pure dict match).
- No new probe / no memory write on re-entry (`_recovery.py:147-170` + the §10 #3 contract).
- Cut-line intact — re-entry resolves a param; it authors no prose.
- Mutation path untouched (§8 deferral stands; this is reads-only re-entry).
- Precedence: keep `extract_explicit_params` / `resolved_params` winning over `recovery_params`
  where keys collide (explicit user value > recovered) — i.e. preserve the `:1860` spread order.

**Client round-trip dependency (DT — name it so it isn't rediscovered as "the fix didn't work"):**
the whole re-entry hinges on the next request's `messages` carrying the prior assistant turn **with
its embedded `clarification_needed` field** (`_recovery.py:151-160` reads it; `response_body` embeds
it at `:134-141`). If the Console/CLI client echoes back only `{role, content}` and strips the
structured field, `recovery_params` is empty for a *different* reason and the server fix won't help.
Verify the real client preserves the field end-to-end.

## Verification (before calling T4 closed)

0. **Routing trace FIRST** (DT owns): instrument where `013_13` / `portofino` enter the chain path
   and why the effective dispatch becomes `forge_manifest_read → format_result`. Confirm the
   early-short-circuit site actually intercepts before that. Don't apply the fix off the static read
   alone — the repro proved it incomplete.
1. **New end-to-end test** (the missing coverage, DT owns the gate): two-turn conversation →
   ambiguous query → clarification → bare referent reply → assert single-tool dispatch lists shots
   for `013_13_…`, **not** a re-clarification, **not** a chain-abort, **not** a compile timeout.
   Variants: exact / unique-prefix / unique-substring / ambiguous(→stays clarified).
2. **Client round-trip check** (DT): assert the client resends the prior assistant turn with
   `clarification_needed` intact.
3. **Live re-probe** (same daemon, post-fix): reply "portofino" returns the shots.
4. Tool-kind re-entry (if scoped in): a tool-choice reply ("list shots") resolves the tool clarification.

### Creative's T4 acceptance (the gate — all must hold)
1. Ambiguous read query produces clarification. *(already ✓ live)*
2. Reply contains only the referent ("portofino").
3. Recovery path reuses **original intent** for tool filtering.
4. Resolved referent merges through the existing `recovery_params` path.
5. No LLM call.  6. No memory write.  7. No new probe.
8. No fresh compile (and no spurious chain) of the clarification text.
9. Two-turn E2E test passes.
10. Client round-trips `clarification_needed` intact.

## Disposition note

This is a **CR.2 increment**, not a defect against the ratified scope — reads-first continuity (the
prompt half) shipped and works; this completes the round-trip. Recommend it lands before the
v1.9 dogfood, since an operator who cannot answer a clarification cannot generate the comprehension
corpus the milestone exists to produce.
