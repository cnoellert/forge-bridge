"""Fast-fail connect timeout for the native ollama.AsyncClient.

Lands SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+ via bridge #173: the client
returned by LLMRouter._get_local_native_client() must carry an explicit
httpx.Timeout with a short (5s) connect timeout so an unreachable Ollama host
fails fast instead of stalling on the ~75s macOS TCP connect default. The
read timeout stays at 120s (the LLM-loop wall-clock cap) so slow-but-responsive
models are unaffected.

These tests use the REAL ollama package (importorskip — no mock_ollama):
the fixture-mocked AsyncClient would accept any kwargs, so only the real
client proves the timeout survives the ollama -> httpx pass-through. No live
service is required: the fast-fail probe targets a loopback port with nothing
listening (the seed's own example host), which is hermetic — it needs the
ABSENCE of a server, not the presence of one.
"""
from __future__ import annotations

import time

import pytest

httpx = pytest.importorskip("httpx")
ollama = pytest.importorskip("ollama")

from forge_bridge.llm.router import LLMRouter

# Seed acceptance example: a deliberately-unreachable loopback endpoint.
_UNREACHABLE_URL = "http://127.0.0.1:65535/v1"


class TestConnectTimeoutConfig:
    def test_native_client_carries_short_connect_long_read_timeout(self):
        """The lazily-built client's underlying httpx timeout is explicit:
        connect=5.0 (fast-fail) while read stays >= 120s (LLM-loop cap)."""
        router = LLMRouter(local_url=_UNREACHABLE_URL)
        client = router._get_local_native_client()
        timeout = client._client.timeout  # underlying httpx.AsyncClient
        assert isinstance(timeout, httpx.Timeout)
        assert timeout.connect == 5.0
        assert timeout.read >= 120.0

    @pytest.mark.asyncio
    async def test_unreachable_host_fails_well_under_ten_seconds(self):
        """Seed acceptance: a request to an unreachable host surfaces an error
        in well under 10s (was ~75s at the OS default connect timeout)."""
        router = LLMRouter(local_url=_UNREACHABLE_URL)
        client = router._get_local_native_client()
        started = time.monotonic()
        with pytest.raises(Exception) as excinfo:
            await client.chat(
                model="qwen2.5-coder:14b",
                messages=[{"role": "user", "content": "ping"}],
            )
        elapsed = time.monotonic() - started
        assert elapsed < 10.0, f"fast-fail took {elapsed:.1f}s (expected < 10s)"
        # Must be a transport-level failure, not a model/API-level response.
        assert isinstance(
            excinfo.value, (httpx.ConnectError, httpx.ConnectTimeout, OSError)
        ), f"unexpected error type: {type(excinfo.value)!r}"
