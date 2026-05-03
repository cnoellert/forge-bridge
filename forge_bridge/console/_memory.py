"""PR26 — Deterministic argument memory (session context).

Process-scoped key-value store for previously resolved tool parameters
(today: ``project_id``). The chat handler's forced-execution path
consults this store *before* running PR25's deterministic resolvers, so
a follow-up request like "fetch versions" can reuse a ``project_id``
that an earlier "list projects" call already established — no
``forge_list_projects`` round-trip, no LLM involvement.

Scope: single-tenant by design. forge-bridge is local-first today, so a
process-global ``_MEMORY`` is appropriate. When SEED-AUTH-V1.5 ships and
multi-user becomes real, this swaps to per-session storage keyed by
caller identity; the public ``ToolMemory`` interface is shaped for that
migration.

Hard constraints (mirror ``_tool_chain``):
  1. **No guessing.** Memory is only ever READ in the resolution path.
     Writes happen exclusively from PR25's deterministic resolver
     success path — never user input, never on error.
  2. **No silent overwrite.** ``set`` does overwrite, but it is only
     called from the deterministic-resolution code path, so every write
     reflects a fresh authoritative value.
  3. **No hidden behavior.** The store is a flat dict; ``get`` and
     ``set`` are direct, observable, and trivially testable.
  4. **Fail closed.** Empty/missing/falsy values are not stored.
     ``get`` returns ``None`` on miss; callers must fall back to the
     PR25 resolver path.
  5. **Key-scoped.** Today: ``project_id`` only. New keys must be added
     to the chain registry's ``requires`` set in ``_tool_chain.py``;
     this module remains a generic key-value store.

Stale memory has no auto-invalidation: if a cached ``project_id`` is
later deleted, the next forced call uses the stale id and the
downstream tool fails with a backend error. This is intentional for v1
— validating memory before every use would defeat the determinism
contract by re-introducing the probe call we cached to avoid. Future
work (when needed): TTL or explicit invalidation on observed failure.
"""
from __future__ import annotations

from typing import Optional


class ToolMemory:
    """Flat string-keyed string store. Atomic single-process semantics
    — Python dict ops are GIL-protected, no locks required for the
    single-tenant local deployment model.

    Empty/falsy values are rejected by ``set`` to keep the contract
    simple: a stored value is always a non-empty string a caller can
    use directly. ``get`` returns ``None`` for both "never set" and
    "rejected on set" cases, which is the same fall-through callers
    need anyway.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
        """Return the stored value for ``key``, or ``None`` if absent."""
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        """Store a non-empty string value. Empty/falsy values are
        silently dropped — the caller's deterministic-resolution
        contract guarantees only valid values reach this method, but
        the guard is defensive against future misuse."""
        if value:
            self._store[key] = value

    def clear(self) -> None:
        """Drop all stored values. Reserved for test isolation —
        production callers should never invalidate memory wholesale.
        Per-key invalidation isn't exposed because no production code
        path needs it today (stale-memory failure mode documented in
        the module docstring)."""
        self._store.clear()


# Process-global instance. Module-level import-time construction means
# the store survives across HTTP requests within a single server
# process and resets cleanly when the process is restarted.
_MEMORY = ToolMemory()
