---
milestone: v1.8
thread: A
phase: CA.1
phase_name: de-blank guard + preview projection + ratify affordance
status: plan-draft-cycle-1
drafted: 2026-05-30
type: phase-plan
derives_from: .planning/phases/CA-thread-a-console-authority/CA.1-DISCUSS-QUESTIONS.md (converged, 17dbcfe)
grounding: this-session live reads — forge-chat.js (send() success branch 166-190; messages-replace :169; termination check :183), templates/chat/panel.html (113 lines; transcript card 26-94; orchestration-termination sibling 59-93; input form 96-111), _chat_compile.py (build_preview_from_steps 89-122; preview dict shape), handlers.py (ratify_endpoint :1208; preview_emitted JSON return :1954), shell.html (5-item nav, Ratifications is CA.2), forge-console.css (orchestration-termination__* styles present)
artifact_role: load-bearing — CA.1 execution derives from this
---

# CA.1 — Phase plan

> Compact per [[feedback-cadence-artifacts-shrink-to-load-bearing]].
> Derives from converged discuss (`17dbcfe`). Scope is **locked** there;
> this plan turns it into ordered, file-grounded task blocks. CA.1 is
> titled **"fix"** — the de-blank guard (L1) is load-bearing, not
> additive: without it the preview (L2) is invisible.
>
> **Substrate byte-equivalent.** Pure `forge-chat.js` + `panel.html`
> (+ `forge-console.css` for card styling). **No Python.**
> `forge_bridge.__all__` stays 19; version stays 1.4.1.

## Scope recap (from converged discuss)

CA.1 = **regime-agnostic destructive-blanking guard + preview projection
+ ratify affordance (with absent-id informational state).** The guard
un-blanks all 8 broken non-SSE regimes, but CA.1 only *renders* one new
thing (the preview + its ratify outcome). Rendering the other six
de-blanked regimes' payloads is **out of scope** →
`SEED-POST-A1-ENVELOPE-CONTRACT-RECONCILIATION-V1.9+`.

Grounded constants this plan depends on:
- Preview dict (`build_preview_from_steps`, `_chat_compile.py:106-122`):
  `{kind: "graph-intent-preview", graph_intent_id?, steps:
  [{step_text, tool_name, args_preview, would_mutate}], summary:
  {total_steps, mutating_steps, requires_ratification}}`. **`graph_intent_id`
  is conditional** — present only when `session_factory is not None`.
- Preview SSE/JSON `stop_reason` value: `"preview_emitted"`
  (`handlers.py:1958`).
- Ratify endpoint: `POST /api/v1/ratify` body `{graph_intent_id, actor}`,
  returns apply/abort outcome (`handlers.py:1208`); the JSON 400 path
  stamps `stop_reason: "chain_aborted"` + `graph_intent_id`.

---

## L1 — Regime-agnostic de-blank guard (`forge-chat.js`)

**File:** `forge_bridge/console/static/forge-chat.js`, `send()` success
branch (currently lines 166-190).

**Change:** Today line 169 runs
`this.messages = (body.messages || []).map(...)` **unconditionally** on
every 2xx, *before* the `stop_reason` inspection at 183 — so any response
without a `messages` key (8 of 9 regimes) wipes the transcript. Restructure
the success branch to:

1. **Dispatch on `body.stop_reason` first.**
2. **Only replace `this.messages` when `body.messages` is genuinely
   present** — guard with `Array.isArray(body.messages)`. When absent,
   **preserve** the existing transcript (the user's turn already pushed in
   `send()` at line 124 stays visible; the assistant simply has no history
   echo for this regime).
3. Keep the existing `termination` projection (183-189) as one branch of
   the `stop_reason` dispatch.

**Shape (reference, not literal — preserve battle-tested topology per
[[feedback-brief-examples-as-behavioral-reference-shapes]]):**
```
} else {                                  // 2xx success
  if (Array.isArray(body.messages)) {     // regime #4 only, today
    this.messages = body.messages.map(/* unchanged id-stamp */);
  }                                       // else: keep transcript intact
  this.preview = null;                    // reset per-turn (L2)
  this.ratifyOutcome = null;              // reset per-turn (L3/L4)
  if (body.stop_reason === "preview_emitted") {
    this.preview = body.preview || null;  // L2
  } else if (body.stop_reason === "orchestration_terminated"
             && body.termination && typeof body.termination === "object") {
    this.termination = body.termination;  // unchanged
  } else {
    this.termination = null;
  }
}
```

**Rationale:** This is the minimal correct contract repair. The guard is
regime-agnostic by nature — special-casing `preview_emitted` would be more
code to do less and leave `->`/multi-step/`apply` still blanking (the
artificial seam rejected in discuss). De-blank ≠ render: this un-blanks
all 8, but only `preview_emitted` gets a consumer here (L2).

**Out of scope (do NOT add):** renderers/consumers for `chain`,
`apply_complete` (non-ratify path), or macro-list payloads. Those stay
seeded.

---

## L2 — Preview projection (`forge-chat.js` state + `panel.html` render)

**Files:** `forge-chat.js` (new Alpine state) + `templates/chat/panel.html`
(new sibling section).

**State (`forge-chat.js`):** add `preview: null` to the `chatPanel()`
returned object (alongside `termination` at line 76). Reset to `null` at
the top of `send()` (next to the `this.termination = null` reset at line
131) and in the L1 success branch. Populate from `body.preview` when
`stop_reason === "preview_emitted"` (L1).

**Render (`panel.html`):** add a `<section class="graph-intent-preview">`
**sibling of the message list**, mirroring the `orchestration-termination`
section (59-93) — same placement (inside the `.chat-transcript` card,
after the termination section), same `x-show` / `x-cloak` / `role="region"`
discipline. Structure:
- **Header:** "Graph-Intent Preview" + sub "compiled by the assistant —
  read before you ratify".
- **Summary badge row (CA-Q1 condensed, confirmed):** `total_steps`,
  `mutating_steps` (the decision-relevant number — visually emphasized),
  `requires_ratification`. All via `x-text` bindings on
  `preview.summary.*`.
- **Steps (expandable per-step `<details>`, default-collapsed):**
  `x-for` over `preview.steps`; each `<summary>` shows `tool_name` + a
  `would_mutate` badge; the open body shows `step_text` and (when present)
  `args_preview`. `args_preview` is near-always empty
  (`extract_explicit_params` → `{project_id}`/`{project_name}`/`{}`), so
  render it only `x-show`-gated on having keys.

**Binding discipline:** `step_text` / `tool_name` / summary fields via
**`x-text`** (verbatim projection — these are compiled artifacts, not
operator prose to markdown-render). Mirrors the termination section's
x-text-not-x-html rule.

**Rationale:** Read-only projection of substrate the daemon already emits
(framing constraint: *derived, not reconstructed*). The LLM authored the
compile; the operator reads it.

---

## L3 — Ratify affordance (`forge-chat.js` action + `panel.html` button)

**Files:** `forge-chat.js` (new `ratify()` method + state) +
`panel.html` (button on the preview card).

**State (`forge-chat.js`):** add `ratifyInflight: false` and
`ratifyOutcome: null`. Reset `ratifyOutcome` per-turn (L1).

**Action (`forge-chat.js`):** add `async ratify()`:
- Guard: if `!this.preview || !this.preview.graph_intent_id` → **return
  immediately, never POST** (the button is disabled in this state per L3
  render, but guard defensively too).
- Set `ratifyInflight = true`; `POST /api/v1/ratify` with
  `{graph_intent_id: this.preview.graph_intent_id, actor: "local"}`
  (CA-Q3 confirmed: `"local"`, matches CLI default).
- On response: populate `this.ratifyOutcome` from the body (L4 renders it);
  reuse the existing status-code error mapping (429/504/422/!ok → the same
  `this.error` banner copy already in `send()`).
- `finally { this.ratifyInflight = false; }`.

**Button (`panel.html`):** inside the L2 preview card, shown only when
`preview.summary.requires_ratification`:
- **Enabled** when `preview.graph_intent_id` is present → label "Ratify &
  Apply", `@click="ratify()"`, `:disabled="ratifyInflight"`, spinner via
  the existing `spinner-amber` pattern (panel.html:108).
- **Absent-id state (Creative framing-grade ruling):** when
  `preview.graph_intent_id` is **absent**, render the button
  **visible-but-disabled** + an informational line ("This preview isn't
  ratifiable — no persisted intent."). **Informational, not error** — no
  error-card styling, no red. Teaches the taxonomy: some previews carry
  authority weight, some don't, the system knows which, nothing is broken.

**Rationale:** The ratify click is the operator's authority act —
constitutionally **not** chat-suggested (LLM never owns assent). Button
exists because the operator chose to look.

---

## L4 — Ratify outcome card (`panel.html` sibling)

**File:** `templates/chat/panel.html`.

**Change:** add a **distinct sibling `<section class="ratify-outcome">`**
(CA-Q2 **binding constraint** — outcome is authority-decided, never a chat
message). Mirror the `orchestration-termination` sibling shape (59-93):
`x-show="ratifyOutcome"`, `x-cloak`, `role="region"`. Render the two
terminal regimes from the ratify response:
- **`apply_complete`** → success header + the applied chain summary
  (verbatim `x-text` over the response's chain/result fields).
- **`chain_aborted`** → abort header + reason (the 400 path stamps
  `stop_reason: "chain_aborted"` + `graph_intent_id`).

**Binding discipline:** `x-text` only (verbatim; never `renderContent`).

**Rationale:** Rendering the outcome as a chat turn would blur the
authority/conversation boundary the whole thread protects. Distinct card,
sibling to messages — the same architectural rhyme as termination.

---

## L5 — Card styling (`forge-console.css`)

**File:** `forge_bridge/console/static/forge-console.css`.

**Change:** add `.graph-intent-preview`, `.ratify-outcome`, and the
absent-id informational-text styles, following the existing
`.orchestration-termination__*` token usage (LOGIK-PROJEKT amber-on-dark
palette). Reuse existing card / badge / `<details>` patterns; **no new
palette tokens**. The `would_mutate` / `mutating_steps` emphasis uses the
existing amber accent; the absent-id informational note uses a muted
(non-error) foreground — explicitly NOT the `.error-card` red.

**Rationale:** Visual parity with the established Console surfaces; the
informational-vs-error color split is the CSS face of the L3 taxonomy
ruling.

---

## L6 — UAT runbook (artist-first dogfood)

**File:** `.planning/phases/CA-thread-a-console-authority/UAT-CA1.md`
(new), per [[project-forge-bridge-ux-philosophy]] (every UI phase gets
non-developer dogfood).

**Scenarios:**
1. **Preview renders (the headline fix).** Type a mutating `commit` intent
   in Console chat → preview card appears with steps + mutating-count
   badge. **Screen does NOT blank.** (Pre-CA.1: blanks.)
2. **Ratify happy path.** Click "Ratify & Apply" → spinner → outcome card
   (`apply_complete`).
3. **Non-mutating regression.** Type `list projects` (regime #4) → still
   renders normally (no regression on the one path that worked).
4. **Multi-step de-blank.** Type a `->` multi-step query → transcript no
   longer blanks (de-blank guard; payload may not render — that's seeded,
   not a CA.1 bug).
5. **Absent-id informational state.** (If reproducible without a DB) a
   preview lacking `graph_intent_id` shows the disabled button + the
   informational note, **not** an error.

---

## Implementation step sequence

1. **L1** — de-blank guard (the load-bearing fix; everything else renders
   on top of a transcript that survives).
2. **L2** — preview state + card (now visible because L1 stopped the wipe).
3. **L3** — ratify button + action (incl. absent-id disabled state).
4. **L4** — outcome card.
5. **L5** — CSS for L2/L3/L4.
6. **L6** — UAT runbook + non-author dogfood pass.

Atomic commits per L-block (L1 alone is a shippable bugfix; L2-L5 build
the projection; L6 is the dogfood gate).

---

## Acceptance gate (phase-level)

- [ ] L1: no 2xx response without `body.messages` blanks the transcript
      (verified across preview / chain / apply / macro regimes).
- [ ] L2: `preview_emitted` renders the condensed summary + expandable
      steps; binding is `x-text` (no markdown pass).
- [ ] L3: ratify button enabled iff `graph_intent_id` present + mutating;
      absent-id = disabled + informational (not error); never POSTs a
      missing id; sends `actor: "local"`.
- [ ] L4: outcome renders as a distinct sibling card (not a chat message);
      both `apply_complete` and `chain_aborted` covered; `x-text` only.
- [ ] Substrate byte-equivalent: `git diff` touches only `forge-chat.js`,
      `panel.html`, `forge-console.css`. No `.py`. `__all__` == 19.
      `pyproject.toml` version == 1.4.1.
- [ ] L6: non-author dogfood passes scenarios 1-4 (5 if reproducible).

---

## What execution-stage needs to confirm at draft time

Grounding obligations carried from discuss + this plan's assumptions —
**read before asserting in code:**

1. **Exact ratify-success body shape.** L4 renders `apply_complete` /
   `chain_aborted`. This plan grounded the **400/abort** stamp
   (`handlers.py:1287` stamps `stop_reason` + `graph_intent_id`) but the
   plan should not assume the 200/apply body field names — execution must
   read the `run_apply_branch` success return + the `ratify_endpoint` 200
   path (`handlers.py:1208+`) and bind L4 to the **actual** keys. (Same
   discipline that caught the cycle-1 SSE/JSON conflation.)
2. **Absent-id reproducibility.** L3's absent-id branch is correct
   defensively, but L6 scenario 5 may be unreproducible on a stock DB
   (production always has `session_factory`). Confirm whether to keep it
   as an automated assertion or a defensive-only branch with a noted
   manual gap.
3. **`forge-console.css` token names.** L5 assumes amber-accent + muted
   foreground tokens exist; execution reads the `:root` custom properties
   before reusing them (no new tokens).

---

## Status

**Plan draft cycle-1.** Six L-blocks over the locked discuss scope; L1 is
the load-bearing de-blank fix, L2-L4 the projection, L5 styling, L6 the
dogfood gate. Substrate byte-equivalent (3 front-end files, no Python).
Three draft-time grounding obligations handed to execution. Room reviews
the L-decomposition + the L1 guard shape + whether L4's outcome-body
binding is safe to leave to execution-stage grounding. Routes to
CA.1 execution on ratification.

---

*Drafted 2026-05-30. Grounded against live console reads; panel.html
confirmed clean (113 lines, no stray content — an earlier memory-claim of
trailing junk was falsified by direct read). Counts (panel.html 113 lines,
5 nav items, 19 __all__) verified by recount.*
