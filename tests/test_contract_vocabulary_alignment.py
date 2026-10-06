"""No-drift invariant: bridge's built-in role/edge vocabulary stays aligned with
the shared forge-contracts vocabulary (Cycle-1 seam freeze, #5 + #4a).

The contract (forge_contracts.vocabulary, v0.2) owns the NAMES + CLASSES; bridge
keeps the operational enrichment (order, generation_floor, Flame L0x aliases).
These tests fail if the two ever silently diverge — e.g. a built-in role added to
bridge without updating the contract, or a frozen edge noun dropped from bridge.

Two directions, deliberately different:
  - Roles: bridge built-ins == contract known sets (the contract froze ALL 14
    built-in roles).
  - Relationship types: contract ⊆ bridge built-ins (the contract froze a
    deliberate 4-noun subset; bridge legitimately also ships references/peer_of/
    consumes, which are not yet contracted).

Open-registry discipline is preserved: only BUILT-INS are constrained; runtime
register() of off-list roles/edges stays allowed (the live `role: plate` row must
not become a contract violation). Validate role_class, never membership.
"""

from forge_contracts.vocabulary import (
    KNOWN_DELIVERABLE_TYPES,
    KNOWN_MEDIA_ROLES,
    KNOWN_RELATIONSHIP_TYPES,
    KNOWN_ROLE_CLASSES,
    KNOWN_TRACK_ROLES,
    ROLE_CLASS_MEDIA,
    ROLE_CLASS_TRACK,
)

from forge_contracts import (
    ASSET_TYPE_FITTED_MODEL,
    KNOWN_ASSET_TYPES,
    KNOWN_CAPACITY_KINDS,
    KNOWN_RESOURCE_KINDS,
    KNOWN_RESPONSIBILITY_PARTIES,
    KNOWN_SCHEDULING_KINDS,
    KNOWN_TASK_SOURCINGS,
    KNOWN_TASK_STATES,
    TASK_STATE_COMPLETE,
)

from forge_bridge.core.registry import Registry
from forge_bridge.core.vocabulary import STANDARD_ROLES, Role, Status
from forge_bridge.store.fitted_model_lifecycle_repo import FITTED_MODEL_ASSET_TYPE
from forge_bridge.store.models import ENTITY_TYPES


def _builtin_role_names(role_class: str) -> set:
    return {
        name
        for name, role in STANDARD_ROLES.items()
        if role.aliases.get("role_class") == role_class
    }


# ── Roles: built-ins == contract known sets ──────────────────────────────────

def test_builtin_track_roles_match_contract():
    assert _builtin_role_names(ROLE_CLASS_TRACK) == set(KNOWN_TRACK_ROLES)


def test_builtin_media_roles_match_contract():
    assert _builtin_role_names(ROLE_CLASS_MEDIA) == set(KNOWN_MEDIA_ROLES)


def test_every_builtin_role_has_a_contract_role_class():
    """role_class is the CLOSED axis — every built-in role declares one, and it is
    one of the contract's known classes."""
    classes = {role.aliases.get("role_class") for role in STANDARD_ROLES.values()}
    assert None not in classes, "a built-in role is missing role_class"
    assert classes == set(KNOWN_ROLE_CLASSES)


# ── Relationship edges: contract ⊆ bridge built-ins ──────────────────────────

def test_contract_relationship_types_are_bridge_builtins():
    reg = Registry()  # seeds built-in relationship types
    for name in KNOWN_RELATIONSHIP_TYPES:
        assert reg.relationships.exists(name), (
            f"contracted relationship noun {name!r} is not a bridge built-in"
        )


# ── Open registry preserved (membership is NOT a closed enum) ─────────────────

def test_offlist_role_still_registerable():
    """The contract publishes *known* roles, not an allow-list. An off-list role
    name (e.g. the live `plate`) must still register cleanly — membership stays
    open; only role_class is validated."""
    reg = Registry()
    reg.roles.register("plate", role=Role("plate", aliases={"role_class": ROLE_CLASS_MEDIA}))
    assert reg.roles.get_by_name("plate").role.name == "plate"
    assert "plate" not in KNOWN_MEDIA_ROLES  # off-list, yet not a violation


# ── Deliverable types: contract owns the axis; bridge's ENTITY_TYPES is a superset ────────────
# (ADR-008 / FND-009 — the D-HOME convergence.) The deliverable-CLASSIFICATION axis {shot, asset}
# is PROMOTED into the contract; bridge keeps the full entity table (sequence/version/media/layer/
# stack + operational orch_* types) and its DB CHECK constraint. "Entity-identity is bridge-sacred;
# entity-classification is federation-shared." These guards fail if the shared subset and bridge's
# superset ever silently drift — the whole point of the promotion.

def test_deliverable_types_seed_is_shot_and_asset():
    """The promoted axis is exactly the version-owner deliverable subset (ADR-008 seed)."""
    assert set(KNOWN_DELIVERABLE_TYPES) == {"shot", "asset"}


def test_deliverable_types_are_a_subset_of_bridge_entity_types():
    """contract ⊆ bridge: every shared deliverable type is a valid bridge entity_type, so the
    shared subset stays a PROJECTION of bridge's private superset — never a fork."""
    assert set(KNOWN_DELIVERABLE_TYPES) <= set(ENTITY_TYPES)


def test_bridge_entity_types_remains_a_proper_superset():
    """Open-world preserved: bridge legitimately ships entity kinds beyond the deliverable axis
    (sequence/version/media/layer/stack + operational types) — they are NOT contract vocabulary,
    and the contract must never swallow bridge's full table."""
    assert set(ENTITY_TYPES) - set(KNOWN_DELIVERABLE_TYPES), "bridge superset collapsed to the axis"


# ── Scheduling vocabulary (forge-contracts v0.9 / ADR-012, #274 slice 0) ──────────────────────
# Task state stays DISTINCT from entity Status, but every task state shares a Status spelling
# except `complete`, which Status.from_string aliases to `delivered`. Contracts tests this against
# a literal copy of Status (it cannot import bridge); this is the reverse guard against the real
# enum — same pattern as the ADR-008 deliverable-type guard above.

def test_task_states_map_onto_status():
    values = {s.value for s in Status}
    assert KNOWN_TASK_STATES - {TASK_STATE_COMPLETE} <= values
    assert Status.from_string(TASK_STATE_COMPLETE) is Status.DELIVERED


def test_closed_scheduling_sets_are_frozensets():
    """The three CLOSED sets are the only scheduling sets bridge may validate against; they must
    import from the top-level package and be immutable."""
    for closed in (KNOWN_TASK_SOURCINGS, KNOWN_RESPONSIBILITY_PARTIES, KNOWN_CAPACITY_KINDS):
        assert isinstance(closed, frozenset)
        assert closed


def test_asset_is_not_a_scheduling_or_resource_kind():
    """ADR-007 collision guard: `asset` is a deliverable entity type, never a scheduling record
    kind nor a bookable resource kind."""
    assert "asset" not in KNOWN_SCHEDULING_KINDS
    assert "asset" not in KNOWN_RESOURCE_KINDS


# ── Asset types (forge-contracts v0.10 / ADR-013, #279) ──────────────────────────────────────
# #160 stored fitted models under the free-text asset_type `fitted-model`; v0.10 promoted that
# value into the contract. Bridge's constant is now bound to the contract — this guard keeps the
# stored value and the contract from drifting apart (same pattern as the ADR-008 guard above).

def test_fitted_model_asset_type_is_the_contract_value():
    assert FITTED_MODEL_ASSET_TYPE == ASSET_TYPE_FITTED_MODEL == "fitted-model"
    assert ASSET_TYPE_FITTED_MODEL in KNOWN_ASSET_TYPES
