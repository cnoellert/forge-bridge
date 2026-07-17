"""MCP round trip for fitted-model retention and two-phase collection."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.console.resources import register_console_resources
from forge_bridge.mcp.tools import (
    FinalizeFittedModelGcInput,
    FittedModelDeletionReceiptInput,
    ListFittedModelGcCandidatesInput,
    MarkFittedModelGcInput,
    SetFittedModelRetentionInput,
)
from tests.test_console_mcp_resources import _ResourceSpy
from tests.test_fitted_model_retention_gc import _registered_model


pytestmark = pytest.mark.asyncio
_NOW = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)


def _registered_tools(session_factory) -> _ResourceSpy:
    manifest = ManifestService()
    execution_log = MagicMock()
    execution_log.snapshot.return_value = ([], 0)
    execution_log._storage_callback = None
    api = ConsoleReadAPI(
        execution_log=execution_log,
        manifest_service=manifest,
        session_factory=session_factory,
    )
    spy = _ResourceSpy()
    register_console_resources(
        spy,
        manifest,
        api,
        session_factory=session_factory,
    )
    return spy


async def test_lifecycle_tools_round_trip_with_storage_receipt(session_factory):
    asset_id, location_id, path = await _registered_model(session_factory)
    tools = _registered_tools(session_factory).tools
    now = datetime.now(timezone.utc)

    retained = json.loads(await tools["forge_set_fitted_model_retention"](
        SetFittedModelRetentionInput(
            asset_id=str(asset_id),
            retention_until=(now - timedelta(days=1)).isoformat(),
            actor="operator",
            reason="show wrapped",
        )
    ))
    assert retained["data"]["retention_until"] == (
        now - timedelta(days=1)
    ).isoformat()

    candidates = json.loads(await tools["forge_list_fitted_model_gc_candidates"](
        ListFittedModelGcCandidatesInput(as_of=now.isoformat())
    ))
    assert candidates["meta"]["total"] == 1
    assert candidates["data"][0]["asset_id"] == str(asset_id)
    assert candidates["data"][0]["locations"][0]["path"] == path

    collect_after = datetime.now(timezone.utc) + timedelta(seconds=0.5)
    marked = json.loads(await tools["forge_mark_fitted_model_gc"](
        MarkFittedModelGcInput(
            asset_id=str(asset_id),
            actor="operator",
            collect_after=collect_after.isoformat(),
        )
    ))
    assert marked["data"]["gc_state"] == "marked"
    assert marked["data"]["locations"][0]["location_id"] == str(location_id)

    premature = json.loads(await tools["forge_finalize_fitted_model_gc"](
        FinalizeFittedModelGcInput(
            asset_id=str(asset_id),
            actor="collector",
            deletion_receipts=[],
        )
    ))
    assert premature["error"]["code"] == "gc_grace_active"

    await asyncio.sleep(0.6)
    collected = json.loads(await tools["forge_finalize_fitted_model_gc"](
        FinalizeFittedModelGcInput(
            asset_id=str(asset_id),
            actor="collector",
            deletion_receipts=[FittedModelDeletionReceiptInput(
                location_id=str(location_id),
                path=path,
                deleted=True,
                storage_receipt="s3-delete-version:tool-proof",
                provider_request_id="req-provider-1",
            )],
        )
    ))
    assert collected["data"]["gc_state"] == "collected"
    receipt = collected["data"]["deletion_receipts"][0]
    assert receipt["storage_receipt"] == "s3-delete-version:tool-proof"
    assert receipt["provider_request_id"] == "req-provider-1"


async def test_lifecycle_tool_returns_structured_errors(session_factory):
    tools = _registered_tools(session_factory).tools
    result = json.loads(await tools["forge_set_fitted_model_retention"](
        SetFittedModelRetentionInput(
            asset_id="not-a-uuid",
            retention_until=_NOW.isoformat(),
            actor="operator",
        )
    ))
    assert result["error"]["code"] == "bad_request"

    with pytest.raises(ValidationError):
        MarkFittedModelGcInput(
            asset_id="11111111-1111-1111-1111-111111111111",
            actor="   ",
            collect_after=(_NOW + timedelta(days=1)).isoformat(),
        )
