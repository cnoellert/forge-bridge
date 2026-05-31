---
milestone: v1.9
phase: CR.1
phase_name: Conversational Reads — the answer-pass spike + comprehension corpus
type: phase-framing
status: cycle-2-draft
drafted: 2026-05-31
derives_from: .planning/milestones/v1.9-CONVERSATIONAL-READS-FRAMING.md (RATIFIED 2026-05-31)
artifact_role: load-bearing — the CR.1 discuss + plan derive from this
grounding: live reads 2026-05-31 — handlers.py:1976-1990 (JSON chain_complete reattach) + :1161-1170 (SSE) + :1937/:1947 (aborted/preview branches, untouched); _chat_compile.py:179-205 (run_compile_branch outcome → chain_body); router.py:602 (acomplete signature); forge_bridge/tools/timeline.py:141 (get_sequence_segments -> str — tool returns are strings); forge-chat.js:176-178 (de-blank guard renders messages when present)
---

# CR.1 — the answer-pass spike + comprehension corpus

> **Cycle-1 phase-framing draft.** Compact per
> [[feedback-cadence-artifacts-shrink-to-load-bearing]]. Derives from the
> ratified v1.9 milestone framing; inherits its spine (NL-read-path as a
> *pressure instrument*), its mechanism ruling (Q-1 = (b) terminal
> synthesis), its four guards, and its named product (the comprehension
> corpus). This artifact resolves the milestone's Q-2 (phase decomposition)
> and hands the grounding obligations to CR.1-discuss.
>
> **The spine, restated for the phase:** make a *successful read* answer a
> human, in plain language, at 2–6 s — rough is fine — so an artist can
> finally drive the tool, and so the dogfood produces the **comprehension
> corpus** (answers loved / hated / overstated / omitted-context /
> missed-intent) the project does not currently have.

## What CR.1 delivers

Two capabilities and one artifact:

1. **The (b) answer-pass on successful reads.** At the `chain_complete`
   seam, a single `acomplete` synthesis turn takes the read results + the
   user's question and emits a plain-language, attributed answer. The model
   authors; the handler does not. **Creative's load-bearing framing:** *the
   synthesis pass does not generate new information — it generates
   understanding from information already present in `{step, result}`.*
   That is interpretation, not fabrication; the substrate stays
   authoritative.
2. **Minimal failure-indication on aborted reads** (Q-CR4, ruled cycle-2).
   When a read chain aborts, pass through *just enough* structured signal
   for an operator to see the request was attempted and where it stopped —
   the abort dict already carries `code` + `original_error` + `step_index`
   (`_engine.py:74-80`). **Structured passthrough, not model narration** —
   orchestrator-mute holds; no prose is authored on the failure path. Not
   diagnostics, not an observability project.
3. **The comprehension corpus** — the dogfood's product. Real artist-first
   usage (non-developer UAT per [[project-forge-bridge-ux-philosophy]]),
   each answer captured against the five fidelity classes. This is not a
   closing formality; it is *why the phase exists*.

## Grounding (live, 2026-05-31)

The reattach is surgical — the read results are already in hand at the
emit site:

- **JSON seam (Console-facing):** `handlers.py:1976-1990` returns
  `{chain: chain_body.get("chain", []), stop_reason: "chain_complete",
  preview: None, ...}`. `chain_body` is already computed
  (`_chat_compile.py:179`, `run_chain_steps`); `chain` is the list of
  per-step read results. **(b) inserts here:** synthesize from
  `chain_body["chain"]` + the user prompt, attach the answer, return.
- **SSE seam (CLI / event-stream consumers):** the symmetric emit at
  `handlers.py:1161-1170`. Console uses JSON (`forge-chat.js` has zero
  EventSource); whether CR.1 reattaches at both or JSON-first is a discuss
  question (Q-CR3).
- **Reads-only falls out of the regime switch structurally.** The model
  answer-pass fires *only* on `regime == "compiled_non_mutating"` (the
  `:1976` branch). The **mutating** branches — `preview_emitted` (`:1947`)
  and apply — are **fully untouched**: mutations stay deterministic preview
  + ratify, no model prose. The `chain_aborted` branch (`:1937`) is a
  *non-mutating read failure*, so per Q-CR4 it gains a **structured-error
  passthrough** (not the model pass, not prose). The answer-pass guard is
  enforced by *which branch the code lives in*, not a runtime check.
- **`acomplete` is exactly a synthesis pass** (`router.py:602`):
  `acomplete(prompt, *, sensitive=True default, system, temperature) ->
  str`. `sensitive=True` → local Ollama (qwen2.5-coder:14b), no tools,
  returns a plain string. No new public symbol; `__all__` stays 19.
- **The `chain` entry shape is `{step, result}`, not flat strings**
  (`_engine.py:85-86`). Each entry is `{"step": "<resolved tool
  invocation>", "result": <parsed>}`, where `result` is the *deserialized*
  tool return (a dict/list), not the raw `-> str` — the tool's string is
  re-parsed before it reaches the seam (`_step.py`). So the synthesis input
  is `[{step, result:<nested>}]`. **The `step` field is a free gift to the
  prompt:** it carries the resolved invocation
  (`forge_list_shots sequence_name=molecule`), giving the model the query
  context with no extra plumbing. The Q-CR1 synthesis prompt is written
  against this wrapped shape. (Cycle-1 said "string payloads" — it grounded
  one hop short, the manifestation-4 pattern; DT cycle-2 corrected it.)
- **DT cycle-2 live probe (the real nested shape):** synthesis over a real
  `[{step, result:<nested>}]` payload (3 shots, status/version/assignee) on
  the production 14b returned a clean, grounded, artist-readable answer in
  **2.5 s** (95 out / 224 in tokens) — and rendered a null assignee
  correctly as "no assignee." The milestone's 2–6 s lean survives contact
  with the real input size; the model handles structured result dicts with
  no flattening. (b) confirmed usable on the true shape.

### The continuity insight (strong lead, confirm at discuss)

The legacy `tool_forced` regime already renders an answer to the Console
via `messages` + `final_text` (`handlers.py:787`). The Console's de-blank
guard — CA.1's one shipped fix — renders `messages` *when present*:
`forge-chat.js:176-178`, `if (Array.isArray(body.messages)) { this.messages
= body.messages.map(...) }`.

**So if (b) populates `messages` on the `chain_complete` response with an
assistant turn carrying the synthesized answer, the Console renders it with
zero new JS** — and the answer lands on exactly the transcript CA.1 stopped
wiping. CA.1's guard ("don't wipe when messages absent") and CR.1's answer
("make chain_complete carry messages") are two halves of one mechanism.
*This is the leading response-envelope approach (Q-CR2), **confirmed by DT
cycle-2:** `forge-chat.js:176` renders a messages-bearing chain_complete
with zero new JS. The plan must pin the assistant turn as `{role:
"assistant", content: <answer>}` so it passes `renderableMessages()`
(`forge-chat.js:96`, filters to user/assistant/tool) and routes through
markdown rendering — correct here, since the answer is model prose, unlike
the verbatim x-text authority surfaces.*

## Q-2 RESOLVED — phase decomposition

**Ruling: single spike phase (CR.1), legibility + (a) seeded as
follow-ons.** The milestone leaned this; the grounding confirms it. The
answer-pass + the corpus it generates are one coherent slice — the corpus
*is* the answer-pass run under real pressure; splitting "ship the pass"
from "collect the corpus" would decompose a single act along a seam that
exists only in process, not in the work. What gets *seeded, not opened*:

- **The legibility / enrichment tier** (consumer-rendering + substrate
  `{reason_code, human_reason}` for failure/empty envelopes) — ranked by
  what the corpus surfaces, not pre-built. (The operator's pain #2, "no
  failure indication," lands here.)
- **The agentic cross-result capability (a)** — gated on the corpus, and
  carrying the milestone's forward constraint: its queries derive from what
  the tools actually compose, not aspirational examples.

## Grounding obligations for CR.1-discuss

Carried as hypothesis-to-confirm; discuss grounds these before the plan
asserts them:

1. **Tool-surface-derived dogfood scenarios (the operator's catch,
   binding) — GROUNDED with scope correction (DT cycle-2).** The dogfood
   query set must be *derived from what the registered read tools actually
   return*, not invented. **Corpus source = the production consumer surface
   (~58 `forge_*`/`flame_*` tools per the 24.1 prefix measurement), NOT the
   21 shipped `forge_bridge/tools/` read tools** (project 9 + batch 8 +
   timeline 4 — DT count). The dogfood runs against the production
   `projekt_forge` daemon; the shipped 21 are the substrate read tools, the
   corpus draws from the consumer set. *Remaining discuss work:* build the
   scenario list from single-result questions those ~58 tools can actually
   answer. No aspirational queries in the UAT.
2. **The corpus-capture mechanism (Q-5 from the milestone) — STILL OPEN.**
   How does each answer get recorded against the five fidelity classes — a
   structured log line, an artifact file, a field on the execution log?
   Must capture: the question, the `chain` it ran, the synthesized answer,
   the operator's verdict (loved / hated / overstated / omitted-context /
   missed-intent), and the (b) wall-clock. This is the phase's actual
   deliverable shape and the one fully-open obligation.
3. **forge-chat.js render — RESOLVED (DT cycle-2).** A messages-bearing
   `chain_complete` renders cleanly through `:176`; pin the assistant turn
   as `{role:"assistant", content}` (see continuity insight).
4. **`chain` entry shape — RESOLVED (DT cycle-2).** `{step, result:<parsed
   dict/list>}` per `_engine.py:85-86`, not flat strings; the synthesis
   prompt is written against the wrapped shape (see grounding).

## Open questions for CR.1-discuss (leans given)

- **Q-CR1: synthesis prompt + system shape.** What does the answer-pass
  system prompt say? *Lean: minimal and grounding-strict — "answer the
  user's question using ONLY the tool results below; if they don't contain
  the answer, say so; do not invent."* The fidelity clause (Part 6) lives
  here as a prompt instruction in cycle-1, observed-and-corrected at
  dogfood, not pre-hardened (milestone Q-3 lean).
- **Q-CR2: response envelope.** Reuse `messages`/`final_text` (zero-JS
  render, lead above) vs a new `answer` field (explicit, but needs JS)?
  *Lean: reuse `messages` — grounded, zero-JS, continuous with CA.1.*
- **Q-CR3: SSE parity.** JSON-only (Console) for the spike, or both seams?
  *Lean: JSON-first — Console is the dogfood surface; SSE rides as a fast
  follow if the CLI chat consumer needs it. Don't widen the spike.*
- **Q-CR4: failure-indication scope. RULED → minimal indication rides in
  the spike** (Creative experience-shape + DT cost-grounding, cycle-2). Not
  rich diagnostics — *just enough* for an operator to see the request was
  attempted and where it stopped. The reframe that flipped my cycle-1 lean:
  the abort dict already carries `code` / `original_error` / `step_index`
  (`_engine.py:74-80`), so this is a **structured-error passthrough**
  (consumer-render tier), near-zero-cost — "spike + one passthrough," not
  "spike vs. build the enrichment tier." Structured passthrough, not model
  prose: orchestrator-mute holds. (My cycle-1 "keep it narrow" instinct was
  the substrate-minimalism reflex fighting usability; corrected.)
- **Q-CR5: dogfood operator + setup.** Who drives the non-developer UAT, on
  which daemon (the production `projekt_forge` surface per the passoff
  cursor), against which project data? Logistics, but blocks the corpus.

## Constraints (inherited from the milestone, binding)

- **Reads-only.** Model answer-pass on `compiled_non_mutating` only.
  Mutating branches (preview / apply) fully untouched. `chain_aborted` (a
  non-mutating read failure) gets a structured-error passthrough only — no
  model prose (Q-CR4).
- **Mutations untouched.** No model prose near `preview_emitted`, ratify,
  apply, `AssentRecord`.
- **Orchestrator stays mute.** The model authors via `acomplete`,
  attributed; the handler never composes prose. Keep 24.4.
- **Fidelity.** No overstatement of certainty / tense / causality;
  prompt-enforced in cycle-1, dogfood-observed.
- **Substrate byte-equivalent.** `__all__` stays 19; version 1.4.1; the
  answer-pass rides existing `LLMRouter.acomplete`. No new endpoint, no new
  primitive.

## Status

**Cycle-2 phase-framing draft, 2026-05-31** (DT grounding + Creative
experience-shape folded). Spine, Q-2 single-spike ruling, and the
reads-only structural guard all hold — uncontested. Cycle-2 changes:

- **Entry shape RESOLVED** (obligation #4) → `{step, result:<parsed>}`
  (`_engine.py:85-86`), not flat strings; cycle-1 grounded one hop short.
  The `step` field is free query context for the synthesis prompt. DT live
  probe: clean grounded answer in 2.5 s on the real nested shape.
- **forge-chat.js render RESOLVED** (obligation #3) → zero-JS `messages`
  render confirmed; pin `{role:"assistant", content}`.
- **Obligation #1 GROUNDED + scope-corrected** → corpus source is the ~58
  consumer tools, not the 21 shipped; scenario-list build remains discuss
  work. Obligation #2 (corpus-capture mechanism) is the one fully-open one.
- **Q-CR4 RULED** → minimal failure-indication rides in the spike as a
  structured-error passthrough (Creative experience + DT near-zero-cost
  grounding); flipped my cycle-1 narrow lean.

The reattach is grounded surgical (`handlers.py:1976`); the zero-JS render
and the entry shape are now verified, not held. Remaining for cycle-3 /
discuss: the corpus-capture mechanism (#2), the Q-CR1 synthesis-prompt
fidelity wording, Q-CR3 SSE-parity, Q-CR5 dogfood logistics. The spike's
scope is now: **(b) answer-pass on success + structured failure-indication
passthrough on abort → the comprehension corpus.** Ready for CR.1-discuss.

Methodology note (parked): cycle-1's "string payloads" error is a 5th
instance of [[feedback-substrate-shape-grounding-at-plan-stage]]
manifestation-4 (envelope/shape grounded one hop short) — the synthesis
input shape required reading `_engine.py`, not the tool's `-> str` boundary.

---

*Cycle-1 drafted 2026-05-31 from the ratified v1.9 milestone framing.
Grounded against live `handlers.py` / `_chat_compile.py` / `router.py` /
`forge-chat.js`; no claims from memory alone. The reattach seam, the
reads-only structural guard, and the `messages` render continuity are all
verified against current code.*
