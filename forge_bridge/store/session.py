"""
forge-bridge database session management.

Provides the async SQLAlchemy engine and session factory.
The server creates one engine at startup and passes sessions
to repository operations. Clients never access this directly.

Configuration is via environment variables or explicit DSN:

    FORGE_DB_URL=postgresql+asyncpg://user:pass@host:5432/forge_bridge

The async driver (asyncpg) is used throughout because the server
is async. Synchronous callers (tests, migrations, CLI tools) use
the sync engine via get_sync_engine().
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from forge_bridge.store.models import Base


# ─────────────────────────────────────────────────────────────
# DSN helpers
# ─────────────────────────────────────────────────────────────

DEFAULT_DB_URL = "postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge"
DEFAULT_SYNC_DB_URL = "postgresql+psycopg2://forge:forge@localhost:5432/forge_bridge"


def get_db_url() -> str:
    """Return the async database URL from env or default."""
    return os.environ.get("FORGE_DB_URL", DEFAULT_DB_URL)


def get_sync_db_url() -> str:
    """Return the sync database URL from env or default.

    Converts asyncpg URLs to psycopg2 automatically.
    """
    url = os.environ.get("FORGE_DB_URL", DEFAULT_SYNC_DB_URL)
    return url.replace("+asyncpg", "+psycopg2")


# ─────────────────────────────────────────────────────────────
# Async engine (used by the server at runtime)
# ─────────────────────────────────────────────────────────────

_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker | None = None


def get_async_engine(
    db_url: str | None = None,
    *,
    pool_size: int = 10,
    max_overflow: int = 20,
    echo: bool = False,
) -> AsyncEngine:
    """Return (or create) the shared async engine.

    The engine is a singleton — calling this multiple times with the
    same URL returns the same engine. Pass a different URL to create
    a second engine (useful in tests).

    Args:
        db_url:      PostgreSQL async URL. Defaults to FORGE_DB_URL env var.
        pool_size:   Connection pool size (default 10 — comfortable for a
                     studio with ~20 simultaneous Flame workstations).
        max_overflow: Extra connections beyond pool_size (default 20).
        echo:        Log all SQL statements (default False).
    """
    global _async_engine, _async_session_factory

    url = db_url or get_db_url()

    if _async_engine is None or db_url is not None:
        _async_engine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=echo,
            # Return connections to pool after each transaction
            pool_pre_ping=True,
        )
        _async_session_factory = async_sessionmaker(
            _async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _async_engine


def get_async_session_factory(
    db_url: str | None = None,
) -> async_sessionmaker:
    """Return the async session factory, initializing if needed."""
    get_async_engine(db_url)
    return _async_session_factory


@asynccontextmanager
async def get_session(
    db_url: str | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a database session.

    Commits on clean exit, rolls back on exception.

    Usage:
        async with get_session() as session:
            result = await session.execute(select(DBProject))
    """
    factory = get_async_session_factory(db_url)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────────────────────────────────────
# Sync engine (used by Alembic migrations and CLI tools)
# ─────────────────────────────────────────────────────────────

_sync_engine: Engine | None = None


def get_sync_engine(
    db_url: str | None = None,
    *,
    echo: bool = False,
) -> Engine:
    """Return (or create) the sync engine.

    Used by Alembic and any synchronous tooling. Not used by the
    server at runtime.
    """
    global _sync_engine

    url = db_url or get_sync_db_url()

    if _sync_engine is None or db_url is not None:
        _sync_engine = create_engine(
            url,
            echo=echo,
            pool_pre_ping=True,
        )

    return _sync_engine


def get_sync_session_factory(db_url: str | None = None) -> sessionmaker:
    engine = get_sync_engine(db_url)
    return sessionmaker(bind=engine, expire_on_commit=False)


# ─────────────────────────────────────────────────────────────
# Schema management
# ─────────────────────────────────────────────────────────────

async def create_tables(db_url: str | None = None) -> None:
    """Create all tables if they don't exist.

    For development and testing. Production should use Alembic migrations.
    """
    engine = get_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(db_url: str | None = None) -> None:
    """Drop all tables. Destructive — use only in tests."""
    engine = get_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def create_tables_sync(db_url: str | None = None) -> None:
    """Sync version of create_tables — used by Alembic env.py."""
    engine = get_sync_engine(db_url)
    Base.metadata.create_all(engine)
