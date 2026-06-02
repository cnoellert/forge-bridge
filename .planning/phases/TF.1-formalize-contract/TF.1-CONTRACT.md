# TF.1 — The Translation Contract (v1.13 Translation Fidelity)

**Status:** formalized — grounded against live source; T1 integrity audit closed (invariant HOLDS).
**Scope:** the contract Phases 2–4 build on. Refines (does not rewrite) `NLT-DISCOVERY-CLOSE.md` — the
boundary follows **contextuality**, not operation type.
**Normative clauses** are marked **[N]**; everything else is informative grounding.

---

## 1. Boundary object

> **Translation** = Natural Language → chain-step graph.  **Substrate** = chain-step graph → execution.

The chain-step graph (`compile_intent` output → `run_chain_steps` consumes → `AssentRecord` stores) is the
contract object. **No separate IntentIR.** Translation-pass and substrate-pass are independent verdicts
(`[[feedback-substrate-pass-translation-open]]`).

## 2. The resolution axis **[N]** — compile-resolved vs context-resolved

| Parameter class | Contract | Applies to |
|---|---|---|
| **compile-resolved** (concrete at compile) | the chain-step graph IS the full contract; validate at compile | reads + mutations |
| **context-resolved** (contextual ref needing dispatch/desktop/runtime state — "this sequence", "last 013 shot", "current project"; or derived mid-chain step-text) | **two-point**: graph captures intent + dispatch resolves; validate at **both** points | reads + mutations |

The axis is **not** reads-vs-mutations. A contextual mutation straddles too: "rename *this sequence*"
compiles to a graph carrying the unresolved ref, resolved at dispatch **post-ratify**. (Grounded: `desktop`
is only reachable at dispatch — the chat handler imports no Flame client; `resolve_query_entities`'s
`desktop` param, `resolver.py:61`, is a passed-in Mapping the resolver never fetches.)

## 3. Ratification-integrity invariant **[N]** (T1-grounded, HOLDS)

> **Dispatch may resolve refs the graph left unresolved (contextual → concrete); it may NEVER override a
> param the operator explicitly ratified.** "Explicitly ratified" ≡ `extract_explicit_params(ratified_step_text)`.

**Enforcement (grounded):** the dispatch merge `{**public_inherited, **semantic_params, **user_params}`
(`_step.py:261`) puts explicit `user_params` last → explicit wins; `semantic_params` fills omitted keys
only. `ratified_replay` (`:425`) gates only the DI.1 authority block, runs *after* the merge, and never
alters params — so replay re-derives from the ratified text (idempotent today; text-only resolution).
`project_name` (`:262/:378`) and the `sequence_name` previous-result fallback (`:397`, fires only on
`UNRESOLVED_KEY`) both fill, never override explicit. **Locked by a ratified-replay regression test** (T1).

**Limitation (not a violation):** the merge is *shallow* — an explicit top-level key wins wholesale; you
**cannot partially override a nested dict** (e.g. `role_overrides` is all-or-nothing per top-level key).
Record so no one later assumes partial nested override works.

## 4. Shape-A coupling **[N]** (note A — what the invariant does NOT cover)

The invariant protects **explicit** params across replay — **not contextual stability.** Once `desktop` is
wired, a contextual ref with no explicit value resolves **at apply** against live desktop; the commit node's
`verify(held, fresh)` is *both apply-time* (D2), so it does **not** catch preview→apply desktop drift.
Therefore:

- **explicit ratified params** → stable across replay (invariant §3).
- **contextually-resolved params** → **Shape-A** (resolve-at-apply); the operator ratifies *intent*, and the
  preview shows an **unresolved ref** ("rename this sequence"). preview→apply stability is a **separate
  property deferred to Shape B / Window-2.** Shape B = ratify the concrete resolved target → requires
  desktop-at-compile (a Flame round-trip in the compile path), the prerequisite a future Shape-B motion
  inherits.

Defect #3 is the first concrete architectural expression of Shape A.

## 5. Translation-quality objective **[N]** (note B — preserve honest uncertainty)

> **Preserve a parameter's unresolved state until it can be resolved honestly.** Manufacturing certainty
> where uncertainty should be preserved is a translation-layer defect.

**Grounded:** the system already has an honest-decline net — a truly-unresolvable `sequence_name` returns
`UNRESOLVED_REQUIRED_PARAM` → *"specify the exact sequence name"* (`:407`). In E2E-01 it **never fired**,
because the LLM baked `30sec_21` into the step text as an *explicit-looking* value → `extract_explicit_params`
captured it → the guard was bypassed. So example-salience (defect #1/#3) is not merely "wrong value" — it is
**"wrong value masquerading as explicit, slipping past the honest-decline net,"** converting uncertainty
into false certainty in a *ratifiable* preview.

Two Phase-4 slices serve this objective and are **prevention + detection** of the same failure:
- **example-strip (prevention):** with no example to lift, the model is likelier to leave the param
  unresolved → `:407` fires → the operator gets an honest "specify the exact sequence" instead of a
  silently-wrong preview. *The strip restores a safety net, not just removes a defect.*
- **provenance signal (detection):** a `filled-from-example` flag marks the value non-grounded even when it
  looks explicit, so the false-certainty is visible at the gate.

## 6. What this contract does NOT define

Detection of *which* params are context-resolved, wiring `desktop`, building the oracle, and the Phase-4
fixes — all downstream (Phase 2 taxonomy / Phase 3a oracle / Phase 4 quality). TF.1 defines the axis,
invariant, coupling, and quality objective; it ships no behavior change.
