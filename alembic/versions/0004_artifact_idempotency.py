"""Enforce artifact registration identity uniqueness.

Revision ID: 0004_artifact_idempotency
Revises: 0003_job_queue_fencing
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_artifact_idempotency"
down_revision = "0003_job_queue_fencing"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_artifacts_identity",
        "artifacts",
        ["job_id", "type", "storage_path"],
    )


def downgrade():
    op.drop_constraint("uq_artifacts_identity", "artifacts", type_="unique")
