"""Skill synthesizer — generates MCP tools from observed code patterns.

When the execution log signals promotion (a code pattern crossed the threshold),
the synthesizer calls the local LLM to generate a reusable async MCP tool,
validates it through 3 stages, and writes it to the synthesized directory
where the watcher picks it up.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json as _json  # for the sidecar write; rename to avoid shadowing
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Optional
from unittest.mock import AsyncMock, patch

from forge_bridge.learning.manifest import manifest_register
from forge_bridge.learning.watcher import SYNTHESIZED_DIR  # shared constant — watcher watches this dir
from forge_bridge.llm.router import LLMRouter, get_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYNTH_SYSTEM = """You are a Flame VFX pipeline tool synthesizer.
Generate async Python MCP tools from observed Flame code patterns.
Respond with ONLY the Python function definition. No explanations."""

SYNTH_PROMPT = """This Flame code pattern was observed {count} times.
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
- MUST call forge_bridge.bridge.execute() or execute_json() to run Flame code — this tool runs in the MCP server, NOT inside Flame, so it cannot `import flame` directly
- Contains no module-level imports (put imports inside the function body)
- NEVER import flame — instead, build the Flame code as a string and pass it to execute(code_string)
- Import bridge functions INSIDE the function body: `from forge_bridge.bridge import execute, execute_json, execute_and_read`

Output only the function definition."""


# ---------------------------------------------------------------------------
# Pre-synthesis hook contract (LRN-04)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreSynthesisContext:
    """Additive context returned by SkillSynthesizer's pre_synthesis_hook.

    Additive-only (D-11): fields contribute to the prompt; they CANNOT
    replace SYNTH_SYSTEM or SYNTH_PROMPT. Consumers populate only what
    they need — all four fields default to empty.

    Fields:
        extra_context: Freeform prose appended to the system prompt after
            any constraints block.
        tags: "key:value" strings (K8s label convention). Stashed next to
            the synthesized tool for later EXT-02 MCP-annotation consumption.
        examples: Few-shot pairs, each a dict with "intent" and "code" keys.
            Rendered as "Example intent: ...\\nExample code:\\n```python\\n...\\n```".
        constraints: Hard rules injected into the system prompt as a
            bulleted "Constraints:" block.
    """

    extra_context: str = ""
    tags: list[str] = field(default_factory=list)
    examples: list[dict] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


PreSynthesisHook = Callable[[str, dict], Awaitable[PreSynthesisContext]]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_function(raw: str) -> str:
    """Strip markdown code fences from LLM output if present."""
    # Use regex with DOTALL | MULTILINE for robust fence extraction
    match = re.search(r"```(?:\w*)\n(.*?)```", raw, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return raw.strip()


# AST node names considered dangerous for synthesized tool code.
_DANGEROUS_CALLS: frozenset[str] = frozenset({
    "eval", "exec", "__import__", "compile", "execfile",
})

_DANGEROUS_ATTR_CALLS: dict[str, frozenset[str]] = {
    "os": frozenset({"system", "popen", "exec", "execvp", "execvpe", "remove", "unlink", "rmdir"}),
    "subprocess": frozenset({"run", "call", "check_call", "check_output", "Popen", "getoutput"}),
    "shutil": frozenset({"rmtree", "move", "copy", "copy2"}),
}


def _check_safety(tree: ast.Module) -> bool:
    """Return True if the AST contains no dangerous calls, False otherwise.

    Scans for:
    - Bare dangerous calls: eval(), exec(), __import__(), compile()
    - Dangerous attribute calls: os.system(), subprocess.run(), shutil.rmtree(), etc.
    - open() calls that are not calling bridge functions
    - FB-C LLMTOOL-07 (D-14): imports from forge_bridge.llm — recursive-synthesis
      attack surface. Synthesized tools that import from forge_bridge.llm.router
      can call back into the LLM, leading to runaway recursion and credential
      exhaustion (research §6.3). Static rejection at synthesis time is the
      first of three layers (D-12/D-13 add a runtime ContextVar check).
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

        # FB-C LLMTOOL-07 (D-14): block recursive synthesis by rejecting any
        # synthesized code that imports from forge_bridge.llm. Catches both:
        #   import forge_bridge.llm
        #   import forge_bridge.llm.router
        # AND:
        #   from forge_bridge.llm import router
        #   from forge_bridge.llm.router import LLMRouter
        # The bare-prefix `forge_bridge` (without .llm) stays allowed —
        # synthesized tools legitimately need to import forge_bridge.bridge.
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

    return True


def _check_signature(tree: ast.Module) -> Optional[str]:
    """Validate AST has exactly one AsyncFunctionDef with synth_ prefix, return annotation, and docstring."""
    async_fns = [
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
    ]
    if len(async_fns) != 1:
        return None

    node = async_fns[0]

    # Must start with synth_
    if not node.name.startswith("synth_"):
        return None

    # Must have return annotation
    if node.returns is None:
        return None

    # Must have docstring (first body statement is Expr containing Constant str)
    if not node.body:
        return None
    first = node.body[0]
    if not isinstance(first, ast.Expr):
        return None
    if not isinstance(first.value, ast.Constant):
        return None
    if not isinstance(first.value.value, str):
        return None

    return node.name


async def _dry_run(fn_code: str, fn_name: str) -> bool:
    """Load function in temp file, call with mock bridge, return True if no exception."""
    tmp_path = None
    try:
        # Write to temp file
        fd, tmp_path = tempfile.mkstemp(suffix=".py")
        os.write(fd, fn_code.encode())
        os.close(fd)

        # Load via importlib
        spec = importlib.util.spec_from_file_location(f"_synth_dryrun_{fn_name}", tmp_path)
        if spec is None or spec.loader is None:
            return False
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        fn = getattr(module, fn_name, None)
        if fn is None or not callable(fn):
            return False

        # Build sample kwargs from signature
        sig = inspect.signature(fn)
        sample_kwargs = {}
        type_defaults = {
            str: "",
            int: 0,
            float: 0.0,
            bool: False,
        }
        for param_name, param in sig.parameters.items():
            annotation = param.annotation
            sample_kwargs[param_name] = type_defaults.get(annotation, None)

        # Patch bridge functions and call
        mock = AsyncMock(return_value="")
        with patch("forge_bridge.bridge.execute", mock), \
             patch("forge_bridge.bridge.execute_json", mock), \
             patch("forge_bridge.bridge.execute_and_read", mock):
            await fn(**sample_kwargs)

        return True
    except Exception:
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class SkillSynthesizer:
    """Generates MCP tools from observed code patterns via LLM synthesis.

    Args:
        router: LLMRouter instance. Defaults to the shared get_router() singleton.
        synthesized_dir: Directory to write synthesized tools to.
                         Defaults to forge_bridge.learning.watcher.SYNTHESIZED_DIR
                         (~/.forge-bridge/synthesized).
    """

    def __init__(
        self,
        router: LLMRouter | None = None,
        synthesized_dir: Path | None = None,
        pre_synthesis_hook: PreSynthesisHook | None = None,
    ) -> None:
        # Eager fallback at init: get_router() is itself lazy, so this just
        # returns the shared singleton or constructs it.
        self._router = router if router is not None else get_router()
        # synthesized_dir=None falls back to the module-level SYNTHESIZED_DIR constant
        self._synthesized_dir = synthesized_dir if synthesized_dir is not None else SYNTHESIZED_DIR
        # No fallback for pre_synthesis_hook — None stays None (no-op).
        self._pre_synthesis_hook: PreSynthesisHook | None = pre_synthesis_hook

    async def synthesize(
        self,
        raw_code: str,
        intent: Optional[str],
        count: int,
    ) -> Optional[Path]:
        """Generate a synthesized MCP tool from an observed code pattern.

        Args:
            raw_code: The observed Python code pattern.
            intent: User-provided description of what the code does.
            count: Number of times this pattern was observed.

        Returns:
            Path to the written synth_*.py file, or None if synthesis/validation failed.
        """
        # Invoke pre-synthesis hook (if registered) — LRN-04.
        # Hook receives (intent, params) per D-09 and returns PreSynthesisContext per D-10.
        ctx: PreSynthesisContext = PreSynthesisContext()
        if self._pre_synthesis_hook is not None:
            try:
                ctx = await self._pre_synthesis_hook(
                    intent or "",
                    {"raw_code": raw_code, "count": count},
                )
            except Exception:
                logger.warning(
                    "pre_synthesis_hook raised — falling back to empty context",
                    exc_info=True,
                )
                ctx = PreSynthesisContext()

        # Compose system prompt additively (D-11). Base SYNTH_SYSTEM is never replaced.
        system_prompt = SYNTH_SYSTEM
        if ctx.constraints:
            constraints_block = "\n".join(f"- {c}" for c in ctx.constraints)
            system_prompt = f"{system_prompt}\n\nConstraints:\n{constraints_block}"
        if ctx.extra_context:
            system_prompt = f"{system_prompt}\n\n{ctx.extra_context}"

        # Build user prompt. Base SYNTH_PROMPT is never replaced; few-shot examples
        # (if present) are prepended so the model sees them first.
        base_prompt = SYNTH_PROMPT.format(
            count=count,
            intent=intent or "unknown",
            code=raw_code,
        )
        if ctx.examples:
            few_shot = "\n\n".join(
                f"Example intent: {ex.get('intent', '')}\n"
                f"Example code:\n```python\n{ex.get('code', '')}\n```"
                for ex in ctx.examples
            )
            user_prompt = f"{few_shot}\n\n{base_prompt}"
        else:
            user_prompt = base_prompt

        # Call LLM with composed prompts.
        try:
            raw = await self._router.acomplete(
                user_prompt,
                sensitive=True,
                system=system_prompt,
                temperature=0.1,
            )
        except RuntimeError:
            logger.warning("LLM unavailable — skipping synthesis")
            return None

        # Extract function from LLM response
        fn_code = _extract_function(raw)

        # Stage 1: Parse
        try:
            tree = ast.parse(fn_code)
        except SyntaxError:
            logger.warning("Synthesis failed: syntax error in LLM output")
            return None

        # Stage 2: Signature check
        fn_name = _check_signature(tree)
        if fn_name is None:
            logger.warning("Synthesis failed: signature validation failed")
            return None

        # Stage 2b: Safety check — reject dangerous calls before execution
        if not _check_safety(tree):
            logger.warning("Synthesis failed: code contains dangerous calls")
            return None

        # Stage 3: Dry run
        if not await _dry_run(fn_code, fn_name):
            logger.warning("Synthesis failed: dry-run raised an exception")
            return None

        # Check for name collision
        output_path = self._synthesized_dir / f"{fn_name}.py"
        if output_path.exists():
            existing_hash = hashlib.sha256(output_path.read_text().encode()).hexdigest()
            new_hash = hashlib.sha256(fn_code.encode()).hexdigest()
            if existing_hash == new_hash:
                logger.info(f"Identical synthesized tool already exists: {output_path}")
                return output_path
            else:
                logger.warning(f"Name collision for {fn_name} — existing file has different content")
                return None

        # Write output
        self._synthesized_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(fn_code)
        manifest_register(output_path)

        # Sidecar envelope: {tags, meta, schema_version=1} — PROV-01 v1.2 shape.
        # Always written for successful synthesis — `meta` provenance is non-empty
        # by construction. v1.2 name is .sidecar.json; the legacy name is retired.
        # Per PROV-01 / PITFALL P-02.1: provenance goes here, NOT into Tool.annotations.
        import forge_bridge as _forge_bridge  # local import — avoid circular at module load

        code_hash = hashlib.sha256(fn_code.encode()).hexdigest()
        sidecar_envelope = {
            "tags": list(ctx.tags),  # preserves caller order; [] if no tags
            "meta": {
                "forge-bridge/origin": "synthesizer",
                "forge-bridge/code_hash": code_hash,
                "forge-bridge/synthesized_at": datetime.now(timezone.utc).isoformat(),
                "forge-bridge/version": _forge_bridge.__version__,
                "forge-bridge/observation_count": count,
            },
            "schema_version": 1,
        }
        sidecar_path = output_path.with_suffix(".sidecar.json")
        sidecar_path.write_text(_json.dumps(sidecar_envelope))

        logger.info(f"Synthesized tool written: {output_path}")
        return output_path
