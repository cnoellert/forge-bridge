# Phase 5: Import Rewiring — Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 9 (files modified or created across both repos)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File (absolute path) | Wave | Role | Data Flow | Closest Analog | Match Quality |
|-----------------------------------|------|------|-----------|----------------|---------------|
| `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` | A+B | config | transform | `/Users/cnoellert/Documents/GitHub/forge-bridge/pyproject.toml` | exact |
| `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/__main__.py` | C | utility | event-driven | `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/__main__.py` (current) | exact — in-place update |
| `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/server/mcp.py` | C | service | request-response | `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/mcp/server.py` | role-match — provides the singleton shape being adopted |
| `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/conftest.py` | D | test | transform | `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/conftest.py` (current) | exact — append-only |
| `/Users/cnoellert/Documents/GitHub/projekt-forge/CLAUDE.md` | A | config | — | `/Users/cnoellert/Documents/GitHub/forge-bridge/CLAUDE.md` | doc-pattern reference |
| All `projekt_forge/**/*.py` (Wave A bulk rename) | A | all | transform | `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/` (current tree) | exact — mechanical sed |
| `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/catalog.py` | B | service | request-response | `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/catalog.py` (current) | exact — in-place import flip |
| `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/scan.py` | B | service | request-response | `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/scan.py` (current) | exact — in-place import flip |
| `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/orchestrate.py` | B | service | event-driven | `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/orchestrate.py` (current) | exact — in-place import flip |

---

## Pattern Assignments

### Wave A — `pyproject.toml` (config, transform)

**Analog:** `/Users/cnoellert/Documents/GitHub/forge-bridge/pyproject.toml`

**Current state** (lines 35–41):
```toml
[project.scripts]
forge-bridge = "forge_bridge.server:main"
forge = "forge_bridge.cli.main:cli"

[tool.hatch.build.targets.wheel]
packages = ["forge_bridge"]
```

**Target state after Wave A + Wave B** — copy the git-dep syntax from forge-bridge's existing optional-dep block (lines 29–33), then apply to the new dep:

```toml
[project]
# ... existing deps unchanged, then add:
dependencies = [
    # ... all existing deps ...,
    "forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.1",
]

[project.scripts]
# forge-bridge script removed — pip package ships its own console_scripts entry
forge = "projekt_forge.cli.main:cli"

[tool.hatch.build.targets.wheel]
packages = ["projekt_forge"]
```

**Note:** The git dep URL version (`@v1.0.1` vs `@v1.0.0`) is determined by whether the v1.0.1 patch release is required before Wave B (RESEARCH.md verdict: YES — v1.0.1 is required). Use `@v1.0.1` once the tag exists.

---

### Wave A — Bulk import rename (all `projekt_forge/**/*.py`, `tests/**/*.py`, `forge_gui/**/*.py`)

**Role:** transform
**Data flow:** batch

**Analog:** The sed pattern from RESEARCH.md §Architecture Patterns "Pattern 1: Wave A Bulk Import Rewrite" — no existing codebase analog; the pattern is the bash command itself.

**macOS-correct sed command** (macOS requires empty string after `-i`):

```bash
find /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge \
     /Users/cnoellert/Documents/GitHub/projekt-forge/tests \
     /Users/cnoellert/Documents/GitHub/projekt-forge/forge_gui \
     -name "*.py" \
     -exec sed -i '' 's/from forge_bridge\./from projekt_forge\./g' {} +

# Also catch bare "import forge_bridge" references if any exist
find /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge \
     /Users/cnoellert/Documents/GitHub/projekt-forge/tests \
     /Users/cnoellert/Documents/GitHub/projekt-forge/forge_gui \
     -name "*.py" \
     -exec sed -i '' 's/^import forge_bridge$/import projekt_forge/g' {} +
```

**CRITICAL:** Do NOT apply sed to `/Users/cnoellert/Documents/GitHub/projekt-forge/flame_hooks/` — those files contain `from forge_bridge.*` inside subprocess script strings that must resolve against the pip package and must stay as `forge_bridge.*`.

**Verify flame_hooks untouched:**
```bash
grep -rn "from projekt_forge" /Users/cnoellert/Documents/GitHub/projekt-forge/flame_hooks/ || echo "CLEAN"
```

**Cache cleanup after rename:**
```bash
find /Users/cnoellert/Documents/GitHub/projekt-forge -type d -name __pycache__ \
     -exec rm -rf {} + 2>/dev/null; true
```

---

### Wave B — `projekt_forge/tools/catalog.py` (service, request-response)

**Analog:** `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/catalog.py` (the current file, already read)

**Current imports** (lines 1–14 after Wave A rename):
```python
from __future__ import annotations
import json
import logging
logger = logging.getLogger(__name__)
```

**Lazy import pattern to preserve** (lines 22–23 and 55–56 and 77–78 — the `# lazy to avoid circular import` comments are load-bearing):
```python
from forge_bridge.client.async_client import AsyncClient  # lazy to avoid circular import
```
```python
from forge_bridge.server.protocol import query_lineage as build_query_lineage  # lazy
```
```python
from forge_bridge.server.protocol import query_shot_deps as build_query_shot_deps  # lazy
```

**Wave B flip decision (per RESEARCH.md §Open Questions #4):**

- If v1.0.1 adds `query_lineage` and `query_shot_deps` to canonical `forge_bridge.server.protocol`: flip these lazy imports to `from forge_bridge.server.protocol import ...` (pip).
- If v1.0.1 does NOT add these builders: keep as `from projekt_forge.server.protocol import ...`.

**The `AsyncClient` import:** After Wave B, `client/async_client.py` is NOT deleted (it has the `project_name` extension that is forge-specific). So the lazy import stays as `from projekt_forge.client.async_client import AsyncClient`.

**Post-Wave-B lazy import block shape:**
```python
# Inside trace_lineage():
from projekt_forge.client.async_client import AsyncClient       # forge-specific project_name extension
from forge_bridge.server.protocol import query_lineage as build_query_lineage  # pip canonical (if v1.0.1)

# Inside get_shot_deps():
from projekt_forge.client.async_client import AsyncClient       # same
from forge_bridge.server.protocol import query_shot_deps as build_query_shot_deps  # pip canonical (if v1.0.1)
```

---

### Wave B — `projekt_forge/tools/scan.py` (service, request-response)

**Analog:** `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/scan.py` (current, read above)

**Lazy import pattern** (lines 23–27 — same lazy-import-inside-function pattern as catalog.py):
```python
from forge_bridge.scanner import MediaScanner, config_role_to_db_role
from forge_bridge.scanner.role_resolver import resolve_directory
from forge_bridge.client.async_client import AsyncClient
from forge_bridge.server.protocol.builders import project_list
```

**After Wave A rename, all become `projekt_forge.*`. Wave B does NOT flip these back** — scanner, scanner.role_resolver, and server.protocol.builders are all forge-specific (D-08 MOVE rule). Only `AsyncClient` flip decision is same as catalog.py above. `project_list` builder is in canonical protocol — flip to `from forge_bridge.server.protocol import project_list` if v1.0.1 includes it, else keep as `projekt_forge.server.protocol.builders`.

---

### Wave B — `projekt_forge/tools/orchestrate.py` (service, event-driven)

**Analog:** `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/orchestrate.py` (current, read above)

**Current bridge import** (line 17):
```python
from forge_bridge import bridge
```

**After Wave A**, this becomes `from projekt_forge import bridge` (wrong — `bridge` module is being deleted). **Wave B flip** for this file:

```python
# Replace:
from forge_bridge import bridge
# With:
from forge_bridge import bridge  # stays as forge_bridge (pip) — bridge.py is deleted from projekt_forge in Wave B
```

Wait — `orchestrate.py` currently imports `from forge_bridge import bridge` (the module, not a symbol). After Wave A, sed rewrites to `from projekt_forge import bridge`. After Wave B deletes `projekt_forge/bridge.py`, this import breaks. The Wave B fix is:

```python
# In projekt_forge/tools/orchestrate.py (Wave B):
# Replace: from forge_bridge import bridge   (after Wave A: from projekt_forge import bridge)
# With direct attribute access from the pip package:
import forge_bridge.bridge as bridge  # pip package — provides BRIDGE_URL, BRIDGE_TIMEOUT
```

The body of `orchestrate.py` uses `bridge.BRIDGE_URL` and `bridge.BRIDGE_TIMEOUT` as attributes. The canonical `forge_bridge.bridge` module exposes these as module-level names (lines 43–44 of bridge.py). This import pattern is safe.

---

### Wave C — `projekt_forge/server/mcp.py` (service, request-response)

**Analog:** `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/mcp/server.py` — provides the shape this file is being rebuilt around.

**Target shape (D-13 verbatim + research pattern 3):**

```python
"""
projekt-forge MCP server — forge-specific tool registration.

Obtains the FastMCP singleton from the forge-bridge pip package (which
already has all flame_* tools registered via register_builtins), then
registers projekt-forge's forge-specific tools under the forge_ prefix.

Usage:
    python -m projekt_forge           # via __main__.py
    python -m projekt_forge --no-db   # MCP only

Config (env vars — same as forge-bridge canonical):
    FORGE_BRIDGE_URL      ws://host:9998
    FORGE_BRIDGE_HOST     127.0.0.1
    FORGE_BRIDGE_PORT     9999
"""
from __future__ import annotations

from forge_bridge import get_mcp, register_tools

from projekt_forge.tools import catalog, orchestrate, scan, seed
from projekt_forge.tools import batch as forge_batch
from projekt_forge.tools import project as forge_project

# All tool registrations must happen before mcp.run() (post-run guard in registry.py).
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
        forge_project.list_desktop,   # if list_desktop MOVE decision made (vs v1.0.1 push)
    ],
    prefix="forge_",
    source="builtin",
)
```

**What is removed:** The entire body of 30+ `mcp.tool(name=..., annotations={...})(fn)` calls in the current `server/mcp.py` (lines 41–503). All flame_* registrations go away — `register_builtins()` inside the pip package's `forge_bridge/mcp/server.py` handles them at import time.

**What stays:** The `main()` function at the bottom of current `server/mcp.py` (lines 508–560) is absorbed into `__main__.py` (see Wave C — `__main__.py` below). The new `mcp.py` does NOT have a `main()` or argparse — that is `__main__.py`'s responsibility.

**Post-run guard awareness** (from `forge_bridge/mcp/registry.py` lines 103–111):
```python
import forge_bridge.mcp.server as _server
if _server._server_started:
    raise RuntimeError(
        "register_tools() cannot be called after the MCP server has started. "
        "Register all tools before calling mcp.run()."
    )
```
All `register_tools()` calls in `mcp.py` execute at module import time (top-level, not inside a lifespan or async function). This is correct.

---

### Wave C — `projekt_forge/__main__.py` (utility, event-driven)

**Analog:** `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/__main__.py` (current — in-place update)

**What changes in Wave C:**

1. All `from forge_bridge.bridge import configure` → `from forge_bridge.bridge import configure` (stays pip — `bridge.py` deleted from projekt_forge in Wave B, so this import must point at pip).
2. All `from forge_bridge.server.mcp import mcp` → `from projekt_forge.server.mcp import mcp` (Wave A already handled this; Wave C ensures it after the mcp.py rewrite).
3. All `from forge_bridge.server.db_server import run_db_server` → `from projekt_forge.server.db_server import run_db_server` (Wave A handled).
4. All `from forge_bridge.db.engine import dispose_all_engines` → `from projekt_forge.db.engine import dispose_all_engines` (Wave A handled).
5. Remove any direct calls to `startup_bridge()` or `shutdown_bridge()` — the canonical lifespan in the pip package's `forge_bridge/mcp/server.py` (lines 68–89) already calls these. `__main__.py` calls `mcp.run()` which triggers the lifespan.

**Core pattern to preserve** (current lines 65–80 — the TaskGroup orchestration is forge-specific and stays):
```python
async with asyncio.TaskGroup() as tg:
    if not getattr(args, "db_only", False):
        tg.create_task(_run_mcp_server(args), name="mcp-server")
    tg.create_task(_run_ws_server(), name="ws-db-server")
    ...
```

**`configure()` call pattern** (current line 19–20 — stays, but import source changes):
```python
from forge_bridge.bridge import configure   # pip package after Wave B
configure(host=args.bridge_host, port=args.bridge_port, timeout=args.bridge_timeout)
```

**What does NOT change:** The `--no-db`, `--db-only`, `--http`, `--bridge-host/port/timeout` argparse block. The TaskGroup. The signal handler. The `dispose_all_engines()` in finally.

---

### Wave D — `tests/conftest.py` (test, transform)

**Analog:** `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/conftest.py` (current — append to bottom)

**Current file structure** (read above): SQLite dialect patches → engine+session fixtures → stub ConnectedClient → stream publishing fixtures. Ends at line 225.

**Append pattern** (from RESEARCH.md §Validation Architecture, D-15):
```python
# ---------------------------------------------------------------------------
# RWR-04 — forge_bridge namespace collision guard (Phase 5)
# ---------------------------------------------------------------------------

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

**Placement:** After the last existing fixture (line 225 of current conftest.py). The `import pathlib` and `import forge_bridge` lines go at the top-level of the append block, not inside the fixture, to match the existing import style in conftest.py (which has all imports at the top). However, to avoid confusing the import ordering with the existing SQLite patch block, place the new imports just before the fixture definition with a section comment as shown above.

---

## Shared Patterns

### `from __future__ import annotations` header

**Source:** Every module in both repos uses this as the first non-comment line.
**Apply to:** All new/rewritten Python files in Wave C (mcp.py especially).

```python
from __future__ import annotations
```

### Module-level logger

**Source:** `forge_bridge/mcp/server.py` (line 44), `projekt_forge/tools/catalog.py` (line 13)
**Apply to:** Any new module in Wave C that logs.

```python
import logging
logger = logging.getLogger(__name__)
```

### Section-separator comment style

**Source:** `forge_bridge/mcp/server.py` (lines 46, 64, 95, 112), `forge_bridge/mcp/registry.py` (line 26)
**Apply to:** All new/rewritten Python files with multiple logical sections.

```python
# ─────────────────────────────────────────────────────────────
# Section heading
# ─────────────────────────────────────────────────────────────
```

### pip-consumer import pattern (the 11-name surface)

**Source:** `forge_bridge/__init__.py` (lines 23–35)
**Apply to:** `projekt_forge/server/mcp.py` (Wave C)

```python
from forge_bridge import get_mcp, register_tools        # MCP singleton + registry
from forge_bridge import startup_bridge, shutdown_bridge # lifecycle (used by __main__ if needed)
from forge_bridge import execute, execute_json, execute_and_read  # Flame HTTP bridge
from forge_bridge import LLMRouter, get_router           # LLM routing (Phase 6, not Phase 5)
```

For Wave C `mcp.py`, only `get_mcp` and `register_tools` are needed.

### `register_tools()` call-before-run contract

**Source:** `forge_bridge/mcp/registry.py` lines 75–115 — the post-run guard.
**Apply to:** `projekt_forge/server/mcp.py` (Wave C) — all `register_tools()` calls must be at module top-level (not inside lifespan, not inside `main()`).

```python
# CORRECT — top-level, runs at import time, before mcp.run()
mcp = get_mcp()
register_tools(mcp, [...], prefix="forge_", source="builtin")

# WRONG — inside lifespan or async context; will raise RuntimeError
@asynccontextmanager
async def _lifespan(server):
    register_tools(...)  # RuntimeError: called after mcp.run() started
    yield
```

### Git dep syntax for pyproject.toml

**Source:** `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` lines 29–33 (the existing git-dep pattern for `forge-align` and `forge-collapse-xform`)

```toml
[project.optional-dependencies]
cv = [
    "forge-align @ git+https://github.com/cnoellert/forge-align.git",
]
```

**Wave B pattern** (core dep, not optional):
```toml
[project]
dependencies = [
    # ... existing deps ...,
    "forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.0.1",
]
```

### Lazy import to avoid circular imports

**Source:** `projekt_forge/tools/catalog.py` (lines 22–23, 55–56, 77–78) and `projekt_forge/tools/scan.py` (lines 23–27)
**Apply to:** Any forge-specific tool that imports from `client.async_client` or `server.protocol`.

```python
# Inside async function body, not at module top:
from projekt_forge.client.async_client import AsyncClient  # lazy to avoid circular import
```

---

## v1.0.1 Patch Patterns (forge-bridge repo — prereq for Wave B)

These files are modified in forge-bridge BEFORE Wave B lands. Pattern analogs are the existing forge-bridge canonical files.

### `forge_bridge/server/protocol.py` — add missing builders

**Analog:** Existing builders in `forge_bridge/server/protocol.py` (flat file, not a directory).
**Pattern:** Same `_msg()` factory pattern used by all existing builders.

The canonical protocol file uses plain class attributes (no enum) and individual builder functions. New builders `query_lineage`, `query_shot_deps`, `media_scan`, and extended `entity_list` must follow the same pattern as the existing builders in that file — read the file directly to extract the exact `_msg()` call signature before adding new builders.

### `forge_bridge/client/async_client.py` — `ref_msg_id` correlation fix

**Analog:** `projekt_forge/forge_bridge/client/async_client.py` (the projekt-forge version has the fix).

**Fix pattern** (in `_handle_message()` or equivalent response correlation code):
```python
# CURRENT (canonical — broken for ref_msg_id):
ref_id = msg.msg_id

# FIXED (from projekt-forge version):
ref_id = msg.get("ref_msg_id") or msg.msg_id
```

### `forge_bridge/tools/timeline.py` — gap-fill fix

**Analog:** `projekt_forge/forge_bridge/tools/timeline.py` (the projekt-forge version has both fixes).
Cherry-pick: the `gap_fills` set and upward track scan in `rename_shots`, plus the `strip("'\\\"")` correction.

---

## Files with No Analog

All files have analogs. No entries.

---

## Critical Ordering Constraints

These are not patterns but must be recorded here because they affect which analog a planner can reference at each step:

| Constraint | What it blocks |
|------------|---------------|
| `git tag v1.0.1 && git push --tags` in forge-bridge BEFORE Wave B commit in projekt-forge | Wave B `pyproject.toml` dep URL; pip install fails if tag missing |
| v1.0.1 patch (protocol builders, async_client fix, timeline fix) in forge-bridge BEFORE Wave B | Wave B delete of local `client/async_client.py` and `tools/timeline.py` |
| Wave A full rename + test suite green BEFORE Wave B | "which forge_bridge did that mean" ambiguity during Wave B |
| All `register_tools()` calls at module top-level in `mcp.py` BEFORE `mcp.run()` | Post-run guard in registry.py raises RuntimeError otherwise |

---

## Metadata

**Analog search scope:**
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/` — canonical pip API source
- `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/` — target of rename + rewire
- `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/` — test fixtures to be updated
- `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` — package config

**Files read for pattern extraction:** 14
- forge-bridge: `__init__.py`, `mcp/__init__.py`, `mcp/server.py`, `mcp/registry.py`, `bridge.py`, `pyproject.toml`
- projekt-forge: `forge_bridge/server/mcp.py`, `forge_bridge/__main__.py`, `pyproject.toml`, `tests/conftest.py`, `forge_bridge/tools/catalog.py`, `forge_bridge/tools/scan.py`, `forge_bridge/tools/orchestrate.py`, `forge_bridge/server/protocol/__init__.py`, `forge_bridge/client/async_client.py` (partial)
- forge-bridge planning: `.planning/codebase/CONVENTIONS.md`

**Pattern extraction date:** 2026-04-16
