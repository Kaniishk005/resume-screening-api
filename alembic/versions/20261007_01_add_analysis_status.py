"""Add candidate status to analysis records.

Revision ID: 20261007_01
Revises: None
Create Date: 2026-10-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261007_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS_VALUES = ("NEW", "SHORTLISTED", "INTERVIEW", "REJECTED", "HIRED")


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("analysis")
    if not columns or "status" in columns:
        return

    op.add_column(
        "analysis",
        sa.Column(
            "status",
            sa.Enum(*STATUS_VALUES, name="candidatestatus"),
            nullable=False,
            server_default="NEW",
        ),
    )


def downgrade() -> None:
    if "status" not in _column_names("analysis"):
        return

    with op.batch_alter_table("analysis") as batch_op:
        batch_op.drop_column("status")
