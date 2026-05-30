"""Per-test logging capture helper for the test(B-K1) cluster.

Why this exists
---------------
pytest's `caplog` fixture relies on a `LogCaptureHandler` attached to the
root logger; the named loggers under test propagate to root, and caplog
collects from there. That contract is robust *unless* an earlier test in
the same process configures Python's logging via
`logging.config.dictConfig(...)` — which is exactly what uvicorn does when
the bridge's `STDERR_ONLY_LOGGING_CONFIG` is applied during
`_start_console_task`. `dictConfig` reconfigures handlers on the loggers
named in its `loggers:` block and, depending on the surrounding state,
can leave the root logger's previously-attached pytest handler stripped
or detached — so any caplog test running later in the same process
captures nothing and asserts on empty records.

The fix is local: each affected test attaches its OWN handler directly
to the named logger it cares about (e.g. `forge_bridge.learning.sanitize`)
instead of leaning on root-handler propagation that an earlier test
might have mutated. The test constrains exactly what it needs.

Usage
-----
    from tests._log_capture import capture_logger

    def test_foo(self):
        with capture_logger("forge_bridge.learning.sanitize") as records:
            do_thing_that_logs()
        assert any("expected substring" in r.message for r in records)

The yielded object is a plain `list[LogRecord]` populated by a small
recording handler attached for the duration of the context. The handler
sets the named logger's level to WARNING so messages reach the handler
even if a prior dictConfig raised the level. Original level + handlers
are restored on exit.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator


class _ListHandler(logging.Handler):
    """Append every emitted LogRecord into a list — no formatting, no I/O."""

    def __init__(self, sink: list[logging.LogRecord]) -> None:
        super().__init__(level=logging.NOTSET)
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self._sink.append(record)


@contextmanager
def capture_logger(
    logger_name: str, level: int = logging.WARNING
) -> Iterator[list[logging.LogRecord]]:
    """Attach a list-recording handler to `logger_name` for the with-block.

    Independent of root logger handler state — works even if an earlier
    test in the same process called `logging.config.dictConfig(...)` and
    stripped pytest's caplog handler from root.
    """
    logger = logging.getLogger(logger_name)
    records: list[logging.LogRecord] = []
    handler = _ListHandler(records)
    handler.setLevel(level)

    saved_level = logger.level
    saved_disabled = logger.disabled
    logger.setLevel(level)
    logger.disabled = False
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)
        logger.setLevel(saved_level)
        logger.disabled = saved_disabled
