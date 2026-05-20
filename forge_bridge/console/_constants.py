"""Shared console constants (PR37 — avoid coupling to handlers)."""

# Runaway guard only — NOT an architectural workflow limit.
# Graph primitives (filter, foreach, collect, if/then) make
# legitimate operator workflows naturally exceed early
# enumerate->mutate->format chain lengths.
#
# Real safety enforcement comes from:
#   - k-fold canonical recurrence termination
#   - execution timeout
#   - per-step structured failure propagation
#
# This guard exists only to catch pathological runaway chains.
CHAIN_MAX_STEPS = 50
