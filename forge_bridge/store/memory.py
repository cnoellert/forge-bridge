"""
forge-bridge in-memory store.

A real store implementation backed by Python dicts. No Postgres required.
Used for demos, the interactive shell, and integration tests.

Drop-in replacement for the Postgres store:
    from forge_bridge.store.memory import patch_for_memory
    patch_for_memory()   # call once before starting the server
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any


# ─────────────────────────────────────────────────────────────
# Store singleton
# ─────────────────────────────────────────────────────────────

class MemoryStore:
    def __init__(self):
        self.reset()

    def reset(self):
        self.projects:      dict[str, dict] = {}   # id → dict
        self.entities:      dict[str, dict] = {}   # id → dict
        self.locations:     dict[str, list] = defaultdict(list)   # entity_id → [loc]
        self.relationships: list[dict]      = []
        self.events:        list[dict]      = []
        self.sessions:      dict[str, dict] = {}

    def summary(self) -> dict:
        counts = defaultdict(int)
        for e in self.entities.values():
            counts[e.get("entity_type", "?")] += 1
        return {
            "projects":      len(self.projects),
            "entities":      dict(sorted(counts.items())),
            "relationships": len(self.relationships),
            "events":        len(self.events),
            "sessions":      len(self.sessions),
        }


_store = MemoryStore()

def get_store() -> MemoryStore:  return _store
def reset_store() -> None:       _store.reset()


# ─────────────────────────────────────────────────────────────
# ORM object substitute
# ─────────────────────────────────────────────────────────────

class _Obj:
    """Plain object with attribute access. Stands in for SQLAlchemy ORM rows."""
    def __repr__(self):
        return f"<{getattr(self, '_cls', 'Obj')} {vars(self)}>"


def _make(cls_name: str, data: dict) -> _Obj:
    obj = _Obj()
    obj._cls = cls_name
    for k, v in data.items():
        setattr(obj, k, v)
    # UUID-promote standard ID fields
    for field in ("id", "project_id", "entity_id", "source_id",
                  "target_id", "rel_type_key", "key"):
        raw = data.get(field)
        if raw and not isinstance(raw, uuid.UUID):
            try:
                setattr(obj, field, uuid.UUID(str(raw)))
            except (ValueError, TypeError):
                pass
    return obj


# ─────────────────────────────────────────────────────────────
# WHERE clause evaluator
# ─────────────────────────────────────────────────────────────

def _matches(row: dict, clause) -> bool:
    """Recursively evaluate a SQLAlchemy WHERE clause against a plain dict."""
    if clause is None:
        return True

    cls = type(clause).__name__

    # AND / OR lists
    if cls in ("BooleanClauseList", "ClauseList"):
        parts = [_matches(row, c) for c in clause.clauses]
        try:
            import sqlalchemy.sql.operators as sqop
            if clause.operator is sqop.and_:
                return all(parts)
            if clause.operator is sqop.or_:
                return any(parts)
        except Exception:
            pass
        return all(parts)

    # Binary comparisons
    if cls == "BinaryExpression":
        col = _col_name(clause.left)
        val = clause.right.value if hasattr(clause.right, 'value') else None

        try:
            import sqlalchemy.sql.operators as sqop
            op = clause.operator
            if op is sqop.eq:
                return _coerce(row.get(col)) == _coerce(val)
            if op is sqop.ne:
                return _coerce(row.get(col)) != _coerce(val)
            if op is sqop.is_:
                return row.get(col) is None
            if op is sqop.is_not:
                return row.get(col) is not None
        except Exception:
            pass

        # JSONB @> containment — detect by operator repr
        try:
            op_repr = repr(clause.operator)
            if '@>' in op_repr and isinstance(val, dict):
                attrs = row.get("attributes", {})
                return all(_coerce(attrs.get(k)) == _coerce(v) for k, v in val.items())
        except Exception:
            pass

        return True   # unknown op — don't filter out

    return True


def _col_name(col) -> str:
    if hasattr(col, 'key'):   return col.key
    if hasattr(col, 'name'):  return col.name
    return str(col).split('.')[-1]


def _coerce(v) -> str:
    """Normalise to string for comparison (UUIDs, ints, etc.)."""
    if v is None:           return ""
    if isinstance(v, uuid.UUID): return str(v)
    return str(v)


# ─────────────────────────────────────────────────────────────
# Session
# ─────────────────────────────────────────────────────────────

class MemorySession:
    def __init__(self, store: MemoryStore):
        self._store   = store
        self._pending = []   # (obj, is_dirty) — dirty means update in-place

    # ── Transaction lifecycle ─────────────────────────────────

    async def commit(self):
        self._flush_pending()

    async def rollback(self):
        self._pending.clear()

    async def flush(self):
        self._flush_pending()

    def add(self, obj):
        self._pending.append(obj)

    def _flush_pending(self):
        for obj in self._pending:
            self._persist(obj)
        self._pending.clear()

    # ── Reads ─────────────────────────────────────────────────

    async def get(self, model_cls, pk):
        """Look up by primary key. Flush first so recent adds are visible."""
        self._flush_pending()
        name = model_cls.__name__ if isinstance(model_cls, type) else type(model_cls).__name__
        key  = str(pk)

        if name == "DBProject":
            row = self._store.projects.get(key)
            if row is None: return None
            obj = _make("DBProject", row)
            # Track so mutations get persisted on commit
            self._pending.append(obj)
            return obj

        if name == "DBEntity":
            row = self._store.entities.get(key)
            if row is None: return None
            obj = _make("DBEntity", row)
            self._pending.append(obj)
            return obj

        if name == "DBClientSession":
            row = self._store.sessions.get(key)
            if row is None: return None
            obj = _make("DBClientSession", row)
            self._pending.append(obj)
            return obj

        return None

    async def execute(self, stmt):
        self._flush_pending()

        from sqlalchemy.sql.selectable import Select
        from sqlalchemy.sql.dml import Delete

        if isinstance(stmt, Delete):
            self._execute_delete(stmt)
            return _Result([])

        if not isinstance(stmt, Select):
            return _Result([])

        table   = self._get_table(stmt)
        sel_cols = list(stmt.selected_columns)
        wc      = stmt.whereclause

        # Check if this is a single-column select (returns tuples) or full-row select
        full_table_cols = {"id", "source_id", "target_id", "rel_type_key",
                           "name", "entity_type", "project_id", "status", "attributes"}
        is_full = len(sel_cols) > 1 or (
            len(sel_cols) == 1 and sel_cols[0].key == "id"
        )

        rows = self._query_table(table, wc, is_full)

        # For single-column selects, return tuples instead of objects
        if len(sel_cols) == 1 and not is_full:
            col_key = sel_cols[0].key
            return _TupleResult([
                (getattr(r, col_key, None),) for r in rows
            ])

        return _Result(rows)

    def _get_table(self, stmt) -> str:
        try:
            froms = list(stmt.get_final_froms())
            if froms: return froms[0].name
        except Exception:
            pass
        return ""

    def _query_table(self, table: str, wc, is_full: bool) -> list:
        if table == "projects":
            rows = [r for r in self._store.projects.values() if _matches(r, wc)]
            return [_make("DBProject", r) for r in rows]

        if table == "entities":
            rows = [r for r in self._store.entities.values() if _matches(r, wc)]
            rows.sort(key=lambda r: r.get("name") or "")
            return [_make("DBEntity", r) for r in rows]

        if table == "relationships":
            rows = [r for r in self._store.relationships if _matches(r, wc)]
            return [_make("DBRelationship", r) for r in rows]

        if table == "locations":
            all_locs = [
                {**loc, "entity_id": eid}
                for eid, locs in self._store.locations.items()
                for loc in locs
            ]
            rows = [r for r in all_locs if _matches(r, wc)]
            return [_make("DBLocation", r) for r in rows]

        if table == "events":
            rows = [r for r in reversed(self._store.events) if _matches(r, wc)]
            try:
                lim = stmt._limit_clause  # noqa
                if lim is not None and hasattr(lim, 'value'):
                    rows = rows[:int(lim.value)]
            except Exception:
                pass
            return [_make("DBEvent", r) for r in rows]

        if table == "sessions":
            rows = [r for r in self._store.sessions.values() if _matches(r, wc)]
            return [_make("DBClientSession", r) for r in rows]

        return []

    def _execute_delete(self, stmt) -> None:
        table = self._get_table(stmt)
        wc    = stmt.whereclause
        if table == "entities":
            keys = [k for k, v in self._store.entities.items() if _matches(v, wc)]
            for k in keys:
                del self._store.entities[k]
        if table == "relationships":
            self._store.relationships = [
                r for r in self._store.relationships if not _matches(r, wc)
            ]

    # ── Writes ────────────────────────────────────────────────

    def _persist(self, obj) -> None:
        cls = getattr(obj, '_cls', type(obj).__name__)

        if cls == "DBProject":
            sid = str(obj.id)
            self._store.projects[sid] = {
                "id":         sid,
                "name":       str(obj.name),
                "code":       str(obj.code),
                "attributes": dict(getattr(obj, "attributes", {}) or {}),
                "created_at": str(getattr(obj, "created_at", "")),
            }

        elif cls == "DBEntity":
            sid = str(obj.id)
            existing = self._store.entities.get(sid, {})
            self._store.entities[sid] = {
                "id":          sid,
                "entity_type": str(obj.entity_type),
                "project_id":  str(obj.project_id) if getattr(obj, "project_id", None) else existing.get("project_id"),
                "name":        getattr(obj, "name", existing.get("name")),
                "status":      getattr(obj, "status", None) or existing.get("status") or "pending",
                "attributes":  dict(getattr(obj, "attributes", {}) or {}),
                "created_at":  str(getattr(obj, "created_at", "")),
            }

        elif cls == "DBLocation":
            eid = str(obj.entity_id)
            loc = {
                "path":         str(obj.path),
                "storage_type": str(getattr(obj, "storage_type", "local")),
                "priority":     int(getattr(obj, "priority", 0)),
                "exists":       bool(getattr(obj, "exists", True)),
            }
            if loc not in self._store.locations[eid]:
                self._store.locations[eid].append(loc)

        elif cls == "DBRelationship":
            rel = {
                "source_id":    str(obj.source_id),
                "target_id":    str(obj.target_id),
                "rel_type_key": str(obj.rel_type_key),
            }
            if rel not in self._store.relationships:
                self._store.relationships.append(rel)

        elif cls == "DBEvent":
            self._store.events.append({
                "id":          str(getattr(obj, "id", uuid.uuid4())),
                "event_type":  str(obj.event_type),
                "payload":     dict(getattr(obj, "payload", {}) or {}),
                "client_name": str(getattr(obj, "client_name", "")),
                "project_id":  str(getattr(obj, "project_id", "") or ""),
                "entity_id":   str(getattr(obj, "entity_id", "") or ""),
                "occurred_at": str(getattr(obj, "occurred_at", "")),
            })

        elif cls == "DBClientSession":
            sid = str(obj.id)
            self._store.sessions[sid] = {
                "id":              sid,
                "client_name":     str(getattr(obj, "client_name", "")),
                "endpoint_type":   str(getattr(obj, "endpoint_type", "")),
                "connected_at":    str(getattr(obj, "connected_at", "")),
                "disconnected_at": getattr(obj, "disconnected_at", None),
            }


class _Result:
    """Full-row result — scalars().all() returns objects."""
    def __init__(self, rows): self._rows = rows
    def scalars(self):        return self
    def all(self):            return self._rows
    def scalar_one_or_none(self): return self._rows[0] if self._rows else None
    def __iter__(self):       return iter(self._rows)


class _TupleResult:
    """Column-select result — all() returns (val,) tuples like real SQLAlchemy."""
    def __init__(self, rows): self._rows = rows
    def all(self):            return self._rows
    def scalar_one_or_none(self): return self._rows[0][0] if self._rows else None
    def scalars(self):        return _ScalarWrapper(self._rows)
    def __iter__(self):       return iter(self._rows)


class _ScalarWrapper:
    def __init__(self, rows): self._rows = rows
    def all(self):            return [r[0] for r in self._rows]


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def get_memory_session():
    session = MemorySession(_store)
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise


def patch_for_memory():
    """Patch both session consumers to use the in-memory store. Call once."""
    import forge_bridge.store.session as sm
    import forge_bridge.server.router as rm
    sm.get_session = get_memory_session
    rm.get_session = get_memory_session
