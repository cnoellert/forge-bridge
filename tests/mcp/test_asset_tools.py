"""C.1 — MCP Asset tool integration tests."""
from __future__ import annotations

import json
import uuid

import pytest
import pytest_asyncio
from pydantic import ValidationError

from forge_bridge.core import Asset, Project, Registry, Shot, Status
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
        self._metadata_by_entity_id: dict[str, dict] = {}
        self._locations_by_entity_id: dict[str, list[dict]] = {}
        self._relationships_by_entity_id: dict[str, list[dict]] = {}

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
                self._metadata_by_entity_id[str(entity.id)] = dict(entity.metadata)
                return {"entity_id": str(entity.id)}

            if msg.type == MsgType.PROJECT_LIST:
                projects = await ProjectRepo(session).list_all()
                return {"projects": [project.to_dict() for project in projects]}

            if msg.type == MsgType.ENTITY_GET:
                entity = await entity_repo.get(uuid.UUID(msg["entity_id"]))
                if entity is None:
                    raise ValueError(f"Entity {msg['entity_id']} not found")
                data = entity.to_dict()
                data["metadata"] = dict(self._metadata_by_entity_id.get(str(entity.id), data["metadata"]))
                data["locations"] = list(self._locations_by_entity_id.get(str(entity.id), []))
                data["relationships"] = list(self._relationships_by_entity_id.get(str(entity.id), []))
                return data

            if msg.type == MsgType.ENTITY_LIST:
                entities = await entity_repo.list_by_type(
                    msg["entity_type"],
                    uuid.UUID(msg["project_id"]),
                )
                rows = []
                for entity in entities:
                    data = entity.to_dict()
                    data["metadata"] = dict(self._metadata_by_entity_id.get(str(entity.id), data["metadata"]))
                    data["locations"] = list(self._locations_by_entity_id.get(str(entity.id), []))
                    data["relationships"] = list(self._relationships_by_entity_id.get(str(entity.id), []))
                    rows.append(data)
                return {"entities": rows}

            if msg.type == MsgType.ENTITY_UPDATE:
                entity = await entity_repo.get(uuid.UUID(msg["entity_id"]))
                if entity is None:
                    raise ValueError(f"Entity {msg['entity_id']} not found")
                if msg.get("name") is not None and hasattr(entity, "name"):
                    entity.name = msg["name"]
                if msg.get("status") is not None and hasattr(entity, "status"):
                    entity.status = Status.from_string(msg["status"])
                attrs = dict(self._metadata_by_entity_id.get(str(entity.id), entity.metadata))
                for key, value in (msg.get("attributes") or {}).items():
                    if key == "entity_type":
                        continue
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                    else:
                        attrs[key] = value
                self._metadata_by_entity_id[str(entity.id)] = attrs
                entity.metadata = attrs
                await entity_repo.save(entity)
                await session.commit()
                return {}

            if msg.type == MsgType.LOC_ADD:
                entity = await entity_repo.get(uuid.UUID(msg["entity_id"]))
                if entity is None:
                    raise ValueError(f"Entity {msg['entity_id']} not found")
                loc = {
                    "path": msg["path"],
                    "storage_type": msg.get("storage_type", "local"),
                    "priority": msg.get("priority", 0),
                    "exists": False,
                    "metadata": {},
                }
                locations = self._locations_by_entity_id.setdefault(str(entity.id), [])
                locations.append(loc)
                locations.sort(key=lambda item: item["priority"], reverse=True)
                return {}

            if msg.type == MsgType.REL_CREATE:
                source = await entity_repo.get(uuid.UUID(msg["source_id"]))
                target = await entity_repo.get(uuid.UUID(msg["target_id"]))
                if source is None:
                    raise ValueError(f"Entity {msg['source_id']} not found")
                if target is None:
                    raise ValueError(f"Entity {msg['target_id']} not found")
                rel = {
                    "source_id": msg["source_id"],
                    "target_id": msg["target_id"],
                    "rel_type": msg["rel_type"],
                    "attributes": msg.get("attributes") or {},
                }
                self._relationships_by_entity_id.setdefault(str(source.id), []).append(rel)
                return {}

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


async def _create_asset(project_id: str, name: str, asset_type: str, status: str | None = None):
    result = await asset_tools.create_asset(
        asset_tools.CreateAssetInput(
            project_id=project_id,
            name=name,
            asset_type=asset_type,
            status=status,
        )
    )
    decoded = json.loads(result)
    assert "error" not in decoded, decoded
    return decoded["asset_id"]


async def _create_shot(session_factory, project_id: str, name: str = "SH010") -> str:
    shot = Shot(name=name)
    async with session_factory() as session:
        await EntityRepo(session, Registry.default()).save(shot, uuid.UUID(project_id))
        await session.commit()
    return str(shot.id)


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


@pytest.mark.asyncio
async def test_list_assets_filters_by_project(repo_client, project_id, session_factory):
    other_project = Project(name="Other Asset Test", code=f"OT{uuid.uuid4().hex[:8]}")
    async with session_factory() as session:
        await ProjectRepo(session).save(other_project)
        await session.commit()
    await _create_asset(project_id, "Project A Asset", "vehicle_spec")
    await _create_asset(str(other_project.id), "Project B Asset", "vehicle_spec")

    result = await asset_tools.list_assets(asset_tools.ListAssetsInput(project_id=project_id))

    decoded = json.loads(result)
    assert decoded["count"] == 1
    assert decoded["assets"][0]["name"] == "Project A Asset"


@pytest.mark.asyncio
async def test_list_assets_filters_by_asset_type(repo_client, project_id):
    await _create_asset(project_id, "Hero Car", "vehicle_spec")
    await _create_asset(project_id, "Hero Material", "material")

    result = await asset_tools.list_assets(asset_tools.ListAssetsInput(asset_type="material"))

    decoded = json.loads(result)
    assert decoded["count"] == 1
    assert decoded["assets"][0]["asset_type"] == "material"


@pytest.mark.asyncio
async def test_list_assets_empty_args(repo_client, project_id):
    await _create_asset(project_id, "All Assets", "reference_pack")

    result = await asset_tools.list_assets(None)

    decoded = json.loads(result)
    assert decoded["count"] >= 1
    assert any(asset["name"] == "All Assets" for asset in decoded["assets"])


@pytest.mark.asyncio
async def test_get_asset_returns_full_payload(repo_client, project_id):
    asset_id = await _create_asset(project_id, "Detailed Asset", "environment")

    result = await asset_tools.get_asset(asset_tools.GetAssetInput(asset_id=asset_id))

    decoded = json.loads(result)
    assert decoded["id"] == asset_id
    assert decoded["entity_type"] == "asset"
    assert decoded["asset_type"] == "environment"
    assert "locations" in decoded
    assert "relationships" in decoded


@pytest.mark.asyncio
async def test_get_asset_rejects_non_asset_uuid(repo_client, project_id, session_factory):
    shot_id = await _create_shot(session_factory, project_id)

    result = await asset_tools.get_asset(asset_tools.GetAssetInput(asset_id=shot_id))

    decoded = json.loads(result)
    assert decoded["error"] == f"Entity {shot_id} is not an asset"


@pytest.mark.asyncio
async def test_update_asset_merges_attributes(repo_client, project_id):
    asset_id = await _create_asset(project_id, "Merge Asset", "material")

    first = await asset_tools.update_asset(
        asset_tools.UpdateAssetInput(asset_id=asset_id, attributes={"color": "red"})
    )
    assert "error" not in json.loads(first)
    second = await asset_tools.update_asset(
        asset_tools.UpdateAssetInput(asset_id=asset_id, attributes={"scale": "large"})
    )
    assert "error" not in json.loads(second)

    loaded = json.loads(await asset_tools.get_asset(asset_tools.GetAssetInput(asset_id=asset_id)))
    assert loaded["metadata"]["color"] == "red"
    assert loaded["metadata"]["scale"] == "large"


@pytest.mark.asyncio
async def test_update_asset_changes_status_via_alias(repo_client, project_id):
    asset_id = await _create_asset(project_id, "Status Asset", "material")

    result = await asset_tools.update_asset(
        asset_tools.UpdateAssetInput(asset_id=asset_id, status="proposed")
    )

    assert "error" not in json.loads(result)
    loaded = json.loads(await asset_tools.get_asset(asset_tools.GetAssetInput(asset_id=asset_id)))
    assert loaded["status"] == "pending"


@pytest.mark.asyncio
async def test_update_asset_preserves_entity_type_against_smuggled_attribute(repo_client, project_id):
    asset_id = await _create_asset(project_id, "Guarded Asset", "material")

    result = await asset_tools.update_asset(
        asset_tools.UpdateAssetInput(
            asset_id=asset_id,
            attributes={"entity_type": "shot", "review_note": "keep"},
        )
    )

    assert "error" not in json.loads(result)
    loaded = json.loads(await asset_tools.get_asset(asset_tools.GetAssetInput(asset_id=asset_id)))
    assert loaded["entity_type"] == "asset"
    listed = json.loads(await asset_tools.list_assets(asset_tools.ListAssetsInput(project_id=project_id)))
    assert any(asset["asset_id"] == asset_id for asset in listed["assets"])


@pytest.mark.asyncio
async def test_attach_asset_location_round_trip(repo_client, project_id):
    asset_id = await _create_asset(project_id, "Located Asset", "cad_source")

    result = await asset_tools.attach_asset_location(
        asset_tools.AttachAssetLocationInput(
            asset_id=asset_id,
            path="/show/assets/car/model.usd",
            storage_type="network",
            priority=10,
        )
    )

    decoded = json.loads(result)
    assert decoded["attached"] is True
    loaded = json.loads(await asset_tools.get_asset(asset_tools.GetAssetInput(asset_id=asset_id)))
    assert loaded["locations"][0]["path"] == "/show/assets/car/model.usd"
    assert loaded["locations"][0]["storage_type"] == "network"


@pytest.mark.asyncio
async def test_attach_asset_location_rejects_non_asset(repo_client, project_id, session_factory):
    shot_id = await _create_shot(session_factory, project_id)

    result = await asset_tools.attach_asset_location(
        asset_tools.AttachAssetLocationInput(asset_id=shot_id, path="/show/shot.mov")
    )

    decoded = json.loads(result)
    assert decoded["error"] == f"Entity {shot_id} is not an asset"


@pytest.mark.asyncio
async def test_relate_asset_creates_edge(repo_client, project_id, session_factory):
    asset_id = await _create_asset(project_id, "Reference Asset", "reference_pack")
    shot_id = await _create_shot(session_factory, project_id)

    result = await asset_tools.relate_asset(
        asset_tools.RelateAssetInput(
            asset_id=asset_id,
            target_id=shot_id,
            rel_type="references",
            attributes={"note": "lookdev"},
        )
    )

    decoded = json.loads(result)
    assert decoded["related"] is True
    loaded = json.loads(await asset_tools.get_asset(asset_tools.GetAssetInput(asset_id=asset_id)))
    assert loaded["relationships"][0]["target_id"] == shot_id
    assert loaded["relationships"][0]["rel_type"] == "references"


@pytest.mark.asyncio
async def test_relate_asset_rejects_non_asset_source(repo_client, project_id, session_factory):
    source_shot_id = await _create_shot(session_factory, project_id, name="SH020")
    target_shot_id = await _create_shot(session_factory, project_id, name="SH030")

    result = await asset_tools.relate_asset(
        asset_tools.RelateAssetInput(
            asset_id=source_shot_id,
            target_id=target_shot_id,
            rel_type="references",
        )
    )

    decoded = json.loads(result)
    assert decoded["error"] == f"Entity {source_shot_id} is not an asset"
