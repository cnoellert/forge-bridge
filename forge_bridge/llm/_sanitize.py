"""Tool-result sanitization for the FB-C LLMRouter tool-call loop.

Per LLMTOOL-06 (D-11): every tool result string is sanitized before being fed
back to the LLM in the next turn. Three transformations applied in order:

  1. Strip ASCII control chars EXCEPT \\n and \\t (preserve human-readable
     formatting; control chars are an established prompt-injection escape vector).
  2. REPLACE case-insensitive INJECTION_MARKERS substrings with the literal
     token "[BLOCKED:INJECTION_MARKER]". This is the SEMANTIC DIVERGENCE from
     Phase 7's _sanitize_tag (which REJECTS the entire tag): tool-result
     content is authoritative output the LLM still needs to see, so dropping
     the whole 8 KB result on one bad substring would break the loop.
  3. Truncate to _TOOL_RESULT_MAX_BYTES (default 8192, overridable via the
     `max_bytes` kwarg / `complete_with_tools(..., tool_result_max_bytes=N)`)
     with suffix "\\n[...truncated, full result was {n} bytes]" per D-08.

Pattern set imported from forge_bridge._sanitize_patterns — single source of
truth shared with Phase 7's learning.sanitize per FB-C D-09/D-10.

Runs on EVERY tool result before it leaves the coordinator, regardless of
provider (Anthropic / Ollama / future). See research §6.5 for threat model.
"""
from __future__ import annotations

import logging
import re

from forge_bridge._sanitize_patterns import INJECTION_MARKERS, _CONTROL_CHAR_RE

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Per D-08: every tool result is truncated to this many bytes (UTF-8) before
# feeding back to the LLM. Overridable per call via _sanitize_tool_result(...,
# max_bytes=N) which Wave 3 plan 15-08 exposes as
# complete_with_tools(..., tool_result_max_bytes=N).
_TOOL_RESULT_MAX_BYTES: int = 8192

# The literal replacement token written inline wherever an INJECTION_MARKERS
# substring is detected. Matches research §6.5 wording verbatim.
_BLOCKED_TOKEN: str = "[BLOCKED:INJECTION_MARKER]"

# Pre-compiled case-insensitive alternation for all markers — built once at
# module load, applied per call. Markers are escaped with re.escape because
# several contain regex-meta chars (`<|`, `|>`, `[INST]`, `]`, etc.).
_INJECTION_RE: re.Pattern[str] = re.compile(
    "|".join(re.escape(m) for m in INJECTION_MARKERS),
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------


def _sanitize_tool_result(text: str, max_bytes: int = _TOOL_RESULT_MAX_BYTES) -> str:
    """Sanitize a tool result string before feeding it back to the LLM.

    Three transformations applied IN ORDER (D-11):

      1. Strip ASCII control chars EXCEPT \\n and \\t.
      2. Replace case-insensitive INJECTION_MARKERS substrings inline with
         the literal token "[BLOCKED:INJECTION_MARKER]".
      3. Truncate to max_bytes (UTF-8 byte count, NOT character count) with
         the suffix "\\n[...truncated, full result was {n} bytes]" where {n}
         is the ORIGINAL byte length.

    Args:
        text: Raw tool result content. Must be a str — coordinator stringifies
              non-str results (dicts via json.dumps) before calling.
        max_bytes: Truncation cap in UTF-8 bytes. Default _TOOL_RESULT_MAX_BYTES
                   (8192). Caller (complete_with_tools) overrides via the
                   `tool_result_max_bytes` kwarg.

    Returns:
        Sanitized string safe to feed back to the LLM as a tool_result content.
        Never None — this helper REPLACES bad content rather than rejecting,
        diverging from Phase 7's _sanitize_tag for reasons in the module docstring.
    """
    # Step 1: strip control chars (preserve \n and \t).
    # _CONTROL_CHAR_RE matches [\x00-\x1f\x7f] which INCLUDES \n (\x0a) and \t (\x09).
    # Strategy: substitute every match with "" EXCEPT when the match is \n or \t,
    # in which case the matched char is kept verbatim. Single-pass via lambda.
    cleaned = _CONTROL_CHAR_RE.sub(
        lambda m: m.group(0) if m.group(0) in ("\n", "\t") else "",
        text,
    )

    # Step 2: replace any INJECTION_MARKERS substring (case-insensitive) inline.
    # Log a WARNING (truncated for safety) the first time a marker is hit so
    # operators can audit suspicious tool outputs. We do NOT log per-match to
    # avoid log flooding on a result containing many markers.
    if _INJECTION_RE.search(cleaned):
        logger.warning(
            "tool result contained injection marker — replaced inline with %s",
            _BLOCKED_TOKEN,
        )
    cleaned = _INJECTION_RE.sub(_BLOCKED_TOKEN, cleaned)

    # Step 3: byte-count truncate with the D-08 suffix.
    encoded = cleaned.encode("utf-8")
    if len(encoded) > max_bytes:
        original_len = len(encoded)
        # Decode with errors="ignore" to handle a multibyte char being split at
        # the byte boundary — drops the partial codepoint cleanly.
        truncated_text = encoded[:max_bytes].decode("utf-8", errors="ignore")
        suffix = f"\n[...truncated, full result was {original_len} bytes]"
        return truncated_text + suffix

    return cleaned
