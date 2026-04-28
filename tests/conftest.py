"""
Shared pytest fixtures for forge-bridge test suite.

Fixtures:
    monkeypatch_bridge  — patches forge_bridge.bridge.execute with a mock BridgeResponse
    mock_openai         — patches openai at module level to prevent import errors
    mock_anthropic      — patches anthropic at module level to prevent import errors
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge_bridge.bridge import BridgeResponse


@pytest.fixture
def monkeypatch_bridge(monkeypatch):
    """Patch forge_bridge.bridge.execute to return a predictable BridgeResponse.

    Usage:
        def test_something(monkeypatch_bridge):
            # bridge.execute is now a coroutine returning the mock response
            ...

    The fixture yields the mock so tests can reconfigure it:
        monkeypatch_bridge.result = '{"key": "value"}'
    """
    mock_response = BridgeResponse(
        stdout='{"result": "ok"}',
        stderr="",
        result="ok",
        error=None,
        traceback=None,
    )

    mock_execute = AsyncMock(return_value=mock_response)

    with patch("forge_bridge.bridge.execute", mock_execute):
        yield mock_execute


@pytest.fixture
def mock_openai():
    """Patch openai so tests run without the package installed.

    Provides a MagicMock at the openai module level. Individual tests
    can configure mock_openai.return_value as needed.
    """
    mock = MagicMock()
    with patch.dict("sys.modules", {"openai": mock, "openai.OpenAI": mock.OpenAI}):
        yield mock


@pytest.fixture
def mock_anthropic():
    """Patch anthropic so tests run without the package installed.

    Provides a MagicMock at the anthropic module level. Individual tests
    can configure mock_anthropic.return_value as needed.
    """
    mock = MagicMock()
    with patch.dict("sys.modules", {"anthropic": mock}):
        yield mock


# ============================================================
# Phase 11 fixtures — shared across all tests/test_cli_*.py files
# ============================================================

import socket as _phase11_socket  # noqa: E402 — alias to avoid collision with existing imports


@pytest.fixture
def free_port() -> int:
    """Return an available local port on 127.0.0.1.

    Source: extracted from tests/test_console_http_transport.py:_find_free_port.
    Used by every Phase 11 CLI integration test that boots a fixture server.
    """
    with _phase11_socket.socket(_phase11_socket.AF_INET, _phase11_socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ============================================================
# Phase 13 (FB-A) fixtures — async-DB session_factory for
# store-layer integration tests. Reusable by FB-B and beyond.
# ============================================================

import os as _phase13_os  # noqa: E402 — alias to avoid collision
import uuid as _phase13_uuid

import pytest_asyncio as _phase13_pytest_asyncio  # noqa: E402

from sqlalchemy import text as _phase13_text
from sqlalchemy.ext.asyncio import create_async_engine as _phase13_create_async_engine

from forge_bridge.store.models import Base as _phase13_Base
from forge_bridge.store.session import (
    get_async_session_factory as _phase13_get_async_session_factory,
)


def _phase13_admin_url() -> str:
    """Return an asyncpg URL pointing at the 'postgres' admin database.

    Used to CREATE / DROP per-test databases. Derived from FORGE_DB_URL or
    the default forge-bridge dev URL by replacing the database name.
    """
    url = _phase13_os.environ.get(
        "FORGE_DB_URL",
        "postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge",
    )
    # Swap the trailing /<db> for /postgres
    scheme_and_host, _slash, _db = url.rpartition("/")
    return f"{scheme_and_host}/postgres"


def _phase13_postgres_available() -> bool:
    """Probe whether the project's Postgres dev backend is reachable.

    Used at module-collect time so a missing database results in a clean
    skip rather than a noisy connection error stack. Matches the local-first
    project philosophy: tests pass on a developer's laptop without Postgres
    if they are running unrelated suites; they SKIP this file specifically.

    Honors FORGE_DB_URL host/port if set so the project's non-default port
    (7533 on dev, per the environment var FORGE_DB_URL) is probed instead of
    the SQL server default 5432 (which on dev hosts the Autodesk Flame DB,
    not forge_bridge).
    """
    import socket
    from urllib.parse import urlparse

    url = _phase13_os.environ.get("FORGE_DB_URL", "")
    if url:
        # urlparse needs a scheme without "+driver" to recognize the netloc cleanly.
        scheme, _, rest = url.partition("://")
        scheme = scheme.split("+", 1)[0] or "postgresql"
        parsed = urlparse(f"{scheme}://{rest}")
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
    else:
        host, port = "localhost", 5432

    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


@_phase13_pytest_asyncio.fixture
async def session_factory():
    """Yield an async_sessionmaker bound to a freshly-created per-test database.

    Behaviour:
      1. Create a unique database (forge_bridge_test_<uuid8>) on the same
         Postgres host as FORGE_DB_URL.
      2. Run Base.metadata.create_all against the new database — schemas
         are created from the SQLAlchemy ORM models (NOT via Alembic, so
         the fixture is independent of migration state). Plan 01's
         ENTITY_TYPES + EVENT_TYPES extensions and the auto-generated
         ck_entities_type CHECK constraint propagate via this path.
      3. Yield an async_sessionmaker. Tests use it as
         `async with session_factory() as session: ...`.
      4. Teardown: drop the per-test database.

    Skipped if Postgres at localhost:5432 is unreachable.
    """
    if not _phase13_postgres_available():
        import pytest
        pytest.skip("Postgres at localhost:5432 unreachable — skipping store-layer integration test")

    # Step 1: provision a fresh per-test database.
    test_db_name = f"forge_bridge_test_{_phase13_uuid.uuid4().hex[:8]}"
    admin_engine = _phase13_create_async_engine(
        _phase13_admin_url(),
        isolation_level="AUTOCOMMIT",
    )
    async with admin_engine.connect() as conn:
        await conn.execute(_phase13_text(f'CREATE DATABASE "{test_db_name}"'))
    await admin_engine.dispose()

    # Step 2: build the engine pointing at the new database and create schema.
    base_url = _phase13_os.environ.get(
        "FORGE_DB_URL",
        "postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge",
    )
    scheme_and_host, _slash, _ = base_url.rpartition("/")
    test_db_url = f"{scheme_and_host}/{test_db_name}"

    engine = _phase13_create_async_engine(test_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(_phase13_Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        yield factory
    finally:
        # Step 4: teardown — close engine, then drop the database.
        await engine.dispose()
        admin_engine = _phase13_create_async_engine(
            _phase13_admin_url(),
            isolation_level="AUTOCOMMIT",
        )
        async with admin_engine.connect() as conn:
            # Disconnect any lingering sessions before drop
            await conn.execute(_phase13_text(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()"
            ))
            await conn.execute(_phase13_text(f'DROP DATABASE "{test_db_name}"'))
        await admin_engine.dispose()
