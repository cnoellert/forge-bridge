---
milestone: v1.8
thread: A
phase: CA.1
type: uat-runbook
status: ready-to-run
drafted: 2026-05-30
derives_from: .planning/phases/CA-thread-a-console-authority/CA.1-PLAN.md (ratified, db331fc)
implements: L6 (the optional sidecar code deferred per the 3-file execution constraint)
covers_commits: 1598917 (L1) · 1692a74 (L2) · 4399486 (L3) · 92c0106 (L4) · 523356f (L5)
---

# UAT-CA1 — Console preview + ratify (artist-first dogfood)

> **Why this runbook is the gate.** CA.1's load-bearing fix (L1 de-blank
> guard) ships with **zero automated JS coverage by decision** (no JS
> harness exists; introducing one is out of a 3-file front-end phase —
> B-3 ruling). This manual sweep is therefore the **sole regression
> guard** for the 8-regime de-blank. It must be run completely, not
> sampled. Run it as a **non-developer / non-author** where possible, per
> [[project-forge-bridge-ux-philosophy]].

## Setup

```
fbridge up
```
Open `http://localhost:9996/ui/chat` in a browser. (A `favicon.ico` 404 in
the console is expected and unrelated.)

**Precondition for the authority scenarios (2, 5):** a reachable Postgres
(`session_factory` present) — otherwise a mutating compile cannot persist
an `AssentRecord` and `graph_intent_id` will be absent (that is itself
scenario 5).

---

## Scenario 1 — Preview renders, screen does NOT blank  *(the headline fix)*

**Do:** type a mutating intent, e.g. `rename shot 0010 to 0020 then commit`
(any phrasing that compiles to a graph containing `commit`). Send.

**Expect:**
- [ ] The **Graph-Intent Preview** card appears (amber authority card).
- [ ] It shows a summary row: `total_steps`, `mutating_steps` (emphasized),
      `requires_ratification`.
- [ ] Each step is an expandable `<details>` — `tool_name` + a
      `would mutate` / `read only` badge; expanding shows `step_text`.
- [ ] **The transcript does NOT blank.** Your submitted turn stays visible.
      *(Pre-CA.1 this wiped the whole screen.)*

## Scenario 2 — Ratify happy path  *(the authority click)*

**Do:** on the preview card from scenario 1, click **Ratify & Apply**.

**Expect:**
- [ ] Button shows a spinner while in-flight, then settles.
- [ ] A distinct **Apply Complete** card appears *below* the preview (its
      own card, **not** a chat message).
- [ ] It shows `graph_intent_id`, `stop_reason` (= `apply_complete`),
      `chat_regime`, `chain_status`.

## Scenario 3 — Non-mutating regression  *(don't break what worked)*

**Do:** type `list projects`. Send.

**Expect:**
- [ ] Normal assistant/tool response renders as before.
- [ ] No preview card, no ratify button, no blanking. *(This is regime #4,
      the one path that always worked — confirm CA.1 didn't regress it.)*

## Scenario 4 — De-blank sweep (ALL regimes)  *(the load-bearing guard)*

For **each** input below: send it, and confirm **the transcript is
preserved — your submitted turn stays visible, the screen does not wipe.**
(Payloads need not render richly; the **no-blank** invariant is the bar.
Rich rendering of these is explicitly seeded for v1.9+, not CA.1.)

- [ ] **#3 multi-step chain:** `get segments on 30sec 21 -> count them`
- [ ] **#7 compiled chain_aborted:** a mutating intent that aborts on apply
      (e.g. target a non-existent shot, then `commit`)
- [ ] **#9 compiled non-mutating:** a `->` chain with no `commit`
- [ ] **#5 apply grammar:** `apply <a real 12-hex graph_intent_id>`
- [ ] **#1 macro:** list macros (or your macro-list trigger)
- [ ] **#2 chain too long:** an over-long `->` chain (exceeds the step cap)
- [ ] **#6 compile error:** deliberately uncompilable gibberish → an
      **error banner** appears (this one is *expected* to surface via the
      error path, not the transcript — still must not blank the history)

*If any of these blanks the transcript, L1 is incomplete — STOP and report.*

## Scenario 5 — Absent-id informational state  *(taxonomy, not error)*

**Do:** produce a mutating preview where `graph_intent_id` is absent. *(Most
reliably reproduced with no DB / `session_factory` unset — see precondition.
May be unreproducible on a stock production DB; mark N/A if so.)*

**Expect:**
- [ ] The Ratify button is **visible but disabled**.
- [ ] An informational note shows: *"This preview isn't ratifiable — no
      persisted intent."*
- [ ] This reads as **informational, not an error** — no red `.error-card`
      styling. *(Teaches: some previews carry authority weight, some don't,
      the system knows which, nothing is broken.)*

---

## Result

| Scenario | Pass / Fail / N-A | Notes |
|---|---|---|
| 1 — preview renders, no blank | | |
| 2 — ratify happy path | | |
| 3 — non-mutating regression | | |
| 4 — de-blank sweep (all 7 inputs) | | |
| 5 — absent-id informational | | |

**Gate:** scenarios 1, 3, 4 are **mandatory pass** (1 = the feature; 3 =
no regression; 4 = the load-bearing guard, the sole guard). 2 is mandatory
if a DB is present. 5 is best-effort (mark N/A if not reproducible).

**On full pass →** CA.1 closes. **On any scenario-4 failure →** L1 is
incomplete; reopen before close.
