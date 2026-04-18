# Phase 6: Learning Pipeline Integration — Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 6 (4 modified in forge-bridge, 1 modified + 0-1 new in projekt-forge, plus tests)
**Analogs found:** 6 / 6

---

## File Classification

| File | New / Modified | Role | Data Flow | Closest Analog | Match Quality |
|------|----------------|------|-----------|----------------|---------------|
| `forge_bridge/learning/execution_log.py` | Modified | service (append-only log + counters) | event-driven (fire-and-forget callback) + file I/O | `forge_bridge/bridge.py` `_on_execution_callback` / `set_execution_callback` (lines 45–51, 162–168) | exact |
| `forge_bridge/learning/synthesizer.py` | Modified | service (LLM-driven codegen) | async request-response with hook injection | Same file — existing `router=` constructor injection (Phase 4 pattern, lines 196–215) | exact |
| `forge_bridge/learning/synthesizer.py` — `PreSynthesisContext` dataclass | New (in-module dataclass) | internal structural type | value object | `forge_bridge/bridge.py::_BridgeConfig` (frozen dataclass lines 20–29) + `forge_bridge/server/protocol.py::Message` (internal structural type) | role-match |
| `forge_bridge/__init__.py` | Modified (re-export `PreSynthesisContext`, `PreSynthesisHook`) | package barrel | re-export | `forge_bridge/core/__init__.py` + existing `forge_bridge/__init__.py` `__all__` block | exact |
| `projekt_forge/__main__.py` | Modified (add learning-pipeline init) | startup wiring | constructor injection from config | Same file — existing `_run_mcp_only(args)` + `configure(...)` pattern (lines 21–39) | exact |
| `tests/test_execution_log.py` | Modified (new test cases for callback) | test | unit + async (pytest-asyncio) | Same file — `tmp_path` + `ExecutionLog(log_path=log_path)` pattern (lines 37–80) + `tests/test_synthesizer.py` `AsyncMock` usage | exact |
| `tests/test_synthesizer.py` | Modified (new test cases for pre_synthesis_hook) | test | unit + async | Same file — existing `TestSynthesize` class with `AsyncMock` / `patch` | exact |

---

## Pattern Assignments

### 1. `forge_bridge/learning/execution_log.py` — add `set_storage_callback()` + dispatch in `.record()`

**Analog:** `forge_bridge/bridge.py` (`set_execution_callback` pattern)

**Why this analog:** Bridge already established the single-callback / setter-function / try-except-swallow pattern. LRN-02 mirrors the shape verbatim, with two differences: (a) the callback lives on the `ExecutionLog` class instance (not a module global), and (b) the callback may be async.

**Pattern to copy — module-level single-callback registration (bridge.py:45–51):**

```python
_on_execution_callback: Optional[Callable] = None


def set_execution_callback(fn: Optional[Callable] = None) -> None:
    """Set (or clear) the execution callback. Pass None to disable."""
    global _on_execution_callback
    _on_execution_callback = fn
```

**Pattern to copy — dispatch with exception isolation (bridge.py:162–168):**

```python
if _on_execution_callback is not None:
    try:
        _on_execution_callback(code, response)
    except Exception:
        pass  # never let callback errors break bridge operation

return response
```

**What's different in LRN-02 (planner must vary):**

1. **Instance attribute, not module global.** Callback lives on `self._storage_callback` because `ExecutionLog` is already a class (unlike `bridge.py` which is module-scoped). Setter becomes a method: `ExecutionLog.set_storage_callback(self, fn)`.
2. **Sync-or-async union.** D-04 requires `Callable[[ExecutionRecord], None | Awaitable[None]]`. Detect mode **once at registration time** via `inspect.iscoroutinefunction(fn)` and store `self._storage_callback_is_async: bool`. Per-call dispatch uses the stored flag — do NOT re-inspect on every `.record()`.
3. **Async dispatch via `asyncio.ensure_future` + `add_done_callback`** (D-05). Fire-and-forget; errors logged via done-callback, not awaited.
4. **`logger.warning` on failure** (the existing `pass` silence is only acceptable for bridge.py because bridge.py has no logger imported there; `execution_log.py` already has `logger = logging.getLogger(__name__)` at line 21 — USE IT).
5. **Callback receives the full record as a dataclass.** D-03 locks the payload shape: a new `ExecutionRecord` frozen dataclass (fields: `code_hash`, `raw_code`, `intent`, `timestamp`, `promoted`) — the same fields already written into the JSONL dict at lines 122–128. Do NOT pass the raw dict; construct the dataclass once, then use `asdict(rec)` or equivalent for the JSONL write to avoid field drift.
6. **Dispatch fires AFTER the JSONL flock+flush completes**, not before. Source-of-truth semantics (D-02, specifics §2): log is persisted first; callback is best-effort mirror.
7. **`ExecutionRecord` is a NEW dataclass in this file** — planner creates it; it is not in any other file today. Put it above `ExecutionLog` near the `LOG_PATH` constant (lines 20–23 area).

**Current call site the planner must modify (execution_log.py:107–141):**

```python
def record(self, code: str, intent: Optional[str] = None) -> bool:
    # ...
    rec = {
        "code_hash": h,
        "raw_code": code,
        "intent": intent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "promoted": False,
    }

    self._path.parent.mkdir(parents=True, exist_ok=True)
    with open(self._path, "a") as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        try:
            fp.write(json.dumps(rec) + "\n")
            fp.flush()
        finally:
            fcntl.flock(fp, fcntl.LOCK_UN)

    # <<< NEW: storage callback dispatch inserts HERE, after flock release,
    #          before the threshold check / return. >>>

    if self._counters[h] >= self._threshold and h not in self._promoted:
        return True
    return False
```

**Sync/async dispatch skeleton (planner to fill in):**

```python
# Build the record dataclass once — reused for both JSONL write and callback.
record = ExecutionRecord(
    code_hash=h,
    raw_code=code,
    intent=intent,
    timestamp=datetime.now(timezone.utc).isoformat(),
    promoted=False,
)
# ... existing JSONL write using asdict(record) ...

if self._storage_callback is not None:
    if self._storage_callback_is_async:
        try:
            task = asyncio.ensure_future(self._storage_callback(record))
            task.add_done_callback(_log_callback_exception)
        except RuntimeError:
            logger.warning("storage_callback scheduled outside event loop — skipped")
    else:
        try:
            self._storage_callback(record)
        except Exception:
            logger.warning("storage_callback raised — execution log unaffected", exc_info=True)
```

**Docstring discipline (specifics §2):** The `set_storage_callback()` docstring must include the phrase _"JSONL log is source-of-truth; the callback is a best-effort mirror"_ verbatim — this is user-facing framing.

---

### 2. `forge_bridge/learning/synthesizer.py` — add `pre_synthesis_hook=` constructor param + invocation

**Analog (primary):** Same file — existing `router=` constructor injection (synthesizer.py:196–215).

**Why this analog:** Phase 4 established the constructor-injection-with-fallback pattern in this exact class. LRN-04 layers onto it. The planner is extending an existing `__init__`, not rebuilding it.

**Pattern to copy — constructor injection with `None` default (synthesizer.py:206–215):**

```python
def __init__(
    self,
    router: LLMRouter | None = None,
    synthesized_dir: Path | None = None,
) -> None:
    # Eager fallback at init: get_router() is itself lazy, so this just
    # returns the shared singleton or constructs it.
    self._router = router if router is not None else get_router()
    # synthesized_dir=None falls back to the module-level SYNTHESIZED_DIR constant
    self._synthesized_dir = synthesized_dir if synthesized_dir is not None else SYNTHESIZED_DIR
```

**What's different for LRN-04 (planner must vary):**

1. **No fallback — `None` stays `None`.** Unlike `router` (which falls back to `get_router()`), `pre_synthesis_hook` default is a genuine no-op. There is no project-wide singleton to fall back to. Store `self._pre_synthesis_hook = pre_synthesis_hook` directly.
2. **Async-only signature** (D-08). Type alias at module level:
   ```python
   PreSynthesisHook = Callable[[str, dict], Awaitable[PreSynthesisContext]]
   ```
3. **Invocation point is inside `synthesize()` BEFORE the `acomplete()` call** (synthesizer.py:241–247):
   ```python
   try:
       raw = await self._router.acomplete(
           prompt,
           sensitive=True,
           system=SYNTH_SYSTEM,
           temperature=0.1,
       )
   ```
   becomes
   ```python
   # Call pre-synthesis hook (if registered) with (intent, params). D-09.
   ctx: PreSynthesisContext = PreSynthesisContext()
   if self._pre_synthesis_hook is not None:
       try:
           ctx = await self._pre_synthesis_hook(intent or "", {"raw_code": raw_code, "count": count})
       except Exception:
           logger.warning("pre_synthesis_hook raised — falling back to empty context", exc_info=True)
           ctx = PreSynthesisContext()

   # Compose system prompt + user prompt using ctx (D-11 additive-only).
   system_prompt = SYNTH_SYSTEM
   if ctx.constraints:
       system_prompt = SYNTH_SYSTEM + "\n\nConstraints:\n" + "\n".join(f"- {c}" for c in ctx.constraints)
   if ctx.extra_context:
       system_prompt += "\n\n" + ctx.extra_context

   user_prompt = prompt  # existing SYNTH_PROMPT-formatted string
   if ctx.examples:
       few_shot = "\n\n".join(
           f"Example intent: {ex.get('intent','')}\nExample code:\n```python\n{ex.get('code','')}\n```"
           for ex in ctx.examples
       )
       user_prompt = f"{few_shot}\n\n{prompt}"

   try:
       raw = await self._router.acomplete(
           user_prompt,
           sensitive=True,
           system=system_prompt,
           temperature=0.1,
       )
   ```
   (Exact prompt-structure is Claude's Discretion per CONTEXT.md §Decisions. The block above is a reasonable default; planner may refine.)
4. **`tags` attaches to synthesized tool, not the LLM call** (D-11). After the write succeeds (synthesizer.py:291–294), set an attribute on the manifest entry or on the output file's metadata:
   ```python
   output_path.write_text(fn_code)
   manifest_register(output_path)
   # Attach tags for later EXT-02 consumption.
   if ctx.tags:
       # Suggested: write a sidecar, or attach via manifest_register. Planner decides.
       setattr(sys.modules.get(f"_synth_dryrun_{fn_name}"), "_synthesized_tags", list(ctx.tags))
   ```
   (This is a stub — the exact mechanism is Claude's Discretion. The locked decision is only that tags must survive somewhere MCP-annotation-accessible. EXT-02 is deferred; a trivial stash is fine now.)
5. **Params dict shape for D-09.** The hook signature is `(intent: str, params: dict)`. The `params` dict passes what the synthesizer already has internally — `raw_code` and `count` are the natural candidates. Planner finalizes exact keys.

**Existing code that becomes a dependency to trace:** `SYNTH_SYSTEM` / `SYNTH_PROMPT` constants at synthesizer.py:32–54 — ctx fields compose onto these; don't replace them (D-11 additive-only).

---

### 3. `PreSynthesisContext` dataclass (new, inside synthesizer.py)

**Analog:** `forge_bridge/bridge.py::_BridgeConfig` (lines 20–29) for the `@dataclass(frozen=True)` shape.

**Pattern to copy — frozen dataclass with defaults (bridge.py:20–29):**

```python
@dataclass(frozen=True)
class _BridgeConfig:
    """Immutable bridge connection settings — swapped atomically."""
    host: str = "127.0.0.1"
    port: int = 9999
    timeout: int = 60

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
```

**Secondary analog for "internal structural type passed between functions":** `forge_bridge/server/protocol.py::Message` (lines 155–189). `Message` is a `dict` subclass rather than a dataclass because it crosses a JSON wire boundary; `PreSynthesisContext` does NOT cross a wire boundary (D-12) so dataclass is the right call. Cite `Message` only for the convention that *internal structural types live in the same module that owns them* — put `PreSynthesisContext` and the `PreSynthesisHook` type alias at the top of `synthesizer.py` near the existing `SYNTH_SYSTEM` / `SYNTH_PROMPT` constants.

**Exact shape locked by D-10 — planner writes this verbatim:**

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class PreSynthesisContext:
    """Additive context returned by SkillSynthesizer's pre_synthesis_hook.

    Additive-only (D-11): fields contribute to the prompt; they cannot
    replace the base SYNTH_SYSTEM / SYNTH_PROMPT.
    """
    extra_context: str = ""                               # appended to system prompt
    tags: list[str] = field(default_factory=list)         # "key:value" (K8s convention); flows to MCP annotations later (EXT-02)
    examples: list[dict] = field(default_factory=list)    # few-shot pairs: [{"intent": "...", "code": "..."}, ...]
    constraints: list[str] = field(default_factory=list)  # hard rules, e.g. "do not import flame"
```

**What's different vs `_BridgeConfig`:**

- No `@property` methods (flat value object, not a computed URL).
- Mutable defaults use `field(default_factory=list)` because `list` is mutable. Bridge's config only has immutable primitives so it didn't need `field()`.
- `frozen=True` is the same — both are immutable once constructed.

---

### 4. `forge_bridge/__init__.py` — re-export new public symbols

**Analog:** Existing `forge_bridge/__init__.py` (whatever Phase 4 landed) — same file, same `__all__` block.

**Why this analog:** Phase 4 set the canonical public surface. Phase 6 adds two symbols: `PreSynthesisContext` and the `PreSynthesisHook` type alias. Both belong in the `__all__` list alongside `SkillSynthesizer` / `LLMRouter`.

**Pattern to copy — grouped re-export with `__all__`:** See `forge_bridge/core/__init__.py` barrel shape (referenced in `04-PATTERNS.md` lines 30–76).

**What's different:** Nothing structural — this is a surgical two-line addition to the existing barrel. Planner inserts into the existing "Learning pipeline" group (or wherever `SkillSynthesizer` lives today).

**Quick check before modifying:** Read the current `forge_bridge/__init__.py` first; the grouping comment structure varies.

---

### 5. `projekt_forge/__main__.py` — LLMRouter construction, synthesizer wiring, callback registration

**Analog (primary):** Same file — existing `_run_mcp_only(args)` helper (lines 21–39).

**Why this analog:** Phase 5 Wave C already established the shape: read args/env, call `forge_bridge.bridge.configure(...)`, import MCP, hand off to `mcp.run()`. Phase 6 inserts the learning-pipeline init at the same lifecycle point — before the `mcp.run()` handoff, after the bridge is configured.

**Pattern to copy — config-read + constructor-injection at startup (projekt_forge/__main__.py:21–39):**

```python
def _run_mcp_only(args) -> None:
    """Blocking: configure the bridge and hand control to mcp.run()."""
    from forge_bridge.bridge import configure
    configure(host=args.bridge_host, port=args.bridge_port, timeout=args.bridge_timeout)

    from projekt_forge.server.mcp import mcp

    if args.http:
        print(
            f"Starting projekt-forge MCP server (HTTP:{args.port})",
            file=sys.stderr,
        )
        mcp.run(transport="streamable_http", port=args.port)
    else:
        mcp.run()  # stdio transport
```

**Secondary analog (config loader):** `projekt_forge/config/forge_config.py::load_forge_config()` (lines 43–63) — already exists, already imported from several call sites (see `projekt_forge/cli/launcher.py:8`). **Do not create a new loader** — reuse this one.

**Pattern to copy — YAML config read with env override (forge_config.py:43–63):**

```python
def load_forge_config() -> dict:
    """Read and return the forge config YAML as a dict."""
    import yaml
    config_path = _resolve_config_path()
    if not config_path.exists():
        raise RuntimeError(
            f"forge config not found at {config_path} — run 'forge install' first"
        )
    with open(config_path) as fh:
        return yaml.safe_load(fh)
```

**Secondary analog (DB session for callback target):** `projekt_forge/db/engine.py::get_engine()` (lines 20–39) and `async_sessionmaker` usage — the storage callback needs an async session to write `ExecutionRecord` rows. EXT-03 is deferred (CONTEXT.md domain §"Out of scope"), so Phase 6 implementation may be as thin as "write to JSON sidecar" or "stub that logs" — planner decides whether to do a full DB write now or a minimal stub. Either way, the async-session pattern is here.

**What's different — new code that goes into `__main__.py`:**

Phase 6 adds a new helper (or inlines into `_run_mcp_only` — planner decides) that:

1. **Loads forge_config.yaml once at startup** via the existing `load_forge_config()` — extract `local_url`, `local_model`, `system_prompt` keys. If the keys are absent, fall through to LLMRouter's env-var / hardcoded defaults (no-op injection — pass `None`).
2. **Constructs the `LLMRouter` once.** Explicit-args-with-`None`-fallback — matches Phase 4 pattern in forge-bridge's own `LLMRouter.__init__` (router.py:79–97):
   ```python
   from forge_bridge.llm.router import LLMRouter
   cfg = load_forge_config()
   llm_cfg = cfg.get("llm", {})
   router = LLMRouter(
       local_url=llm_cfg.get("local_url"),
       local_model=llm_cfg.get("local_model"),
       system_prompt=llm_cfg.get("system_prompt"),
   )
   ```
3. **Constructs `ExecutionLog` with per-project path** (LRN-01, D-15/D-16):
   ```python
   from pathlib import Path
   project_root = Path(os.environ.get("FORGE_PROJECT_ROOT", Path.home() / ".forge-bridge"))
   log_path = project_root / ".forge" / "executions.jsonl"
   execution_log = ExecutionLog(log_path=log_path)
   ```
4. **Registers the storage callback** (LRN-02):
   ```python
   async def _persist_execution(record):
       """Mirror execution record into projekt-forge DB. Best-effort."""
       from projekt_forge.db.engine import get_engine
       # ... open session, insert row ...
   execution_log.set_storage_callback(_persist_execution)
   ```
5. **Constructs `SkillSynthesizer` with `router=` and `pre_synthesis_hook=`** (LRN-03 + LRN-04):
   ```python
   async def _build_context(intent: str, params: dict) -> PreSynthesisContext:
       """Enrich synthesis prompt with projekt-forge project context."""
       # ... read active shot/roles/naming conventions from DB ...
       return PreSynthesisContext(
           extra_context="...",
           tags=[f"project:{project_code}", ...],
           constraints=["do not import flame"],
       )
   synthesizer = SkillSynthesizer(router=router, pre_synthesis_hook=_build_context)
   ```
6. **Insertion point:** All of the above runs **before** `mcp.run()` inside `_run_mcp_only()` (and inside `_run_mcp_server()`, which has the same shape at lines 42–56). Extract into a helper function `_init_learning_pipeline(args) -> None` so both call sites share it.

**CRITICAL — RWR-04 guard compatibility (CONTEXT.md canonical_refs §Phase 5):** Any new `from forge_bridge...` import added to `__main__.py` must resolve to the installed site-packages copy, not to `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/`. The Phase 5 pytest guard enforces this. No `sys.path` hackery; just import normally.

---

### 6. Tests — `tests/test_execution_log.py` and `tests/test_synthesizer.py`

**Analog (primary):** Same files — existing test shape.

**Why this analog:** Both test files already use `tmp_path` + instantiate-the-real-class + make-assertions patterns. New test cases slot alongside.

**Pattern to copy — `tmp_path` + ExecutionLog construction (test_execution_log.py:37–48):**

```python
def test_record_appends_jsonl(tmp_path):
    """ExecutionLog.record(code) appends a JSON line to the log file."""
    from forge_bridge.learning.execution_log import ExecutionLog

    log_path = tmp_path / "executions.jsonl"
    log = ExecutionLog(log_path=log_path)
    log.record("print('hello')")

    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert isinstance(rec, dict)
```

**Pattern to copy — AsyncMock for async-hook testing (test_synthesizer.py:8, 27):**

```python
from unittest.mock import AsyncMock, MagicMock, patch

# ...

mock = AsyncMock(return_value="")
with patch("forge_bridge.bridge.execute", mock):
    await fn(**sample_kwargs)
```

**New test cases the planner adds (minimum viable coverage):**

For `test_execution_log.py`:
1. `test_storage_callback_fires_on_record` — sync callback, assert called with `ExecutionRecord`.
2. `test_async_storage_callback_fires_on_record` — async callback (`@pytest.mark.asyncio`), assert awaited.
3. `test_storage_callback_error_does_not_break_jsonl_write` — callback raises, JSONL line still written, warning logged.
4. `test_set_storage_callback_none_clears` (Claude's Discretion — recommended yes per CONTEXT.md §Claude's Discretion).
5. `test_callback_receives_full_execution_record` — assert dataclass fields match.

For `test_synthesizer.py`:
1. `test_pre_synthesis_hook_invoked_with_intent_and_params` — AsyncMock hook, assert called with `(intent, params)` per D-09.
2. `test_pre_synthesis_hook_none_is_noop` — synthesis still works.
3. `test_pre_synthesis_context_extra_context_appended_to_system` — mock router, assert system prompt contains `ctx.extra_context`.
4. `test_pre_synthesis_context_constraints_injected` — similar.
5. `test_pre_synthesis_hook_exception_falls_back_to_empty_context` — hook raises, synthesis continues with default `PreSynthesisContext()`.

**What's different:** Async test cases need `@pytest.mark.asyncio`. Check existing tests/test_llm.py or tests/test_synthesizer.py for the exact decorator idiom already in use before adding new imports.

---

## Shared Patterns

### Exception isolation with logger.warning

**Source:** `forge_bridge/bridge.py:162–166` (bare `except: pass` — deprecated for our use) + `forge_bridge/learning/synthesizer.py:248–250` (the correct `logger.warning(...)` + return-sentinel pattern).

**Apply to:** Both LRN-02 callback dispatch AND LRN-04 pre-synthesis hook invocation.

**Correct pattern to copy (synthesizer.py:248–250):**

```python
try:
    raw = await self._router.acomplete(...)
except RuntimeError:
    logger.warning("LLM unavailable — skipping synthesis")
    return None
```

Generalize: narrow exception class if possible, `logger.warning(...)`, return a safe default, never re-raise into the caller's critical path.

---

### Constructor injection with `None` default + explicit fallback

**Source:** `forge_bridge/llm/router.py:79–97` (Phase 4 canonical example).

**Apply to:** LLMRouter construction in projekt_forge/__main__.py, SkillSynthesizer's new `pre_synthesis_hook=` param.

**Pattern (router.py:79–97):**

```python
def __init__(
    self,
    local_url: str | None = None,
    local_model: str | None = None,
    cloud_model: str | None = None,
    system_prompt: str | None = None,
) -> None:
    self.local_url = local_url or os.environ.get(
        "FORGE_LOCAL_LLM_URL", "http://localhost:11434/v1"
    )
    self.local_model = local_model or os.environ.get(
        "FORGE_LOCAL_MODEL", "qwen2.5-coder:32b"
    )
    # ... etc
```

The `None` → `or os.environ.get(...)` → `or hardcoded_default` chain is the house pattern. When consuming from projekt-forge, the chain shortens to `yaml_value or None` — the router itself fills in env/default.

---

### Frozen dataclass for internal structural types

**Source:** `forge_bridge/bridge.py:20–29` (`_BridgeConfig`).

**Apply to:** `PreSynthesisContext` and the new `ExecutionRecord` dataclass.

**Pattern:** `@dataclass(frozen=True)` + primitive field defaults inline + `field(default_factory=...)` for mutable defaults + no methods unless they're `@property` read-only computed values.

---

## No Analog Found

None. Every Phase 6 file/symbol has a strong in-codebase analog.

---

## Metadata

**Analog search scope:**
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/` (full tree)
- `/Users/cnoellert/Documents/GitHub/forge-bridge/tests/` (full tree)
- `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/__main__.py`
- `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/config/forge_config.py`
- `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/db/engine.py`, `models.py`
- `.planning/phases/04-api-surface-hardening/04-PATTERNS.md` (prior-phase pattern precedent)

**Files scanned:** ~12 source files read, ~40 cross-referenced via directory listing.

**Pattern extraction date:** 2026-04-17

*Phase: 06-learning-pipeline-integration*
