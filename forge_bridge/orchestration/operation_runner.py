"""Daemon-edge adapter for forge-core operation dispatch.

Composition owns the graph boundary and receives an injected ``run_operation``
callable. This module is the optional federation seam that builds that callable
when a compatible forge-core/Pipeline installation is present.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class OperationRunnerUnavailable(ImportError):
    """Raised when the forge-core operation-dispatch surface is unavailable."""


DEFAULT_OPERATION_RECEIPT_DIR = Path.home() / ".forge-bridge" / "operation-receipts"


def build_operation_runner(
    registry: Any | None = None,
    *,
    receipt_dir: str | Path | None = None,
):
    """Return an async callable matching ``OperationDispatchBoundary``.

    The import is deliberately guarded: stock Bridge installations may not have
    Pipeline's forge-core operation dispatcher installed. In that case callers
    can degrade the boundary to declaration-dark instead of crashing bootstrap.
    """

    try:
        from forge_core.operations import OperationRequest
        from forge_core.operations.dispatch import dispatch
        from forge_core.operations.registry import get_default_registry
    except (ImportError, ModuleNotFoundError) as exc:
        raise OperationRunnerUnavailable(
            "forge_core operation dispatch is unavailable"
        ) from exc

    reg = registry or get_default_registry()

    async def run_operation(
        operation_type: str,
        *,
        params: Mapping[str, Any],
        receipt_path: str | None = None,
        **metadata: Any,
    ) -> Any:
        idempotency_key = metadata.get("idempotency_key") or _derive_idempotency_key(
            operation_type=operation_type,
            params=params,
            metadata=metadata,
        )
        resolved_receipt_path = receipt_path
        if resolved_receipt_path is None:
            target_dir = (
                Path(receipt_dir)
                if receipt_dir is not None
                else DEFAULT_OPERATION_RECEIPT_DIR
            )
            target_dir = target_dir.expanduser()
            target_dir.mkdir(parents=True, exist_ok=True)
            resolved_receipt_path = str(target_dir / f"{idempotency_key}.jsonl")

        request = OperationRequest(
            operation_type=operation_type,
            bridge_asset_ids=list(metadata.get("bridge_asset_ids") or []),
            idempotency_key=idempotency_key,
            params=dict(params),
            project_id=metadata.get("project_id"),
            requested_by=metadata.get("requested_by"),
        )
        return await dispatch(request, reg, receipt_path=resolved_receipt_path)

    return run_operation


def _derive_idempotency_key(
    *,
    operation_type: str,
    params: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> str:
    """Derive a stable key when the graph caller omits one."""

    seed = json.dumps(
        {
            "operation_type": operation_type,
            "params": params,
            "bridge_asset_ids": list(metadata.get("bridge_asset_ids") or []),
            "project_id": metadata.get("project_id"),
            "requested_by": metadata.get("requested_by"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
