"""Phase 24.2 regression: utility.ping echoes bridge_url on the failure path.

Pre-Phase-24.2, the failure-path body returned ``{"connected": False, "error": ...}``
with no ``bridge_url`` field. Phase 24.2's daemon-routed doctor probe compares
the daemon-effective ``bridge_url`` against doctor's re-derived
``config.flame_bridge_url()`` to detect config-context divergence — but with no
``bridge_url`` in the failure body, doctor couldn't perform the comparison and
fell through to FAIL-daemon-says-broken with a misleading fix line ("start
Flame...") instead of WARN-divergent with the operator-action-bearing env-file
fix recipe.

The portofino canonical-probe re-fire on 2026-05-15 surfaced this gap: env file
shipped ``FORGE_BRIDGE_PORT=9998`` (the state_ws port) → daemon's
``bridge.BRIDGE_URL`` resolved to ``:9998`` → ``flame_ping`` failed with
"Bridge communication error: Server disconnected without sending a response" →
doctor mis-classified as FAIL-daemon-says-broken. With the failure-path echo,
doctor receives the daemon's bridge_url even when dispatch fails, surfaces the
divergence as WARN, and renders the correct operator-action fix line.

See:
  - .planning/milestones/v1.6-PHASE-24-2-FRAMING.md §6.4 (Q4 4-state taxonomy)
  - ~/.forge-bridge/measurements/2026-05-15-phase-24-2-rerun/README.md
"""
from __future__ import annotations

import json
from unittest.mock import patch, AsyncMock

import pytest


async def test_ping_failure_path_echoes_bridge_url():
    """When bridge.execute_json raises BridgeConnectionError, the returned
    JSON body MUST include the daemon's effective bridge.BRIDGE_URL so the
    Phase 24.2 doctor probe can detect config-context divergence even when
    dispatch fails."""
    from forge_bridge import bridge
    from forge_bridge.tools import utility

    expected_url = "http://127.0.0.1:9998"  # simulated misconfig — Flame at 9999
    with patch.object(bridge, "BRIDGE_URL", expected_url), \
         patch.object(
             bridge, "execute_json",
             new=AsyncMock(side_effect=bridge.BridgeConnectionError(
                 "Bridge communication error: Server disconnected without sending a response."
             )),
         ):
        raw = await utility.ping()

    body = json.loads(raw)
    assert body["connected"] is False
    assert "error" in body
    assert "Server disconnected" in body["error"]
    # Phase 24.2 design-gap fix: bridge_url MUST be present on failure path.
    assert body.get("bridge_url") == expected_url, (
        "utility.ping failure-path body must echo bridge.BRIDGE_URL so Phase 24.2 "
        "doctor can detect daemon vs shell config-context divergence under "
        "dispatch-failed conditions. See "
        "~/.forge-bridge/measurements/2026-05-15-phase-24-2-rerun/."
    )


async def test_ping_success_path_still_echoes_bridge_url():
    """Existing behavior: the success path already includes bridge_url in the
    body it builds via bridge.execute_json's snippet. Verify this didn't
    regress when adding the failure-path echo."""
    from forge_bridge import bridge
    from forge_bridge.tools import utility

    expected_url = "http://127.0.0.1:9999"
    # Simulate a successful execute_json — return the dict that flame_ping's
    # snippet would have produced when run inside Flame.
    fake_result = {
        "connected": True,
        "version": "2026.2.2",
        "project": "test_project",
        "current_tab": "Conform",
        "bridge_url": expected_url,
    }
    with patch.object(bridge, "BRIDGE_URL", expected_url), \
         patch.object(bridge, "execute_json", new=AsyncMock(return_value=fake_result)):
        raw = await utility.ping()

    body = json.loads(raw)
    assert body["connected"] is True
    assert body["bridge_url"] == expected_url
    assert body["version"] == "2026.2.2"


async def test_ping_failure_path_bridge_url_reflects_current_bridge_module_state():
    """The failure-path body's bridge_url must be read at call time (not
    cached) — it always reflects the daemon's current bridge.BRIDGE_URL, even
    if the daemon's effective URL changes between calls."""
    from forge_bridge import bridge
    from forge_bridge.tools import utility

    for url in ("http://127.0.0.1:9998", "http://other-host:9999"):
        with patch.object(bridge, "BRIDGE_URL", url), \
             patch.object(
                 bridge, "execute_json",
                 new=AsyncMock(side_effect=bridge.BridgeConnectionError("boom")),
             ):
            raw = await utility.ping()
        body = json.loads(raw)
        assert body["bridge_url"] == url, (
            f"failure-path bridge_url must equal current bridge.BRIDGE_URL "
            f"({url}); got {body.get('bridge_url')!r}"
        )
