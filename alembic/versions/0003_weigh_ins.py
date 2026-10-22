"""weigh_ins

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weigh_ins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("day", name="uq_weigh_ins_day"),
    )


def downgrade() -> None:
    op.drop_table("weigh_ins")
