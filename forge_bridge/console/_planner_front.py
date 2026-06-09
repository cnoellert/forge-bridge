"""V1 planner-front: LLM authors the plan, substrate executes, LLM narrates.

The deliberate inversion (see CONVERSATIONAL-RECOVERY → planner-front arc):
the model owns comprehension — read the human, resolve the referent, choose
the tools, narrate the result — and the deterministic substrate executes what
the model authored. NO deterministic narrowing, NO per-step resolver, NO
recovery machinery in this path.

V1 scope (deliberately thin): reads only; live entity grounding (projects);
no pattern memory, no retrieval, no learning. Authors the plan from scratch
each turn. Mutations are NOT eligible here — only read-only tools are exposed
to the planner, so a mutation can never be authored on this path.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import asyncio

from forge_bridge.console._step import serialize_forced_tool_result
from forge_bridge.console._vocab_digest import planner_vocabulary_digest
from forge_bridge.mcp.arguments import normalize_tool_args

logger = logging.getLogger(__name__)

_NARRATE_SYSTEM = (
    "Answer the user's question using ONLY the tool results provided. If the "
    "results do not contain the answer, say so plainly. Do not invent values "
    "or overstate certainty. Be concise and plain-language — an artist, not a "
    "developer, is reading."
)
_NARRATE_TIMEOUT_S = 25.0

_PLANNER_SYSTEM = (
    "You are a planning agent for a post-production pipeline assistant. Given "
    "the CONVERSATION, the available PROJECTS (id, name), and the read-only "
    "TOOLS (name, purpose, args), respond to the LAST user message. Resolve "
    "pronouns and back-references (\"it\", \"that project\", \"those shots\") "
    "from earlier turns. Pass tool arguments FLAT (e.g. {\"project_id\": "
    "\"<id>\"}); resolve any project the user names to its id from PROJECTS.\n"
    "If you can proceed, output the MINIMAL plan:\n"
    '{"plan": [{"tool": "<tool_name>", "args": {<flat args>}}]}\n'
    "Filtering/selecting terms must be grounded before you plan. If a term "
    "maps to one defined status, role, alias, or tool purpose in the grounding, "
    "use that meaning. If it maps to more than one concept or layer, ask which "
    "meaning the user intends and name the options. If it has no defined "
    "meaning in the grounding, ask for clarification; say you do not have a "
    "defined meaning for that term and offer plausible interpretations if "
    "obvious. Never silently drop an unknown filter term and run a broader "
    "query. If there is no filtering/selecting term, proceed without asking.\n"
    "If you CANNOT be sure which entity the user means — no project is named "
    "and the conversation doesn't make it clear, OR the name they gave matches "
    "MORE THAN ONE entry in PROJECTS — do NOT guess. Ask, naming the "
    "candidates:\n"
    '{"clarify": "<a short question that lists the candidate project names>"}\n'
    "Output ONLY one JSON object (either a plan or a clarify), no prose."
)


def _read_only_tools(tools: list) -> list:
    return [t for t in tools
            if getattr(getattr(t, "annotations", None), "readOnlyHint", None) is True]


def _inner_param_schema(tool: Any) -> dict:
    """Resolve a tool's flat parameter schema (handles the params-model wrapper)."""
    schema = getattr(tool, "inputSchema", None) or {}
    props = schema.get("properties") or {}
    params = props.get("params")
    if isinstance(params, dict):
        ref = params.get("$ref")
        if not ref:
            for key in ("anyOf", "oneOf"):
                for v in params.get(key, []) or []:
                    if isinstance(v, dict) and isinstance(v.get("$ref"), str):
                        ref = v["$ref"]
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            return (schema.get("$defs") or {}).get(ref[len("#/$defs/"):], {}) or {}
    return schema  # already flat


def _tool_line(tool: Any) -> str:
    title = getattr(getattr(tool, "annotations", None), "title", None) or ""
    inner = _inner_param_schema(tool)
    req = set(inner.get("required") or [])
    args = []
    for name in (inner.get("properties") or {}):
        args.append(f"{name}{'' if name in req else '?'}")
    arg_str = ", ".join(args) if args else "(none)"
    return f"- {tool.name}({arg_str}) — {title or (tool.description or '').splitlines()[0]}"


async def _ground_projects(mcp: Any, tools: list) -> list[dict]:
    try:
        raw = await mcp.call_tool("forge_list_projects", normalize_tool_args(
            "forge_list_projects", {}, tools))
        parsed = json.loads(serialize_forced_tool_result(raw))
        return [{"id": p.get("id"), "name": p.get("name")}
                for p in (parsed.get("projects") or [])]
    except Exception as exc:  # noqa: BLE001 - grounding is best-effort
        logger.info("planner_front: project grounding failed: %s", exc)
        return []


def _parse_planner_output(raw: str) -> dict:
    """Parse the planner's JSON — either {"plan": [...]} or {"clarify": "..."}."""
    text = (raw or "").strip()
    if "```" in text:
        text = text.split("```")[1] if text.count("```") >= 2 else text
        if text.startswith("json"):
            text = text[4:]
    try:
        obj = json.loads(text)
    except Exception:
        a, b = text.find("{"), text.rfind("}")
        if a == -1 or b == -1:
            return {}
        try:
            obj = json.loads(text[a:b + 1])
        except Exception:
            return {}
    return obj if isinstance(obj, dict) else {}


def _conversation(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role, content = m.get("role"), m.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            lines.append(f"{role}: {content.strip()}")
    return "\n".join(lines)


def _last_user(messages: list[dict]) -> str:
    for m in reversed(messages):
        if (isinstance(m, dict) and m.get("role") == "user"
                and isinstance(m.get("content"), str)):
            return m["content"]
    return ""


def _response(text: str, messages: list[dict], *, plan: list | None = None,
              chain: list | None = None, stop: str = "planner_front",
              grounded: int = 0) -> dict:
    return {
        "final_text": text,
        "stop_reason": stop,
        "plan": plan or [],
        "chain": chain or [],
        "grounded_projects": grounded,
        "messages": list(messages) + [{"role": "assistant", "content": text}],
    }


def _slim_entity(x: Any) -> Any:
    if isinstance(x, dict):
        keep = {k: x[k] for k in ("name", "code", "id", "status", "type") if k in x}
        return keep or x
    return x


def _compact_result(result: Any, max_items: int = 25) -> Any:
    """Trim verbose entity lists so narration gets digestible evidence."""
    if isinstance(result, dict):
        out: dict = {}
        for k, v in result.items():
            if isinstance(v, list):
                slim = [_slim_entity(i) for i in v[:max_items]]
                out[k] = {"count": len(v), "sample": slim} if len(v) > max_items else slim
            else:
                out[k] = v
        return out
    return result


async def _narrate(router: Any, convo: str, chain: list[dict]) -> str:
    lines = [f"- {c['step']}\n  {json.dumps(_compact_result(c['result']), ensure_ascii=False)}"
             for c in chain]
    evidence = "\n".join(lines) if lines else "(no tool results)"
    prompt = (f"Conversation:\n{convo}\n\nTool results:\n{evidence}\n\n"
              "Answer the user's latest request using the tool results:")
    try:
        ans = await asyncio.wait_for(
            router.acomplete(prompt, sensitive=True, system=_NARRATE_SYSTEM,
                             temperature=0.1),
            timeout=_NARRATE_TIMEOUT_S)
        return ans.strip() if isinstance(ans, str) else ""
    except Exception as exc:  # noqa: BLE001 - narration failure must not crash the read
        logger.info("planner_front: narration failed: %s", exc)
        return ""


async def run_planner_front(messages: list[dict], *, router: Any, mcp: Any,
                            tools: list) -> dict:
    """Ground → plan (or clarify) → execute → narrate. Chat-shaped dict.

    Takes the full conversation so the planner can resolve cross-turn
    references ("it"). When certainty is insufficient — no referent, multi-
    match, or an unresolvable back-reference — the planner asks instead of
    guessing (one unified mechanism).
    """
    read_tools = _read_only_tools(tools)
    read_names = {t.name for t in read_tools}
    projects = await _ground_projects(mcp, tools)
    user_message = _last_user(messages)
    convo = _conversation(messages) or f"user: {user_message}"

    grounding = (
        "CONVERSATION:\n" + convo + "\n\n"
        + planner_vocabulary_digest() + "\n\n"
        + "PROJECTS:\n" + json.dumps(projects, ensure_ascii=False) + "\n\n"
        + "TOOLS:\n" + "\n".join(_tool_line(t) for t in read_tools) + "\n\n"
        "Respond to the LAST user message."
    )
    try:
        plan_raw = await router.acomplete(grounding, sensitive=True,
                                          system=_PLANNER_SYSTEM, temperature=0.1)
    except Exception as exc:  # noqa: BLE001 - planning must never 500 the endpoint
        logger.info("planner_front: planning failed: %s", exc)
        return _response("Sorry — I hit a problem working that out. Try rephrasing?",
                         messages, stop="planner_error")

    parsed = _parse_planner_output(plan_raw)
    clarify = parsed.get("clarify")
    if isinstance(clarify, str) and clarify.strip():
        return _response(clarify.strip(), messages, stop="clarification_needed",
                         grounded=len(projects))

    plan = [s for s in (parsed.get("plan") or [])
            if isinstance(s, dict) and s.get("tool")]

    chain: list[dict] = []
    for step in plan:
        name = step.get("tool")
        args = step.get("args") or {}
        if name not in read_names:  # reads-only guard — never execute a non-read tool here
            chain.append({"step": f"{name}(rejected: not a read tool)", "result": None})
            continue
        try:
            params = normalize_tool_args(name, dict(args), tools)
            raw = await mcp.call_tool(name, params)
            result = json.loads(serialize_forced_tool_result(raw))
        except Exception as exc:  # noqa: BLE001 - surface, don't crash
            result = {"error": str(exc)}
        chain.append({"step": f"{name}({json.dumps(args, ensure_ascii=False)})",
                      "result": result})

    answer = await _narrate(router, convo, chain)
    return _response(answer, messages, plan=plan, chain=chain,
                     grounded=len(projects))
