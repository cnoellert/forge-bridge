# Operation-Front Addition Surface — B1 Input

Date: 2026-06-09

Scope: Stage B widen over the proven create-reel operation-front pattern.
This records what changed to add two safe additive operations and what
remained the irreducible per-operation kernel.

## Operation Set

| Operation | Shape | Target semantics | API fact |
| --- | --- | --- | --- |
| create_reel | additive create | target=library by default; may target reel_group | `library.create_reel(name)` / `reel_group.create_reel(name)` |
| create_reel_group | additive create | target=desktop | `desktop.create_reel_group(name)` |
| create_library | additive create | no operator-selected target; current workspace | `workspace.create_library(name)` |

Together these bracket the additive-create family:
target=library/reel_group, target=desktop, and no-target/current-workspace.

## Files Touched

### `forge_bridge/console/_operation_digest.py`

Mode: copy-paste-modify from create-reel digest lines.

Kernel:
- operation name
- required argument key
- target semantics
- API fact
- output graph tool name

### `forge_bridge/console/_operation_front.py`

Mode: mostly copy-paste-modify collapsed into a table-driven internal
`_OperationSpec`.

Kernel:
- operation string
- MCP tool name
- required argument tuple
- deterministic clarification question
- default target args for preview/tool args
- operator-facing preview sentence

Shared unchanged surface:
- `validate_required_operation_args()` is reused unchanged for all three
  operations.
- placeholder/empty rejection stays upstream of AssentRecord persistence.
- preview->ratify->apply rail is unchanged.

### `forge_bridge/tools/timeline.py`

Mode: copy-paste-modify from `create_reel`, with a distinct Flame kernel.

Kernel:
- `create_reel`: resolve target container, then `target.create_reel(reel_name)`.
- `create_reel_group`: resolve current desktop, then
  `desk.create_reel_group(reel_group_name)`.
- `create_library`: resolve current workspace, then
  `ws.create_library(library_name)`.

Shared unchanged surface:
- discover/verify/apply mode split.
- mutation manifest shape.
- `apply_counterpart` points back to the same tool with `mode=apply`.
- apply drift returns the existing drift error shape.

### `forge_bridge/mcp/registry.py`

Mode: copy-paste-modify registration entries.

Kernel:
- tool function reference
- MCP tool name
- short operator-readable title
- `readOnlyHint=False`

### `THIRD-PARTY.md`

Mode: additive notice update.

Kernel:
- MIT `abrahamADSK/flame-mcp` remains the API-fact grounding source.
- No source code copied.
- Autodesk quarantined sample subtree not used.

### Tests

Mode: expanded existing operation-front and timeline manifest tests.

Kernel:
- preview/persist tests for the two new operations.
- placeholder/empty gate tests for each required name.
- ratified replay tests for each new tool.
- apply-failure probe over the existing failure surface:
  `chain_aborted` outcome + AssentRecord status `failed`, with no fake
  partial mutation recorded.

## B1 Shape Finding

For additive Flame creates, the reusable operation-addition surface is:

1. Add a compact digest line.
2. Add an `_OperationSpec` row.
3. Add one MCP mutation tool with the discover/verify/apply manifest shape.
4. Register the tool as mutating.
5. Add preview, gate, replay, and failure-surface tests.

The irreducible kernel is small: API call, target semantics, required-name
field, and preview phrasing. Everything else is boilerplate today.

## Failure Probe Result

The code-level probe exercises an apply-time drift response. The existing
ratify/apply substrate surfaces this as:

- `ApplyBranchOutcome.regime == "chain_aborted"`
- AssentRecord status becomes `failed`
- failure reason is `drift_invalid`

There is not currently a distinct `apply_failed` regime. The current surface
is deterministic and records failure on the AssentRecord; a named
`apply_failed` taxon would be a separate surface-design decision.

Live Flame confirmation was not run as part of this artifact.
