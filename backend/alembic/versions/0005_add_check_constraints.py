"""Add CHECK constraints for data validation.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-08 12:15:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deal constraints
    op.create_check_constraint(
        "ck_deals_stage",
        "deals",
        "stage IN ('lead','qualified','proposal','negotiation','closed_won','closed_lost')"
    )
    op.create_check_constraint(
        "ck_deals_status",
        "deals",
        "status IN ('active','won','lost')"
    )
    op.create_check_constraint(
        "ck_deals_source",
        "deals",
        "source IN ('manual','ai_chat')"
    )

    # Activity constraints
    op.create_check_constraint(
        "ck_activities_type",
        "activities",
        "type IN ('call','email','meeting','note','task')"
    )

    # Chat session constraints
    op.create_check_constraint(
        "ck_chat_sessions_status",
        "chat_sessions",
        "status IN ('active','archived','closed')"
    )

    # Chat message constraints
    op.create_check_constraint(
        "ck_chat_messages_role",
        "chat_messages",
        "role IN ('user','assistant')"
    )

    # Chat action constraints
    op.create_check_constraint(
        "ck_chat_actions_status",
        "chat_actions",
        "status IN ('pending','confirmed','rejected','completed')"
    )
    op.create_check_constraint(
        "ck_chat_actions_entity_type",
        "chat_actions",
        "entity_type IN ('contact','deal','activity')"
    )

    # User constraints
    op.create_check_constraint(
        "ck_users_plan",
        "users",
        "plan IN ('free','pro','enterprise')"
    )

    # Contact constraints
    op.create_check_constraint(
        "ck_contacts_source",
        "contacts",
        "source IN ('manual','ai_chat')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_contacts_source", "contacts")
    op.drop_constraint("ck_users_plan", "users")
    op.drop_constraint("ck_chat_actions_entity_type", "chat_actions")
    op.drop_constraint("ck_chat_actions_status", "chat_actions")
    op.drop_constraint("ck_chat_messages_role", "chat_messages")
    op.drop_constraint("ck_chat_sessions_status", "chat_sessions")
    op.drop_constraint("ck_activities_type", "activities")
    op.drop_constraint("ck_deals_source", "deals")
    op.drop_constraint("ck_deals_status", "deals")
    op.drop_constraint("ck_deals_stage", "deals")
