"""A.1 chat compile branch helpers.

This module owns the compile -> classify -> preview-or-execute branch shared
by the JSON and SSE chat transports. It does not own HTTP response shaping.
"""
from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import Any, Optional

from forge_bridge.console._authority import dispatch_authority
from forge_bridge.console._engine import run_chain_steps
from forge_bridge.console._param_extract import extract_explicit_params
from forge_bridge.graph.commit import graph_contains_commit_node, is_commit_step
from forge_bridge.llm.router import CompileError
from forge_bridge.store.assent_record_repo import AssentRecordRepo


@dataclass(frozen=True)
class CompileBranchOutcome:
    """Structured outcome of the compile-branch helper."""

    regime: str
    steps: list[str]
    preview: Optional[dict]
    chain_body: Optional[dict]
    compile_error: Optional[Any]
    graph_intent_id: Optional[str] = None
    assent_record_id: Optional[uuid.UUID] = None


@dataclass(frozen=True)
class ApplyBranchOutcome:
    """Structured outcome of the ratified apply branch."""

    regime: str
    graph_intent_id: str
    chain_body: Optional[dict] = None
    error: Optional[dict] = None
    status_code: int = 200
    assent_record: Optional[dict] = None


def _tool_name(tool: Any) -> str | None:
    if isinstance(tool, dict):
        value = tool.get("name")
    else:
        value = getattr(tool, "name", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _tool_description(tool: Any) -> str:
    if isinstance(tool, dict):
        value = tool.get("description", "")
    else:
        value = getattr(tool, "description", "")
    return str(value or "").strip()


def _strip_commit_for_exact_read_graph(steps: list[str], tools: list) -> list[str] | None:
    tools_by_name: dict[str, list[Any]] = {}
    for tool in tools:
        name = _tool_name(tool)
        if name:
            tools_by_name.setdefault(name, []).append(tool)

    read_steps: list[str] = []
    for step_text in steps:
        if is_commit_step(step_text):
            continue

        first_token = step_text.split(maxsplit=1)[0] if step_text.strip() else ""
        matches = tools_by_name.get(first_token, [])
        if len(matches) != 1 or dispatch_authority(matches[0]):
            return None
        read_steps.append(step_text)

    return read_steps or None


def build_compile_system_prompt(tools: list) -> str:
    """Format the compile system prompt from the registered tool surface."""
    catalogue_lines: list[str] = []
    for tool in tools:
        name = _tool_name(tool)
        if not name:
            continue
        description = _tool_description(tool)
        catalogue_lines.append(
            f"- {name}: {description}" if description else f"- {name}"
        )

    catalogue = "\n".join(catalogue_lines) or "- (empty tool set)"
    return (
        "Compile the operator's request into forge-bridge chain-step text.\n\n"
        "Return only chain-step text. Use the literal `->` chain syntax "
        "between ordered steps. Do not include Markdown, prose, or code "
        "fences.\n\n"
        "Available tools:\n"
        f"{catalogue}\n\n"
        "Authority transition:\n"
        "Use the `commit` keyword only for a previewed host-mutation "
        "authority transition. A graph containing `commit` is previewed for "
        "operator ratification before apply."
    )


def build_preview_from_steps(
    steps: list[str],
    graph_intent_id: Optional[str] = None,
) -> dict:
    """Construct the L4 preview shape from compiled chain steps."""
    preview_steps: list[dict[str, Any]] = []
    for step_text in steps:
        commit_step = is_commit_step(step_text)
        first_token = step_text.split(maxsplit=1)[0] if step_text.strip() else ""
        preview_steps.append({
            "step_text": step_text,
            "tool_name": "__commit__" if commit_step else first_token,
            "args_preview": extract_explicit_params(step_text),
            "would_mutate": commit_step,
        })

    mutating_steps = sum(1 for step in preview_steps if step["would_mutate"])
    preview = {
        "kind": "graph-intent-preview",
        "steps": preview_steps,
        "summary": {
            "total_steps": len(preview_steps),
            "mutating_steps": mutating_steps,
            "requires_ratification": mutating_steps > 0,
        },
    }
    if graph_intent_id is not None:
        preview = {
            "kind": preview["kind"],
            "graph_intent_id": graph_intent_id,
            "steps": preview["steps"],
            "summary": preview["summary"],
        }
    return preview


async def run_compile_branch(
    *,
    router: Any,
    user_prompt: str,
    tools: list,
    mcp: Any,
    request_id: str,
    client_ip: str,
    started: float,
    compile_system: Optional[str] = None,
    session_factory: Optional[Any] = None,
) -> CompileBranchOutcome:
    """Compile, classify, then either preview or execute chain steps."""
    system = (
        compile_system
        if compile_system is not None
        else build_compile_system_prompt(tools)
    )
    try:
        steps = await router.compile_intent(
            user_prompt,
            tools,
            system=system,
        )
    except CompileError as exc:
        return CompileBranchOutcome(
            regime="compile_error",
            steps=[],
            preview=None,
            chain_body=None,
            compile_error=exc,
        )

    if graph_contains_commit_node(steps):
        read_steps = _strip_commit_for_exact_read_graph(steps, tools)
        if read_steps is not None:
            steps = read_steps
        else:
            graph_intent_id: str | None = None
            assent_record_id: uuid.UUID | None = None
            if session_factory is not None:
                async with session_factory() as session:
                    assent_repo = AssentRecordRepo(session)
                    record = await assent_repo.propose(chain_steps=steps)
                    await session.commit()
                graph_intent_id = record.graph_intent_id
                assent_record_id = record.id
            return CompileBranchOutcome(
                regime="compiled_mutating_preview",
                steps=steps,
                preview=build_preview_from_steps(steps, graph_intent_id),
                chain_body=None,
                compile_error=None,
                graph_intent_id=graph_intent_id,
                assent_record_id=assent_record_id,
            )
    chain_body = await run_chain_steps(
        steps=steps,
        tools=tools,
        mcp=mcp,
        request_id=request_id,
        client_ip=client_ip,
        started=started,
    )
    regime = (
        "chain_aborted"
        if isinstance(chain_body, dict) and chain_body.get("status") == "error"
        else "compiled_non_mutating"
    )
    return CompileBranchOutcome(
        regime=regime,
        steps=steps,
        preview=None,
        chain_body=chain_body,
        compile_error=None,
    )


async def run_apply_branch(
    *,
    graph_intent_id: str,
    session_factory: Optional[Any],
    tools: list,
    mcp: Any,
    request_id: str,
    client_ip: str,
    started: float,
    actor: Optional[str] = None,
) -> ApplyBranchOutcome:
    """Replay a stored graph-intent after ratification."""
    if session_factory is None:
        return ApplyBranchOutcome(
            regime="error",
            graph_intent_id=graph_intent_id,
            error={
                "code": "internal_error",
                "message": "Session factory is unavailable.",
                "graph_intent_id": graph_intent_id,
            },
            status_code=500,
        )

    from forge_bridge.store.assent_record_repo import (
        AssentRecordLifecycleError,
        AssentRecordNotFound,
    )

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        try:
            if actor is not None:
                record = await repo.ratify(graph_intent_id, actor=actor)
            else:
                record = await repo.get_by_graph_intent_id(graph_intent_id)
                if record is None:
                    raise AssentRecordNotFound(graph_intent_id)
                if record.status != "ratified":
                    return ApplyBranchOutcome(
                        regime="error",
                        graph_intent_id=graph_intent_id,
                        error={
                            "code": "assent_illegal_state",
                            "message": "AssentRecord is not ratified.",
                            "current_status": record.status,
                            "graph_intent_id": graph_intent_id,
                        },
                        status_code=409,
                    )
        except AssentRecordNotFound:
            return ApplyBranchOutcome(
                regime="error",
                graph_intent_id=graph_intent_id,
                error={
                    "code": "assent_record_not_found",
                    "message": "No AssentRecord found for graph_intent_id.",
                    "graph_intent_id": graph_intent_id,
                },
                status_code=404,
            )
        except AssentRecordLifecycleError as exc:
            return ApplyBranchOutcome(
                regime="error",
                graph_intent_id=graph_intent_id,
                error={
                    "code": "assent_illegal_state",
                    "message": "AssentRecord is not in a ratifiable state.",
                    "current_status": exc.from_status,
                    "graph_intent_id": graph_intent_id,
                },
                status_code=409,
            )

        chain_body = await run_chain_steps(
            steps=record.chain_steps,
            tools=tools,
            mcp=mcp,
            request_id=request_id,
            client_ip=client_ip,
            started=started,
            assent_record=record,
        )
        if isinstance(chain_body, dict) and chain_body.get("status") == "error":
            original = (chain_body.get("error") or {}).get("original_error") or {}
            reason = (
                "drift_invalid"
                if original.get("type") == "PLAN_STATE_DRIFT"
                else "chain_aborted"
            )
            failed = await repo.mark_failed(
                graph_intent_id,
                reason=reason,
                result=chain_body,
            )
            await session.commit()
            return ApplyBranchOutcome(
                regime="chain_aborted",
                graph_intent_id=graph_intent_id,
                chain_body=chain_body,
                status_code=400,
                assent_record=failed.to_dict(),
            )

        applied = await repo.mark_applied(graph_intent_id, result=chain_body)
        await session.commit()
        return ApplyBranchOutcome(
            regime="apply_complete",
            graph_intent_id=graph_intent_id,
            chain_body=chain_body,
            assent_record=applied.to_dict(),
        )
