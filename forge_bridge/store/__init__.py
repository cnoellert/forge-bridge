"""
forge-bridge persistence layer.

The store package manages all database access. Nothing outside this
package writes SQL directly.

    from forge_bridge.store.session import get_session, create_tables
    from forge_bridge.store.repo import (
        RegistryRepo, ProjectRepo, EntityRepo,
        LocationRepo, RelationshipRepo, EventRepo,
    )
    from forge_bridge.store.staged_operations import (
        StagedOpRepo, StagedOpLifecycleError,
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
from forge_bridge.store.staged_operations import (
    StagedOpLifecycleError,
    StagedOpRepo,
)
from forge_bridge.store.content_addressed_repo import (
    ContentAddressedRepo,
    ImmutableArtifactError,
)
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
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
    "StagedOpRepo", "StagedOpLifecycleError",
    "ContentAddressedRepo", "ImmutableArtifactError", "LockedIntentRepo",
    "get_session", "get_async_engine", "get_sync_engine",
    "get_db_url", "create_tables",
]
