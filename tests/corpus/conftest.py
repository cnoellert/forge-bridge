"""Shared fixtures for corpus tests."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _sync_console_package_attrs_with_sys_modules():
    """Defensive: re-sync ``forge_bridge.console.*`` package
    attributes with ``sys.modules`` entries at every test start.

    Background — PR 8 Step 4 6th amendment-at-incarnation:

    ``test_pr4_no_dependency`` uses ``importlib.import_module`` +
    ``monkeypatch.delitem(sys.modules, ...)`` to force-reload the
    handlers + chain-step modules. After the test's monkeypatch
    teardown, ``sys.modules`` is restored to the ORIGINAL module
    object, but the parent-package attributes (e.g.,
    ``forge_bridge.console.handlers``) were updated to the NEW
    module during the reload and are NOT restored — monkeypatch
    only tracks the ``sys.modules`` dictionary.

    This creates an asymmetry between two import resolution paths:

      - ``from forge_bridge.console.handlers import chat_handler``
        resolves via ``sys.modules`` → ORIGINAL module (restored).
      - ``import forge_bridge.console.handlers`` (and dotted-path
        attribute access used internally by ``monkeypatch.setattr``)
        resolves via parent-package attribute → NEW module
        (post-reload).

    The asymmetry causes ``monkeypatch.setattr("forge_bridge.
    console.handlers.chat_handler", sentinel)`` to patch the NEW
    module's ``chat_handler``, while production code's function-
    scoped ``from forge_bridge.console.handlers import
    chat_handler`` retrieves from the ORIGINAL module — the patch
    silently no-ops.

    This autouse fixture re-syncs the package attributes with
    ``sys.modules`` at every test start, ensuring both paths
    agree. It is a no-op when the state is already consistent
    (the normal case); it repairs the divergence after PR 4's
    reload-and-restore pattern.

    Affected production code: ``forge_bridge/corpus/_seed.py``'s
    ``_invoke_chat_handler_in_process`` uses a function-scoped
    ``from forge_bridge.console.handlers import chat_handler``
    import per carrier #15's effective-scope protection
    (A.5.3.2-PR8-SPEC.md §4.5.3 + §4.5.4). The function-scoped
    placement is structurally load-bearing; this fixture protects
    against the test-infrastructure asymmetry without forcing the
    production code to module-scope its import.

    Surfaced during PR 8 Step 4 verification (2026-05-11). The
    autouse fixture is the minimal fix at the test infrastructure
    layer; the production code is unchanged.
    """
    import sys

    import forge_bridge.console

    # Only re-sync modules that are loaded. If a module isn't in
    # sys.modules, the package attribute may not exist either —
    # nothing to sync.
    for submodule in ("handlers", "_step", "_engine", "_rate_limit"):
        qualified = f"forge_bridge.console.{submodule}"
        if qualified in sys.modules:
            setattr(forge_bridge.console, submodule, sys.modules[qualified])

    yield


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


@pytest.fixture
def clean_rate_limit_state():
    """Clear chat_handler's rate-limit state before and after.

    PR 8 driver-invoking tests (Step 4) exercise ``chat_handler``'s
    D-13 rate-limit pre-gate via ``drive_seed_fixture``. Without
    isolation, consecutive tests in the same pytest process
    accumulate rate-limit state across the synthetic per-invocation
    client identities (the cache key is ``client_ip``; each test
    uses a different synthetic id, but the ``_buckets`` cache
    itself persists across tests).

    The fixture invokes the handler's existing test affordance —
    ``forge_bridge.console._rate_limit._reset_for_tests()`` —
    on entry AND on exit, ensuring each driver-invoking test
    exercises a clean rate-limit surface.

    Implementation grounding (per A.5.3.2-PR8-SPEC.md §4.6): the
    rate-limit module already exposed a ``_-prefixed`` test
    affordance. Spec §4.6 named the architectural contract
    (entry+exit isolation against the actual handler-owned cache);
    Step 4 grounded the concrete reset surface
    (``_reset_for_tests`` rather than direct ``_buckets``
    manipulation). The spec-level contract binds; the
    implementation choice is the artifact of the grounding.

    Tests using this fixture: every PR 8 driver-invoking test
    (test_driver_does_not_invoke_chain_step,
    test_driver_emits_expectation_through_helper,
    test_driver_opens_scope_around_chat_handler,
    test_driver_invokes_chat_handler_in_process).
    """
    from forge_bridge.console._rate_limit import _reset_for_tests

    _reset_for_tests()
    yield
    _reset_for_tests()
