# Phase 15 (FB-C): LLMRouter Tool-Call Loop — Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 16 (8 source, 1 packaging, 7 tests)
**Analogs found:** 16 / 16 (100% — all files map to a closely related sibling)

---

## File Classification

| File | Type | Role | Data Flow | Closest Analog | Match Quality |
|------|------|------|-----------|----------------|---------------|
| `forge_bridge/llm/router.py` | MODIFY | service (router) | request-response + event-loop | `forge_bridge/llm/router.py` (self) | exact (extending) |
| `forge_bridge/llm/_adapters.py` | NEW | service (provider adapters + dataclasses + Protocol) | transform | `forge_bridge/learning/storage.py` (Protocol+docstring) + `forge_bridge/learning/execution_log.py` (dataclass cluster) | role-match (compose two analogs) |
| `forge_bridge/llm/_sanitize.py` | NEW | utility (sanitization helper) | transform | `forge_bridge/learning/sanitize.py` (`_sanitize_tag` shape) | role-match |
| `forge_bridge/_sanitize_patterns.py` | NEW | utility (constants module) | n/a (pure data) | `forge_bridge/learning/sanitize.py:50-62` (origin of hoisted constants) | exact (extracted) |
| `forge_bridge/learning/sanitize.py` | MODIFY | utility (re-export shim) | transform | `forge_bridge/llm_router.py` (existing backwards-compat shim pattern) | exact |
| `forge_bridge/learning/synthesizer.py` | MODIFY | service (AST safety walker) | static analysis | `forge_bridge/learning/synthesizer.py:119-143` (self) | exact (extending) |
| `forge_bridge/mcp/registry.py` | MODIFY | service (tool registry) | request-response | `forge_bridge/mcp/registry.py:129` (`register_tools`) | exact (sibling function) |
| `forge_bridge/__init__.py` | MODIFY | barrel | n/a | `forge_bridge/__init__.py:55` (self, Phase 8 grew it 15→16) | exact |
| `pyproject.toml` | MODIFY | config | n/a | `pyproject.toml` `[llm]` extra (already has `openai`/`anthropic`) | exact |
| `tests/llm/test_complete_with_tools.py` | NEW | test (coordinator unit) | event-driven (stub adapter) | `tests/test_llm.py` + `tests/test_synthesizer.py` (mock-router style) | role-match |
| `tests/llm/test_anthropic_adapter.py` | NEW | test (wire-format unit) | request-response (mocked HTTP) | `tests/conftest.py::mock_anthropic` + adapter unit pattern | role-match |
| `tests/llm/test_ollama_adapter.py` | NEW | test (wire-format unit) | request-response (mocked HTTP) | `tests/conftest.py::mock_openai` (OpenAI shim test pattern) | role-match |
| `tests/llm/test_sanitize_tool_result.py` | NEW | test (sanitization unit) | transform | `tests/test_sanitize.py` (`TestSanitizeTag` class layout) | exact |
| `tests/llm/test_recursive_guard.py` | NEW | test (contextvar + AST guard) | event-driven + static analysis | `tests/test_synthesizer.py::TestCheckSignature` (AST-walk test pattern) | role-match |
| `tests/llm/conftest.py` | NEW | test fixture | n/a | `tests/console/conftest.py` (subdir conftest pattern) | exact |
| `tests/integration/test_complete_with_tools_live.py` | NEW | test (live integration, env-gated) | request-response (real HTTP) | `tests/test_integration.py` (integration fixture pattern) + Phase 8 env-gated convention (newly introduced) | role-match (env-gating is greenfield) |

---

## Pattern Assignments

### `forge_bridge/llm/router.py` (MODIFY — service)

**Analog:** Self (extending). The new method `complete_with_tools()` slots into the same class alongside `acomplete()` (lines 105-132).

**Imports pattern** (lines 30-35) — extend with `asyncio`, `collections`, `contextvars`, `time`, `json`, `hashlib`, `logging`, `dataclasses` already covered. New stdlib needed:
```python
import collections     # for Counter (D-07 seen_calls state)
import contextvars     # for _in_tool_loop (D-12)
import hashlib         # for args_hash log field (D-26)
import json            # for args canonicalization (D-07)
import time            # for monotonic wall-clock (D-04)
from typing import Awaitable, Callable, TYPE_CHECKING
```

**Constructor kwargs > env vars > hardcoded defaults precedence** (lines 79-99 — the locked pattern any new `complete_with_tools` runtime knob follows):
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
    self.cloud_model = cloud_model or os.environ.get(
        "FORGE_CLOUD_MODEL", "claude-opus-4-6"
    )
    self.system_prompt = system_prompt or os.environ.get(
        "FORGE_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT
    )
    self._local_client: Optional["AsyncOpenAI"] = None  # type: ignore[name-defined]
    self._cloud_client: Optional["AsyncAnthropic"] = None  # type: ignore[name-defined]
```
Add a third lazy slot: `self._local_native_client: Optional["ollama.AsyncClient"] = None` for D-02.

**Lazy-import-with-RuntimeError pattern for new `_get_local_native_client()`** — copy `_get_cloud_client()` (lines 203-213) verbatim, swap names:
```python
def _get_cloud_client(self):
    if self._cloud_client is None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. "
                "Install LLM support: pip install forge-bridge[llm]"
            )
        self._cloud_client = AsyncAnthropic()
    return self._cloud_client
```
New `_get_local_native_client()` mirrors this 1-for-1 with `from ollama import AsyncClient` and `self._local_native_client = AsyncClient(host=self.local_url.rstrip("/v1") or "http://localhost:11434")`.

**Public method pattern (signature + docstring + sensitive routing)** — copy `acomplete()` (lines 105-132). The shape `if sensitive: <local-path> else: <cloud-path>` and the docstring with `Args/Returns/Raises` headers are mandatory:
```python
async def acomplete(
    self,
    prompt: str,
    sensitive: bool = True,
    system: Optional[str] = None,
    temperature: float = 0.1,
) -> str:
    """
    Generate a completion asynchronously.

    Args: ...
    Returns: ...
    Raises:
        RuntimeError: If the selected backend is unavailable.
    """
    if sensitive:
        return await self._async_local(prompt, system, temperature)
    return await self._async_cloud(prompt, system, temperature)
```
Apply to new `complete_with_tools()` — same docstring shape, same `if sensitive` branching to adapter selection (per research §4.1).

**Backend wrapper try/except pattern** (lines 219-237 — `_async_local`, the pattern for "wrap provider call, raise RuntimeError"):
```python
async def _async_local(
    self, prompt: str, system: Optional[str], temperature: float
) -> str:
    client = self._get_local_client()
    sys_msg = system if system is not None else self.system_prompt
    messages = []
    if sys_msg:
        messages.append({"role": "system", "content": sys_msg})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = await client.chat.completions.create(
            model=self.local_model,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Local LLM call failed ({self.local_url}): {e}")
```
**Important:** D-34 + Phase 8 cf221fe rule mandates `type(exc).__name__` not `str(exc)` in coordinator catches that may carry credentials. The new `complete_with_tools` exception handlers MUST log `type(exc).__name__` instead of the bare exception string.

**Exception class placement** — lives at module top of `router.py` per D-16 (matches `StoragePersistence` next to `ExecutionLog` pattern). Place all three exception classes between the `_DEFAULT_SYSTEM_PROMPT` block (line 53) and `class LLMRouter` (line 56). The `LLMLoopBudgetExceeded` `__init__` signature is locked verbatim from D-18 / research §4.1 lines 292-298.

**ContextVar pattern** — module-level singleton:
```python
import contextvars
_in_tool_loop: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_in_tool_loop", default=False
)
```
Set/reset via the D-12 token pattern inside `complete_with_tools()`. Both `acomplete()` and `complete_with_tools()` check `_in_tool_loop.get()` on entry per D-13.

---

### `forge_bridge/llm/_adapters.py` (NEW — service + dataclasses + Protocol)

**Analog (compose two):**
- **Module-docstring + Protocol shape:** `forge_bridge/learning/storage.py` (lines 72-98). Frozen dataclasses, `runtime_checkable` Protocol, contract documented in module docstring.
- **Dataclass cluster shape:** `forge_bridge/learning/execution_log.py:36-56` — `@dataclass(frozen=True) ExecutionRecord` plus a `Callable` type alias.

**Imports pattern** (copy `forge_bridge/learning/storage.py:72-77`):
```python
from __future__ import annotations

from typing import Awaitable, Protocol, Union, runtime_checkable

from forge_bridge.learning.execution_log import ExecutionRecord
```
For `_adapters.py` use:
```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from forge_bridge.llm._sanitize import _sanitize_tool_result  # NOT YET — likely no — only coordinator uses it

if TYPE_CHECKING:
    import anthropic
    import mcp.types
    import ollama

logger = logging.getLogger(__name__)
```

**Frozen dataclass pattern** — `forge_bridge/learning/execution_log.py:36-54` is the load-bearing analog for `ToolCallResult` (D-15, frozen, transparent fields):
```python
@dataclass(frozen=True)
class ExecutionRecord:
    """Payload delivered to storage callbacks after every ExecutionLog.record() write.
    ...
    Frozen so consumer code cannot mutate state shared between the log write and
    the callback fire.
    """

    code_hash: str
    raw_code: str
    intent: Optional[str]
    timestamp: str
    promoted: bool
```
Apply to `ToolCallResult` (D-15, research §4.1 lines 305-311). `_TurnResponse` and `_ToolCall` may be plain `@dataclass` (mutable) since the coordinator builds them up turn-by-turn; copy the shape from research §4.4 lines 484-496.

**Protocol declaration pattern** — `forge_bridge/learning/storage.py:79-98`:
```python
@runtime_checkable
class StoragePersistence(Protocol):
    """Typed contract for durable-storage mirrors of ExecutionLog writes (STORE-01, D-02, D-03).

    Implementations MUST provide a `persist` method. ...
    """

    def persist(self, record: ExecutionRecord) -> Union[None, Awaitable[None]]: ...
```
Apply to `_ToolAdapter` Protocol per research §4.4 lines 474-480. **Decision per D-09 spirit (minimum API surface):** `_ToolAdapter` is internal — leave OFF `@runtime_checkable` decorator (no isinstance use case).

**Module-level frozenset constant pattern** — `forge_bridge/learning/synthesizer.py:108-110`:
```python
_DANGEROUS_CALLS: frozenset[str] = frozenset({
    "eval", "exec", "__import__", "compile", "execfile",
})
```
Apply to D-29:
```python
_OLLAMA_TOOL_MODELS: frozenset[str] = frozenset({
    "qwen3:32b", "qwen3-coder:32b", "qwen2.5-coder:32b",
    "llama3.1:70b", "mixtral:8x22b",
})
```

**Lazy-import-then-instantiate inside the adapter constructor** — mirrors `LLMRouter._get_cloud_client()` (router.py:203-213). Adapter constructors should NOT lazy-import; they receive an already-instantiated client (the router owns the lazy slot per D-02). Adapter signatures per research §4.1 lines 350-355:
```python
adapter = (
    OllamaToolAdapter(self._get_local_native_client(), self.local_model)
    if sensitive
    else AnthropicToolAdapter(self._get_cloud_client(), self.cloud_model)
)
```

---

### `forge_bridge/llm/_sanitize.py` (NEW — utility)

**Analog:** `forge_bridge/learning/sanitize.py` (`_sanitize_tag()` lines 80-118).

**Module-docstring + imports + module-level logger pattern** — `forge_bridge/learning/sanitize.py:1-34`:
```python
"""Sanitization and size-budget enforcement for consumer-supplied tag payloads.

Per PROV-03 / PITFALL P-02.5: ...
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)
```
For `_sanitize.py`:
```python
"""Tool-result sanitization for the FB-C LLMRouter tool-call loop.

Per LLMTOOL-06 (D-11): every tool result string is sanitized before feeding
back to the LLM. Strips ASCII control chars (except \\n, \\t), replaces
injection markers inline with [BLOCKED:INJECTION_MARKER], and truncates to
_TOOL_RESULT_MAX_BYTES. Helpers in forge_bridge/learning/sanitize.py and
this module both import the patterns from forge_bridge._sanitize_patterns
to keep one source of truth (D-09).
"""
from __future__ import annotations

import logging
from forge_bridge._sanitize_patterns import INJECTION_MARKERS, _CONTROL_CHAR_RE

logger = logging.getLogger(__name__)

_TOOL_RESULT_MAX_BYTES: int = 8192
```

**Helper function shape (single doc-stringed function returning a transformed string)** — copy `_sanitize_tag()` lines 80-118 with the **critical semantic change** noted in `<specifics>`:
```python
def _sanitize_tag(tag: Any) -> Optional[str]:
    """Return the sanitized tag, or None if rejected.

    Rejection cases (all log WARNING once):
      - Non-string input
      - Empty string
      - Contains control chars (\\x00-\\x1f, \\x7f)
      - Contains any INJECTION_MARKERS

    Transformation:
      - Allowlist prefix match -> pass through, truncate to MAX_TAG_CHARS
      - Otherwise -> `"redacted:" + sha256(tag.encode("utf-8")).hexdigest()[:8]`
    """
    if not isinstance(tag, str):
        logger.warning("tag rejected (not a string): %s", _truncate_for_log(tag))
        return None
    ...
    if _CONTROL_CHAR_RE.search(tag):
        logger.warning("tag rejected (control char): %s", _truncate_for_log(tag))
        return None
    tag_lower = tag.lower()
    for marker in INJECTION_MARKERS:
        if marker.lower() in tag_lower:
            logger.warning(
                "tag rejected (injection marker %r): %s",
                marker,
                _truncate_for_log(tag),
            )
            return None
    ...
```
**Semantic divergence (per `<specifics>` and D-11):** `_sanitize_tool_result()` REPLACES inline (does NOT return None). The skeleton:
```python
def _sanitize_tool_result(text: str, max_bytes: int = _TOOL_RESULT_MAX_BYTES) -> str:
    """Sanitize a tool result string before feeding it back to the LLM."""
    # 1. Strip control chars (preserve \n, \t — re-insert via a 2-pass strip + restore)
    ...
    # 2. Replace each INJECTION_MARKERS substring (case-insensitive) inline
    #    with the literal token "[BLOCKED:INJECTION_MARKER]". Log WARNING once
    #    per marker hit (use _truncate_for_log style).
    ...
    # 3. Truncate to max_bytes; suffix "\n[...truncated, full result was {n} bytes]"
    encoded = text.encode("utf-8")
    if len(encoded) > max_bytes:
        return encoded[:max_bytes].decode("utf-8", errors="ignore") + (
            f"\n[...truncated, full result was {len(encoded)} bytes]"
        )
    return text
```

---

### `forge_bridge/_sanitize_patterns.py` (NEW top-level — utility constants)

**Analog:** `forge_bridge/learning/sanitize.py:50-62` (the constants being hoisted, verbatim).

**Source excerpt to extract verbatim** (sanitize.py:50-62):
```python
# Injection markers — presence in a tag -> reject entirely
INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous",
    "<|",
    "|>",
    "[INST]",
    "[/INST]",
    "<|im_start|>",
    "```",  # triple backtick — markdown code fence
    "---",  # yaml document separator
)

# Control characters: \x00-\x1f plus \x7f (DEL)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
```

**Module skeleton** (minimum surface — D-09 mandates "Hoist patterns, NOT helpers"):
```python
"""forge_bridge._sanitize_patterns — single source of truth for sanitization patterns.

Both forge_bridge/learning/sanitize.py (Phase 7 PROV-03 — tag sanitization) and
forge_bridge/llm/_sanitize.py (FB-C LLMTOOL-06 — tool-result sanitization)
import the patterns from this module. The HELPERS are NOT centralized — each
consumer owns its own rejection semantics:

  - learning.sanitize._sanitize_tag(): REJECTS the entire tag on marker hit.
  - llm._sanitize._sanitize_tool_result(): REPLACES inline with [BLOCKED:INJECTION_MARKER].

Different consumers, different semantics, same pattern set.
"""
from __future__ import annotations

import re

INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous",
    "<|",
    "|>",
    "[INST]",
    "[/INST]",
    "<|im_start|>",
    "```",
    "---",
)

_CONTROL_CHAR_RE: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]")
```

---

### `forge_bridge/learning/sanitize.py` (MODIFY — re-export shim)

**Analog:** `forge_bridge/llm_router.py` (existing top-level shim from Phase 1, exact backwards-compat pattern).

**Backwards-compat shim pattern** — `forge_bridge/llm_router.py` (the file that exists for test_llm_shim_import per `tests/test_llm.py:216-225`):
```python
from forge_bridge.llm.router import LLMRouter, get_router

__all__ = ["LLMRouter", "get_router"]
```

**Application to D-10:** sanitize.py keeps `_sanitize_tag()` and `apply_size_budget()` IN PLACE (helpers don't move). The two constants get replaced with the re-export:

Before (sanitize.py:50-62):
```python
INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous", ...
)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
```

After:
```python
# Re-exported from forge_bridge._sanitize_patterns to keep one source of truth
# (FB-C D-09/D-10). watcher and registry callers continue to import from this
# module unchanged.
from forge_bridge._sanitize_patterns import INJECTION_MARKERS, _CONTROL_CHAR_RE  # noqa: F401
```

**Verified caller invariant (from CONTEXT.md D-10):**
- `forge_bridge/learning/watcher.py:17` imports `_sanitize_tag, apply_size_budget` — unchanged.
- `forge_bridge/mcp/registry.py:90` references `_sanitize_tag` in comment only — unchanged.

---

### `forge_bridge/learning/synthesizer.py` (MODIFY — extend `_check_safety()`)

**Analog:** Self — `_check_safety()` (lines 119-143) is the existing AST-walk pattern that D-14 extends.

**Existing AST walk skeleton to extend in-place** (synthesizer.py:119-143):
```python
def _check_safety(tree: ast.Module) -> bool:
    """Return True if the AST contains no dangerous calls, False otherwise.

    Scans for:
    - Bare dangerous calls: eval(), exec(), __import__(), compile()
    - Dangerous attribute calls: os.system(), subprocess.run(), shutil.rmtree(), etc.
    - open() calls that are not calling bridge functions
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check bare name calls: eval(...), exec(...), __import__(...)
            if isinstance(node.func, ast.Name) and node.func.id in _DANGEROUS_CALLS:
                return False
            # Check open() — only allowed inside forge_bridge.bridge calls
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                return False
            # Check attribute calls: os.system(...), subprocess.run(...)
            if isinstance(node.func, ast.Attribute):
                attr_name = node.func.attr
                if isinstance(node.func.value, ast.Name):
                    module_name = node.func.value.id
                    if module_name in _DANGEROUS_ATTR_CALLS:
                        if attr_name in _DANGEROUS_ATTR_CALLS[module_name]:
                            return False
    return True
```

**D-14 extension pattern** — add a parallel branch inside the same `for node in ast.walk(tree):` loop. Same structure: an `isinstance(node, ast.Import)` branch and an `isinstance(node, ast.ImportFrom)` branch, each checking the module name prefix:
```python
        # FB-C LLMTOOL-07 (D-14): block recursive synthesis by rejecting any
        # synthesized code that imports from forge_bridge.llm.
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "forge_bridge.llm" or alias.name.startswith("forge_bridge.llm."):
                    return False
        if isinstance(node, ast.ImportFrom):
            if node.module and (
                node.module == "forge_bridge.llm"
                or node.module.startswith("forge_bridge.llm.")
            ):
                return False
```

---

### `forge_bridge/mcp/registry.py` (MODIFY — add `invoke_tool`)

**Analog:** `register_tools()` (lines 129-169) — sibling public function in the same module.

**Public function shape** (registry.py:129-169):
```python
def register_tools(
    mcp: FastMCP,
    fns: list[Callable[..., Any]],
    prefix: str = "",
    source: str = "user-taught",
) -> None:
    """Register multiple tools under a shared prefix and source tag.

    Public API for downstream consumers (e.g. projekt-forge).

    Usage (before mcp.run()):
        from forge_bridge.mcp import register_tools, get_mcp
        register_tools(get_mcp(), [my_fn1, my_fn2], prefix="forge_")

    Note: Must be called before mcp.run(). ...

    Raises:
        RuntimeError: If called after mcp.run() has started. ...

    Args:
        mcp:    The live FastMCP instance.
        fns:    List of callables to register.
        prefix: Prefix prepended to each fn.__name__ to form the tool name.
        source: Source tag for all tools in this batch.
    """
    # Lazy import avoids the server.py -> registry.py -> server.py cycle.
    import forge_bridge.mcp.server as _server
    if _server._server_started:
        raise RuntimeError(...)
    for fn in fns:
        ...
```

**D-21 application:** add a NEW public function in registry.py (after `register_tools`, before `register_builtins`). The new function signature per D-21 / D-22 / research §4.1:
```python
async def invoke_tool(name: str, args: dict) -> str:
    """Default tool executor for LLMRouter.complete_with_tools (FB-C LLMTOOL).

    Looks up `name` against the live FastMCP tool registry, calls the tool with
    `args`, and returns the result as a string. Coordinator handles all
    sanitization/truncation downstream.

    Args:
        name: Tool name (must match a registered MCP tool — e.g. flame_*, forge_*, synth_*).
        args: Tool arguments dict (JSON-shaped).

    Returns:
        Tool result as a string. Tools that return dicts are JSON-stringified.

    Raises:
        KeyError: If `name` is not a registered tool (caller surfaces to LLM as
                  hallucinated-tool-name error per research §4.3).
        Exception: Tool-internal exceptions propagate to the caller (the
                   coordinator wraps them as is_error=True ToolCallResult).
    """
    # Lazy import — same anti-cycle pattern as register_tools (line 159).
    from forge_bridge.mcp.server import mcp as _mcp
    # FastMCP tool storage internals: see _tool_manager._tools dict
    ...
```

The coordinator's invocation pattern from research §4.1 lines 348-350:
```python
if tool_executor is None:
    from forge_bridge.mcp.registry import invoke_tool
    tool_executor = invoke_tool
```

**Module re-export note:** D-21 deferred the question of whether `invoke_tool` should be re-exported from `forge_bridge.mcp.__init__`. Current barrel (mcp/__init__.py:15) is `__all__ = ["register_tools", "get_mcp"]` — planner decides whether to grow to `["register_tools", "get_mcp", "invoke_tool"]`. Recommended: yes, mirror `register_tools` symmetry.

---

### `forge_bridge/__init__.py` (MODIFY — barrel growth 16 → 19)

**Analog:** Self — Phase 8 grew `__all__` 15→16 by adding `StoragePersistence`. The exact same growth shape applies for FB-C 16→19.

**Existing barrel pattern** (`forge_bridge/__init__.py:31-77`):
```python
# LLM routing
from forge_bridge.llm.router import LLMRouter, get_router

# Learning pipeline
from forge_bridge.learning.execution_log import (
    ExecutionLog,
    ExecutionRecord,
    StorageCallback,
)
from forge_bridge.learning.storage import StoragePersistence
...

__all__ = [
    # LLM routing
    "LLMRouter",
    "get_router",
    # Learning pipeline
    ...
    "StoragePersistence",
    ...
]
```

**D-15 extension:**
```python
# LLM routing
from forge_bridge.llm.router import (
    LLMRouter,
    get_router,
    LLMLoopBudgetExceeded,
    RecursiveToolLoopError,
    LLMToolError,
)
...
__all__ = [
    # LLM routing
    "LLMRouter",
    "get_router",
    "LLMLoopBudgetExceeded",
    "RecursiveToolLoopError",
    "LLMToolError",
    # Learning pipeline
    ...
]
```

**Public-API contract test:** `tests/test_public_api.py` already enforces `__all__` is the surface. New entries MUST be added there too — verify by grepping for `"StoragePersistence"` in that file and replicating the assertion shape for the three new exception classes.

---

### `pyproject.toml` (MODIFY — add `ollama` to `[llm]` extra)

**Analog:** Self — `[project.optional-dependencies].llm` already pins `openai`/`anthropic` (lines 28-31).

**Existing pattern** (pyproject.toml:27-31):
```toml
[project.optional-dependencies]
llm = [
    "openai>=1.0",
    "anthropic>=0.25",
]
```

**D-02 extension** — add one line (research §3 + D-02 specify `ollama>=0.6.1,<1`); also bump `anthropic` per research §1 (`>=0.97,<1`):
```toml
[project.optional-dependencies]
llm = [
    "openai>=1.0",
    "anthropic>=0.97,<1",
    "ollama>=0.6.1,<1",
]
```

---

### `tests/llm/test_complete_with_tools.py` (NEW — coordinator unit tests)

**Analog:** `tests/test_llm.py` (existing router tests) + `tests/test_synthesizer.py::TestSkillSynthesizer` (mock-router-with-AsyncMock pattern).

**File header / docstring pattern** (`tests/test_llm.py:1-21`):
```python
"""
Wave 0 test scaffolds for Phase 1 LLM Router requirements (LLM-01 through LLM-08).

Tests marked @pytest.mark.skip are stubs to be unskipped as implementation lands.
test_llm_shim_import is not skipped — it verifies the backwards-compat shim in
forge_bridge/llm_router.py which already exists.

Requirements covered:
    LLM-01  forge_bridge.llm.router.LLMRouter class exists, importable
    ...
"""

import pytest
```
Apply: list LLMTOOL-03..07 acceptance tests in the file header.

**Async test pattern (auto mode — no decorator)** (`tests/test_staged_operations.py:17`): "pytest-asyncio is in `auto` mode — no @pytest.mark.asyncio decorator needed." Functions starting `async def test_*` Just Work.

**Mock-router AsyncMock pattern** (`tests/test_synthesizer.py:148-153`):
```python
async def test_returns_path_on_valid_llm_output(self, tmp_path):
    from forge_bridge.learning.synthesizer import SkillSynthesizer

    mock_router = MagicMock()
    mock_router.acomplete = AsyncMock(return_value=VALID_SYNTH_CODE)

    synth = SkillSynthesizer(router=mock_router, synthesized_dir=tmp_path)
    result = await synth.synthesize("some code", "get shot name", 5)
```
Apply via `_StubAdapter` (D-37) — fixture-loaded from `tests/llm/conftest.py`.

**Test class organization** (`tests/test_sanitize.py:19`): one class per concept (`TestSanitizeTag`, `TestApplySizeBudget`, `TestAllowlistConstant`). For coordinator tests, organize:
- `TestLoopTermination` (LLMTOOL-01 happy path, terminal end_turn)
- `TestRepeatCallDetection` (LLMTOOL-04 — D-07 third-call synthetic injection)
- `TestBudgetCaps` (LLMTOOL-03 — max_iterations, max_seconds, per-tool 30s ceiling)
- `TestHallucinatedToolName` (research §4.3 — coordinator catches before invocation)
- `TestEmptyToolsRejection` (D-23 — `ValueError`)
- `TestToolResultSanitization` (LLMTOOL-06 — coordinator invokes `_sanitize_tool_result()`)

---

### `tests/llm/test_anthropic_adapter.py` (NEW — wire-format unit tests)

**Analog:** `tests/test_synthesizer.py` (mock-LLM unit) + `tests/conftest.py::mock_anthropic` fixture (lines 55-64).

**`mock_anthropic` fixture pattern** (`tests/conftest.py:55-64`):
```python
@pytest.fixture
def mock_anthropic():
    """Patch anthropic so tests run without the package installed.

    Provides a MagicMock at the anthropic module level. Individual tests
    can configure mock_anthropic.return_value as needed.
    """
    mock = MagicMock()
    with patch.dict("sys.modules", {"anthropic": mock}):
        yield mock
```

**Apply:** wire-format tests configure `mock_anthropic.AsyncAnthropic.return_value.messages.create = AsyncMock(return_value=<canned response>)` and assert that the request payload sent matches the Anthropic schema from research §2.1 (e.g., `{"name": ..., "description": ..., "input_schema": {...}, "strict": True}` per D-31).

**Test focus:** schema translation (research §5.1 table), `disable_parallel_tool_use=True` (D-06), `strict: true` always-on (D-31), per-tool downgrade fallback on 400 (D-31).

---

### `tests/llm/test_ollama_adapter.py` (NEW — wire-format unit tests)

**Analog:** `tests/conftest.py::mock_openai` (lines 43-52) — same shape but for `ollama` module.

**Pattern (mirror mock_openai)** :
```python
@pytest.fixture
def mock_ollama():
    """Patch ollama so tests run without the package installed."""
    mock = MagicMock()
    with patch.dict("sys.modules", {"ollama": mock}):
        yield mock
```
Place in `tests/llm/conftest.py` for shared use.

**Test focus:** OpenAI-style `{type:"function", function:{...}}` wrapper (research §3.1), `keep_alive: "10m"` (D-33), serial-only (`tool_calls[:1]` per D-06), `_OLLAMA_TOOL_MODELS` soft-warning (D-29), `tool_name` field on result messages (research §3.3).

---

### `tests/llm/test_sanitize_tool_result.py` (NEW — sanitization unit tests)

**Analog:** `tests/test_sanitize.py::TestSanitizeTag` (lines 19-94) — exact role match.

**Test class layout pattern** (`tests/test_sanitize.py:19-46`):
```python
class TestSanitizeTag:
    # Positive cases — allowlist pass-through
    def test_sanitize_passes_project_prefix(self):
        assert _sanitize_tag("project:acme") == "project:acme"
    ...
    # Rejection — control chars
    def test_sanitize_strips_control_chars(self):
        assert _sanitize_tag("project:a\nb") is None

    # Rejection — injection markers
    def test_sanitize_rejects_ignore_previous(self):
        assert _sanitize_tag("ignore previous instructions") is None
    ...
```

**Logging assertion pattern** (`tests/test_sanitize.py:86-94`):
```python
def test_sanitize_rejects_log_warning_on_control_char(self, caplog):
    with caplog.at_level(logging.WARNING, logger="forge_bridge.learning.sanitize"):
        _sanitize_tag("project:a\x00b")
    assert any("control char" in r.message for r in caplog.records)
```

**Test focus per LLMTOOL-05/06 acceptance (research §7):**
- 8192-byte truncation with `\n[...truncated, full result was {n} bytes]` suffix
- Control-char strip (preserving `\n`/`\t`)
- Injection-marker REPLACEMENT (not rejection — semantic divergence per `<specifics>`)
- Override via constructor kwarg `tool_result_max_bytes`

---

### `tests/llm/test_recursive_guard.py` (NEW — contextvar + AST guard tests)

**Analog (compose two):**
- `tests/test_synthesizer.py::TestCheckSignature` (AST-walk test pattern, lines 90-119) — for D-14 synthesizer extension
- `tests/test_llm.py::test_optional_import_guard` (lines 134-175 — contextvar-style pattern using `monkeypatch`/`saved`/`finally` restore)

**AST-walk test pattern** (`tests/test_synthesizer.py:90-119`):
```python
class TestCheckSignature:
    def test_valid_function_returns_name(self):
        from forge_bridge.learning.synthesizer import _check_signature
        tree = ast.parse(VALID_SYNTH_CODE)
        assert _check_signature(tree) == "synth_get_shot_name"

    def test_rejects_sync_function(self):
        from forge_bridge.learning.synthesizer import _check_signature
        tree = ast.parse(SYNC_FUNCTION_CODE)
        assert _check_signature(tree) is None
```

**Apply for D-14:**
```python
RECURSIVE_LLM_CODE = textwrap.dedent('''
    async def synth_recursive(prompt: str) -> str:
        """Bad: imports from forge_bridge.llm."""
        from forge_bridge.llm.router import LLMRouter
        router = LLMRouter()
        return await router.acomplete(prompt)
''')

class TestSafetyForgeBridgeLlmImport:
    def test_rejects_import_from_forge_bridge_llm(self):
        from forge_bridge.learning.synthesizer import _check_safety
        tree = ast.parse(RECURSIVE_LLM_CODE)
        assert _check_safety(tree) is False
```

**Contextvar test pattern (LLMTOOL-07 acceptance per research §7):**
```python
async def test_recursive_call_raises():
    from forge_bridge.llm.router import LLMRouter, RecursiveToolLoopError
    router = LLMRouter()

    async def evil_executor(name, args):
        # Try to recurse — should raise on entry.
        return await router.acomplete("inner call")

    with pytest.raises(RecursiveToolLoopError):
        await router.complete_with_tools(
            "outer", tools=[<one stub tool>], tool_executor=evil_executor,
        )
```

---

### `tests/llm/conftest.py` (NEW — shared fixtures)

**Analog:** `tests/console/conftest.py` (subdir conftest pattern — lines 1-69).

**Subdir conftest header pattern** (`tests/console/conftest.py:1-22`):
```python
"""Shared fixtures for tests/console/ — FB-B HTTP handler integration tests.

Shared fixtures extracted here per PLAN.md Task 2 Claude's Discretion directive:
both test_staged_handlers_list.py and test_staged_handlers_writes.py use these
to avoid duplication.

Requires: session_factory fixture from tests/conftest.py (Phase 13 deliverable).
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app
...
```

**`_StubAdapter` fixture pattern (D-37):**
```python
"""Shared fixtures for tests/llm/ — FB-C LLMRouter tool-call loop tests.

Provides _StubAdapter (D-37) — a deterministic adapter that replays a scripted
sequence of _TurnResponse. Lets every loop-logic test be deterministic without
a live LLM.
"""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge_bridge.llm._adapters import _TurnResponse, _ToolCall, ToolCallResult


@dataclass
class _StubState:
    history: list = None


class _StubAdapter:
    """Deterministic adapter that replays a scripted sequence of _TurnResponse."""
    supports_parallel = False

    def __init__(self, scripted_responses: list[_TurnResponse]) -> None:
        self._scripted = list(scripted_responses)

    def init_state(self, *, prompt, system, tools, temperature) -> _StubState:
        return _StubState(history=[{"role": "user", "content": prompt}])

    async def send_turn(self, state: _StubState) -> _TurnResponse:
        return self._scripted.pop(0)

    def append_results(self, state, response, results) -> _StubState:
        # No-op for tests (or append minimal state if needed by next turn assertion)
        return state


@pytest.fixture
def stub_adapter():
    return _StubAdapter
```

---

### `tests/integration/test_complete_with_tools_live.py` (NEW — env-gated live tests)

**Analog:** `tests/test_integration.py` (existing integration test file, lines 1-50) for general integration shape; **env-gating pattern is greenfield** (CONTEXT.md D-32 cites Phase 8 precedent but no `FB_INTEGRATION_TESTS` skip currently exists — first instance lands here).

**Integration test header pattern** (`tests/test_integration.py:1-12`):
```python
"""
forge-bridge integration tests.

Spins up a real ForgeServer on a random port (no Postgres required —
uses SQLite via the test fixture), connects both async and sync clients,
and exercises the full request/response/event cycle.

Run with: pytest tests/test_integration.py -v
...
"""
from __future__ import annotations

import asyncio
...
```

**Env-gating pattern (NEW — codify here):**
```python
import os
import pytest

requires_integration = pytest.mark.skipif(
    os.environ.get("FB_INTEGRATION_TESTS") != "1",
    reason="live LLM integration tests require FB_INTEGRATION_TESTS=1",
)

requires_anthropic = pytest.mark.skipif(
    os.environ.get("FB_INTEGRATION_TESTS") != "1"
    or not os.environ.get("ANTHROPIC_API_KEY"),
    reason="LLMTOOL-02 cloud test requires FB_INTEGRATION_TESTS=1 and ANTHROPIC_API_KEY",
)

@requires_integration
async def test_ollama_tool_call_loop_live():
    """LLMTOOL-01: live Ollama loop against assist-01."""
    from forge_bridge.llm.router import LLMRouter
    ...

@requires_anthropic
async def test_anthropic_tool_call_loop_live():
    """LLMTOOL-02: live Anthropic loop."""
    ...
```

**Note for planner:** `tests/integration/` directory does NOT yet exist — Plan must create it with an empty `__init__.py` to mirror `tests/console/__init__.py` and `tests/mcp/__init__.py`.

---

## Shared Patterns

### Lazy-import-with-RuntimeError (cross-file)

**Source:** `forge_bridge/llm/router.py:188-213` (`_get_local_client` and `_get_cloud_client`).

**Apply to:** `_get_local_native_client()` (new method on `LLMRouter` for D-02 ollama client).

```python
def _get_cloud_client(self):
    if self._cloud_client is None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. "
                "Install LLM support: pip install forge-bridge[llm]"
            )
        self._cloud_client = AsyncAnthropic()
    return self._cloud_client
```

### Module-level frozenset constant (cross-file)

**Source:** `forge_bridge/learning/synthesizer.py:108-110` and `forge_bridge/learning/sanitize.py:50-59`.

**Apply to:** `_OLLAMA_TOOL_MODELS` in `_adapters.py` (D-29).

```python
_DANGEROUS_CALLS: frozenset[str] = frozenset({
    "eval", "exec", "__import__", "compile", "execfile",
})
```

### `from __future__ import annotations` always-first

**Source:** Every modified file in `forge_bridge/` has it at line 1 (verified: `learning/synthesizer.py:8`, `learning/sanitize.py:26`, `mcp/registry.py:18`, `mcp/__init__.py:2`).

**Apply to:** All new files (`_adapters.py`, `_sanitize.py`, `_sanitize_patterns.py`, every test file).

### Module-level logger

**Source:** Every consumer module — `learning/sanitize.py:34`, `learning/synthesizer.py:29`, `learning/watcher.py:25`, `learning/execution_log.py:25`:
```python
import logging
logger = logging.getLogger(__name__)
```

**Apply to:** All new modules (`_adapters.py`, `_sanitize.py`).

### Credential-leak prevention

**Source:** Phase 8 cf221fe convention + `forge_bridge/cli/doctor.py:198`:
> "Reports parse failures by line number + exception class name only — never raw line content (LRN-05 / T-11-01 credential-leak rule)."

**Apply to:** All exception handlers in `complete_with_tools()` that catch provider errors (Anthropic/Ollama 5xx may carry credentials in headers/messages):
```python
except Exception as exc:
    logger.warning("provider call failed: %s", type(exc).__name__)  # NOT str(exc)
    raise LLMToolError(f"provider call failed: {type(exc).__name__}") from exc
```

### Public exception classes inherit RuntimeError

**Source:** Project CONVENTIONS.md (line 67) + `forge_bridge/learning/storage.py` exports + `forge_bridge/llm/router.py:237` (`raise RuntimeError(f"Local LLM call failed ...")`).

**Apply to:** All three new exception classes (D-15) — `LLMLoopBudgetExceeded`, `RecursiveToolLoopError`, `LLMToolError`. Per D-18 the `LLMLoopBudgetExceeded.__init__` signature is locked.

### Single-line key=value structured log

**Source:** Per CONTEXT.md D-24/D-25 — Phase 8 LRN-05 + Phase 9 console handlers (greppable, single-line). No verbatim analog inside the code today; D-24 establishes the convention for FB-C.

**Apply to:** Per-turn `logger.info` line (D-24) and per-session terminal line (D-25). Format:
```
tool-call iter=1 tool=forge_list_staged args_hash=ab12cd34 prompt_tokens=412 completion_tokens=78 elapsed_ms=823 status=continuing
```

---

## No Analog Found

All 16 files map to a close existing analog. The closest cases to "no analog":

| File | Why Partial | Mitigation |
|------|-------------|------------|
| `tests/integration/test_complete_with_tools_live.py` | `tests/integration/` directory does not exist; `FB_INTEGRATION_TESTS=1` env-gating is greenfield (CONTEXT.md cites Phase 8 precedent but no skipif use found in `tests/`) | Codify the pattern in this file; subsequent live-integration tests (FB-D, etc.) follow it |
| Per-turn structured log line (D-24) | Documented as Phase 8 LRN-05 / Phase 9 shape, but no exact verbatim grep match in current source | Establish the format inside `complete_with_tools()` per D-24; document in router.py module docstring for FB-D to copy |

---

## Metadata

**Analog search scope:**
- `forge_bridge/llm/` (router.py, health.py, __init__.py)
- `forge_bridge/learning/` (sanitize.py, synthesizer.py, storage.py, execution_log.py, watcher.py, probation.py)
- `forge_bridge/mcp/` (registry.py, server.py, tools.py, __init__.py)
- `forge_bridge/__init__.py`, `pyproject.toml`
- `tests/test_llm.py`, `tests/test_sanitize.py`, `tests/test_synthesizer.py`, `tests/test_storage_protocol.py`, `tests/test_integration.py`, `tests/test_staged_operations.py`
- `tests/console/conftest.py`, `tests/conftest.py`, `tests/mcp/`
- `.planning/codebase/CONVENTIONS.md`

**Files scanned:** ~50 source/test files

**Pattern extraction date:** 2026-04-26
