"""
forge-bridge persistence layer.

The store package manages all database access. Nothing outside this
package writes SQL directly.

    from forge_bridge.store.session import get_session, create_tables
    from forge_bridge.store.repo import (
        RegistryRepo, ProjectRepo, EntityRepo,
        LocationRepo, RelationshipRepo, EventRepo,
    )

The server holds one async engine and creates sessions per-request.
Clients never access the store directly — they talk to the server
via the socket protocol.
"""

from forge_bridge.store.repo import (
    ClientSessionRepo,
    EntityRepo,
    EventRepo,
    LocationRepo,
    ProjectRepo,
    RegistryRepo,
    RelationshipRepo,
)
from forge_bridge.store.session import (
    create_tables,
    get_async_engine,
    get_db_url,
    get_session,
    get_sync_engine,
)

__all__ = [
    "RegistryRepo", "ProjectRepo", "EntityRepo",
    "LocationRepo", "RelationshipRepo", "EventRepo", "ClientSessionRepo",
    "get_session", "get_async_engine", "get_sync_engine",
    "get_db_url", "create_tables",
]
