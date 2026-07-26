"""Shared mechanics for durable, closed, fingerprinted product workflows.

#235 / Phase 149 shipped the first one (``editorial_edit_workflow``). #242 adds
a structural sibling (``editorial_workspace_publish_workflow``). What the two
share is *mechanism*, not *meaning*: canonical fingerprinting, a durable
proposal-keyed store, receipt closure + fingerprinting, refusal plumbing, the
commit-outcome readers, and the per-proposal transition guard.

What deliberately does NOT live here (it is per-workflow semantics, and
collapsing it would make one workflow's contract silently govern the other):

- the proposal field set and its validation;
- graph composition (which tool feeds ``commit``);
- receipt status/recovery vocabularies and their invariants;
- recovery / restore rail semantics.

Nothing in this module knows a workflow's reason codes. Callers that need a
code pass it in.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Optional, Protocol


def canonical_fingerprint(value: Any) -> str:
    """sha256 over canonical JSON (sorted keys, compact separators)."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Durable workflow store
# --------------------------------------------------------------------------- #
class WorkflowStore(Protocol):
    """Durable correlation store keyed by ``proposal_id``.

    ``get_by_authority_fingerprint`` looks the record up by the ONE upstream
    authority fingerprint a workflow binds exclusively (the preview authority
    for #235, the publish preview for #242) so a second proposal cannot rebind
    the same authority.
    """

    async def get_by_proposal_id(
        self, proposal_id: str
    ) -> Optional[dict[str, Any]]: ...

    async def get_by_authority_fingerprint(
        self, fingerprint: str
    ) -> Optional[dict[str, Any]]: ...

    async def create(self, record: dict[str, Any]) -> dict[str, Any]: ...

    async def update(
        self, proposal_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]: ...


class InMemoryWorkflowStore:
    """Process-local store. NOT durable across restarts — for tests and for a
    stock install without Postgres. Production uses the session-factory store.

    ponytail: a plain dict; the DB store is the authority.
    """

    def __init__(self, *, authority_field: str) -> None:
        self._authority_field = authority_field
        self._rows: dict[str, dict[str, Any]] = {}

    async def get_by_proposal_id(
        self, proposal_id: str
    ) -> Optional[dict[str, Any]]:
        row = self._rows.get(proposal_id)
        return dict(row) if row is not None else None

    async def get_by_authority_fingerprint(
        self, fingerprint: str
    ) -> Optional[dict[str, Any]]:
        for row in self._rows.values():
            if row.get(self._authority_field) == fingerprint:
                return dict(row)
        return None

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        proposal_id = str(record["proposal_id"])
        if proposal_id in self._rows:
            raise ValueError(f"workflow already exists: {proposal_id}")
        self._rows[proposal_id] = dict(record)
        return dict(record)

    async def update(
        self, proposal_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        row = self._rows[proposal_id]
        row.update(patch)
        return dict(row)


class SessionFactoryWorkflowStore:
    """Durable store backed by a workflow repo class + a session factory.

    Opens and commits one session per operation, matching the repos'
    caller-owns-the-transaction contract. ``repo_factory`` builds the repo from
    a session; ``authority_method`` names the repo's authority lookup so a repo
    can keep a domain-specific method name (#235's shipped repo does).
    """

    def __init__(
        self,
        session_factory: Any,
        *,
        repo_factory: Callable[[Any], Any],
        authority_method: str = "get_by_authority_fingerprint",
    ) -> None:
        self._session_factory = session_factory
        self._repo_factory = repo_factory
        self._authority_method = authority_method

    async def get_by_proposal_id(
        self, proposal_id: str
    ) -> Optional[dict[str, Any]]:
        async with self._session_factory() as session:
            repo = self._repo_factory(session)
            return await repo.get_by_proposal_id(proposal_id)

    async def get_by_authority_fingerprint(
        self, fingerprint: str
    ) -> Optional[dict[str, Any]]:
        async with self._session_factory() as session:
            repo = self._repo_factory(session)
            lookup = getattr(repo, self._authority_method)
            return await lookup(fingerprint)

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        async with self._session_factory() as session:
            created = await self._repo_factory(session).create(record)
            await session.commit()
            return created

    async def update(
        self, proposal_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        async with self._session_factory() as session:
            repo = self._repo_factory(session)
            current = await repo.get_by_proposal_id(proposal_id)
            merged = dict(current or {})
            merged.update(patch)
            updated = await repo.update(proposal_id, merged)
            await session.commit()
            return updated


# --------------------------------------------------------------------------- #
# Per-proposal transition guard
# --------------------------------------------------------------------------- #
class ProposalTransitionGuard:
    """Serialize mutating transitions per proposal, then re-read durable state.

    ponytail: a per-process async lock keyed by ``proposal_id``. Multi-worker
    deployments need a DB advisory lock; ``reload`` (re-reading the durable row
    INSIDE the lock, so the caller's status check sees committed state) is the
    cross-process backstop that keeps the failure closed rather than doubled.
    """

    def __init__(self, store: WorkflowStore) -> None:
        self._store = store
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def lock(self, proposal_id: str) -> asyncio.Lock:
        return self._locks[proposal_id]

    async def reload(self, proposal_id: str) -> Optional[dict[str, Any]]:
        return await self._store.get_by_proposal_id(proposal_id)


# --------------------------------------------------------------------------- #
# Receipts
# --------------------------------------------------------------------------- #
class ReceiptFieldSetError(ValueError):
    """The assembled receipt is not exactly the closed field set."""


def finalize_receipt(
    receipt: Mapping[str, Any],
    keys: tuple[str, ...],
    *,
    fingerprint_excludes: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Order a receipt to its closed field set and append its fingerprint.

    Fails closed on a missing OR unknown field — a receipt that drifted from the
    published field set is not a receipt the consumer can pin against.
    """
    supplied = set(receipt)
    expected = set(keys)
    if supplied != expected:
        raise ReceiptFieldSetError(
            "receipt fields differ from the closed set: "
            f"missing={sorted(expected - supplied)} "
            f"unknown={sorted(supplied - expected)}"
        )
    ordered = {key: receipt[key] for key in keys}
    body = {
        key: value
        for key, value in ordered.items()
        if key not in fingerprint_excludes
    }
    ordered["fingerprint"] = canonical_fingerprint(body)
    return ordered


BuildReceipt = Callable[..., dict[str, Any]]


def refuse(
    build_receipt: BuildReceipt,
    action: str,
    workflow: Mapping[str, Any],
    reason_code: str,
    *,
    action_status: Optional[str] = None,
) -> dict[str, Any]:
    """Emit a closed refusal receipt without mutating durable state."""
    refused = dict(workflow)
    refused["reason_code"] = reason_code
    if action_status is None:
        return build_receipt(action, refused, action_status="refused")
    return build_receipt(action, refused, action_status=action_status)


def fingerprint_refusal(
    build_receipt: BuildReceipt,
    action: str,
    workflow: Mapping[str, Any],
    expected_proposal_fingerprint: str,
    reason_code: str,
    *,
    action_status: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Refuse when the caller's expected proposal fingerprint has drifted."""
    if workflow["proposal_fingerprint"] != expected_proposal_fingerprint:
        return refuse(
            build_receipt,
            action,
            workflow,
            reason_code,
            action_status=action_status,
        )
    return None


# --------------------------------------------------------------------------- #
# Commit-outcome readers
# --------------------------------------------------------------------------- #
def held_manifest_from_record(record: Any) -> Optional[dict[str, Any]]:
    """The held mutation manifest persisted on a proposed AssentRecord."""
    metadata = getattr(record, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    replay = metadata.get("graph_replay")
    if not isinstance(replay, dict):
        return None
    held = replay.get("held_manifest")
    return held if isinstance(held, dict) else None


def apply_failure_reason(
    commit_result: Any,
    *,
    commit_failed: str,
    assent_invalid: str,
) -> str:
    """Map a CommitBoundary reason code onto a workflow refusal code."""
    reason_code = getattr(commit_result, "reason_code", None)
    if reason_code in {"PLAN_STATE_DRIFT", "VERIFICATION_FAILED"}:
        return commit_failed
    if reason_code == "ASSENT_INVALID":
        return assent_invalid
    return commit_failed


def assent_failure_reason(commit_result: Any) -> str:
    """Map a CommitBoundary reason code onto an AssentRecord failure reason."""
    reason_code = getattr(commit_result, "reason_code", None)
    if reason_code == "PLAN_STATE_DRIFT":
        return "drift_invalid"
    if reason_code == "ASSENT_INVALID":
        return "assent_invalid"
    return "chain_aborted"


def commit_error(commit_result: Any) -> dict[str, Any]:
    """The structured commit error carried onto the AssentRecord row."""
    output = getattr(commit_result, "output", None)
    error = output.get("error") if isinstance(output, dict) else None
    return {
        "type": getattr(commit_result, "reason_code", None),
        "detail": error if isinstance(error, dict) else None,
    }


# --------------------------------------------------------------------------- #
# Host-generated recovery tokens
# --------------------------------------------------------------------------- #
# A host mutation that ships its own inverse hands back ONE closed recovery
# token on the forward apply. Bridge persists it byte-for-byte and hands it
# straight back to the host's recovery counterpart — it never reconstructs the
# token or computes any index inside it. #235/#237 (split restore) is the first
# consumer; #241 (temporal transaction restore) is the second. The token BODIES
# differ per host mutation, so the per-key expectations are parameters, not
# assumptions baked in here.
def is_valid_recovery_token(
    recovery: Any,
    sequence_name: Optional[str],
    *,
    schema_version: int = 1,
    kind: Optional[str] = None,
    truthy_keys: tuple[str, ...] = ("method",),
    required_keys: tuple[str, ...] = (),
) -> bool:
    """Is this exactly one valid recovery token for this sequence?

    ``kind`` is only checked when supplied — #235's shipped split token carries
    no ``kind`` field, so requiring one would reject live tokens.
    """
    if not isinstance(recovery, dict):
        return False
    if kind is not None and recovery.get("kind") != kind:
        return False
    if recovery.get("schema_version") != schema_version:
        return False
    for key in truthy_keys:
        if not recovery.get(key):
            return False
    if recovery.get("sequence_name") != sequence_name:
        return False
    for key in required_keys:
        if key not in recovery:
            return False
    return True


def extract_recovery_token(
    outcome: Mapping[str, Any],
    sequence_name: Optional[str],
    **checks: Any,
) -> Optional[dict[str, Any]]:
    """Pull the single closed recovery token out of a forward apply result.

    Returns ``None`` (never raises) if the shape is not exactly one valid token
    for this sequence — a missing or malformed token never rewrites the forward
    apply's success, it only leaves the restore rail unavailable.
    """
    commit_result = outcome.get("commit_result")
    if not isinstance(commit_result, dict):
        return None
    apply_result = commit_result.get("apply_result")
    if not isinstance(apply_result, dict):
        return None
    results = apply_result.get("results")
    if not isinstance(results, list) or len(results) != 1:
        return None
    first = results[0]
    if not isinstance(first, dict):
        return None
    recovery = first.get("recovery")
    if not is_valid_recovery_token(recovery, sequence_name, **checks):
        return None
    return dict(recovery)


# --------------------------------------------------------------------------- #
# Small shared helpers
# --------------------------------------------------------------------------- #
def is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def workflow_identifier(prefix: str, fingerprint: str) -> str:
    """Stable, path-free identifier derived from a proposal fingerprint."""
    return f"{prefix}{fingerprint[:16]}"


def sanitize(message: str) -> str:
    """Path-free: never leak filesystem paths in a typed error message."""
    return " ".join(part for part in str(message).split() if "/" not in part)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


__all__ = [
    "BuildReceipt",
    "InMemoryWorkflowStore",
    "ProposalTransitionGuard",
    "ReceiptFieldSetError",
    "SessionFactoryWorkflowStore",
    "WorkflowStore",
    "apply_failure_reason",
    "assent_failure_reason",
    "canonical_fingerprint",
    "commit_error",
    "extract_recovery_token",
    "finalize_receipt",
    "fingerprint_refusal",
    "held_manifest_from_record",
    "is_sha256",
    "is_valid_recovery_token",
    "maybe_await",
    "refuse",
    "sanitize",
    "utc_now_iso",
    "workflow_identifier",
]
