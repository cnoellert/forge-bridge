---
milestone: v1.8
thread: A
phase: CA.1
phase_name: preview projection + ratify affordance + JSON preview-branch fix
status: discuss-questions-converged
drafted: 2026-05-30
type: discuss-questions
derives_from: .planning/phases/CA-thread-a-console-authority/CA-THREAD-A-FRAMING.md (cycle-2, a4bfa1a)
grounding: this-session live reads — handlers.py JSON returns (preview_emitted :1954, chain_complete :1977), forge-chat.js (messages-replace :169, orchestration_terminated :183), panel.html (orchestration-termination sibling :59), _chat_compile.py (conditional graph_intent_id :161-171)
---

# CA.1 — Discuss questions

> Compact per [[feedback-cadence-artifacts-shrink-to-load-bearing]].
> Derives from the cycle-2 framing. CA-Q2 (outcome card) is already a
> binding constraint and is **not** re-litigated here. Q1 below is the
> framing's grounding-obligation #1 — it must resolve first because it
> sets CA.1's true scope (bug-close vs new-taxon ordering). The rest pose
> CA.1's open UI decisions with leans.

## Q1 — What does `/api/v1/chat` actually return to the Console, per regime? — RESOLVED (DT trace + Orch scope ruling)

**Verdict: neither H1 nor H2 cleanly — a third shape. CA.1 is titled
"fix." Broad regime-agnostic guard is in scope.**

### The decisive fact (DT trace)

`grep -c '"messages"'` in `handlers.py` = **exactly one** response-bearing
return: line **787**, inside `_execute_forced_tool` (the other hits are
the docstring `1307/1313` and the request-side read `1367`).

### Full non-SSE regime tree (dispatch order)

| # | Regime | Return | `messages`? | JS:169 effect |
|---|--------|--------|:---:|---|
| 1 | list/delete macro | 1522/1548 | ❌ | blanks |
| 2 | chain too long | 1587 | ❌ | blanks |
| 3 | multi-step chain (`->`, >1) | 830/867 | ❌ chain | blanks |
| 4 | single-tool forced exec (PR20) | 787 | ✅ out_messages | **renders** |
| 5 | `apply <id>` grammar | 1834 | ❌ apply_complete | blanks |
| 6 | compile error | 1924 | ❌ error | error banner (ok) |
| 7 | chain_aborted (compiled) | 1941 | ❌ | blanks |
| 8 | compiled_mutating_preview | 1954 | ❌ preview | blanks |
| 9 | compiled_non_mutating | 1977 | ❌ chain | blanks |

**8 of 9 non-SSE regimes blank the Console transcript today; only
forced-single-tool (#4) survives.** The D-03 contract `forge-chat.js` was
written against (`{messages, stop_reason: "end_turn"}`, docstring `1313`)
is satisfied by **zero** current JSON return paths — the only path that
would emit `end_turn` + full history is the **SSE** path, which the Console
never requests (no `Accept: text/event-stream`, confirmed). The handler
evolved through PR20/PR30/compile/SSE migrations; each new regime returned
its own envelope; the JSON client stayed alive **only** because #4 happened
to retain `out_messages`. That's the one regime the Console was ever
dogfooded against (a plain `list projects` narrows-to-1 and force-executes)
— which is why nobody saw the blank. **Pre-existing latent defect,
inherited, not introduced by CA.1.**

### Why neither hypothesis fit

- **H1** (compiled blanks every turn) — too broad: it's not just the
  compiled regime, and #4 genuinely works.
- **H2** (separate path echoes messages, compile unexercised) —
  directionally right but mis-attributed the cause: there's exactly one
  `messages`-echoing path (#4), not a "non-compiled path."

### Scope ruling (Orch — the decision DT handed up)

The grounding distinction DT's table doesn't separate: **de-blank ≠
render.** The JS consumes only `renderableMessages()` (filters
`this.messages`) + the `termination` sibling. There is **no consumer** for
`chain` / `preview` / `apply_complete` / macro-list keys. So the
regime-agnostic guard (gate `this.messages =` on `body.messages` present;
dispatch `stop_reason` first):

- **#8 preview:** guard de-blanks **+ CA.1 builds the renderer** → fully
  fixed.
- **#1/2/3/5/7/9:** guard de-blanks (transcript preserved, not wiped) but
  payloads **still don't render** — no consumer exists.

**Ruling: BROAD guard, in scope. Rendering the other regimes is out.**

- **In scope (CA.1):** the regime-agnostic destructive-blanking fix. One
  natural change, and a **prerequisite for CA.1's own preview to survive**
  (preview_emitted wipes the screen before `body.preview` is read).
  Narrow — special-casing `preview_emitted` — is *more code to do less*,
  leaves a known-blanking bug for `->`/multi-step/`apply`, and is the
  artificial seam. Rejected.
- **Out of scope:** *rendering* the six de-blanked regimes' payloads
  (chain results, apply_complete cards, macro lists). CA.1 still renders
  exactly one new thing (preview + ratify). This rendering work is the
  post-A.1 envelope debt — routes to
  `SEED-POST-A1-ENVELOPE-CONTRACT-RECONCILIATION-V1.9+`, not CA.1.

**CA.1 = destructive-blanking fix (regime-agnostic) + preview/ratify
render.** The blanking fix is load-bearing — without it the preview is
invisible. Title: **"fix."** The "one coherent slice" boundary holds:
de-blank is the minimal correct contract repair the preview already
requires; render-the-rest stays seeded and separate.

## Q2 — Ratify button: states + placement

The button POSTs `{graph_intent_id, actor}` to `/api/v1/ratify` and the
outcome renders as a distinct authority card (CA-Q2 constraint). Open: the
button's own states and where it sits.

**Absent-id state — SETTLED (Creative ruling, framing-grade):**

> When `graph_intent_id` is absent, the ratify control remains **visible
> but disabled**, accompanied by explanatory text describing why
> ratification is not applicable. The state is **informational, not
> error-oriented.**

This is the operator-experience face of the constitutional rule. It draws
a **taxonomy line** CA.1 must render on two distinct surfaces:

- **Non-ratifiable preview** (`graph_intent_id` absent — conditional per
  `_chat_compile.py:161-171`): visible-but-disabled control + informational
  text. *Not* an error. Teaches: some previews carry authority weight,
  some don't, the system knows which, nothing is broken.
- **Ratification failure** (`AssentRecordNotFound` / apply abort on POST):
  the actual error/abort surface — distinct from the informational state
  above. Conflating the two would teach the operator that a non-mutating
  preview is "broken," which inverts the mental model the authority chain
  exists to build.

Never POST a missing id.

*Remaining leans (confirm):*
- **In-flight:** disable + spinner during the POST (reuse the existing
  `inflight` pattern in `forge-chat.js`).
- **Placement:** the ratify control belongs **on the preview card** (it
  acts on that intent); the outcome card renders as a **sibling below**,
  matching the `orchestration-termination` sibling shape (`panel.html:59`)
  the CA-Q2 constraint already points at.

## Q3 — Render fidelity (CA-Q1) — CONFIRMED (DT)

*Confirmed:* condensed summary + expandable per-step `<details>`, matching
the existing tool-trace collapsed pattern.
`args_preview` is `extract_explicit_params` → today only
`{project_id}` / `{project_name}` / `{}`, so per-step args are usually
empty; full-fidelity rendering is low-value. Open detail for discuss:
which summary fields lead the collapsed view — `total_steps`,
`mutating_steps`, `requires_ratification`? *Lean: all three as a one-line
badge row; the mutating count is the operator's decision-relevant number.*

## Q4 — Actor value (CA-Q3) — CONFIRMED (DT)

*Confirmed:* send `actor="local"`, identical to the CLI ratify
default (endpoint defaults `"local"` `handlers.py:1242`; CLI defaults
`"local"` `cli/main.py:300`). No browser-supplied label pre-auth.
Forward-pointer only (NOT CA.1 scope): SEED-AUTH-V1.5 is a milestone-wide
three-convention unification (CLI ratify, Console ratify, staged-ops
`_resolve_actor` D-06) — overlaps
SEED-POST-A1-ENVELOPE-CONTRACT-RECONCILIATION. CA.1 changes nothing here;
it just must not invent a *fourth* actor convention.

## Parked (not CA.1)

- **CA.3 grounding obligation:** does `read_api.py`'s health mirror re-run
  the `runtime_doctor` checklist or maintain its own? Determines whether
  the `_check_ratification` mirror is rendering-only. Carried to CA.3, not
  resolved here.

## Status

**Discuss-questions — CONVERGED. Ready for CA.1-PLAN.**

- **Q1 (blocker) RESOLVED** — DT trace: 8 of 9 non-SSE regimes blank the
  transcript; only forced-exec (#4) carries `messages`. Third shape, not
  H1/H2. Orch scope ruling: **broad regime-agnostic de-blank guard in
  scope** (prerequisite for preview survival); rendering the other six
  regimes' payloads out of scope → envelope-contract seed. **CA.1 titled
  "fix."**
- **Q2 absent-id** — settled (Creative framing-grade: visible-but-disabled,
  informational-not-error, non-ratifiable/failure taxonomy line).
- **Q2 in-flight + placement** — leans stand (disable+spinner; control on
  preview card, outcome card as sibling). Plan-grade detail.
- **Q3 render fidelity** — confirmed (DT: condensed + expandable).
- **Q4 actor** — confirmed (DT: `"local"`; v1.9 three-site forward-pointer).

CA.1 scope, locked: **regime-agnostic destructive-blanking guard +
preview projection + ratify affordance (with absent-id informational
state).** Substrate byte-equivalent (pure `forge-chat.js` + template; no
Python). Routes to CA.1-PLAN.
