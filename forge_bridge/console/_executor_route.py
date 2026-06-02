"""Executor routing for compiled mutation graphs."""
from __future__ import annotations

from typing import Any

from forge_bridge.console._authority import dispatch_authority


_EXECUTOR_MAP = {
    "flame_rename_shots": "forge_apply_rename",
}
# Publish is intentionally excluded from C2: no arg parity, separate motion.


def _tool_name(tool: Any) -> str | None:
    if isinstance(tool, dict):
        value = tool.get("name")
    else:
        value = getattr(tool, "name", None)
    return value if isinstance(value, str) and value else None


def _first_token(step: str) -> str:
    return step.split(maxsplit=1)[0] if step.strip() else ""


def _mutating_step_count(steps: list[str], tools_by_name: dict[str, Any]) -> int:
    count = 0
    for step in steps:
        tool = tools_by_name.get(_first_token(step))
        if tool is not None and dispatch_authority(tool):
            count += 1
    return count


def apply_executor_routing(steps: list[str], tools: list) -> list[str]:
    """Route compile-emitted bare mutation tools to registered executors."""
    tools_by_name = {
        name: tool
        for tool in tools
        if (name := _tool_name(tool))
    }
    if _mutating_step_count(steps, tools_by_name) > 1:
        return steps

    routed: list[str] = []
    changed = False
    for step in steps:
        parts = step.split(maxsplit=1)
        first_token = parts[0] if parts else ""
        tool = tools_by_name.get(first_token)
        executor_name = _EXECUTOR_MAP.get(first_token)
        executor_tool = tools_by_name.get(executor_name or "")

        if (
            tool is not None
            and dispatch_authority(tool)
            and executor_name is not None
            and executor_tool is not None
            and dispatch_authority(executor_tool)
        ):
            routed.append(
                f"{executor_name} {parts[1]}" if len(parts) > 1 else executor_name
            )
            routed.append("commit")
            changed = True
        else:
            routed.append(step)

    return routed if changed else steps
