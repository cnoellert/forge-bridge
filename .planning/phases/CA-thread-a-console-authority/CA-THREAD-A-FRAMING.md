---
milestone: v1.8
thread: A
thread_name: Console Authority — operator-surface completion of the authority chain
phase_prefix: CA
status: phase-framing-draft-cycle-1
drafted: 2026-05-29
type: thread-framing
derives_from: .planning/milestones/v1.8-CONSOLE-AUTHORITY-FRAMING.md
preceded_by: v1.8 Thread B (main reliability cleanup) — CLOSED + PUSHED, 86548c0
grounding: this-session live reads of console/handlers.py (ratify_endpoint + preview_emitted SSE), console/_chat_compile.py (preview dict shape), console/static/forge-chat.js (SSE stop_reason switch), console/templates/shell.html (nav), console/templates/health/detail.html + read_api.py (_check_ratification row)
artifact_role: load-bearing — the CA.1/CA.2/CA.3 phase plans derive from this
naming_note: "v1.8 Thread A reuses the 'Thread A' milestone label but namespaces phase dirs as CA.* (Console Authority) to avoid collision with v1.7's A.1/A.2/A.3 (chat-compile/ratify/hardening). 'Thread A' = milestone-framing label; 'CA.*' = phase identity."
---

# Thread A — Console Authority

> **Cycle-1 phase-framing draft.** Compact per
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

This is the load-bearing grounding finding (verified this session):

**The ratify substrate is fully wired; Thread A adds zero handler/endpoint code.**

- `preview_emitted` SSE event already carries `{preview, chain,
  stop_reason: "preview_emitted", request_id, tools_available, ...}`
  (`handlers.py:1140`).
- `outcome.preview` is a structured dict:
  `{kind: "graph-intent-preview", graph_intent_id, steps: [{step_text,
  tool_name, args_preview, would_mutate}], summary: {total_steps,
  mutating_steps, requires_ratification}}` (`_chat_compile.py:106-122`).
- **`graph_intent_id` rides inside `preview`** — so the ratify button's
  only argument is already in the event the browser receives. No handler
  change needed to plumb it.
- `POST /api/v1/ratify` accepts `{graph_intent_id: <12-hex>, actor: str}`
  and returns the apply/abort outcome (`handlers.py:1208`). The Console
  button calls the same endpoint `fbridge ratify` calls.
- `forge-chat.js` (202 lines) already branches on `body.stop_reason`
  (handles `orchestration_terminated` at line 183) — preview rendering
  slots into the existing switch.
- `_check_ratification` doctor row already exists (A.3); the Console
  health view consumes daemon doctor truth via `read_api.py` — the
  mirror is a rendering addition, not a new probe.

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

- **CA.1 — preview projection + ratify affordance.** Gaps 1+2 together.
  The grounding finding makes the milestone's worry about option (c)
  concrete: the milestone (and Creative) flagged that splitting "preview
  rendering" from "ratify click" decomposes a *single operator
  interaction* along a code seam that doesn't exist in operator
  experience. The operator sees a preview AND acts on it in one surface;
  `graph_intent_id` is already in the preview event, so the button has
  no separate plumbing phase to justify. (c) is rejected for that reason.
  Gaps 1+2 are one coherent slice.
- **CA.2 — ratification ledger view.** Gap 3's historical record. Its own
  phase because it's a *new view* (new route, new template, new nav
  entry per Q-4) consuming different substrate (the A.3 helpers, not the
  chat SSE stream). Distinct surface, distinct phase.
- **CA.3 — health-row mirror + hardening.** Gap 3's doctor mirror + the
  cross-cutting hardening (UAT catalog, non-author dogfood per the
  forge-bridge UX philosophy that every UI phase gets non-developer
  dogfood). Mirrors v1.7 A.3's hardening-phase shape.

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
- **Derived, not reconstructed.** Every Console authority surface derives
  from substrate truth — preview from the SSE event, ledger from the A.3
  helpers' `assent_record` reads, health from daemon doctor truth. No
  parallel client-side authority store.
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
| CA.1 | preview projection + ratify affordance (chat panel) | `preview_emitted` SSE + `POST /api/v1/ratify` | yes |
| CA.2 | ratification ledger view + top-level nav | A.3 `console.helpers` assent reads | yes |
| CA.3 | health-row mirror + hardening + UAT catalog | `_check_ratification` doctor row | yes (non-author) |

## Open questions for discuss-phase (CA.1 first)

These are CA.1-discuss inputs, not framing blockers:

- **CA-Q1: preview render fidelity.** How much of the `preview` dict does
  CA.1 render — full per-step `args_preview` + `would_mutate` badges, or
  a condensed summary with expand-on-demand? *Lean: condensed summary +
  expandable steps, matching the existing chat tool-trace
  default-collapsed `<details>` pattern (panel.html already uses it).*
- **CA-Q2: ratify outcome surfacing.** apply_complete / chain_aborted
  outcomes from `/api/v1/ratify` — rendered inline in the chat panel as a
  new message kind, or as a distinct result card? *Lean: distinct card,
  mirroring the existing `orchestration_termination` sibling-section
  pattern in panel.html (policy-decided events render as siblings, not
  styled messages).*
- **CA-Q3: actor value pre-auth.** `/api/v1/ratify` takes `actor` (free-
  string, SEED-AUTH-V1.5 defers identity). What does the Console send —
  hardcoded "local" (matching CLI default), or a browser-supplied label?
  *Lean: "local", identical to CLI ratify default, so the auth migration
  (v1.9) changes both surfaces at one site, not two divergent ones.*

## Status

**Cycle-1 phase-framing draft.** Q-1 (decomposition → option b, 3 phases)
+ Q-4 (nav → top-level) ruled from the milestone routing. Three CA phases
named; CA.1 is the main slice (preview + ratify, one interaction). The
load-bearing grounding finding — substrate fully wired, Thread A is
projection-only — is what makes (b) over (c) correct and CA.1 small. The
room rules on: the (b) decomposition, the three CA-Q discuss leans, and
whether the projection-only framing holds (or hides a substrate need the
grounding missed).

---

*Drafted 2026-05-29. Grounded against live console reads; no claims from
memory alone. Counts (202 js lines, 5 nav items, 19 __all__) verified by
recount.*
