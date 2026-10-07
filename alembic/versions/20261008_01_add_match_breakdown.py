"""Add nullable explainable match breakdown to analysis records.

Revision ID: 20261008_01
Revises: 20261007_01
Create Date: 2026-10-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261008_01"
down_revision: Union[str, Sequence[str], None] = "20261007_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("analysis")
    if not columns or "match_breakdown" in columns:
        return
    op.add_column("analysis", sa.Column("match_breakdown", sa.Text(), nullable=True))


def downgrade() -> None:
    if "match_breakdown" not in _column_names("analysis"):
        return
    with op.batch_alter_table("analysis") as batch_op:
        batch_op.drop_column("match_breakdown")
