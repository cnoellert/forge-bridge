# Phase 5: Import Rewiring - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Rewire **projekt-forge** (`/Users/cnoellert/Documents/GitHub/projekt-forge/`) to stop shipping its own embedded `forge_bridge/` package and consume forge-bridge v1.0.0 as a pip dependency. Scope: rename projekt-forge's local package to `projekt_forge/`, add the pip dep, delete duplicated modules, swap imports, rebuild the MCP server around the pluggable registry, and verify the pip install resolves correctly.

Phase 5 is a forge-bridge milestone phase because its purpose is to validate forge-bridge's public API surface (declared in Phase 4) through its only consumer. Implementation commits land in the **projekt-forge** repo; planning artifacts live here in forge-bridge's `.planning/`.

Out of scope: Phase 6's learning-pipeline integration (`pre_synthesis_hook`, `set_execution_callback`, LLMRouter config wiring from forge_config.yaml); PyPI publishing (deferred); re-syncing any tool-file diffs between projekt-forge's local copies and canonical forge-bridge before the switch (see D-12 for how that's handled).

</domain>

<decisions>
## Implementation Decisions

### Local package rename (resolves namespace collision)

- **D-01:** Rename `projekt-forge/forge_bridge/` → `projekt-forge/projekt_forge/`. The distribution name `projekt-forge` stays; only the Python import package renames. Matches PEP 8 and the existing sibling pattern (`forge-bridge`/`forge_bridge`, `forge-align`/`forge_align`, `forge-collapse-xform`/`forge_collapse_xform`).
- **D-02:** Rewrite all 178 `from forge_bridge.*` imports inside projekt-forge that reference forge-specific code (cli, config, conform, db, scanner, seed, forge-specific tools, forge-specific server modules) to `from projekt_forge.*`. Imports that reference *canonical* symbols (bridge execute, canonical tools, clients) get rewritten separately in Wave B — those point at the pip package.
- **D-03:** Update `pyproject.toml` in projekt-forge: `packages = ["projekt_forge"]` and rewrite the two `[project.scripts]` entries. The `forge-bridge = "forge_bridge.server:main"` script is **removed** — the pip package ships its own `forge-bridge` console script now. `forge = "forge_bridge.cli.main:cli"` becomes `forge = "projekt_forge.cli.main:cli"`.

### pip dependency source (no PyPI)

- **D-04:** projekt-forge's `pyproject.toml` adds `forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.0` to dependencies. Version-pinned, portable, reproducible.
- **D-05:** **Prerequisite for this phase:** tag forge-bridge's `main` at `v1.0.0` before Wave B lands. `pyproject.toml` already has `version = "1.0.0"` from Phase 4 (D-23); this phase creates the matching git tag that the `@v1.0.0` URL references.
- **D-06:** Local dev loop: after `pip install -e .` in projekt-forge, run `pip install -e /Users/cnoellert/Documents/GitHub/forge-bridge` to shadow the git-pinned install with the working copy. Document in projekt-forge's CLAUDE.md as part of Wave A.
- **D-07:** Skip PyPI entirely for v1.1 (confirmed in PROJECT.md). Skip `file://` paths in pyproject.toml — machine-specific.

### Delete / move / audit rule (scope-of-deletion)

- **D-08:** Rule over upfront inventory. Research step produces the full file-by-file list; this context fixes the *criteria*:
  - **DELETE** when the file is a direct duplicate of canonical forge-bridge and the canonical version is imported via the pip package instead: `bridge.py`; canonical tool files `tools/{batch,project,publish,timeline,switch_grade,reconform,utility}.py`; canonical client files `client/{async_client,sync_client}.py`.
  - **MOVE + rename namespace** when the file is forge-specific and has no canonical counterpart: `cli/`, `config/`, `conform/`, `db/`, `scanner/`, `seed/`, `server/{handlers,db_server,registry}.py`, `tools/{catalog,orchestrate,scan,seed}.py`, `__main__.py` (the bespoke TaskGroup(mcp + db_server) orchestration is forge-specific).
  - **REWRITE** `server/mcp.py`: its 30+ manual `mcp.tool(...)` calls collapse to `mcp = get_mcp(); register_tools(mcp, [...], prefix="forge_", source="builtin")` — details in D-13.
- **D-09:** **Two hybrids must be audited during research before Wave B plans are written.** Research cannot skip these:
  - `projekt-forge/forge_bridge/server/protocol/` vs canonical `forge-bridge/forge_bridge/server/protocol.py` — audit whether projekt-forge's version is (a) a proper superset/extension that stays as `projekt_forge/server/protocol/`, or (b) a stale fork that should be deleted in favor of the canonical symbols. Report the diff; planner decides.
  - `projekt-forge/forge_bridge/client/{async_client,sync_client}.py` diffs vs canonical — research captures what diverged and why. If the divergence is bug fixes or improvements, they get pushed back to forge-bridge as a patch release (v1.0.1) *before* Wave B deletes the local copies. If the divergence is forge-specific behavior that shouldn't be upstream, the local files become `projekt_forge/client/` instead of being deleted.
- **D-10:** The known tool-file diffs (`batch.py`, `project.py`, `publish.py`, `timeline.py`, `switch_grade.py`) between projekt-forge's local copies and canonical forge-bridge — research must confirm canonical forge-bridge v1.0 has the evolved versions (this was Phase 1 of v1.0). If any divergence remains, same patch-release rule as D-09 applies before Wave B.

### Execution shape (4 waves, each atomic)

- **D-11:** Four waves, each lands as one commit (or a tight sequence of atomic commits within the wave). Wave B is the literal RWR-02 atomic switch.
  - **Wave A — Rename prep (behavior-preserving).** Rename `forge_bridge/` → `projekt_forge/` in projekt-forge; rewrite all internal imports; update `pyproject.toml` package list + script entries; add dev-loop docs to CLAUDE.md. No pip dep yet. Full test suite must pass. Single commit, big diff, zero behavior change — bisectable.
  - **Wave B — pip consume (RWR-01, RWR-02).** Add `forge-bridge @ git+...@v1.0.0` dep; delete the duplicated modules identified by D-08; rewrite their call sites to `from forge_bridge import ...`. One commit.
  - **Wave C — MCP rewire (RWR-03).** Rebuild `projekt_forge/server/mcp.py` around `get_mcp()` + `register_tools(..., source="builtin")`; update `__main__.py` if needed. One commit.
  - **Wave D — Verify (RWR-04).** Add conftest assertion (D-15); run full pytest; record green run in phase verification. One commit.
- **D-12:** If D-09 audit forces a forge-bridge v1.0.1 patch release (client diffs, protocol diffs), that patch-and-tag work happens **before Wave B** as a pre-phase unblocker. The phase plan lists it as an explicit dependency, not a deviation.

### MCP server rewire details (RWR-03, API-04, API-05)

- **D-13:** `projekt_forge/server/mcp.py` post-Wave-C shape:
  ```python
  from forge_bridge import get_mcp, register_tools
  from projekt_forge.tools import catalog, orchestrate, scan, seed

  mcp = get_mcp()  # FastMCP singleton from pip package, flame_* tools pre-registered

  register_tools(
      mcp,
      [catalog.trace_lineage, catalog.get_shot_deps,
       orchestrate.publish_pipeline,
       scan.media_scan,
       seed.seed_catalog, ...],
      prefix="forge_",
      source="builtin",
  )
  ```
  All `flame_*` tool registrations in projekt-forge's current file go away — they come from the pip package's own lifespan.
- **D-14:** projekt-forge's custom `__main__.py` (TaskGroup(mcp + db_server)) stays as `projekt_forge/__main__.py` but is updated to use the pip package's `startup_bridge()` / `shutdown_bridge()` via the FastMCP lifespan — no direct `_startup`/`_shutdown` calls anywhere.

### RWR-04 verification

- **D-15:** pytest conftest assertion in projekt-forge, runs on every test invocation:
  ```python
  # projekt-forge/tests/conftest.py
  import pathlib
  import forge_bridge

  def test_forge_bridge_resolves_to_site_packages():
      p = pathlib.Path(forge_bridge.__file__).resolve()
      assert "site-packages" in p.parts, (
          f"forge_bridge resolved to {p} — expected site-packages. "
          "Re-check: no local forge_bridge/ directory, pip install current."
      )
  ```
  Plus a defensive assertion that no top-level `forge_bridge/` directory exists at the projekt-forge repo root (catches someone recreating the collision).
- **D-16:** "Verified in CI" requirement is satisfied by any pytest run — dev machine, or a GitHub Actions workflow if/when added. No new CI infrastructure is a Phase 5 deliverable; the assertion is the contract.

### Planning location + cross-repo tracking

- **D-17:** Phase 5 plans, research artifact, verification report live in `forge-bridge/.planning/phases/05-import-rewiring/`. Commits recording planning artifacts land in the **forge-bridge** repo.
- **D-18:** Implementation commits land in the **projekt-forge** repo. Commit-message convention: `{type}(projekt_forge): {subject} — forge-bridge phase 5 wave {A|B|C|D}`. Example: `refactor(projekt_forge): rename forge_bridge→projekt_forge namespace — forge-bridge phase 5 wave A`.
- **D-19:** Executor `cd`s into `/Users/cnoellert/Documents/GitHub/projekt-forge` for implementation commits; absolute paths in plan files are required (no repo-relative paths — the plan lives in a different repo than the file it's modifying).

### Claude's Discretion

- Whether Wave A's 178-import rewrite is mechanical `sed`/ruff-rewrite or a more surgical pass (planner decides based on whether imports cluster into easy patterns).
- Whether Wave A updates `projekt-forge/.planning/` artifacts to reflect the rename, or leaves those to projekt-forge's own roadmap cycle.
- Exact wording of the conftest assertion error messages (D-15).
- Whether to split Wave A into two commits (rename + import fix-up) if the diff is large enough to hurt review, or keep it as one commit per the "each wave atomic" rule (D-11) — planner picks.
- Whether projekt-forge's `flame_hooks/forge_tools/` references to `forge_bridge.client.sync_client` resolve against the pip package (runs inside Flame's stdlib-only interpreter — may not have the pip install available). Research must flag any hook that imports from a non-stdlib path.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements

- `.planning/ROADMAP.md` §Phase 5 — Goal, depends-on (Phase 4), 4 success criteria
- `.planning/REQUIREMENTS.md` §Import Rewiring — RWR-01, RWR-02, RWR-03, RWR-04 definitions
- `.planning/PROJECT.md` §Constraints — backward-compat (don't break deployed Flame hook or MCP server), standalone independence, Python 3.10+, optional LLM deps
- `.planning/PROJECT.md` §Active — projekt-forge rewire is the first listed active item
- `.planning/STATE.md` §Blockers/Concerns — "[Phase 5]: Import blast radius in projekt-forge not yet measured" — resolved during discussion (178 imports across ~40 files; blocker can be removed in state update)

### Phase 4 decisions this phase depends on

- `.planning/phases/04-api-surface-hardening/04-CONTEXT.md` §Public API surface (D-01, D-02, D-03) — the 11-name public surface projekt-forge imports from: `LLMRouter`, `get_router`, `ExecutionLog`, `SkillSynthesizer`, `register_tools`, `get_mcp`, `startup_bridge`, `shutdown_bridge`, `execute`, `execute_json`, `execute_and_read`
- `.planning/phases/04-api-surface-hardening/04-CONTEXT.md` §Server lifecycle + post-run guard (D-11, D-14, D-15) — explains the `startup_bridge`/`shutdown_bridge` rename and the `_server_started` guard that affects D-14 above
- `.planning/phases/04-api-surface-hardening/04-CONTEXT.md` §Registry & Packaging (D-22, D-23) — `register_tools(source="builtin")` is already supported; version `1.0.0` is already in pyproject.toml
- `.planning/phases/04-api-surface-hardening/04-VERIFICATION.md` — confirms Phase 4 success criteria pass, establishes what's safe to consume

### forge-bridge canonical source (read to understand what's being imported)

- `forge_bridge/__init__.py` — the 11-name public surface; projekt-forge imports from this module root after Wave B
- `forge_bridge/mcp/__init__.py` — exports `register_tools`, `get_mcp`
- `forge_bridge/mcp/server.py` — `startup_bridge`, `shutdown_bridge`, the FastMCP `mcp` singleton
- `forge_bridge/mcp/registry.py` — `register_tools(mcp, fns, prefix, source)` signature and the post-`run()` guard
- `forge_bridge/bridge.py` — `execute`, `execute_json`, `execute_and_read`
- `pyproject.toml` (this repo) — version 1.0.0, what the git tag will anchor

### projekt-forge source to modify (cross-repo)

- `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` — dep addition, package list, script entries
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/` — entire tree renames to `projekt_forge/` in Wave A; duplicates get deleted in Wave B
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/server/mcp.py` — full rewrite in Wave C (currently registers 30+ tools manually)
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/__main__.py` — TaskGroup(mcp + db_server); updates in Wave C
- `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/` — conftest gets RWR-04 assertion; all test imports follow the rename in Wave A
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_gui/` — GUI imports forge_bridge.config/cli; follow the rename in Wave A
- `/Users/cnoellert/Documents/GitHub/projekt-forge/flame_hooks/forge_tools/` — audit for any `from forge_bridge.*` imports (per D-08 Claude's Discretion note)
- `/Users/cnoellert/Documents/GitHub/projekt-forge/CLAUDE.md` — update for dev-loop doc (D-06)

### Codebase conventions (both repos)

- `.planning/codebase/CONVENTIONS.md` — ruff config, 100-char lines, Python 3.10+ `|` unions, `from __future__ import annotations`, explicit `__init__.py` re-exports
- `.planning/codebase/STRUCTURE.md` §Where to Add New Code — module layout reference for forge-bridge; **note: written 2026-04-14, predates v1.0; may not reflect current `llm/`, `learning/`, rebuilt `mcp/` structure** (same caveat Phase 4 flagged)

### Historical context (acknowledged stale — do not follow literally)

- `MIGRATION_PLAN.md` (repo root) — written pre-v1.0; describes the v1.1 rewire at a very different level of abstraction. Useful for motivation context; out-of-date for current phase/requirement numbering. **Do not use as an implementation spec.**

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `forge_bridge.get_mcp()` (pip) — returns the module-level FastMCP singleton from `forge_bridge.mcp.server`; projekt-forge's rewired `server/mcp.py` (D-13) calls this once instead of constructing its own `FastMCP("forge_bridge")`.
- `forge_bridge.register_tools(mcp, fns, prefix, source)` (pip) — already supports `source="builtin"` (Phase 4 D-22). Projekt-forge's Wave C calls it once with all forge-specific tool functions.
- `forge_bridge.bridge.execute` / `execute_json` / `execute_and_read` (pip) — the canonical HTTP-to-Flame entry points. Projekt-forge's forge-specific tools (catalog, orchestrate, scan, seed) currently call the local `forge_bridge.bridge`; Wave B switches them to the pip imports.

### Established Patterns

- **Pip-consumer shape** — FastMCP singleton accessed via `get_mcp()`, tools registered externally via `register_tools()`. Phase 4 D-01/D-02/D-04 established this exact API for downstream consumption; Phase 5 is the first test of it.
- **Namespace rename without behavior change** (Wave A pattern) — full-tree move + import sweep + verify tests pass, no functional edits. Same pattern as any Python-package rename.
- **Clean-break rename philosophy** — carried forward from Phase 4 (D-11, D-19). No `forge_bridge` alias module in projekt-forge pointing at `projekt_forge`. No transitional shims.
- **Cross-repo commit convention** — new for this phase (D-18). Documented here so Phase 6 can follow the same pattern.

### Integration Points

- **projekt-forge pyproject.toml** — single-file touch for dep addition, package list, script entries (Wave A + Wave B).
- **projekt-forge tests/conftest.py** — single-file touch for RWR-04 verification (Wave D).
- **projekt-forge server/mcp.py** — single-file rewrite for MCP wiring (Wave C); every forge-specific tool that was registered manually collapses into one `register_tools()` call.
- **projekt-forge `__main__.py`** — updated to use `startup_bridge`/`shutdown_bridge` from the pip package (Wave C).

### Downstream awareness

- Phase 6 will construct `LLMRouter(local_url=..., local_model=..., system_prompt=...)` from `forge_config.yaml` values — that's a `projekt_forge.config.forge_config` import calling `forge_bridge.LLMRouter(...)`. Phase 5's Wave A must not break the `config.forge_config` module; Phase 6 adds the LLMRouter construction inside it.
- Phase 6 will add a storage-callback hook on `ExecutionLog` and a `pre_synthesis_hook` kwarg to `SkillSynthesizer(router=..., pre_synthesis_hook=...)`. Both are pip-package changes (forge-bridge v1.1.x patch), consumed by projekt-forge via imports that already work after Phase 5. Phase 5 sets up the import path; Phase 6 exercises it.

### Known blast radius

- **178 `from forge_bridge.*` imports** in projekt-forge (measured during discussion)
- Distribution:
  - `forge_bridge.config.*`: 16
  - `forge_bridge.db.*`: 26
  - `forge_bridge.server.*` (protocol, handlers, etc.): 23
  - `forge_bridge.conform.*`: 20
  - `forge_bridge.client.*`: 12
  - `forge_bridge.cli.*`: 20
  - `forge_bridge.scanner.*`: 11
  - `forge_bridge.seed.*`: 5
  - `forge_bridge.tools.*`: 10 (canonical + forge-specific mixed)
  - `forge_bridge.bridge`: 3
- Wave A rewrites all of these to `from projekt_forge.*`; Wave B flips the canonical subset back to `from forge_bridge.*` (pip).

</code_context>

<specifics>
## Specific Ideas

- **Atomic waves over mega-commit.** RWR-02 says "in same commit" — that's about the pip-dep-add + duplicate-delete being atomic together (Wave B), not about the entire phase being one commit. The phase overall spans 4 commits so each state is independently buildable and bisectable. If a wave fails CI, the previous wave is a known-good rollback target.
- **Wave A before Wave B is a safety belt, not a detour.** Renaming in place first means every Wave B conflict shows up as "pip import missing" (clean error), not "which `forge_bridge.bridge` did that mean — local or pip?" (silent ambiguity). The rename cost is paid once anyway.
- **Git tag on forge-bridge is a Phase 5 deliverable.** v1.1's dep URL says `@v1.0.0` but no git tag exists today. Phase 5's first concrete action is `git tag v1.0.0 && git push --tags` in forge-bridge before Wave B starts. Plan treats this as an explicit unblocker task, not implicit.
- **conftest over CI workflow for RWR-04.** The requirement language "verified in CI" is achievable without building CI — a test-suite-level assertion runs on every pytest invocation by every developer, and automatically satisfies the requirement the moment any CI system runs the test suite. No commitment to a specific CI vendor or YAML to maintain.
- **D-09 audits are real work.** Research cannot just skim these — the client/ and server/protocol/ diffs may force a forge-bridge patch release (v1.0.1) before Wave B. That dependency needs to surface in the research artifact, not be discovered during execution.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 6 wiring** — `pre_synthesis_hook`, `set_execution_callback`, `LLMRouter` construction from `forge_config.yaml`, storage callback to forge's DB. All explicitly out of scope per Phase 4 D-21, and confirmed out of scope here.
- **PyPI publishing** — deferred per PROJECT.md constraints; git dep is the permanent v1.1 solution.
- **Dropping `projekt-forge/forge_bridge/` from `.gitignore` / adding a pre-commit hook** to prevent the collision from reappearing — nice belt-and-suspenders on top of D-15's defensive assertion, but the assertion is sufficient. Note for future.
- **Renaming projekt-forge's distribution name** — stays `projekt-forge`. No project-wide rename; only the Python package directory changes.
- **GitHub Actions workflow for projekt-forge** — not a Phase 5 deliverable (D-16). When/if projekt-forge needs CI, that's its own scoping exercise.
- **Migrating projekt-forge's flame_hooks to use the pip package's flame_hooks** — the pip package ships `flame_hooks/forge_bridge/scripts/forge_bridge.py`; projekt-forge has `flame_hooks/forge_tools/` (forge-specific, separate concern). Not in scope; projekt-forge's hooks are distinct from forge-bridge's bridge hook.
- **Resolving the `STRUCTURE.md` staleness** (2026-04-14, predates v1.0 reshape). Noted in canonical_refs; not a Phase 5 fix.

</deferred>

---

*Phase: 05-import-rewiring*
*Context gathered: 2026-04-16*
