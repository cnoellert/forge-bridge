## Update — registration resolved; slice-3 UAT passed live; ingest converged as an operator node

**1. Registration ask (a/b/c) RESOLVED.** Pipeline `v2.1.1` shipped the `traffik` `forge_core.plugins` entry-point (option a); Bridge #119 (`tests/orchestration/test_traffik_operation_plugin_live.py`) proves `build_operation_runner()` dispatches both traffik ops via plugin discovery, no manual `registry.register(...)`. Thanks.

**2. Live-runtime validation still open in the Bridge env.** Today: `entry_points("forge_core.plugins")` = `['blender','flame','fusion','houdini']` — no `traffik`; no `forge-core` dist metadata; `FORGE_PLUGINS` unset. The installed forge_core here predates the v2.1.1 entry-point. **Operator action:** install/refresh Pipeline `v2.1.1+` in the Bridge runtime + `FORGE_PLUGINS=traffik`, then the discovery-clean path is validated live.

**3. Slice-3 `select_delta` UAT — PASSED live** on `FORGE_UAT_HOST_APPLY_20260624`, first segment `260511_HMA_FIFA_DIEGO__recharge_011_9x16` (Gate B harness):
- proposed (non-ratified) assent → `ASSENT_INVALID` (refused before apply — fail-closed gate holds)
- ratified forward apply → live rename → probe matched
- ratified revert → **independent** segment probe confirms original restored; residue-free; `status: passed`
- needed **no** traffik registration (drives `project_flame_delta_host_resolve_payload` + `apply_segment_delta` directly).

Bridge's slice-3 is complete: `select_delta` node + boundary + admission shipped (`9654ec7`, #118), unit-tested, full 5-node chain `apply_steps → select_delta → host_resolve → delta_to_manifest → commit` passes through the executor. `apply_steps → select_delta` runs live (real operator emits 5 deltas; extracts `deltas[0]`).

**4. The one unproven-live composition + converged plan to close it.** The full inline chain on a live sequence needs a real `apply_steps` delta that resolves against live Flame — blocked today by (i) no rename atom (`editing/operations.py` is temporal/structural; rename = `analysis/rename.py`), and (ii) no operator-clean Flame→EditState ingest (`traffik_adapters.reader` exists but isn't yet that source).

**Converged decisions (Bridge + Pipeline, 2026-06-25):**
- **Ingest is an operator node, not config.** The graph represents work, not just decisions — Flame sequence → EditState is a representation production with identity/provenance/diagnostics/failure modes, so it's a node: `ingest → apply_steps → select_delta → host_resolve → commit`. Pipeline exposes ingest with an operation envelope (wrapping the existing Flame reader); Bridge admits it like it admitted `host_resolve`. Configuration describes how to run a node, never replaces one.
- **First live inline vertical = temporal edit**, not rename — the temporal/trim lane is already live-probed; rename would add naming-analysis + a new atom at once and muddy the vertical. Rename atom (a pure editorial `set_segment_name`/rename-plan atom) rides next, then connects `analysis.rename`.
- **Executor routing contract — classifier level, not a literal string:** `apply_steps` emits host-resolve deltas carrying a **valid executor identifier from the Pipeline classifier contract**; Bridge validates that identifier against its trusted allow-list (`_TRUSTED_EXECUTORS`) and routes. Pipeline decides which executor a delta requires; Bridge decides which it trusts; the classifier contract is the only seam. Bridge already works this way — no Bridge code change.

**No Bridge code pending.** When Pipeline lands the ingest operator, the live temporal vertical is wiring (the graph shape is stable), not redesign.
