"""Lower-case stored emails and make them unique case-insensitively (SEC-12).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-26 12:00:00.000000

Fails loudly if two accounts differ only by email case; resolve those by hand.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET email = lower(email) WHERE email <> lower(email)")
    op.execute("CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))")


def downgrade() -> None:
    op.execute("DROP INDEX uq_users_email_lower")
