import sqlalchemy as sa

from alembic import op

revision = "0002_submission_idempotency"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.add_column(sa.Column("source_message_id", sa.Integer(), nullable=True))
        batch_op.create_unique_constraint(
            "uq_processing_jobs_submission",
            ["submitted_by", "source_message_id"],
        )


def downgrade():
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.drop_constraint("uq_processing_jobs_submission", type_="unique")
        batch_op.drop_column("source_message_id")
