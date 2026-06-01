# forge-bridge findings — handoff to bridge team

**Date:** 2026-05-31
**Reporter:** projekt-forge integration (Flame publish → registry)
**Environment:** macOS (Apple Silicon), Flame 2026.2.2, Postgres 17 @ `127.0.0.1:7533` db `forge_bridge`, project `013_13_13`, forge-bridge working copy at `pr24-stable` (declares `1.4.1`).

While getting the Flame publish→registry path working end-to-end we hit three forge-bridge-side issues. The publish now fully registers (20 shots / 20 versions / 45 media with `version_of` + `produces` edges) after working around them locally, but the root causes live in forge-bridge and should be fixed there.

---

## 1. Built-in relationship types are not guaranteed in a restored registry  — **HIGH**

**Symptom.** `relationship_create(version_id, shot_id, "version_of")` fails with:
```
[NOT_FOUND] Relationship type 'version_of' not found
```
The live `registry_relationship_types` table held only the 16 types seeded by migration `0004_phase4b_relationship_types` (`produces`, `consumes`, `reference_*`, `superseded_by`, …). The protected built-ins `member_of`, `version_of`, `derived_from`, `references`, `peer_of` were **absent**, so any client creating those edges fails. Publishes registered shots, then aborted on the version→shot link (0 versions/media).

**Root cause.** `forge_bridge/store/repo.py::RegistryRepo.restore_registry()` builds the registry with `Registry(seed_defaults=False)` and then loads **only** what's persisted in the DB:
```python
registry = Registry(seed_defaults=False)   # repo.py:138
# ... loads roles + relationship types from tables
```
The built-ins are defined in `core/registry.py::Registry._seed()` with permanent UUIDs from `core/traits.py::SYSTEM_REL_KEYS` and are marked *protected* — i.e. they're meant to be invariant — but nothing guarantees they exist in a given DB. A DB whose relationship types were established by migrations alone (not by a seeded `Registry`) is missing them.

**Impact.** Every Flame publish (and any consumer using built-in relationships) is broken on such DBs. Likely affects all existing project DBs provisioned via migrations.

**Suggested fix.** Make the 7 built-ins invariant rather than data:
- Either have server startup / `restore_registry()` **upsert** the built-ins from `SYSTEM_REL_KEYS` (idempotent — fixed UUIDs, protected), or
- Add a migration that inserts the 7 built-in rows, and validate relationship-type lookups fall back to `SYSTEM_REL_KEYS` for system types.

**Local workaround applied.** Seeded `member_of/version_of/derived_from/references/peer_of` into `registry_relationship_types` with canonical UUIDs via `Registry()` → `RegistryRepo.save_relationship_type`. Idempotent. (`consumes`/`produces` were already present.)

---

## 2. `v1.4.1` tag does not match the schema/code it's pinned for  — **HIGH (release hygiene)**

**Observed.**
- Downstream (`projekt_forge/pyproject.toml`) pins `forge-bridge @ git+…@v1.4.1`.
- The **`v1.4.1` tag** ships store migrations only through **`0003`** — the old dedicated `staged_operations` *table* design.
- **`main` HEAD** ships migrations through **`0009`** — staged ops are now **entity-backed** (`DBEntity` rows, `entity_type='staged_operation'`; no `staged_operations` table) — yet `pyproject.toml` on HEAD still declares `version = "1.4.1"`.
- The package actually **installed** in the env was **`1.3.0`** (older still).
- Live project DBs are at store alembic **`0009`** (provisioned by `main` HEAD).

**Impact.** Anyone resolving the `@v1.4.1` pin gets code + migration head `0003` whose `StagedOpRepo`/schema (a `staged_operations` table) **does not exist** in the live `0009` DB → import/usage mismatch. We had to `pip install -e` the `main` working copy to align code with the live DB.

**Suggested fix.**
- Bump the version on `main` (6 migrations past the tag still says `1.4.1`); version should move with schema/migration changes.
- Cut a fresh tag at the `0009`/entity-backed schema and have downstreams re-pin to it.
- Consider a startup assertion that the installed package's migration head matches the DB's `alembic_version`, failing fast on skew.

---

## 3. Topology note: prefer standalone `forge_bridge.server` for the ws DB server  — **MEDIUM**

Not strictly a forge-bridge bug, but relevant. `projekt_forge` can run its own embedded ws DB server (when launched without `--no-db`); that embedded server **accepts connections but never answers requests** (every `SyncClient` call hangs to the 30s client timeout). A freshly launched standalone **`forge_bridge.server` (1.4.1)** on the same DB answers `project_list`/`entity_list`/`entity_create` in **<1 ms**.

**Recommendation.** Document/standardize that the canonical ws DB server is `python -m forge_bridge.server` (env `FORGE_HOST`/`FORGE_PORT`, default `0.0.0.0:9998`), and consumers run MCP-only and talk to it — rather than embedding a second ws server. If the embedded path is meant to be supported, its request handler needs debugging (it's the projekt_forge side, but worth a heads-up since it shares forge-bridge store/session code).

---

## Reproduction pointers
- Built-in check: `SELECT name FROM registry_relationship_types ORDER BY name;` — note absence of `version_of` etc.
- Schema skew: `git ls-tree -r v1.4.1 -- forge_bridge/store/migrations/versions` (→0003) vs `main` (→0009); live DB `SELECT version_num FROM alembic_version;` (→0009).
- ws responsiveness: a `SyncClient(...).project_list()` against the embedded server hangs; against `forge_bridge.server` returns instantly.
