"""add_chat_message_indexes

Revision ID: 9a7d2c4e1b3f
Revises: 637dfa704ba3
Create Date: 2026-05-23 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a7d2c4e1b3f"
down_revision: Union[str, None] = "637dfa704ba3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    message_indexes = _index_names("messages")
    if "idx_message_chat" not in message_indexes:
        op.create_index(
            "idx_message_chat",
            "messages",
            ["chat_id", "created_at"],
            unique=False,
        )

    chat_indexes = _index_names("chats")
    if "idx_chat_updated" not in chat_indexes:
        op.create_index(
            "idx_chat_updated",
            "chats",
            [sa.text("updated_at DESC")],
            unique=False,
        )


def downgrade() -> None:
    chat_indexes = _index_names("chats")
    if "idx_chat_updated" in chat_indexes:
        op.drop_index("idx_chat_updated", table_name="chats")

    message_indexes = _index_names("messages")
    if "idx_message_chat" in message_indexes:
        op.drop_index("idx_message_chat", table_name="messages")
