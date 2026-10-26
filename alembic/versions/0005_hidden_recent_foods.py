"""hidden recent foods

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hidden_recent_foods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name_key", sa.String(100), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=False),
        sa.Column("protein", sa.Float(), nullable=False),
        sa.Column("fat", sa.Float(), nullable=False),
        sa.Column("carbs", sa.Float(), nullable=False),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("hidden_recent_foods")
