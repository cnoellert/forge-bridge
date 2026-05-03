"""PR16 — high-collision tool descriptions follow the disambiguation template.

These descriptions are what the LLM sees when picking a tool. The PR16
template requires every disambiguated tool to:
  1. Lead with a domain prefix (``Flame:`` or ``Forge:``).
  2. Include a positive ``Use this tool ONLY when`` block.
  3. Include a negative ``Do NOT use this tool for`` block (with at least
     one explicit redirect to a sibling tool).

This test exists so a future docstring edit can't accidentally weaken the
disambiguation contract for the most-confused tools (the ``list_*`` /
``get_*`` cluster).

PR16 scope is the high-collision tools enumerated in ``_PR16_TOOLS``. The
remaining tools may still use shorter descriptions. Adding a tool to that
list is how you opt in to the contract.
"""
from __future__ import annotations

import asyncio

import pytest


# Tools that MUST follow the PR16 disambiguation contract.
# Cluster: list_* and get_* across both Flame and Forge domains plus the
# in-process forge tools that share verbs ("staged" / "manifest" / "tools").
_PR16_TOOLS = frozenset({
    # Flame project / library / desktop / context cluster
    "flame_get_project",
    "flame_list_libraries",
    "flame_list_desktop",
    "flame_context",
    "flame_find_media",
    # Forge pipeline registry cluster
    "forge_list_projects",
    "forge_get_project",
    "forge_list_shots",
    "forge_get_shot",
    "forge_list_versions",
    "forge_list_roles",
    "forge_list_media",
    "forge_list_published_plates",
    # In-process forge_* (staged ops + read shims)
    "forge_manifest_read",
    "forge_tools_read",
    "forge_list_staged",
    "forge_get_staged",
    "forge_approve_staged",
    "forge_reject_staged",
    "forge_staged_pending_read",
})


def _registry_descriptions() -> dict[str, str]:
    """Return {tool_name: description} for every tool the MCP server exposes.

    Drives the tool list off the live MCP registry so we exercise the same
    text the LLM actually sees — not just the source-level docstrings.

    ``register_builtins`` runs at import; the in-process ``forge_*`` cluster
    is registered by ``register_console_resources``, which the daemon only
    invokes inside its lifespan. We register it here with stub deps so the
    full surface is visible to the test."""
    from unittest.mock import MagicMock
    from forge_bridge.mcp import server as mcp_server
    from forge_bridge.console.resources import register_console_resources

    # Stub manifest_service / console_read_api / session_factory — we never
    # invoke the tools, just inspect their registration metadata.
    fake_manifest_service = MagicMock()
    fake_api = MagicMock()
    fake_session_factory = MagicMock()
    try:
        register_console_resources(
            mcp_server.mcp,
            manifest_service=fake_manifest_service,
            console_read_api=fake_api,
            session_factory=fake_session_factory,
        )
    except Exception:
        # Already registered (re-import in same process) — that's fine.
        pass

    async def _list():
        return await mcp_server.mcp.list_tools()

    tools = asyncio.run(_list())
    return {t.name: (t.description or "") for t in tools}


@pytest.fixture(scope="module")
def descriptions() -> dict[str, str]:
    return _registry_descriptions()


def test_pr16_tools_present_in_registry(descriptions):
    """Sanity: every tool we're asserting on must actually be registered."""
    missing = sorted(_PR16_TOOLS - set(descriptions))
    assert not missing, (
        "PR16 tools missing from the live MCP registry — list out of date?\n"
        f"  Missing: {missing}"
    )


@pytest.mark.parametrize("tool_name", sorted(_PR16_TOOLS))
def test_pr16_description_contains_use_only_when(tool_name, descriptions):
    """Every disambiguated tool description MUST include the positive block."""
    desc = descriptions[tool_name]
    assert "Use this tool ONLY when" in desc, (
        f"{tool_name}: description does not contain 'Use this tool ONLY when'\n"
        f"  description={desc!r}"
    )


@pytest.mark.parametrize("tool_name", sorted(_PR16_TOOLS))
def test_pr16_description_contains_do_not_use_for(tool_name, descriptions):
    """Every disambiguated tool description MUST include the negative block."""
    desc = descriptions[tool_name]
    assert "Do NOT use this tool for" in desc, (
        f"{tool_name}: description does not contain 'Do NOT use this tool for'\n"
        f"  description={desc!r}"
    )


@pytest.mark.parametrize("tool_name", sorted(_PR16_TOOLS))
def test_pr16_description_starts_with_domain_prefix(tool_name, descriptions):
    """Every disambiguated tool description MUST start with a domain prefix.

    Flame-prefixed tools start with ``Flame:`` and forge-prefixed tools
    start with ``Forge:`` so the model can latch onto the domain in one
    glance, even before reading the rules."""
    desc = descriptions[tool_name].lstrip()
    if tool_name.startswith("flame_"):
        assert desc.startswith("Flame:"), (
            f"{tool_name}: description must start with 'Flame:' — got {desc[:60]!r}"
        )
    elif tool_name.startswith("forge_"):
        assert desc.startswith("Forge:"), (
            f"{tool_name}: description must start with 'Forge:' — got {desc[:60]!r}"
        )
    else:
        pytest.fail(
            f"unexpected tool prefix in PR16 set: {tool_name}"
        )


def test_pr16_flame_list_libraries_disambiguates_against_projects(descriptions):
    """The motivating UAT case — flame_list_libraries description must
    redirect 'projects' queries away from itself."""
    desc = descriptions["flame_list_libraries"]
    assert "forge_list_projects" in desc, (
        "flame_list_libraries should explicitly redirect to forge_list_projects "
        "in its 'Do NOT use this tool for' block."
    )


def test_pr16_forge_list_projects_disambiguates_against_libraries(descriptions):
    """And the reverse — forge_list_projects must steer 'libraries' away."""
    desc = descriptions["forge_list_projects"]
    assert "flame_list_libraries" in desc, (
        "forge_list_projects should explicitly redirect to flame_list_libraries "
        "in its 'Do NOT use this tool for' block."
    )
