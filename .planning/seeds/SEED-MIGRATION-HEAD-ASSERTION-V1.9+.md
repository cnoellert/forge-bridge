---
name: migration-head-assertion
description: "Fast-follow hardening from projekt-forge findings 2026-05-31 #2. Add a startup assertion that the installed package's expected Alembic migration head matches the live DB's alembic_version, failing fast on skew. The v1.4.1-tag-vs-0009-DB mismatch (consumer pinned code whose schema head was 6 migrations behind the live DB) was silent and indefinite — diagnosable only by manual git ls-tree + SELECT version_num. A head-skew assert turns that class of failure loud at boot."
type: hardening
planted: 2026-05-31
planted_during: "Registry self-heal interlude (commit 1cb5aa7). Operator queued this while ordering: fix #1 -> release-hygiene #2 -> resume CR.1-discuss. Release hygiene (v1.5.1 tag + re-pin) closed the *current* skew; this assert prevents the *next* one."
trigger_when: "Any reliability/operability phase, OR next time a schema migration lands. Cheap, self-contained, one subsystem. Do NOT let it expand into a migration-management project."
relates_to:
  - docs/forge-bridge-findings-2026-05-31.md
  - forge_bridge/server/app.py (start() — create_tables / restore_registry site)
  - forge_bridge/store/session.py
---

# Seed — migration-head assertion at startup (fast-follow)

## What

At server startup, compare the migration head the *installed code* expects
against the live DB's `alembic_version.version_num`; fail fast (clear error,
not a silent mismatch) when they diverge.

## Why (provenance)

projekt-forge findings 2026-05-31, item #2 (HIGH, release hygiene):

- Downstream pinned `forge-bridge @ …@v1.4.1`; that tag ships migrations
  through `0003` (old `staged_operations` *table* design).
- `main`/live DB is at `0009` (entity-backed staged ops; no such table).
- Result: code expecting a `0003`-era schema ran against a `0009` DB — an
  import/usage mismatch that was **silent and indefinite**, diagnosable only
  by hand (`git ls-tree -r <tag> -- …/migrations/versions` vs `SELECT
  version_num FROM alembic_version`).

The v1.5.1 release closed the *current* skew (tag now matches the `0009`
schema, consumers re-pin). This assert closes the *class*: the next time a
tag and a live DB drift, it surfaces at boot instead of as confusing
downstream behavior.

## Shape (lean, confirm at build)

- Determine the expected head from the packaged Alembic migrations (script
  directory `get_current_head()`), not a hardcoded constant — so it tracks
  automatically as migrations land.
- Read the live head via `alembic_version` (or Alembic `MigrationContext`).
- On mismatch: raise/log a single explicit error naming both heads and the
  remedy (`alembic upgrade head` or re-pin the package). Consider a
  `doctor` row mirroring it (same daemon-observed-truth discipline as the
  Phase 24.2 Flame probe).
- Decision to settle at build: hard-fail boot vs. loud-warn-and-continue.
  Lean: hard-fail when the live head is *ahead* of code (code too old, the
  reported case); warn when code is ahead of DB (operator forgot `upgrade`).

## Anti-scope

Not a migration runner, not auto-upgrade-on-boot, not a migration-management
subsystem. One assertion + one clear error. If it wants to grow, stop.
