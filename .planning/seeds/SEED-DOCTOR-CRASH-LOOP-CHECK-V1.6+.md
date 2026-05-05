---
name: SEED-DOCTOR-CRASH-LOOP-CHECK-V1.6+
description: Add a heartbeat check to `fbridge doctor` that detects silent supervisor crash-loops by inspecting the most recent supervisor stdout for repeated Click/Python error blocks
type: forward-looking-idea
planted_during: PR40-PR42 single-runtime consolidation arc (2026-05-04) — extracted from docs/learnings/single-runtime-pr40-42.md surprise #1
trigger_when: v1.6 milestone opens OR `fbridge doctor` gets significant attention OR another silent supervisor crash-loop is hit OR an `fbridge doctor` gap surfaces in operator usage
---

# SEED-DOCTOR-CRASH-LOOP-CHECK-V1.6+: doctor heartbeat for silent supervisor crash-loops

## Idea

Extend `fbridge doctor` to inspect the recent stdout of each supervised daemon (launchd plist `StandardOutPath` on macOS, journald for the systemd unit on Linux) and surface a warning when the tail looks like supervisor-respawn errors rather than normal application logs.

Pattern-match for the symptoms of a wrapper-script invocation hitting a CLI it no longer matches:
- Click error blocks (`Usage: ... [OPTIONS] COMMAND [ARGS]...`, `No such option: ...`, `Try '... --help' for help.`)
- Repeated `Traceback (most recent call last):` blocks at uniform intervals (typical of `KeepAlive` / `Restart=always` respawn loops)
- `ModuleNotFoundError` / `ImportError` blocks (broken venv, wrong interpreter)

Surface as a single `warn` row in `fbridge doctor` output:

```
console     warn         crash-loop-suspected (89 Click error blocks in last 1h of /var/log/forge-bridge/console.log)
                         → check /usr/local/bin/forge-bridge-daemon invocation matches the current CLI
```

## Why This Matters

PR40 verification burned roughly 30 minutes on a silent crash-loop nobody had noticed. The launchd plist's wrapper had been invoking `python -m forge_bridge --transport streamable-http --mcp-port 9997` for an unknown period — a CLI surface that had been refactored to `mcp http --port 9997`. The plist's `KeepAlive={SuccessfulExit:false}` faithfully respawned it on every crash. `/var/log/forge-bridge/console.log` accumulated ~85,000 lines of Click error blocks. The *working* daemon was started by `fbridge up` (a separate path), so `fbridge status` showed everything green and nothing surfaced the rot.

`fbridge doctor` is the tool whose job is "is this box ready to work?" — it already inspects ports, processes, and surface health. It has authority and access to read the supervisor's recent stdout. It just doesn't, and so the silent rot propagated.

This class of bug — "supervisor faithfully respawns a broken invocation" — is *easy* to catch with a tail + regex pass. The cost-to-build is low; the cost-of-NOT-having-it is whatever-the-next-CLI-refactor-costs-its-discoverer.

## Boundaries

In scope (when this seed activates):
- Read the last N lines (e.g., 200 or last 1h) of each supervised daemon's stdout destination (launchd `StandardOutPath`, systemd journal).
- Pattern-match for Click error blocks, repeated tracebacks, repeated import errors at uniform intervals.
- Surface as a `warn` row in `fbridge doctor` output (not a `fail` — the daemon may still be functional via another launch path).
- Honest message that points at the wrapper script + suggests checking the CLI surface.
- Linux variant: `journalctl -u forge-bridge.service --since "1 hour ago"` parsing.

Out of scope:
- Fixing the wrapper itself (this seed only detects, doesn't repair).
- Auto-disabling KeepAlive — outside `fbridge doctor`'s authority.
- Cross-supervisor unification (different platforms have different log shapes; treat them as separate parsers).

## When This Seed Activates

Any of:
1. **v1.6 milestone opens** — natural re-evaluation point as operator-experience hardening.
2. **`fbridge doctor` is being meaningfully edited** — any plan that touches `forge_bridge/cli/runtime_doctor.py` is a low-cost place to fold this in.
3. **Another silent crash-loop is hit** — strong signal the gap is recurring; bump the priority and ship as a hotfix.
4. **A non-author install UAT** (per `SEED-PHASE-20.1-ARTIST-UAT-V1.6+`) surfaces "doctor said all-green but daemon was actually broken" — same class of false-clean as the PR40 incident.

## Breadcrumbs

Code references (current as of 2026-05-04):
- `forge_bridge/cli/runtime_doctor.py` — existing doctor implementation; this is where the check would be added.
- `forge_bridge/cli/doctor.py` — older doctor module (legacy, may be merged with runtime_doctor.py).
- `packaging/launchd/com.cnoellert.forge-bridge.plist` — defines `StandardOutPath` = `/var/log/forge-bridge/console.log`.
- `packaging/launchd/forge-bridge-daemon` — wrapper template (the thing that crash-loops if its invocation drifts from the CLI).
- `packaging/systemd/forge-bridge.service` — Linux equivalent; `StandardOutput=journal`.
- `docs/learnings/single-runtime-pr40-42.md` — original incident report (surprise #1: "The launchd plist had been crash-looping silently for an unknown period").
- `tests/test_packaging.py` — packaging contract tests; the integration test `test_daemon_persistence` would have caught the drift but was excluded from default runs (lesson: marked `@pytest.mark.integration`, never executed in CI).

## Open Questions (for the v1.6+ planning loop)

- Should the heartbeat run *every* `fbridge doctor` invocation (always-on) or only when an explicit `--deep` flag is passed (cheap default + opt-in scan)? Tail of last 200 lines is essentially free, so probably always-on.
- Where should the parser live — colocated with `runtime_doctor.py`, or a separate `forge_bridge.cli/_supervisor_health.py` module that doctor imports? Latter if it grows beyond ~50 lines.
- Should we lift the `@pytest.mark.integration` exclusion on `test_daemon_persistence` while we're here, so packaging-contract drift is caught in CI before it ships? That's a separate fix but related.
- Does `forge-bridge console doctor` need the same check, or does `fbridge doctor` cover it? Both, ideally — one check, two surfaces.

## Why Plant Now

PR40 caught the consequence of this gap (wasted diagnosis time + 85k lines of silent log noise) but the *root* — `fbridge doctor` couldn't see what was happening — wasn't fixed in PR40's scope. PR40/41/42 are about runtime architecture; doctor enhancement is operator-experience. Different milestone, different planning loop. Capturing it now means the lesson doesn't evaporate when context ages out.
