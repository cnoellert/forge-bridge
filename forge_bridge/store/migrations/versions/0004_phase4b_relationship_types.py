"""Phase 4B relationship types — artifact, run, and reference-role lineage.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-28

Changes:
  registry_relationship_types
    - Seed Phase 4B artifact-lineage types: content_source, anchored_to,
      remediated_from, superseded_by
    - Seed Phase 4B run-lineage types: replays_run, remediates_run, amends_run
    - Seed Phase 4B reference-role types: reference_structural,
      reference_editorial, reference_identity, reference_motion,
      reference_depth, reference_compositional_anchor,
      reference_source_truth_anchor

Per PHASE-4B-ORCHESTRATION-DESIGN.md §4 (Relationship type families).
No table-shape changes — seed rows only.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


# ── Well-known UUIDs (4B block 0040) ─────────────────────────────────────────
# Per PHASE-4B-ORCHESTRATION-DESIGN.md §4 — pinned; never uuid.uuid4() at runtime.

_REL_KEYS: dict[str, uuid.UUID] = {
    # Artifact lineage
    "content_source": uuid.UUID("00000000-0000-0000-0040-000000000001"),
    "anchored_to": uuid.UUID("00000000-0000-0000-0040-000000000002"),
    "remediated_from": uuid.UUID("00000000-0000-0000-0040-000000000003"),
    "superseded_by": uuid.UUID("00000000-0000-0000-0040-000000000004"),
    # Run lineage
    "replays_run": uuid.UUID("00000000-0000-0000-0040-000000000005"),
    "remediates_run": uuid.UUID("00000000-0000-0000-0040-000000000006"),
    "amends_run": uuid.UUID("00000000-0000-0000-0040-000000000007"),
    # Reference roles
    "reference_structural": uuid.UUID("00000000-0000-0000-0040-000000000008"),
    "reference_editorial": uuid.UUID("00000000-0000-0000-0040-000000000009"),
    "reference_identity": uuid.UUID("00000000-0000-0000-0040-000000000010"),
    "reference_motion": uuid.UUID("00000000-0000-0000-0040-000000000011"),
    "reference_depth": uuid.UUID("00000000-0000-0000-0040-000000000012"),
    "reference_compositional_anchor": uuid.UUID(
        "00000000-0000-0000-0040-000000000013"
    ),
    "reference_source_truth_anchor": uuid.UUID(
        "00000000-0000-0000-0040-000000000014"
    ),
}

_REL_ROWS: list[dict] = [
    {
        "name": "content_source",
        "label": "content source",
        "description": "Content lineage (what produced what)",
    },
    {
        "name": "anchored_to",
        "label": "anchored to",
        "description": (
            "Anchor lineage (rule 4 — what each step was anchored against)"
        ),
    },
    {
        "name": "remediated_from",
        "label": "remediated from",
        "description": "Artifact-level remediation lineage",
    },
    {
        "name": "superseded_by",
        "label": "superseded by",
        "description": "Promotion supersession",
    },
    {
        "name": "replays_run",
        "label": "replays run",
        "description": "Top-level replay relationship",
    },
    {
        "name": "remediates_run",
        "label": "remediates run",
        "description": "Remediation entry to source run",
    },
    {
        "name": "amends_run",
        "label": "amends run",
        "description": "Specifically the amended-intent variant",
    },
    {
        "name": "reference_structural",
        "label": "reference structural",
        "description": "Structural reference role",
    },
    {
        "name": "reference_editorial",
        "label": "reference editorial",
        "description": "Editorial reference (never image input)",
    },
    {
        "name": "reference_identity",
        "label": "reference identity",
        "description": "Identity-lock reference",
    },
    {
        "name": "reference_motion",
        "label": "reference motion",
        "description": "Motion-source reference",
    },
    {
        "name": "reference_depth",
        "label": "reference depth",
        "description": "Depth reference",
    },
    {
        "name": "reference_compositional_anchor",
        "label": "reference compositional anchor",
        "description": "Compositional anchor (rule 9)",
    },
    {
        "name": "reference_source_truth_anchor",
        "label": "reference source truth anchor",
        "description": "Source-truth anchor (rule 4)",
    },
]

_ALL_REL_UUIDS = tuple(_REL_KEYS.values())


def upgrade() -> None:
    rel_table = sa.table(
        "registry_relationship_types",
        sa.column("key", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("label", sa.String),
        sa.column("description", sa.Text),
        sa.column("directionality", sa.String),
        sa.column("protected", sa.Boolean),
    )
    op.bulk_insert(
        rel_table,
        [
            {
                "key": _REL_KEYS[row["name"]],
                "name": row["name"],
                "label": row["label"],
                "description": row["description"],
                "directionality": "→",
                "protected": True,
            }
            for row in _REL_ROWS
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    placeholders = ", ".join(f":k{i}" for i in range(len(_ALL_REL_UUIDS)))
    params = {f"k{i}": str(key) for i, key in enumerate(_ALL_REL_UUIDS)}
    conn.execute(
        sa.text(
            f"DELETE FROM registry_relationship_types WHERE key IN ({placeholders})"
        ),
        params,
    )
