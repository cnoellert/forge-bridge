"""Cloud-backed terminal formatter for deterministic chain results."""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

FormatClass = Literal["email", "table", "bullets"]

MAX_CLOUD_TOKENS_EQUIVALENT = 2000
_CHARS_PER_TOKEN_EQUIVALENT = 4
_MAX_CLOUD_CHARS = MAX_CLOUD_TOKENS_EQUIVALENT * _CHARS_PER_TOKEN_EQUIVALENT
_EGRESS_WARNING = (
    "format_result sends condensed data to Anthropic cloud model. "
    "Ensure ANTHROPIC_API_KEY is set and data-egress policy permits."
)
_HASH_RE = re.compile(r"(^|_)(hash|sha|sha256|md5|checksum|digest)($|_)", re.I)
_PATH_RE = re.compile(r"(^|_)(path|file_path|source_path|media_path)($|_)", re.I)
_FRAME_RE = re.compile(r"(^|_)(frame|frames|record_in|record_out|source_in|source_out|head|tail)($|_)", re.I)
_INTERNAL_RE = re.compile(r"^_|(^|_)(trace|debug|raw|payload|stdout|stderr|traceback)($|_)", re.I)
_warned_egress = False


class FormatResultInput(BaseModel):
    data: Any = Field(..., description="Structured JSON payload from the preceding chain step")
    format: FormatClass = Field(..., description="Output format class")


@dataclass(frozen=True)
class CondensedPayload:
    data: Any
    stripped: dict[str, int]
    truncated: bool
    chars: int


async def format_result(params: FormatResultInput) -> str:
    """Format a prior chain result as human-readable operator text.

    This tool intentionally uses the cloud router path. It is a terminal chain
    formatter, not a data-fetching tool.
    """
    _require_cloud_key()
    warning = _operator_warning_once()
    condensed = condense_payload(params.data, params.format)
    prompt = build_format_prompt(
        format_class=params.format,
        condensed_payload=condensed.data,
        stripped=condensed.stripped,
        truncated=condensed.truncated,
    )

    from forge_bridge.llm.router import get_router

    rendered = await get_router().acomplete(
        prompt,
        sensitive=False,
        temperature=0.1,
    )
    rendered = rendered.strip()
    return f"{warning}\n\n{rendered}" if warning else rendered


def condense_payload(data: Any, format_class: FormatClass) -> CondensedPayload:
    """Strip substrate noise and cap the payload before cloud egress."""
    stripped: dict[str, int] = {
        "hashes": 0,
        "internal": 0,
        "paths": 0,
        "frame_numbers": 0,
        "empty": 0,
    }
    condensed = _strip_value(data, format_class=format_class, stripped=stripped)
    text = json.dumps(condensed, ensure_ascii=False, sort_keys=True, default=str)
    truncated = len(text) > _MAX_CLOUD_CHARS
    if truncated:
        prefix = text[:_MAX_CLOUD_CHARS]
        condensed = {
            "truncated": True,
            "token_cap_equivalent": MAX_CLOUD_TOKENS_EQUIVALENT,
            "payload_prefix": prefix,
        }
        capped = json.dumps(condensed, ensure_ascii=False, sort_keys=True, default=str)
        while len(capped) > _MAX_CLOUD_CHARS and condensed["payload_prefix"]:
            overage = len(capped) - _MAX_CLOUD_CHARS
            condensed["payload_prefix"] = condensed["payload_prefix"][:-overage]
            capped = json.dumps(condensed, ensure_ascii=False, sort_keys=True, default=str)
        text = capped
        logger.warning(
            "format_result condensation truncated payload chars=%d cap=%d",
            len(text),
            _MAX_CLOUD_CHARS,
        )
    logger.info("format_result condensation stripped=%s", stripped)
    return CondensedPayload(
        data=condensed,
        stripped=stripped,
        truncated=truncated,
        chars=min(len(text), _MAX_CLOUD_CHARS),
    )


def build_format_prompt(
    *,
    format_class: FormatClass,
    condensed_payload: Any,
    stripped: dict[str, int],
    truncated: bool,
) -> str:
    instructions = {
        "email": (
            "Write a professional summary suitable for forwarding to a producer. "
            "Use a concise subject line and short paragraphs."
        ),
        "table": (
            "Render a column-aligned plain-text table suitable for verification. "
            "Use stable columns and keep values scannable."
        ),
        "bullets": (
            "Render a flat bullet list in readable prose. Do not nest bullets."
        ),
    }
    payload = json.dumps(condensed_payload, ensure_ascii=False, indent=2, default=str)
    return (
        "You are formatting VFX production data from Flame for a post-production operator.\n"
        f"Format class: {format_class}\n"
        f"Instruction: {instructions[format_class]}\n"
        "Use only the condensed payload below. Do not invent missing details.\n"
        f"Condensation audit: stripped={stripped}, truncated={truncated}.\n\n"
        "[Condensed payload]\n"
        f"{payload}"
    )


def _strip_value(value: Any, *, format_class: FormatClass, stripped: dict[str, int]) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for raw_key, raw_item in value.items():
            key = str(raw_key)
            bucket = _strip_bucket_for_key(key, format_class)
            if bucket:
                stripped[bucket] += 1
                continue
            item = _strip_value(raw_item, format_class=format_class, stripped=stripped)
            if item in (None, "", [], {}):
                stripped["empty"] += 1
                continue
            out[key] = item
        return out
    if isinstance(value, list):
        items = [
            _strip_value(item, format_class=format_class, stripped=stripped)
            for item in value
        ]
        return [item for item in items if item not in (None, "", [], {})]
    return value


def _strip_bucket_for_key(key: str, format_class: FormatClass) -> str | None:
    if _HASH_RE.search(key):
        return "hashes"
    if _INTERNAL_RE.search(key):
        return "internal"
    if _PATH_RE.search(key) and format_class != "email":
        return "paths"
    if _FRAME_RE.search(key):
        return "frame_numbers"
    return None


def _require_cloud_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "format_result requires ANTHROPIC_API_KEY because it sends "
            "condensed data to the Anthropic cloud model."
        )


def _operator_warning_once() -> str:
    global _warned_egress
    if _warned_egress:
        return ""
    _warned_egress = True
    logger.warning(_EGRESS_WARNING)
    return _EGRESS_WARNING


def _reset_for_tests() -> None:
    global _warned_egress
    _warned_egress = False
