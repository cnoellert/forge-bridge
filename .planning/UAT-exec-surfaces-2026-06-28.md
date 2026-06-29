# UAT / dogfood checklist — exec surfaces + seam (2026-06-28)

Hands-on validation for everything shipped this session that unit tests can't reach
(live Flame, live Ollama, live daemon). Untracked working doc — edit/check off/delete freely.

## Shared prerequisites
- [ ] conda env `forge` active; editable install anchored to THIS checkout
      (`pip show forge-bridge | grep -E 'Location|Editable'` → points here).
- [ ] Postgres reachable (stage/ratify persistence).
- [ ] A Flame project open with a sequence on the desktop (host-mutation tests).
- [ ] `FORGE_PLUGINS` includes `flame,traffik`; projekt-forge pinned so the host-apply
      tools (`forge_apply_segment_delta`, `forge_apply_segment_temporal_delta`) are callable.
- [ ] Local Ollama up with `qwen2.5-coder:14b` (NL-composer test only).

**Gotchas**
- The **daemon serves the code from whatever branch was checked out when it started.**
  After ANY `git checkout`, run `fbridge down && fbridge up` before testing.
- `#124` and `#126` are **unmerged branches** — check them out to test, then return to `main`.
  They're separate branches; test one, then the other.
- Suggested order: **C + D first** (on `main`, no checkout) → **#124** → **#126**.

---

## C. Host-mutation slices on `main` (merged in #123) — highest value

### C1. Trim verb — the `record_in_frame` probe (slice-2 make-or-break)
- [ ] `fbridge exec`  → at the REPL: `/trim <sequence> #<n> <new-in-point-frame>`
- [ ] Preview renders a domain-language head-trim description.
- [ ] `[y]` to apply → confirm in Flame: the segment's in-point moved; start frame/duration shifted together.
- [ ] Revert: `/trim <sequence> #<n> <original-frame>` → `[y]` → timeline restored.
- **FAIL signal to report:** preview/apply fails closed with `temporal_before_mismatch`.
  That means the bridge probe's `record_in_frame` ≠ the live value the apply tool re-probes —
  the one thing units can't exercise. Capture the exact message if it happens.

### C2. Stage-for-ratify (slice-4) — "preview now, ratify later"
- [ ] `fbridge exec` → `/rename <sequence> #<n> <newname>`
- [ ] At the `[y]apply / [s]stage / [n]cancel` prompt, choose **`s`**.
- [ ] Confirm it prints `fbridge ratify <graph_intent_id>` and says **nothing applied yet**.
- [ ] In a terminal (daemon up): `fbridge ratify <graph_intent_id>` → expect `apply_complete`
      and the rename enacted in Flame.
- [ ] Revert (rename back). 
- **Doctrine check:** `[s]` must NOT mutate Flame; only `fbridge ratify` does.

---

## D. Artist-description seam display (merged #125/#127) — quick, may show fallbacks

> Note: most peers haven't authored `summary`/`label` yet, so expect **derived fallbacks**
> (humanized tool names). That's success — it proves the path resolves. Real peer prose
> appears only once a peer populates `CapabilityDeclaration.summary`/`label`.

- [ ] `fbridge discover tools` (daemon up) → tool list renders with a Description column.
- [ ] `fbridge discover tool <name>` → detail shows label / origin / namespace / artist_description.
- [ ] Daemon DOWN (`fbridge down`): `fbridge discover tools` → **exit code 2**, clean
      "unreachable" message (check `echo $?`). Bring it back with `fbridge up`.
- [ ] `fbridge discover tools --json` → pure JSON; records carry `artist_description` + `artist_label`.
- [ ] Console: open `http://localhost:9996/ui/tools` → each tool shows a short label line +
      a description line (distinct from the machine tool id).

---

## #124 — Web renderer (Actions view) — UI dogfood

```
git checkout feat/exec-web-renderer
fbridge down && fbridge up
```
- [ ] Open `http://localhost:9996/ui/actions` → verb cards (Rename, Trim) list.
- [ ] Rename → enter the open sequence's name → **Load segments** → live picker populates from the timeline.
- [ ] Pick a segment, enter a new name → **Preview** → domain-language preview renders
      ("will rename 1 segment: old → new, reversible").
- [ ] **Stage for ratification** → a real `graph_intent_id` returns; copy says nothing applied yet.
- [ ] Ratify via the **Chat view's Ratify & Apply** button (CA.1) OR `fbridge ratify <id>` in a terminal
      → `apply_complete` + rename in Flame.
- [ ] Revert.
- [ ] **Degraded path:** with no sequence open (or Flame unreachable), Load segments → a clear
      "couldn't reach the live timeline" message renders — **never a blank page or traceback** (de-blank guard).
- **Doctrine check:** there is **no Apply button** in the Actions view — it stages only; apply
  happens through the ratify affordance. (If you find a mutate-on-click path here, that's a bug.)
- [ ] `git checkout main && fbridge down && fbridge up` when done.

---

## #126 — NL-composer — extraction-quality dogfood

```
git checkout feat/nl-composer
# (REPL runs in-process; daemon only needed for the ratify step)
```
- [ ] `fbridge exec` → type **free text** (no leading `/`): e.g.
      `rename the third shot on <sequence> to BG_010`
- [ ] Confirm the `understood →` echo shows the extraction: verb=rename, sequence, segment #3, new name=BG_010.
- [ ] Confirm it then runs the **same** preview → `[y/s/n]` gate (NL did NOT auto-apply).
- [ ] `[n]` to cancel → nothing applied.

**Extraction quality — try several phrasings, note hits/misses:**
- [ ] verb pick: "rename …" vs "trim …" → correct verb chosen.
- [ ] "the third shot" / "shot 3" → segment index 3.
- [ ] spoken/sloppy sequence name → resolves to the real sequence string.
- [ ] number path: `trim segment 5 on <sequence> to frame 1015` → trim, seg 5, frame 1015.
- [ ] gibberish / unmappable → clean "couldn't map that to a verb — try /rename or /trim, or rephrase";
      no traceback, REPL survives.

**What you're judging:** the *plumbing* is unit-proven; you're rating *accuracy* (does qwen2.5-coder:14b
reliably pick the verb, resolve "third shot"→index, map a spoken name→sequence). The system prompt is a
first cut — note phrasings that mis-extract; the doctrine rail holds regardless (every miss lands in the
visible `understood →` + preview where you catch it before `[y]`).
- [ ] `git checkout main && fbridge down && fbridge up` when done.

---

## If something fails
- Capture the exact message + which step. For host-mutation fail-closed (`temporal_before_mismatch`,
  `PLAN_STATE_DRIFT`, `unauthorized_mutation`) note the sequence + segment used.
- `ModuleNotFoundError: forge_bridge` after a checkout switch → editable anchor drift; re-run
  `pip install -e ".[dev,llm]"` from the checkout you're keeping (see docs/TROUBLESHOOTING.md).
