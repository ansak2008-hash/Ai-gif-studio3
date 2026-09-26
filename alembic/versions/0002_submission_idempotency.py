from alembic import op
import sqlalchemy as sa

revision = "0002_submission_idempotency"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("processing_jobs", sa.Column("source_message_id", sa.Integer(), nullable=True))
    op.create_unique_constraint(
        "uq_processing_jobs_submission",
        "processing_jobs",
        ["submitted_by", "source_message_id"],
    )


def downgrade():
    op.drop_constraint("uq_processing_jobs_submission", "processing_jobs", type_="unique")
    op.drop_column("processing_jobs", "source_message_id")
