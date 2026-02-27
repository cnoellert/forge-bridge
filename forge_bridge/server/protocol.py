"""
forge-bridge wire protocol.

Every message that crosses the socket is defined here — client→server
and server→client. Both sides import from this module. If it isn't
here it doesn't exist on the wire.

Message format: JSON object with at minimum:

    {
        "type": "<message_type>",
        "id":   "<uuid>",          # client-generated request ID (requests only)
        ...payload fields...
    }

Server responses always echo the request "id" so the client can
correlate responses to requests:

    {
        "type": "ok",
        "id":   "<same uuid>",
        ...result fields...
    }

Errors:

    {
        "type":    "error",
        "id":      "<same uuid or null>",
        "code":    "NOT_FOUND",
        "message": "Shot EP60_010 not found"
    }

Events pushed by the server (no request id):

    {
        "type":       "event",
        "event_type": "entity.updated",
        "entity_id":  "...",
        "project_id": "...",
        "payload":    {...}
    }

Message types are grouped:
  - Handshake:   hello, welcome, ping, pong
  - Registry:    role.*, relationship_type.*
  - Projects:    project.*
  - Entities:    entity.*
  - Graph:       relationship.*, location.*
  - Queries:     query.*
  - Server push: event, broadcast
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import json


# ─────────────────────────────────────────────────────────────
# Message type constants
# ─────────────────────────────────────────────────────────────

class MsgType:
    # Handshake
    HELLO   = "hello"       # client → server on connect
    WELCOME = "welcome"     # server → client after hello
    PING    = "ping"        # either direction
    PONG    = "pong"        # reply to ping
    BYE     = "bye"         # clean disconnect notification

    # Generic responses
    OK      = "ok"          # server → client: success + optional result
    ERROR   = "error"       # server → client: failure

    # Registry — roles
    ROLE_REGISTER   = "role.register"
    ROLE_RENAME     = "role.rename"
    ROLE_LABEL      = "role.rename_label"
    ROLE_UPDATE     = "role.update"
    ROLE_DELETE     = "role.delete"
    ROLE_LIST       = "role.list"

    # Registry — relationship types
    REL_TYPE_REGISTER = "rel_type.register"
    REL_TYPE_RENAME   = "rel_type.rename"
    REL_TYPE_LABEL    = "rel_type.rename_label"
    REL_TYPE_DELETE   = "rel_type.delete"
    REL_TYPE_LIST     = "rel_type.list"

    # Projects
    PROJECT_CREATE = "project.create"
    PROJECT_UPDATE = "project.update"
    PROJECT_GET    = "project.get"
    PROJECT_LIST   = "project.list"
    PROJECT_DELETE = "project.delete"

    # Entities (shots, sequences, versions, media, layers, stacks, assets)
    ENTITY_CREATE = "entity.create"
    ENTITY_UPDATE = "entity.update"
    ENTITY_GET    = "entity.get"
    ENTITY_LIST   = "entity.list"
    ENTITY_DELETE = "entity.delete"

    # Graph
    REL_CREATE  = "relationship.create"
    REL_REMOVE  = "relationship.remove"
    LOC_ADD     = "location.add"
    LOC_REMOVE  = "location.remove"

    # Queries
    QUERY_DEPENDENTS   = "query.dependents"    # what depends on X?
    QUERY_DEPENDENCIES = "query.dependencies"  # what does X depend on?
    QUERY_SHOT_STACK   = "query.shot_stack"    # all layers for a shot
    QUERY_EVENTS       = "query.events"        # recent event log

    # Subscriptions
    SUBSCRIBE   = "subscribe"    # client → server: I want events for project X
    UNSUBSCRIBE = "unsubscribe"

    # Server push
    EVENT       = "event"        # server → clients: something changed


# ─────────────────────────────────────────────────────────────
# Error codes
# ─────────────────────────────────────────────────────────────

class ErrorCode:
    NOT_FOUND        = "NOT_FOUND"
    ALREADY_EXISTS   = "ALREADY_EXISTS"
    ORPHAN_BLOCKED   = "ORPHAN_BLOCKED"
    PROTECTED        = "PROTECTED"
    INVALID          = "INVALID"
    UNAUTHORIZED     = "UNAUTHORIZED"
    INTERNAL         = "INTERNAL"
    UNKNOWN_TYPE     = "UNKNOWN_TYPE"


# ─────────────────────────────────────────────────────────────
# Base message helpers
# ─────────────────────────────────────────────────────────────

def _new_id() -> str:
    return str(uuid.uuid4())


class Message(dict):
    """A wire message — just a dict with a type field and helpers.

    We subclass dict so it serializes directly with json.dumps() and
    can be pattern-matched on ["type"] without unwrapping.
    """

    @classmethod
    def parse(cls, raw: str | bytes) -> "Message":
        """Deserialize a JSON string into a Message."""
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object, got {type(data)}")
        if "type" not in data:
            raise ValueError("Message missing 'type' field")
        return cls(data)

    def serialize(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self)

    @property
    def type(self) -> str:
        return self["type"]

    @property
    def msg_id(self) -> str | None:
        return self.get("id")

    def is_request(self) -> bool:
        return "id" in self

    def __repr__(self) -> str:
        return f"Message(type={self.type!r}, id={self.msg_id!r})"


# ─────────────────────────────────────────────────────────────
# Constructors — client → server messages
# ─────────────────────────────────────────────────────────────

def hello(
    client_name: str,
    endpoint_type: str = "unknown",
    capabilities: dict | None = None,
    last_event_id: str | None = None,
) -> Message:
    """First message from client after connecting.

    last_event_id: if the client is reconnecting, pass the ID of the last
    event it received. The server will replay any missed events.
    """
    return Message({
        "type":          MsgType.HELLO,
        "id":            _new_id(),
        "client_name":   client_name,
        "endpoint_type": endpoint_type,
        "capabilities":  capabilities or {},
        "last_event_id": last_event_id,
    })


def ping(msg_id: str | None = None) -> Message:
    return Message({"type": MsgType.PING, "id": msg_id or _new_id()})


def bye(reason: str = "client_shutdown") -> Message:
    return Message({"type": MsgType.BYE, "reason": reason})


def subscribe(project_id: str, msg_id: str | None = None) -> Message:
    return Message({
        "type":       MsgType.SUBSCRIBE,
        "id":         msg_id or _new_id(),
        "project_id": project_id,
    })


def unsubscribe(project_id: str, msg_id: str | None = None) -> Message:
    return Message({
        "type":       MsgType.UNSUBSCRIBE,
        "id":         msg_id or _new_id(),
        "project_id": project_id,
    })


# Project messages
def project_create(name: str, code: str, metadata: dict | None = None) -> Message:
    return Message({
        "type": MsgType.PROJECT_CREATE,
        "id":   _new_id(),
        "name": name,
        "code": code,
        "metadata": metadata or {},
    })


def project_get(project_id: str) -> Message:
    return Message({"type": MsgType.PROJECT_GET, "id": _new_id(), "project_id": project_id})


def project_list() -> Message:
    return Message({"type": MsgType.PROJECT_LIST, "id": _new_id()})


# Entity messages
def entity_create(
    entity_type: str,
    project_id: str,
    attributes: dict,
    name: str | None = None,
    status: str | None = None,
) -> Message:
    return Message({
        "type":        MsgType.ENTITY_CREATE,
        "id":          _new_id(),
        "entity_type": entity_type,
        "project_id":  project_id,
        "name":        name,
        "status":      status,
        "attributes":  attributes,
    })


def entity_update(
    entity_id: str,
    attributes: dict | None = None,
    name: str | None = None,
    status: str | None = None,
) -> Message:
    return Message({
        "type":       MsgType.ENTITY_UPDATE,
        "id":         _new_id(),
        "entity_id":  entity_id,
        "name":       name,
        "status":     status,
        "attributes": attributes,
    })


def entity_get(entity_id: str) -> Message:
    return Message({"type": MsgType.ENTITY_GET, "id": _new_id(), "entity_id": entity_id})


def entity_list(entity_type: str, project_id: str) -> Message:
    return Message({
        "type":        MsgType.ENTITY_LIST,
        "id":          _new_id(),
        "entity_type": entity_type,
        "project_id":  project_id,
    })


# Graph messages
def relationship_create(
    source_id:  str,
    target_id:  str,
    rel_type:   str,
    attributes: dict | None = None,
) -> Message:
    msg: dict = {
        "type":      MsgType.REL_CREATE,
        "id":        _new_id(),
        "source_id": source_id,
        "target_id": target_id,
        "rel_type":  rel_type,
    }
    if attributes:
        msg["attributes"] = attributes
    return Message(msg)


def location_add(
    entity_id: str,
    path: str,
    storage_type: str = "local",
    priority: int = 0,
) -> Message:
    return Message({
        "type":         MsgType.LOC_ADD,
        "id":           _new_id(),
        "entity_id":    entity_id,
        "path":         path,
        "storage_type": storage_type,
        "priority":     priority,
    })


# Query messages
def query_dependents(entity_id: str) -> Message:
    return Message({"type": MsgType.QUERY_DEPENDENTS, "id": _new_id(), "entity_id": entity_id})


def query_shot_stack(shot_id: str) -> Message:
    return Message({"type": MsgType.QUERY_SHOT_STACK, "id": _new_id(), "shot_id": shot_id})


def query_events(
    project_id: str | None = None,
    entity_id: str | None = None,
    limit: int = 50,
) -> Message:
    return Message({
        "type":       MsgType.QUERY_EVENTS,
        "id":         _new_id(),
        "project_id": project_id,
        "entity_id":  entity_id,
        "limit":      limit,
    })


# Registry messages
def role_register(
    name: str,
    label: str | None = None,
    order: int = 0,
    path_template: str | None = None,
    aliases: dict | None = None,
) -> Message:
    return Message({
        "type":          MsgType.ROLE_REGISTER,
        "id":            _new_id(),
        "name":          name,
        "label":         label,
        "order":         order,
        "path_template": path_template,
        "aliases":       aliases or {},
    })


def role_rename(old_name: str, new_name: str) -> Message:
    return Message({
        "type": MsgType.ROLE_RENAME, "id": _new_id(),
        "old_name": old_name, "new_name": new_name,
    })


def role_list() -> Message:
    return Message({"type": MsgType.ROLE_LIST, "id": _new_id()})


def role_delete(name: str, migrate_to: str | None = None) -> Message:
    return Message({
        "type": MsgType.ROLE_DELETE, "id": _new_id(),
        "name": name, "migrate_to": migrate_to,
    })


# ─────────────────────────────────────────────────────────────
# Constructors — server → client messages
# ─────────────────────────────────────────────────────────────

def ok(request_id: str, result: Any = None) -> Message:
    msg = Message({"type": MsgType.OK, "id": request_id})
    if result is not None:
        msg["result"] = result
    return msg


def error(
    request_id: str | None,
    code: str,
    message: str,
    details: dict | None = None,
) -> Message:
    msg = Message({
        "type":    MsgType.ERROR,
        "id":      request_id,
        "code":    code,
        "message": message,
    })
    if details:
        msg["details"] = details
    return msg


def welcome(
    session_id: str,
    request_id: str,
    server_version: str = "0.1.0",
    registry_summary: dict | None = None,
) -> Message:
    return Message({
        "type":             MsgType.WELCOME,
        "id":               request_id,
        "session_id":       session_id,
        "server_version":   server_version,
        "registry_summary": registry_summary or {},
    })


def pong(request_id: str) -> Message:
    return Message({"type": MsgType.PONG, "id": request_id})


def event(
    event_type: str,
    payload: dict,
    project_id: str | None = None,
    entity_id: str | None = None,
    event_id: str | None = None,
) -> Message:
    """Server-push event to all subscribed clients."""
    return Message({
        "type":       MsgType.EVENT,
        "event_id":   event_id or _new_id(),
        "event_type": event_type,
        "project_id": project_id,
        "entity_id":  entity_id,
        "payload":    payload,
    })
