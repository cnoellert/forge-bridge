# Phase 7 Plan 04 Summary — Release Ceremony + Deployment UAT

**Plan:** 07-04 — Release Ceremony: v1.2.0 tag, GitHub release, projekt-forge pin bump, cross-repo UAT
**Status:** COMPLETE (UAT completed via Phase 07.1)
**Completed:** 2026-04-21T18:25:00Z

## What shipped

- forge-bridge `v1.2.0` annotated tag on main (commit `0987525`, 2026-04-20)
- GitHub release at https://github.com/cnoellert/forge-bridge/releases/tag/v1.2.0 with wheel + sdist attached
- `mcp[cli]>=1.19,<2` dependency pin (PITFALL P-02.1 — 1.19 is the first SDK with `meta=` param on `FastMCP.tool`; `<2` prevents the in-progress FastMCP→MCPServer rename from silently breaking consumers)
- `__version__ == "1.2.0"` exposed via `importlib.metadata`
- projekt-forge pinned to `@v1.2.0` (initial pin landed 2026-04-20; subsequently bumped to `@v1.2.1` per Phase 07.1 Plan 03 after the deployment UAT surfaced the startup_bridge bug)

## Deployment UAT — deferred to Phase 07.1

The original UAT attempted on 2026-04-20 surfaced a deployment-blocking bug in
`forge_bridge.mcp.server.startup_bridge`: the try/except guarded only
`wait_until_connected()` and let `_client.start()`'s `ConnectionRefusedError`
escape, crashing the MCP server lifespan on any machine without a listener on
`:9998`. That session worked around the bug with a runtime monkey-patch
(`/tmp/run_pf_mcp.py`) — which made the UAT "pass" but was not actually
testing the deployment path. The monkey-patch was the tell: a real deployment
would have no such shim, and the bug would resurface the first time anyone
booted projekt-forge without a :9998 listener co-running.

**The true deployment UAT for Phase 7's PROV-02 work is captured in
Phase 07.1:**

- **Hotfix:** `forge_bridge/mcp/server.py startup_bridge()` wraps BOTH
  `_client.start()` AND `wait_until_connected()` in a single try/except;
  `_client.stop()` called in a nested try/except on failure; `_client = None`
  so `shutdown_bridge()` cleanly skips. Released as `v1.2.1`.
- **Regression test:** `tests/test_mcp_server_graceful_degradation.py` — FAILED
  against v1.2.0, PASSES against v1.2.1. Acts as the nyquist gate against
  regression.
- **UAT vehicle:** the user's Claude Code session on Portofino with
  projekt-forge registered as an MCP server via `claude mcp add -s user` — a
  REAL MCP client, no monkey-patches, no harness.
- **UAT evidence:** `.planning/phases/07.1-startup-bridge-graceful-degradation-hotfix-deployment-uat/07.1-UAT-EVIDENCE.md`
  captures verbatim tool-call results proving all five PROV-02 `_meta` keys
  (`forge-bridge/origin`, `code_hash`, `synthesized_at`, `version`,
  `observation_count`) reach a real MCP client on a freshly Ollama-synthesized
  `synth_set_segment_gain` tool, AND confirms `flame_*` / `forge_*` (non-synth)
  tools have no PROV-02 contamination.

## Commits carrying this plan

- `0987525` — `chore(release): bump version 1.1.1 → 1.2.0; pin mcp[cli]>=1.19,<2` (the v1.2.0 release commit itself)
- `4b64232` — `docs(07-04): handoff note for session restart` (original UAT attempt hand-off)
- **Phase 07.1 commits that completed the UAT that 07-04 promised:**
  - `bb472c9` — `test(07.1): add failing regression for startup_bridge graceful degradation` (TDD RED)
  - `8cfcb62` — `fix(mcp): startup_bridge graceful degradation on unreachable :9998` (TDD GREEN — the hotfix itself)
  - `abd047c` — `chore(release): bump version 1.2.0 → 1.2.1 — startup_bridge graceful degradation hotfix`
  - `f069407` — `docs(07.1-02): complete v1.2.1 hotfix release plan`
  - `d6aee82` — `docs(07.1-03): complete projekt-forge cross-repo re-pin to @v1.2.1 (Option A shadow remediation)`
  - `73f6af3` — `docs(07.1-04): handoff note for Claude Code restart before deployment UAT`
  - `d242521` — `docs(07.1-04): UAT evidence — PROV-02 _meta end-to-end via real MCP client`
  - `ce2e7de` — `docs(07.1-04): plan 04 summary — deployment UAT via real MCP client`

## Requirements closed

- **PROV-01** (sidecar schema): verified via Phase 07.1 UAT step 3 — fresh Ollama synthesis writes `.sidecar.json` with `schema_version=1`, `tags` list, and `meta` dict containing five canonical `forge-bridge/*` keys.
- **PROV-02** (`_meta` surfaces on `tools/list`): verified via Phase 07.1 UAT step 4 — MCP SDK probe's `tools/list` response shows full `_meta` envelope on `synth_set_segment_gain` with all five keys. Zero PROV-02 contamination on builtin `flame_*`/`forge_*` tools (step 6).
- **PROV-03** (sanitization at read boundary + size budgets + redaction allowlist): implemented in Plan 07-02 (`_sanitize_tag`, `apply_size_budget`); verified live by UAT step 4 (tags list starts with `"synthesized"` literal from watcher.py:117, confirming the read-boundary sanitizer ran).
- **PROV-04** (synthesized tools baseline `readOnlyHint=False`): verified via Phase 07.1 UAT step 4 — probe's MCP wire `annotations` dict for `synth_set_segment_gain` shows `readOnlyHint: false`, consistent with registry.py:101-104 safety baseline.
- **PROV-05** (async callback hygiene — WR-01): tests landed in Plan 07-03 (`tests/test_async_callback.py` or equivalent); no regressions observed in Phase 07.1 pytest gate (422 passed + 3 xfailed baseline match).
- **PROV-06** (`ExecutionRecord` docstring fix + README conda-env section — WR-02): landed in Plan 07-03; untouched by Phase 07.1. No UAT surface.

All six PROV-0X requirements are closed via the combination of Plans 07-01..07-03 (implementation) and Phase 07.1 Plan 04 (deployment UAT evidence).

## What did not ship in 07-04 (intentionally deferred)

- None — all 07-04 release-ceremony deliverables (pyproject bump, mcp[cli] pin, v1.2.0 tag, GitHub release, projekt-forge pin) shipped on 2026-04-20. The UAT itself was deferred to Phase 07.1 because the latent `startup_bridge` bug made the original UAT environment an unreliable deployment reproducer. The Phase 07.1 remediation retrofits the missing deployment evidence onto the v1.2.0→v1.2.1 lineage without re-releasing v1.2.0.

## Relationship to Phase 07.1

Phase 07.1 is the hotfix-and-re-UAT cycle that retroactively completes 07-04's UAT gate. It did NOT re-bump the Phase 7 milestone scope or add new PROV-0X requirements — it patched the latent bug (v1.2.0 → v1.2.1) and executed the UAT that 07-04 always intended. Phase 7's own close-out pipeline (`gsd-code-review 7`, regression gate, schema-drift verifier, `gsd-verifier`, `phase complete 07`) can now run because this SUMMARY + the 07.1-UAT-EVIDENCE.md pointer unblock it.

## Next

Phase 7 close-out pipeline (runs AFTER this plan's commit):
1. `/gsd-code-review 7` (advisory)
2. Regression gate (prior-phase tests — `pytest tests/test_phase_06_smoke.py`, etc.)
3. `gsd-tools.cjs verify schema-drift 07`
4. Spawn `gsd-verifier` for `07-VERIFICATION.md`
5. `gsd-tools.cjs phase complete 07`

Phase 8 (SQL Persistence Protocol) is gated on Phase 7 close-out completing.
