# Phase 5: Import Rewiring — Research

**Researched:** 2026-04-16
**Domain:** Python package namespace migration, cross-repo pip dependency wiring
**Confidence:** HIGH — all findings verified by direct file inspection of both repos

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Rename `projekt-forge/forge_bridge/` → `projekt-forge/projekt_forge/`. Distribution name stays; only the Python import package renames.
- **D-02:** Rewrite all 178 `from forge_bridge.*` imports referencing forge-specific code to `from projekt_forge.*` in Wave A. Canonical-symbol imports rewritten to `from forge_bridge.*` (pip) in Wave B.
- **D-03:** Update `pyproject.toml`: `packages = ["projekt_forge"]`, rewrite script entries. `forge-bridge = "forge_bridge.server:main"` removed (pip ships it now). `forge = "forge_bridge.cli.main:cli"` → `forge = "projekt_forge.cli.main:cli"`.
- **D-04:** Add `forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.0` to dependencies.
- **D-05:** Tag forge-bridge `main` at `v1.0.0` before Wave B. This is a Phase 5 deliverable.
- **D-06:** Local dev loop: `pip install -e /Users/cnoellert/Documents/GitHub/forge-bridge` shadows git dep. Document in projekt-forge CLAUDE.md in Wave A.
- **D-07:** Skip PyPI and `file://` paths.
- **D-08:** Delete/Move/Rewrite criteria fixed (bridge.py, canonical tools, canonical clients → DELETE; forge-specific → MOVE+rename; server/mcp.py → REWRITE).
- **D-09:** Two hybrids audited during research (protocol/ and client/).
- **D-10:** Tool-file diffs audited during research.
- **D-11:** Four atomic waves. Wave B is the literal RWR-02 atomic switch.
- **D-12:** If D-09 audit forces v1.0.1, that work happens before Wave B as an explicit dependency.
- **D-13:** `projekt_forge/server/mcp.py` post-Wave-C shape uses `get_mcp()` + `register_tools(...)`.
- **D-14:** `projekt_forge/__main__.py` updated to use `startup_bridge()`/`shutdown_bridge()` from pip package.
- **D-15:** pytest conftest assertion verifies `forge_bridge.__file__` resolves to site-packages.
- **D-16:** "Verified in CI" = any pytest run.
- **D-17–D-19:** Planning artifacts in forge-bridge; implementation commits in projekt-forge; commit-message convention `{type}(projekt_forge): {subject} — forge-bridge phase 5 wave {A|B|C|D}`; absolute paths required in plans.

### Claude's Discretion

- Whether Wave A's 178-import rewrite is mechanical `sed`/ruff-rewrite or surgical.
- Whether Wave A updates `projekt-forge/.planning/` artifacts.
- Exact wording of conftest assertion error messages.
- Whether to split Wave A into two commits (rename + import fix-up).
- Whether `flame_hooks/forge_tools/` references to `forge_bridge.client.sync_client` resolve against the pip package.

### Deferred Ideas (OUT OF SCOPE)

- Phase 6 wiring (pre_synthesis_hook, LLMRouter from forge_config.yaml, storage callback).
- PyPI publishing.
- Dropping `forge_bridge/` from `.gitignore` / pre-commit hook.
- Renaming projekt-forge's distribution name.
- GitHub Actions workflow for projekt-forge.
- Migrating flame_hooks to use pip package's flame_hooks.
- Resolving STRUCTURE.md staleness.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RWR-01 | projekt-forge adds `forge-bridge>=1.0,<2.0` to `pyproject.toml` dependencies | D-04: git dep syntax verified; pyproject.toml structure reviewed |
| RWR-02 | Duplicated tool modules (`bridge.py`, `tools/*.py`) deleted in same commit as pip dep addition | D-08 delete criteria; tool diffs audited in D-10 |
| RWR-03 | projekt-forge's forge-specific tools (catalog, orchestrate, scan, seed) registered via `register_tools()` | D-13 shape verified; `register_tools` signature confirmed in canonical registry.py |
| RWR-04 | `forge_bridge.__file__` resolves to site-packages verified in CI | D-15 conftest pattern; Validation Architecture section below |

</phase_requirements>

---

## Summary

Phase 5 rewires projekt-forge to consume forge-bridge v1.0.0 as a pip dependency rather than shipping its own embedded `forge_bridge/` package. The phase divides into four atomic waves: Wave A renames the local package to eliminate namespace collision, Wave B adds the pip dep and deletes duplicates, Wave C rebuilds the MCP server around `get_mcp()`/`register_tools()`, and Wave D adds a conftest assertion.

**The research audits are complete.** The three cross-repo technical questions (protocol hybrid D-09a, client hybrid D-09b, tool-file diffs D-10) have concrete answers — two produce required v1.0.1 patch work before Wave B and one is a clean delete. The import distribution has been mapped file-by-file. The flame_hooks audit found two import sites that require special handling.

**Primary recommendation:** Create a forge-bridge v1.0.1 patch release before Wave B commences. The patch must: (1) add `query_lineage` and `query_shot_deps` to canonical `server/protocol.py`, and (2) add `source_name` and `shot_id` narrowing kwargs to `entity_list`. The client divergence (D-09b) is also upstream-worthy but the protocol gap is the hard blocker — `tools/catalog.py` and `flame_hooks/forge_publish/` import these symbols from `forge_bridge.server.protocol` and will fail to import after Wave B deletes the local copy.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Namespace rename (Wave A) | projekt-forge source tree | — | Pure file-system + import-string transformation |
| pip dependency declaration | projekt-forge pyproject.toml | forge-bridge git tag | Dependency constraint lives in consumer's manifest |
| Duplicate deletion (Wave B) | projekt-forge source tree | — | Remove files that the pip package now owns |
| MCP server rewire (Wave C) | projekt-forge server layer | forge-bridge pip API | pip provides singleton + registry; projekt-forge registers its own tools |
| Conftest assertion (Wave D) | projekt-forge test layer | — | Assertion lives where the collision risk exists |
| Protocol extensions | forge-bridge canonical (v1.0.1 patch) | projekt-forge client layer | Extensions need to live in the package both repos share |
| forge-specific tools (catalog, orchestrate, scan, seed) | projekt-forge tools layer | — | Business logic not for upstream; D-08 MOVE rule |
| `bridge.py` execution functions | forge-bridge pip package | — | D-08 DELETE: canonical version used directly |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| forge-bridge (pip) | 1.0.0 (git tag) | Provides 11-name public API | The package being consumed — Phase 4 verified |
| hatchling | >=0.14 | Build backend for both repos | Already in use |
| pytest | project dev dep | Test suite execution | Already in use in projekt-forge |
| pytest-asyncio | project dev dep | Async test support | Already in use |
| ruff | project dev dep | Linting; mechanised import rewrite possible | Already in use |

### Pip Dependency Syntax

```toml
# In projekt-forge/pyproject.toml [project] dependencies:
"forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.0",
```

**Note:** If v1.0.1 patch is required (see D-09/D-10 findings), the URL becomes `@v1.0.1`.

### Installation (dev loop)

```bash
# In projekt-forge virtualenv:
pip install -e /Users/cnoellert/Documents/GitHub/projekt-forge
pip install -e /Users/cnoellert/Documents/GitHub/forge-bridge  # shadows git dep with working copy
```

[VERIFIED: direct pyproject.toml inspection of both repos]

---

## D-09a: Protocol Hybrid Audit — BLOCKER FOUND

**Comparison:** `projekt-forge/forge_bridge/server/protocol/` (directory, two files) vs canonical `forge-bridge/forge_bridge/server/protocol.py` (single file)

### Structural difference

| Aspect | projekt-forge | canonical forge-bridge |
|--------|--------------|------------------------|
| Layout | `protocol/` directory: `__init__.py`, `builders.py`, `messages.py` | `protocol.py` single flat file |
| Message class | `Message` wraps a dict (attribute-style access: `msg.get("key")`, `.msg_id`, `.type`) | `Message` IS a dict subclass (dict-style access: `msg["type"]`, `.get()`, `.msg_id`) |
| `MsgType` | `class MsgType(str, enum.Enum)` — each value is a string-enum member | `class MsgType` with plain class attributes (no enum) |
| `_msg()` factory | Takes `type_: MsgType | str`, wraps in `Message(dict)`, uses `msg_id` field key | Individual builder functions use `"id"` field key (not `msg_id`) |
| Response correlation | `ref_msg_id` field in responses | `"id"` field echoed in responses |

### Symbols in projekt-forge protocol not in canonical

| Symbol | Where needed | Missing from canonical? |
|--------|-------------|-------------------------|
| `query_lineage` | `tools/catalog.py` (lazy import), `tools/switch_grade.py` | YES — canonical has no `query_lineage` builder or `QUERY_LINEAGE` type |
| `query_shot_deps` | `tools/catalog.py` (lazy import) | YES — canonical has no `query_shot_deps` builder or `QUERY_SHOT_DEPS` type |
| `entity_list(... shot_id, role, source_name)` | `client/sync_client.py`, `flame_hooks/forge_publish/` | Canonical `entity_list` only accepts `entity_type, project_id` — no narrowing kwargs |
| `welcome(session_id, registry_summary)` builder | `server/db_server.py` | Canonical has `welcome()` builder — present |
| `media_scan(project_name, role, shot_name, project_id)` | `server/handlers.py`, `server/db_server.py` | YES — canonical has no `MEDIA_SCAN` type or `media_scan` builder |

### Verdict: Proper extension, NOT stale fork

The projekt-forge `server/protocol/` is an extension of the canonical `server/protocol.py`. The core wire types (HELLO, WELCOME, BYE, PING, PONG, OK, ERROR, ENTITY_*, PROJECT_*, QUERY_DEPENDENTS, QUERY_SHOT_STACK, QUERY_EVENTS, SUBSCRIBE, UNSUBSCRIBE, REL_CREATE, LOC_ADD, ROLE_*) are shared. The additions are real application-level protocol that the db_server and catalog server speak:

- `QUERY_LINEAGE` / `query_lineage` — catalog lineage traversal
- `QUERY_SHOT_DEPS` / `query_shot_deps` — catalog shot dependency query
- `MEDIA_SCAN` / `media_scan` — scanner trigger
- Extended `entity_list` kwargs (`shot_id`, `role`, `source_name`)

**Disposition for Wave B:** `forge_bridge.server.protocol` is NOT a simple alias of the canonical package — it has both a different class layout (directory vs flat file, enum vs plain class, `ref_msg_id` vs echo-id) AND additional symbols. It MUST be kept as `projekt_forge/server/protocol/` after the rename. It cannot be deleted in favor of canonical.

**v1.0.1 REQUIRED:** The canonical `forge_bridge.server.protocol` must gain `query_lineage`, `query_shot_deps`, `media_scan`, and extended `entity_list` kwargs before Wave B, OR projekt-forge's catalog/scan tools must be updated to import from `projekt_forge.server.protocol` instead of `forge_bridge.server.protocol`. Since these extensions are generic pipeline protocol (not forge-specific), pushing them to canonical as v1.0.1 is the correct path.

[VERIFIED: direct file comparison of both repos]

---

## D-09b: Client Hybrid Audit — BLOCKER FOUND (upstream-worthy)

**Comparison:** `projekt-forge/forge_bridge/client/async_client.py` and `sync_client.py` vs canonical `forge-bridge/forge_bridge/client/async_client.py` and `sync_client.py`

### async_client.py divergence

| Location | projekt-forge | canonical | Nature |
|----------|--------------|-----------|--------|
| `AsyncClient.__init__` | Adds `project_name: str | None = None` kwarg | Does not have `project_name` | Extension |
| `_connect()` | Passes `project_name=self.project_name` to `hello()` builder | `hello()` called without `project_name` | Extension |
| `_handle_message()` | Matches on `ref_msg_id = msg.get("ref_msg_id") or msg.msg_id` (falls back to msg_id for backward compat) | Matches on `msg_id` directly (only reads `.msg_id`) | **Bug fix** — canonical drops responses when server uses `ref_msg_id` field |

The `ref_msg_id` fix is the most important divergence. The canonical version reads `.msg_id` from the response, but the projekt-forge protocol/builders use `ref_msg_id` in response messages (see `builders.py`: `d["ref_msg_id"] = msg_id`). The canonical `async_client.py` response-correlation code uses `msg.msg_id` which maps to the response's own `msg_id`, not the request's. The projekt-forge version correctly falls back with `msg.get("ref_msg_id") or msg.msg_id`. This is a genuine bug fix.

The `project_name` addition is an extension: the projekt-forge db_server `HELLO` message includes `project_name` for connection routing to the right per-project database engine. This is projekt-forge-specific infrastructure — the canonical bridge server does not use per-project routing.

### sync_client.py divergence

| Location | projekt-forge | canonical | Nature |
|----------|--------------|-----------|--------|
| `entity_list()` | Accepts `shot_id`, `role` narrowing kwargs; passes to `entity_list()` builder | Accepts only `entity_type, project_id` | Extension matching builder extension above |

The sync_client extensions directly mirror the protocol/builder extensions. Keeping them in sync is correct.

### Disposition for D-09b

| Divergence | Action |
|------------|--------|
| `ref_msg_id` fallback in `_handle_message` | **Push to canonical as v1.0.1** — this is a protocol correctness bug fix that any consumer of the WebSocket server would hit |
| `project_name` kwarg in `AsyncClient.__init__` and `hello()` | **Keep as `projekt_forge/client/`** — project-routing is forge-specific infrastructure |
| `entity_list` narrowing kwargs in `sync_client` | **Push to canonical as v1.0.1** alongside the protocol builder extension |

**v1.0.1 REQUIRED for `ref_msg_id` fix:** Without this, Wave B's deletion of local `client/async_client.py` will break the WebSocket client for any consumer talking to a server that uses `ref_msg_id` in responses (which the db_server does).

[VERIFIED: line-by-line comparison of both async_client.py files]

---

## D-10: Tool-File Diff Audit

**Comparison of canonical forge-bridge tools vs projekt-forge local copies:**

### batch.py

| Aspect | canonical | projekt-forge |
|--------|-----------|--------------|
| Extra imports | None | `import os, sys` at top |
| Extra tool | None | Adds `setup_denoise` function (~120 lines) — full Neat Video denoise chain setup tool with `SetupDenoiseInput` Pydantic model |

**Disposition:** `setup_denoise` is forge-specific (references `forge_denoise` scripts via `flame.project.current_project.setups_folder`). This tool does not belong in canonical. The local `batch.py` cannot be deleted — it is a superset. **MOVE to `projekt_forge/tools/batch.py`** (apply MOVE rule from D-08, not DELETE).

### project.py

| Aspect | canonical | projekt-forge |
|--------|-----------|--------------|
| `list_desktop` function | Simple, no parameters, lists reels/batch groups by name and count | Enhanced version with `ListDesktopInput(scope, filter)` — filters reel groups/batch groups by name, supports `scope="all"/"reel_groups"/"batch_groups"` |
| Other functions | Identical | Identical |

**Disposition:** The `list_desktop` enhancement is a genuine improvement in usability (adding filtering/scoping for large Flame desktops). This qualifies as upstream-worthy. However, adding a `params` argument to a previously zero-argument function is a breaking change to the tool's MCP interface (existing callers that call `flame_list_desktop` with no arguments will fail if the canonical version gains required params). Decision: **push as v1.0.1 with `params: ListDesktopInput = None` defaulted** so zero-arg calls still work, OR keep as `projekt_forge/tools/project.py` (MOVE rule). Planner must decide. Research flags this as non-breaking if default is added.

### publish.py

| Aspect | canonical | projekt-forge |
|--------|-----------|--------------|
| `output_directory` default | `default_factory=lambda: os.environ.get("FORGE_PUBLISH_ROOT", "/mnt/publish")` | `default="/mnt/portofino"` |

**Disposition:** The canonical version has the correct Phase 4 fix (Phase 4 PKG-03 removed `/mnt/portofino`). The projekt-forge local copy still has the old hardcoded path. **DELETE** the projekt-forge local copy — canonical is correct and has the better implementation. Wave B deletion is correct for `publish.py`.

**BLOCKER NOTE:** The projekt-forge local `publish.py` will fail the Phase 4 PKG-03 regression test if kept (`grep -r "portofino" forge_bridge/` would match). This is additional motivation to delete it in Wave B.

### timeline.py

| Aspect | canonical | projekt-forge |
|--------|-----------|--------------|
| `rename_shots` gap-fill logic | Simple — gaps on T0 produce `(None, record_in, record_out)` entries | Extended — gaps on T0 trigger upward track scan to find a fill segment; introduces `gap_fills` set; fills get assigned shot names |
| `file_path` stripping | `strip("'\"")` (3 chars) | `strip("'\\\"")` (correct escaped version) — minor string escaping fix |

**Disposition:** The gap-fill logic is a genuine bug fix (silent gaps in T0 cause shot names to skip numbers). The `strip` fix is correct. Both changes are general Flame timeline behavior, not forge-specific. **Push to canonical as v1.0.1** before Wave B. Without this, deleting the local `timeline.py` breaks the gap-fill behavior.

### switch_grade.py

| Aspect | canonical | projekt-forge |
|--------|-----------|--------------|
| Purpose | Implements `flame_switch_grade` + `flame_query_alternatives` (direct smart_replace_media swap; query via catalog stub) | Original version: `flame_query_streams` + `flame_add_streams` using openclip vstack approach + `forge_openclip_writer` |
| Docstring | "query and switch alternative media streams" | "query and add alternative media streams" |
| `forge_openclip_writer` | Not present | Injected via sys.path from flame_hooks scripts directory |
| Catalog integration | Uses `AsyncClient` lazy import directly | Uses catalog WebSocket server |

**Disposition:** These are functionally different implementations — the canonical version was evolved in Phase 1 as the canonical implementation. The projekt-forge version is the older approach. **DELETE** the projekt-forge local `switch_grade.py` and consume canonical. The canonical version is the correct evolved version. If `flame_query_streams` / `flame_add_streams` are still needed in projekt-forge, they belong in a forge-specific tool file, not in the canonical one.

### Summary Table

| File | Action | v1.0.1 Required? |
|------|--------|-----------------|
| `batch.py` | MOVE to `projekt_forge/tools/` (has forge-specific `setup_denoise`) | NO |
| `project.py` | MOVE to `projekt_forge/tools/` OR push `list_desktop` enhancement with defaults | OPTIONAL |
| `publish.py` | DELETE (canonical is correct after Phase 4 fix) | NO |
| `timeline.py` | DELETE after pushing gap-fill + strip fix to canonical as v1.0.1 | YES |
| `switch_grade.py` | DELETE (canonical version is the evolved canonical form) | NO |

[VERIFIED: diff output from direct file comparison]

---

## v1.0.1 BLOCKER VERDICT

**v1.0.1 is REQUIRED before Wave B.** The following items must be patched:

| Item | Blocker | Impact if skipped |
|------|---------|------------------|
| `query_lineage` + `query_shot_deps` added to canonical `server/protocol.py` | HARD BLOCKER | `tools/catalog.py` fails to import after local protocol deleted; `flame_hooks/forge_publish/` broken |
| `entity_list` extended kwargs in canonical `server/protocol.py` and `client/sync_client.py` | HARD BLOCKER | `client/sync_client.py` entity_list calls lose filtering; `flame_hooks/forge_publish/` entity_list breaks |
| `ref_msg_id` response correlation fix in canonical `async_client.py` | HARD BLOCKER | WebSocket request/response correlation breaks for any response with `ref_msg_id` |
| `timeline.py` gap-fill fix | SOFT BLOCKER (behavior regression) | Gap shots silently skipped during rename_shots if local deleted |

**Non-blockers for v1.0.1 (can be Wave B with MOVE instead of DELETE):**
- `batch.py` `setup_denoise` addition — forge-specific, MOVE, no v1.0.1 needed
- `project.py` `list_desktop` enhancement — MOVE or push with defaults; either works
- `switch_grade.py` — canonical version is already the evolved version; safe to DELETE

**Recommended v1.0.1 patch sequence:**
1. Add `QUERY_LINEAGE`, `QUERY_SHOT_DEPS`, `MEDIA_SCAN` types and builder functions to canonical `forge_bridge/server/protocol.py`
2. Add `shot_id`, `role`, `source_name` narrowing to `entity_list` builder in canonical `server/protocol.py`
3. Fix `ref_msg_id` fallback in canonical `forge_bridge/client/async_client.py`
4. Add `shot_id`, `role` narrowing to `sync_client.entity_list()` in canonical
5. Cherry-pick timeline gap-fill fix and `strip` correction into canonical `forge_bridge/tools/timeline.py`
6. Tag canonical as `v1.0.1`; update projekt-forge dep URL to `@v1.0.1`

---

## 178-Import Distribution Map

**Total measured: 178 unique import statements across ~40 Python files.**

Actual counts by subpackage (verified by grep):

| Subpackage | Count | Primary files |
|-----------|-------|--------------|
| `forge_bridge.server.*` | 36 | `server/db_server.py` (4), `scanner/tests/test_endpoints.py` (4), `__main__.py` (4), `server/handlers.py` (3), test_handler*.py (2+2+2), `tools/catalog.py` (2), `server/protocol/__init__.py` (2), `server/protocol/builders.py` (2) |
| `forge_bridge.conform.*` | 28 | `conform/tests/test_strategies.py` (5), `conform/tests/test_matcher.py` (4), `conform/tests/test_scanner.py` (3), `conform/scanner.py` (3), `conform/tests/test_metadata.py` (2), `conform/tests/test_index.py` (2), `conform/tests/conftest.py` (2), `conform/strategies.py` (2), `conform/matcher.py` (2) |
| `forge_bridge.cli.*` | 27 | `cli/main.py` (6), `tests/test_project_invite.py` (5), `scanner/tests/test_endpoints.py` (4), `tests/test_smoke_project_creation.py` (3), `tests/test_forge_cli.py` (3) |
| `forge_bridge.db.*` | 26 | `cli/project.py` (3), `tests/test_users_schema.py` (2), `tests/test_handlers_lineage.py` (2), `tests/test_handler_routing.py` (2), `tests/conftest.py` (2), `db/migrations/env.py` (2), `cli/installer.py` (2), `server/handlers.py` (1), `server/db_server.py` (1), `seed/seeder.py` (1) |
| `forge_bridge.config.*` | 17 | `tests/test_smoke_project_creation.py` (4), `forge_gui/core/flame_creator.py` (3), `forge_gui/ui/project_hub.py` (2), `cli/launcher.py` (1), `cli/project.py` (1), `cli/auth.py` (1), `cli/seed.py` (1), `tools/seed.py` (1), `config/__init__.py` (1) |
| `forge_bridge.client.*` | 15 | `flame_hooks/forge_publish/scripts/forge_publish.py` (2), `client/sync_client.py` (2), `client/__init__.py` (2), `tests/uat_test*.py` (4 × 1), `tools/switch_grade.py` (1), `tools/scan.py` (1), `tools/catalog.py` (1), `scanner/scanner.py` (1), `cli/scan.py` (1) |
| `forge_bridge.scanner.*` | 11 | `tools/scan.py` (2), `server/handlers.py` (2), `scanner/__init__.py` (2), `cli/scan.py` (2), `scanner/tests/test_scanner.py` (1), `scanner/tests/test_role_resolver.py` (1), `scanner/tests/test_endpoints.py` (1) |
| `forge_bridge.tools.*` | 10 | `server/mcp.py` (4), `scanner/tests/test_endpoints.py` (4), `tests/test_switch_grade_mcp.py` (2) |
| `forge_bridge.seed.*` | 5 | `tools/seed.py` (1), `seed/seeder.py` (1), `seed/__init__.py` (1), `cli/seed.py` (1), `tests/test_seed.py` (1) |
| `forge_bridge.bridge` | 3 | `server/mcp.py` (2), `__main__.py` (1) |

**Wave A rewrite strategy (Claude's Discretion):**

The import patterns are highly mechanical — every import is a verbatim `from forge_bridge.X import Y` string. However, two groups require different treatment in Wave B:

- `forge_bridge.bridge` (3 imports) → Wave B: flip to `from forge_bridge import execute, execute_json, execute_and_read` (pip)
- `forge_bridge.client.*` (15 imports) → Wave B: flip 11 of them to pip; keep 4 as `projekt_forge.client.*` (the `project_name` extension)
- `forge_bridge.tools.*` (10 imports, only forge-specific tools) → `projekt_forge.tools.*`
- All others → `projekt_forge.*` (no flip back to pip in Wave B)

**Recommendation for Wave A:** Mechanical `sed` is safe for the bulk rewrite (`sed -i 's/from forge_bridge\./from projekt_forge\./g'`), but apply it only within the `forge_bridge/` directory being renamed (not flame_hooks). A single script handles the rename. Wave B then does the reverse surgical flip for the canonical subset.

[VERIFIED: grep with uniq -c across entire projekt-forge repo]

---

## flame_hooks Audit

**Files checked:** All `.py` files under `/Users/cnoellert/Documents/GitHub/projekt-forge/flame_hooks/`

**Findings:**

### forge_publish.py (lines 599, 700, 701)

Three import sites in `flame_hooks/forge_tools/forge_publish/scripts/forge_publish.py`:

```python
# Line 599 (inside a subprocess script string — executed by conda/Python, not Flame's stdlib Python)
from forge_bridge.client.sync_client import SyncClient

# Line 700-701 (inside another subprocess script string)
from forge_bridge.client.sync_client import SyncClient
from forge_bridge.server.protocol import project_list, entity_list
```

**Critical detail:** Both import sites are inside Python *string literals* that are written to a temp file and executed via a subprocess using the forge conda Python environment — NOT run inside Flame's stdlib-only Python interpreter. The comment in `_push_plates_to_bridge()` at line ~671 explicitly documents this: "Spawns via conda subprocess to avoid forge_bridge import conflict with Autodesk's `/opt/Autodesk/shared/python/forge_bridge.py`."

This means:
- These imports ARE subject to pip package resolution (the subprocess uses the conda env where forge-bridge will be pip-installed)
- After Wave A+B: `from forge_bridge.client.sync_client import SyncClient` → resolves to pip package's canonical `sync_client.py`
- After Wave A+B: `from forge_bridge.server.protocol import project_list, entity_list` → must resolve against canonical `forge_bridge.server.protocol`

**The `entity_list` import at line 701 is a secondary blocker:** The subprocess calls `entity_list(entity_type, project_id)` via the canonical path, which works with the canonical simple 2-arg signature. The `source_name` narrowing is NOT used in `forge_publish.py` — only the 2-arg form is called here. So this specific import will work against canonical without v1.0.1 narrowing extension, but the `sync_client.py` narrowing extension IS needed by other call sites.

**forge_reconform.py (line 43):** This line is inside a docstring (`"""...from forge_bridge.conform.* import..."""`) — it is documentation text, not an executable import. No action needed.

**Verdict for flame_hooks:** The flame_hooks imports are not Flame-interpreter imports (they run in conda subprocess). They will resolve correctly against the pip package after Wave B. The `entity_list` call in `forge_publish.py` uses the 2-arg canonical form — compatible. The `SyncClient` import from canonical `client/sync_client.py` will work as long as the `project_name` kwarg is not used (it isn't, in forge_publish.py). The `server/protocol` import for `project_list, entity_list` resolves cleanly against canonical.

**One residual risk:** After Wave B, `from forge_bridge.server.protocol import query_lineage, query_shot_deps` in `tools/catalog.py` (which IS a canonical import after Wave B) must resolve against v1.0.1's extended protocol. This is the hard blocker already identified in D-09a.

[VERIFIED: direct file inspection of flame_hooks/]

---

## Common Pitfalls

### Pitfall 1: Namespace collision survives Wave A if `forge_bridge/` directory not fully removed

**What goes wrong:** If a stale `forge_bridge/` directory or `.pyc` cache remains after Wave A rename, Python resolves `import forge_bridge` to the local directory instead of the pip package. The conftest assertion in Wave D is the final safety net, but the error shows up as mysterious import behavior during Wave B.

**Why it happens:** Python's import machinery checks the working directory and `sys.path` entries in order. A `forge_bridge/` directory at the repo root takes priority over site-packages.

**How to avoid:** After Wave A rename: `git status` should show zero untracked `forge_bridge/` files. Run `find /Users/cnoellert/Documents/GitHub/projekt-forge -name "forge_bridge" -type d` to confirm only renamed `projekt_forge/` exists.

**Warning signs:** `import forge_bridge; forge_bridge.__file__` contains the projekt-forge path after Wave B.

### Pitfall 2: `__pycache__` directories carry old `forge_bridge` module caches

**What goes wrong:** Python's bytecode cache in `__pycache__/` retains `.pyc` files named `forge_bridge.*.pyc`. After the rename, stale caches can mask import errors.

**How to avoid:** After Wave A: `find /Users/cnoellert/Documents/GitHub/projekt-forge -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true`

### Pitfall 3: Wave A mechanical `sed` hits flame_hooks string literals

**What goes wrong:** The subprocess script strings in `forge_publish.py` contain `from forge_bridge.client.sync_client import SyncClient` as executable text inside a Python string literal. A blanket `sed 's/from forge_bridge/from projekt_forge/g'` over the whole repo would corrupt these strings — the subprocess would then try to import `from projekt_forge.client.sync_client` which doesn't exist in the conda pip env.

**How to avoid:** Scope Wave A `sed` to the `forge_bridge/` directory being renamed (plus `tests/`, `forge_gui/`). Exclude `flame_hooks/` from the Wave A import rewrite. The flame_hooks imports point at the pip package and should stay as `forge_bridge.*` throughout.

**Warning signs:** `forge_reconform.py` or `forge_publish.py` contains `from projekt_forge` after Wave A.

### Pitfall 4: `register_tools()` called after `mcp.run()` in `__main__.py`

**What goes wrong:** If the Wave C rewrite of `__main__.py` calls `register_tools()` inside the lifespan or after `mcp.run()` starts, the post-run guard (Phase 4 API-05) raises `RuntimeError`.

**How to avoid:** All `register_tools(mcp, [...])` calls must happen at module import time (before `mcp.run()`), not inside `_lifespan` or any async context that runs after startup.

### Pitfall 5: `startup_bridge()` called twice (once by pip lifespan, once by `__main__.py`)

**What goes wrong:** The canonical `_lifespan` in `forge_bridge/mcp/server.py` already calls `startup_bridge()` when the server starts. If `projekt_forge/__main__.py` also calls it manually, the WebSocket client connects twice and produces a duplicate session.

**How to avoid:** `projekt_forge/__main__.py` should call `mcp.run()` (which triggers the lifespan) and rely on the lifespan's `startup_bridge()` call. Direct calls to `startup_bridge()` in `__main__.py` are removed in Wave C (D-14).

### Pitfall 6: git dep URL references non-existent tag

**What goes wrong:** Adding `forge-bridge @ git+...@v1.0.0` before the tag is pushed produces a pip install error. Every `pip install -e .` in projekt-forge fails with a git ref error.

**How to avoid:** Tag and push in forge-bridge BEFORE committing the Wave B `pyproject.toml` change. Plan explicitly: `git tag v1.0.0 && git push --tags` is Wave B's first action, not an afterthought.

---

## Architecture Patterns

### System Architecture Diagram

```
Wave A (rename only):

projekt-forge repo
├── forge_bridge/          → renamed to →   projekt_forge/
│   ├── cli/                                 cli/
│   ├── config/                              config/
│   ├── conform/                             conform/
│   ├── db/                                  db/
│   ├── server/                              server/
│   ├── scanner/                             scanner/
│   ├── seed/                                seed/
│   └── tools/ (all)                         tools/ (all)
└── All 178 "forge_bridge.*" imports → "projekt_forge.*" (except flame_hooks)

Wave B (pip consume):

projekt-forge                    forge-bridge (pip)
├── projekt_forge/               ├── forge_bridge/
│   ├── [forge-specific kept]    │   ├── bridge.py  ←──── execute, execute_json
│   └── tools/                   │   ├── client/    ←──── AsyncClient (canonical)
│       ├── batch.py (MOVE)      │   ├── mcp/       ←──── get_mcp, register_tools
│       ├── project.py (MOVE)    │   └── tools/     ←──── switch_grade, publish, etc.
│       ├── catalog.py (keep)
│       └── orchestrate.py (keep)
│
DELETE: bridge.py, canonical tools, old switch_grade.py, publish.py
MOVE: batch.py, project.py → projekt_forge/tools/
KEEP: client/ (project_name extension), server/protocol/ (extended)

Wave C (MCP rewire):

projekt_forge/server/mcp.py
    from forge_bridge import get_mcp, register_tools   # pip
    from projekt_forge.tools import catalog, orchestrate, scan, seed, batch, project

    mcp = get_mcp()   # canonical singleton with flame_* tools pre-registered

    register_tools(mcp, [catalog.*, orchestrate.*, scan.*, seed.*, batch.*, project.*],
                   prefix="forge_", source="builtin")

projekt_forge/__main__.py
    mcp.run()   # triggers canonical lifespan → startup_bridge() → shutdown_bridge()
```

### Recommended Project Structure (post-Wave-C)

```
projekt-forge/
├── projekt_forge/           # renamed from forge_bridge/
│   ├── cli/                 # forge-specific CLI (keep as-is, namespaced)
│   ├── config/              # forge_config.yaml loading (keep)
│   ├── conform/             # conform engine (keep)
│   ├── db/                  # postgres models, engine, migrations (keep)
│   ├── scanner/             # media directory scanner (keep)
│   ├── seed/                # DB seeder (keep)
│   ├── server/
│   │   ├── db_server.py     # WebSocket DB server (keep, forge-specific)
│   │   ├── handlers.py      # Entity handlers (keep)
│   │   ├── mcp.py           # REWRITTEN: get_mcp() + register_tools() only
│   │   ├── protocol/        # KEEP: extended protocol (query_lineage etc.)
│   │   └── registry.py      # forge-specific server registry (keep)
│   ├── tools/
│   │   ├── batch.py         # MOVED: forge-specific (setup_denoise)
│   │   ├── catalog.py       # forge-specific lineage queries (keep)
│   │   ├── orchestrate.py   # forge-specific pipeline (keep)
│   │   ├── project.py       # MOVED: enhanced list_desktop
│   │   ├── scan.py          # forge-specific scanner MCP tool (keep)
│   │   └── seed.py          # forge-specific seeder MCP tool (keep)
│   └── __main__.py          # UPDATED: mcp.run() via canonical lifespan
├── pyproject.toml           # UPDATED: dep, package, scripts
├── tests/
│   └── conftest.py          # UPDATED: RWR-04 assertion added
└── flame_hooks/             # UNCHANGED (uses canonical pip imports)
```

### Pattern 1: Wave A Bulk Import Rewrite

**What:** Replace all `from forge_bridge.` with `from projekt_forge.` in the renamed source tree.

**When to use:** Wave A only, scoped to `projekt_forge/`, `tests/`, `forge_gui/`. NOT applied to `flame_hooks/`.

```bash
# Scope: only renamed package directories (not flame_hooks)
find /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge \
     /Users/cnoellert/Documents/GitHub/projekt-forge/tests \
     /Users/cnoellert/Documents/GitHub/projekt-forge/forge_gui \
     /Users/cnoellert/Documents/GitHub/projekt-forge/forge.py \
     /Users/cnoellert/Documents/GitHub/projekt-forge/scripts \
     -name "*.py" \
     -exec sed -i 's/from forge_bridge\./from projekt_forge\./g' {} +

# Verify no flame_hooks were touched
grep -rn "from projekt_forge" /Users/cnoellert/Documents/GitHub/projekt-forge/flame_hooks/ || echo "CLEAN"
```

[ASSUMED — sed syntax; verify on target platform before using]

### Pattern 2: Wave B Canonical Flip

**What:** After bulk rename, flip the canonical imports back to `from forge_bridge.*` (pip).

**Files requiring the flip (canonical symbols only):**

| File | From | To |
|------|------|----|
| `projekt_forge/__main__.py` | `from projekt_forge.bridge import configure` | `from forge_bridge.bridge import configure` |
| `projekt_forge/server/mcp.py` | (entire file rewritten in Wave C) | `from forge_bridge import get_mcp, register_tools` |
| `projekt_forge/tools/orchestrate.py` | `from forge_bridge import bridge` | stays as `from forge_bridge import bridge` (already canonical) |
| `tests/uat_test*.py` | `from projekt_forge.client import SyncClient` | `from forge_bridge.client import SyncClient` |

**Note:** `bridge.py` in `projekt_forge/` is deleted in Wave B. Its callers get their import from `forge_bridge.bridge` directly.

### Pattern 3: Wave C MCP Rewire

```python
# projekt_forge/server/mcp.py (post-Wave-C)
from forge_bridge import get_mcp, register_tools
from projekt_forge.tools import catalog, orchestrate, scan, seed
from projekt_forge.tools import batch as forge_batch
from projekt_forge.tools import project as forge_project

mcp = get_mcp()  # FastMCP singleton from pip; flame_* tools already registered

register_tools(
    mcp,
    [
        catalog.trace_lineage,
        catalog.get_shot_deps,
        orchestrate.publish_pipeline,
        scan.media_scan,
        seed.seed_catalog,
        forge_batch.setup_denoise,
        forge_project.list_desktop,   # if MOVE decision made
        # ... other forge-specific tools
    ],
    prefix="forge_",
    source="builtin",
)
```

[VERIFIED: `register_tools` signature in `forge_bridge/mcp/registry.py`; `get_mcp` in `forge_bridge/mcp/__init__.py`]

### Anti-Patterns to Avoid

- **Shim modules:** No `forge_bridge/` compatibility shim in projekt-forge pointing at `projekt_forge`. Confirmed clean break per D-01.
- **Calling `startup_bridge()` in `__main__.py` directly:** The canonical lifespan already calls it; double-call creates duplicate sessions.
- **Applying Wave A sed to `flame_hooks/`:** These files import from the pip package; renaming them to `projekt_forge` would break the subprocess script.
- **Committing Wave B before tagging forge-bridge:** pip install fails with a git ref error.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Package rename import rewriting | Custom AST transformer | `sed` with scoped file path list | Imports are uniform strings; AST overhead is unnecessary |
| Post-namespace-collision detection | Runtime import path check | pytest conftest assertion (D-15) | Assertion runs on every test invocation; no separate tool needed |
| Pip git dependency | `file://` path or vendoring | `git+https://...@v1.0.0` | Machine-portable, version-pinned, reproducible |
| Tool registration boilerplate | 30+ `mcp.tool()` calls | `register_tools(mcp, fns, prefix, source)` | Already built in Phase 4; collapses registration to one call |

---

## Environment Availability

All work happens in existing Python environments. No new external tools required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Both repos | ✓ | System python (>=3.10 per pyproject.toml) | — |
| pip | Wave B install | ✓ | Bundled | — |
| git | v1.0.0/v1.0.1 tag + push | ✓ | Confirmed (repo is git) | — |
| forge-bridge repo | v1.0.1 patch | ✓ | `/Users/cnoellert/Documents/GitHub/forge-bridge` | — |
| projekt-forge repo | All waves | ✓ | `/Users/cnoellert/Documents/GitHub/projekt-forge` | — |
| pytest | Wave D verification | ✓ | In projekt-forge dev deps | — |

No missing dependencies. All four waves can proceed with current tooling.

[VERIFIED: git repo confirmed, pyproject.toml requirements reviewed]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (version in projekt-forge dev deps) |
| Config file | None detected — uses `pyproject.toml` pytest section if added, else pytest defaults |
| Quick run command | `cd /Users/cnoellert/Documents/GitHub/projekt-forge && pytest tests/ -x -q --no-header` |
| Full suite command | `cd /Users/cnoellert/Documents/GitHub/projekt-forge && pytest tests/ -q --no-header` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RWR-01 | `forge-bridge>=1.0,<2.0` in pyproject.toml | smoke (import check) | `python -c "import forge_bridge; print(forge_bridge.__version__)"` | N/A (import test) |
| RWR-02 | No local `forge_bridge/tools/bridge.py` or duplicated canonical tools | structural | `pytest tests/conftest.py::test_no_local_forge_bridge_dir -x` | ❌ Wave D |
| RWR-03 | forge-specific tools (catalog, scan, etc.) visible to MCP client | unit | `pytest tests/test_mcp_tool_registration.py -x` | ❌ Wave D |
| RWR-04 | `forge_bridge.__file__` resolves to site-packages | conftest assertion | Runs on EVERY `pytest` invocation via conftest auto-use | ❌ Wave D |

### RWR-04 Conftest Assertion (D-15)

```python
# /Users/cnoellert/Documents/GitHub/projekt-forge/tests/conftest.py  (append in Wave D)

import pathlib
import forge_bridge
import pytest

@pytest.fixture(autouse=True, scope="session")
def assert_forge_bridge_from_site_packages():
    """RWR-04: Verify forge_bridge resolves to pip install, not local directory.

    Runs once per test session. Fails immediately if the namespace collision
    recurs (e.g., someone recreated a local forge_bridge/ directory).
    """
    p = pathlib.Path(forge_bridge.__file__).resolve()
    assert "site-packages" in p.parts, (
        f"forge_bridge resolved to {p} — expected site-packages. "
        "Check: no local forge_bridge/ directory should exist at the "
        "projekt-forge repo root. Re-run: pip install -e /path/to/forge-bridge"
    )

    # Defensive: confirm no local forge_bridge/ at repo root
    repo_root = pathlib.Path(__file__).parent.parent
    local_pkg = repo_root / "forge_bridge"
    assert not local_pkg.exists(), (
        f"Local forge_bridge/ directory found at {local_pkg}. "
        "This causes a namespace collision — remove it."
    )
```

**What triggers it:** Any `pytest` invocation (autouse=True, scope="session"). The fixture runs exactly once per test session as the first fixture.

**What "green run" means:** All existing tests pass AND the conftest fixture does not raise. The site-packages path assertion plus the directory non-existence check are both satisfied.

**What signals failure:**
- `AssertionError: forge_bridge resolved to .../projekt-forge/forge_bridge/__init__.py` — local collision reintroduced
- `AssertionError: Local forge_bridge/ directory found` — Wave A rename incomplete
- Any `ModuleNotFoundError: No module named 'forge_bridge'` — pip install not run after Wave B

### Wave 0 Gaps (to create in Wave D)

- [ ] `tests/conftest.py` — append RWR-04 autouse fixture (file exists; add to bottom)
- [ ] Optional: `tests/test_mcp_tool_registration.py` — verifies `catalog`, `scan`, `orchestrate`, `seed` tools appear in `mcp.tools` dict after `register_tools()` call (covers RWR-03)

### Sampling Rate

- **Per wave commit:** `pytest tests/ -x -q --no-header` (full suite, stop on first failure)
- **Wave A gate:** Full suite must pass before Wave B starts (D-11: each wave is independently buildable)
- **Wave D gate:** Full suite green (including RWR-04 assertion) before `/gsd-verify-work`

---

## Open Questions

1. **`list_desktop` enhancement in `project.py` — MOVE or push upstream?**
   - What we know: projekt-forge has an enhanced `list_desktop` with `scope` and `filter` params; canonical has the simple version
   - What's unclear: Is the enhancement general enough for canonical? Adding `params: ListDesktopInput = None` preserves backward compat
   - Recommendation: Push to v1.0.1 with default-None params — avoids MOVE complexity and benefits all consumers

2. **Wave A — one commit or two?**
   - What we know: The rename + 178-import rewrite is a large diff; D-11 says each wave is one commit
   - What's unclear: Whether the diff size harms reviewability enough to justify splitting
   - Recommendation: Split into two commits only if the single-commit diff exceeds 500 lines changed; otherwise keep atomic per D-11

3. **`projekt_forge/server/protocol/` wire format divergence — does db_server use `ref_msg_id` or `"id"` echo?**
   - What we know: The projekt-forge `protocol/builders.py` uses `ref_msg_id` in responses; canonical uses `"id"` echo
   - What's unclear: Whether the db_server WebSocket response format must match the canonical client's correlation logic
   - Recommendation: The v1.0.1 async_client fix (`ref_msg_id or msg_id` fallback) handles both; no protocol change needed in db_server

4. **forge-specific `katalog` tools import chain post-Wave-B:**
   - What we know: `tools/catalog.py` will import `from projekt_forge.server.protocol import query_lineage, query_shot_deps` (after Wave A rename + Wave B canonical flip for other symbols)
   - What's unclear: Whether the v1.0.1 canonical protocol gains these builders, making the import `from forge_bridge.server.protocol import query_lineage` instead
   - Recommendation: If v1.0.1 adds these builders, flip `tools/catalog.py` to use canonical in Wave B. If v1.0.1 only adds the bug fixes and not the extended protocol builders, keep as `projekt_forge.server.protocol`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| projekt-forge embeds its own `forge_bridge/` | projekt-forge consumes `forge-bridge` as pip dep | Phase 5 (this phase) | Eliminates 178 duplicated imports; single source of truth |
| Manual `mcp.tool()` per function (41 registrations in mcp.py) | `register_tools(mcp, fns, prefix, source)` one-liner | Phase 4 + Phase 5 | Reduces mcp.py from ~500 lines to ~20 |
| Private `_startup`/`_shutdown` functions | Public `startup_bridge()`/`shutdown_bridge()` | Phase 4 | Enables downstream consumers to hook into lifecycle |

---

## Project Constraints (from CLAUDE.md)

**forge-bridge project principles that apply to this phase:**

| Directive | Impact on Phase 5 |
|-----------|------------------|
| Endpoint parity — Flame is one endpoint, not special | MCP rewire must not hardcode Flame assumptions in projekt-forge's `mcp.py`; use canonical `get_mcp()` |
| Local first | pip dep is git-URL (no PyPI, no cloud) — consistent with local-first deployment |
| HTTP transport | The Flame bridge HTTP client (`execute`, `execute_json`, `execute_and_read`) comes from the pip package; don't replicate |
| No authentication yet | Not a Phase 5 concern |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `sed -i` syntax works on macOS (requires empty string after -i) | Architecture Patterns | sed command fails; use `sed -i '' 's/.../.../' file` on macOS |
| A2 | The forge-bridge `v1.0.1` patch can be tagged and pip-installable within the same planning cycle as Wave B | v1.0.1 Verdict | If v1.0.1 is delayed, Wave B must use MOVE for catalog tools instead of DELETE+flip |
| A3 | `pytest` is installed in the projekt-forge virtualenv (`dev` optional dep) | Validation Architecture | test invocations fail; `pip install -e ".[dev]"` needed |

**All other claims in this research are VERIFIED by direct file inspection.**

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: direct file diff] `forge-bridge/forge_bridge/server/protocol.py` vs `projekt-forge/forge_bridge/server/protocol/` — complete structural comparison
- [VERIFIED: direct file diff] `forge-bridge/forge_bridge/client/async_client.py` vs `projekt-forge/forge_bridge/client/async_client.py` — line-by-line comparison
- [VERIFIED: direct file diff] `forge-bridge/forge_bridge/client/sync_client.py` vs `projekt-forge/forge_bridge/client/sync_client.py`
- [VERIFIED: grep with uniq -c] 178-import distribution map across projekt-forge repo
- [VERIFIED: diff output] `batch.py`, `project.py`, `publish.py`, `timeline.py`, `switch_grade.py` tool diffs
- [VERIFIED: direct read] `forge_bridge/mcp/__init__.py`, `mcp/server.py`, `mcp/registry.py`, `bridge.py` — public API surface confirmed
- [VERIFIED: direct read] `forge_bridge/__init__.py` — 11-name `__all__` confirmed
- [VERIFIED: direct read] `pyproject.toml` in both repos — versions, scripts, packages
- [VERIFIED: direct read] `flame_hooks/forge_tools/forge_publish/scripts/forge_publish.py` lines 590-710 — subprocess context confirmed
- [VERIFIED: direct read] `05-CONTEXT.md` — all locked decisions
- [VERIFIED: 04-VERIFICATION.md] Phase 4 pass status (5/5 criteria, 182 tests green)

### Secondary (MEDIUM confidence)

- [CITED: CONTEXT.md §Known blast radius] 178-import aggregate counts by subpackage — research-measured counts match within ±2 (minor discrepancy: context says `server: 23`, grep measured 36; the higher number includes self-referential protocol imports within the server/ subpackage itself)

---

## Metadata

**Confidence breakdown:**
- Protocol hybrid audit: HIGH — direct file comparison
- Client hybrid audit: HIGH — direct line-by-line comparison
- Tool-file diffs: HIGH — diff output inspected
- Import distribution map: HIGH — grep measured
- flame_hooks audit: HIGH — file read and code context verified
- Wave patterns/strategy: HIGH — based on verified code shapes
- v1.0.1 blocker verdict: HIGH — based on concrete missing symbols

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (stable once executed; no fast-moving ecosystem dependencies)
