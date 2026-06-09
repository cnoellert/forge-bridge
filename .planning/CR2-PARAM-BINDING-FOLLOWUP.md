# Follow-up — Forced-tool param binding drops resolved args (Optional-model-param tools)

**Found by:** live re-probe after CR.2 T4 verified (referent re-entry dispatches `forge_list_shots`
with `{project_id: 2753ec84-…}` → tool returns `MISSING_PROJECT_ID`).
**Disposition:** pre-existing bridge bug, **independent of CR.2**, newly *reachable* because CR.2
made "forced read with a resolved required param" happen for the first time.
**Status:** root cause pinned (DT). Pass-to-code.

---

## Symptom

A forced single-tool dispatch hands `forge_list_shots` a resolved `{project_id: <uuid>}`, and the
tool still returns `MISSING_PROJECT_ID` (`tools.py:521`, `if params is None`). The param is present
on the wire but `None` inside the tool.

## Root cause — one layer below the symptom

`tools.py:521` is where it *surfaces*; the binding fails in `normalize_tool_args`
(`arguments.py`), applied at `handlers.py:765` before `mcp.call_tool`.

`forge_list_shots` takes a **single Pydantic model param named `params`**, Optional:

```python
async def list_shots(params: Optional[ListShotsInput] = None) -> str:   # tools.py:497
    if params is None: return _err(..., code="MISSING_PROJECT_ID")      # :521
    ... params.project_id ...                                           # :529
```

FastMCP needs the call args nested as `{"params": {"project_id": …}}`. The forced path produces a
**flat** `{"project_id": …}` (from `resolve_required_params` / `user_params`). `normalize_tool_args`
exists to bridge flat→nested — **but its gate is too narrow:**

```python
# arguments.py — requires_params_wrapper(...)
required = input_schema.get("required") or []
if "params" not in required:        # ← Optional[...] = None ⇒ params NOT required ⇒ returns False
    return False
...
ref = params_schema.get("$ref")     # ← Optional shape emits anyOf:[{$ref},{null}], not a direct $ref
if not isinstance(ref, str): return False
```

An `Optional[Model] = None` param emits a schema where (a) `params` is **not in `required`**, and
(b) the `$ref` sits under `anyOf`, not at the property root. **Either condition alone** makes
`requires_params_wrapper` return `False`, so `normalize_tool_args` passes the flat args through
**unwrapped** → no `params` key → `params` defaults to `None` → `MISSING_PROJECT_ID`.

## The asymmetry that proves it

- `get_project(params: GetProjectInput)` — **required** model param → `"params" in required`,
  direct `$ref` → wrapper fires → **works.**
- `list_shots(params: Optional[ListShotsInput] = None)` — **optional** model param → wrapper
  skipped → flat args dropped → **fails.**

Same dispatch path, opposite outcome, gated entirely on the Optional-ness of the model param.

## Scope — who else bites

Any tool with `params: Optional[<Model>] = None` **and** a practically-required field. Audit the
`Optional[...Input] = None` signatures in `tools.py` (e.g. `list_shots`; `list_staged` is likely
benign — all-optional fields tolerate `params=None`). Required-model-param tools (`get_project`,
`create_project`, …) are unaffected.

## Fix shape (for code)

Teach `requires_params_wrapper` (or `normalize_tool_args`) to recognize the **Optional-model-param**
shape: a `params` property whose schema is an `anyOf`/`oneOf` containing a `$ref` to an object
`$def`, **even when `params` is not in `required`**.

⚠ **Preserve PR22's graceful-empty path.** A genuinely empty call (`forge_list_shots` with no args)
must still bind to `params=None` and return the friendly `MISSING_PROJECT_ID`, *not* a Pydantic
validation error. So **wrap only non-empty flat args**: `{}` stays `{}` (→ `params=None` → graceful);
`{project_id: …}` wraps to `{params: {project_id: …}}` (→ binds). No LLM, no probe — pure schema-shape
normalization at the existing `:765` seam.

## For DT to pin before execute

1. Confirm the live `inputSchema` for `list_shots` actually emits `anyOf:[{$ref},{null}]` + `params`
   absent from `required` (drives the exact predicate to relax).
2. The `{}`-stays-`None` boundary — the one case the relaxed wrapper must *not* swallow.

## Verification (close the coverage gap that hid this)

The matcher unit test, DT's in-process e2e, and the routing trace all missed it — **the e2e used a
controlled tool without the Optional-model-param shape.** Add an apply-path test that forces a
dispatch to a tool with `params: Optional[<Model>] = None` carrying a required field, asserting the
field arrives bound (not `None`). One live-wire-shaped test on a real `tools.py` tool would have
caught it; that's the regression surface to add.
