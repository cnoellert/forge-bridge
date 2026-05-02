---
name: SEED-PHASE-20.1-ARTIST-UAT-V1.6+
description: Phase 20.1 walks were author-walked per D-19; commit a real-artist UAT at v1.6+ on a truly fresh machine
type: forward-looking-idea
planted_during: Phase 20.1 close-out (2026-05-01) after both author-walks passed PASS-with-deviations
trigger_when: v1.6 milestone is opened OR a non-author Flame artist becomes available to walk the install OR a fresh Rocky 9 VM / fresh-state Mac is provisioned for QA
---

# SEED-PHASE-20.1-ARTIST-UAT-V1.6+: Real-artist fresh-machine UAT for the install path

## Idea

Phase 20.1 closed v1.5 ship-blocker by walking `docs/INSTALL.md` end-to-end on:
- **flame-01** (Linux Rocky 9, projekt-forge dev box) — `20.1-HUMAN-UAT-LINUX.md` PASS-with-deviations
- **portofino** (macOS, dev laptop) — `20.1-HUMAN-UAT-MACOS.md` PASS-with-deviations

Both walks were **author-walked** by cnoellert (Phase 20.1 planning author + bootstrap script
designer). Per D-19 (honesty model), neither walk could earn a clean PASS — only PASS-with-deviations
— because the walker carries author-context that a real Flame artist would not. Both walks logged
explicit Deviation 0 acknowledging this.

At v1.6+ (or sooner if a non-author tester is available), commit a **real-artist UAT** on a
**truly fresh machine** that earns clean PASS:

- Walker: a Flame artist or sysadmin who has NOT seen the bootstrap script source, the planning
  artifacts, or the Phase 20.1 commits. They walk `docs/INSTALL.md` verbatim with zero
  prior-context recovery.
- Linux: a fresh Rocky 9 VM with NO prior conda env, NO prior `forge` Postgres role, NO prior
  `/etc/forge-bridge/`, NO prior `~/.forge-bridge/`, NO prior systemd units, NO prior
  `forge-bridge` checkout. Cold-install code paths exercised: `dnf install postgresql`,
  `--initdb`, `pg_hba.conf` rewrite, role/db creation, alembic from empty schema.
- macOS: a fresh-state Mac with NO prior conda env, NO prior repo, NO prior `forge` role.
  If the test machine is a Flame workstation, exercise the **Autodesk-bundled Postgres on `:7533`
  path** (the actual reality, not the bootstrap's assumed Homebrew default — see
  SEED-PHASE-20.1-POSTGRES-OWNERSHIP-V1.6+ for the architectural restructure that should
  precede this walk).

## Why This Matters

**Author-walks miss the install's real-artist failure modes:**
- The walker mentally autocompletes ambiguous doc instructions, hiding doc gaps that a fresh
  reader would surface.
- The walker recognizes "command not found" errors and silently route-arounds (`brew install foo`,
  `pip install bar`) that an artist would log as a gap.
- The walker pre-knows where Postgres lives, what port, how to invoke `psql`, what Autodesk
  installs by default — collapsing several minutes of "where does this come from?" investigation
  per step.
- The walker tolerates infrastructure quirks (port collisions, conda env activation, Postgres
  superuser auth) that an artist would treat as install failure.
- The walker accepts PARTIAL doctor output as "fine" because they know which warns are degraded-
  tolerant; an artist seeing a `warn` row may interpret it as a broken install.

**Phase 20.1's 5 in-flight gaps prove the friction surface is larger than this walk could capture:**
The author-walks surfaced 1 gap on Linux (stdio-vs-daemon, structural) and 5 gaps on macOS
(Postgres port `:7533`, chown user-vs-group, log-dir ownership, port collision with projekt-forge,
stale site-packages install). Each was patchable in-flight by the author. A real artist would
have stopped at gap #1 and called for help. The artist UAT is the gate that proves the install
is artist-runnable, not author-runnable.

**v1.6+ value:** clean PASS on a fresh machine by a non-author closes the artist-readiness loop
and validates that v1.5's "Legibility" milestone goal — make forge-bridge usable by its first
daily user — actually held when faced with cold reality.

## Boundaries

In scope (when this seed activates):
- A documented walk transcript on a fresh machine with a non-author walker.
- Surface a Linux + macOS variant if both platforms are still supported at v1.6+.
- Capture every prior-context dependence (SSH access, IDE, scripted teardown, etc.) the
  artist needed but the doc didn't specify.
- Update `docs/INSTALL.md` for any gap that surfaces; route structural gaps to fix plans.

Out of scope (other seeds cover):
- The Postgres-ownership architectural fix → `SEED-PHASE-20.1-POSTGRES-OWNERSHIP-V1.6+`
- Chat streaming UX (slow-but-works → snappy) → `SEED-CHAT-STREAMING-V1.4.x`
- Auth on the new `:9997` MCP HTTP surface → `SEED-AUTH-V1.5`
- Default model bump → `SEED-DEFAULT-MODEL-BUMP-V1.4.x`

## When This Seed Activates

Any of:
1. **v1.6 milestone opens** — automatic re-evaluation point; pair with the Postgres-ownership
   seed if both can be addressed in a single milestone.
2. **A non-author tester becomes available** — colleague, sysadmin, contracted Flame artist.
3. **Fresh-VM or fresh-state Mac provisioning** — QA box, CI runner with macOS support, or a
   spare Mac being repurposed.
4. **Significant install-path changes ship** — any plan that materially edits
   `scripts/install-bootstrap.sh`, `packaging/systemd/`, `packaging/launchd/`, or `docs/INSTALL.md`
   should re-trigger this seed.

## Phase 20.1 Author-Walk Artifacts (the baseline this seed re-validates)

- `.planning/phases/20.1-.../20.1-HUMAN-UAT-LINUX.md` — flame-01 first-pass FAIL preserved per
  D-02.1, then re-walk PASS-with-deviations after Plan 20.1-08 lifespan composition fix
  (commit `7fe9779`).
- `.planning/phases/20.1-.../20.1-HUMAN-UAT-MACOS.md` — portofino PASS-with-deviations after
  3 in-flight bootstrap fixes (commits `c73227f`, `c9aac41`, `cb687f8`) + 2 operator actions
  (Postgres setup against Autodesk's `:7533`, stale site-packages rebuild).
- The 5 in-flight gaps logged in those UATs are the **lower bound** on what a real-artist walk
  would surface. Plan accordingly: budget the artist UAT as a multi-day activity with the
  artist allowed to call for help, not a one-shot smoke test.

## Open Questions (for the v1.6+ planning loop)

- Should the artist UAT happen on a `forge-bridge` install ONLY, or also chain a `projekt-forge`
  install on top? The two share `:9996` by default (Phase 20.1 macOS Gap #4) and projekt-forge
  is the canonical consumer — an artist install almost certainly wants both.
- Should `docs/INSTALL.md` ship a "Help! It didn't work" troubleshooting appendix tuned to
  the gaps Phase 20.1 surfaced? Or should `forge-bridge console doctor` cover that role?
- What's the right cadence for re-running the artist UAT — every milestone, every minor, or
  only on install-path-touching plans?

## Why Plant Now

Phase 20.1 closed v1.5's ship blocker. Both author-walks PASS-with-deviations. The honest
artifact at this point is "this works for me" — not "this works for any artist." Capturing
the real-artist UAT as a deferred commitment keeps the Legibility milestone goal honest:
v1.5 made the install legible to the author; v1.6+ proves it legible to the artist.
