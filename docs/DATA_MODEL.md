# forge-bridge Data Model

## Philosophy

forge-bridge is post-production git. The analogy is precise:

| Git concept    | forge-bridge concept                              |
|----------------|---------------------------------------------------|
| Repository     | Shot                                              |
| Commit         | Version (= the batch file IS the commit object)   |
| Tracked blob   | Media                                             |
| File path      | Location                                          |
| `git log`      | List versions of a shot in order                  |
| `git blame`    | Which version produced this render?               |
| `git diff`     | Which media changed between two versions?         |
| Blast radius   | Which shots consume this media?                   |

---

## Entity Hierarchy

```
Project
  └── Sequence   (editorial cut, e.g. "test", "sc01")
        └── Shot (container/repository, e.g. "ABC_010")
              └── Version  (the process/commit — == the batch file)
                    ├── consumes ──▶ Media (input atoms)
                    └── produces ──▶ Media (output atoms / render slots)
```

Media exists independently. The same Media entity can be consumed
by versions across multiple shots. It is not owned by any version.

---

## Entity Definitions

### Shot
The repository. Contains the complete history of compositional work
on one editorial unit.

```
attributes:
  sequence_name    str    which sequence this shot belongs to
  cut_in           int    editorial in frame
  cut_out          int    editorial out frame
  status           str    in_progress | approved | on_hold | omit
```

### Version
The commit. Represents a specific compositional state — the batch file
that was published at a point in time. The batch file IS the version.
Not a plate or render — those are Media entities produced by this version.

```
attributes:
  shot_id          uuid   parent shot
  iteration        int    version counter within this shot (001, 002...)
  published_by     str    artist name
  published_at     datetime
  sequence_name    str    which sequence
  notes            str    free-form description of changes

location:
  path/to/shot_v001.batch    storage_type="batch"
```

Version.iteration is the comp revision counter.
It is entirely separate from Media.generation (see below).

### Media
The atomic unit of content. Immutable from the moment of creation.
Represents one specific processed state of source material.

Media has two independent numbering axes:
- `role`       — what pipeline stage produced it (raw/grade/denoise/prep/roto/comp)
- `generation` — iteration within that role (0, 1, 2...)

`generation=0` is reserved exclusively for raw camera material.
Nothing can have generation=0 unless it arrived directly from camera.
A grade v1 has generation=1 of role=grade. If the grade is revised,
the new delivery has generation=2 of role=grade. The old one still exists.

```
attributes:
  role           str    raw | grade | denoise | prep | roto | comp | ref
  generation     int    0=camera source, 1+ = processed iterations
  format         str    exr | dpx | mov | batch | clip
  width          int
  height         int
  colorspace     str    ACEScct | ACEScg | linear | log3g10 | etc.
  bit_depth      str    16f | 32f | 10bit | 12bit
  fps            str    23.976 | 24 | 25 | 29.97
  frame_in       int    first frame number
  frame_out      int    last frame number
  tape_name      str    Flame tape name (camera roll or grade pass ID)
  source_tc_in   str    source timecode in (HH:MM:SS:FF)
  source_tc_out  str    source timecode out
  layer_index    int    which comp layer (1=L01, 2=L02, 3=L03...)
                        null for project-level media (not layer-specific)

locations (1..n per media entity):
  primary path:   /path/to/frames.[####].exr    storage_type="local"
  clip pointer:   /path/to/segment.clip         storage_type="clip"
  (openClip is a second location on the same media, not a separate entity)
```

### Render Media
A subtype of Media (role=comp, generation starts at 1 after first render).
Created at publish time as an output slot — no frames yet.

```
attributes: (same as Media)
  role       = "comp"
  generation = 0   (no renders yet — slot is empty)
  format     = "clip"

location:
  /path/to/shot.clip    storage_type="clip"
  (batchOpenClip — Flame's pointer to where renders will land)
```

When a render happens, generation increments and frame_in/frame_out
are populated. The batchOpenClip location remains stable.

---

## Relationship Types

### Structural (what it IS)
```
shot       member_of  →  sequence     (shot belongs to sequence)
sequence   member_of  →  project      (sequence belongs to project)
version    member_of  →  shot         (version is a commit in this shot's history)
```

### Process (what it DOES)
```
version    consumes   →  media        (version had this media as input)
version    produces   →  media        (version created this media as output)
```
The `consumes` edge has an edge attribute: `comp_role` (primary / matte /
background / foreground / reference) — this is the compositional function
of the media within this specific version, NOT a property of the media itself.

### Lineage (where it CAME FROM)
```
media      derived_from  →  media     (this media was produced from that media)
```
Raw camera media has no derived_from edge. It is a graph root.
Every other media entity has exactly one derived_from edge pointing
to its immediate processing ancestor.

---

## Role Vocabularies

Two separate vocabularies, both stored in registry_roles with a
`role_class` discriminator attribute.

### Media Roles (role_class = "media")
Describe what pipeline stage produced a piece of media.
These travel with the Media entity.

| name    | description                                              |
|---------|----------------------------------------------------------|
| raw     | Direct camera capture — generation always 0              |
| grade   | Colour graded plate                                      |
| denoise | Noise reduction pass                                     |
| prep    | Paint / cleanup work                                     |
| roto    | Rotoscope delivery                                       |
| comp    | Composite render output                                  |
| ref     | Reference material (editorial cut, director's ref, etc.) |

### Comp Roles (role_class = "comp")
Describe the compositional function of a media entity within a
specific version's comp stack. These live on the `consumes` edge,
not on the media itself. The same plate can be `primary` in one
shot's comp and `background` in another.

| name       | flame_alias | description                              |
|------------|-------------|------------------------------------------|
| primary    | L01         | Main plate — hero element of the comp    |
| matte      | L02         | Matte / holdout element                  |
| background | L03+        | Background plate                         |
| foreground | —           | Foreground element                       |
| reference  | own version | Editorial picture lock — match target    |

Note: Flame timeline versions and tracks:
- A Flame timeline VERSION is a group of tracks (not a pipeline version)
- All tracks within one Flame version can be vertically composited
- Tracks on different Flame versions cannot be composited together
- The reference track lives on its own Flame version by convention
- The reference Flame version is separate from the comp Flame version

---

## Publish Event — What Gets Created

When `forge_publish_shots` runs for one shot with 3 layers:

```
Entities created:
  Shot           ABC_010                           (if not exists)
  Version        ABC_010_v001                      (the batch file)
  Media          ABC_010_grade_L01_v01             (layer 1 plate)
  Media          ABC_010_grade_L02_v01             (layer 2 plate)
  Media          ABC_010_grade_L03_v01             (layer 3 plate)
  Media          ABC_010_comp_slot                 (render output slot)

Locations:
  Version     → ABC_010_v001.batch                storage_type="batch"
  Media L01   → ABC_010_graded_L01.[####].exr     storage_type="local"
              → ABC_010_graded_L01.clip            storage_type="clip"
  Media L02   → ABC_010_graded_L02.[####].exr     storage_type="local"
              → ABC_010_graded_L02.clip            storage_type="clip"
  Media L03   → ABC_010_graded_L03.[####].exr     storage_type="local"
              → ABC_010_graded_L03.clip            storage_type="clip"
  Comp slot   → ABC_010.clip                      storage_type="clip"

Relationships:
  Version    member_of   → Shot
  Version    consumes    → Media L01    (edge attr: comp_role="primary")
  Version    consumes    → Media L02    (edge attr: comp_role="matte")
  Version    consumes    → Media L03    (edge attr: comp_role="background")
  Version    produces    → Comp slot
  Media L01  derived_from → [grade media entity, if traceable]
```

---

## Schema Changes Required

### registry_roles — add role_class column
```sql
ALTER TABLE registry_roles ADD COLUMN role_class VARCHAR(32) DEFAULT 'comp';
```
Existing roles (primary/reference/matte/background/foreground/audio)
are comp roles. New media roles (raw/grade/denoise/prep/roto/comp/ref)
get role_class='media'.

### registry_relationship_types — add consumes / produces
```
consumes    version → media    "Version used this media as input"
produces    version → media    "Version created this media as output"
```
`derived_from` already exists.

### relationships — edge attributes already exist
The `attributes` JSONB column on DBRelationship handles `comp_role`
on consumes edges without schema changes.

### entity_attributes — Media
Current: version entity holds plate metadata (wrong model).
Required: Media entity holds format/resolution/colorspace/generation/role.

The `version` entity needs to shed plate metadata from attributes.
Clean `version` attributes:
  shot_id, iteration, published_by, published_at, sequence_name, notes

### locations — add storage_type values
Current storage_type CHECK constraint: local | network | cloud | archive
Required: add `batch` and `clip` to the allowed values.

---

## Open Questions (parking lot)

1. Ingest event — does raw camera arrival create a synthetic "ingest"
   version, or is raw media genuinely parentless?
   Current answer: genuinely parentless. Optionally tagged with ingest
   metadata (who, when, from what source) in Media.attributes.

2. Reference track publishing — automated only if timeline version can
   be tagged. Tagging system (segment colours, tags) is a future work item.

3. Audio — excluded from shot-level model for now. Sequence-level concern.

4. External deliveries (paint/roto returns from vendors) — they arrive
   as new Media entities with role=prep or role=roto and derived_from
   pointing to whatever they were derived from. System doesn't own their
   internal versioning — it just records the delivered state.
