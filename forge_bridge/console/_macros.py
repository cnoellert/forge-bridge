"""PR33 — User-defined macros that expand into PR30-compatible chains.

Macros are pure string substitution before ``parse_chain``. Execution,
resolver, memory, and PR31/PR32 behavior are unchanged.

The registry is in-memory only — no persistence across process restarts
unless something calls ``register_macro`` at startup.
"""
from __future__ import annotations

from typing import Dict, Optional

_MACROS: Dict[str, str] = {}


def register_macro(name: str, chain: str) -> None:
    if isinstance(name, str) and isinstance(chain, str):
        name = name.strip()
        chain = chain.strip()
        if name and chain:
            _MACROS[name] = chain


def get_macro(name: str) -> Optional[str]:
    if not isinstance(name, str):
        return None
    return _MACROS.get(name.strip())


def expand_macro(message: str) -> str:
    """Expand a macro at the start of the message.

    Supported forms:

      ``run <macro_name> [rest]``
      ``<macro_name> [rest]``

    Behavior:

      - Expands only once (no recursion).
      - Only expands if the macro name is the first token (after strip),
        or ``run`` followed by the macro name as the second token.
      - Appends remaining tokens to the expanded chain.
      - Returns the original message if no macro match.
    """
    if not isinstance(message, str):
        return message

    msg = message.strip()
    if not msg:
        return message

    tokens = msg.split()
    if not tokens:
        return message

    # Case 1: run <macro>
    if tokens[0] == "run" and len(tokens) >= 2:
        macro_name = tokens[1]
        rest = " ".join(tokens[2:])
        chain = get_macro(macro_name)
        if chain:
            return f"{chain} {rest}".strip()
        return message

    # Case 2: <macro>
    macro_name = tokens[0]
    rest = " ".join(tokens[1:])
    chain = get_macro(macro_name)
    if chain:
        return f"{chain} {rest}".strip()

    return message


def _clear_macros_for_tests() -> None:
    """Reset macro registry — tests/console autouse fixture only."""
    _MACROS.clear()
