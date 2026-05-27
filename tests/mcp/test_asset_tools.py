"""C.1 — MCP Asset tool integration tests."""
from __future__ import annotations

import json
import uuid

import pytest
import pytest_asyncio
from pydantic import ValidationError

from forge_bridge.core import Asset, Project, Registry, Status
from forge_bridge.mcp import tools as asset_tools
from forge_bridge.mcp.registry import register_builtins
from forge_bridge.server.protocol import MsgType, entity_get
from forge_bridge.store.repo import EntityRepo, ProjectRepo


class _ToolSpy:
    def __init__(self):
        self.tools: dict[str, callable] = {}
        self.registered_tools: dict[str, dict] = {}

    def add_tool(self, fn, *, name, annotations=None, meta=None):
        self.tools[name] = fn
        self.registered_tools[name] = {
            "annotations": annotations or {},
            "meta": meta or {},
        }

    def resource(self, *_args, **_kwargs):
        def decorator(fn):
            return fn
        return decorator


class _RepoBackedClient:
    """Tiny protocol client backed by the real store repositories.

    The MCP tool bodies still build wire protocol messages; this test client
    handles those messages against the real session_factory database so JSONB
    fields such as asset_type round-trip through EntityRepo.
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def request(self, msg):
        async with self._session_factory() as session:
            entity_repo = EntityRepo(session, Registry.default())
            if msg.type == MsgType.ENTITY_CREATE:
                if msg["entity_type"] == "asset":
                    entity = Asset(
                        name=msg.get("name") or "",
                        asset_type=(msg.get("attributes") or {}).get("asset_type", "generic"),
                        project_id=msg.get("project_id"),
                        status=msg.get("status") or Status.PENDING,
                        metadata=msg.get("attributes") or {},
                    )
                else:
                    raise AssertionError(f"unsupported entity_create type {msg['entity_type']!r}")
                await entity_repo.save(entity, uuid.UUID(msg["project_id"]))
                await session.commit()
                return {"entity_id": str(entity.id)}

            if msg.type == MsgType.ENTITY_GET:
                entity = await entity_repo.get(uuid.UUID(msg["entity_id"]))
                if entity is None:
                    raise ValueError(f"Entity {msg['entity_id']} not found")
                return entity.to_dict()

        raise AssertionError(f"unsupported message type {msg.type!r}")


@pytest_asyncio.fixture
async def project_id(session_factory):
    project = Project(name="Asset Test", code=f"AT{uuid.uuid4().hex[:8]}")
    async with session_factory() as session:
        await ProjectRepo(session).save(project)
        await session.commit()
    return str(project.id)


@pytest.fixture
def repo_client(session_factory, monkeypatch):
    client = _RepoBackedClient(session_factory)
    monkeypatch.setattr(asset_tools, "_client", lambda: client)
    return client


def test_create_asset_requires_asset_type():
    with pytest.raises(ValidationError):
        asset_tools.CreateAssetInput()
    with pytest.raises(ValidationError):
        asset_tools.CreateAssetInput(project_id=str(uuid.uuid4()), name="Hero Car")


@pytest.mark.asyncio
async def test_create_asset_round_trip(repo_client, project_id):
    result = await asset_tools.create_asset(
        asset_tools.CreateAssetInput(
            project_id=project_id,
            name="Hero Car",
            asset_type="vehicle_spec",
            attributes={"department": "art"},
        )
    )

    decoded = json.loads(result)
    assert "error" not in decoded, decoded
    assert decoded["created"] is True
    assert decoded["asset_type"] == "vehicle_spec"

    stored = await repo_client.request(entity_get(decoded["asset_id"]))
    assert stored["entity_type"] == "asset"
    assert stored["name"] == "Hero Car"
    assert stored["asset_type"] == "vehicle_spec"
    assert stored["status"] == "pending"


@pytest.mark.asyncio
async def test_create_asset_accepts_open_asset_type(repo_client, project_id):
    result = await asset_tools.create_asset(
        asset_tools.CreateAssetInput(
            project_id=project_id,
            name="Open Type",
            asset_type="vehicle_spec",
        )
    )

    decoded = json.loads(result)
    assert "error" not in decoded, decoded
    assert decoded["created"] is True
    assert decoded["asset_type"] == "vehicle_spec"


def test_create_asset_registered_with_pr22_annotations():
    spy = _ToolSpy()
    register_builtins(spy)

    assert "forge_create_asset" in spy.tools
    annotations = spy.registered_tools["forge_create_asset"]["annotations"]
    assert annotations["readOnlyHint"] is False
    assert annotations["idempotentHint"] is False
