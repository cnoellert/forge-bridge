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
    KNOWN_MEDIA_ROLES,
    KNOWN_RELATIONSHIP_TYPES,
    KNOWN_ROLE_CLASSES,
    KNOWN_TRACK_ROLES,
    ROLE_CLASS_MEDIA,
    ROLE_CLASS_TRACK,
)

from forge_bridge.core.registry import Registry
from forge_bridge.core.vocabulary import STANDARD_ROLES, Role


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
