"""
forge-bridge message router.

Every message that arrives from a client comes here.
The router owns a ConnectionManager and a Registry, and has access
to the database via session factories.

Design:
  - Each message type maps to one handler method
  - Handlers are async coroutines
  - Handlers write to Postgres, update the in-memory registry,
    and broadcast events to subscribers
  - Errors are caught and returned as error messages — they never
    crash the server or disconnect the client

The router is the only place in the server that touches both the
store layer and the connection layer simultaneously.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Coroutine

from forge_bridge.core.entities import (
    Asset, Layer, Media, Project as CoreProject,
    Sequence as CoreSequence, Shot, Stack, Version,
)
from forge_bridge.core.registry import (
    OrphanError, ProtectedEntryError, Registry,
    RegistryError, UnknownNameError,
)
from forge_bridge.core.vocabulary import Status
from forge_bridge.server.connections import ConnectionManager, ConnectedClient
from forge_bridge.server.protocol import (
    ErrorCode, Message, MsgType,
    error, ok, pong, welcome,
)
from forge_bridge.store.repo import (
    ClientSessionRepo, EntityRepo, EventRepo,
    LocationRepo, ProjectRepo, RegistryRepo, RelationshipRepo,
)
from forge_bridge.store.session import get_session

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────

class Router:
    """Dispatches incoming messages to handler methods.

    Holds:
        connections  — ConnectionManager (live WebSocket state)
        registry     — Registry (in-memory, authoritative)

    All handlers follow the signature:
        async def handle_*(
            self,
            msg: Message,
            client: ConnectedClient,
        ) -> Message
    """

    def __init__(self, connections: ConnectionManager, registry: Registry):
        self.connections = connections
        self.registry    = registry
        self._dispatch: dict[str, Callable] = {
            MsgType.HELLO:       self._handle_hello,
            MsgType.PING:        self._handle_ping,
            MsgType.BYE:         self._handle_bye,
            MsgType.SUBSCRIBE:   self._handle_subscribe,
            MsgType.UNSUBSCRIBE: self._handle_unsubscribe,

            # Registry — roles
            MsgType.ROLE_REGISTER: self._handle_role_register,
            MsgType.ROLE_RENAME:   self._handle_role_rename,
            MsgType.ROLE_LABEL:    self._handle_role_label,
            MsgType.ROLE_UPDATE:   self._handle_role_update,
            MsgType.ROLE_DELETE:   self._handle_role_delete,
            MsgType.ROLE_LIST:     self._handle_role_list,

            # Registry — relationship types
            MsgType.REL_TYPE_REGISTER: self._handle_rel_type_register,
            MsgType.REL_TYPE_RENAME:   self._handle_rel_type_rename,
            MsgType.REL_TYPE_LABEL:    self._handle_rel_type_label,
            MsgType.REL_TYPE_DELETE:   self._handle_rel_type_delete,
            MsgType.REL_TYPE_LIST:     self._handle_rel_type_list,

            # Projects
            MsgType.PROJECT_CREATE: self._handle_project_create,
            MsgType.PROJECT_UPDATE: self._handle_project_update,
            MsgType.PROJECT_GET:    self._handle_project_get,
            MsgType.PROJECT_LIST:   self._handle_project_list,

            # Entities
            MsgType.ENTITY_CREATE: self._handle_entity_create,
            MsgType.ENTITY_UPDATE: self._handle_entity_update,
            MsgType.ENTITY_GET:    self._handle_entity_get,
            MsgType.ENTITY_LIST:   self._handle_entity_list,
            MsgType.ENTITY_DELETE: self._handle_entity_delete,

            # Graph
            MsgType.REL_CREATE: self._handle_relationship_create,
            MsgType.REL_REMOVE: self._handle_relationship_remove,
            MsgType.LOC_ADD:    self._handle_location_add,
            MsgType.LOC_REMOVE: self._handle_location_remove,

            # Queries
            MsgType.QUERY_DEPENDENTS:   self._handle_query_dependents,
            MsgType.QUERY_DEPENDENCIES: self._handle_query_dependencies,
            MsgType.QUERY_SHOT_STACK:   self._handle_query_shot_stack,
            MsgType.QUERY_EVENTS:       self._handle_query_events,
        }

    async def dispatch(
        self,
        msg: Message,
        client: ConnectedClient,
    ) -> Message | None:
        """Route a message to the right handler.

        Returns a reply message, or None if no reply should be sent
        (e.g. BYE is fire-and-forget).
        """
        handler = self._dispatch.get(msg.type)
        if handler is None:
            return error(
                msg.msg_id,
                ErrorCode.UNKNOWN_TYPE,
                f"Unknown message type: {msg.type!r}",
            )
        try:
            return await handler(msg, client)
        except Exception as e:
            logger.exception(f"Unhandled error in handler for {msg.type!r}: {e}")
            return error(
                msg.msg_id,
                ErrorCode.INTERNAL,
                f"Internal server error: {e}",
            )

    # ─────────────────────────────────────────────────────────
    # Handshake
    # ─────────────────────────────────────────────────────────

    async def _handle_hello(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        # The client object was already created by the server before dispatch.
        # This handler just sends the welcome response with registry state.
        async with get_session() as session:
            # Write session record
            session_repo = ClientSessionRepo(session)
            db_session = await session_repo.open(
                client_name=client.client_name,
                endpoint_type=client.endpoint_type,
                host=client.remote_address,
            )
            await session.flush()

            # If reconnecting, queue missed events (sent separately after welcome)
            catchup_events = []
            if msg.get("last_event_id"):
                event_repo = EventRepo(session)
                missed = await event_repo.get_since_sequence(
                    uuid.UUID(msg["last_event_id"])
                )
                catchup_events = [e.payload for e in missed]

        return welcome(
            session_id=str(client.session_id),
            request_id=msg.msg_id,
            registry_summary=self.registry.summary(),
        )

    async def _handle_ping(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        return pong(msg.msg_id)

    async def _handle_bye(
        self, msg: Message, client: ConnectedClient
    ) -> None:
        # Disconnect is handled by the server's connection loop
        return None

    async def _handle_subscribe(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        project_id = uuid.UUID(msg["project_id"])
        self.connections.subscribe(client.session_id, project_id)
        return ok(msg.msg_id, {"subscribed": str(project_id)})

    async def _handle_unsubscribe(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        project_id = uuid.UUID(msg["project_id"])
        self.connections.unsubscribe(client.session_id, project_id)
        return ok(msg.msg_id, {"unsubscribed": str(project_id)})

    # ─────────────────────────────────────────────────────────
    # Registry — roles
    # ─────────────────────────────────────────────────────────

    async def _handle_role_register(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        name = msg.get("name")
        if not name:
            return error(msg.msg_id, ErrorCode.INVALID, "name is required")
        try:
            role_def = self.registry.roles.register(
                name,
                label=msg.get("label"),
                order=msg.get("order", 0),
                path_template=msg.get("path_template"),
                aliases=msg.get("aliases", {}),
            )
        except RegistryError as e:
            return error(msg.msg_id, ErrorCode.ALREADY_EXISTS, str(e))

        async with get_session() as session:
            repo = RegistryRepo(session)
            await repo.save_role(role_def)
            event_repo = EventRepo(session)
            db_event = await event_repo.append(
                "role.registered",
                {"name": name, "key": str(role_def.key)},
                session_id=client.session_id,
                client_name=client.client_name,
            )

        await self.connections.broadcast_event(
            "role.registered",
            {"name": name, "key": str(role_def.key)},
            originator_session_id=client.session_id,
            event_id=str(db_event.id),
        )
        return ok(msg.msg_id, {"key": str(role_def.key), "name": name})

    async def _handle_role_rename(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        old_name = msg.get("old_name")
        new_name = msg.get("new_name")
        if not old_name or not new_name:
            return error(msg.msg_id, ErrorCode.INVALID, "old_name and new_name required")
        try:
            key = self.registry.roles.get_key(old_name)
            self.registry.roles.rename(old_name, new_name)
        except (UnknownNameError, RegistryError) as e:
            return error(msg.msg_id, ErrorCode.NOT_FOUND, str(e))

        async with get_session() as session:
            repo       = RegistryRepo(session)
            role_def   = self.registry.roles.get_by_key(key)
            await repo.save_role(role_def)
            event_repo = EventRepo(session)
            db_event   = await event_repo.append(
                "role.renamed",
                {"old_name": old_name, "new_name": new_name, "key": str(key)},
                session_id=client.session_id, client_name=client.client_name,
            )

        await self.connections.broadcast_event(
            "role.renamed",
            {"old_name": old_name, "new_name": new_name, "key": str(key)},
            originator_session_id=client.session_id,
            event_id=str(db_event.id),
        )
        return ok(msg.msg_id, {"key": str(key), "new_name": new_name})

    async def _handle_role_label(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        name = msg.get("name")
        new_label = msg.get("new_label")
        if not name or not new_label:
            return error(msg.msg_id, ErrorCode.INVALID, "name and new_label required")
        try:
            self.registry.roles.rename_label(name, new_label)
            key = self.registry.roles.get_key(name)
        except UnknownNameError as e:
            return error(msg.msg_id, ErrorCode.NOT_FOUND, str(e))

        async with get_session() as session:
            repo     = RegistryRepo(session)
            role_def = self.registry.roles.get_by_key(key)
            await repo.save_role(role_def)
            event_repo = EventRepo(session)
            db_event = await event_repo.append(
                "role.label_changed",
                {"name": name, "new_label": new_label, "key": str(key)},
                session_id=client.session_id, client_name=client.client_name,
            )

        await self.connections.broadcast_event(
            "role.label_changed",
            {"name": name, "new_label": new_label},
            originator_session_id=client.session_id,
            event_id=str(db_event.id),
        )
        return ok(msg.msg_id)

    async def _handle_role_update(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        name = msg.get("name")
        if not name:
            return error(msg.msg_id, ErrorCode.INVALID, "name required")
        try:
            role_def = self.registry.roles.update(
                name,
                label=msg.get("label"),
                order=msg.get("order"),
                path_template=msg.get("path_template"),
                aliases=msg.get("aliases"),
            )
        except UnknownNameError as e:
            return error(msg.msg_id, ErrorCode.NOT_FOUND, str(e))

        async with get_session() as session:
            repo = RegistryRepo(session)
            await repo.save_role(role_def)

        return ok(msg.msg_id)

    async def _handle_role_delete(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        name       = msg.get("name")
        migrate_to = msg.get("migrate_to")
        if not name:
            return error(msg.msg_id, ErrorCode.INVALID, "name required")
        try:
            key      = self.registry.roles.get_key(name)
            migrated = self.registry.roles.delete(name, migrate_to=migrate_to)
        except ProtectedEntryError as e:
            return error(msg.msg_id, ErrorCode.PROTECTED, str(e))
        except OrphanError as e:
            return error(msg.msg_id, ErrorCode.ORPHAN_BLOCKED, str(e),
                         details={"entity_ids": [str(i) for i in e.entity_ids[:20]]})
        except UnknownNameError as e:
            return error(msg.msg_id, ErrorCode.NOT_FOUND, str(e))

        async with get_session() as session:
            repo       = RegistryRepo(session)
            await repo.delete_role(key)
            event_repo = EventRepo(session)
            db_event   = await event_repo.append(
                "role.deleted",
                {"name": name, "key": str(key), "migrated": migrated,
                 "migrate_to": migrate_to},
                session_id=client.session_id, client_name=client.client_name,
            )

        await self.connections.broadcast_event(
            "role.deleted",
            {"name": name, "migrate_to": migrate_to, "migrated": migrated},
            originator_session_id=client.session_id,
            event_id=str(db_event.id),
        )
        return ok(msg.msg_id, {"migrated": migrated})

    async def _handle_role_list(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        roles = [
            {
                "key":           str(self.registry.roles.get_key(name)),
                "name":          name,
                "label":         self.registry.roles.get_by_name(name).label,
                "order":         self.registry.roles.get_by_name(name).role.order,
                "ref_count":     self.registry.roles.ref_count(name),
            }
            for name in self.registry.roles.names()
        ]
        return ok(msg.msg_id, {"roles": roles})

    # ─────────────────────────────────────────────────────────
    # Registry — relationship types
    # ─────────────────────────────────────────────────────────

    async def _handle_rel_type_register(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        name = msg.get("name")
        if not name:
            return error(msg.msg_id, ErrorCode.INVALID, "name required")
        try:
            typedef = self.registry.relationships.register(
                name,
                label=msg.get("label"),
                description=msg.get("description", ""),
                directionality=msg.get("directionality", "→"),
            )
        except RegistryError as e:
            return error(msg.msg_id, ErrorCode.ALREADY_EXISTS, str(e))

        async with get_session() as session:
            repo = RegistryRepo(session)
            await repo.save_relationship_type(typedef)

        return ok(msg.msg_id, {"key": str(typedef.key), "name": name})

    async def _handle_rel_type_rename(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        old_name = msg.get("old_name")
        new_name = msg.get("new_name")
        if not old_name or not new_name:
            return error(msg.msg_id, ErrorCode.INVALID, "old_name and new_name required")
        try:
            self.registry.relationships.rename(old_name, new_name)
            key = self.registry.relationships.get_key(new_name)
            typedef = self.registry.relationships.get_by_key(key)
        except (UnknownNameError, RegistryError) as e:
            return error(msg.msg_id, ErrorCode.NOT_FOUND, str(e))

        async with get_session() as session:
            repo = RegistryRepo(session)
            await repo.save_relationship_type(typedef)

        await self.connections.broadcast_event(
            "relationship_type.renamed",
            {"old_name": old_name, "new_name": new_name, "key": str(key)},
            originator_session_id=client.session_id,
        )
        return ok(msg.msg_id, {"key": str(key), "new_name": new_name})

    async def _handle_rel_type_label(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        name = msg.get("name")
        new_label = msg.get("new_label")
        if not name or not new_label:
            return error(msg.msg_id, ErrorCode.INVALID, "name and new_label required")
        try:
            self.registry.relationships.rename_label(name, new_label)
        except UnknownNameError as e:
            return error(msg.msg_id, ErrorCode.NOT_FOUND, str(e))

        async with get_session() as session:
            key = self.registry.relationships.get_key(name)
            typedef = self.registry.relationships.get_by_key(key)
            repo = RegistryRepo(session)
            await repo.save_relationship_type(typedef)

        return ok(msg.msg_id)

    async def _handle_rel_type_delete(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        name       = msg.get("name")
        migrate_to = msg.get("migrate_to")
        if not name:
            return error(msg.msg_id, ErrorCode.INVALID, "name required")
        try:
            key      = self.registry.relationships.get_key(name)
            migrated = self.registry.relationships.delete(name, migrate_to=migrate_to)
        except ProtectedEntryError as e:
            return error(msg.msg_id, ErrorCode.PROTECTED, str(e))
        except OrphanError as e:
            return error(msg.msg_id, ErrorCode.ORPHAN_BLOCKED, str(e))
        except UnknownNameError as e:
            return error(msg.msg_id, ErrorCode.NOT_FOUND, str(e))

        async with get_session() as session:
            repo = RegistryRepo(session)
            await repo.delete_relationship_type(key)

        return ok(msg.msg_id, {"migrated": migrated})

    async def _handle_rel_type_list(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        types = [
            {
                "key":   str(self.registry.relationships.get_key(name)),
                "name":  name,
                "label": self.registry.relationships.get_by_name(name).label,
            }
            for name in self.registry.relationships.names()
        ]
        return ok(msg.msg_id, {"relationship_types": types})

    # ─────────────────────────────────────────────────────────
    # Projects
    # ─────────────────────────────────────────────────────────

    async def _handle_project_create(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        name = msg.get("name")
        code = msg.get("code")
        if not name or not code:
            return error(msg.msg_id, ErrorCode.INVALID, "name and code are required")

        project = CoreProject(name=name, code=code, metadata=msg.get("metadata", {}))

        async with get_session() as session:
            repo       = ProjectRepo(session)
            await repo.save(project)
            event_repo = EventRepo(session)
            db_event   = await event_repo.append(
                "project.created",
                project.to_dict(),
                session_id=client.session_id,
                client_name=client.client_name,
                project_id=project.id,
            )

        await self.connections.broadcast_event(
            "project.created",
            {"id": str(project.id), "name": project.name, "code": project.code},
            project_id=project.id,
            originator_session_id=client.session_id,
            event_id=str(db_event.id),
        )
        return ok(msg.msg_id, {"project_id": str(project.id)})

    async def _handle_project_update(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        project_id = msg.get("project_id")
        if not project_id:
            return error(msg.msg_id, ErrorCode.INVALID, "project_id required")

        async with get_session() as session:
            repo    = ProjectRepo(session)
            project = await repo.get(uuid.UUID(project_id))
            if not project:
                return error(msg.msg_id, ErrorCode.NOT_FOUND, f"Project {project_id} not found")

            if msg.get("name"):
                project.name = msg["name"]
            if msg.get("code"):
                project.code = msg["code"]

            await repo.save(project)
            event_repo = EventRepo(session)
            db_event   = await event_repo.append(
                "project.updated", project.to_dict(),
                session_id=client.session_id, client_name=client.client_name,
                project_id=project.id,
            )

        await self.connections.broadcast_event(
            "project.updated",
            {"id": str(project.id), "name": project.name, "code": project.code},
            project_id=project.id,
            originator_session_id=client.session_id,
            event_id=str(db_event.id),
        )
        return ok(msg.msg_id)

    async def _handle_project_get(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        project_id = msg.get("project_id")
        if not project_id:
            return error(msg.msg_id, ErrorCode.INVALID, "project_id required")

        async with get_session() as session:
            project = await ProjectRepo(session).get(uuid.UUID(project_id))

        if not project:
            return error(msg.msg_id, ErrorCode.NOT_FOUND, f"Project {project_id} not found")
        return ok(msg.msg_id, project.to_dict())

    async def _handle_project_list(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        async with get_session() as session:
            projects = await ProjectRepo(session).list_all()
        return ok(msg.msg_id, {"projects": [p.to_dict() for p in projects]})

    # ─────────────────────────────────────────────────────────
    # Entities
    # ─────────────────────────────────────────────────────────

    async def _handle_entity_create(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_type = msg.get("entity_type")
        project_id  = msg.get("project_id")
        if not entity_type or not project_id:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_type and project_id required")

        # Build the core entity object from the message
        entity = self._build_entity(msg)
        if entity is None:
            return error(msg.msg_id, ErrorCode.INVALID, f"Unknown entity_type: {entity_type!r}")

        proj_uuid = uuid.UUID(project_id)

        async with get_session() as session:
            repo       = EntityRepo(session, self.registry)
            await repo.save(entity, project_id=proj_uuid)
            event_repo = EventRepo(session)
            db_event   = await event_repo.append(
                "entity.created",
                entity.to_dict(),
                session_id=client.session_id,
                client_name=client.client_name,
                project_id=proj_uuid,
                entity_id=entity.id,
            )

        await self.connections.broadcast_event(
            "entity.created",
            {"entity_type": entity_type, "entity_id": str(entity.id),
             "name": getattr(entity, "name", None)},
            project_id=proj_uuid,
            entity_id=entity.id,
            originator_session_id=client.session_id,
            event_id=str(db_event.id),
        )
        return ok(msg.msg_id, {"entity_id": str(entity.id)})

    async def _handle_entity_update(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_id = msg.get("entity_id")
        if not entity_id:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_id required")

        eid = uuid.UUID(entity_id)
        async with get_session() as session:
            repo   = EntityRepo(session, self.registry)
            entity = await repo.get(eid)
            if not entity:
                return error(msg.msg_id, ErrorCode.NOT_FOUND, f"Entity {entity_id} not found")

            if msg.get("name") is not None and hasattr(entity, "name"):
                entity.name = msg["name"]
            if msg.get("status") is not None and hasattr(entity, "status"):
                entity.status = Status.from_string(msg["status"])
            if msg.get("attributes"):
                for k, v in msg["attributes"].items():
                    if hasattr(entity, k):
                        setattr(entity, k, v)

            await repo.save(entity)
            event_repo = EventRepo(session)
            db_event   = await event_repo.append(
                "entity.updated", entity.to_dict(),
                session_id=client.session_id, client_name=client.client_name,
                entity_id=eid,
            )

        await self.connections.broadcast_event(
            "entity.updated",
            {"entity_id": entity_id, "entity_type": entity.entity_type},
            entity_id=eid,
            originator_session_id=client.session_id,
            event_id=str(db_event.id),
        )
        return ok(msg.msg_id)

    async def _handle_entity_get(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_id = msg.get("entity_id")
        if not entity_id:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_id required")

        async with get_session() as session:
            entity = await EntityRepo(session, self.registry).get(uuid.UUID(entity_id))

        if not entity:
            return error(msg.msg_id, ErrorCode.NOT_FOUND, f"Entity {entity_id} not found")
        return ok(msg.msg_id, entity.to_dict())

    async def _handle_entity_list(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_type = msg.get("entity_type")
        project_id  = msg.get("project_id")
        if not entity_type or not project_id:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_type and project_id required")

        async with get_session() as session:
            entities = await EntityRepo(session, self.registry).list_by_type(
                entity_type, uuid.UUID(project_id)
            )
        return ok(msg.msg_id, {"entities": [e.to_dict() for e in entities]})

    async def _handle_entity_delete(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_id = msg.get("entity_id")
        if not entity_id:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_id required")

        eid = uuid.UUID(entity_id)
        async with get_session() as session:
            repo = EntityRepo(session, self.registry)
            entity = await repo.get(eid)
            if not entity:
                return error(msg.msg_id, ErrorCode.NOT_FOUND, f"Entity {entity_id} not found")
            await repo.delete(eid)
            event_repo = EventRepo(session)
            db_event = await event_repo.append(
                "entity.deleted", {"entity_id": entity_id},
                session_id=client.session_id, client_name=client.client_name,
                entity_id=eid,
            )

        await self.connections.broadcast_event(
            "entity.deleted",
            {"entity_id": entity_id, "entity_type": entity.entity_type},
            entity_id=eid,
            originator_session_id=client.session_id,
            event_id=str(db_event.id),
        )
        return ok(msg.msg_id)

    # ─────────────────────────────────────────────────────────
    # Graph — relationships and locations
    # ─────────────────────────────────────────────────────────

    async def _handle_relationship_create(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        source_id = msg.get("source_id")
        target_id = msg.get("target_id")
        rel_type  = msg.get("rel_type")
        if not all([source_id, target_id, rel_type]):
            return error(msg.msg_id, ErrorCode.INVALID,
                         "source_id, target_id, rel_type required")

        try:
            rel_key = self.registry.relationships.get_key(rel_type)
        except UnknownNameError:
            return error(msg.msg_id, ErrorCode.NOT_FOUND,
                         f"Relationship type {rel_type!r} not found")

        from forge_bridge.core.traits import Relationship
        rel = Relationship(
            source_id=uuid.UUID(source_id),
            target_id=uuid.UUID(target_id),
            rel_key=rel_key,
        )
        async with get_session() as session:
            await RelationshipRepo(session).save(rel)

        await self.connections.broadcast_event(
            "relationship.created",
            {"source_id": source_id, "target_id": target_id, "rel_type": rel_type},
            originator_session_id=client.session_id,
        )
        return ok(msg.msg_id)

    async def _handle_relationship_remove(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        source_id = msg.get("source_id")
        target_id = msg.get("target_id")
        rel_type  = msg.get("rel_type")
        if not all([source_id, target_id, rel_type]):
            return error(msg.msg_id, ErrorCode.INVALID,
                         "source_id, target_id, rel_type required")

        try:
            rel_key = self.registry.relationships.get_key(rel_type)
        except UnknownNameError:
            return error(msg.msg_id, ErrorCode.NOT_FOUND,
                         f"Relationship type {rel_type!r} not found")

        async with get_session() as session:
            await RelationshipRepo(session).delete(
                uuid.UUID(source_id), uuid.UUID(target_id), rel_key
            )
        return ok(msg.msg_id)

    async def _handle_location_add(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_id    = msg.get("entity_id")
        path         = msg.get("path")
        if not entity_id or not path:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_id and path required")

        eid = uuid.UUID(entity_id)
        async with get_session() as session:
            repo   = EntityRepo(session, self.registry)
            entity = await repo.get(eid)
            if not entity:
                return error(msg.msg_id, ErrorCode.NOT_FOUND, f"Entity {entity_id} not found")

            entity.add_location(
                path=path,
                storage_type=msg.get("storage_type", "local"),
                priority=msg.get("priority", 0),
            )
            loc_repo = LocationRepo(session)
            await loc_repo.save_entity_locations(entity)

        await self.connections.broadcast_event(
            "location.added",
            {"entity_id": entity_id, "path": path},
            entity_id=eid,
            originator_session_id=client.session_id,
        )
        return ok(msg.msg_id)

    async def _handle_location_remove(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_id = msg.get("entity_id")
        path      = msg.get("path")
        if not entity_id or not path:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_id and path required")

        eid = uuid.UUID(entity_id)
        async with get_session() as session:
            repo   = EntityRepo(session, self.registry)
            entity = await repo.get(eid)
            if entity:
                entity._locations = [
                    loc for loc in entity.get_locations()
                    if loc.path != path
                ]
                await LocationRepo(session).save_entity_locations(entity)
        return ok(msg.msg_id)

    # ─────────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────────

    async def _handle_query_dependents(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_id = msg.get("entity_id")
        if not entity_id:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_id required")

        async with get_session() as session:
            dependent_ids = await RelationshipRepo(session).get_dependents(
                uuid.UUID(entity_id)
            )
        return ok(msg.msg_id, {
            "entity_id": entity_id,
            "dependents": [str(i) for i in dependent_ids],
            "count": len(dependent_ids),
        })

    async def _handle_query_dependencies(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_id = msg.get("entity_id")
        if not entity_id:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_id required")

        async with get_session() as session:
            dep_ids = await RelationshipRepo(session).get_dependencies(
                uuid.UUID(entity_id)
            )
        return ok(msg.msg_id, {
            "entity_id": entity_id,
            "dependencies": [str(i) for i in dep_ids],
            "count": len(dep_ids),
        })

    async def _handle_query_shot_stack(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        shot_id = msg.get("shot_id")
        if not shot_id:
            return error(msg.msg_id, ErrorCode.INVALID, "shot_id required")

        # Layers that have shot_id in their attributes (via stack→shot relationship)
        async with get_session() as session:
            entity_repo  = EntityRepo(session, self.registry)
            # Find the stack for this shot
            stacks = await entity_repo.find_by_attribute(
                "stack", {"shot_id": shot_id}
            )
            if not stacks:
                return ok(msg.msg_id, {"shot_id": shot_id, "layers": []})

            stack    = stacks[0]
            layers   = await entity_repo.find_by_attribute(
                "layer", {"stack_id": str(stack.id)}
            )
            layers.sort(key=lambda l: getattr(l, "order", 0))

        return ok(msg.msg_id, {
            "shot_id": shot_id,
            "stack_id": str(stack.id),
            "layers": [l.to_dict() for l in layers],
        })

    async def _handle_query_events(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        project_id = msg.get("project_id")
        entity_id  = msg.get("entity_id")
        limit      = min(msg.get("limit", 50), 500)

        async with get_session() as session:
            events = await EventRepo(session).get_recent(
                limit=limit,
                project_id=uuid.UUID(project_id) if project_id else None,
                entity_id=uuid.UUID(entity_id)   if entity_id  else None,
            )

        return ok(msg.msg_id, {
            "events": [
                {
                    "id":          str(e.id),
                    "event_type":  e.event_type,
                    "client_name": e.client_name,
                    "occurred_at": e.occurred_at.isoformat(),
                    "payload":     e.payload,
                }
                for e in events
            ]
        })

    # ─────────────────────────────────────────────────────────
    # Entity factory
    # ─────────────────────────────────────────────────────────

    def _build_entity(self, msg: Message):
        """Construct a core entity object from an entity.create message."""
        t    = msg.get("entity_type")
        a    = msg.get("attributes", {})
        name = msg.get("name")
        status = msg.get("status", "pending")

        if t == "sequence":
            return CoreSequence(
                name=name,
                project_id=msg.get("project_id"),
                frame_rate=a.get("frame_rate", "24"),
            )
        elif t == "shot":
            from forge_bridge.core.vocabulary import Timecode
            return Shot(
                name=name,
                sequence_id=a.get("sequence_id"),
                cut_in=Timecode.from_string(a["cut_in"])   if a.get("cut_in")  else None,
                cut_out=Timecode.from_string(a["cut_out"]) if a.get("cut_out") else None,
                status=status,
            )
        elif t == "asset":
            return Asset(
                name=name,
                asset_type=a.get("asset_type", "generic"),
                project_id=msg.get("project_id"),
                status=status,
            )
        elif t == "version":
            return Version(
                version_number=a.get("version_number", 1),
                parent_id=a.get("parent_id"),
                parent_type=a.get("parent_type", "shot"),
                status=status,
                created_by=a.get("created_by"),
            )
        elif t == "media":
            from forge_bridge.core.vocabulary import FrameRange
            from fractions import Fraction
            fr_data = a.get("frame_range")
            fr = FrameRange(fr_data["start"], fr_data["end"],
                            Fraction(fr_data.get("fps", "24"))) if fr_data else None
            return Media(
                format=a.get("format", "EXR"),
                resolution=a.get("resolution"),
                frame_range=fr,
                colorspace=a.get("colorspace"),
                bit_depth=a.get("bit_depth"),
                version_id=a.get("version_id"),
            )
        elif t == "layer":
            role_name = a.get("role", "primary")
            return Layer(
                role=role_name,
                stack_id=a.get("stack_id"),
                order=a.get("order", 0),
                version_id=a.get("version_id"),
                registry=self.registry,
            )
        elif t == "stack":
            return Stack(shot_id=a.get("shot_id"))
        else:
            return None
