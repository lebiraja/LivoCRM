"""Allow chat_actions.status = 'failed' so failed AI saves are recorded (SEC-06).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-26 13:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_chat_actions_status", "chat_actions")
    op.create_check_constraint(
        "ck_chat_actions_status",
        "chat_actions",
        "status IN ('pending','confirmed','rejected','completed','failed')"
    )


def downgrade() -> None:
    op.execute("UPDATE chat_actions SET status = 'rejected' WHERE status = 'failed'")
    op.drop_constraint("ck_chat_actions_status", "chat_actions")
    op.create_check_constraint(
        "ck_chat_actions_status",
        "chat_actions",
        "status IN ('pending','confirmed','rejected','completed')"
    )
