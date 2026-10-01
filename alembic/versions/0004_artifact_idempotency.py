"""Enforce artifact registration identity uniqueness.

Revision ID: 0004_artifact_idempotency
Revises: 0003_job_queue_fencing
"""

from alembic import op

revision = "0004_artifact_idempotency"
down_revision = "0003_job_queue_fencing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.create_unique_constraint(
            "uq_artifacts_identity",
            ["job_id", "type", "storage_path"],
        )


def downgrade() -> None:
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_constraint("uq_artifacts_identity", type_="unique")
