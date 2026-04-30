"""forge_bridge._sanitize_patterns — single source of truth for sanitization patterns.

Both forge_bridge/learning/sanitize.py (Phase 7 PROV-03 — tag sanitization) and
forge_bridge/llm/_sanitize.py (FB-C LLMTOOL-06 — tool-result sanitization)
import the patterns from this module per FB-C D-09 (hoist patterns, NOT helpers).

The HELPERS are NOT centralized — each consumer owns its own rejection semantics:

  - learning.sanitize._sanitize_tag(): REJECTS the entire tag on marker hit.
  - llm._sanitize._sanitize_tool_result(): REPLACES inline with [BLOCKED:INJECTION_MARKER].

Different consumers, different semantics, same pattern set.
"""
from __future__ import annotations

import re

# Injection markers — presence triggers consumer-specific rejection/replacement.
INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous",
    "<|",
    "|>",
    "[INST]",
    "[/INST]",
    "<|im_start|>",
    "```",  # triple backtick — markdown code fence
    "---",  # yaml document separator
    "<|im_end|>",     # qwen chat template — terminal token (POLISH-04)
    "<|endoftext|>",  # qwen chat template — sequence terminator (POLISH-04)
)

# Control characters: \x00-\x1f plus \x7f (DEL)
_CONTROL_CHAR_RE: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]")
