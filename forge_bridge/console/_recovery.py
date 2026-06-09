"""Deterministic conversational recovery payloads.

Recoverable states are conversation continuations, not terminal errors. This
module is the single normalization point for the fixed-stem prompts and
substrate-held candidate sets that feed the chat transports.
"""

from __future__ import annotations

from typing import Any


def _candidate_name(candidate: Any) -> str:
    if isinstance(candidate, dict):
        value = candidate.get("name") or candidate.get("id") or candidate.get("label")
    else:
        value = candidate
    return str(value or "").strip()


def normalize_referent_candidates(candidates: list[Any]) -> list[dict[str, str]]:
    """Normalize concrete names/ids into a stable candidate list."""
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        if isinstance(candidate, dict):
            cid = str(candidate.get("id") or candidate.get("name") or "").strip()
            name = _candidate_name(candidate)
        else:
            name = str(candidate or "").strip()
            cid = name
        if not cid and not name:
            continue
        entry = {"id": cid or name, "name": name or cid}
        key = (entry["id"], entry["name"])
        if key not in seen:
            seen.add(key)
            normalized.append(entry)
    return normalized


def tool_action_label(tool: Any) -> str:
    """Human-authored action label for a runtime tool object."""
    annotations = getattr(tool, "annotations", None)
    title = getattr(annotations, "title", None)
    if isinstance(title, str) and title.strip():
        return title.strip()

    description = getattr(tool, "description", "")
    if not isinstance(description, str):
        description = ""
    lines = description.strip().splitlines()
    label = lines[0].strip() if lines else ""
    name = getattr(tool, "name", "")
    if isinstance(name, str) and name:
        label = label.replace(name, "").strip(" :-")
    if len(label) < 12 or not any(ch.isalpha() for ch in label):
        return "another available result"
    return label


def clarification_needed(
    *,
    kind: str,
    prompt: str,
    candidates: list[dict[str, Any]],
    resolve_hint: dict[str, Any],
) -> dict[str, Any]:
    """Normalized non-terminal recovery taxon."""
    return {
        "type": "clarification_needed",
        "kind": kind,
        "prompt": prompt,
        "candidates": candidates,
        "resolve_hint": resolve_hint,
    }


def referent_clarification(
    *,
    key: str,
    candidates: list[Any],
) -> dict[str, Any]:
    normalized = normalize_referent_candidates(candidates)
    noun = {
        "project_id": "project",
        "sequence_name": "sequence",
        "reel_name": "reel",
    }.get(key, key.replace("_", " "))
    if normalized:
        prompt = f"Found {len(normalized)} {noun}s. Which one?"
    else:
        prompt = f"Which {noun} should I use?"
    return clarification_needed(
        kind="referent",
        prompt=prompt,
        candidates=normalized,
        resolve_hint={
            "key": key,
            "accepted_reply": "name, unique prefix, or unique substring",
        },
    )


def tool_clarification(tools: list[Any]) -> dict[str, Any]:
    candidates = [
        {"label": tool_action_label(tool)}
        for tool in tools
    ]
    return clarification_needed(
        kind="tool",
        prompt="This could mean more than one action. Which result do you want?",
        candidates=candidates,
        resolve_hint={
            "key": "tool",
            "accepted_reply": "one of the listed outcomes",
        },
    )


def response_body(
    *,
    request_id: str,
    clarification: dict[str, Any],
    messages: list[dict] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "status": "clarification_needed",
        "request_id": request_id,
        "clarification_needed": clarification,
        "stop_reason": "clarification_needed",
    }
    if messages is not None:
        body["messages"] = list(messages) + [
            {
                "role": "assistant",
                "content": clarification["prompt"],
                "clarification_needed": clarification,
            }
        ]
    if extra:
        body.update(extra)
    return body


def recovery_context_from_messages(
    messages: list[dict],
    reply: str,
) -> dict[str, Any] | None:
    """Return the held recovery context for a natural follow-up reply.

    The assistant clarification is the marker. The user turn immediately
    before that assistant message is the intent to replay; the current reply
    is only a candidate selector.
    """
    from forge_bridge.console._name_resolve import resolve_name_from_candidates

    for index in range(len(messages) - 2, -1, -1):
        message = messages[index]
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        clarification = message.get("clarification_needed")
        if not isinstance(clarification, dict):
            continue
        if clarification.get("kind") != "referent":
            continue
        hint = clarification.get("resolve_hint")
        candidates = clarification.get("candidates")
        if not isinstance(hint, dict) or not isinstance(candidates, list):
            continue
        key = hint.get("key")
        if not isinstance(key, str) or not key:
            continue
        resolved = resolve_name_from_candidates(reply, candidates)
        intent_text = ""
        for prior in range(index - 1, -1, -1):
            prior_message = messages[prior]
            if (
                isinstance(prior_message, dict)
                and prior_message.get("role") == "user"
                and isinstance(prior_message.get("content"), str)
            ):
                intent_text = prior_message["content"]
                break
        return {
            "params": ({key: resolved} if resolved is not None else {}),
            "clarification": clarification,
            "intent_text": intent_text,
        }
    return None


def recovery_params_from_messages(messages: list[dict], reply: str) -> dict[str, Any]:
    """Resolve a natural reply against the previous held candidate set."""
    context = recovery_context_from_messages(messages, reply)
    if context is None:
        return {}
    params = context.get("params")
    return dict(params) if isinstance(params, dict) else {}
