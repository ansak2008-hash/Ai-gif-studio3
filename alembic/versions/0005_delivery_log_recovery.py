"""Add durable delivery log and job state-change timestamp.

Revision ID: 0005_delivery_log_recovery
Revises: 0004_artifact_idempotency
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_delivery_log_recovery"
down_revision = "0004_artifact_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.alter_column("updated_at", nullable=False, server_default=None)

    op.create_table(
        "delivery_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("external_ref", sa.String(length=255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.artifact_id"]),
        sa.ForeignKeyConstraint(["job_id"], ["processing_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id", "artifact_id", "channel", name="uq_delivery_log_identity"
        ),
    )
    op.create_index("ix_delivery_log_job_id", "delivery_log", ["job_id"])
    op.create_index("ix_delivery_log_artifact_id", "delivery_log", ["artifact_id"])
    op.create_index("ix_delivery_log_state", "delivery_log", ["state"])


def downgrade() -> None:
    op.drop_index("ix_delivery_log_state", table_name="delivery_log")
    op.drop_index("ix_delivery_log_artifact_id", table_name="delivery_log")
    op.drop_index("ix_delivery_log_job_id", table_name="delivery_log")
    op.drop_table("delivery_log")
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.drop_column("updated_at")
