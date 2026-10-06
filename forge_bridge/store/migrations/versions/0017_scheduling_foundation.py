"""Scheduling foundation: nine record kinds + derived indexes (#274).

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-05

Changes:
  entities
    - Extend ck_entities_type CHECK with the nine forge-contracts v0.9
      scheduling record kinds: task, responsibility, person, vendor, resource,
      resource_dependency, booking, bid, bid_line. Each is a plain entities row
      with typed fields in JSONB attributes (the 0009/0012/0013/0015/0016
      one-CHECK-enum-add pattern), NOT a new table.
    - uq_entities_person_email_lower: one person per email, case-insensitive.
    - uq_entities_resource_person_id: at most one bookable resource facet per
      person (resource_kind='person' rows carry person_id).
  projects
    - lifecycle_state String(32) NOT NULL server_default 'active'. Backfills
      every existing project to 'active'. Open set — no CHECK.
  booking_resource (new, derived — written only by EntityRepo.save)
    - (booking_id, resource_id) PK; booking_id -> entities ON DELETE CASCADE,
      resource_id -> entities ON DELETE RESTRICT, project_id -> projects
      ON DELETE CASCADE; starts_at / ends_at timestamptz, state, quantity.
    - btree (resource_id, starts_at) and (project_id, starts_at). No GiST /
      exclusion constraint: conflict detection belongs to Pipeline.
  person_username (new, derived — written only by EntityRepo.save)
    - username PK; person_id -> entities ON DELETE CASCADE.

Downgrade:
  Reverses every change above. It FAILS while any scheduling rows exist:
  recreating the pre-0017 ck_entities_type CHECK rejects the existing
  task/booking/... rows. Delete the scheduling rows first if a downgrade is
  really intended (that data is not recoverable from the downgraded schema).
  The projects.lifecycle_state values are dropped with the column.

Deploy note: run ``alembic upgrade head`` before restarting the daemons on
code that writes scheduling records.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


# Pre-#274 entity types = the post-0016 (post-#242) set. Kept explicit (and as
# literals, not contract imports) so the drop+recreate is self-contained.
_PRE_274_ENTITY_TYPES = (
    "asset",
    "assent_record",
    "consent_grant",
    "editorial_edit_workflow",
    "generation_grant",
    "layer",
    "media",
    "orch_audit_report",
    "orch_capability_snapshot",
    "orch_execution_plan",
    "orch_execution_result",
    "orch_generation_artifact",
    "orch_inputs_catalog",
    "orch_locked_intent",
    "orch_partial_fidelity_snapshot",
    "orch_pipeline_run",
    "orch_provenance_manifest",
    "orch_rule_snapshot",
    "orch_spec_convergence_trace",
    "orch_validation_report",
    "orch_workflow_record",
    "sequence",
    "shot",
    "stack",
    "staged_operation",
    "version",
)

# forge-contracts v0.9 KNOWN_SCHEDULING_KINDS at the time of this migration.
SCHEDULING_ENTITY_TYPES = (
    "task",
    "responsibility",
    "person",
    "vendor",
    "resource",
    "resource_dependency",
    "booking",
    "bid",
    "bid_line",
)

_POST_274_ENTITY_TYPES = tuple(
    sorted(_PRE_274_ENTITY_TYPES + SCHEDULING_ENTITY_TYPES)
)

PERSON_EMAIL_INDEX = "uq_entities_person_email_lower"
PERSON_EMAIL_EXPRESSION = "lower(attributes ->> 'email')"
PERSON_EMAIL_PREDICATE = "entity_type = 'person'"

RESOURCE_PERSON_INDEX = "uq_entities_resource_person_id"
RESOURCE_PERSON_EXPRESSION = "(attributes ->> 'person_id')"
RESOURCE_PERSON_PREDICATE = "entity_type = 'resource'"

BOOKING_RESOURCE_INDEXES = {
    "ix_booking_resource_resource_starts": ("resource_id", "starts_at"),
    "ix_booking_resource_project_starts": ("project_id", "starts_at"),
}
PERSON_USERNAME_INDEX = "ix_person_username_person_id"


def _entity_type_check(types: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{t}'" for t in types)
    return f"entity_type IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_POST_274_ENTITY_TYPES),
    )
    op.create_index(
        PERSON_EMAIL_INDEX,
        "entities",
        [sa.text(PERSON_EMAIL_EXPRESSION)],
        unique=True,
        postgresql_where=sa.text(PERSON_EMAIL_PREDICATE),
    )
    op.create_index(
        RESOURCE_PERSON_INDEX,
        "entities",
        [sa.text(RESOURCE_PERSON_EXPRESSION)],
        unique=True,
        postgresql_where=sa.text(RESOURCE_PERSON_PREDICATE),
    )

    op.add_column(
        "projects",
        sa.Column(
            "lifecycle_state",
            sa.String(32),
            nullable=False,
            server_default="active",
        ),
    )

    op.create_table(
        "booking_resource",
        sa.Column(
            "booking_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "entities.id",
                name="fk_booking_resource_booking_id",
                ondelete="CASCADE",
            ),
            primary_key=True,
        ),
        sa.Column(
            "resource_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "entities.id",
                name="fk_booking_resource_resource_id",
                ondelete="RESTRICT",
            ),
            primary_key=True,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "projects.id",
                name="fk_booking_resource_project_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("ends_at > starts_at", name="ck_booking_resource_interval"),
        sa.CheckConstraint("quantity >= 1", name="ck_booking_resource_quantity"),
    )
    for name, columns in BOOKING_RESOURCE_INDEXES.items():
        op.create_index(name, "booking_resource", list(columns))

    op.create_table(
        "person_username",
        sa.Column("username", sa.String(256), primary_key=True),
        sa.Column(
            "person_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "entities.id",
                name="fk_person_username_person_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
    )
    op.create_index(PERSON_USERNAME_INDEX, "person_username", ["person_id"])


def downgrade() -> None:
    op.drop_index(PERSON_USERNAME_INDEX, table_name="person_username")
    op.drop_table("person_username")
    for name in BOOKING_RESOURCE_INDEXES:
        op.drop_index(name, table_name="booking_resource")
    op.drop_table("booking_resource")
    op.drop_column("projects", "lifecycle_state")
    op.drop_index(RESOURCE_PERSON_INDEX, table_name="entities")
    op.drop_index(PERSON_EMAIL_INDEX, table_name="entities")
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_274_ENTITY_TYPES),
    )
