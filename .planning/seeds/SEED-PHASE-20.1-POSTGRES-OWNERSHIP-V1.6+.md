---
name: SEED-PHASE-20.1-POSTGRES-OWNERSHIP-V1.6+
description: forge-bridge claims to be middleware but installs Postgres — revisit cluster vs. schema ownership at v1.6+
type: forward-looking-idea
planted_during: Phase 20.1 macOS UAT walk on portofino (2026-05-01)
trigger_when: v1.6 milestone is opened, OR projekt-forge v1.5+ is being planned, OR a new endpoint adapter is being scoped that needs DB access
---

# SEED-PHASE-20.1-POSTGRES-OWNERSHIP-V1.6+: Decouple Postgres cluster ownership from forge-bridge

## Idea

forge-bridge currently does two things with Postgres:
1. **Owns the schema** — alembic migrations live in `forge_bridge/store/migrations/`, schema design in `forge_bridge/store/`, `StoragePersistence` Protocol contract.
2. **Owns the cluster** — `scripts/install-bootstrap.sh` installs Postgres binaries (Homebrew on macOS, dnf on Linux), initializes the cluster on Linux, configures `pg_hba.conf` auth, creates role + db.

The second job is in tension with forge-bridge's own architectural thesis (per CLAUDE.md): *"forge-bridge is **middleware** — a protocol-agnostic communication bus for post-production pipelines."* A communication bus that ships infrastructure provisioning is doing two jobs.

At v1.6+, retire (2). Keep (1).

## Why This Matters

**Operational reality (the immediate trigger):** Phase 20.1's macOS UAT walk on portofino surfaced that the bootstrap was about to `brew install postgresql@16` on a host that already had `/opt/Autodesk/pgsql-17/` — Autodesk-bundled Postgres that Flame and projekt-forge have been using for years. We patched this in-flight (`scripts/install-bootstrap.sh:bootstrap_pg_macos()` now detects `/opt/Autodesk/pgsql-*/bin` first), but the patch is a workaround. The real question is: **why is forge-bridge in the business of installing Postgres at all?**

**Architectural reality:** projekt-forge is the only consumer of forge-bridge that exists today. On a Flame workstation, projekt-forge has its own data state in Autodesk's bundled Postgres. forge-bridge wants its own role + db within that cluster. Two reasonable layerings:

| Concern | Today (forge-bridge owns both) | Proposed (split ownership) |
|---------|--------------------------------|----------------------------|
| Postgres binary install / cluster init | forge-bridge `install-bootstrap.sh` | Operator (or projekt-forge bootstrap) |
| `forge` role + `forge_bridge` db provisioning | forge-bridge `install-bootstrap.sh` | Operator (or projekt-forge bootstrap) |
| `FORGE_DB_URL` env contract | forge-bridge consumes | forge-bridge consumes (unchanged) |
| Alembic migrations | forge-bridge owns | forge-bridge owns (unchanged) |
| Schema design + Protocol StoragePersistence | forge-bridge owns | forge-bridge owns (unchanged) |

The split aligns forge-bridge with how it already treats Ollama: the bootstrap doesn't `brew install ollama` — it accepts `FORGE_LOCAL_LLM_URL` and expects the operator to provision Ollama separately. Postgres should be the same.

**Cost of doing nothing:**
- Every new endpoint adapter (Maya, editorial, shot-tracking, custom AI worker) inherits the Postgres-install assumption — the bootstrap script grows another OS branch each time.
- Flame-workstation reality (Autodesk-bundled Postgres) gets papered over with detection patches like the 20.1 in-flight fix; future Flame versions ship pgsql-18, pgsql-19, etc. and we keep adding `ls /opt/Autodesk/pgsql-*/bin` glob detection.
- Multi-host topologies (db on a separate server) are awkward to support — the bootstrap implicitly assumes Postgres is local.
- True "middleware" composability never materializes — forge-bridge keeps owning operator-host concerns it shouldn't.

## Boundaries

This seed is about **cluster lifecycle ownership**, NOT about the schema or the Protocol layer. Specifically out of scope:
- Changing `forge_bridge/store/migrations/` — alembic stays in forge-bridge.
- Changing `StoragePersistence` Protocol or how it's consumed — those are middleware concerns.
- Removing forge-bridge's ability to run alembic — `forge-bridge migrate` (or equivalent) is a fine command for a middleware library to ship.

In scope (when this seed activates):
- Stripping `bootstrap_pg_*` functions from `scripts/install-bootstrap.sh`.
- Documenting the operator's pre-install responsibility (or pointing at projekt-forge's bootstrap).
- Adding a connectivity preflight check (`pg_isready` against `FORGE_DB_URL`) at install-time so install fails fast if the cluster isn't reachable.
- Updating `docs/INSTALL.md` to reflect the new layering.
- Possibly: a `forge-bridge migrate` CLI subcommand for operators who want to run alembic explicitly.

## When This Seed Activates

Any of:
1. **v1.6 milestone opens** — automatic re-evaluation point.
2. **projekt-forge v1.5+ planning starts** — projekt-forge is the natural candidate to own the cluster bootstrap, so its planning loop should pull this in as a coupled decision.
3. **A new endpoint adapter is being scoped** (Maya, editorial, etc.) — if the new adapter would inherit the install-bootstrap inconsistency, address ownership first.
4. **The bootstrap script's macOS branch needs a third Postgres-detection patch** (e.g., a non-Autodesk, non-Homebrew install path appears) — that's a signal the workaround layer is calcifying.

## Phase 20.1 In-Flight Patch (already shipped)

`scripts/install-bootstrap.sh:bootstrap_pg_macos()` now detects `/opt/Autodesk/pgsql-*/bin` before falling back to Homebrew. Regression test: `tests/test_packaging.py::test_install_bootstrap_macos_detects_autodesk_postgres_before_brew`. This is a workaround that buys us time until this seed activates; do NOT take it as a precedent for adding Linux/RPM equivalents (`/usr/pgsql-17/`, etc.) — that's the calcification signal flagged above.

## Open Questions (for the v1.6+ planning loop)

- Does projekt-forge ship a Postgres bootstrap today? If yes, does it cover Flame workstations and Linux servers (the two forge-bridge install targets)? If no, who provisions Postgres on a fresh forge-bridge install — pure operator responsibility, or a thin shared bootstrap?
- Should forge-bridge's `console doctor` check `FORGE_DB_URL` reachability and surface a clear error pointing at the responsibility split, instead of failing alembic mid-install?
- What's the migration story for existing forge-bridge installs? `install-bootstrap.sh` users on v1.5 have a `forge_bridge` db they expect; v1.6+ shouldn't break their cluster.

## Why Plant Now

Phase 20.1 closed the v1.5 ship blocker and is in the close-out loop. The in-flight Autodesk-Postgres detection patch makes the macOS walk pass without disturbing v1.5 scope. But the architectural concern surfaced honestly during a real UAT walk and deserves a structural answer at the next milestone — capturing it now keeps the option live.
