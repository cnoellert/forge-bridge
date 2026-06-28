"""Unit tests for ConsoleReadAPI (API-01 + EXECS-04 + API-04 precondition)."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI


def _make_record(name: str) -> ToolRecord:
    return ToolRecord(
        name=name, origin="synthesized", namespace="synth",
        tags=("synthesized",),
    )


def _patch_mcp_and_reachability(
    monkeypatch,
    tool_names: list[str],
    flame_ok: bool = True,
) -> None:
    """Bug C — stub the live MCP registry + reachability probe used by get_tools.

    Without this stub get_tools() would hit the real FastMCP singleton (which
    holds the actual ~49 builtins) and the real flame_bridge probe.
    """
    import forge_bridge.mcp.server as real_server
    from forge_bridge.console import _tool_filter

    async def _list_tools():
        return [SimpleNamespace(name=n) for n in tool_names]

    monkeypatch.setattr(
        real_server, "mcp",
        SimpleNamespace(list_tools=_list_tools),
    )

    async def _fake_reach():
        return {"flame_bridge": flame_ok}

    monkeypatch.setattr(_tool_filter, "_get_backend_reachability", _fake_reach)


# -- Instance-identity / construction ---------------------------------------


def test_console_read_api_init_requires_execution_log_and_manifest_service():
    with pytest.raises(TypeError):
        ConsoleReadAPI()  # no args
    with pytest.raises(TypeError):
        ConsoleReadAPI(execution_log=MagicMock())  # missing manifest_service
    # Both required args -> ok
    ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ManifestService())


# -- Tools delegation -------------------------------------------------------


async def test_get_tools_sources_from_mcp_with_manifest_enrichment(monkeypatch):
    """Bug C — get_tools() pulls from the live MCP registry; manifest enriches.

    The manifest carries provenance only for synthesized tools. Builtins live
    only in the MCP registry; get_tools() must surface them with origin="builtin".
    """
    ms = ManifestService()
    await ms.register(_make_record("synth_a"))
    _patch_mcp_and_reachability(
        monkeypatch,
        tool_names=["flame_ping", "forge_list_shots", "synth_a"],
        flame_ok=True,
    )
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    got = await api.get_tools()
    by_name = {t.name: t for t in got}

    # All three tools surface — no silent drops.
    assert set(by_name) == {"flame_ping", "forge_list_shots", "synth_a"}
    # Builtins synthesized into ToolRecord on the fly.
    assert by_name["flame_ping"].origin == "builtin"
    assert by_name["flame_ping"].namespace == "flame"
    assert by_name["forge_list_shots"].origin == "builtin"
    # Manifest enrichment wins for synthesized tools.
    assert by_name["synth_a"].origin == "synthesized"
    assert by_name["synth_a"].tags == ("synthesized",)


async def test_get_tools_marks_unreachable_but_never_drops(monkeypatch):
    """Bug C acceptance — flame/forge tools stay listed when backend is down."""
    ms = ManifestService()
    _patch_mcp_and_reachability(
        monkeypatch,
        tool_names=["flame_ping", "forge_list_shots", "forge_list_staged",
                    "synth_a"],
        flame_ok=False,
    )
    # Pre-register one synth so we know enrichment ran.
    await ms.register(_make_record("synth_a"))
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    got = await api.get_tools()
    av = {t.name: t.available for t in got}

    # Backend-dependent tools are present but marked unavailable.
    assert av["flame_ping"] is False
    assert av["forge_list_shots"] is False
    # In-process tools (the seven _IN_PROCESS_FORGE_TOOLS) and synth_* always
    # available — see _tool_filter._is_in_process_tool.
    assert av["forge_list_staged"] is True
    assert av["synth_a"] is True
    # No tools dropped — count matches the registry.
    assert len(got) == 4


def _patch_canonical_registry(monkeypatch, summaries: dict[str, str] | None) -> None:
    """Stub the daemon lifespan's _canonical_tool_registry.

    ``summaries=None`` simulates a standalone process (no live daemon) where the
    registry is None — every tool then resolves to its derived fallback. A dict
    installs a registry whose .get(name) returns a registration carrying the
    given summary (or None when the name is absent).
    """
    import forge_bridge.mcp.server as real_server

    if summaries is None:
        monkeypatch.setattr(real_server, "_canonical_tool_registry", None, raising=False)
        return

    class _Reg:
        def get(self, name):
            s = summaries.get(name)
            return SimpleNamespace(summary=s) if name in summaries else None

    monkeypatch.setattr(
        real_server, "_canonical_tool_registry", _Reg(), raising=False,
    )


async def test_get_tools_resolves_peer_summary_as_artist_description(monkeypatch):
    """The peer-authored CapabilityDeclaration.summary (carried onto
    ToolRegistration.summary) is the canonical artist description and wins."""
    ms = ManifestService()
    _patch_mcp_and_reachability(
        monkeypatch, tool_names=["forge_list_shots", "flame_ping"], flame_ok=True,
    )
    _patch_canonical_registry(
        monkeypatch, {"forge_list_shots": "List every shot in a sequence."},
    )
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    by_name = {t.name: t for t in await api.get_tools()}
    # Canonical peer summary surfaces verbatim.
    assert by_name["forge_list_shots"].artist_description == "List every shot in a sequence."
    # A tool with no registration falls back to the derived (humanized) label —
    # subordinate, never blank.
    assert by_name["flame_ping"].artist_description == "Flame ping"
    # to_dict carries the new field for the JSON/template surfaces.
    assert by_name["forge_list_shots"].to_dict()["artist_description"] == (
        "List every shot in a sequence."
    )


async def test_get_tools_registry_none_all_fallback(monkeypatch):
    """No live daemon registry in-process → every tool resolves to the derived
    fallback (the Console de-blank guard never yields a blank description)."""
    ms = ManifestService()
    _patch_mcp_and_reachability(
        monkeypatch, tool_names=["forge_list_shots"], flame_ok=True,
    )
    _patch_canonical_registry(monkeypatch, None)
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    (rec,) = await api.get_tools()
    # humanized from tool_id, never blank
    assert rec.artist_description == "Forge list shots"


async def test_get_tool_resolves_peer_summary(monkeypatch):
    ms = ManifestService()
    _patch_mcp_and_reachability(monkeypatch, tool_names=["forge_list_shots"])
    _patch_canonical_registry(
        monkeypatch, {"forge_list_shots": "List every shot in a sequence."},
    )
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    rec = await api.get_tool("forge_list_shots")
    assert rec is not None
    assert rec.artist_description == "List every shot in a sequence."


def _patch_canonical_registry_labels(monkeypatch, labels: dict[str, str] | None) -> None:
    """Stub the daemon registry returning registrations carrying ``label`` (mirrors
    _patch_canonical_registry for the short-name seam)."""
    import forge_bridge.mcp.server as real_server

    if labels is None:
        monkeypatch.setattr(real_server, "_canonical_tool_registry", None, raising=False)
        return

    class _Reg:
        def get(self, name):
            return SimpleNamespace(label=labels.get(name)) if name in labels else None

    monkeypatch.setattr(real_server, "_canonical_tool_registry", _Reg(), raising=False)


async def test_get_tools_resolves_peer_label_as_artist_label(monkeypatch):
    """The peer-authored CapabilityDeclaration.label (carried onto
    ToolRegistration.label) is the canonical short name and wins; a tool with no
    registration falls back to the derived humanized label (never blank)."""
    ms = ManifestService()
    _patch_mcp_and_reachability(
        monkeypatch, tool_names=["forge_list_shots", "flame_ping"], flame_ok=True,
    )
    _patch_canonical_registry_labels(monkeypatch, {"forge_list_shots": "List Shots"})
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    by_name = {t.name: t for t in await api.get_tools()}
    # Canonical peer label surfaces verbatim — distinct from the machine name.
    assert by_name["forge_list_shots"].artist_label == "List Shots"
    assert by_name["forge_list_shots"].name == "forge_list_shots"
    # No registration → derived humanized fallback, never blank.
    assert by_name["flame_ping"].artist_label == "Flame ping"
    # to_dict carries the additive field for JSON/template surfaces.
    assert by_name["forge_list_shots"].to_dict()["artist_label"] == "List Shots"


async def test_get_tools_label_registry_none_all_fallback(monkeypatch):
    """No live daemon registry → every tool resolves to the derived short-name
    fallback (the Console de-blank guard never yields a blank label)."""
    ms = ManifestService()
    _patch_mcp_and_reachability(
        monkeypatch, tool_names=["forge_list_shots"], flame_ok=True,
    )
    _patch_canonical_registry_labels(monkeypatch, None)
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    (rec,) = await api.get_tools()
    assert rec.artist_label == "Forge list shots"


async def test_get_tool_resolves_peer_label(monkeypatch):
    ms = ManifestService()
    _patch_mcp_and_reachability(monkeypatch, tool_names=["forge_list_shots"])
    _patch_canonical_registry_labels(monkeypatch, {"forge_list_shots": "List Shots"})
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    rec = await api.get_tool("forge_list_shots")
    assert rec is not None
    assert rec.artist_label == "List Shots"


async def test_get_tool_surfaces_builtin_with_availability(monkeypatch):
    ms = ManifestService()
    await ms.register(_make_record("synth_a"))
    _patch_mcp_and_reachability(
        monkeypatch,
        tool_names=["flame_ping", "synth_a"],
        flame_ok=True,
    )
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    builtin = await api.get_tool("flame_ping")
    assert builtin is not None
    assert builtin.name == "flame_ping"
    assert builtin.origin == "builtin"
    assert builtin.available is True

    synth = await api.get_tool("synth_a")
    assert synth is not None
    assert synth.origin == "synthesized"
    assert synth.available is True

    assert await api.get_tool("nope") is None  # unregistered name


async def test_get_tool_marks_unreachable_builtin_unavailable(monkeypatch):
    ms = ManifestService()
    _patch_mcp_and_reachability(
        monkeypatch,
        tool_names=["flame_ping"],
        flame_ok=False,
    )
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)

    rec = await api.get_tool("flame_ping")
    assert rec is not None
    assert rec.available is False  # still surfaced, just flagged


async def test_to_dict_carries_available_field():
    """Bug C — to_dict must serialize the new field for the JSON envelope."""
    rec = ToolRecord(name="x", origin="builtin", namespace="flame", available=False)
    d = rec.to_dict()
    assert "available" in d
    assert d["available"] is False


# -- Executions forwarding --------------------------------------------------


async def test_get_executions_forwards_all_kwargs_to_snapshot():
    # W-01: `tool` kwarg intentionally absent -- route layer rejects with 400.
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ManifestService())
    since = datetime(2026, 4, 22, 0, 0, 0)
    await api.get_executions(
        limit=5, offset=2, since=since,
        promoted_only=True, code_hash="abc",
    )
    mock_log.snapshot.assert_called_once_with(
        limit=5, offset=2, since=since,
        promoted_only=True, code_hash="abc",
    )


async def test_get_executions_does_not_accept_tool_kwarg():
    """W-01: `tool` kwarg must NOT exist on ConsoleReadAPI.get_executions.

    The /api/v1/execs route handler in Plan 09-03 rejects `?tool=...` with
    a 400 `not_implemented` response; the read layer therefore never sees
    it and should not quietly accept it.
    """
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ManifestService())
    with pytest.raises(TypeError):
        # Attempting to pass tool= must raise (unexpected kwarg)
        await api.get_executions(tool="synth_*")


# -- Manifest envelope shape -----------------------------------------------


async def test_get_manifest_returns_envelope_shape():
    ms = ManifestService()
    await ms.register(_make_record("a"))
    await ms.register(_make_record("b"))
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ms)
    got = await api.get_manifest()
    assert set(got.keys()) == {"tools", "count", "schema_version"}
    assert got["count"] == 2
    assert got["schema_version"] == "1"
    assert isinstance(got["tools"], list)
    assert got["tools"][0]["name"] == "a"
    # tags should be on the wire as a list, not a tuple
    assert isinstance(got["tools"][0]["tags"], list)


# -- Async method signatures -----------------------------------------------


def test_get_tools_is_async():
    assert asyncio.iscoroutinefunction(ConsoleReadAPI.get_tools)


def test_get_executions_is_async():
    assert asyncio.iscoroutinefunction(ConsoleReadAPI.get_executions)


def test_get_manifest_is_async():
    assert asyncio.iscoroutinefunction(ConsoleReadAPI.get_manifest)


# -- session_factory constructor parameter (D-03 / FB-B) --------------------
# These tests do NOT require Postgres — they only test constructor behavior.

def test_console_read_api_session_factory_defaults_to_none():
    """session_factory kwarg must default to None (backward-compat guard)."""
    api = ConsoleReadAPI(execution_log=MagicMock(), manifest_service=ManifestService())
    assert api._session_factory is None


def test_console_read_api_session_factory_stored():
    """session_factory passed to __init__ must be stored as _session_factory."""
    sentinel = MagicMock()
    api = ConsoleReadAPI(
        execution_log=MagicMock(),
        manifest_service=ManifestService(),
        session_factory=sentinel,
    )
    assert api._session_factory is sentinel


def test_get_staged_ops_is_async():
    assert asyncio.iscoroutinefunction(ConsoleReadAPI.get_staged_ops)


def test_get_staged_op_is_async():
    assert asyncio.iscoroutinefunction(ConsoleReadAPI.get_staged_op)


# -- get_staged_ops / get_staged_op integration tests (require Postgres) -----
# These use the session_factory fixture from conftest.py, which skips cleanly
# when Postgres at localhost:5432 is unavailable (local-first philosophy).


@pytest_asyncio.fixture
async def api_with_session_factory(session_factory):
    """ConsoleReadAPI wired to a real per-test session_factory (D-03)."""
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    return ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ManifestService(),
        session_factory=session_factory,
    )


async def test_get_staged_ops_returns_tuple(api_with_session_factory, session_factory):
    """get_staged_ops() returns (list, int) with correct counts."""
    from forge_bridge.store.staged_operations import StagedOpRepo
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.propose(operation="a", proposer="x", parameters={})
        await repo.propose(operation="b", proposer="x", parameters={})
        await session.commit()
    records, total = await api_with_session_factory.get_staged_ops()
    assert total == 2
    assert len(records) == 2


async def test_get_staged_ops_filter_by_status(api_with_session_factory, session_factory):
    """get_staged_ops(status='proposed') returns only proposed ops."""
    from forge_bridge.store.staged_operations import StagedOpRepo
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op1 = await repo.propose(operation="flame.publish", proposer="x", parameters={})
        op2 = await repo.propose(operation="flame.export", proposer="x", parameters={})
        await session.commit()
    # Approve op2 in a separate session
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.approve(op2.id, approver="x")
        await session.commit()
    records, total = await api_with_session_factory.get_staged_ops(status="proposed")
    assert total == 1
    assert len(records) == 1
    assert records[0].status == "proposed"


async def test_get_staged_ops_pagination_passes_through(api_with_session_factory, session_factory):
    """Pagination limit/offset pass through to repo.list()."""
    from forge_bridge.store.staged_operations import StagedOpRepo
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        for i in range(5):
            await repo.propose(operation=f"op_{i}", proposer="x", parameters={})
        await session.commit()
    page1, total1 = await api_with_session_factory.get_staged_ops(limit=2, offset=0)
    assert len(page1) == 2
    assert total1 == 5
    page2, total2 = await api_with_session_factory.get_staged_ops(limit=2, offset=2)
    assert len(page2) == 2
    assert total2 == 5


async def test_get_staged_op_returns_record(api_with_session_factory, session_factory):
    """get_staged_op(op.id) returns the StagedOperation with the correct id."""
    from forge_bridge.store.staged_operations import StagedOpRepo
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op = await repo.propose(operation="flame.publish", proposer="x", parameters={})
        await session.commit()
    result = await api_with_session_factory.get_staged_op(op.id)
    assert result is not None
    assert result.id == op.id


async def test_get_staged_op_returns_none_for_unknown(api_with_session_factory):
    """get_staged_op(bogus_uuid) returns None."""
    bogus = uuid.uuid4()
    result = await api_with_session_factory.get_staged_op(bogus)
    assert result is None


async def test_get_staged_ops_opens_fresh_session_per_call(
    api_with_session_factory, session_factory,
):
    """Two successive get_staged_ops() calls must not raise RuntimeError about closed session."""
    from forge_bridge.store.staged_operations import StagedOpRepo
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        await repo.propose(operation="flame.publish", proposer="x", parameters={})
        await session.commit()
    # Both calls must succeed independently — per-call session pattern (D-03)
    result1, _ = await api_with_session_factory.get_staged_ops()
    result2, _ = await api_with_session_factory.get_staged_ops()
    assert len(result1) == len(result2)
