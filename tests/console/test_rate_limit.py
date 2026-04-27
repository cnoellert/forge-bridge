"""Unit tests for forge_bridge/console/_rate_limit.py (CHAT-01 / D-13).

All time-dependent tests use monkeypatch on time.monotonic to keep the suite
deterministic and fast (<1s total). Real time.sleep is NOT used.
"""
from __future__ import annotations

import dataclasses
import pytest

from forge_bridge.console import _rate_limit
from forge_bridge.console._rate_limit import (
    RateLimitDecision, check_rate_limit, _reset_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_state():
    """Every test starts with empty bucket state."""
    _reset_for_tests()
    yield
    _reset_for_tests()


class TestRateLimitDecision:
    def test_decision_is_frozen(self):
        d = RateLimitDecision(allowed=True, retry_after=0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            d.allowed = False  # type: ignore[misc]

    def test_decision_fields(self):
        d = RateLimitDecision(allowed=False, retry_after=42)
        assert d.allowed is False
        assert d.retry_after == 42


class TestCheckRateLimit:
    def test_first_request_allowed(self):
        d = check_rate_limit("1.2.3.4")
        assert d.allowed is True
        assert d.retry_after == 0

    def test_eleventh_request_blocked(self):
        """D-13: capacity=10, so the 11th rapid request returns allowed=False."""
        for i in range(10):
            d = check_rate_limit("1.2.3.4")
            assert d.allowed is True, f"request {i+1} unexpectedly blocked"
        d = check_rate_limit("1.2.3.4")
        assert d.allowed is False
        assert d.retry_after >= 1

    def test_distinct_ips_have_independent_buckets(self):
        """Two clients each get full 10-token capacity — no cross-IP throttle."""
        for _ in range(10):
            assert check_rate_limit("1.2.3.4").allowed is True
        # IP 1.2.3.4 is now empty; IP 5.6.7.8 must still have full capacity
        for _ in range(10):
            assert check_rate_limit("5.6.7.8").allowed is True
        # And both are now empty
        assert check_rate_limit("1.2.3.4").allowed is False
        assert check_rate_limit("5.6.7.8").allowed is False

    def test_refill_after_60s(self, monkeypatch):
        """After 60 s of inactivity, the bucket refills to capacity."""
        clock = {"now": 1000.0}
        monkeypatch.setattr(_rate_limit.time, "monotonic", lambda: clock["now"])

        # Drain the bucket
        for _ in range(10):
            check_rate_limit("1.2.3.4")
        assert check_rate_limit("1.2.3.4").allowed is False

        # Advance 60 s — bucket should refill enough for 10 more
        clock["now"] += 60.0
        for _ in range(10):
            d = check_rate_limit("1.2.3.4")
            assert d.allowed is True

    def test_partial_refill_proportional(self, monkeypatch):
        """30 s after draining → ~5 tokens (refill_rate = 10/60 = 0.1666 tok/s)."""
        clock = {"now": 1000.0}
        monkeypatch.setattr(_rate_limit.time, "monotonic", lambda: clock["now"])

        for _ in range(10):
            check_rate_limit("1.2.3.4")
        # Drained. Wait 30 s.
        clock["now"] += 30.0
        # ~5 tokens should be available — assert at least 4 succeed in a row
        # (we don't assert exactly 5 because of float math + the int(...)
        # truncation; the contract is "approximately 50% refill at 50% time").
        successes = 0
        for _ in range(6):
            if check_rate_limit("1.2.3.4").allowed:
                successes += 1
            else:
                break
        assert 4 <= successes <= 5

    def test_stale_buckets_evicted_after_ttl(self, monkeypatch):
        """A bucket idle for >300 s is removed lazily on the next call."""
        clock = {"now": 1000.0}
        monkeypatch.setattr(_rate_limit.time, "monotonic", lambda: clock["now"])

        check_rate_limit("evictable-ip")
        assert "evictable-ip" in _rate_limit._buckets

        clock["now"] += 301.0
        # Trigger lazy sweep via a different IP
        check_rate_limit("trigger-ip")
        assert "evictable-ip" not in _rate_limit._buckets

    def test_unknown_ip_handled(self):
        """RESEARCH.md pitfall §3.1: when Starlette request.client is None,
        the chat handler passes 'unknown'. All such callers share one bucket;
        the function MUST NOT crash."""
        for _ in range(10):
            assert check_rate_limit("unknown").allowed is True
        assert check_rate_limit("unknown").allowed is False

    def test_reset_for_tests_clears_state(self):
        check_rate_limit("1.2.3.4")
        check_rate_limit("5.6.7.8")
        assert len(_rate_limit._buckets) == 2
        _reset_for_tests()
        assert len(_rate_limit._buckets) == 0
