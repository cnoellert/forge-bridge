# Phase 5: Import Rewiring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `05-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 05-import-rewiring
**Areas discussed:** All six gray areas (user asked for recommendations across the board)

---

## Pre-Discussion Scout

Blast radius measurement resolving STATE.md blocker:

- **178** `from forge_bridge.*` import lines in projekt-forge across tests, CLI, GUI, tools, flame_hooks
- Top clusters: `db.*` (26), `server.*` (23), `conform.*` (20), `cli.*` (20), `config.*` (16), `client.*` (12), `scanner.*` (11), `tools.*` (10), `seed.*` (5), `bridge` (3)
- projekt-forge's embedded `forge_bridge/` contains duplicates (`bridge.py`, canonical `tools/*.py`, `client/*.py` — all differ from canonical v1.0), forge-specific modules (`cli/`, `config/`, `conform/`, `db/`, `scanner/`, `seed/`), and hybrids (`server/mcp.py` registers both flame_* and forge_* tools; `server/protocol/` may be canonical or a fork)
- `pyproject.toml` has `forge-bridge = "forge_bridge.server:main"` script entry — collides with pip package name

---

## Area 1: Local namespace collision resolution

Embedded `projekt-forge/forge_bridge/` shadows the pip package. Must change.

| Option | Description | Selected |
|--------|-------------|----------|
| `projekt_forge/` | Matches distribution name (PEP 8: `projekt-forge` → `projekt_forge`); sibling pattern (`forge_bridge`, `forge_align`, `forge_collapse_xform`) | ✓ |
| `forge/` | Short; but "forge" is already overloaded (`forge` CLI command, `forge.py` at repo root) | |
| `forge_pipeline/` | From stale MIGRATION_PLAN.md; "pipeline" is only part of what lives there (CLI, GUI, DB, scanner too) | |
| Multi-package split (`forge_cli/`, `forge_db/`, etc.) | Adds dep-graph complexity for no gain at this scale | |

**User's choice:** `projekt_forge/`
**Notes:** User asked explicitly about the hyphen-vs-underscore convention across sibling tools. Answer: PEP 8 pattern — hyphens at distribution layer, underscores at Python import layer. Existing siblings (`forge-bridge`/`forge_bridge`, `forge-align`/`forge_align`, `forge-collapse-xform`/`forge_collapse_xform`) all follow this. `projekt-forge` → `projekt_forge` is mechanical and matches.

---

## Area 2: pip dependency source

PyPI deferred per PROJECT.md. Real options:

| Option | Description | Selected |
|--------|-------------|----------|
| Git tag in pyproject | `forge-bridge @ git+...@v1.0.0` — portable, version-pinned, reproducible | ✓ |
| Local `file://` path | Machine-specific; brittle in version control even with single dev | |
| Editable install separate from pyproject | Flexible but requires manual step, easy to forget | |
| Git tag + local editable override | Git-pinned in pyproject + `pip install -e ../forge-bridge` as dev loop | ✓ (combined) |

**User's choice:** Git tag primary + local editable override for dev loop
**Notes:** Phase 5 prerequisite surfaced: tag forge-bridge's `main` at `v1.0.0` before Wave B lands. `pyproject.toml` version is already 1.0.0 (Phase 4 D-23), but no matching git tag exists. Documented in D-05 as explicit unblocker.

---

## Area 3: Scope of delete / move / keep

Hybrid files require audit; rule over upfront inventory.

| Option | Description | Selected |
|--------|-------------|----------|
| Upfront file-by-file inventory | Attempt to decide every file's fate now | |
| Rule-based with research audit | Fix the criteria; research produces the file list; two named hybrids must be audited | ✓ |

**User's choice:** Rule-based with research audit
**Notes:** Two hybrids flagged for research:
1. `projekt-forge/forge_bridge/server/protocol/` vs canonical `forge-bridge/forge_bridge/server/protocol.py` — is projekt-forge's a proper extension (stays) or a stale fork (deletes)?
2. `projekt-forge/forge_bridge/client/*.py` — diffs against canonical; if divergence is worth keeping, may force forge-bridge v1.0.1 patch release before Wave B. Same rule applies to any tool-file diffs discovered during research.

Known duplicates to delete: `bridge.py`, canonical `tools/{batch,project,publish,timeline,switch_grade,reconform,utility}.py`, `client/{async_client,sync_client}.py`.
Known forge-specific to move: `cli/`, `config/`, `conform/`, `db/`, `scanner/`, `seed/`, `server/{handlers,db_server,registry}.py`, `tools/{catalog,orchestrate,scan,seed}.py`, `__main__.py`.
Known rewrite: `server/mcp.py` (full rewrite around `get_mcp()` + `register_tools()`).

---

## Area 4: Execution atomicity

RWR-02 says "in same commit." Literal reading vs pragmatic reading.

| Option | Description | Selected |
|--------|-------------|----------|
| One mega-commit (literal RWR-02) | 200+ files in one diff; bisecting breaks if anything fails | |
| 4 waves, each atomic | Wave B = the literal RWR-02 atomic switch; A/C/D wrap it | ✓ |
| Long-running branch, squash at end | Loses bisect granularity during development | |

**User's choice:** 4-wave execution
**Notes:** Each wave is one commit (or a tight sequence of atomic commits within the wave if splitting aids review — planner's call per D-11 Claude's Discretion). Wave ordering: A (rename prep, behavior-preserving) → B (pip consume + duplicate delete, the RWR-02 atomic commit) → C (MCP rewire) → D (RWR-04 verify). Rationale: Wave A surfaces pip-import errors cleanly in Wave B because everything local is already renamed; without Wave A, `forge_bridge.bridge` is ambiguous between local and pip during the switch.

---

## Area 5: Planning + tracking location

Phase lives in forge-bridge's roadmap; code lands in projekt-forge.

| Option | Description | Selected |
|--------|-------------|----------|
| Plans here, commits in projekt-forge | forge-bridge hosts the phase; commits reference phase in message | ✓ |
| Mirror phase in projekt-forge's `.planning/` | Sync burden across two GSD states for one phase | |
| Worktree / workspace for both repos | Overkill for linear 4-wave migration | |

**User's choice:** Plans in forge-bridge; implementation commits in projekt-forge
**Notes:** Commit-message convention documented in D-18: `{type}(projekt_forge): {subject} — forge-bridge phase 5 wave {A|B|C|D}`. Plans use absolute paths for projekt-forge files (D-19). Phase 6 will follow the same pattern.

---

## Area 6: RWR-04 verification path

"Verified in CI" requirement — projekt-forge has no CI workflow yet.

| Option | Description | Selected |
|--------|-------------|----------|
| Add GitHub Actions workflow as Phase 5 deliverable | New infrastructure commitment; YAML to maintain | |
| Manual verification recorded in STATE.md | One-time check, doesn't guard against regression | |
| pytest conftest assertion | Runs on every pytest invocation; satisfies "CI" automatically if any CI runs `pytest` | ✓ |

**User's choice:** pytest conftest assertion
**Notes:** Assertion checks `pathlib.Path(forge_bridge.__file__).resolve()` contains `site-packages`. Plus a defensive check that no top-level `forge_bridge/` directory exists at repo root (catches re-introduction of the collision). "Verified in CI" becomes automatic the moment any CI system runs the existing pytest suite — no separate workflow to maintain.

---

## Claude's Discretion

Areas the user left to the planner:

- Mechanical vs surgical approach to the 178-import rewrite in Wave A
- Whether to split Wave A into rename + import-fixup commits if review benefits
- Exact wording of conftest assertion error messages
- How to handle projekt-forge's `flame_hooks/forge_tools/` imports (those hooks run inside Flame's stdlib-only interpreter — may not resolve against pip install)
- Updating projekt-forge's own `.planning/` to reflect the rename

## Deferred Ideas

- Phase 6 learning-pipeline wiring (`pre_synthesis_hook`, callback, LLMRouter from forge_config.yaml) — explicit Phase 4 D-21 and Phase 5 deferral
- PyPI publishing — PROJECT.md constraint
- Pre-commit hook or `.gitignore` to prevent `forge_bridge/` collision reappearing — D-15 conftest assertion is sufficient
- projekt-forge distribution rename — stays `projekt-forge`
- GitHub Actions for projekt-forge — separate scoping exercise
- Migrating flame_hooks to pip flame_hooks — out of scope, different concerns
- Resolving `STRUCTURE.md` staleness (predates v1.0 reshape)
