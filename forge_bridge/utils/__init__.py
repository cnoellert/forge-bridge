"""
forge_bridge/utils/ — substrate normalization utilities.

This package holds pure data-transformation functions that convert
between Flame-native serialized representations and typed
substrate-native values consumed by graph-layer primitives.

Utilities here:
    - Have zero Flame runtime dependencies (pure functions)
    - Are fully unit-testable in isolation
    - Are called by tool implementations at output boundaries
    - Are NOT called by graph/, console/, or llm/ layers directly

Architectural rule (first stated here, formalized in typed port
API phase): Flame-native representations stay INSIDE tool
implementations. Substrate-native types cross OUTWARD through
these utilities.
"""
