# Phase 3: Learning Pipeline - Research

**Researched:** 2026-04-14
**Domain:** Python AST normalization, JSONL append logging, LLM-powered code synthesis, MCP hot-registration, probation systems
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LEARN-01 | Create forge_bridge/learning/ package with execution_log.py | Package skeleton exists (`__init__.py` only). execution_log.py must be created. |
| LEARN-02 | JSONL execution log at ~/.forge-bridge/executions.jsonl with append-only writes | Verified: `open(path, 'a')` + `json.dumps(record) + '\n'` is crash-safe. Path confirmed: `Path.home() / '.forge-bridge' / 'executions.jsonl'`. |
| LEARN-03 | Replay JSONL on startup to rebuild in-memory promotion counters | Pattern: read all lines on `ExecutionLog.__init__`, count hashes, mark already-promoted so synthesis not re-triggered. |
| LEARN-04 | AST-based code normalization (ast.unparse with literal stripping) and SHA-256 hash fingerprinting | Verified: `ast.parse` + `LiteralStripper(NodeTransformer)` + `ast.unparse` + `hashlib.sha256`. Works in Python 3.10+. |
| LEARN-05 | Promotion threshold counter (configurable, default 3) returning promoted=True signal | Simple `dict[str, int]` counter per hash, configurable via `FORGE_PROMOTION_THRESHOLD` env var. |
| LEARN-06 | Intent tracking — optional intent string logged alongside code for synthesis prompt enrichment | `intent: Optional[str]` field in JSONL record. Passed through to synthesizer prompt. |
| LEARN-07 | Create forge_bridge/learning/synthesizer.py targeting Python MCP tools | New module. LLM prompt template verified. Writes async function to `~/.forge-bridge/synthesized/synth_*.py`. |
| LEARN-08 | Synthesizer uses LLM router as backend with sensitive=True (always local, production code in prompts) | LLM router already built in Phase 1. Call `get_router().acomplete(prompt, sensitive=True, temperature=0.1)`. |
| LEARN-09 | Synthesized tool validation: ast.parse, function signature check, sample parameter dry-run | Three-stage validated approach: (1) `ast.parse`, (2) AST signature walk, (3) importlib load + async call with mocked bridge. |
| LEARN-10 | Probation system: success/failure counters per synthesized tool, quarantine on threshold breach | ProbationTracker singleton. Wraps synthesized callables before registration. Quarantine = move to `~/.forge-bridge/quarantined/`, then `mcp.remove_tool()`. |
| LEARN-11 | Wire execution logging into bridge.py as optional on_execution callback (off by default) | Module-level `_on_execution_callback: Optional[Callable]` in bridge.py. Set via `bridge.set_execution_callback(fn)`. |
</phase_requirements>

---

## Summary

Phase 3 builds the learning pipeline end-to-end: from execution capture in `bridge.py`, through JSONL persistence, AST normalization and fingerprinting, promotion threshold tracking, LLM synthesis, tool validation, file output, and probation-based quality gating.

The codebase entering Phase 3 already has:
- `forge_bridge/learning/__init__.py` — empty package stub
- `forge_bridge/learning/watcher.py` — fully implemented, hot-loads `.py` files from `~/.forge-bridge/synthesized/` into MCP via `importlib`
- `forge_bridge/mcp/registry.py` — `register_tool()` with namespace enforcement and source tagging
- `forge_bridge/llm/router.py` — `LLMRouter` with `acomplete(prompt, sensitive=True)` async API
- `forge_bridge/bridge.py` — `execute()` async function, no callback hook yet
- 100 passing tests; watcher and registry have full test coverage

Phase 3 adds three new modules to `forge_bridge/learning/`: `execution_log.py` (LEARN-01 to LEARN-06, LEARN-11), `synthesizer.py` (LEARN-07, LEARN-08, LEARN-09), and `probation.py` (LEARN-10). It also makes one targeted edit to `bridge.py` (LEARN-11).

The existing watcher in `forge_bridge/learning/watcher.py` watches `~/.forge-bridge/synthesized/` — the synthesizer must write tools there. This is the correct integration point: synthesizer writes file → watcher detects → watcher loads + registers.

**Primary recommendation:** Implement in dependency order: execution_log.py → bridge.py callback → synthesizer.py → probation.py. Wire them in the order they need to exist. The watcher integration is already done.

---

## Standard Stack

### Core (all stdlib or already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ast | stdlib | Parse, walk, normalize, unparse Python code | Only correct tool for code fingerprinting |
| hashlib | stdlib | SHA-256 fingerprinting of normalized code | Already used by watcher.py; consistent pattern |
| json | stdlib | JSONL serialization for execution log | Append-only, crash-safe, human-readable |
| pathlib | stdlib | File paths for `~/.forge-bridge/` data dirs | Already used throughout codebase |
| asyncio | stdlib | Async callback in bridge.py, async dry-run | Server is already async |
| importlib.util | stdlib | Load synthesized .py for dry-run validation | Already used by watcher.py |
| unittest.mock | stdlib | Patch `bridge.execute` during dry-run | No Flame needed for validation |
| forge_bridge.llm.router | Phase 1 built | LLM completion backend | Already exists, tested |
| forge_bridge.mcp.registry | Phase 2 built | register_tool() for synth_ tools | Already exists, tested |
| forge_bridge.learning.watcher | Phase 2 built | File-watching, hot-registration | Already exists, tested |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| textwrap | stdlib | dedent code before normalization | Consistent with bridge.py's existing dedent |
| logging | stdlib | Structured logging for pipeline events | Consistent with existing modules |
| os | stdlib | Environment variable for threshold config | FORGE_PROMOTION_THRESHOLD |

**Installation:** No new packages required. Phase 3 is pure stdlib + existing project modules.

**Version verification:** No new packages to verify. All dependencies confirmed installed and working (test suite green at 100 tests passing).

---

## Architecture Patterns

### Recommended File Layout After Phase 3

```
forge_bridge/
└── learning/
    ├── __init__.py           # Already exists (empty stub)
    ├── watcher.py            # Already exists — DO NOT MODIFY
    ├── execution_log.py      # NEW: LEARN-01 to LEARN-06
    ├── synthesizer.py        # NEW: LEARN-07, LEARN-08, LEARN-09
    └── probation.py          # NEW: LEARN-10

~/.forge-bridge/
    ├── executions.jsonl      # Append-only log (LEARN-02)
    ├── synthesized/          # Output dir — watcher watches this
    │   ├── synth_foo.py
    │   └── synth_bar.py
    └── quarantined/          # Failed probation tools (LEARN-10)
        └── synth_bad.py
```

### Pattern 1: JSONL Execution Log (LEARN-01 to LEARN-03)

**What:** `ExecutionLog` class with append-only writes and startup replay.
**When to use:** Called from bridge.py on_execution callback.

```python
# Source: verified locally (2026-04-14)
import json, hashlib, ast
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

LOG_PATH = Path.home() / ".forge-bridge" / "executions.jsonl"

@dataclass
class ExecutionRecord:
    code_hash: str       # SHA-256 of normalized code
    raw_code: str        # Original code (for synthesis prompt)
    intent: Optional[str]  # LEARN-06: optional user intent label
    timestamp: str       # ISO8601

class ExecutionLog:
    def __init__(self, log_path: Path = LOG_PATH, threshold: int = 3):
        self._path = log_path
        self._threshold = int(os.environ.get("FORGE_PROMOTION_THRESHOLD", threshold))
        self._counters: dict[str, int] = {}        # hash -> count
        self._promoted: set[str] = set()           # hashes already synthesized
        self._code_by_hash: dict[str, str] = {}    # hash -> raw_code (latest seen)
        self._intent_by_hash: dict[str, Optional[str]] = {}
        self._replay()   # rebuild state from disk

    def _replay(self) -> None:
        """Rebuild counters from JSONL without re-triggering synthesis."""
        if not self._path.exists():
            return
        with open(self._path) as fp:
            for line in fp:
                try:
                    rec = json.loads(line.strip())
                    h = rec["code_hash"]
                    self._counters[h] = self._counters.get(h, 0) + 1
                    self._code_by_hash[h] = rec.get("raw_code", "")
                    self._intent_by_hash[h] = rec.get("intent")
                    if rec.get("promoted"):
                        self._promoted.add(h)
                except (json.JSONDecodeError, KeyError):
                    pass  # skip malformed lines

    def record(self, code: str, intent: Optional[str] = None) -> bool:
        """Append execution, return True if threshold just crossed (promote signal)."""
        normalized = _normalize(code)
        h = hashlib.sha256(normalized.encode()).hexdigest()
        self._code_by_hash[h] = code
        self._intent_by_hash[h] = intent
        self._counters[h] = self._counters.get(h, 0) + 1

        rec = {
            "code_hash": h,
            "raw_code": code,
            "intent": intent,
            "timestamp": _now_iso(),
            "promoted": False,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as fp:
            fp.write(json.dumps(rec) + "\n")

        if self._counters[h] >= self._threshold and h not in self._promoted:
            return True   # promote signal
        return False

    def mark_promoted(self, code_hash: str) -> None:
        """Append a promoted=True record so replay skips re-synthesis."""
        self._promoted.add(code_hash)
        rec = {"code_hash": code_hash, "promoted": True, "timestamp": _now_iso()}
        with open(self._path, "a") as fp:
            fp.write(json.dumps(rec) + "\n")
```

### Pattern 2: AST Normalization (LEARN-04)

**What:** Strip string/numeric literals before hashing so `shot = 'ACM_0010'` and `shot = 'ACM_0020'` produce the same fingerprint.

```python
# Source: verified locally (2026-04-14) — ast.unparse confirmed in Python 3.10+
import ast

class _LiteralStripper(ast.NodeTransformer):
    def visit_Constant(self, node: ast.Constant) -> ast.Constant:
        if isinstance(node.value, str):
            return ast.Constant(value="STR")
        if isinstance(node.value, (int, float)):
            return ast.Constant(value=0)
        return node

def _normalize(code: str) -> str:
    """Normalize code to a canonical form for fingerprinting.
    
    Strips string and numeric literals so pattern matching is
    insensitive to shot names, paths, and frame numbers.
    """
    try:
        tree = ast.parse(textwrap.dedent(code).strip())
        stripped = _LiteralStripper().visit(tree)
        return ast.unparse(stripped)
    except SyntaxError:
        return code   # fallback: use raw code if unparseable
```

### Pattern 3: Bridge Callback Hook (LEARN-11)

**What:** Module-level optional callback in `bridge.py`. Off by default. Wired by `execution_log` at startup when opt-in is active.

```python
# Source: verified locally against bridge.py (2026-04-14)
# Add to forge_bridge/bridge.py

from typing import Callable, Optional

_on_execution_callback: Optional[Callable] = None

def set_execution_callback(fn: Optional[Callable]) -> None:
    """Set (or clear) the execution callback. Pass None to disable."""
    global _on_execution_callback
    _on_execution_callback = fn

# In execute() after BridgeResponse is built:
    if _on_execution_callback is not None:
        if asyncio.iscoroutinefunction(_on_execution_callback):
            asyncio.create_task(_on_execution_callback(code, response))
        else:
            _on_execution_callback(code, response)
```

### Pattern 4: Synthesizer (LEARN-07 to LEARN-09)

**What:** Takes `(raw_code, intent, count)` → calls LLM → validates output → writes to `~/.forge-bridge/synthesized/synth_*.py`.

```python
# Source: derived from llm/router.py API (verified Phase 1)
# forge_bridge/learning/synthesizer.py

SYNTH_SYSTEM = """
You are a Flame VFX pipeline tool synthesizer.
Generate async Python MCP tools from observed Flame code patterns.
Respond with ONLY the Python function definition. No explanations.
"""

SYNTH_PROMPT = """
This Flame code pattern was observed {count} times.
User intent: {intent}

Code pattern:
```python
{code}
```

Write a single async Python function that:
- Is named synth_<descriptive_name> (synth_ prefix required)
- Has typed parameters (str, int, float, bool) extracted from the code literals
- Has a return type annotation (-> str or -> dict)
- Has a docstring explaining what it does
- Calls forge_bridge.bridge.execute() or execute_json() internally
- Contains no module-level imports (put imports inside the function body)

Output only the function definition.
"""

async def synthesize(raw_code: str, intent: Optional[str], count: int) -> Path | None:
    """Generate a synthesized tool. Returns path to written file, or None on failure."""
    router = get_router()
    prompt = SYNTH_PROMPT.format(code=raw_code, intent=intent or "not specified", count=count)
    try:
        raw = await router.acomplete(prompt, sensitive=True, system=SYNTH_SYSTEM, temperature=0.1)
    except RuntimeError:
        logger.warning("LLM unavailable — synthesis skipped")
        return None
    
    fn_code = _extract_function(raw)  # strip markdown fences if present
    
    # Validation stage 1: AST parse
    try:
        tree = ast.parse(fn_code)
    except SyntaxError as e:
        logger.warning(f"Synthesized code has syntax error: {e}")
        return None
    
    # Validation stage 2: signature check
    fn_name = _check_signature(tree)  # returns name or raises ValueError
    if fn_name is None:
        return None
    
    # Validation stage 3: dry-run (import + call with mocked bridge)
    if not await _dry_run(fn_code, fn_name):
        return None
    
    # Write to synthesized dir
    out_dir = Path.home() / ".forge-bridge" / "synthesized"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{fn_name}.py"
    out_path.write_text(fn_code)
    logger.info(f"Synthesized tool written: {out_path}")
    return out_path
```

**Signature check requirements (LEARN-09):**
1. Exactly one `AsyncFunctionDef` at module level
2. Name starts with `synth_`
3. Has return annotation (`node.returns is not None`)
4. Has docstring (first body statement is `ast.Expr` containing `ast.Constant`)

**Dry-run (LEARN-09):** Load via `importlib`, patch `forge_bridge.bridge.execute` with async mock, call the function with auto-generated sample args (empty string for `str`, `0` for `int`, `False` for `bool`). Catch all exceptions — any exception = validation failure.

### Pattern 5: Probation System (LEARN-10)

**What:** `ProbationTracker` singleton. Each synthesized tool registration goes through `wrap()`. On failure threshold breach: quarantine file, remove from MCP.

```python
# forge_bridge/learning/probation.py
# Source: derived from requirements (2026-04-14)

QUARANTINE_DIR = Path.home() / ".forge-bridge" / "quarantined"
SYNTH_DIR = Path.home() / ".forge-bridge" / "synthesized"

_DEFAULT_FAILURE_THRESHOLD = int(os.environ.get("FORGE_PROBATION_THRESHOLD", "3"))

class ProbationTracker:
    """In-memory probation counters per synthesized tool name."""

    def __init__(self, failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD):
        self._threshold = failure_threshold
        self._successes: dict[str, int] = {}
        self._failures: dict[str, int] = {}

    def wrap(self, fn: Callable, tool_name: str, mcp: "FastMCP") -> Callable:
        """Return a wrapped callable that tracks success/failure for probation."""
        @functools.wraps(fn)
        async def _wrapped(*args, **kwargs):
            try:
                result = await fn(*args, **kwargs)
                self._successes[tool_name] = self._successes.get(tool_name, 0) + 1
                return result
            except Exception as e:
                self._failures[tool_name] = self._failures.get(tool_name, 0) + 1
                logger.warning(f"Synthesized tool {tool_name} failed: {e}")
                if self._failures[tool_name] >= self._threshold:
                    self._quarantine(tool_name, mcp)
                raise
        return _wrapped

    def _quarantine(self, tool_name: str, mcp: "FastMCP") -> None:
        """Move tool file to quarantine dir and remove from MCP registry."""
        src = SYNTH_DIR / f"{tool_name}.py"
        if src.exists():
            QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
            dest = QUARANTINE_DIR / f"{tool_name}.py"
            src.rename(dest)
            logger.warning(f"Quarantined {tool_name} -> {dest}")
        try:
            mcp.remove_tool(tool_name)
            logger.info(f"Removed quarantined tool from MCP: {tool_name}")
        except Exception:
            pass
```

**Watcher integration:** The watcher must call `probation_tracker.wrap(fn, stem, mcp)` before `register_tool()`. This requires a small modification to `watcher.py`'s `_scan_once()` to accept an optional `ProbationTracker`.

### Anti-Patterns to Avoid

- **Sandboxed Python execution for synthesized tools:** Explicitly out of scope (REQUIREMENTS.md). Breaks Flame API access. Use validation + probation instead.
- **Auto-purge synthesized tools on quarantine:** Out of scope. Move to quarantine dir, never delete. Preserves captured knowledge.
- **Re-synthesis on probation failure:** Out of scope (v2 LEARN-V2-01). Phase 3 only quarantines.
- **Cloud LLM for synthesis:** LEARN-08 explicitly requires `sensitive=True`. Always route to local Ollama.
- **Modification of watcher.py to change its polling path:** Watcher watches `~/.forge-bridge/synthesized/`. Synthesizer must write there. Do not change the watcher's target dir.
- **Modifying `forge_bridge/mcp/server.py` for learning integration:** The lifespan already calls `watch_synthesized_tools()`. No server changes needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM completion backend | Custom HTTP call to Ollama | `get_router().acomplete(sensitive=True)` | Already built in Phase 1, handles routing, error, retries |
| Dynamic tool registration | Direct `mcp._tool_manager._tools` mutation | `register_tool(mcp, fn, name, source="synthesized")` | Registry enforces namespace rules and source tagging |
| Hot-file detection | Custom inotify/kqueue watcher | Existing `watcher.py` (already polls SHA-256) | Fully implemented and tested in Phase 2 |
| Code normalization | Custom string regex | `ast.parse` + `NodeTransformer` + `ast.unparse` | Regex misses whitespace variants, comment differences, etc. |
| Async wrapper for sync callback | `asyncio.run()` inside execute() | `asyncio.create_task()` for async callbacks | `asyncio.run()` raises inside running event loop |

**Key insight:** The heavy infrastructure (LLM router, MCP registry, watcher, async event loop) was all built in Phases 1-2. Phase 3 is a coordination layer on top — the new code is relatively thin.

---

## Common Pitfalls

### Pitfall 1: Re-triggering synthesis on restart (LEARN-03)
**What goes wrong:** Every time the server starts, all hashes in the JSONL that crossed threshold get re-synthesized, generating duplicate synth_ files.
**Why it happens:** Replay rebuilds counters but doesn't track which hashes were already promoted.
**How to avoid:** The JSONL must persist `"promoted": true` records. The `_promoted` set is rebuilt from these records during `_replay()`. `record()` checks `if h in self._promoted` before emitting the promote signal.
**Warning signs:** Duplicate synth_*.py files in `~/.forge-bridge/synthesized/` with timestamps on server restart.

### Pitfall 2: LiteralStripper producing invalid AST (LEARN-04)
**What goes wrong:** `ast.unparse` fails or produces broken code because the transformer returns inconsistent node types.
**Why it happens:** `visit_Constant` must return a valid `ast.Constant` node, not a string. The `ast.copy_location` pattern is needed for correct line info.
**How to avoid:** Always `return ast.Constant(value=...)` (not a raw value). Wrap in try/except SyntaxError as fallback.
**Warning signs:** `TypeError` inside `ast.unparse()` on seemingly valid code.

### Pitfall 3: Synthesized tool name collision (LEARN-09)
**What goes wrong:** LLM generates function named `synth_foo` but `synth_foo.py` already exists in synthesized dir from a previous run.
**Why it happens:** LLM may reuse descriptive names for similar patterns.
**How to avoid:** Synthesizer checks if `~/.forge-bridge/synthesized/{name}.py` exists and either skips (idempotent) or appends a suffix. Best option: if hash of existing file matches new output, skip. Otherwise append `_v2`, `_v3`.
**Warning signs:** Silent overwrite of a working synthesized tool.

### Pitfall 4: Watcher loads quarantined tool back (LEARN-10)
**What goes wrong:** After quarantine removes the file from `~/.forge-bridge/synthesized/`, the watcher correctly removes the tool. But if something re-copies the file back, probation counters are lost (in-memory only) and the tool re-registers fresh.
**Why it happens:** In-memory probation counters don't survive restart.
**How to avoid:** This is an accepted limitation for Phase 3 (v2 LEARN-V2-01 covers persistence). Document it. The quarantine dir acts as the permanent record of failures.
**Warning signs:** Quarantined tool reappears in MCP tool list after server restart.

### Pitfall 5: bridge.py callback creating task without running loop
**What goes wrong:** `asyncio.create_task()` raises `RuntimeError: no running event loop` if called during certain startup sequences.
**Why it happens:** Bridge is also used outside async contexts (sync tools still use it via httpx).
**How to avoid:** Guard with `try/except RuntimeError` and fall back to calling the callback synchronously if no loop is running. The callback signature should be `Callable[[str, BridgeResponse], None]` (sync) for simplicity — async callbacks can be avoided entirely by making `ExecutionLog.record()` synchronous (it only does file I/O, which is fast).
**Warning signs:** `RuntimeError: no current event loop` in bridge logs.

### Pitfall 6: Dry-run patches wrong module reference
**What goes wrong:** The synthesized tool does `import forge_bridge.bridge as bridge` then calls `bridge.execute()`. Patching `forge_bridge.bridge.execute` in the test context works, but `importlib` may load the module into a different namespace.
**Why it happens:** `importlib.util.spec_from_file_location` loads into a fresh module object, not the existing `sys.modules` namespace. The synthesized tool's `import forge_bridge.bridge` will resolve to the real module.
**How to avoid:** Use `unittest.mock.patch("forge_bridge.bridge.execute")` as a context manager wrapping the dry-run call. This patches the real module, which the synthesized tool's import will find.
**Warning signs:** Dry-run actually trying to reach Flame, failing with `BridgeConnectionError`.

---

## Code Examples

Verified patterns for Phase 3 implementation:

### AST Normalization + SHA-256 Fingerprint
```python
# Source: verified locally 2026-04-14 (Python 3.11 in conda 'forge' env)
import ast, hashlib, textwrap

class _LiteralStripper(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            return ast.Constant(value="STR")
        if isinstance(node.value, (int, float)):
            return ast.Constant(value=0)
        return node

def normalize_and_hash(code: str) -> tuple[str, str]:
    """Returns (normalized_code, sha256_hex)."""
    clean = textwrap.dedent(code).strip()
    try:
        tree = ast.parse(clean)
        tree = _LiteralStripper().visit(tree)
        normalized = ast.unparse(tree)
    except SyntaxError:
        normalized = clean
    return normalized, hashlib.sha256(normalized.encode()).hexdigest()

# Verified output:
# normalize_and_hash("seg.name = 'ACM_0010'") == ("seg.name = 'STR'", "abc123...")
# normalize_and_hash("seg.name = 'ACM_0020'") == ("seg.name = 'STR'", "abc123...")
# Same hash for both — pattern matches regardless of shot name
```

### JSONL Append (crash-safe)
```python
# Source: verified locally 2026-04-14
import json
from pathlib import Path

def _append_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fp:
        fp.write(json.dumps(record) + "\n")
        fp.flush()  # ensure OS buffer is flushed; survives kill -9 after flush
```

### importlib Load for Dry-Run
```python
# Source: matches pattern in forge_bridge/learning/watcher.py
import importlib.util
from unittest.mock import AsyncMock, patch

async def _dry_run(fn_code: str, fn_name: str) -> bool:
    """Return True if the function loads and calls without error."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(fn_code)
        tmp_path = f.name
    try:
        spec = importlib.util.spec_from_file_location(fn_name, tmp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, fn_name, None)
        if not callable(fn):
            return False
        # Build sample args from type annotations
        import inspect
        sig = inspect.signature(fn)
        sample_kwargs = {}
        for param_name, param in sig.parameters.items():
            ann = param.annotation
            if ann == str or ann == inspect.Parameter.empty:
                sample_kwargs[param_name] = ""
            elif ann == int:
                sample_kwargs[param_name] = 0
            elif ann == bool:
                sample_kwargs[param_name] = False
            elif ann == float:
                sample_kwargs[param_name] = 0.0
            else:
                sample_kwargs[param_name] = None
        mock_resp = AsyncMock(return_value="")
        with patch("forge_bridge.bridge.execute", mock_resp), \
             patch("forge_bridge.bridge.execute_json", mock_resp), \
             patch("forge_bridge.bridge.execute_and_read", mock_resp):
            import asyncio
            await fn(**sample_kwargs)
        return True
    except Exception as e:
        logger.warning(f"Dry-run failed for {fn_name}: {e}")
        return False
    finally:
        os.unlink(tmp_path)
```

### Probation Wrapper
```python
# Source: derived from requirements (2026-04-14)
import functools

def wrap_for_probation(fn, tool_name, mcp, tracker):
    @functools.wraps(fn)
    async def _wrapped(*args, **kwargs):
        try:
            result = await fn(*args, **kwargs)
            tracker.record_success(tool_name)
            return result
        except Exception:
            should_quarantine = tracker.record_failure(tool_name)
            if should_quarantine:
                tracker.quarantine(tool_name, mcp)
            raise
    return _wrapped
```

### Watcher Modification (how to thread probation through)
```python
# Minimal modification to _scan_once in watcher.py
# Add optional tracker param; falls back to no-op if absent

def _scan_once(mcp, seen, synthesized_dir, tracker=None):
    # ... existing code ...
    fn = _load_fn(path, stem)
    if fn is None:
        continue
    if tracker is not None:
        fn = tracker.wrap(fn, stem, mcp)
    from forge_bridge.mcp.registry import register_tool
    register_tool(mcp, fn, name=stem, source="synthesized")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-coded RPC wrappers | LLM-synthesized tools from observed patterns | Phase 3 design | Self-extending tool set without manual coding |
| Static tool list | Hot-registered synth_* tools via watcher | Phase 2 (watcher) + Phase 3 (synthesizer) | MCP tool list evolves at runtime |
| No execution tracking | Append-only JSONL log | Phase 3 | Audit trail + promotion trigger |
| All LLM calls allowed cloud | sensitive=True forces local Ollama for synthesis | Phase 1 + Phase 3 | Production code never leaves local network |

**Not applicable to this project:**
- `watchfiles` library (rejected Phase 2 — SHA-256 polling chosen instead)
- Sandboxed execution (explicitly out of scope — breaks Flame API)
- PostgreSQL execution log (explicitly out of scope — JSONL is simpler)

---

## Open Questions

1. **Probation human review gate (from STATE.md blocker)**
   - What we know: LEARN-10 says quarantine on failure threshold breach. No explicit "approval" step is required by any LEARN requirement.
   - What's unclear: STATE.md flagged "approval MCP tool vs. log-only gate vs. UI notification" as unresolved.
   - Recommendation: No approval step needed for Phase 3. Quarantine = automatic (move file + remove tool). This satisfies all LEARN requirements as stated. An approval MCP tool would be a v2 addition. The probation gate is purely failure-count-based.

2. **Synthesizer tool naming strategy when LLM reuses names**
   - What we know: LLM may generate `synth_rename_shot` for two different patterns.
   - What's unclear: Should synthesizer deduplicate by hash or by name?
   - Recommendation: Check if `~/.forge-bridge/synthesized/{fn_name}.py` exists. If same content (hash match), skip (idempotent). If different content, log warning and skip — don't overwrite a working tool. The user can quarantine manually to clear the slot.

3. **Watcher modification scope**
   - What we know: `watcher.py` is complete, tested, and working. Probation requires wrapping before registration.
   - What's unclear: How much of watcher.py to touch.
   - Recommendation: Add optional `tracker: Optional[ProbationTracker] = None` to `_scan_once()` and `watch_synthesized_tools()`. Zero behavior change if tracker is None. Server.py passes the tracker singleton when starting the watcher.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x (installed in conda 'forge' env) |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`) |
| Quick run command | `python -m pytest tests/test_learning.py -x -q` |
| Full suite command | `python -m pytest tests/ --ignore=tests/test_e2e.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LEARN-01 | forge_bridge.learning.execution_log importable | unit | `pytest tests/test_learning.py::test_execution_log_importable -x` | ❌ Wave 0 |
| LEARN-02 | record() appends JSONL, file survives between instances | unit | `pytest tests/test_learning.py::test_jsonl_append -x` | ❌ Wave 0 |
| LEARN-03 | ExecutionLog replay rebuilds counters, skips promoted hashes | unit | `pytest tests/test_learning.py::test_replay_skips_promoted -x` | ❌ Wave 0 |
| LEARN-04 | Different shot names hash identically after normalization | unit | `pytest tests/test_learning.py::test_normalize_strips_literals -x` | ❌ Wave 0 |
| LEARN-05 | record() returns True at threshold, False before | unit | `pytest tests/test_learning.py::test_promotion_threshold -x` | ❌ Wave 0 |
| LEARN-06 | intent field preserved in JSONL record | unit | `pytest tests/test_learning.py::test_intent_logged -x` | ❌ Wave 0 |
| LEARN-07 | synthesize() writes synth_*.py to ~/.forge-bridge/synthesized | unit (mocked LLM) | `pytest tests/test_synthesizer.py::test_synthesize_writes_file -x` | ❌ Wave 0 |
| LEARN-08 | LLM router called with sensitive=True | unit | `pytest tests/test_synthesizer.py::test_synthesizer_uses_sensitive -x` | ❌ Wave 0 |
| LEARN-09 | Validation rejects bad syntax, wrong signature, failed dry-run | unit | `pytest tests/test_synthesizer.py::test_validation_rejects_bad_code -x` | ❌ Wave 0 |
| LEARN-10 | ProbationTracker quarantines tool after N failures | unit | `pytest tests/test_probation.py::test_quarantine_on_threshold -x` | ❌ Wave 0 |
| LEARN-11 | bridge.execute() fires callback when set | unit | `pytest tests/test_learning.py::test_bridge_callback -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_learning.py tests/test_synthesizer.py tests/test_probation.py -x -q`
- **Per wave merge:** `python -m pytest tests/ --ignore=tests/test_e2e.py -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_learning.py` — covers LEARN-01 through LEARN-06, LEARN-11
- [ ] `tests/test_synthesizer.py` — covers LEARN-07, LEARN-08, LEARN-09 (with mocked LLM router)
- [ ] `tests/test_probation.py` — covers LEARN-10
- [ ] No new framework installs needed — pytest + pytest-asyncio already present

---

## Sources

### Primary (HIGH confidence)
- Locally verified Python 3.11 stdlib: `ast`, `hashlib`, `json`, `pathlib`, `asyncio`, `importlib.util`, `unittest.mock`
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/learning/watcher.py` — existing implementation inspected
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/mcp/registry.py` — existing implementation inspected
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/llm/router.py` — existing implementation inspected
- `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/bridge.py` — existing implementation inspected
- `/Users/cnoellert/Documents/GitHub/forge-bridge/.planning/REQUIREMENTS.md` — canonical requirements
- Test suite run: 100 tests passing (verified 2026-04-14)

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — accumulated decisions and blockers
- Phase 02 RESEARCH.md — FastMCP add_tool/remove_tool API verification carried forward

### Tertiary (LOW confidence)
- LLM synthesis prompt template structure — derived from requirements + router.py API; actual LLM output quality not verified (depends on local model qwen2.5-coder:32b)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib + already-installed project modules
- Architecture: HIGH — verified against existing code; patterns are consistent with Phase 1/2 choices
- Pitfalls: HIGH — verified locally; dry-run patching and JSONL append-flush confirmed
- LLM synthesis quality: LOW — depends on local model performance; validation + probation are the safety net

**Research date:** 2026-04-14
**Valid until:** Stable — stdlib + internal modules; no external package versions to track
