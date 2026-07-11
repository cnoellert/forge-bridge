"""Slice A (#160) — the canonical `fitted-model` asset registration shape.

A guard/integration test proving a fitted-model asset registers through the
EXISTING store surface — no new MCP tool, no new entity type, no migration.
It pins the shape that forge-generators must author when it publishes a trained
model:

  * an ``Asset`` with ``asset_type="fitted-model"`` (the literal string, so the
    future forge-contracts symbol promotion is a zero-migration symbol-bind),
  * a ``Version(parent_type="asset")`` iteration (the ``version_of`` axis Asset
    already carries via the Versionable trait),
  * the weights blob riding as a ``Media`` + a cloud/archive ``Location``
    (the Locatable trait), and
  * a ``derived_from`` lineage edge from the model to its training input(s).

Everything here is an EXISTING surface — ``create_asset`` / ``Version`` /
``add_location`` / ``Relationship`` — so no helper is warranted (YAGNI): the
test itself documents the canonical shape.
"""

from __future__ import annotations

import uuid

import pytest

from forge_bridge.core import Asset, Project, Registry, Status
from forge_bridge.core.entities import Media, Version
from forge_bridge.core.traits import Relationship
from forge_bridge.store.repo import (
    EntityRepo,
    LocationRepo,
    ProjectRepo,
    RelationshipRepo,
)

pytestmark = pytest.mark.asyncio


async def test_fitted_model_registers_through_existing_surface(session_factory):
    project = Project(name="Fitted Model Test", code=f"FM{uuid.uuid4().hex[:8]}")

    # The training input the model was fitted from (the lineage anchor). A plain
    # asset stands in for whatever real corpus/plates the fit consumed.
    training_input = Asset(
        name="Training Plates",
        asset_type="training-dataset",
        project_id=project.id,
        status=Status.APPROVED,
    )

    # The fitted model itself — the literal `fitted-model` asset_type EVERYWHERE.
    model = Asset(
        name="hero_deblur.fitted",
        asset_type="fitted-model",
        project_id=project.id,
        status=Status.APPROVED,
    )

    # A Version iteration of the model (parent_type="asset" — the Versionable
    # axis). Version.__init__ stamps the version_of auto-edge on the core object.
    version = Version(version_number=1, parent_id=model.id, parent_type="asset")

    # The GB weights blob rides as a Media atom carrying a cloud/archive
    # Location (Locatable). It references the model version.
    weights = Media(
        format="safetensors",
        version_id=version.id,
        name="hero_deblur.v1.safetensors",
    )
    weights.add_location(
        "s3://forge-models/hero_deblur/v1/weights.safetensors",
        storage_type="cloud",
        priority=10,
    )

    # ── register through the existing store surfaces ──────────────────────
    async with session_factory() as session:
        registry = Registry.default()
        entity_repo = EntityRepo(session, registry)

        await ProjectRepo(session).save(project)
        for entity in (training_input, model, version, weights):
            await entity_repo.save(entity, project.id)

        # Persist the weights blob's cloud location (Locatable → DBLocation).
        await LocationRepo(session).save_entity_locations(weights)

        rel_repo = RelationshipRepo(session)
        # Lineage: the fitted model derived_from its training input.
        await rel_repo.save(
            Relationship(
                source_id=model.id,
                target_id=training_input.id,
                rel_key="derived_from",
            )
        )
        # The version_of edge (auto-stamped on the core object above) is
        # persisted explicitly through the relationship repo.
        await rel_repo.save(
            Relationship(
                source_id=version.id,
                target_id=model.id,
                rel_key="version_of",
            )
        )
        await session.commit()

    # ── assert the canonical shape round-trips ────────────────────────────
    async with session_factory() as session:
        entity_repo = EntityRepo(session, Registry.default())

        stored_model = await entity_repo.get(model.id)
        assert stored_model is not None
        assert stored_model.entity_type == "asset"
        assert stored_model.asset_type == "fitted-model"

        stored_version = await entity_repo.get(version.id)
        assert stored_version is not None
        assert stored_version.entity_type == "version"
        assert stored_version.parent_type == "asset"
        assert stored_version.parent_id == model.id

        # The weights blob is a Media atom at a cloud (or archive) Location.
        locations = await LocationRepo(session).get_entity_locations(weights.id)
        assert locations, "expected a persisted weights blob location"
        assert any(
            loc.storage_type in ("cloud", "archive") for loc in locations
        ), [loc.storage_type for loc in locations]

        rel_repo = RelationshipRepo(session)
        # The derived_from lineage edge points model → training input.
        model_deps = await rel_repo.get_dependencies(model.id)
        assert training_input.id in model_deps

        # The version_of edge points version → model.
        version_deps = await rel_repo.get_dependencies(version.id)
        assert model.id in version_deps
