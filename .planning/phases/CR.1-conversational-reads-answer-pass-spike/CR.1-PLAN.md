---
milestone: v1.9
phase: CR.1
phase_name: Conversational Reads — the answer-pass spike + comprehension corpus
status: phase-plan
opened: 2026-05-31
drafted: 2026-05-31
type: phase-plan
derives_from:
  - .planning/phases/CR.1-conversational-reads-answer-pass-spike/CR.1-FRAMING.md (cycle-2)
  - .planning/phases/CR.1-conversational-reads-answer-pass-spike/CR.1-DISCUSS-QUESTIONS.md (f45404e)
grounding: this-session reads — handlers.py:1426 (router = console_read_api._llm_router, None-guarded) + :1969-1990 (JSON chain_complete compiled_non_mutating seam; chain_body.get("chain")) + :1932 (JSON chain_aborted branch) + _engine.py:69-82 (abort envelope {code,message,step_index,original_error}) + :85-86 ({step,result} chain entry) + router.py:602 (acomplete sig: prompt, sensitive=True, system=None, temperature=0.1; _in_tool_loop guard) + forge_bridge/corpus/_capture.py:197-199/465-620 (env-var gate + _make_header + single-write atomic-append) + corpus/reader.py (header schema_version validate + yield) + forge-chat.js:96/176 (renderableMessages filter + de-blank guard)
artifact_role: code-handoff — CR.1 implementation drafts from these shape locks
---

# CR.1 — Phase plan

Six shape locks (L1..L6) + the OBL-1 scenario enumeration covering the
CR.1-DISCUSS rulings. Rationale + cascade analysis live in FRAMING +
DISCUSS; this artifact carries what implementation needs to land each
lock. Per `[[feedback-substrate-shape-grounding-at-plan-stage]]` every
shape below is grounded by a file read at draft time (see frontmatter);
per `[[feedback-cadence-artifacts-shrink-to-load-bearing]]` ceremony is
dropped, shape locks kept.

**Substrate-byte-equivalence constraint (inherited):** `forge_bridge.__all__`
stays **19**; `pyproject.toml` stays `1.5.1`; no new external libraries.
The new comprehension package carries its own `__all__` (like
`forge_bridge.corpus`) — that does NOT touch the top-level 19.

## L1 — The (b) answer-pass at the JSON `chain_complete` seam (per R-CR1/R-CR2)

**File:** `forge_bridge/console/handlers.py`

**Where:** the `compiled_non_mutating` JSON return in `chat_handler`,
immediately after `chain_body = outcome.chain_body or {}` (~`:1969`)
and before the `return JSONResponse({...})` (~`:1977`). `router` is in
scope from `:1426`.

**Add (sketch — behavioral reference per
`[[feedback-brief-examples-as-behavioral-reference-shapes]]`):**

```python
chain = chain_body.get("chain", [])
answer, answer_ms = await _synthesize_answer(router, messages, chain)  # L2
# response dict gains:
    "messages": [{"role": "assistant", "content": answer}] if answer else [],
```

**Load-bearing properties:**
- **Reads-only by structure.** This edit lives ONLY in the
  `compiled_non_mutating` branch. `preview_emitted` (~`:1955`),
  apply, and ratify are untouched — the guard is *which branch the
  code is in*, not a runtime check.
- **`_in_tool_loop` guard does NOT fire.** The seam is the
  deterministic chain-engine path, outside `complete_with_tools`, so
  `acomplete`'s `RecursiveToolLoopError` guard (`router.py`) is
  inert here. Confirmed by control flow, not assumed.
- **Synthesis failure must not fail the read.** The read already
  succeeded (`chain_complete`). `_synthesize_answer` swallows its own
  exceptions (L2) and returns `("", ms)`; the response then carries
  `messages: []` and the Console falls back to CA.1 no-wipe behavior
  (`forge-chat.js:176` renders only when messages present). The
  answer pass is additive; it cannot regress the read.

**Acceptance:**
- A non-mutating read returns `messages:[{role:"assistant",content}]`;
  Console renders it with zero new JS (passes `renderableMessages()`
  `forge-chat.js:96` → markdown).
- Preview / apply / ratify responses are byte-identical to pre-CR.1.
- `acomplete` raising → response still 200 with the chain + empty
  messages (no 5xx, no wiped transcript).

## L2 — Synthesis prompt + `acomplete` call (per R-CR1)

**File:** `forge_bridge/console/handlers.py` (private helper
`_synthesize_answer`, sibling to existing `_chat_*` privates) — or
`forge_bridge/console/_answer.py` if it reads cleaner; no public symbol.

**Signature:**

```python
async def _synthesize_answer(
    router: Any,
    messages: list[dict],
    chain: list[dict],   # [{step, result}], result already parsed (_engine.py:85-86)
) -> tuple[str, int]:    # (answer_text, wall_clock_ms); ("", ms) on any failure
```

**Call:** `await router.acomplete(prompt, sensitive=True,
system=_SYNTHESIS_SYSTEM, temperature=0.1)` — `sensitive=True` → local
Ollama qwen2.5-coder:14b, no tools, no data egress.

**`_SYNTHESIS_SYSTEM` (locked wording; dogfood tunes per milestone Q-3):**

> Answer the user's question using ONLY the tool results provided.
> If the results do not contain the answer, say so plainly. Do not
> invent values, infer beyond the data, or overstate certainty,
> tense, or causality. Be concise and plain-language — an artist,
> not a developer, is reading.

**User prompt builder:** the question is the last user turn
(`messages[-1]["content"]`); the evidence is the wrapped chain — emit
each entry as `"- {step}\n  {compact-json(result)}"` so the resolved
invocation (`step`, e.g. `forge_list_shots sequence_name=molecule`) is
free query context. DT cycle-2 probe: 2.5s / 95-out-224-in tokens on
the real 3-shot nested shape; well inside the 2–6s lean and the 125s
outer wall-clock.

**Acceptance:** grounded answer on a populated read; "the results do
not contain that" on an empty/irrelevant read; null fields rendered as
absence ("no assignee"), not fabricated.

## L3 — Comprehension capture module (per OBL-2; mirror, do not couple)

**New package:** `forge_bridge/comprehension/` — a **distinct
instrument**, named so it can never be conflated with
`forge_bridge/corpus/` (the divergence corpus). Mirrors corpus's
*pattern*, imports nothing from it.

**Files (mirror `corpus/_capture.py` + `reader.py` shapes):**
- `_capture.py` — `comprehension_capture_enabled() -> bool` (reads
  `FORGE_BRIDGE_COMPREHENSION_CAPTURE`, `_TRUTHY={"1","true","yes"}`,
  absent→False, invalid→warn-once) + `emit_comprehension_capture(...)`.
- `_schema.py` — `SCHEMA_VERSION = "1"`, `validate_comprehension_record`.
- `reader.py` — `read_comprehension_file(path)` (header `schema_version`
  check + yield records); see L6.
- `__init__.py` — own `__all__` (does not touch top-level 19).

**`emit_comprehension_capture` (fire-and-forget, keyword-only —
mirror corpus I-6):**

```python
def emit_comprehension_capture(
    *, question: str, chain: list[dict], answer: str,
    wall_clock_ms: int, model: str,
) -> None:
    # entire body wrapped in try/except Exception → log WARNING + swallow.
    # observation failure cannot become answer failure.
```

**Writer discipline (mirror `corpus/_capture.py:605-620`):** single
`file.write(...)` atomic append; bundle `_header` + first record when
the file is new/empty; record-alone when appending; date-partitioned
JSONL under `FORGE_BRIDGE_COMPREHENSION_DIR` (default
`~/.forge-bridge/comprehension/`). No partial-record recovery.

**Wiring + gate (per OBL-2 coupling ruling — env-gated, NOT
default-on):** L1 calls `emit_comprehension_capture(...)` after
synthesis, but the package's own gate means it is a **no-op in the
shipped daemon unless `FORGE_BRIDGE_COMPREHENSION_CAPTURE` is set**.
On-ness lives in the dogfood runbook (L-UAT), so capture cannot
outlive the spike by accident — closes the PR3 ungoverned-memory risk
DT flagged.

**Acceptance:** gate unset → `emit_*` is a no-op, zero files written,
answer path unchanged. Gate set → one JSONL record appended per
answered read; a raised exception inside `emit_*` is swallowed and the
answer still returns.

## L4 — Comprehension record schema (per OBL-2)

**File:** `forge_bridge/comprehension/_schema.py`

**Record shape (`schema_version="1"`):**

```json
{
  "schema_version": "1",
  "captured_at": "<iso8601>",
  "question": "<user question>",
  "chain": [{"step": "<resolved invocation>", "result": <parsed>}],
  "answer": "<synthesized text>",
  "wall_clock_ms": 2500,
  "model": "qwen2.5-coder:14b",
  "verdict": null
}
```

**Header record:** `{"_header": true, "schema_version": "1",
"captured_at": "<iso8601>"}` (mirror `corpus/_capture.py:_make_header`).

**`verdict`** is `null` at capture (two-part capture, R/OBL-2) and is
filled out-of-band by L6 to one of the five fidelity classes:
`loved | hated | overstated | omitted_context | missed_intent`. Adding
the enum's allowed values is non-breaking; *requiring* verdict would be
a `SCHEMA_VERSION` bump (it is never required — it is annotation).

**Acceptance:** `validate_comprehension_record` accepts a verdict-null
record and a verdict-tagged record; rejects a missing required field
(question/chain/answer/wall_clock_ms/model/captured_at) by name.

## L5 — Structured failure passthrough on `chain_aborted` (per R-CR4)

**File:** `forge_bridge/console/handlers.py` — JSON `chain_aborted`
branch at `:1932` (NOT the SSE path `:1013`/`:1119`).

**Surface** the abort envelope built at `_engine.py:69-82` —
`{code, message, step_index, original_error}` — onto the JSON response
under an `error` key. **Structured passthrough, not model prose:** no
`acomplete` on this branch; orchestrator-mute holds. Whatever shape the
engine already produces is forwarded verbatim; the handler adds no
narration and reconstructs nothing.

**Acceptance:** an aborted read returns `stop_reason:"chain_aborted"`
+ `error:{code,message,step_index,original_error}`; no `messages` key
authored; no LLM call on the path (assert via no qwen turn logged).

**Residual grounding obligation (manifestation-4, flagged honestly):**
the *source* shape is grounded at `_engine.py:69-82`, but the
handler-side availability is NOT yet read — i.e. does `outcome` (or the
`body` already built at `:1934`) actually carry that error envelope
into the `:1932` branch, or does it stop at the engine boundary?
Implementation/review confirms this trace before merging the key; if
the envelope does not reach the handler, L5 needs a plumbing step, not
just a passthrough.

## L6 — Reader + verdict-annotation surface (per OBL-2 two-part capture)

**File:** `forge_bridge/comprehension/reader.py` + a thin tag step.

- `read_comprehension_file(path)` mirrors `corpus/reader.py`: validate
  header `schema_version`, yield each record (raise
  `SchemaVersionMismatch` on skew).
- **Verdict annotation (lean — reader + simple tag step):** a small
  loop that reads records with `verdict is null`, prints
  question/answer/chain, prompts for one of the five classes, and
  rewrites the file with the verdict filled. Runs **out-of-band**
  (operator/author review pass), not during the artist's session — so
  capture stays silent and the verdict stays deliberate. Whether this
  is an `fbridge` subcommand or a dogfood-local script is an
  implementation choice; it adds **no** MCP tool, HTTP endpoint, or
  wire surface, and nothing to the top-level `__all__`.

**Acceptance:** the tag step turns a verdict-null corpus into a
verdict-tagged one without losing or mutating any other field; a second
pass skips already-tagged records.

## OBL-1 — Dogfood scenario enumeration (single-result, consumer-tool-derived)

Built from the live production `projekt_forge` consumer surface — each
a single-tool read with a known-answerable, plain-language question.
**No query that the registered tools cannot answer from one read.**
Finalize the exact list against the daemon at dogfood time; the
grounded starting set (against tools present in this session):

| # | Question (artist phrasing) | Tool it resolves to | Single-result? |
|---|---|---|---|
| 1 | "what shots are in sequence X?" | `forge_list_shots` | ✓ list |
| 2 | "what's the status of shot Y?" | `forge_get_shot` | ✓ |
| 3 | "how many versions does shot Y have?" | `forge_get_shot_versions` | ✓ |
| 4 | "what's the latest published plate for Y?" | `forge_list_published_plates` | ✓ |
| 5 | "what media is registered for Y?" | `forge_list_media` | ✓ |
| 6 | "what segments are on the 30sec sequence?" | `flame_get_sequence_segments` | ✓ |
| 7 | "what assets does shot Y use?" | `forge_get_shot_stack` / `forge_list_assets` | ✓ |
| 8 | "what depends on plate Z?" | `forge_get_dependents` | ✓ |

(8 is the live-grounded floor; PLAN does not cap — the runbook may add
more as the daemon surface confirms them. Listed so the UAT is not
silently truncated per `[[feedback-grep-c-completion-invariant]]`.)

## L-UAT — Dogfood runbook (per R-CR5; author-driven spike-1 corpus)

- **Prereq:** projekt_forge re-pinned to `v1.5.1`; `013_13_13`
  re-published so reads return current state.
- **Enable capture:** `export FORGE_BRIDGE_COMPREHENSION_CAPTURE=1`
  before the dogfood session (the gate's only on-switch; unset after).
- **Run:** author drives the OBL-1 scenarios (+ ad-hoc) through the
  Console chat against `013_13_13`.
- **Annotate:** out-of-band L6 tag pass assigns each answer a fidelity
  class.
- **Close honesty (R-CR5):** this is the **author-driven spike-1
  corpus**. Non-developer UAT stays an explicit carry-forward — CR.1
  close MUST NOT claim artist-comprehension fidelity it has not
  measured (`[[feedback-operational-maturity-not-completeness]]`).

## Task order

1. L3 + L4 (capture module + schema) — substrate first, tested on its
   own per `[[feedback-substrate-before-consumer-landing]]`; gate-off
   no-op + gate-on append + swallow-on-error.
2. L2 (`_synthesize_answer`) — unit against a stubbed router returning
   a fixed string; assert prompt-builder shape from `[{step,result}]`.
3. L1 (seam wiring) — wire synthesis + `messages` + the L3 emit call;
   assert reads-only branch, graceful synthesis-failure, preview/apply
   byte-identical.
4. L5 (abort passthrough) — independent of L1; assert envelope + no LLM.
5. L6 (reader + tag step).
6. L-UAT (author-driven dogfood) → seed-1 comprehension corpus.

## Acceptance (phase)

- Non-mutating reads answer in plain language at ~2–6s via `messages`;
  Console renders zero-JS; mutating paths untouched; aborts carry the
  structured error.
- Gate-off: shipped daemon byte-equivalent (no capture, no files).
  Gate-on: one record per answered read; verdict annotated out-of-band.
- `forge_bridge.__all__` == 19; version `1.5.1`; no new external deps;
  no coupling between `forge_bridge/comprehension/` and
  `forge_bridge/corpus/`.
- Spike-1 corpus produced under author drive; non-developer UAT logged
  as carry-forward, not closed.
