---
milestone: v1.9
phase: CR.1
phase_name: Conversational Reads — the answer-pass spike + comprehension corpus
type: phase-framing
status: cycle-1-draft
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

One capability and one artifact:

1. **The (b) answer-pass on successful reads.** At the `chain_complete`
   seam, a single `acomplete` synthesis turn takes the read results + the
   user's question and emits a plain-language, attributed answer. The model
   authors; the handler does not.
2. **The comprehension corpus** — the dogfood's product. Real artist-first
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
- **Reads-only falls out of the regime switch structurally.** The
  answer-pass fires *only* on `regime == "compiled_non_mutating"` (the
  `:1976` branch). The mutating-preview branch (`:1947`, `preview_emitted`)
  and the aborted branch (`:1937`, `chain_aborted`) are **not touched** —
  mutations stay deterministic preview + ratify, no model prose. The guard
  is enforced by *which branch the code lives in*, not by a runtime check.
- **`acomplete` is exactly a synthesis pass** (`router.py:602`):
  `acomplete(prompt, *, sensitive=True default, system, temperature) ->
  str`. `sensitive=True` → local Ollama (qwen2.5-coder:14b), no tools,
  returns a plain string. No new public symbol; `__all__` stays 19.
- **Tool returns are strings** (`forge_bridge/tools/timeline.py:141`,
  `get_sequence_segments -> str`), so the synthesis input is string
  payloads — often JSON-ish or pre-formatted text. The answer-pass turns
  those into operator language. (DT-discuss obligation: characterize the
  *shape* of `chain` entries — are they raw tool strings, or wrapped step
  records? The synthesis prompt depends on it.)

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
*This is the leading response-envelope approach (Q-CR2); confirm
forge-chat.js renders a messages-bearing chain_complete cleanly
post-de-blank-fix before the plan asserts it.*

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
   binding).** The dogfood query set must be *derived from what the
   registered read tools actually return*, not invented. Enumerate the
   read-shaped tools on the dogfood daemon's surface (shipped
   `forge_bridge/tools/` *plus* the production consumer's `forge_*`/`flame_*`
   set), and build the scenario list from single-result questions those
   tools can actually answer. No aspirational queries in the UAT.
2. **The corpus-capture mechanism (Q-5 from the milestone).** How does each
   answer get recorded against the five fidelity classes — a structured
   log line, an artifact file, a field on the execution log? Must capture:
   the question, the `chain` it ran, the synthesized answer, the operator's
   verdict (loved / hated / overstated / omitted-context / missed-intent),
   and the (b) wall-clock. This is the phase's actual deliverable shape.
3. **forge-chat.js render confirmation** — confirm a messages-bearing
   `chain_complete` renders cleanly through `:176-178` post-CA.1 (the
   continuity insight above).
4. **`chain` entry shape** — raw tool strings vs wrapped step records
   (drives the synthesis prompt; DT grounding).

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
- **Q-CR4: failure-narration scope.** Does CR.1 also narrate
  `chain_aborted` / empty-read results, or is that the enrichment follow-on?
  *Lean: keep the spike to successful-read answers — the comprehension
  corpus is about answer fidelity, which needs answers. Failure-indication
  is the seeded enrichment tier. Revisit only if dogfood is unusable
  without it.*
- **Q-CR5: dogfood operator + setup.** Who drives the non-developer UAT, on
  which daemon (the production `projekt_forge` surface per the passoff
  cursor), against which project data? Logistics, but blocks the corpus.

## Constraints (inherited from the milestone, binding)

- **Reads-only.** Answer-pass on `compiled_non_mutating` only; preview /
  aborted / apply branches untouched.
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

**Cycle-1 phase-framing draft, 2026-05-31.** Single-voice; awaits
cross-voice cycles (DT: `chain` entry shape + the forge-chat.js render
confirm + tool-surface enumeration; Creative: dogfood scenario shape +
"usable enough" bar + the corpus-capture artifact; Orch: synthesis-prompt
fidelity + the seam-parity call). Q-2 ruled (single spike phase; legibility
+ (a) seeded). The reattach is grounded surgical (`handlers.py:1976`); the
zero-JS `messages` render is the leading envelope approach, held as
confirm-at-discuss. Four grounding obligations handed to discuss — #1
(tool-surface-derived scenarios) is the operator's binding catch. Ready for
CR.1-discuss.

---

*Cycle-1 drafted 2026-05-31 from the ratified v1.9 milestone framing.
Grounded against live `handlers.py` / `_chat_compile.py` / `router.py` /
`forge-chat.js`; no claims from memory alone. The reattach seam, the
reads-only structural guard, and the `messages` render continuity are all
verified against current code.*
