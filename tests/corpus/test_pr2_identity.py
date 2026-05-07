"""PR 2 — identity-hash helpers tests.

Preserved invariants for PR 2 (verbatim from the user-supplied
review framing — carry into commit message under "preserved
invariants" and into this docstring):

  1. Descriptive, not evaluative.
     Capture: reachable/unreachable, configured/available,
              identity/version, routing state.
     Do not capture: healthy, preferred, recommended, fallback-worthy.
     Evaluative fields propagate semantic weight that belongs in
     Layer 2.

  2. Observational, not semantic.
     Identity hashes record state snapshots.
     Do not invent: compatibility grades, equivalence classes,
                    drift scoring.
     Those are derived judgments for Layer 2's classifier.

  3. No lazy runtime side effects.
     Topology and identity helpers must not:
       - initialize providers
       - warm clients
       - allocate transports
       - touch arbitration state
       - spawn background tasks
       - mutate caches into warm-state preparation
     Capture observes existing state; capture never causes state.
     Test this explicitly.

  4. Loud asymmetry preserved.
     Topology working without writes is correct.
     Identity working without replay is correct.
     The writer remains deferred to PR 3 specifically because the
     architectural pressure to fuse observation with persistence is
     highest at this moment.

This test module covers the three identity helpers
(``narrower_version_hash``, ``registered_tools_snapshot_hash``,
``daemon_git_sha``) against the four invariants. Topology coverage
lives in ``test_pr2_topology.py``.
"""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


# ── narrower_version_hash ──────────────────────────────────────────────────


def test_narrower_version_hash_returns_sha256_hex(clean_identity_caches):
    """Returns a 64-char lowercase hex string."""
    from forge_bridge.corpus._identity import narrower_version_hash

    h = narrower_version_hash()
    assert _HEX64.match(h), f"expected 64-char hex, got {h!r}"


def test_narrower_version_hash_is_stable_across_calls(clean_identity_caches):
    """Repeated calls return identical hash (cached after first call)."""
    from forge_bridge.corpus._identity import narrower_version_hash

    hashes = {narrower_version_hash() for _ in range(10)}
    assert len(hashes) == 1, f"expected 1 unique hash, got {hashes}"


def test_narrower_version_hash_first_call_reads_file_once(
    clean_identity_caches,
):
    """Invariant 3: cached after first call. Second through tenth
    calls do NOT re-read ``_tool_filter.py`` from disk."""
    from forge_bridge.corpus import _identity

    # Patch read_bytes on Path to count calls during the FIRST call.
    with patch.object(
        _identity.Path, "read_bytes", autospec=True,
        side_effect=lambda self: b"fake _tool_filter content",
    ) as read_bytes_mock:
        _identity.narrower_version_hash()
        first_call_count = read_bytes_mock.call_count
        assert first_call_count == 1, (
            f"first call should read file once, got {first_call_count}"
        )

        for _ in range(10):
            _identity.narrower_version_hash()

        assert read_bytes_mock.call_count == first_call_count, (
            "subsequent calls re-read the file; cache is not honored"
        )


# ── registered_tools_snapshot_hash ─────────────────────────────────────────


def _mk_tool(name: str, schema: dict | None = None) -> MagicMock:
    t = MagicMock()
    t.name = name
    t.inputSchema = schema if schema is not None else {"type": "object"}
    return t


def test_registered_tools_hash_returns_sha256_hex():
    from forge_bridge.corpus._identity import registered_tools_snapshot_hash

    h = registered_tools_snapshot_hash([_mk_tool("forge_list_staged")])
    assert _HEX64.match(h), f"expected 64-char hex, got {h!r}"


def test_registered_tools_hash_same_input_produces_same_hash():
    from forge_bridge.corpus._identity import registered_tools_snapshot_hash

    tools = [_mk_tool("a"), _mk_tool("b"), _mk_tool("c")]
    h1 = registered_tools_snapshot_hash(tools)
    h2 = registered_tools_snapshot_hash(tools)
    assert h1 == h2


def test_registered_tools_hash_order_independent():
    """Same set in different orders produces the same hash —
    sorted internally, see _NORMALIZATION_VERSION."""
    from forge_bridge.corpus._identity import registered_tools_snapshot_hash

    a = _mk_tool("a")
    b = _mk_tool("b")
    h_ab = registered_tools_snapshot_hash([a, b])
    h_ba = registered_tools_snapshot_hash([b, a])
    assert h_ab == h_ba


def test_registered_tools_hash_changes_when_name_changes():
    from forge_bridge.corpus._identity import registered_tools_snapshot_hash

    h1 = registered_tools_snapshot_hash([_mk_tool("forge_list_staged")])
    h2 = registered_tools_snapshot_hash([_mk_tool("forge_get_staged")])
    assert h1 != h2


def test_registered_tools_hash_changes_when_schema_changes():
    """Different argument schema → different hash. The 'arg-schema
    contract' is what the hash protects."""
    from forge_bridge.corpus._identity import registered_tools_snapshot_hash

    h1 = registered_tools_snapshot_hash([
        _mk_tool("foo", {"type": "object", "properties": {"x": {}}}),
    ])
    h2 = registered_tools_snapshot_hash([
        _mk_tool("foo", {"type": "object", "properties": {"y": {}}}),
    ])
    assert h1 != h2


def test_registered_tools_hash_handles_missing_schema_attribute():
    """Defensive: if a tool object has no inputSchema attribute,
    treat as empty schema rather than raising."""
    from forge_bridge.corpus._identity import registered_tools_snapshot_hash

    t = MagicMock(spec=["name"])
    t.name = "no_schema_tool"
    h = registered_tools_snapshot_hash([t])
    assert _HEX64.match(h)


def test_registered_tools_hash_does_not_include_description():
    """A description-only change should NOT change the hash. The
    contract is name + arg schema; descriptions are documentation."""
    from forge_bridge.corpus._identity import registered_tools_snapshot_hash

    t1 = _mk_tool("foo")
    t1.description = "old description"
    t2 = _mk_tool("foo")
    t2.description = "completely different description"
    assert registered_tools_snapshot_hash([t1]) == \
        registered_tools_snapshot_hash([t2])


# ── daemon_git_sha ─────────────────────────────────────────────────────────


def test_daemon_git_sha_returns_40_hex_or_non_git(clean_identity_caches):
    """In a git checkout, returns a 40-char hex SHA. Outside one
    (or on subprocess failure), returns the literal 'non-git'."""
    from forge_bridge.corpus._identity import daemon_git_sha

    sha = daemon_git_sha()
    assert sha == "non-git" or _HEX40.match(sha), (
        f"expected 40-char hex or 'non-git', got {sha!r}"
    )


def test_daemon_git_sha_is_stable_across_calls(clean_identity_caches):
    """Repeated calls return identical value (cached after first)."""
    from forge_bridge.corpus._identity import daemon_git_sha

    shas = {daemon_git_sha() for _ in range(10)}
    assert len(shas) == 1


def test_daemon_git_sha_first_call_runs_subprocess_once(
    clean_identity_caches,
):
    """Invariant 3: cached after first call. Subsequent calls do NOT
    re-invoke subprocess."""
    from forge_bridge.corpus import _identity

    with patch.object(
        _identity.subprocess, "run",
        return_value=MagicMock(
            returncode=0, stdout="a" * 40 + "\n", stderr="",
        ),
    ) as run_mock:
        _identity.daemon_git_sha()
        first_count = run_mock.call_count
        assert first_count == 1

        for _ in range(10):
            _identity.daemon_git_sha()
        assert run_mock.call_count == first_count, (
            "subsequent calls re-invoked subprocess; cache not honored"
        )


def test_daemon_git_sha_returns_non_git_on_subprocess_failure(
    clean_identity_caches,
):
    from forge_bridge.corpus import _identity

    with patch.object(
        _identity.subprocess, "run",
        return_value=MagicMock(returncode=128, stdout="", stderr="fatal"),
    ):
        assert _identity.daemon_git_sha() == "non-git"


def test_daemon_git_sha_returns_non_git_on_subprocess_exception(
    clean_identity_caches,
):
    """Any exception from subprocess (timeout, missing binary, etc.)
    results in 'non-git' rather than propagating."""
    from forge_bridge.corpus import _identity

    with patch.object(
        _identity.subprocess, "run",
        side_effect=FileNotFoundError("git not on PATH"),
    ):
        assert _identity.daemon_git_sha() == "non-git"


def test_daemon_git_sha_returns_non_git_on_malformed_output(
    clean_identity_caches,
):
    """Defensive: subprocess succeeds but output is not a 40-char
    hex SHA → 'non-git' rather than passing garbage forward."""
    from forge_bridge.corpus import _identity

    with patch.object(
        _identity.subprocess, "run",
        return_value=MagicMock(
            returncode=0, stdout="not-a-sha\n", stderr="",
        ),
    ):
        assert _identity.daemon_git_sha() == "non-git"


# ── Invariant 3 — no side effects beyond the lazy first-call I/O ──────────


def test_identity_helpers_do_not_open_network_connections(
    clean_identity_caches,
):
    """None of the three identity helpers should ever open a TCP
    connection, regardless of call count."""
    from forge_bridge.corpus._identity import (
        daemon_git_sha,
        narrower_version_hash,
        registered_tools_snapshot_hash,
    )

    with patch(
        "asyncio.open_connection",
        side_effect=AssertionError("identity helpers must not open conns"),
    ):
        for _ in range(10):
            narrower_version_hash()
            registered_tools_snapshot_hash([])
            daemon_git_sha()


def test_identity_helpers_do_not_initialize_providers(
    clean_identity_caches,
):
    """None of the three identity helpers should import or initialize
    any LLM provider client. Verified by patching the LLM router and
    asserting nothing in it is touched."""
    from forge_bridge.corpus._identity import (
        daemon_git_sha,
        narrower_version_hash,
        registered_tools_snapshot_hash,
    )

    # If any identity helper accidentally imported the router and called
    # acomplete / complete_with_tools, this would fire.
    with patch(
        "forge_bridge.llm.router.LLMRouter",
        side_effect=AssertionError(
            "identity helpers must not initialize the LLM router"
        ),
    ):
        for _ in range(10):
            narrower_version_hash()
            registered_tools_snapshot_hash([])
            daemon_git_sha()


def test_identity_helpers_idempotent_first_and_tenth_call(
    clean_identity_caches,
):
    """Per invariant 3 verbatim: 'the first and tenth invocation
    should be operationally indistinguishable except for returned
    data freshness'. For identity, freshness is irrelevant (the
    returned data is stable for cached helpers, deterministic for
    the pure helper)."""
    from forge_bridge.corpus._identity import (
        daemon_git_sha,
        narrower_version_hash,
        registered_tools_snapshot_hash,
    )

    h1 = narrower_version_hash()
    h10 = [narrower_version_hash() for _ in range(10)][-1]
    assert h1 == h10

    s1 = daemon_git_sha()
    s10 = [daemon_git_sha() for _ in range(10)][-1]
    assert s1 == s10

    tools = [_mk_tool("a"), _mk_tool("b")]
    r1 = registered_tools_snapshot_hash(tools)
    r10 = [registered_tools_snapshot_hash(tools) for _ in range(10)][-1]
    assert r1 == r10
