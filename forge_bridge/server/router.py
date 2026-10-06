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

import inspect
import logging
import uuid
from fractions import Fraction
from typing import Callable

from forge_contracts.scheduling import (
    KNOWN_CAPACITY_KINDS,
    KNOWN_RESPONSIBILITY_PARTIES,
    KNOWN_TASK_SOURCINGS,
    SCHEDULING_KIND_BID,
    SCHEDULING_KIND_BID_LINE,
    SCHEDULING_KIND_BOOKING,
    SCHEDULING_KIND_PERSON,
    SCHEDULING_KIND_RESOURCE,
    SCHEDULING_KIND_RESOURCE_DEPENDENCY,
    SCHEDULING_KIND_RESPONSIBILITY,
    SCHEDULING_KIND_TASK,
    SCHEDULING_KIND_VENDOR,
)
from sqlalchemy.exc import IntegrityError

from forge_bridge.core import scheduling as sched
from forge_bridge.core.entities import (
    Asset, Layer, Media, Project as CoreProject,
    Sequence as CoreSequence, Shot, Stack, Version,
)
from forge_bridge.core.registry import (
    OrphanError, ProtectedEntryError, Registry,
    RegistryError, UnknownNameError,
)
from forge_bridge.core.scheduling import SCHEDULING_CLASSES
from forge_bridge.core.vocabulary import FrameRange, Status, Timecode
from forge_bridge.server.connections import ConnectionManager, ConnectedClient
from forge_bridge.server.protocol import (
    ErrorCode, Message, MsgType,
    error, ok, pong, welcome,
)
from forge_bridge.store.repo import (
    _TYPED_ATTR_KEYS, ClientSessionRepo, EntityRepo, EventRepo,
    LocationRepo, ProjectRepo, RegistryRepo, RelationshipRepo,
)
from forge_bridge.store.scheduling_repo import SchedulingRepo
from forge_bridge.store.session import get_session

logger = logging.getLogger(__name__)


class _Rejected(Exception):
    """An INVALID request detected inside a session scope.

    Raised (not returned) so the session rolls back before the handler
    answers — used where a write may already have been flushed.
    """


def _merge_patch(target, patch):
    """Apply an RFC 7386 JSON merge patch and return the result.

    Dict values merge recursively, ``None`` deletes the key, and any other
    value replaces. ``target`` is never mutated.
    """
    if not isinstance(patch, dict):
        return patch
    result = dict(target) if isinstance(target, dict) else {}
    for k, v in patch.items():
        if v is None:
            result.pop(k, None)
        else:
            result[k] = _merge_patch(result.get(k), v)
    return result


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

            # Scheduling queries (#274)
            MsgType.QUERY_BOOKINGS:           self._handle_query_bookings,
            MsgType.QUERY_TASKS:              self._handle_query_tasks,
            MsgType.QUERY_BIDS:               self._handle_query_bids,
            MsgType.QUERY_PERSON_BY_USERNAME: self._handle_query_person_by_username,
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
            await session_repo.open(
                client_name=client.client_name,
                endpoint_type=client.endpoint_type,
                host=client.remote_address,
            )
            await session.flush()

            # If reconnecting, queue missed events (sent separately after welcome)
            if msg.get("last_event_id"):
                event_repo = EventRepo(session)
                missed = await event_repo.get_since_sequence(
                    uuid.UUID(msg["last_event_id"])
                )
                _catchup_events = [event.payload for event in missed]

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

        try:
            project = CoreProject(
                name=name, code=code, metadata=msg.get("metadata", {}),
                lifecycle_state=msg.get("lifecycle_state"),
            )
        except (TypeError, ValueError) as e:
            return error(msg.msg_id, ErrorCode.INVALID, str(e))

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
        lifecycle_state = msg.get("lifecycle_state")
        if lifecycle_state is not None:
            # Open set (forge_contracts KNOWN_PROJECT_STATES): class check only.
            try:
                lifecycle_state = sched._text(lifecycle_state, "lifecycle_state")
            except (TypeError, ValueError) as e:
                return error(msg.msg_id, ErrorCode.INVALID, str(e))

        async with get_session() as session:
            repo    = ProjectRepo(session)
            project = await repo.get(uuid.UUID(project_id))
            if not project:
                return error(msg.msg_id, ErrorCode.NOT_FOUND, f"Project {project_id} not found")

            if msg.get("name"):
                project.name = msg["name"]
            if msg.get("code"):
                project.code = msg["code"]
            if lifecycle_state is not None:
                project.lifecycle_state = lifecycle_state

            await repo.save(project)
            event_repo = EventRepo(session)
            db_event   = await event_repo.append(
                "project.updated", project.to_dict(),
                session_id=client.session_id, client_name=client.client_name,
                project_id=project.id,
            )

        await self.connections.broadcast_event(
            "project.updated",
            {"id": str(project.id), "name": project.name, "code": project.code,
             "lifecycle_state": project.lifecycle_state},
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
        states = msg.get("lifecycle_state")
        if states is not None:
            try:
                if isinstance(states, str):
                    states = [states]
                states = sched._str_list(states, "lifecycle_state")
            except (TypeError, ValueError) as e:
                return error(msg.msg_id, ErrorCode.INVALID, str(e))

        async with get_session() as session:
            repo = ProjectRepo(session)
            projects = await (
                repo.list_all() if states is None else repo.list_all(lifecycle_states=states)
            )
        logger.info(
            "project.list returned %d projects for client=%s session=%s",
            len(projects),
            client.client_name,
            client.session_id,
        )
        return ok(msg.msg_id, {
            "projects": [p.to_dict() for p in projects],
            "store_health": {
                "status": "healthy",
                "source": "postgres",
                "read": "project.list",
            },
        })

    # ─────────────────────────────────────────────────────────
    # Entities
    # ─────────────────────────────────────────────────────────

    async def _handle_entity_create(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_type = msg.get("entity_type")
        project_id  = msg.get("project_id")
        cls = SCHEDULING_CLASSES.get(entity_type) if isinstance(entity_type, str) else None
        if cls is None:
            if not entity_type or not project_id:
                return error(msg.msg_id, ErrorCode.INVALID, "entity_type and project_id required")
        else:
            # Scheduling kinds carry their own scope (#274).
            scope_error = _scope_error(cls, project_id)
            if scope_error:
                return error(msg.msg_id, ErrorCode.INVALID, scope_error)

        # Build the core entity object from the message. Constructor
        # validation failures are the caller's input, not a server fault.
        try:
            entity = self._build_entity(msg)
        except (TypeError, ValueError, KeyError, ArithmeticError) as e:
            return error(msg.msg_id, ErrorCode.INVALID, f"{entity_type}: {e}")
        if entity is None:
            return error(msg.msg_id, ErrorCode.INVALID, f"Unknown entity_type: {entity_type!r}")

        if cls is None:
            proj_uuid = uuid.UUID(project_id)
            created = [entity]
            async with get_session() as session:
                await EntityRepo(session, self.registry).save(entity, project_id=proj_uuid)
                db_events = await self._append_created(session, client, created, proj_uuid)
        else:
            proj_uuid = entity.project_id   # None for studio-scoped kinds
            try:
                async with get_session() as session:
                    created = await self._save_scheduling(session, msg, entity)
                    db_events = await self._append_created(session, client, created, proj_uuid)
            except _Rejected as e:
                return error(msg.msg_id, ErrorCode.INVALID, str(e))

        for created_entity, db_event in zip(created, db_events):
            await self.connections.broadcast_event(
                "entity.created",
                {"entity_type": created_entity.entity_type,
                 "entity_id": str(created_entity.id),
                 "name": getattr(created_entity, "name", None)},
                project_id=proj_uuid,
                entity_id=created_entity.id,
                originator_session_id=client.session_id,
                event_id=str(db_event.id),
            )
        result = {"entity_id": str(entity.id)}
        if entity_type == SCHEDULING_KIND_PERSON:
            # The bookable facet (None when created with bookable=false).
            result["resource_id"] = str(created[1].id) if len(created) > 1 else None
        return ok(msg.msg_id, result)

    @staticmethod
    async def _append_created(session, client, entities, project_id) -> list:
        event_repo = EventRepo(session)
        return [
            await event_repo.append(
                "entity.created",
                created.to_dict(),
                session_id=client.session_id,
                client_name=client.client_name,
                project_id=project_id,
                entity_id=created.id,
            )
            for created in entities
        ]

    async def _save_scheduling(self, session, msg: Message, entity) -> list:
        """Check references, then save a new scheduling record.

        Returns the saved records: ``[entity]``, or ``[person, facet]`` for a
        bookable person. Raises ``_Rejected`` for a bad reference.
        """
        sched_repo = SchedulingRepo(session, self.registry)
        if entity.project_id is not None and await ProjectRepo(session).get(entity.project_id) is None:
            raise _Rejected(f"project_id: project {entity.project_id} not found")
        problem = await _scheduling_ref_problem(sched_repo, entity)
        if problem:
            raise _Rejected(problem)
        try:
            if entity.entity_type == SCHEDULING_KIND_PERSON:
                bookable = (msg.get("attributes") or {}).get("bookable", True)
                person, facet = await sched_repo.create_person(entity, bookable=bookable)
                return [person] if facet is None else [person, facet]
            await sched_repo.entities.save(entity)
            return [entity]
        except (IntegrityError, ValueError) as e:
            # Uniqueness (person email / username, one facet per person) and
            # store-level identity checks: the request is at fault.
            raise _Rejected(_write_conflict(entity.entity_type, e)) from e

    async def _handle_entity_update(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        entity_id = msg.get("entity_id")
        if not entity_id:
            return error(msg.msg_id, ErrorCode.INVALID, "entity_id required")

        eid = uuid.UUID(entity_id)
        try:
            return await self._update_entity(msg, client, entity_id, eid)
        except _Rejected as e:
            # Raised inside the session scope, so it has rolled back.
            return error(msg.msg_id, ErrorCode.INVALID, str(e))

    async def _update_entity(
        self, msg: Message, client: ConnectedClient, entity_id: str, eid: uuid.UUID,
    ) -> Message:
        async with get_session() as session:
            repo   = EntityRepo(session, self.registry)
            entity = await repo.get(eid)
            if not entity:
                return error(msg.msg_id, ErrorCode.NOT_FOUND, f"Entity {entity_id} not found")

            # Validate everything first, then apply, so a rejected request
            # mutates nothing (#270).
            fields = _UPDATABLE_FIELDS.get(entity.entity_type, {})
            typed: dict = {}
            if msg.get("name") is not None and hasattr(entity, "name"):
                typed["name"] = msg["name"]
            if msg.get("status") is not None and hasattr(entity, "status"):
                # A type's own status coercer wins (task / booking states are
                # stored raw, never aliased — #274); otherwise entity Status.
                coerce = fields.get("status", Status.from_string)
                try:
                    typed["status"] = coerce(msg["status"])
                except (TypeError, ValueError, AttributeError) as e:
                    return error(msg.msg_id, ErrorCode.INVALID, f"status: {e}")

            metadata = entity.metadata
            attributes = msg.get("attributes") or {}
            if not isinstance(attributes, dict):
                return error(msg.msg_id, ErrorCode.INVALID, "attributes must be an object")
            # Allowlisted typed fields are coerced as on create. `metadata` is
            # merge-patched onto the existing dict (RFC 7386) rather than
            # replacing it, and any other key is stored into metadata with the
            # same semantics — never silently dropped (#266). Identity fields,
            # non-updatable typed fields, methods and properties are rejected.
            for k, v in attributes.items():
                if k == "metadata":
                    if not isinstance(v, dict):
                        return error(msg.msg_id, ErrorCode.INVALID,
                                     "attributes.metadata must be an object")
                    metadata = _merge_patch(metadata, v)
                elif k in fields:
                    try:
                        typed[k] = fields[k](v)
                    except (TypeError, ValueError, KeyError, ArithmeticError) as e:
                        return error(msg.msg_id, ErrorCode.INVALID,
                                     f"attributes.{k}: invalid value {v!r} ({e})")
                elif _is_protected_attribute(entity, k):
                    return error(msg.msg_id, ErrorCode.INVALID,
                                 f"attributes.{k} cannot be updated on a "
                                 f"{entity.entity_type}")
                else:
                    metadata = _merge_patch(metadata, {k: v})

            cls = SCHEDULING_CLASSES.get(entity.entity_type)
            if cls is None:
                for k, v in typed.items():
                    setattr(entity, k, v)
                entity.metadata = metadata
                await repo.save(entity)
            else:
                # Re-validate the merged record through the class constructor
                # (cross-field rules such as ends_at > starts_at), check any
                # changed reference, and only then save (#274).
                before = entity
                try:
                    entity = cls(**{
                        **_scheduling_kwargs(before),
                        **typed,
                        "metadata": metadata,
                    })
                except (TypeError, ValueError) as e:
                    return error(msg.msg_id, ErrorCode.INVALID, f"{before.entity_type}: {e}")
                problem = await _scheduling_ref_problem(
                    SchedulingRepo(session, self.registry), entity, before=before,
                )
                if problem:
                    return error(msg.msg_id, ErrorCode.INVALID, problem)
                try:
                    await repo.save(entity)
                except (IntegrityError, ValueError) as e:
                    raise _Rejected(_write_conflict(entity.entity_type, e)) from e
            payload = entity.to_dict()
            if msg.get("note") is not None:
                payload["note"] = msg["note"]
            event_repo = EventRepo(session)
            db_event   = await event_repo.append(
                "entity.updated", payload,
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
        cls = SCHEDULING_CLASSES.get(entity_type) if isinstance(entity_type, str) else None
        if cls is None:
            if not entity_type or not project_id:
                return error(msg.msg_id, ErrorCode.INVALID, "entity_type and project_id required")
        else:
            scope_error = _scope_error(cls, project_id)
            if scope_error:
                return error(msg.msg_id, ErrorCode.INVALID, scope_error)

        try:
            proj_uuid = uuid.UUID(project_id) if project_id else None
        except (TypeError, ValueError, AttributeError):
            if cls is None:
                raise
            return error(msg.msg_id, ErrorCode.INVALID, f"project_id must be a UUID, got {project_id!r}")

        async with get_session() as session:
            entities = await EntityRepo(session, self.registry).list_by_type(
                entity_type, proj_uuid
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
        rel_attrs = msg.get("attributes") or {}
        rel = Relationship(
            source_id=uuid.UUID(source_id),
            target_id=uuid.UUID(target_id),
            rel_key=rel_key,
            metadata=rel_attrs,
        )
        async with get_session() as session:
            await RelationshipRepo(session).save(rel)

        await self.connections.broadcast_event(
            "relationship.created",
            {"source_id": source_id, "target_id": target_id, "rel_type": rel_type,
             "attributes": rel_attrs},
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
            layers.sort(key=lambda layer: getattr(layer, "order", 0))

        return ok(msg.msg_id, {
            "shot_id": shot_id,
            "stack_id": str(stack.id),
            "layers": [layer.to_dict(self.registry) for layer in layers],
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
    # Scheduling queries (#274) — thin reads over SchedulingRepo.
    # Input validation failures are INVALID; no query decides anything.
    # ─────────────────────────────────────────────────────────

    async def _handle_query_bookings(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        resource_ids = msg.get("resource_ids")
        project_id   = msg.get("project_id")
        if (resource_ids is None) == (project_id is None):
            return error(msg.msg_id, ErrorCode.INVALID,
                         "query.bookings takes resource_ids (with from/to) or project_id")
        try:
            states = _states(msg.get("states"))
            if resource_ids is not None:
                if isinstance(resource_ids, str) or not isinstance(resource_ids, list):
                    raise TypeError("resource_ids must be a list of UUIDs")
                ids = [sched._uuid(r, "resource_ids[]") for r in resource_ids]
                start = sched._aware(msg.get("from"), "from")
                end = sched._aware(msg.get("to"), "to")
                if end <= start:
                    raise ValueError("to must be after from")
            else:
                pid = sched._uuid(project_id, "project_id")
        except (TypeError, ValueError) as e:
            return error(msg.msg_id, ErrorCode.INVALID, str(e))

        async with get_session() as session:
            repo = SchedulingRepo(session, self.registry)
            if resource_ids is not None:
                bookings = await repo.bookings_in_range(ids, start, end, states=states)
            else:
                bookings = await repo.bookings_for_project(pid, states=states)
        return ok(msg.msg_id, {
            "bookings": [b.to_dict() for b in bookings],
            "count": len(bookings),
        })

    async def _handle_query_tasks(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        party = msg.get("party_type") is not None or msg.get("party_id") is not None
        modes = [party, msg.get("owner_id") is not None, msg.get("project_id") is not None]
        if sum(modes) != 1:
            return error(msg.msg_id, ErrorCode.INVALID,
                         "query.tasks takes exactly one of: party_type + party_id, "
                         "owner_id, project_id")
        if msg.get("on") is not None and not party:
            return error(msg.msg_id, ErrorCode.INVALID, "on applies only to a party query")
        try:
            if party:
                party_type = sched._closed(
                    msg.get("party_type"), "party_type", KNOWN_RESPONSIBILITY_PARTIES,
                )
                party_id = sched._uuid(msg.get("party_id"), "party_id")
                on = sched._opt_date(msg.get("on"), "on")
            elif msg.get("owner_id") is not None:
                owner_id = sched._uuid(msg["owner_id"], "owner_id")
            else:
                pid = sched._uuid(msg["project_id"], "project_id")
        except (TypeError, ValueError) as e:
            return error(msg.msg_id, ErrorCode.INVALID, str(e))

        async with get_session() as session:
            repo = SchedulingRepo(session, self.registry)
            if party:
                tasks = await repo.tasks_for_party(party_type, party_id, on=on)
            elif msg.get("owner_id") is not None:
                tasks = await repo.tasks_for_owner(owner_id)
            else:
                tasks = await repo.tasks_for_project(pid)
        return ok(msg.msg_id, {"tasks": [t.to_dict() for t in tasks], "count": len(tasks)})

    async def _handle_query_bids(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        try:
            pid = sched._uuid(msg.get("project_id"), "project_id")
            active = None if msg.get("active") is None else sched._bool(msg["active"], "active")
            awarded = None if msg.get("awarded") is None else sched._bool(msg["awarded"], "awarded")
            include_lines = sched._bool(msg.get("include_lines", False), "include_lines")
        except (TypeError, ValueError) as e:
            return error(msg.msg_id, ErrorCode.INVALID, str(e))

        async with get_session() as session:
            repo = SchedulingRepo(session, self.registry)
            bids = await repo.bids_for_project(pid, active=active, awarded=awarded)
            lines = await repo.bid_lines_for_bids([b.id for b in bids]) if include_lines else {}

        out = []
        for bid in bids:
            d = bid.to_dict()
            if include_lines:
                d["lines"] = [line.to_dict() for line in lines[bid.id]]
            out.append(d)
        return ok(msg.msg_id, {"bids": out, "count": len(out)})

    async def _handle_query_person_by_username(
        self, msg: Message, client: ConnectedClient
    ) -> Message:
        try:
            username = sched._text(msg.get("username"), "username")
        except (TypeError, ValueError) as e:
            return error(msg.msg_id, ErrorCode.INVALID, str(e))

        async with get_session() as session:
            repo = SchedulingRepo(session, self.registry)
            person = await repo.person_by_username(username)
            facet = await repo.person_resource(person.id) if person else None
        # No match is an answer, not an error: {"person": null}.
        return ok(msg.msg_id, {
            "person": person.to_dict() if person else None,
            "resource_id": str(facet.id) if facet else None,
        })

    # ─────────────────────────────────────────────────────────
    # Entity factory
    # ─────────────────────────────────────────────────────────

    def _build_entity(self, msg: Message):
        """Construct a core entity object from an entity.create message."""
        t    = msg.get("entity_type")
        if t in SCHEDULING_CLASSES:
            return _build_scheduling_entity(msg)
        a    = msg.get("attributes", {})
        name = msg.get("name")
        status = msg.get("status") or "pending"

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
                # Preserve all extra attributes in metadata for JSONB storage
                metadata={k: v for k, v in a.items()
                          if k not in ("sequence_id", "cut_in", "cut_out")},
            )
        elif t == "asset":
            return Asset(
                name=name,
                asset_type=a.get("asset_type", "generic"),
                project_id=msg.get("project_id"),
                status=status,
                metadata={k: v for k, v in a.items() if k != "asset_type"},
            )
        elif t == "version":
            # Our publish attributes: shot_id, iteration, version_label,
            # sequence_name, published_by. Legacy: version_number, parent_id.
            shot_id     = a.get("shot_id") or a.get("parent_id")
            iter_num    = a.get("iteration") or a.get("version_number", 1)
            v_entity = Version(
                version_number=int(iter_num),
                parent_id=shot_id,
                parent_type=a.get("parent_type", "shot"),
                status=status,
                created_by=a.get("created_by") or a.get("published_by"),
            )
            # Preserve all extra attributes in metadata for JSONB storage
            v_entity.metadata = {k: v for k, v in a.items()
                                 if k not in ("parent_id", "parent_type")}
            if name:
                v_entity.name = name
            return v_entity
        elif t == "media":
            from forge_bridge.core.vocabulary import FrameRange
            from fractions import Fraction
            # Support both new flat keys (colour_space, width, height, fps,
            # depth, tape_name, layer_index, kind) and legacy structured keys.
            fr_data = a.get("frame_range")
            fr = (FrameRange(fr_data["start"], fr_data["end"],
                             Fraction(fr_data.get("fps", "24"))) if fr_data else None)
            m_entity = Media(
                format=a.get("format", "EXR"),
                resolution=( f"{a['width']}x{a['height']}"
                             if a.get("width") and a.get("height")
                             else a.get("resolution") ),
                frame_range=fr,
                colorspace=a.get("colorspace") or a.get("colour_space"),
                bit_depth=a.get("bit_depth") or a.get("depth"),
                version_id=a.get("version_id"),
            )
            # Preserve all extra attributes (kind, tape_name, layer_index, etc.)
            m_entity.metadata = {k: v for k, v in a.items()
                                 if k not in ("frame_range", "version_id")}
            if name:
                m_entity.name = name
            return m_entity
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


# ─────────────────────────────────────────────────────────────
# Scheduling records over entity.* (#274)
# ─────────────────────────────────────────────────────────────

# Constructor keyword arguments each scheduling class takes from a create
# message's `attributes` (its typed keys, plus status / label where defined).
_SCHEDULING_INIT_KEYS: dict[str, frozenset[str]] = {
    t: frozenset(
        p for p in inspect.signature(cls.__init__).parameters
        if p not in ("self", "base", "name")
    )
    for t, cls in SCHEDULING_CLASSES.items()
}


def _scope_error(cls, project_id) -> str | None:
    """Project-scoped kinds need a project_id; studio-scoped kinds refuse one."""
    if cls.PROJECT_SCOPED and not project_id:
        return f"{cls.ENTITY_TYPE} is project-scoped: project_id required"
    if not cls.PROJECT_SCOPED and project_id:
        return f"{cls.ENTITY_TYPE} is studio-scoped: project_id must be omitted"
    return None


def _build_scheduling_entity(msg: Message):
    """Construct a scheduling record from an entity.create message.

    Typed keys come from ``attributes``; any other attribute key is kept in
    open metadata (as on the other kinds), except the identity keys, which
    are refused. Raises TypeError / ValueError on invalid input.
    """
    t = msg["entity_type"]
    attributes = msg.get("attributes") or {}
    if not isinstance(attributes, dict):
        raise TypeError("attributes must be an object")
    attributes = dict(attributes)
    if t == SCHEDULING_KIND_PERSON:
        # Router-level flag: create the bookable resource facet too (default).
        sched._bool(attributes.pop("bookable", True), "bookable")
    protected = sorted(_PROTECTED_KEYS & set(attributes))
    if protected:
        raise ValueError(f"attributes may not set {protected}")
    init_keys = _SCHEDULING_INIT_KEYS[t]
    kwargs = {k: attributes.pop(k) for k in list(attributes) if k in init_keys}
    name = msg.get("name")
    if name is None:
        name = attributes.pop("name", None)
    if msg.get("status") is not None and "status" in init_keys:
        kwargs["status"] = msg["status"]
    return SCHEDULING_CLASSES[t](
        name=name,
        project_id=msg.get("project_id") or None,
        metadata=attributes,
        **kwargs,
    )


def _scheduling_kwargs(entity) -> dict:
    """Constructor kwargs that rebuild ``entity`` as stored (for update)."""
    kwargs = {
        **entity.to_attributes(),
        "name": entity.name,
        "project_id": entity.project_id,
        "id": entity.id,
        "created_at": entity.created_at,
        "metadata": entity.metadata,
    }
    if hasattr(entity, "status"):
        kwargs["status"] = entity.status
    return kwargs


def _scheduling_refs(entity) -> list[tuple[str, uuid.UUID, frozenset[str], bool]]:
    """``(field, referenced id, allowed entity types, must share project)``."""
    t = entity.entity_type
    refs: list[tuple[str, uuid.UUID, frozenset[str], bool]] = []

    def add(field, ref_id, types, same_project):
        if ref_id is not None:
            refs.append((field, ref_id, frozenset(types), same_project))

    if t == SCHEDULING_KIND_TASK:
        add("owner_id", entity.owner_id, {entity.owner_type}, True)
    elif t == SCHEDULING_KIND_RESPONSIBILITY:
        add("party_id", entity.party_id, {entity.party_type}, False)
        add("task_id", entity.task_id, {SCHEDULING_KIND_TASK}, True)
    elif t == SCHEDULING_KIND_RESOURCE:
        add("person_id", entity.person_id, {SCHEDULING_KIND_PERSON}, False)
    elif t == SCHEDULING_KIND_BOOKING:
        for rid in entity.resource_ids:
            add("resources[].resource_id", rid, {SCHEDULING_KIND_RESOURCE}, False)
        add("task_id", entity.task_id, {SCHEDULING_KIND_TASK}, True)
        add("bid_line_id", entity.bid_line_id, {SCHEDULING_KIND_BID_LINE}, True)
    elif t == SCHEDULING_KIND_BID_LINE:
        add("bid_id", entity.bid_id, {SCHEDULING_KIND_BID}, True)
        add("vendor_id", entity.vendor_id, {SCHEDULING_KIND_VENDOR}, False)
    return refs


async def _scheduling_ref_problem(sched_repo: SchedulingRepo, entity, before=None) -> str | None:
    """Why ``entity``'s references are invalid, or None.

    On update (``before`` given) only references that changed are checked, so
    a record whose old target was since deleted can still be edited.
    """
    unchanged = {(f, i) for f, i, _, _ in _scheduling_refs(before)} if before else set()
    for field, ref_id, types, same_project in _scheduling_refs(entity):
        if (field, ref_id) in unchanged:
            continue
        found = await sched_repo.entity_ref(ref_id)
        if found is None:
            return f"{field}: {ref_id} not found"
        ref_type, ref_project = found
        if ref_type not in types:
            return f"{field}: {ref_id} is a {ref_type}, not a {' or '.join(sorted(types))}"
        if same_project and ref_project != entity.project_id:
            return f"{field}: {ref_id} belongs to another project"
    return None


def _write_conflict(entity_type: str, exc: Exception) -> str:
    if isinstance(exc, IntegrityError):
        return f"{entity_type} conflicts with an existing record: {exc.orig}"
    return f"{entity_type}: {exc}"


def _states(value) -> list[str] | None:
    """An optional list of open-set states (stored lowercased)."""
    if value is None:
        return None
    if isinstance(value, str) or not isinstance(value, list):
        raise TypeError("states must be a list of strings")
    return [sched._state(s, "states[]") for s in value]


# ─────────────────────────────────────────────────────────────
# entity.update field policy (#270)
# ─────────────────────────────────────────────────────────────

def _str(v):
    if not isinstance(v, str):
        raise TypeError("expected a string")
    return v


def _opt_str(v):
    return None if v is None else _str(v)


def _int(v):
    if isinstance(v, bool):
        raise TypeError("expected an integer")
    return int(v)


def _opt_uuid(v):
    if v is None:
        return None
    if not isinstance(v, str):
        raise TypeError("expected a UUID string")
    return uuid.UUID(v)


def _status(v):
    if not isinstance(v, str):
        raise TypeError("expected a status string")
    return Status.from_string(v)


def _opt_timecode(v):
    return None if v is None else Timecode.from_string(_str(v))


def _frame_rate(v):
    if isinstance(v, bool) or not isinstance(v, (str, int, float)):
        raise TypeError("expected a number or numeric string")
    return Fraction(v).limit_denominator(1001)


def _opt_frame_range(v):
    if v is None:
        return None
    if not isinstance(v, dict):
        raise TypeError("expected an object with start/end/fps")
    return FrameRange(_int(v["start"]), _int(v["end"]), Fraction(v.get("fps", "24")))


def _opt_bit_depth(v):
    if v is None or (isinstance(v, (str, int)) and not isinstance(v, bool)):
        return v
    raise TypeError("expected a string or integer")


# Typed fields entity.update may set via `attributes`, per entity type, each
# with the coercion `_build_entity` applies on create. Any other key either
# merge-patches into metadata or, if `_is_protected_attribute`, is rejected.
_UPDATABLE_FIELDS: dict[str, dict[str, Callable]] = {
    "sequence": {"name": _str, "frame_rate": _frame_rate},
    "shot":     {"name": _str, "status": _status, "sequence_id": _opt_uuid,
                 "cut_in": _opt_timecode, "cut_out": _opt_timecode},
    "asset":    {"name": _str, "status": _status, "asset_type": _str},
    "version":  {"name": _str, "status": _status, "version_number": _int,
                 "parent_id": _opt_uuid, "parent_type": _str,
                 "created_by": _opt_str},
    "media":    {"name": _opt_str, "status": _status, "format": _str,
                 "resolution": _opt_str, "colorspace": _opt_str,
                 "bit_depth": _opt_bit_depth, "frame_range": _opt_frame_range,
                 "version_id": _opt_uuid},
    "layer":    {"order": _int, "stack_id": _opt_uuid, "version_id": _opt_uuid},
    "stack":    {"shot_id": _opt_uuid},
}


# Scheduling kinds (#274). Coercers are the record classes' own field
# validators; the merged record is then rebuilt through its constructor
# (cross-field rules) before save. Typed keys left out of an allowlist —
# task owner, responsibility party/task/effective_from, resource kind and
# person_id, dependency types, bid version, bid_line bid_id — are protected
# by `_is_protected_attribute` via `_TYPED_ATTR_KEYS`.
def _f(validator, field, *args):
    return lambda v: validator(v, field, *args)


def _contacts(v):
    if not isinstance(v, list) or not all(isinstance(c, dict) for c in v):
        raise TypeError("expected a list of objects")
    return v


_NAME = {"name": _f(sched._opt_text, "name")}
_UPDATABLE_FIELDS.update({
    SCHEDULING_KIND_TASK: {
        **_NAME,
        "status":      _f(sched._state, "status"),   # raw: complete stays complete
        "task_type":   _f(sched._text, "task_type"),
        "sourcing":    _f(sched._closed, "sourcing", KNOWN_TASK_SOURCINGS),
        "estimate":    _f(sched._opt_decimal, "estimate"),
        "target_date": _f(sched._opt_date, "target_date"),
        "due_date":    _f(sched._opt_date, "due_date"),
    },
    SCHEDULING_KIND_RESPONSIBILITY: {
        **_NAME,
        "responsibility_type": _f(sched._text, "responsibility_type"),
        "effective_until":     _f(sched._opt_date, "effective_until"),
    },
    SCHEDULING_KIND_PERSON: {
        **_NAME,
        "email":            _f(sched._text, "email"),
        "usernames":        _f(sched._str_list, "usernames"),
        "external_user_id": _f(sched._opt_text, "external_user_id"),
    },
    SCHEDULING_KIND_VENDOR: {**_NAME, "contacts": _contacts},
    SCHEDULING_KIND_RESOURCE: {
        **_NAME,
        "capacity_kind": _f(sched._closed, "capacity_kind", KNOWN_CAPACITY_KINDS),
        "resource_type": _f(sched._opt_text, "resource_type"),
        "availability":  sched._availability,
    },
    SCHEDULING_KIND_RESOURCE_DEPENDENCY: {
        **_NAME,
        "quantity": lambda v: sched._int(v, "quantity", minimum=1),
    },
    SCHEDULING_KIND_BOOKING: {
        **_NAME,
        "label":       _f(sched._opt_text, "label"),
        "status":      _f(sched._state, "status"),   # open booking-state set
        "starts_at":   _f(sched._aware, "starts_at"),
        "ends_at":     _f(sched._aware, "ends_at"),
        "resources":   sched._booking_resources,
        "task_id":     _f(sched._opt_uuid, "task_id"),
        "bid_line_id": _f(sched._opt_uuid, "bid_line_id"),
    },
    SCHEDULING_KIND_BID: {
        **_NAME,
        "is_active":  _f(sched._bool, "is_active"),
        "is_awarded": _f(sched._bool, "is_awarded"),
        "currency":   _f(sched._text, "currency"),
    },
    SCHEDULING_KIND_BID_LINE: {
        **_NAME,
        "kind":          _f(sched._text, "kind"),
        "task_type":     _f(sched._opt_text, "task_type"),
        "resource_type": _f(sched._opt_text, "resource_type"),
        "qty":           _f(sched._decimal, "qty"),
        "rate":          _f(sched._decimal, "rate"),
        "vendor_id":     _f(sched._opt_uuid, "vendor_id"),
        "section":       _f(sched._opt_text, "section"),
    },
})

# Identity and ownership. Re-parenting into another project is not an
# entity.update operation.
_PROTECTED_KEYS = frozenset({"id", "entity_type", "created_at", "project_id"})


def _is_protected_attribute(entity, key: str) -> bool:
    """True if ``key`` names something on the entity update must not set.

    Covers identity fields, typed storage keys outside the allowlist (they
    would be silently overwritten by ``_attrs_to_dict`` on save), and any
    instance attribute, method or property of the entity.
    """
    return (
        key in _PROTECTED_KEYS
        or key in _TYPED_ATTR_KEYS.get(entity.entity_type, ())
        or hasattr(entity, key)
    )
