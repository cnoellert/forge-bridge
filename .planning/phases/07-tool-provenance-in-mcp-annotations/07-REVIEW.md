---
phase: 07-tool-provenance-in-mcp-annotations
reviewed: 2026-04-21T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - forge_bridge/learning/synthesizer.py
  - forge_bridge/learning/sanitize.py
  - forge_bridge/learning/watcher.py
  - forge_bridge/learning/execution_log.py
  - forge_bridge/mcp/registry.py
  - tests/test_synthesizer.py
  - tests/test_sanitize.py
  - tests/test_watcher.py
  - tests/test_mcp_registry.py
  - tests/test_execution_log.py
  - README.md
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-04-21T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 7 delivers sidecar-envelope v1.2 (`.sidecar.json`), PROV-03 tag sanitization + size budgets, `register_tool` provenance merging with `forge-bridge/*` namespace enforcement, PROV-04 `readOnlyHint=False` baseline for synthesized tools, WR-01 async-callback hygiene, and README conda-env docs. The core security work is solid: the allowlist redaction, injection-marker rejection, canonical-key protection, and namespace-filtered `_meta` merge are all well-structured and well-tested. The round-trip tests in `tests/test_synthesizer.py::TestSidecarEnvelope` and `tests/test_mcp_registry.py::TestProvenanceMerge` cover the happy path and the defense-in-depth cases (rogue keys dropped, empty tags omitted).

No critical issues. Four warnings involve a documented-but-missing defense-in-depth check on `register_tool`, dead feature-detection code in the watcher, a stale version pin in the README, and a type-safety gap in `_read_sidecar` that silently corrupts tags when the sidecar's `tags` key is not a list. Six info items cover minor code-quality nits: test-harness imports (`unittest.mock`) leaking into the production module, eviction-order determinism in `apply_size_budget`, and silent exception swallowing in the watcher poll loop.

## Warnings

### WR-01: `register_tool` does not apply `apply_size_budget` to caller-supplied `provenance`

**File:** `forge_bridge/mcp/registry.py:82-90`
**Issue:** The `sanitize.py` module docstring (line 15) documents both `watcher._read_sidecar` AND `registry.register_tool` as callers that go through `apply_size_budget` before the payload reaches `mcp.add_tool`. Only the watcher does so (`watcher.py:119`). `register_tool` accepts `provenance` as a public kwarg and merges `prov_meta` / `tags` directly into `merged_meta` with no size budget, no per-tag sanitization, and no tag-count ceiling. A non-watcher caller (downstream consumer, future synthesizer shortcut, test, or internal plugin that constructs a provenance dict by hand) can push arbitrary-size meta values and unbounded tag lists onto the MCP wire. This defeats the PROV-03 defense-in-depth guarantee the docstring promises.

**Fix:**
```python
# In forge_bridge/mcp/registry.py, inside register_tool, before building merged_meta:
from forge_bridge.learning.sanitize import _sanitize_tag, apply_size_budget

if provenance is not None:
    # Defense-in-depth: re-apply PROV-03 sanitization at the write boundary.
    raw_tags = provenance.get("tags") or []
    clean_tags = [t for t in (_sanitize_tag(x) for x in raw_tags) if t is not None]
    budgeted = apply_size_budget({"tags": clean_tags, "meta": provenance.get("meta") or {}})
    prov_meta = budgeted["meta"]
    tags = budgeted["tags"]
else:
    prov_meta = {}
    tags = []

for k, v in prov_meta.items():
    if k.startswith("forge-bridge/"):
        merged_meta[k] = v
if tags:
    merged_meta["forge-bridge/tags"] = list(tags)
```

Alternatively, update `sanitize.py:15` to narrow the contract to "watcher is the only trusted entry point" — but given `register_tool` is explicitly called out as a PROV-03 consumer in `07-03-PLAN.md`, adding the enforcement is the correct fix.

### WR-02: `_read_sidecar` trusts `tags` field type — non-list payloads yield corrupted iteration

**File:** `forge_bridge/learning/watcher.py:85-88, 101-104, 109-113`
**Issue:** After `_json.loads`, the code does `"tags": loaded.get("tags") or []`. If the sidecar file contains `{"tags": "project:acme", "meta": {}, "schema_version": 1}` (a string rather than a list), the truthy-`or` coalescing does NOT replace it with `[]` — the string is truthy. The subsequent `for t in raw["tags"]` then iterates CHARACTERS of the string and runs `_sanitize_tag('p')`, `_sanitize_tag('r')`, etc. Each single-char tag misses the allowlist prefix and is redacted to a `redacted:<hash>` entry, producing 13+ spurious tag rows. Same issue with `meta`: if the file has `{"meta": 42}`, the `or {}` keeps `42` through, and `dict(raw["meta"])` raises `TypeError: cannot convert dictionary update sequence element #0 to a sequence`, killing `_read_sidecar` inside `_scan_once`'s try-block with a stack trace logged as "Error in synthesized tool watcher" rather than a targeted "malformed sidecar" warning.

**Fix:**
```python
# After loading, explicitly validate types:
tags_field = loaded.get("tags")
if tags_field is not None and not isinstance(tags_field, list):
    logger.warning(
        ".sidecar.json for %s has non-list tags field — skipping provenance",
        py_path.stem,
    )
    return None
meta_field = loaded.get("meta")
if meta_field is not None and not isinstance(meta_field, dict):
    logger.warning(
        ".sidecar.json for %s has non-dict meta field — skipping provenance",
        py_path.stem,
    )
    return None
raw = {"tags": tags_field or [], "meta": meta_field or {}}
```

### WR-03: Dead feature-detection branch in `_scan_once`

**File:** `forge_bridge/learning/watcher.py:162-166`
**Issue:** The comment says "Plan 07-03 adds `provenance` kwarg to register_tool. Until then, fall back to the no-kwarg call so Wave 2 can land independently of Wave 3." Phase 7 has landed both waves — `register_tool` now always has `provenance` in its signature (`registry.py:58`). The `inspect.signature(...).parameters` feature-detect runs on EVERY scan iteration (every 5 s per `_POLL_INTERVAL`), pays a reflection cost, and the `else` branch is unreachable code. Unreachable code in a security-sensitive path is a maintenance hazard: a future refactor that accidentally removes the `provenance` kwarg would silently fall through to a path that drops all provenance without warning, defeating PROV-02.

**Fix:** Remove the feature-detect and call `register_tool` with `provenance=provenance` unconditionally:
```python
try:
    provenance = _read_sidecar(path)
    register_tool(mcp, fn, name=stem, source="synthesized", provenance=provenance)
    seen[stem] = digest
    logger.info(f"Registered synthesized tool: {stem}")
except ValueError as e:
    logger.warning(f"Skipped {stem}: {e}")
```

### WR-04: README installer URL pins stale version `v1.1.0`

**File:** `README.md:106, 109`
**Issue:** The one-liner installer curls `https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.1.0/scripts/install-flame-hook.sh` and the env-var default is `FORGE_BRIDGE_VERSION=v1.1.0`. Per the git log on `main`, the current shipped version is `v1.2.1` (hotfix for startup-bridge graceful degradation). A fresh install from the README will pin operators to a version that predates the PROV-* work the README is sitting alongside — and predates the startup-bridge hotfix. This is a documentation-correctness bug that affects every new workstation install.

**Fix:** Bump both occurrences to `v1.2.1`:
```markdown
curl -fsSL https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.2.1/scripts/install-flame-hook.sh | bash
```
And update the parenthetical to `(default v1.2.1)`. Consider replacing literal version pins in docs with a `$(git describe --tags --abbrev=0)` style note or a `latest` alias so this doesn't recur on every release.

## Info

### IN-01: `unittest.mock` imported at module scope in production synthesizer

**File:** `forge_bridge/learning/synthesizer.py:23`
**Issue:** `from unittest.mock import AsyncMock, patch` sits in the top-level imports of a production module. These are used only inside `_dry_run` (lines 213-216). `unittest` is stdlib so it's not a packaging concern, but module-level test-harness imports muddy the separation between production and test code and make `forge_bridge.learning.synthesizer` appear to be importing test tooling when grepping dependencies.
**Fix:** Move the import inside `_dry_run`:
```python
async def _dry_run(fn_code: str, fn_name: str) -> bool:
    from unittest.mock import AsyncMock, patch  # used only for sandboxed dry-run
    ...
```

### IN-02: `apply_size_budget` eviction order is deterministic-by-insertion-but-undocumented

**File:** `forge_bridge/learning/sanitize.py:136-145`
**Issue:** `non_canonical = [k for k in meta if k not in _PROTECTED_META_KEYS]` preserves dict-insertion order; `non_canonical.pop()` removes from the end. Which non-canonical key is evicted first depends entirely on the caller's dict-build order — this is stable in CPython 3.7+ but not documented in the function contract. Operators debugging "why was my tag evicted" will be surprised.
**Fix:** Either sort deterministically (e.g., `sorted(non_canonical, reverse=True)` for lexicographic-stable eviction) or add a line to the docstring: "Non-canonical meta keys are evicted in reverse dict-insertion order (most-recently-added first) until the budget fits."

### IN-03: Silent `except Exception` in watcher `remove_tool` cleanup paths

**File:** `forge_bridge/learning/watcher.py:150-153, 175-179`
**Issue:** Two `try: mcp.remove_tool(stem); except Exception: pass` blocks. If `remove_tool` starts raising a new exception type in a future `mcp` version (e.g., `ToolNotRegisteredError`), the watcher will silently drop the cleanup failure and leak stale tool registrations across reloads.
**Fix:** At minimum, log at debug level so the failure leaves a trace:
```python
try:
    mcp.remove_tool(stem)
except Exception:
    logger.debug("remove_tool(%s) raised during cleanup", stem, exc_info=True)
```

### IN-04: `watch_synthesized_tools` bare `except Exception` in poll loop

**File:** `forge_bridge/learning/watcher.py:46-49`
**Issue:** `except Exception: logger.exception("Error in synthesized tool watcher")` is appropriate for a never-dying poll loop, but it also swallows `SystemExit`-adjacent conditions silently (OK — those subclass `BaseException`, not `Exception`). The concern is that a persistently-failing scan will log one stack trace per 5 seconds with no rate limiting, flooding the logs. Not a bug, just a readability/ops concern.
**Fix:** Consider adding a simple backoff or a "log once per distinct exception type" counter if ops ever complain about log volume. Low priority.

### IN-05: `_replay` has no bound on JSONL file size

**File:** `forge_bridge/learning/execution_log.py:147-180`
**Issue:** On every process start, the entire `~/.forge-bridge/executions.jsonl` is re-read line-by-line to rebuild counters. A multi-month-old pipeline with thousands of unique code patterns will replay a growing file on every MCP server restart. This is explicitly out of v1 scope per the review scope definition (performance), but worth noting for the next phase that touches this module.
**Fix:** None required for Phase 7. A future phase should either (a) checkpoint the rebuilt state periodically to a compact index or (b) compact the JSONL when it exceeds a threshold.

### IN-06: `synthesizer.py` local import of `forge_bridge` has a comment but not a clear cycle explanation

**File:** `forge_bridge/learning/synthesizer.py:372`
**Issue:** `import forge_bridge as _forge_bridge  # local import — avoid circular at module load` — the comment says "avoid circular" but doesn't say which chain. A reader has to trace the import graph to verify the claim. This is only needed for `_forge_bridge.__version__`; a cleaner alternative is to read the version once at module load via `importlib.metadata`.
**Fix:** Either document the cycle chain explicitly, or use `importlib.metadata.version("forge-bridge")` which avoids the cycle entirely:
```python
from importlib.metadata import version as _pkg_version
# ... later ...
"forge-bridge/version": _pkg_version("forge-bridge"),
```

---

_Reviewed: 2026-04-21T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
