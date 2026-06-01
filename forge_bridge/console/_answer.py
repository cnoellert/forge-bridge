"""Answer synthesis for successful conversational read chains."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

_SYNTHESIS_TIMEOUT_S = 8.0
_SYNTHESIS_SYSTEM = (
    "Answer the user's question using ONLY the tool results provided.\n"
    "If the results do not contain the answer, say so plainly. Do not\n"
    "invent values, infer beyond the data, or overstate certainty,\n"
    "tense, or causality. Be concise and plain-language — an artist,\n"
    "not a developer, is reading."
)


def _last_user_question(messages: list[dict]) -> str:
    for message in reversed(messages):
        if (
            isinstance(message, dict)
            and message.get("role") == "user"
            and isinstance(message.get("content"), str)
        ):
            return message["content"]
    return ""


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _build_synthesis_prompt(messages: list[dict], chain: list[dict]) -> str:
    question = _last_user_question(messages)
    evidence_lines: list[str] = []
    for entry in chain:
        if not isinstance(entry, dict):
            continue
        step = entry.get("step", "")
        result = entry.get("result")
        evidence_lines.append(f"- {step}\n  {_compact_json(result)}")
    evidence = "\n".join(evidence_lines) if evidence_lines else "(no tool results)"
    return (
        "Question:\n"
        f"{question}\n\n"
        "Tool results:\n"
        f"{evidence}\n\n"
        "Answer:"
    )


async def _synthesize_answer(
    router: Any,
    messages: list[dict],
    chain: list[dict],
) -> tuple[str, int]:
    """Return a concise read answer, or ("", ms) if synthesis fails."""
    started = time.monotonic()
    prompt = _build_synthesis_prompt(messages, chain)
    try:
        answer = await asyncio.wait_for(
            router.acomplete(
                prompt,
                sensitive=True,
                system=_SYNTHESIS_SYSTEM,
                temperature=0.1,
            ),
            timeout=_SYNTHESIS_TIMEOUT_S,
        )
    except Exception:  # noqa: BLE001 - answer pass may not fail the read
        return "", int((time.monotonic() - started) * 1000)

    if not isinstance(answer, str):
        return "", int((time.monotonic() - started) * 1000)
    return answer.strip(), int((time.monotonic() - started) * 1000)
