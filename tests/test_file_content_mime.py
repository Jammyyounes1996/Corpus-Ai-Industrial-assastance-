from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.api.routes.files import get_file_content


@pytest.mark.asyncio
async def test_file_content_endpoint_returns_png_media_type(monkeypatch, tmp_path: Path):
    image_path = tmp_path / "13.png"
    image_path.write_bytes(b"png-bytes")
    db_file = SimpleNamespace(
        id="file-13",
        original_name="13.png",
        disk_path=str(image_path),
    )
    get_file = AsyncMock(return_value=db_file)
    monkeypatch.setattr("backend.api.routes.files.crud.get_file", get_file)
    fake_session = object()

    response = await get_file_content("file-13", session=fake_session)

    assert response.media_type == "image/png"
    get_file.assert_awaited_once_with(fake_session, "file-13")
