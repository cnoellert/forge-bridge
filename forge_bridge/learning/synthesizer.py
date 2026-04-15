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
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, patch

from forge_bridge.learning.watcher import SYNTHESIZED_DIR  # shared constant — watcher watches this dir

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
- Calls forge_bridge.bridge.execute() or execute_json() internally
- Contains no module-level imports (put imports inside the function body)

Output only the function definition."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_function(raw: str) -> str:
    """Strip markdown code fences from LLM output if present."""
    if "```" in raw:
        # Find content between first ``` and last ```
        parts = raw.split("```")
        if len(parts) >= 3:
            code_block = parts[1]
            # Remove optional language tag on first line
            lines = code_block.split("\n", 1)
            if len(lines) > 1 and lines[0].strip().isalpha():
                code_block = lines[1]
            return code_block.strip()
    return raw.strip()


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


async def synthesize(
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
    # Lazy import to avoid circular deps at module load time
    from forge_bridge.llm.router import get_router

    # Build prompt
    prompt = SYNTH_PROMPT.format(
        count=count,
        intent=intent or "unknown",
        code=raw_code,
    )

    # Call LLM
    try:
        raw = await get_router().acomplete(
            prompt,
            sensitive=True,
            system=SYNTH_SYSTEM,
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

    # Stage 3: Dry run
    if not await _dry_run(fn_code, fn_name):
        logger.warning("Synthesis failed: dry-run raised an exception")
        return None

    # Check for name collision
    output_path = SYNTHESIZED_DIR / f"{fn_name}.py"
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
    SYNTHESIZED_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(fn_code)
    logger.info(f"Synthesized tool written: {output_path}")
    return output_path
