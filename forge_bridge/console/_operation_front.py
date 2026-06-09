"""Operation-front seam for mutating, ratified Flame operations."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from forge_bridge.console._chat_compile import build_preview_from_steps
from forge_bridge.console._operation_digest import operation_v1_digest
from forge_bridge.store.assent_record_repo import AssentRecordRepo

logger = logging.getLogger(__name__)

_DEFAULT_TARGET_SENTINEL = "__default_workspace_library__"

_OPERATION_SYSTEM = (
    "You are an operation planner for a post-production pipeline assistant. "
    "Given CONVERSATION and OPERATIONS, respond to the LAST user message. "
    "This slice supports exactly three additive mutating operations: "
    "create_reel, create_reel_group, and create_library. If the user asks to "
    "create/name one of those Flame objects and gives the required name, "
    "return only JSON in one of these shapes:\n"
    '{"operation": "create_reel", "args": {"reel_name": "dailies", '
    '"target_type": "library", "target_name": "finishing"}}\n'
    '{"operation": "create_reel_group", "args": {"reel_group_name": "client"}}\n'
    '{"operation": "create_library", "args": {"library_name": "plates"}}\n'
    "If a reel target container is omitted, use target_type=library and omit "
    "target_name. If a required name is missing or intent is outside these "
    "operations, return {\"clarify\": \"<short question>\"}. Never output a literal "
    "placeholder or angle-bracketed token as a value; if a required value is "
    "not supplied, clarify. Do not invent other operations. "
    "Never execute; only author operation intent for preview and ratification."
)

_PLACEHOLDER_RE = re.compile(r"^<.*>$")


@dataclass(frozen=True)
class _OperationSpec:
    operation: str
    tool_name: str
    required: tuple[str, ...]
    clarify_question: str
    description_template: str
    defaults: dict[str, Any] = field(default_factory=dict)
    preview_defaults: dict[str, Any] = field(default_factory=dict)


_OPERATION_SPECS: dict[str, _OperationSpec] = {
    "create_reel": _OperationSpec(
        operation="create_reel",
        tool_name="flame_create_reel",
        required=("reel_name",),
        clarify_question="What should the new reel be called?",
        description_template="create reel {reel_name!r} in {target_type} {target_name!r}",
        defaults={
            "target_type": "library",
            "target_name": _DEFAULT_TARGET_SENTINEL,
        },
        preview_defaults={
            "target_name": "default workspace library",
        },
    ),
    "create_reel_group": _OperationSpec(
        operation="create_reel_group",
        tool_name="flame_create_reel_group",
        required=("reel_group_name",),
        clarify_question="What should the new reel group be called?",
        description_template="create reel group {reel_group_name!r} on desktop {target_name!r}",
        defaults={
            "target_type": "desktop",
            "target_name": "current desktop",
        },
    ),
    "create_library": _OperationSpec(
        operation="create_library",
        tool_name="flame_create_library",
        required=("library_name",),
        clarify_question="What should the new library be called?",
        description_template="create library {library_name!r} in workspace {target_name!r}",
        defaults={
            "target_type": "workspace",
            "target_name": "current workspace",
        },
    ),
}


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


def _format_operation_description(
    spec: _OperationSpec,
    preview_args: dict[str, Any],
) -> str:
    return spec.description_template.format(**preview_args)


def _operation_step(
    spec: _OperationSpec,
    args: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    tool_args = dict(spec.defaults)
    for key in spec.required:
        tool_args[key] = str(args[key]).strip()
    if spec.operation == "create_reel":
        target_type = str(args.get("target_type") or "library").strip() or "library"
        if target_type not in {"library", "reel_group"}:
            target_type = "library"
        raw_target = args.get("target_name")
        target_name = str(raw_target).strip() if raw_target is not None else ""
        tool_args["target_type"] = target_type
        tool_args["target_name"] = target_name or _DEFAULT_TARGET_SENTINEL

    preview_args = dict(tool_args)
    if (
        spec.operation == "create_reel"
        and preview_args.get("target_name") == _DEFAULT_TARGET_SENTINEL
    ):
        preview_args["target_name"] = spec.preview_defaults["target_name"]
    step = spec.tool_name + " " + json.dumps({"params": tool_args}, sort_keys=True)
    return step, preview_args


def _invalid_required_value(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    text = value.strip()
    return not text or text == "<name>" or bool(_PLACEHOLDER_RE.fullmatch(text))


def validate_required_operation_args(
    args: dict[str, Any],
    required: tuple[str, ...],
) -> str | None:
    """Return the first missing/placeholder required arg, else ``None``."""
    for key in required:
        if _invalid_required_value(args.get(key)):
            return key
    return None


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

    operation = parsed.get("operation")
    spec = _OPERATION_SPECS.get(operation) if isinstance(operation, str) else None
    if spec is None or not isinstance(parsed.get("args"), dict):
        return _response(
            "I can only plan creating a Flame reel, reel group, or library in this operation pass.",
            messages,
            stop="clarification_needed",
        )

    args = parsed["args"]
    if validate_required_operation_args(args, spec.required) is not None:
        return _response(
            spec.clarify_question,
            messages,
            stop="clarification_needed",
        )

    step, preview_args = _operation_step(spec, args)
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
        "operation": spec.operation,
        "description": _format_operation_description(spec, preview_args),
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
