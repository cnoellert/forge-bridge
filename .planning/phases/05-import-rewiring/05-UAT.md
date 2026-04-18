---
status: complete
phase: 05-import-rewiring
source: [05-00-SUMMARY.md, 05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md]
started: 2026-04-17T22:45:00Z
updated: 2026-04-17T23:40:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test — pip install forge-bridge v1.0.1
expected: Clean virtualenv + `pip install 'forge-bridge @ git+...@v1.0.1'` + `import forge_bridge` prints `1.0.1` without error. Confirms the tag is real, the package publishes correctly, and projekt-forge's pip dep string is resolvable.
result: pass
notes: Install clean. Version via `importlib.metadata.version('forge-bridge')` returns `1.0.1`. `forge_bridge.__version__` attribute is NOT set on the package — minor public-API follow-up for v1.0.2 (non-blocking, logged below).

### 2. Public API surface intact
expected: From the pip-installed package, `from forge_bridge import LLMRouter, ExecutionLog, SkillSynthesizer, register_tools, get_mcp, startup_bridge, shutdown_bridge, execute, execute_json, execute_and_read` succeeds. This is the Phase 4 contract that Phase 5's rewiring depends on.
result: pass

### 3. v1.0.1 protocol builders + entity_list narrowing
expected: `from forge_bridge.server.protocol import query_lineage, query_shot_deps, media_scan, entity_list` succeeds. 2-arg positional `entity_list('Shot', 'proj-uuid')` preserves backward compat. Narrowing kwargs (`shot_id`, `role`) round-trip into the message dict. query_lineage/query_shot_deps/media_scan all produce valid messages. Confirms the Plan 05-00 patch.
result: pass

### 4. projekt-forge test suite green against pip v1.0.1
expected: In `/Users/cnoellert/Documents/GitHub/projekt-forge` with forge-bridge 1.0.1 installed to site-packages, `pytest tests/` reports `414 passed, 3 xfailed` and exit code 0. This is the integration confirmation that Waves A-D delivered a working projekt-forge on top of canonical forge-bridge.
result: pass
notes: 414 passed + 3 xfailed + 1 pre-existing websockets deprecation warning. Matches Wave D baseline exactly.

### 5. RWR-04 site-packages guard fires on regression
expected: The autouse fixture must fail loudly and self-documentingly when forge_bridge resolves to a local directory or a `forge_bridge/` directory reappears at the projekt-forge repo root.
result: pass
notes: Verified in the wild, not by synthetic test. A stale pre-rename `forge_bridge/` directory was found untracked at the projekt-forge repo root (resurrected from outside git — not in reflog). The fixture fired 414 times with a clear remediation message pointing directly at the offending path. After `mv forge_bridge /tmp/forge_bridge-fossil-*`, pytest returned to green. Both assertions (site-packages and defensive local-dir) are live; the defensive one earned its keep on the first real-world run.

### 6. projekt-forge MCP server launches via pip lifespan
expected: In projekt-forge, `python -m projekt_forge --help` exits 0 and usage shows `projekt_forge` (not `forge_bridge`). Confirms Wave C's 560→45 line MCP rewrite is functional end-to-end.
result: pass
notes: Exit code 0. Usage header shows `projekt_forge`, description shows `projekt-forge MCP + DB Server`. Argparse flags (--bridge-host, --bridge-port, --bridge-timeout, --http, --port, --no-db, --db-only) all present. Live server start not executed in this UAT (Flame bridge not required for --help path); entry-point wiring is proven.

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

## Minor Follow-ups (non-blocking)

- `forge_bridge.__version__` attribute not exposed on package root. Install resolves correctly and `importlib.metadata.version('forge-bridge')` returns `1.0.1`, but consumers expecting `forge_bridge.__version__` get `AttributeError`. Suggest adding `__version__ = version('forge-bridge')` to `forge_bridge/__init__.py` in v1.0.2.
