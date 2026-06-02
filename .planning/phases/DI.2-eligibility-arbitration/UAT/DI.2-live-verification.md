# DI.2 — Live Verification

Status: recorded 2026-06-01 after T2/T5/T6 landed.

## Provenance

- Console/chat endpoint: `http://127.0.0.1:9990`
- MCP HTTP port: `9991`
- Startup SHA: `5b17c85e76df32d1a3c5266a63a5ce2431c6848f`
- Disk SHA: `5b17c85e76df32d1a3c5266a63a5ce2431c6848f`
- Model: `qwen2.5-coder:14b`
- Postgres: reachable
- Flame bridge: reachable

## Result

R8/R9/R10 no longer fail with `tool_selection_ambiguous` for the compiled
`forge_get_shot` step. Divergence capture shows `post_pr14_filter:
["forge_get_shot"]` and `narrower.decision: ["forge_get_shot"]` for the
compiled step.

The reads still return `chain_aborted`, now at the next seam:

```text
Error executing tool forge_get_shot: 1 validation error for get_shotArguments
params.shot_id
  Field required
```

Interpretation: DI.2's resolver-overmatch failure is cleared for the reachable
class, but the dogfood reads do not yet become successful read answers because
the compile/parameter layer does not provide or resolve `shot_id` for "shot
10". This is downstream of DI.2's exact-name arbitration ladder.
