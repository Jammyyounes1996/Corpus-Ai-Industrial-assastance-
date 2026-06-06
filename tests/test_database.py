import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.database.crud import create_message
from backend.database.models import Chat


@pytest.mark.asyncio
async def test_timestamps_are_not_frozen(db_session):
    chat1 = Chat(
        title="chat-1",
        model_provider="ollama",
        model_name="gemma4:latest",
    )
    db_session.add(chat1)
    await db_session.flush()

    await asyncio.sleep(0.01)

    chat2 = Chat(
        title="chat-2",
        model_provider="ollama",
        model_name="gemma4:latest",
    )
    db_session.add(chat2)
    await db_session.flush()

    assert chat1.created_at != chat2.created_at


@pytest.mark.asyncio
async def test_create_message_uses_flush_not_commit():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()

    await create_message(
        session,
        chat_id="chat-id",
        role="assistant",
        content="",
    )

    session.flush.assert_awaited_once()
    session.commit.assert_not_called()
