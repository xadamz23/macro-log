"""profile

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sex", sa.String(10), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("height_in", sa.Float(), nullable=True),
        sa.Column("goal", sa.String(20), nullable=True),
        sa.Column("training", sa.String(500), nullable=True),
        sa.Column("activity", sa.String(500), nullable=True),
        sa.Column("notes", sa.String(2000), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("profile")
