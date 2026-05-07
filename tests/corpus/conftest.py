"""Shared fixtures for corpus tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def clean_warning_state():
    """Clear ``_warned_invalid_values`` so the test sees a fresh state.

    Tests that exercise the env-var gate's invalid-value warning
    behavior must request this fixture explicitly. Without it, prior
    tests in the same pytest process leave the set populated, and the
    "warns once per unique invalid value" assertion becomes order-
    dependent.

    Explicit-request rather than autouse: the dependency is visible
    at the test signature (a reader sees ``clean_warning_state`` in
    the parameter list and knows the test depends on this state),
    rather than hidden in module-level autouse magic.

    See the comment block on ``_warned_invalid_values`` in
    ``forge_bridge/corpus/_capture.py`` for the design rationale.
    """
    from forge_bridge.corpus._capture import _warned_invalid_values

    _warned_invalid_values.clear()
    yield
    # Post-yield clear keeps subsequent tests clean even if the test
    # body mutates the set further than expected.
    _warned_invalid_values.clear()


@pytest.fixture
def clean_identity_caches():
    """Reset lazy-cached identity hashes so the test sees a cold cache.

    Tests that exercise ``narrower_version_hash`` / ``daemon_git_sha``
    first-call vs. cached-call behavior must request this fixture
    explicitly. Without it, the first PR 2 test to run pre-warms the
    caches and subsequent first-call assertions become order-dependent.

    Same explicit-request pattern as ``clean_warning_state``; same
    rationale (the dependency is visible at the test signature).

    See the comment block on ``_narrower_hash_cache`` /
    ``_daemon_git_sha_cache`` in ``forge_bridge/corpus/_identity.py``
    for the design rationale.
    """
    from forge_bridge.corpus._identity import _reset_caches_for_tests

    _reset_caches_for_tests()
    yield
    _reset_caches_for_tests()


@pytest.fixture
def clean_flame_reachability_cache():
    """Clear the ``_tool_filter._cache`` so topology snapshots see a
    cold cache.

    Tests that exercise ``snapshot_topology`` against specific cache
    states (warm with reachable=True, warm with reachable=False, cold)
    must request this fixture so they're not contaminated by prior
    tests' probes.
    """
    from forge_bridge.console._tool_filter import _cache as _flame_cache

    _flame_cache.clear()
    yield
    _flame_cache.clear()
