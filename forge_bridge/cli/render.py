"""Rich rendering helpers for forge-bridge console CLI.

Single home for the artist-UX choices ported from Phase 10.1 D-40/D-41:
  - rich.box.SQUARE for tables
  - bold yellow header style (amber-ish on most terminals)
  - status chip color map: active/ok green, loaded dim cyan,
    degraded/warn yellow, fail red, absent dim
  - 8-char hash truncation on lists, full hash on drilldowns
  - "Created ▼" sort-affordance glyph (Phase 10.1 HUMAN-UAT #2 lesson)

No subcommand re-implements rendering primitives — they all import from here.
"""
from __future__ import annotations

from typing import Optional

from rich import box
from rich.console import Console
from rich.text import Text

# Locked Phase 11 visual contract (CONTEXT.md Area 3)
TOOLS_BOX = box.SQUARE
HEADER_STYLE = "bold yellow"

# Status chip color map — green/cyan/amber/red/dim
_STATUS_STYLES: dict[str, str] = {
    "active": "green",
    "ok": "green",
    "loaded": "dim cyan",
    "degraded": "yellow",
    "warn": "yellow",
    "fail": "red",
    "absent-when-required": "red",
    "absent": "dim",
}
_DEFAULT_STATUS_STYLE = "white"

# Column header glyph — Phase 10.1 HUMAN-UAT #2 default-sort affordance.
SORT_DESC_GLYPH = "▼"


def make_console(no_color: bool = False, stderr: bool = False) -> Console:
    """Construct a Rich Console honoring --no-color flag and NO_COLOR/FORCE_COLOR env.

    Rich's Console.__init__ already reads NO_COLOR/FORCE_COLOR from os.environ
    — we only need to pass through the explicit --no-color flag.
    """
    return Console(no_color=no_color, stderr=stderr)


def status_chip(status: str) -> Text:
    """Render a status keyword as a Rich Text object styled per the chip map."""
    style = _STATUS_STYLES.get(status, _DEFAULT_STATUS_STYLE)
    return Text(status, style=style)


def short_hash(code_hash: Optional[str], width: int = 8) -> str:
    """Truncate a hash for list views (default 8 chars per CONTEXT.md Area 3)."""
    if not code_hash:
        return ""
    return code_hash[:width]


def format_timestamp(ts: Optional[str]) -> str:
    """Render an ISO 8601 timestamp for table cells.

    Phase 11 default: pass through the API's ISO 8601 string. Humanized
    timestamps ("2h ago") are explicitly deferred (CONTEXT.md `<deferred>`).
    Returns "" for missing values rather than "None".
    """
    if not ts:
        return ""
    return ts


def created_column_header() -> str:
    """Default `Created ▼` header text — Phase 10.1 HUMAN-UAT #2 sort affordance."""
    return f"Created {SORT_DESC_GLYPH}"
