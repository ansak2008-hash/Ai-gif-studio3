import sqlalchemy as sa

from alembic import op

revision = "0003_job_queue_fencing"
down_revision = "0002_submission_idempotency"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("owner_id", sa.String(255), nullable=True))
        batch_op.add_column(
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index("ix_processing_jobs_owner_id", ["owner_id"])


def downgrade():
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.drop_index("ix_processing_jobs_owner_id")
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("owner_id")
        batch_op.drop_column("attempt")
        batch_op.drop_column("version")
