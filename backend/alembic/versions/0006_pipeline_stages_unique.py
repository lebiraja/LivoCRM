"""Add UNIQUE constraint to pipeline_stages (user_id, name).

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-08 12:30:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_pipeline_stages_user_name",
        "pipeline_stages",
        ["user_id", "name"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_pipeline_stages_user_name", "pipeline_stages")
