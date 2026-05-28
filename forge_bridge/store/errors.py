"""Shared store-layer exceptions for Phase 4B operational repos."""


class LifecycleConsistencyError(Exception):
    """Raised when orchestration lifecycle paused↔block invariant would be violated."""

    def __init__(self, run_id, status: str, has_block: bool) -> None:
        self.run_id = run_id
        self.status = status
        self.has_block = has_block
        super().__init__(
            f"Lifecycle consistency violation for run {run_id}: "
            f"status={status!r} requires block "
            f"{'present' if status == 'paused' else 'absent'}, "
            f"has_block={has_block}"
        )


class MultipleActiveRunsError(Exception):
    """Raised when more than one active lifecycle row exists for one shot."""

    def __init__(self, shot_id, run_ids: list) -> None:
        self.shot_id = shot_id
        self.run_ids = run_ids
        super().__init__(
            f"Multiple active orchestration runs for shot {shot_id}: {run_ids}"
        )


class AppendOnlyLedgerError(Exception):
    """Raised when a caller attempts to mutate an append-only ledger row."""

    def __init__(self, table_name: str, operation: str) -> None:
        self.table_name = table_name
        self.operation = operation
        super().__init__(
            f"{operation}() is not supported on append-only table "
            f"{table_name!r}. Insert-only discipline applies."
        )
