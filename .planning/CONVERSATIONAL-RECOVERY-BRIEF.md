# Pass-to-Code Brief — Conversational Recovery (CR.2)

**Frontier:** restore conversational *continuity*. **Not** answer fidelity, **not** the
consumer loop, **not** more substrate.
**Lineage:** successor to CR.1 (the read answer-pass). CR.1 made successful reads *speak*;
CR.2 makes recoverable *non-success* reads *continue*.
**Status:** room-converged + **DT verify points §10 all CLOSED** (Creative problem statement +
Orch synthesis + DT grounding ×2). Pass-to-code ready.
**Scope lane:** reads-first. Mutation interaction is bounded in §8.

> **Post-grounding characterization (Creative, ratified):** this is **not** "build conversational
> recovery" — it is **"replace terminal-on-recoverable with *deterministic* continuation-on-recoverable."**
> DT's grounding collapsed the speculative half: the substrate already holds the candidate sets
> *and* human-authored action labels, so **for CR.2's entire read scope the recovery path is fully
> deterministic — model re-entry never fires.** The missing piece was never intelligence; it is a
> conversation **state transition**. Model-re-entry survives in §5/§6 only as a *named, dormant
> escalation path* for some future recovery kind whose answer space isn't substrate-held.

---

## 1. The thesis (Creative, endorsed)

The conversational loop breaks *before* an operator receives a usable response. The substrate
correctly identifies recoverable internal states — referent ambiguity, unresolved referents,
tool-selection ambiguity — but treats them as **terminal user-facing outcomes** when they are
**inputs to the next conversational turn.**

**Invariant:** *No recoverable internal state may terminate the conversation.* Every recoverable
state produces either (1) a usable answer or (2) a clarifying turn that invites continuation.

## 2. Why this is doctrine, not a new doctrine

This lands *inside* "the orchestrator owns control flow, not meaning." Today, on a recoverable
state, the orchestrator emits a terminal `400` — that is the orchestrator making a *meaning*
decision ("this is a dead end") that belongs to the conversation. CR.2 has the orchestrator
choose **continue** instead of **terminate**; the recovery turn's *content* is authored by the
entitled layer (§5). The current terminal-on-recoverable behavior is the latent violation we are
correcting.

## 3. Grounded architecture (DT)

Three terminal feeder seams across two layers, with **two different return shapes** — this is why
the fix is a unifying sink, not a one-seam reshape:

| Seam | Layer | Enumerates | Return shape today |
|---|---|---|---|
| `__disambiguation__` → `MULTIPLE_PROJECTS` | referent-resolution (`handlers.py:674-680`) | real project candidates | `_chat_error` **400 envelope** |
| `__unresolved__` → sequence name | referent-resolution (`handlers.py:682-689`) | sentinel carries `{key, tool}` only — **but real names exist one layer up** via `_known_names_for(key, desktop)` (`resolver.py:346-360`) | `_chat_error` **400 envelope** |
| `tool_selection_ambiguous` | tool-narrowing (`_step.py:347-355`) | tool *outcomes* | `{"error": {...}}` **dict inside chain-step result** |

Sentinels: `DISAMBIGUATION_KEY` / `UNRESOLVED_KEY` (`_tool_chain.py:58-59`).

**Two true things at once:** the candidate *payloads* already exist (Creative under-scoped);
the *unifying recovery contract* does not (Orch under-scoped). The missing layer is a **common
recovery sink** that normalizes these bespoke envelopes into one continuation contract.

**Multi-turn input already exists** — the chat handler accepts `messages: non-empty list[dict]`
(`handlers.py:1473`), and PR29 already does a *structured* second turn for the project case
(`project_name=<v>` resolved against the candidate list, `handlers.py:607-655`). What is missing
is (a) the recovery *prompt* shaped to invite a reply, and (b) re-entry that consumes a **natural
conversational reply** — not only the explicit-param form.

## 4. The design — one sink, two strategies, normalized contract

**(a) A common recovery contract.** All three feeder seams route into one normalization point
that emits a single non-terminal taxon (proposed: `clarification_needed`) carrying:
`{ kind: "referent" | "tool", prompt, candidates: [...], resolve_hint }`. This replaces the
bespoke `_chat_error(400)` / chain-step `{"error"}` envelopes for *recoverable* states only.
Genuinely terminal taxa (`compile_error`, `chain_aborted`, transport `error`) are untouched.

**(b) Next-turn re-entry.** The operator's reply re-enters resolution with the prior candidate set
in context. ⚠ **Reply interpretation is a second authorship question, distinct from prompt
authorship (§5), and PR29 alone cannot answer it:** PR29 is **exact-match-only**
(`_name_resolve.py:14-20` — no partials/substrings), so a natural reply like *"the portofino one"*
will never exact-match `013_13_13_2026_2_1_portofino`. Per the §5 governing principle, reply
interpretation follows the same default: **relax matching to deterministic unique-prefix/substring
*scoped to the held candidate set*** (still no LLM, still scoped); escalate to model mapping only if
the reply stays irreducibly ambiguous against that set. **No new probe, no memory write** on the
re-entry (preserve PR26/PR28 contracts).

## 5. Authorship — governing principle + the resolved fork

**Governing principle (Creative steer, ratified):** *Deterministic recovery is the default
wherever the substrate knows the answer space. Model re-entry is escalation — justified only
when the recovery path cannot be formulated from substrate facts alone.* Burning an LLM
round-trip to ask "which of these five projects?" is paying inference cost to format a
dropdown. So the axis is **not** referent-vs-tool — it is *does the substrate already hold an
actionable answer space?*

| Recovery kind | Substrate answer space (grounded) | Authoring strategy |
|---|---|---|
| **Referent** (project/sequence) | concrete real entity names — actionable | **Deterministic enumeration** — fixed stem + real candidates. Cut-line safe (§6). |
| **Tool** (`tool_selection_ambiguous`) | enumerable; **`annotations.title` carries human-authored action labels** ("List all pipeline projects", "Get shot details with stack") (`registry.py:305-463`) — actionable | **Deterministic enumeration via `annotations.title`** (DT verify #2 CLOSED). `_ambiguity_outcomes` prefers `title`; the `description[0]` degenerate fallback (`_step.py:131-145`) only fires if `title` is *also* absent. Model re-entry **does not fire** for this scope. |

DT verify #2 (CLOSED): the degenerate-label fear is resolved by an **existing** field —
`annotations.title` already holds exactly the operator-actionable labels an ambiguity prompt
needs (inside the R3 fence; no minting). So the tool case lands on **deterministic** like every
other CR.2 recovery kind. Residual is **execute-time, not design**: confirm the runtime tool
object at the `_step.py` narrowing site exposes `annotations` (`getattr → .title`) — the data is
registered; only the attribute-access shape needs a 5-minute check.

## 6. Why this preserves the cut-line (no-impersonation)

- **Deterministic referent enumeration** is *presentation of facts that exist* (the candidates are
  substrate-real) under a **fixed stem** ("Found N projects — which one?"). A fixed stem is not
  meaning-authoring, and the handler already authors such strings today (`handlers.py:676,685`).
  Cut-line intact: no synthesized facts.
- **Model re-entry** keeps the model in the meaning lane — it authors the interpretive prompt; the
  orchestrator only chose *continue*. Cut-line intact: model authors, orchestrator routes.
  **(For CR.2's read scope this branch is dormant — see post-grounding note up top. It is retained
  only as the named escalation path for a future recovery kind whose answer space isn't
  substrate-held.)**
- Either way: **the handler never synthesizes facts that do not exist**, and **assent stays the
  operator's** (§8). For CR.2 the strongest position holds: **the model authors no recovery prose
  at all** — recovery stays deterministic, inspectable, testable, corpus-friendly.

## 7. Task breakdown

- **T1 — recovery contract + sink.** Define the `clarification_needed` taxon and the normalized
  payload; one normalization point both layers feed.
- **T2 — referent feeders (deterministic, enumerate).** Route `MULTIPLE_PROJECTS` + `__unresolved__`
  through the sink with deterministic enumeration. **DT verify #1 CLOSED → enumerate (not
  hint-fallback):** thread the real names into the `__unresolved__` sentinel at the failure point.
  Graceful degradation intact: empty desktop → `[]` → fixed-stem hint.
  - **Implementation note (2026-06-08, DT):** as shipped, `_known_names_for_key` does a *localized*
    `await mcp.call_tool("flame_context", {})` on the **cold** unresolved-sequence error path rather
    than reusing in-hand desktop (the brief's "not a probe" wording didn't hold literally —
    in-hand desktop wasn't reachable at `_tool_chain`'s layer without invasive threading). Defensible:
    cold path, not hot; degrades to `[]`. **The load-bearing invariant is unaffected** — §10 #3's
    no-probe constraint is about *re-entry*, which stayed pure.
- **T3 — tool feeder (deterministic, via `annotations.title`).** Route `tool_selection_ambiguous`
  through the sink. **DT verify #2 CLOSED → deterministic, de-conditionalized:** `_ambiguity_outcomes`
  prefers `annotations.title` (`registry.py:305-463`); `description[0]` degenerate fallback only if
  `title` absent. Model re-entry does NOT fire. Sole residual is **execute-time:** confirm the runtime
  tool object at `_step.py` narrowing exposes `annotations` (`getattr → .title`) — 5-min check, the
  data is registered. (R3 fence honored: `title` is an existing field, no minting.)
- **T4 — next-turn re-entry (reply interpretation).** Per §4(b): relax candidate-matching from
  PR29's exact-match to deterministic unique-prefix/substring scoped to the held set so a natural
  reply resolves; escalate to model only if irreducibly ambiguous. Assert no-probe /
  no-memory-write on re-entry.
- **T5 — recovery corpus + gate.** Build the read-query corpus from the probes; **each entry
  records the condition** (e.g. Flame-up vs Flame-down — DT: "list all projects" has ≥2 failure
  modes by condition, so query-only entries are non-reproducible).

## 8. Mutation interaction — EXPLICIT DEFERRAL (triggered), reads-first ratified

Referent ambiguity also occurs on **mutations** ("rename *this* shot" with 2+ matches). **As of the
2026-06-08 landing this is DEFERRED, not done:** the recovery sink is wired into
`compiled_non_mutating` only; the mutating-preview path still terminates on referent-ambiguity. The
mutation path was correctly left **untouched** (good — no recovery code near assent), but the original
"bounded, not deferred" framing overstated scope. Reads-first was the ratified scope, so this is
**carry-forward, not defect.**

- **Re-entry trigger:** an observed operator-hit on a *terminal* mutation referent-ambiguity in real
  use (measure-first, same discipline as the reads corpus) — not pre-built.
- **Forward constraint (binding when built):** the mutation recovery turn MUST fire **before**
  preview→ratify, never replace it; the `AssentRecord` chain stays the gate; **no recovery prose
  anywhere near assent.** (This is §8's original guard, preserved as the design contract for the
  increment.)

## 9. Spun-out task **CR.1b — narration wiring** (same milestone, different fix) — empty `final_text`

*"List all projects → empty"* is **not** a recovery gap. Grounded at `handlers.py:851-857`: the
`tool_forced` short-circuit deliberately emits `final_text=""` because *"the model never spoke on
this path."* The tool **succeeded**; CR.1's answer-pass lives at the `chain_complete` seam and the
short-circuit **bypasses it**. → **CR.1b:** wire the CR.1 answer-pass to the forced-tool
short-circuit. Tracked alongside CR.2 (same operator-visible symptom class) but must not be
folded into the recovery sink — that would scaffold a clarifying question around a read that
worked.

## 10. Acceptance gate & DT verify points

**Gate (scoped by task — the two fixes have distinct gates):**
- **CR.2 (recovery sink):** over the recovery corpus — **zero raw ambiguity errors, zero raw
  resolution errors.** Every ambiguous/unresolved interaction ends with an answer or a conversational
  recovery prompt.
- **CR.1b (narration wiring):** **zero empty `final_text` on successful reads.** This is NOT
  cleared by the recovery sink (the read succeeded — §9); it gates on the answer-pass wiring.
- The *combined* continuity claim ("no query strands the operator") holds only when **both** land.

**DT verify points — ALL CLOSED (grounded 2026-06-08):**
1. ✅ **CLOSED → enumerate.** `__unresolved__` candidates are cheaply available via
   `_known_names_for(key, desktop)` (`resolver.py:346-360`); T2 threads the list into the sentinel
   (plumbing, not a probe). Empty desktop degrades to fixed-stem hint.
2. ✅ **CLOSED → deterministic.** `annotations.title` (`registry.py:305-463`) is the richer existing
   field; `_ambiguity_outcomes` prefers it. T3 stays deterministic; model re-entry never fires.
   Residual = execute-time attribute-access check (`getattr → .title` at `_step.py` narrowing).
3. ✅ **CLOSED → contract preserved.** `_name_resolve.py` §1/§4/§5 (no upstream query, no `_MEMORY`
   read, no LLM, no memory write) + `handlers.py:641-643` (re-call short-circuits before any probe,
   never writes memory). The R1 relaxation only swaps the comparison operator inside the pure-dict
   matcher (still scoped, single-match-or-None) — all three invariants hold.

**Net for plan:** T2 upgraded (enumerate), T3 de-conditionalized (deterministic), T4 contract
confirmed. Nothing left conditional; the only open item is one execute-time 5-min attribute check.

## 11. Non-goals

- Not answer fidelity (CR.1 already shipped that for the success path; the §9 spin-out is the only
  fidelity touch, and it is wiring an existing pass).
- Not the consumer loop / projekt-forge re-pin — **CR.2 is consumer-independent** (corpus built
  from probes), which is *why* it precedes the consumer-loop close: continuity must exist before
  operator pressure can be applied.
- Not new substrate states — the substrate already produces every state we need; CR.2 only changes
  what happens to them.
- `forge_bridge.__all__` stays **19**.

## 12. Grounding anchors

`handlers.py:607-655` (PR29 second-turn), `:641-643` (re-entry short-circuits before probe / no
memory write), `:674-680` (MULTIPLE_PROJECTS), `:682-689` (UNRESOLVED), `:851-857` (empty
final_text short-circuit), `:1473` (multi-turn input); `_step.py:131-145` (`_ambiguity_outcomes`
degenerate fallback — to be `title`-preferring), `:347-355` (`tool_selection_ambiguous`);
`_tool_chain.py:58-59` (sentinels); `resolver.py:346-360` (`_known_names_for` — referent candidate
source for `__unresolved__`); `registry.py:305-463` (`annotations.title` — tool action labels);
`_name_resolve.py:14-20` (exact-match constraint to relax) / §1,§4,§5 (no-probe/no-memory/no-LLM
contract). Terminal regimes: `error / chain_aborted / compile_error / compiled_non_mutating /
compiled_mutating_preview / ratified_apply`.
