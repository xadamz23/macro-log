"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _macro_columns() -> list[sa.Column]:
    return [
        sa.Column("calories", sa.Integer(), nullable=False),
        sa.Column("protein", sa.Float(), nullable=False),
        sa.Column("fat", sa.Float(), nullable=False),
        sa.Column("carbs", sa.Float(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timezone", sa.String(64), nullable=False),
    )
    op.create_table(
        "targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        *_macro_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("effective_date", name="uq_targets_effective_date"),
    )
    op.create_table(
        "quick_foods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("serving_label", sa.String(50), nullable=False),
        *_macro_columns(),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )
    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        *_macro_columns(),
        sa.Column("servings", sa.Float(), nullable=False),
        sa.Column(
            "quick_food_id",
            sa.Integer(),
            sa.ForeignKey("quick_foods.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_entries_day", "entries", ["day"])


def downgrade() -> None:
    op.drop_index("ix_entries_day", table_name="entries")
    op.drop_table("entries")
    op.drop_table("quick_foods")
    op.drop_table("targets")
    op.drop_table("app_settings")
