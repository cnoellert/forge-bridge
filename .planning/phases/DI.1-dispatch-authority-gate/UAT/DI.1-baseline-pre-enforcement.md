# DI.1 Baseline — Pre-Enforcement Control

Date: 2026-06-01
Disk HEAD: 2d01d72
Task: T2 baseline, after T1 capture-seam extension and before T3/T5/T6 behavior changes.

## Result

Baseline run not executed.

## Why

The live daemon failed the current-code precondition. `fbridge doctor`
reported:

- `install_provenance`: warn — daemon serving `b88a65e4`; disk advanced to
  `2d01d722`; restart required to load latest.
- `flame_bridge`: fail/warn — Flame hook endpoint unavailable/degraded.

Using the running daemon would contaminate the control with stale code. That
would violate the T2 purpose: a contemporaneous baseline against current main,
after the T1 capture-seam extension.

## Failure Shape Recorded

The baseline itself is blocked by environment/provenance, not by a DI.1 runtime
response shape.

```text
baseline_status: blocked
blocking_surface: daemon_install_provenance
served_commit: b88a65e4
disk_commit: 2d01d72
rerun_condition: restart daemon so install_provenance is green on disk HEAD,
                 then rerun the 11 dogfood reads before T3/T5/T6 enforcement.
```

## Rerun Contract

Before claiming DI.1 acceptance evidence, rerun the dogfood reads only when:

1. `fbridge doctor` reports install provenance green for the current disk HEAD.
2. The daemon is serving code at or after T1 and before enforcement, or the
   baseline explicitly names the exact pre-enforcement commit used.
3. The run records per-read response shape, not just counts.

This artifact preserves the measure-first discipline honestly: no stale daemon
output is accepted as a control.
