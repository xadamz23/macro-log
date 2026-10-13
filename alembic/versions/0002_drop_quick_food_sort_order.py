"""drop quick_foods.sort_order

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Native ALTER TABLE DROP COLUMN, not batch mode: batch recreates the table, and dropping
    # the old one with foreign_keys=ON would null out every entries.quick_food_id.
    op.drop_column("quick_foods", "sort_order")


def downgrade() -> None:
    op.add_column("quick_foods", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
