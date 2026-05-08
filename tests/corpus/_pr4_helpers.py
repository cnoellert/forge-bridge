"""Shared helpers for PR 4 tests.

Ships the ``capture_state_cycling`` fixture, a ``CaptureState``
type alias, and a narrow ``Path.open`` failure-injection helper
scoped to the corpus directory.

Per ``A.5.3.2-PR4-FRAMING.md`` §1.2 and ``A.5.3.2-PR4-SPEC.md`` §5,
the architectural concern PR 4 introduces (capture-call-site state
coupling — arbitration invariance under all capture states) deserves
explicit fixture vocabulary. Stretching the existing chat-handler
fixtures to absorb capture-state cycling was rejected at the spec
layer; this module is where the new vocabulary lives.

Four cycling states, each exercising a distinct property:

  - ``disabled``   : zero-capture path; pre-PR-4 baseline.
  - ``enabled``    : successful-capture happy path.
  - ``failing``    : I-6 failure-invisibility at integration level.
  - ``recovering`` : transition between failure and success;
                     no inter-call state retention.

The fixture is parametrized via ``request.param``. Tests opt in
with ``indirect=True`` parametrization on the fixture name itself
(``capture_state_cycling``), routing each parameter through the
fixture rather than passing it as a raw argument.

Adding more states (e.g., ``permission_denied``, ``partial_write``,
``disk_full``) would duplicate PR 3's I-6 unit-level coverage at
the integration level without adding new architectural invariants.
Removing any of the four loses a distinct property. The fixture
is closed for extension at the spec layer; growth requires spec
amendment.
"""
from __future__ import annotations

import pathlib
from collections.abc import Iterator
from pathlib import Path
from typing import Callable, Literal

import pytest


CaptureState = Literal["disabled", "enabled", "failing", "recovering"]


_ALL_STATES: tuple[CaptureState, ...] = (
    "disabled", "enabled", "failing", "recovering",
)


def _scoped_failing_open(
    real_open: Callable[..., object],
    corpus_dir: Path,
    fail_until_call: int | None = None,
) -> Callable[..., object]:
    """Wrap ``Path.open`` to raise ``OSError`` on calls inside the
    corpus directory and pass through every other call.

    ``fail_until_call=None``: every corpus-scoped call fails.
    ``fail_until_call=N``  : the first N corpus-scoped calls fail,
                             subsequent calls succeed. Used by the
                             ``recovering`` state to verify that no
                             inter-call state is retained between
                             writes.

    Calls outside the corpus directory (pytest internals, log files,
    user code under tmp_path siblings) MUST pass through unchanged —
    a global ``Path.open`` mock would break the test harness.

    Path-boundary check uses ``Path.is_relative_to`` rather than
    ``str.startswith`` because the latter encodes path-boundary
    semantics into string-prefix semantics, failing on sibling
    directories that share a name prefix (e.g., ``/tmp/corpus`` vs.
    ``/tmp/corpus_backup``). This helper defines what counts as
    corpus adjacency — an architectural boundary, not a convenience
    predicate.
    """
    call_count = [0]

    def wrapper(self: Path, *args: object, **kwargs: object) -> object:
        if self.is_relative_to(corpus_dir):
            call_count[0] += 1
            if fail_until_call is None or call_count[0] <= fail_until_call:
                raise OSError(
                    f"simulated capture write failure (corpus-scoped "
                    f"call #{call_count[0]})"
                )
        return real_open(self, *args, **kwargs)

    return wrapper


@pytest.fixture
def capture_state_cycling(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[CaptureState]:
    """Configure the capture environment per the parametrized state.

    Tests that exercise arbitration invariance under capture states
    request this fixture with ``indirect=True`` parametrization::

        @pytest.mark.parametrize(
            "capture_state_cycling",
            ["disabled", "enabled", "failing", "recovering"],
            indirect=True,
        )
        def test_arbitration_invariant(capture_state_cycling):
            state = capture_state_cycling
            # ... drive a chat request, assert envelope-identity ...

    Per ``A.5.3.2-PR4-FRAMING.md`` §1.2, this fixture is binding for
    every test that asserts arbitration invariance. Older
    chat-handler fixtures answer different questions; conflating them
    here would obscure which assertion is protecting which property.

    The corpus directory is always pinned to a tmp_path child, even
    in ``disabled`` state where the gate short-circuits before any
    directory access — defensive isolation against future regressions
    where something might accidentally read the corpus dir when
    disabled.
    """
    state: CaptureState = request.param
    if state not in _ALL_STATES:
        raise ValueError(
            f"capture_state_cycling: unknown state {state!r}; "
            f"expected one of {list(_ALL_STATES)}"
        )

    corpus_dir = tmp_path / "corpus"
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(corpus_dir))

    if state == "disabled":
        # Env var unset; gate returns False; emit_divergence_capture
        # short-circuits before touching the corpus dir.
        monkeypatch.delenv(
            "FORGE_BRIDGE_DIVERGENCE_CAPTURE", raising=False,
        )
    else:
        # All non-disabled states route through divergence_capture_enabled() == True.
        monkeypatch.setenv("FORGE_BRIDGE_DIVERGENCE_CAPTURE", "1")

    if state == "failing":
        real_open = pathlib.Path.open
        monkeypatch.setattr(
            pathlib.Path,
            "open",
            _scoped_failing_open(real_open, corpus_dir),
        )
    elif state == "recovering":
        # Tests using this state must assert recovery across separate
        # arbitration invocations, not merely successive Path.open calls
        # within one invocation. The fixture mechanism is temporal
        # call-level failure transition; the spec §5.3 protected property
        # is inter-emission state independence. These coincide because
        # _capture.py makes one Path.open per emission (verified at
        # PR 4 step 4 commit time); future writer changes that break
        # this property require the fixture to be re-evaluated.
        real_open = pathlib.Path.open
        monkeypatch.setattr(
            pathlib.Path,
            "open",
            _scoped_failing_open(
                real_open, corpus_dir, fail_until_call=1,
            ),
        )

    yield state
