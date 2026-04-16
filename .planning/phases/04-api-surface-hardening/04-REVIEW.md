---
phase: 04-api-surface-hardening
reviewed: 2026-04-16T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - forge_bridge/__init__.py
  - forge_bridge/learning/synthesizer.py
  - forge_bridge/llm/router.py
  - forge_bridge/mcp/__init__.py
  - forge_bridge/mcp/registry.py
  - forge_bridge/mcp/server.py
  - forge_bridge/tools/publish.py
  - pyproject.toml
  - tests/test_llm.py
  - tests/test_mcp_registry.py
  - tests/test_public_api.py
  - tests/test_synthesizer.py
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-04-16
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found (2 warnings, 5 info — all minor / pre-existing or low-severity)

## Summary

Phase 04 ("API Surface Hardening") is a tidy, consistent refactor. The public surface is explicit
(11-name `__all__`), the MCP lifecycle hooks are cleanly renamed (`startup_bridge`/`shutdown_bridge`
with matching `arg → env → default` injection pattern), the `_server_started` post-run guard on
`register_tools()` is wired both in production (`_lifespan`) and correctly reset for tests, and the
scrub of forge-specific strings (`portofino|assist-01|ACM_|flame-01|Backburner|cmdjob`) is verified
clean by grep across `forge_bridge/` (the PKG-03 regression guard itself passes).

The `SkillSynthesizer` class promotion is well-tested (router injection, `synthesized_dir`
injection, None-fallback semantics), and the `D-19` removal of the module-level `synthesize()` is
guarded by a regression test at both the `forge_bridge.learning.synthesizer` layer and the
`tests/test_public_api.py` layer.

No critical issues. No security issues. Two warnings below are modest correctness concerns that
predate Phase 04 but surface more visibly now that this phase formalises the API. The five info
items cover style, test portability, and a couple of subtle import-time side effects that may
matter to downstream consumers.

## Warnings

### WR-01: `_async_local()` may return `None` despite the declared `-> str` type

**File:** `forge_bridge/llm/router.py:235`
**Issue:** `acomplete()` is annotated `-> str`, and for the sensitive=True path it returns
`resp.choices[0].message.content`. The OpenAI Python SDK types `ChatCompletionMessage.content` as
`Optional[str]` — an empty / tool-call-only response yields `None`. Downstream code in
`SkillSynthesizer.synthesize()` passes this value directly to `_extract_function(raw)` and then
`ast.parse(fn_code)` — if `raw` is `None`, `re.search` raises `TypeError` before the signature
validation fence catches it. The `except RuntimeError` at `synthesizer.py:248` will not catch that
`TypeError`, so a degenerate local-LLM response leaks an uncaught exception out of the synthesizer.

**Fix:**
```python
# forge_bridge/llm/router.py _async_local
content = resp.choices[0].message.content
if content is None:
    raise RuntimeError(
        f"Local LLM returned empty content (model={self.local_model})"
    )
return content
```
This keeps the `-> str` contract honest and routes degenerate responses through the existing
`except RuntimeError` branch in `SkillSynthesizer.synthesize()`. (The cloud path at
`router.py:252` has the same pattern via `resp.content[0].text` but `.text` is declared `str` in
the anthropic SDK, so the same treatment is only strictly required for local.)

### WR-02: `SkillSynthesizer()` default construction eagerly instantiates `LLMRouter`

**File:** `forge_bridge/learning/synthesizer.py:213`
**Issue:** `self._router = router if router is not None else get_router()` is evaluated inside
`__init__`. That is documented in the docstring ("Eager fallback at init"), and the unit test
`test_router_injection` relies on it — but it means every `SkillSynthesizer()` default
construction constructs the shared `LLMRouter` singleton, which in turn reads env vars. If a
downstream consumer instantiates `SkillSynthesizer()` at import time (e.g. in a class-level
default) they pay the env-read cost and the router singleton is built whether or not they ever
synthesise. The lazy pattern would be `self._router = router` and deferring `get_router()` to
first use inside `synthesize()`.

This is a deliberate design call per the `D-05 / D-17` injection story (so callers can assert
`assert synth._router is something` eagerly). Flagging as a warning only because it's a silent
side effect of a no-arg constructor, and it's worth confirming this is the intended contract.

**Fix:** If the eager behaviour is intentional (it appears to be — test `test_router_injection`
at `tests/test_synthesizer.py:218` exercises it), add a one-line note to the class docstring:
```
Note: passing router=None resolves get_router() at construction time, not at
synthesize() call time. Construct SkillSynthesizer lazily if you want to
defer LLMRouter singleton creation.
```
If it is *not* intentional, defer resolution:
```python
def __init__(self, router=None, synthesized_dir=None):
    self._router = router  # lazy — resolved in synthesize()
    self._synthesized_dir = synthesized_dir or SYNTHESIZED_DIR

async def synthesize(self, ...):
    router = self._router if self._router is not None else get_router()
    ...
```

## Info

### IN-01: `test_no_forge_specific_strings` depends on system `grep` availability

**File:** `tests/test_public_api.py:188`
**Issue:** The PKG-03 regression guard shells out to `subprocess.run(["grep", "-r", "-E", ...])`.
This works on any macOS/Linux dev machine, but BSD grep vs GNU grep handle `-E` and `--include`
slightly differently, and CI containers (especially minimal Python images) sometimes omit `grep`.
If `grep` is missing the test raises `FileNotFoundError` rather than failing with a clear message.
**Fix:** Replace the shell-out with a pure-Python walk — iterating `Path(root).rglob("*.py")` and
applying `re.search(r"portofino|assist-01|ACM_", text)` is a few lines, needs no subprocess, and
produces identical coverage:
```python
import re
pattern = re.compile(r"portofino|assist-01|ACM_")
hits = []
for p in Path(root).rglob("*.py"):
    for i, line in enumerate(p.read_text().splitlines(), 1):
        if pattern.search(line):
            hits.append(f"{p}:{i}: {line}")
assert not hits, "Found forge-specific strings:\n" + "\n".join(hits)
```

### IN-02: `import forge_bridge` now transitively imports the MCP registry and builtins

**File:** `forge_bridge/__init__.py:32`
**Issue:** The barrel imports `startup_bridge, shutdown_bridge` from `forge_bridge.mcp.server`,
which at module level runs `register_builtins(mcp)` (server.py:107). That pulls in
`forge_bridge.mcp.tools` and all of `forge_bridge.tools.{project,timeline,batch,utility,publish,
reconform,switch_grade}` — each of which imports `forge_bridge.bridge` (httpx client). The net
effect is that `import forge_bridge` now has a non-trivial startup cost and imports `httpx`, all
the tool modules, and `forge_bridge.llm.health` eagerly, even if the consumer only wants
`execute()`.
**Fix:** This is acceptable for a "batteries-included" consumer surface and is consistent with the
phase goal of a single well-known public surface. If lazy imports are desired later, use
`__getattr__` at the module level (PEP 562) to defer the heavy imports until the name is first
accessed. Noted as info only — not a bug.

### IN-03: `get_router()` singleton is not thread-safe

**File:** `forge_bridge/llm/router.py:263`
**Issue:** Classic double-construction race — two threads hitting `get_router()` concurrently on
a fresh process can both observe `_router is None` and both run `_router = LLMRouter()`, with the
last write winning and the first one silently discarded. In practice the MCP server is single-
asyncio-loop so this is extremely unlikely to matter, but any future multi-threaded consumer (e.g.
a FastAPI integration) would hit it.
**Fix:** Either (a) document "call from the main thread only" in the docstring, or (b) wrap with
a `threading.Lock`:
```python
_router_lock = threading.Lock()
def get_router():
    global _router
    if _router is None:
        with _router_lock:
            if _router is None:  # double-check
                _router = LLMRouter()
    return _router
```
Pre-existing issue, not introduced by Phase 04.

### IN-04: Local LLM call has no `max_tokens` / timeout cap

**File:** `forge_bridge/llm/router.py:230`
**Issue:** `_async_cloud` sets `max_tokens=4096` but `_async_local` does not. Ollama's default
context length varies per model; a runaway generation could block the synthesiser indefinitely.
There is also no explicit timeout on the AsyncOpenAI client (httpx default 5s connect / none for
read in AsyncOpenAI without an explicit `timeout=`). For a tool that blocks the MCP lifespan on
synthesis, a wedged local call is a liveness concern.
**Fix:** Pass a timeout and a `max_tokens` budget:
```python
resp = await client.chat.completions.create(
    model=self.local_model,
    messages=messages,
    temperature=temperature,
    max_tokens=2048,
    timeout=60.0,
)
```
Pre-existing — not a Phase 04 regression. Flagged because Phase 04 formalises
`LLMRouter.acomplete()` as the public async entry point.

### IN-05: `_lifespan` does not reset `_server_started` if `startup_bridge()` raises

**File:** `forge_bridge/mcp/server.py:72-89`
**Issue:** The lifespan sets `_server_started = True` *after* `startup_bridge()` completes. If
`startup_bridge()` itself raises (e.g. `AsyncClient(...).start()` fails synchronously before
`wait_until_connected()`'s try/except swallows it), execution never reaches the `try:` block, so
the `finally:` resets `_server_started = False` against a value that was never set to `True`. The
assignment is a no-op in that case — fine. But if a future refactor sets `_server_started = True`
*before* calling `startup_bridge()` (tempting, to close the D-14 "post `mcp.run()`" window
tighter), the current ordering would need to move the flag assignment into the `try:` block to
preserve the cleanup guarantee.
**Fix:** No change needed today. Add a one-line comment at line 74 documenting the ordering
invariant:
```python
# _server_started is set AFTER startup_bridge() so a raising startup leaves
# the flag False. Do not move this assignment before startup_bridge().
```

---

_Reviewed: 2026-04-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
