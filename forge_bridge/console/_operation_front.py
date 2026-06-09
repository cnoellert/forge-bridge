"""Operation-front seam for mutating, ratified Flame operations."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from forge_bridge.console._chat_compile import build_preview_from_steps
from forge_bridge.console._operation_digest import operation_v1_digest
from forge_bridge.store.assent_record_repo import AssentRecordRepo

logger = logging.getLogger(__name__)

_DEFAULT_TARGET_SENTINEL = "__default_workspace_library__"

_OPERATION_SYSTEM = (
    "You are an operation planner for a post-production pipeline assistant. "
    "Given CONVERSATION and OPERATIONS, respond to the LAST user message. "
    "This slice supports exactly one mutating operation: create_reel. "
    "If the user asks to create/name a Flame reel and gives a reel name, "
    "return only JSON in this shape:\n"
    '{"operation": "create_reel", "args": {"reel_name": "<name>", '
    '"target_type": "library|reel_group", "target_name": "<optional name>"}}\n'
    "If target container is omitted, use target_type=library and omit "
    "target_name. If the reel name is missing or intent is not create_reel, "
    'return {"clarify": "<short question>"}. Do not invent other operations. '
    "Never execute; only author operation intent for preview and ratification."
)


def _conversation(messages: list[dict]) -> str:
    lines = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            lines.append(f"{role}: {content.strip()}")
    return "\n".join(lines)


def _last_user(messages: list[dict]) -> str:
    for message in reversed(messages):
        if (
            isinstance(message, dict)
            and message.get("role") == "user"
            and isinstance(message.get("content"), str)
        ):
            return message["content"]
    return ""


def _parse_operation_output(raw: str) -> dict:
    text = (raw or "").strip()
    if "```" in text:
        text = text.split("```")[1] if text.count("```") >= 2 else text
        if text.startswith("json"):
            text = text[4:]
    try:
        obj = json.loads(text)
    except Exception:
        left, right = text.find("{"), text.rfind("}")
        if left == -1 or right == -1:
            return {}
        try:
            obj = json.loads(text[left:right + 1])
        except Exception:
            return {}
    return obj if isinstance(obj, dict) else {}


def _operation_step(args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    reel_name = str(args["reel_name"]).strip()
    target_type = str(args.get("target_type") or "library").strip() or "library"
    if target_type not in {"library", "reel_group"}:
        target_type = "library"
    raw_target = args.get("target_name")
    target_name = str(raw_target).strip() if raw_target is not None else ""
    tool_args = {
        "reel_name": reel_name,
        "target_type": target_type,
        "target_name": target_name or _DEFAULT_TARGET_SENTINEL,
    }
    preview_args = dict(tool_args)
    if not target_name:
        preview_args["target_name"] = "default workspace library"
    step = "flame_create_reel " + json.dumps({"params": tool_args}, sort_keys=True)
    return step, preview_args


def _response(
    text: str,
    messages: list[dict],
    *,
    stop: str,
    preview: Optional[dict] = None,
    graph_intent_id: Optional[str] = None,
) -> dict:
    body = {
        "final_text": text,
        "stop_reason": stop,
        "messages": list(messages) + [{"role": "assistant", "content": text}],
    }
    if preview is not None:
        body["preview"] = preview
    if graph_intent_id is not None:
        body["graph_intent_id"] = graph_intent_id
    return body


async def run_operation_front(
    messages: list[dict],
    *,
    router: Any,
    session_factory: Optional[Any],
) -> dict:
    """Plan one ratified operation and persist it as graph intent."""
    user_message = _last_user(messages)
    convo = _conversation(messages) or f"user: {user_message}"
    grounding = (
        "CONVERSATION:\n" + convo + "\n\n"
        + operation_v1_digest() + "\n\n"
        + "Respond to the LAST user message."
    )
    try:
        raw = await router.acomplete(
            grounding,
            sensitive=True,
            system=_OPERATION_SYSTEM,
            temperature=0.1,
        )
    except Exception as exc:  # noqa: BLE001 - planner failure must not 500
        logger.info("operation_front: planning failed: %s", exc)
        return _response(
            "Sorry — I hit a problem planning that operation. Try rephrasing?",
            messages,
            stop="operation_error",
        )

    parsed = _parse_operation_output(raw)
    clarify = parsed.get("clarify")
    if isinstance(clarify, str) and clarify.strip():
        return _response(clarify.strip(), messages, stop="clarification_needed")

    if parsed.get("operation") != "create_reel" or not isinstance(parsed.get("args"), dict):
        return _response(
            "I can only plan creating a Flame reel in this operation pass.",
            messages,
            stop="clarification_needed",
        )

    args = parsed["args"]
    reel_name = args.get("reel_name")
    if not isinstance(reel_name, str) or not reel_name.strip():
        return _response(
            "What should the new reel be called?",
            messages,
            stop="clarification_needed",
        )

    step, preview_args = _operation_step(args)
    steps = [step, "commit"]
    graph_intent_id: str | None = None
    assent_record_id = None
    if session_factory is not None:
        async with session_factory() as session:
            repo = AssentRecordRepo(session)
            record = await repo.propose(chain_steps=steps)
            await session.commit()
        graph_intent_id = record.graph_intent_id
        assent_record_id = str(record.id)

    preview = build_preview_from_steps(steps, graph_intent_id)
    if preview.get("steps"):
        preview["steps"][0]["args_preview"] = preview_args
    preview["summary"] = {
        **preview["summary"],
        "operation": "create_reel",
        "description": (
            f"create reel {reel_name.strip()!r} in "
            f"{preview_args['target_type']} {preview_args['target_name']!r}"
        ),
    }
    if assent_record_id is not None:
        preview["assent_record_id"] = assent_record_id

    return _response(
        "Preview ready — read it before ratifying.",
        messages,
        stop="preview_emitted",
        preview=preview,
        graph_intent_id=graph_intent_id,
    )
