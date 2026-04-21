"""Sanitization and size-budget enforcement for consumer-supplied tag payloads.

Per PROV-03 / PITFALL P-02.5: consumer tags written by Phase 6-02's
pre_synthesis_hook reach LLMs that call `tools/list` on this MCP server.
Every tag is a prompt-injection surface. This module applies:

- Control-char and NUL stripping (reject tags containing them)
- Injection-marker rejection (reject tags containing any INJECTION_MARKERS)
- 64-char truncation AFTER allowlist match / redaction hash
- Allowlist: only `project:`, `phase:`, `shot:`, `type:` prefixes pass through.
  Everything else becomes `redacted:<sha256[:8]>` — the hash is stable so
  consumers can correlate back via their own records.
- Size budget: <= 16 tags per tool, <= 4 KB `meta` per tool.

Callers:
- `learning.watcher._read_sidecar` — runs `_sanitize_tag` on every consumer
  tag AND applies `apply_size_budget` at READ time (full PROV-03 boundary).
- `mcp.registry.register_tool` — applies `apply_size_budget` only at the
  WRITE boundary (WR-01 defense-in-depth). Per-tag `_sanitize_tag` is NOT
  re-applied here because tags arriving via the watcher are already
  sanitized and include the literal `"synthesized"` filter tag (TS-02.1)
  which would otherwise be redacted on a second pass. Non-watcher callers
  (plugins, tests) are therefore expected to pre-sanitize tag content if
  they care about the allowlist; the registry enforces only size/shape.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Size ceilings per PROV-03 / SUMMARY
MAX_TAG_CHARS: int = 64
MAX_TAGS_PER_TOOL: int = 16
MAX_META_BYTES: int = 4096

# Allowlist of tag prefixes that pass through unredacted
SANITIZE_ALLOWLIST: tuple[str, ...] = (
    "project:",
    "phase:",
    "shot:",
    "type:",
)

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

# Canonical meta keys (from Plan 07-01) that must NEVER be evicted by budget pressure
_PROTECTED_META_KEYS: frozenset[str] = frozenset({
    "forge-bridge/origin",
    "forge-bridge/code_hash",
    "forge-bridge/synthesized_at",
    "forge-bridge/version",
    "forge-bridge/observation_count",
})


def _truncate_for_log(tag: object, limit: int = 32) -> str:
    """Safe repr for log lines — truncates + repr-escapes control chars."""
    s = repr(tag)
    return s if len(s) <= limit else s[: limit - 3] + "..."


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
        (always fits under MAX_TAG_CHARS because redacted: + 8 hex = 17 chars)
    """
    if not isinstance(tag, str):
        logger.warning("tag rejected (not a string): %s", _truncate_for_log(tag))
        return None
    if tag == "":
        logger.warning("tag rejected (empty string)")
        return None
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
    # Allowlist pass-through
    for prefix in SANITIZE_ALLOWLIST:
        if tag.startswith(prefix):
            return tag[:MAX_TAG_CHARS]
    # Not in allowlist -> redact
    digest = hashlib.sha256(tag.encode("utf-8")).hexdigest()[:8]
    return f"redacted:{digest}"


def apply_size_budget(payload: dict) -> dict:
    """Enforce MAX_TAGS_PER_TOOL and MAX_META_BYTES on a sidecar payload.

    Operates on the `{"tags": [...], "meta": {...}}` shape (the `schema_version`
    key is stripped by callers before this point). Returns a NEW dict — does not
    mutate the input. Always preserves canonical `forge-bridge/*` meta keys.
    """
    tags = list(payload.get("tags") or [])
    meta = dict(payload.get("meta") or {})

    # Tag count ceiling
    if len(tags) > MAX_TAGS_PER_TOOL:
        dropped = len(tags) - MAX_TAGS_PER_TOOL
        logger.warning(
            "dropped %d tags over MAX_TAGS_PER_TOOL=%d",
            dropped,
            MAX_TAGS_PER_TOOL,
        )
        tags = tags[:MAX_TAGS_PER_TOOL]

    # Meta byte ceiling — evict non-canonical keys first, never canonical ones
    meta_bytes = len(json.dumps(meta, sort_keys=True).encode("utf-8"))
    if meta_bytes > MAX_META_BYTES:
        non_canonical = [k for k in meta if k not in _PROTECTED_META_KEYS]
        while non_canonical and meta_bytes > MAX_META_BYTES:
            victim = non_canonical.pop()
            logger.warning(
                "evicting non-canonical meta key %r to fit MAX_META_BYTES=%d",
                victim,
                MAX_META_BYTES,
            )
            meta.pop(victim, None)
            meta_bytes = len(json.dumps(meta, sort_keys=True).encode("utf-8"))
        if meta_bytes > MAX_META_BYTES:
            logger.warning(
                "meta still exceeds MAX_META_BYTES=%d after evicting non-canonical "
                "keys (canonical keys are protected); payload size=%d bytes",
                MAX_META_BYTES,
                meta_bytes,
            )

    return {"tags": tags, "meta": meta}
