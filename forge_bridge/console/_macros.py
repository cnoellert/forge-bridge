"""PR33 / PR34 — User-defined macros that expand into PR30-compatible chains.

Macros are pure string substitution before ``parse_chain``. Execution,
resolver, memory, and PR31/PR32 behavior are unchanged.

Persistence (PR34): definitions are stored in a local JSON file (default
``~/.forge_macros.json``). Load happens at import; ``register_macro`` saves
best-effort (silent failure on IO errors). No locking or versioning.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

_MACRO_FILE = os.path.expanduser("~/.forge_macros.json")

_MACROS: Dict[str, str] = {}


def _load_macros() -> None:
    if not os.path.exists(_MACRO_FILE):
        return
    try:
        with open(_MACRO_FILE, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(k, str) and isinstance(v, str):
                        name = k.strip()
                        chain = v.strip()
                        if name and chain:
                            _MACROS[name] = chain
    except Exception:
        pass


def _save_macros() -> None:
    try:
        parent = os.path.dirname(_MACRO_FILE)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(_MACRO_FILE, "w", encoding="utf-8") as f:
            json.dump(_MACROS, f, indent=2)
    except Exception:
        pass


def register_macro(name: str, chain: str) -> None:
    if isinstance(name, str) and isinstance(chain, str):
        name = name.strip()
        chain = chain.strip()
        if name and chain:
            _MACROS[name] = chain
            _save_macros()


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


_load_macros()
