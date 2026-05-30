---
milestone: v1.8
thread: A
thread_name: Console Authority — operator-surface completion of the authority chain
phase_prefix: CA
status: phase-framing-draft-cycle-2
drafted: 2026-05-29
type: thread-framing
derives_from: .planning/milestones/v1.8-CONSOLE-AUTHORITY-FRAMING.md
preceded_by: v1.8 Thread B (main reliability cleanup) — CLOSED + PUSHED, 86548c0
grounding: cycle-2 live reads — console/handlers.py (ratify_endpoint :1208 + JSON preview_emitted :1954 + SSE preview_emitted :1140), console/_chat_compile.py (preview dict + conditional graph_intent_id :161-171), console/static/forge-chat.js (plain JSON fetch; messages replace :169; stop_reason check :183), store/assent_record_repo.py (get_by_graph_intent_id :211), cli/runtime_doctor.py (_check_ratification :479), console/templates/shell.html (nav), console/templates/panel.html (orchestration_termination sibling :59)
artifact_role: load-bearing — the CA.1/CA.2/CA.3 phase plans derive from this
naming_note: "v1.8 Thread A reuses the 'Thread A' milestone label but namespaces phase dirs as CA.* (Console Authority) to avoid collision with v1.7's A.1/A.2/A.3 (chat-compile/ratify/hardening). 'Thread A' = milestone-framing label; 'CA.*' = phase identity."
---

# Thread A — Console Authority

> **Cycle-2 phase-framing draft.** Compact per
> [[feedback-cadence-artifacts-shrink-to-load-bearing]]. Derives from the
> ratified v1.8 milestone framing; inherits its doctrine (authority-
> surface parity, ratified authority-operators-only) and its three
> grounded surface gaps. This artifact decomposes Thread A into phases
> and resolves the milestone's Q-1 (phase decomposition) + Q-4 (nav
> placement) — the two questions the milestone explicitly routed here.

## What Thread A delivers

The milestone thesis, verbatim: **the substrate is complete; the Console
projection of it is missing.** v1.7 shipped the authority chain
CLI-complete (`fbridge ratify`); the Console can show a preview event but
cannot drive ratification. Thread A closes that — every gap is
*projection of substrate the daemon already emits*, not new substrate.

This is the load-bearing grounding finding (re-verified cycle-2 across
three voices — DT grounding pass corrected three cycle-1 inaccuracies):

**The ratify substrate is fully wired; Thread A adds zero handler/endpoint code.**

- The Console chat panel is on the **JSON** transport, not SSE:
  `forge-chat.js` issues a plain `fetch()` with
  `Content-Type: application/json` and no `Accept: text/event-stream`
  (no `EventSource` anywhere). CA.1's preview branch lands in the **JSON**
  `preview_emitted` response at `handlers.py:1954`, not the SSE emit at
  `:1140`. (Both transports exist; the Console uses JSON.) — *cycle-1
  said "slots into the existing SSE switch"; that was wrong.*
- The JSON `preview_emitted` body is `{preview, chain: [], stop_reason:
  "preview_emitted", ...}` with **no `messages` key**, while
  `forge-chat.js` runs `this.messages = (body.messages || [])` (line 169)
  *before* it checks `stop_reason` (line 183 — a single `if (stop_reason
  === "orchestration_terminated")`, not a switch). So a mutating intent
  typed into the Console today would blank the transcript and drop the
  preview. **CA.1 is preview projection + ratify affordance _plus_ fixing
  this JSON preview-branch ordering** — still JS-only, but not "additive
  rendering." (Severity is high-confidence but marked
  hypothesis-to-confirm — see CA.1-discuss grounding obligation #1.)
- `outcome.preview` is a structured dict:
  `{kind: "graph-intent-preview", graph_intent_id, steps: [{step_text,
  tool_name, args_preview, would_mutate}], summary: {total_steps,
  mutating_steps, requires_ratification}}` (`_chat_compile.py:106-122`).
- **`graph_intent_id` rides inside `preview` — but conditionally:** the
  key is present only when `session_factory is not None`;
  `build_preview_from_steps` omits it otherwise
  (`_chat_compile.py:161-171`). Production always has a DB, but the ratify
  button must handle `preview.graph_intent_id` absent (disable, don't
  crash).
- `POST /api/v1/ratify` accepts `{graph_intent_id: <12-hex>, actor: str}`
  and returns the apply/abort outcome (`handlers.py:1208`, regex
  `[a-f0-9]{12}` at `:1244`). The button works after the chat response is
  gone because ratify is a **stateless POST** that resolves a *persisted*
  `AssentRecord` — `repo.get_by_graph_intent_id`
  (`assent_record_repo.py:211`, raising `AssentRecordNotFound`), backed by
  migration `0009_assent_record.py`. This persistence is the actual
  linchpin of "projection-only": preview → close panel → ratify later all
  resolves by id. The Console button calls the same endpoint
  `fbridge ratify` calls.
- `_check_ratification` lives in `cli/runtime_doctor.py:479` (**not**
  `read_api.py`, which has zero `ratif` references). Whether the Console
  health mirror is "just rendering" depends on whether `read_api.py`
  re-runs the runtime-doctor checklist or maintains its own — a CA.3
  grounding obligation, not a CA.1 concern.

Net: Thread A is HTML/CSS/JS + template work over an unchanged Python
substrate. `forge_bridge.__all__` stays 19; no new endpoints; no new
graph primitives.

## The three surface gaps (inherited from milestone, now grounded)

1. **Preview projection (chat panel).** Render the `preview_emitted`
   event as an interactive surface: the graph-intent steps (tool_name +
   args_preview + would_mutate flag), the summary (N steps, M mutating,
   requires_ratification), all from the structured `preview` dict. Read-
   only; the LLM authored the compile, the operator reads it.
2. **Ratify affordance (the authority click).** A button on a previewed
   mutating intent that POSTs `{graph_intent_id, actor}` to
   `/api/v1/ratify` and renders the apply/abort outcome. This is the
   operator's authority act — constitutionally NOT chat-suggested (the
   LLM never owns assent). The button exists because the operator
   decided to look, not because the model proposed it.
3. **Ratification ledger + health mirror.** A view consuming the A.3
   `forge_bridge.console.helpers` (recent_ratifications /
   pending_assent_records / recent_failed_applies) — the historical
   authority record — plus mirroring the `_check_ratification` doctor
   row into the Console health view.

## Q-1 RESOLVED — phase decomposition

The milestone surfaced three candidate decompositions (a/b/c) and routed
the choice here. **Ruling: option (b), three phases.**

- **CA.1 — preview projection + ratify affordance + JSON preview-branch
  fix.** Gaps 1+2 together, plus the JSON-path correction cycle-2
  surfaced. The grounding finding makes the milestone's worry about option
  (c) concrete: the milestone (and Creative) flagged that splitting
  "preview rendering" from "ratify click" decomposes a *single operator
  interaction* along a code seam that doesn't exist in operator
  experience. The operator sees a preview AND acts on it in one surface;
  `graph_intent_id` is already in the preview event, so the button has
  no separate plumbing phase to justify. (c) is rejected for that reason.
  Gaps 1+2 are one coherent slice — and CA.1 also corrects the JSON
  preview-branch ordering (`forge-chat.js:169`) so a mutating intent stops
  blanking the transcript; still JS-only, substrate byte-equivalent.
- **CA.2 — ratification ledger view.** Gap 3's historical record. Its own
  phase because it's a *new view* (new route, new template, new nav
  entry per Q-4) consuming different substrate (the A.3 helpers, not the
  chat JSON response). Distinct surface, distinct phase.
- **CA.3 — health-row mirror + hardening.** Gap 3's doctor mirror + the
  cross-cutting hardening (UAT catalog, non-author dogfood per the
  forge-bridge UX philosophy that every UI phase gets non-developer
  dogfood). Mirrors v1.7 A.3's hardening-phase shape.

CA.2 and CA.3 split gap 3 along a tense boundary: the ledger is the
retrospective record — **what authority acts happened** — while the
health-row mirror is the present-tense trust signal — **whether the
authority machinery is currently healthy and worth trusting**. That
past-vs-present distinction, not phase size, is what earns them separate
surfaces.

Rationale: (b) keeps each phase a coherent operator surface. (a)
single-phase would bundle three distinct templates + a nav change + a
hardening pass into one unreviewable slice. (c) over-fragments the
single preview→ratify interaction.

## Q-4 RESOLVED — ratification ledger nav placement

**Ruling: top-level nav item ("Ratifications").** The milestone drafter's
lean, confirmed against `shell.html`: the nav is a flat 5-item bar
(Tools / Executions / Manifest / Health / Chat) using a uniform
`nav-link` + `active_view` pattern. A 6th item drops in trivially. The
ledger is historical authority state — categorically distinct from chat
state (ephemeral conversation) and health state (current system status)
— so it earns its own surface, not a corner of an existing one. Lands in
CA.2 (the ledger-view phase).

## Architectural constraints (inherited, binding)

- **LLM never owns assent.** The ratify affordance is operator-driven.
  Preview is read-only context the operator chose to inspect; the click
  is the operator's, never the model's suggestion.
- **Ratify outcome is not a chat message.** apply_complete / chain_aborted
  outcomes render as a distinct authority-result card (the
  `orchestration_termination` sibling pattern, `panel.html:59`), never as
  a styled chat turn. *Constraint, not preference* (promoted from CA-Q2 by
  all three voices): the outcome is authority-decided, not model-authored
  — rendering it as conversation would blur the same authority/conversation
  boundary the previous constraint protects.
- **Derived, not reconstructed.** Every Console authority surface derives
  from substrate truth — preview from the JSON chat response, ledger from
  the A.3 helpers' `assent_record` reads, health from daemon doctor truth.
  No parallel client-side authority store.
- **Substrate byte-equivalent.** No Python handler/endpoint/primitive
  changes. If a gap *seems* to need substrate work, that's a signal to
  re-examine — the grounding says it doesn't. `__all__` stays 19;
  version stays 1.4.1.
- **Artist-first dogfood.** Per [[project-forge-bridge-ux-philosophy]],
  every UI phase gets non-developer dogfood UAT (CA.1 + CA.3 at minimum;
  the v1.7 A.5.3.2 / Phase 10.1 precedent).

## Phase summary

| Phase | Delivers | Substrate consumed | Dogfood |
|---|---|---|---|
| CA.1 | preview projection + ratify affordance + JSON preview-branch fix | JSON `preview_emitted` (`handlers.py:1954`) + `POST /api/v1/ratify` | yes |
| CA.2 | ratification ledger view + top-level nav | A.3 `console.helpers` assent reads | yes |
| CA.3 | health-row mirror + hardening + UAT catalog | `_check_ratification` doctor row | yes (non-author) |

## Open questions for discuss-phase (CA.1 first)

These are CA.1-discuss inputs, not framing blockers. (CA-Q2 outcome-
surfacing was promoted to a binding constraint — see above — and is no
longer an open question.)

- **CA-Q1: preview render fidelity.** *Lean: condensed summary +
  expandable steps, matching the existing chat tool-trace
  default-collapsed `<details>` pattern (panel.html already uses it).*
  Strengthened cycle-2: `args_preview` is `extract_explicit_params`,
  which today only ever yields `{project_id}` / `{project_name}` / `{}` —
  per-step args are usually empty, so full-fidelity rendering is
  low-value. Condensed is *more* right than cycle-1 knew.
- **CA-Q3: actor value pre-auth.** *Lean: "local", identical to the CLI
  ratify default — the endpoint itself defaults to `"local"`
  (`handlers.py:1242`) and the CLI defaults `"local"` (`cli/main.py:300`),
  so the ratify-surface auth migration is a single site.* Caveat
  (forward-pointer, not a CA.1 concern): the ratify endpoint uses its own
  `body.get("actor", "local")`, **not** the `_resolve_actor` D-06 chain
  (`X-Forge-Actor` header → body → `http:anonymous`) that the staged-ops
  handlers use (`handlers.py:205`). So the *milestone-wide* SEED-AUTH-V1.5
  migration is a three-convention unification (CLI ratify, Console ratify,
  staged-ops `_resolve_actor`), not one — overlaps
  SEED-POST-A1-ENVELOPE-CONTRACT-RECONCILIATION.

## CA.1-discuss grounding obligations

Carried from cycle-2's grounding pass — claims held as hypothesis-to-
confirm that CA.1-discuss must ground *before* the CA.1 plan asserts them:

1. **Map the full `/api/v1/chat` JSON return-shape across regimes.** The
   transcript-blank-on-preview risk rests on `preview_emitted` (`:1954`)
   lacking a `messages` key while `forge-chat.js:169` replaces
   `this.messages` unconditionally. But the `chain_complete` return
   (`:1977`) *also* appears to lack `messages`, which would imply normal
   chat blanks too — which cannot be right. A return-shape is not yet
   fully traced. Resolve this first; it sets CA.1's true scope (is the
   JSON branch fix a bug-close, or just correct ordering for a new taxon?).
2. **CA.3 only:** does `read_api.py`'s health mirror re-run the
   `runtime_doctor` checklist or maintain its own? Determines whether the
   `_check_ratification` mirror is rendering-only or more.

## Status

**Cycle-2 phase-framing draft (three-voice reconciliation: DT grounding +
Creative experience-shape + Orch synthesis).** Q-1 (decomposition → option
b) and Q-4 (nav → top-level) hold. Q-C (does projection-only hold?) —
**yes**, at the substrate level: `__all__` stays 19, no Python
handler/endpoint change. Cycle-2 corrected three cycle-1 grounding
inaccuracies (SSE→JSON transport conflation; `_check_ratification`
location; conditional `graph_intent_id`) and promoted CA-Q2 to a binding
constraint. CA.1's honest scope grew from "rendering only" to "preview +
ratify + JSON preview-branch fix" — still JS-only, substrate
byte-equivalent intact. Two hypotheses-to-confirm are handed to
CA.1-discuss as grounding obligations, not asserted here. Ready for
CA.1-discuss.

---

*Cycle-2 drafted 2026-05-30, reconciling DT's cycle-2 grounding pass +
Creative's experience-shape disposition + Orch synthesis. Grounded against
live console reads; no claims from memory alone. Counts (5 nav items, 19
__all__) verified by recount; the transcript-blank severity and the
`read_api.py` doctor-mirror shape are explicitly held as CA.1-discuss /
CA.3 grounding obligations, not asserted.*
