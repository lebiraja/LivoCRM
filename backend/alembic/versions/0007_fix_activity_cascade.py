"""Fix inconsistent cascade rule for activities.contact_id (CASCADE -> SET NULL).

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-08 12:45:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old FK with CASCADE
    op.drop_constraint("activities_contact_id_fkey", "activities", type_="foreignkey")

    # Create new FK with SET NULL
    op.create_foreign_key(
        "activities_contact_id_fkey",
        "activities",
        "contacts",
        ["contact_id"],
        ["id"],
        ondelete="SET NULL"
    )


def downgrade() -> None:
    # Drop the new FK with SET NULL
    op.drop_constraint("activities_contact_id_fkey", "activities", type_="foreignkey")

    # Restore old FK with CASCADE
    op.create_foreign_key(
        "activities_contact_id_fkey",
        "activities",
        "contacts",
        ["contact_id"],
        ["id"],
        ondelete="CASCADE"
    )
