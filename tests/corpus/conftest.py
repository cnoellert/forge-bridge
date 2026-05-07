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
