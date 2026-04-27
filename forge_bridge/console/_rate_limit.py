"""IP-keyed token-bucket rate limiter for /api/v1/chat (Phase 16 / FB-D, D-13).

Greenfield module — no existing in-process throttler in the repo. Reused
patterns: module-level state from console/read_api.py (canonical id tracking),
logger setup from console/handlers.py:45.

Design (D-13):
    capacity     = 10 tokens
    refill_rate  = 10 tokens / 60 s  (1 token every 6 s, sliding window)
    TTL          = 300 s (idle eviction, lazy on each call)
    lock         = threading.Lock (NOT asyncio.Lock — single-process v1.4
                   per STATE.md "single-bridge process per machine").

Public surface:
    check_rate_limit(client_ip: str) -> RateLimitDecision
    _reset_for_tests() -> None     # test affordance, _-prefixed

Migration path: when v1.5 auth lands (SEED-AUTH-V1.5), the bucket key
swaps from `client_ip` to `caller_id` — the rest of the surface is stable.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# D-13 numerical contract — pin in module constants for grep-ability.
_CAPACITY: float = 10.0
_REFILL_SECONDS: float = 60.0
_REFILL_RATE: float = _CAPACITY / _REFILL_SECONDS  # 0.1666... tokens/sec
_TTL_SECONDS: float = 300.0

# Module state: ip -> (tokens, last_seen_monotonic)
_buckets: dict[str, tuple[float, float]] = {}
_lock: threading.Lock = threading.Lock()


@dataclass(frozen=True)
class RateLimitDecision:
    """Outcome of a single rate-limit check.

    allowed:     True if the request consumed a token; False if blocked.
    retry_after: Seconds until at least one token will be available. >= 1
                 when allowed=False, 0 when allowed=True. Suitable for the
                 HTTP `Retry-After` header value (D-09 / D-13 contract).
    """
    allowed: bool
    retry_after: int


def check_rate_limit(client_ip: str) -> RateLimitDecision:
    """Consume one token for *client_ip*; return decision.

    First call for an IP starts the bucket at full capacity. Subsequent calls
    refill linearly since the last seen timestamp. The 11th call inside 60 s
    for the same IP returns allowed=False with retry_after populated to the
    nearest second (clamped to >=1 to avoid 0-second client retry storms).

    Stale buckets (no activity for TTL_SECONDS) are evicted lazily on every
    call to bound memory — bounded by call rate, no background sweeper needed.

    Args:
        client_ip: Remote IP string from request.client.host. May be "unknown"
            when Starlette's request.client is None (RESEARCH.md pitfall §3.1);
            all "unknown" callers share a single bucket — documented v1.4
            posture, resolved by SEED-AUTH-V1.5.

    Returns:
        RateLimitDecision(allowed, retry_after)
    """
    now = time.monotonic()
    with _lock:
        # Lazy TTL sweep — every call inspects all buckets. O(N_active_ips),
        # bounded by call rate, no background task needed.
        stale = [ip for ip, (_, last) in _buckets.items() if now - last > _TTL_SECONDS]
        for ip in stale:
            _buckets.pop(ip, None)

        tokens, last = _buckets.get(client_ip, (_CAPACITY, now))
        # Refill since last touch.
        tokens = min(_CAPACITY, tokens + (now - last) * _REFILL_RATE)
        if tokens >= 1.0:
            _buckets[client_ip] = (tokens - 1.0, now)
            return RateLimitDecision(allowed=True, retry_after=0)
        # Blocked — how long until at least 1 token is available?
        retry_after = max(1, int((1.0 - tokens) / _REFILL_RATE))
        _buckets[client_ip] = (tokens, now)
        return RateLimitDecision(allowed=False, retry_after=retry_after)


def _reset_for_tests() -> None:
    """Clear all bucket state — exclusively for unit tests, hence _-prefix.

    Production code MUST NOT call this; rate-limit invariants depend on
    monotonic continuity of bucket history.
    """
    with _lock:
        _buckets.clear()
