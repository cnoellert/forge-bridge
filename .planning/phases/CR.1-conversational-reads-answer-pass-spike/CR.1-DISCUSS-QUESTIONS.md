---
milestone: v1.9
phase: CR.1
phase_name: Conversational Reads — the answer-pass spike + comprehension corpus
status: phase-discuss
opened: 2026-05-31
drafted: 2026-05-31
type: phase-discuss
derives_from:
  - .planning/phases/CR.1-conversational-reads-answer-pass-spike/CR.1-FRAMING.md (cycle-2)
  - .planning/milestones/v1.9-CONVERSATIONAL-READS-FRAMING.md (RATIFIED 2026-05-31)
grounding: CR.1-FRAMING cycle-2 + this-session live reads — forge_bridge/corpus/ package (the EXISTING Layer-1 divergence corpus: imported-but-gated-off — guarded try/except imports at handlers.py:107 + _step.py:35, emit behind divergence_capture_enabled() env var, default-off) + handlers.py:1980 (JSON chain_complete compiled_non_mutating seam) / :1932 (JSON chain_aborted) + _engine.py:69-82 (authoritative abort-envelope shape) + router.py:602 (acomplete) + the registry-fix interlude (v1.5.1) that unblocks the production dogfood surface
artifact_role: load-bearing — CR.1-PLAN.md drafts from these rulings
---

# CR.1 — Phase discuss: rulings against the cycle-2 framing

Rules on the framing's five open questions (Q-CR1..Q-CR5) and two
grounding obligations. The spine, the single-spike ruling (Q-2), the
reads-only structural guard, and the inherited milestone laws are
preserved verbatim — not relitigated. Rationale is brief; framing
already walked the candidates. The one genuinely-new finding this
session is the **corpus-package collision** (OBL-2), surfaced by
grounding `forge_bridge/corpus/` before asserting a capture mechanism.

## R-CR1 — Synthesis prompt: minimal, grounding-strict (Q-CR1 lean confirmed)

The answer-pass system prompt instructs: *answer the user's question
using ONLY the tool results provided; if they do not contain the
answer, say so plainly; do not invent, infer beyond, or overstate.*
The fidelity clause (no overstated certainty / tense / causality)
lives here as **prompt instruction**, observed-and-corrected at
dogfood — NOT pre-hardened into validators (milestone Q-3).

- Input shape is the wrapped `[{step, result:<parsed dict/list>}]`
  (`_engine.py:85-86`), with the `step` field handed to the model as
  free query context. Confirmed usable: DT cycle-2 probe returned a
  clean grounded answer in 2.5s on the real nested shape.
- `acomplete(prompt, *, sensitive=True, system, temperature) -> str`
  (`router.py:602`), `sensitive=True` → local Ollama qwen2.5-coder:14b,
  no tools. No new public symbol; `__all__` stays 19.

**Why minimal over hardened:** the corpus exists to *discover* the
fidelity failure modes; pre-hardening the prompt presupposes what we
are trying to observe. PLAN locks the exact wording; the dogfood
corpus drives any tightening.

## R-CR2 — Response envelope: reuse `messages` (Q-CR2, resolved in framing)

(b) populates `messages` on the `chain_complete` response with an
assistant turn `{role: "assistant", content: <answer>}`. The Console
renders it with **zero new JS** via the CA.1 de-blank guard
(`forge-chat.js:176`), routed through `renderableMessages()`
(`:96`, filters to user/assistant/tool) → markdown rendering (correct
for model prose, unlike the verbatim x-text authority surfaces).
CA.1's "don't wipe when messages absent" and CR.1's "make
chain_complete carry messages" are two halves of one mechanism.

**Why reuse over a new `answer` field:** grounded, zero-JS,
continuous with CA.1. A new field would need JS for no gain.

## R-CR3 — JSON-first; SSE rides as fast-follow (Q-CR3 lean confirmed)

The spike reattaches at the JSON seam only (`handlers.py:1976`).
Console is the dogfood surface and uses JSON (zero EventSource). The
symmetric SSE emit (`:1161`) is left untouched in the spike; SSE
parity opens only if the CLI chat consumer needs it.

**Why JSON-first:** don't widen the spike past the dogfood surface.
SSE is a clean fast-follow with a known seam.

## R-CR4 — Minimal structured failure-indication rides in the spike (Q-CR4, ruled in framing)

On `chain_aborted` (a non-mutating read failure; JSON regime check
`handlers.py:1932`, SSE path `:1013`/`:1119`), pass through the
structured signal the abort dict already carries. **Authoritative
shape source is `_engine.py:69-82`**, where the envelope is built:
`error: {code, message, step_index, original_error}` (four fields —
`message` included). So an operator sees the request was attempted,
*why* it stopped (`message` + `original_error`), and *where*
(`step_index`). **Structured passthrough, not model prose**:
orchestrator-mute holds; no `acomplete` on the failure path.
Near-zero cost (the data exists).

**Why in-spike:** "spike + one passthrough," not "spike vs. build the
enrichment tier." Rich diagnostics / `{reason_code, human_reason}`
enrichment stays seeded, ranked by what the corpus surfaces.

## R-CR5 — Dogfood: production projekt-forge daemon; author-driven spike-1 corpus, non-developer UAT carried forward (Q-CR5 — resolved)

- **Surface:** the production `projekt_forge` MCP daemon (the ~58
  `forge_*`/`flame_*` consumer tool surface), **now unblocked** — it
  must re-pin `forge-bridge @ v1.5.1` to pull the registry self-heal
  (the publish fix from this session's interlude). Until it re-pins,
  publishes — and therefore populated read data — stay broken.
- **Project:** `013_13_13` — the standing test project (and the one
  in the 2026-05-31 findings doc that hit the registry bug). **Confirm
  it is re-published after the v1.5.1 re-pin** so reads return current
  state, not the partial/stale data left from the broken-publish era.
- **Driver:** the **author** (operator).

**Name it honestly — this is the author-driven spike-1 corpus, NOT the
non-developer UAT the UX philosophy mandates.** It is real and
load-bearing: it proves the mechanism (does (b) answer at 2–6s, captured
correctly?) and produces the first corpus, which is what *ranks the
legibility/enrichment tier* the framing seeds. But an author who knows
the ~58-tool surface under-samples the **comprehension-gap failure
class** a non-author would surface — the confusing / over-compressed /
operationally-useless answers that are the entire reason for the
grounded-AND-understandable second axis (`[[chat-synthesis-calibration]]`).

**Ruling (per `[[feedback-distinct-success-criteria-per-adjacent-layer]]`):**
author-corpus and non-author-corpus are **adjacent layers with different
success criteria**. The author-driven spike-1 corpus is CR.1's success
criterion. **Non-developer UAT (per `[[project-forge-bridge-ux-philosophy]]`)
stays an explicit carry-forward / seed — it is NOT closed by this run.**
Do not let the author run get booked as "non-developer UAT passed";
CR.1 close must not claim artist-comprehension fidelity it has not
measured (`[[feedback-operational-maturity-not-completeness]]`).

## OBL-1 — Scenarios derive from the consumer tool surface (binding)

The dogfood query set is built from **single-result questions the
~58 production `forge_*`/`flame_*` tools actually answer** — NOT the
21 shipped `forge_bridge/tools/` substrate read tools, and NOT
aspirational queries. The agentic cross-result capability (a) stays
gated on the corpus and out of CR.1.

**PLAN work:** enumerate the scenario list against the live consumer
surface (read `mcp__projekt-forge__forge_*` returns / the manifest),
each a single-tool read with a known-answerable question. No query in
the UAT that the registered tools cannot answer from one read.

## OBL-2 — Comprehension corpus is a NEW, distinct instrument (the grounding catch)

**Finding (this session):** `forge_bridge/corpus/` already exists — the
**Layer-1 divergence corpus** (A.5.3.2 Gate-1, PR1–PR15). It captures
execution-path/arbitration *divergence* (topology snapshots, candidate
sets, did-the-model-pick-the-same-path). Its ship-dark discipline is
**imported-but-gated-off**, NOT "not imported": guarded try/except
imports at `handlers.py:107` + `_step.py:35` (no-op fallbacks if the
package is absent), with the emit behind `divergence_capture_enabled()`
(env var, absent→disabled). It is a **different instrument answering a
different question** than CR.1's comprehension corpus (did the *answer*
help the human?).

**Ruling:** CR.1's comprehension corpus is a **separate, explicitly
distinct instrument**. Do NOT extend the divergence schema, share its
`SCHEMA_VERSION` lineage, or couple to its gate. DO mirror its proven
*persistence pattern* — atomic-append JSONL writer + versioned schema
+ reader (`_capture.py`/`_schema.py`/`reader.py`) — as a reference
shape, not a code dependency. Name the two distinctly everywhere
(**comprehension corpus** vs **divergence corpus**) per
`[[feedback-transitional-structure-naming]]` so the neighbor never
gets conflated again.

**Capture mechanism (lean — PLAN locks):** two-part.
1. **Auto-capture at the answer seam** (`handlers.py:1976`, where (b)
   attaches): append one structured record per answered read —
   `{question, chain:[{step,result}], answer, wall_clock_ms, model,
   ts}`. Atomic-append JSONL, mirroring the divergence writer's
   discipline. Default location a new artifact (e.g.
   `~/.forge-bridge/comprehension-corpus.jsonl`); NOT
   `executions.jsonl` (that is the learning pipeline's
   pattern-promotion log — different concern, would conflate).
2. **Verdict out-of-band.** The five fidelity classes (loved / hated /
   overstated / omitted-context / missed-intent) are a **human
   judgment added after**, not captured at answer time — so the artist
   dogfoods frictionlessly (just chats) and the verdict is annotated
   in a review pass (operator/developer-side). This keeps the artist
   surface zero-friction and the corpus analyzable.

**Why two-part / why not in-band verdict:** the artist cannot be asked
to classify their own answer mid-conversation without contaminating
the very UX the corpus measures. Auto-capture is silent; verdict is
deliberate and separate.

**Gate × wiring are ONE coupled question, not two (DT cycle catch).**
Because the dogfood runs against the *production* projekt-forge daemon
(R-CR5), there is no dogfood-vs-production boundary. So **default-on +
wired as a `forge_bridge` module = silent capture on every successful
read in production, indefinitely, past the spike** — exactly the
ungoverned institutional memory PR3 disciplined against. Default-on is
only safe if capture is not silently wired into the shipped daemon.
Two clean resolutions:

- **(lean) Env-gated like its sibling.** Capture lives in
  `forge_bridge` but is gated behind an env var (mirror
  `divergence_capture_enabled()`); the dogfood runbook sets the var.
  Identical posture in code; on-ness lives in the UAT setup and cannot
  outlive the spike by accident.
- **(alt) Default-on but a dogfood-local script**, not a `forge_bridge`
  module — safe precisely because it is not production-wired.

The **lean is env-gated** (option 1): it reuses the sibling's exact,
proven ship-dark mechanism and keeps capture inside the package where
the seam lives, with the spike's on-ness expressed in the runbook.

**Open for PLAN:** record schema (fields above + version), the
verdict-annotation surface (a reader + a simple tag step vs a thin
review affordance), and — under the env-gated lean — the env-var name +
artifact path (mirroring the divergence corpus's gate + writer shape).

## Disposition summary

| Q / OBL | Ruling |
|---|---|
| Q-CR1 | Minimal grounding-strict synthesis prompt; fidelity as prompt instruction, dogfood-observed |
| Q-CR2 | Reuse `messages` `{role:"assistant",content}`; zero-JS render |
| Q-CR3 | JSON-first; SSE fast-follow |
| Q-CR4 | Minimal structured failure passthrough in-spike; no model prose |
| Q-CR5 | Production projekt-forge daemon (re-pin v1.5.1 + re-publish), project `013_13_13`; author-driven spike-1 corpus; non-developer UAT carried forward, NOT closed by this run |
| OBL-1 | Scenarios from the ~58 consumer tools; single-result, non-aspirational |
| OBL-2 | NEW instrument distinct from `forge_bridge/corpus/`; mirror the persistence pattern, don't couple; two-part capture (auto-seam + out-of-band verdict); gate×wiring is ONE question → lean env-gated-in-package, dogfood enables via runbook |

## What PLAN needs to lock

- Synthesis prompt + system wording (against the `{step, result}` shape)
- Comprehension-corpus record schema + version, plus (under the
  env-gated lean) the env-var name + artifact path — mirroring the
  divergence corpus's `divergence_capture_enabled()` gate + writer shape
- Verdict-annotation surface (reader + tag step vs thin affordance)
- The scenario list (OBL-1) against the live consumer tool surface
- Failure-passthrough envelope from `_engine.py:69-82`
  (`{code, message, step_index, original_error}`) onto the `chain_aborted`
  JSON response
- Naming convention lock: comprehension corpus ≠ divergence corpus,
  enforced in module/file names if capture lands in `forge_bridge`
