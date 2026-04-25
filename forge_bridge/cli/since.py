"""--since / --until parser for forge-bridge console execs (D-02).

Accepts a small relative grammar (Nm/Nh/Nd/Nw) AND ISO 8601 timestamps.
Emits an ISO 8601 UTC string for the API. Stdlib only — no new deps.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

_RELATIVE_RE = re.compile(r'^(\d+)(m|h|d|w)$')
_UNIT_SECONDS = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}


def parse_since(value: str) -> str:
    """Parse --since value into an ISO 8601 string for the API.

    Accepts:
      - Relative: "30m", "24h", "7d", "2w"
      - ISO 8601: "2026-04-24T10:00:00Z", "2026-04-24T10:00:00+00:00"

    Returns an ISO 8601 string. Raises ValueError on bad input.
    """
    m = _RELATIVE_RE.match(value)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        dt = datetime.now(timezone.utc) - timedelta(seconds=n * _UNIT_SECONDS[unit])
        return dt.isoformat()
    # Normalize Z suffix for Python 3.10 compatibility (project minimum is 3.10).
    normalized = value[:-1] + '+00:00' if value.endswith('Z') else value
    dt = datetime.fromisoformat(normalized)  # ValueError on bad input — propagate
    return dt.isoformat()
