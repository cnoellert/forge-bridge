# forge-bridge Vocabulary

The vocabulary is the most important design document in this system. It defines the canonical language that bridge speaks — the common terms that any connected endpoint must map its native concepts to.

This document is the constitution. When two endpoints disagree about what something means, the vocabulary is the authority.

---

## Design Philosophy

### Two tiers: Entities and Traits

The vocabulary has two distinct layers:

**Entities** are the nouns — the things that exist in the pipeline world.

**Traits** are cross-cutting capabilities that any entity can possess. Rather than baking versioning or pathing into specific entity types, those behaviors are defined once as traits and any entity that needs them simply declares that it carries the trait.

This means when a new entity type is added, versioning and path logic come for free — no reimplementation.

### Roles as semantic translation

A "shot" in Flame, a "clip" in Resolve, an "entity" in ShotGrid — these are all pointing at the same real-world thing. Bridge uses **Roles** to map between what a system calls something and what bridge calls it canonically.

---

## Entities

### Project
The top-level container. Everything in bridge lives inside a Project.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Canonical identifier |
| `name` | string | Human-readable name |
| `code` | string | Short code (e.g. "EP60") |
| `metadata` | dict | Open key/value store |

Traits: `Versionable`, `Locatable`, `Relational`

---

### Sequence
An ordered collection of shots. Could be a reel, episode, scene, or cut.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Canonical identifier |
| `name` | string | Human-readable name |
| `project_id` | uuid | Parent project |
| `frame_rate` | fraction | e.g. 23.976, 25, 29.97 |
| `duration` | timecode | Total duration |
| `metadata` | dict | Open key/value store |

Traits: `Versionable`, `Locatable`, `Relational`

**Endpoint mappings:**
- Flame: timeline / sequence
- Editorial NLE: sequence / timeline
- ShotGrid: Sequence entity

---

### Shot
A discrete unit of work with a defined place in a Sequence. Has a name, a duration, and a position.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Canonical identifier |
| `name` | string | Shot code (e.g. "EP60_010") |
| `sequence_id` | uuid | Parent sequence |
| `cut_in` | timecode | In point in sequence |
| `cut_out` | timecode | Out point in sequence |
| `duration` | timecode | Duration |
| `status` | Status | Lifecycle state |
| `metadata` | dict | Open key/value store |

Traits: `Versionable`, `Locatable`, `Relational`

**Endpoint mappings:**
- Flame: segment in timeline
- ShotGrid: Shot entity
- ftrack: Shot task container

---

### Asset
Anything that isn't a Shot but gets used in one. Characters, elements, textures, audio, reference material.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Canonical identifier |
| `name` | string | Asset name |
| `asset_type` | string | Category (character, element, etc.) |
| `project_id` | uuid | Parent project |
| `status` | Status | Lifecycle state |
| `metadata` | dict | Open key/value store |

Traits: `Versionable`, `Locatable`, `Relational`

---

### Version
A specific iteration of a Shot or Asset at a point in time. Versions are immutable once created — a new version is always a new entity.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Canonical identifier |
| `version_number` | integer | Monotonically increasing |
| `parent_id` | uuid | The Shot or Asset this is a version of |
| `parent_type` | string | "shot" or "asset" |
| `created_at` | datetime | Creation timestamp |
| `created_by` | string | Author identifier |
| `status` | Status | Lifecycle state |
| `metadata` | dict | Open key/value store |

Traits: `Locatable`, `Relational`

---

### Media
The atomic unit — the actual file or frame sequence on disk (or in a storage system). Media is the terminus of every data chain. It does not carry meaning by itself; meaning is given to it by whatever entity references it.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Canonical identifier |
| `format` | string | File format (EXR, MOV, DPX, etc.) |
| `resolution` | string | e.g. "1920x1080", "4096x2160" |
| `frame_range` | FrameRange | Start/end/duration |
| `colorspace` | string | e.g. "AP0", "Rec709", "ARRI_LogC3" |
| `bit_depth` | string | e.g. "16f", "10", "8" |
| `metadata` | dict | Open key/value store |

Traits: `Versionable`, `Locatable`, `Relational`

Note: A single piece of Media may be referenced by many Versions, and may exist at multiple Locations simultaneously (local cache, network share, cloud). Location is a trait of Media, not an intrinsic property.

---

### Stack
A collection of Layers that are bound together by shared identity. In Flame terms, this is an L01/L02/L03 group where all layers belong to the same shot but serve different roles.

A Stack is not an independent entity — it is a named relationship pattern. When bridge observes multiple Layers sharing a shot identity, it recognizes them as a Stack automatically.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Canonical identifier (derived from member relationships) |
| `shot_id` | uuid | The Shot all members belong to |
| `layers` | list[Layer] | Ordered member layers |

Traits: `Relational`

---

### Layer
A single member of a Stack. Carries a Role assignment that distinguishes it from other layers in the same stack.

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | uuid | Canonical identifier |
| `stack_id` | uuid | Parent stack |
| `role` | Role | The function this layer serves |
| `order` | integer | Position within stack (1-based) |
| `version_id` | uuid | Current version reference |

Traits: `Relational`

---

## Roles

A Role is a named function that an entity fulfills. Roles provide semantic meaning that transcends software boundaries — what Flame calls "L01" and what ShotGrid calls "primary" may be the same Role in bridge's vocabulary.

Role definitions are configurable per pipeline. The following are suggested defaults:

| Role Name | Description |
|-----------|-------------|
| `primary` | The main deliverable layer. L01 in typical Flame stacks. |
| `reference` | Reference or guide material. |
| `matte` | Matte or holdout element. |
| `background` | Background plate or element. |
| `foreground` | Foreground element. |
| `color` | Color grade or LUT application layer. |
| `audio` | Audio track. |

Roles are **Locatable** — a role definition can carry folder path patterns describing where media for that role lives in the filesystem.

### Role as path template

```yaml
role: primary
path_template: "{project}/{sequence}/{shot}/plates/v{version:04d}"
```

---

## Traits

### Versionable
The entity can exist as a series of discrete iterations over time.

Any Versionable entity supports:
- `get_versions()` — return all versions, ordered
- `get_latest()` — return most recent version
- `get_version(n)` — return specific version number
- `create_version()` — create a new version

---

### Locatable
The entity has one or more path-based addresses. A Location is not a simple string — it is a structured object that knows its storage type, its base path, and whether it currently exists.

Any Locatable entity supports:
- `get_locations()` — return all known locations
- `get_primary_location()` — return the canonical/preferred location
- `add_location(path, storage_type)` — register a new location
- `resolve_path()` — return the best available path given current system state

Location types:
- `local` — local filesystem path
- `network` — network share (NFS, SMB)
- `cloud` — cloud storage (S3, GCS, etc.)
- `archive` — archived/offline storage

---

### Relational
The entity can declare and traverse relationships to other entities.

Relationship types:
- `member_of` — this entity belongs to a collection (Shot member_of Sequence)
- `version_of` — this entity is an iteration of another (Version version_of Shot)
- `derived_from` — this entity was produced from another (render derived_from source)
- `references` — this entity uses another without ownership (Layer references Version)
- `peer_of` — this entity is related to another at the same level (Layer peer_of Layer within Stack)

Any Relational entity supports:
- `get_relationships(type=None)` — return relationships, optionally filtered by type
- `add_relationship(target, type)` — declare a relationship
- `get_dependents()` — return everything that depends on this entity
- `get_dependencies()` — return everything this entity depends on

---

## Context

### Timecode
A position or range expressed in hours:minutes:seconds:frames notation. Bridge speaks timecode natively and understands the relationship between timecode and frame numbers given a frame rate.

### Frame
A discrete position. Bridge understands both frames and timecode and can convert between them.

### FrameRange
A start frame, end frame, and duration. Bridge treats these as related — changing one updates the others consistently.

### Status
Where something is in its lifecycle. Status values are configurable per pipeline. Bridge maps between whatever terms a connected system uses and its canonical Status values.

Suggested canonical values: `pending`, `in_progress`, `review`, `approved`, `rejected`, `delivered`, `archived`

---

## Connections

### Endpoint
Any piece of software connected to bridge. Has an identity, a declared type, and a capability declaration (what operations it supports).

### Channel
A named pipe between two or more endpoints. Channels can be one-to-one or broadcast. Messages sent to a Channel are delivered to all subscribers.

### Session
A period of active connection for an endpoint. Sessions have a start time, an endpoint identity, and track what capabilities are active.

---

## Verbs (Operations)

| Verb | Pattern | Description |
|------|---------|-------------|
| `query` | Request/Response | Ask bridge for information. Returns a response. |
| `push` | Fire and forget | Send information to bridge or to another endpoint. |
| `subscribe` | Registration | Register interest in a type of event. Bridge notifies on match. |
| `publish` | Broadcast | Announce that something has changed. Triggers subscriptions. |
| `translate` | Transform | Map a term from one endpoint's vocabulary to bridge canonical form. |
| `resolve` | Lookup | Ask bridge to identify something from partial information. |

---

## Dependency Graph

Bridge automatically constructs a dependency graph as data flows through it. Dependencies are inferred from the natural hierarchy of the data — no manual declaration required.

When bridge parses incoming data, it asks:
1. What type of entity is this?
2. What does its structure tell me about its relationships?
3. What already exists in the graph that this connects to?
4. What dependencies does that create or update?

The resulting graph can be queried:
- "What is the blast radius if this Version changes?"
- "What does this Shot depend on?"
- "What broke when this Asset was updated?"

See [ARCHITECTURE.md](ARCHITECTURE.md) for implementation details.

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 0.1 | 2026-02-24 | Initial vocabulary draft. Entities, traits, roles defined. |
