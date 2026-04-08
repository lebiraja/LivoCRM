"""Add missing indexes on foreign keys and filtered columns.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-08 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deals table indexes
    op.create_index("ix_deals_contact_id", "deals", ["contact_id"])
    op.create_index("ix_deals_stage", "deals", ["stage"])
    op.create_index("ix_deals_status", "deals", ["status"])

    # Activities table indexes
    op.create_index("ix_activities_contact_id", "activities", ["contact_id"])
    op.create_index("ix_activities_deal_id", "activities", ["deal_id"])


def downgrade() -> None:
    op.drop_index("ix_activities_deal_id", table_name="activities")
    op.drop_index("ix_activities_contact_id", table_name="activities")
    op.drop_index("ix_deals_status", table_name="deals")
    op.drop_index("ix_deals_stage", table_name="deals")
    op.drop_index("ix_deals_contact_id", table_name="deals")
