"""add_groundx_lifecycle_fields

Revision ID: e6f4c7b8a9d0
Revises: 9a7d2c4e1b3f
Create Date: 2026-06-12 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6f4c7b8a9d0"
down_revision: Union[str, None] = "9a7d2c4e1b3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _column_names("files")

    if "groundx_process_id" not in columns:
        op.add_column("files", sa.Column("groundx_process_id", sa.String(length=100), nullable=True))
    if "groundx_document_id" not in columns:
        op.add_column("files", sa.Column("groundx_document_id", sa.String(length=100), nullable=True))
    if "groundx_bucket_id" not in columns:
        op.add_column("files", sa.Column("groundx_bucket_id", sa.String(length=100), nullable=True))
    if "status_message" not in columns:
        op.add_column("files", sa.Column("status_message", sa.Text(), nullable=True))


def downgrade() -> None:
    columns = _column_names("files")

    if "status_message" in columns:
        op.drop_column("files", "status_message")
    if "groundx_bucket_id" in columns:
        op.drop_column("files", "groundx_bucket_id")
    if "groundx_document_id" in columns:
        op.drop_column("files", "groundx_document_id")
    if "groundx_process_id" in columns:
        op.drop_column("files", "groundx_process_id")
