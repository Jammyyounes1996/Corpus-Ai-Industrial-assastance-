import pytest
from httpx import AsyncClient, ASGITransport

from backend.database import crud
from backend.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_list_files_default(db_session):
    await crud.create_file(
        db_session,
        original_name="doc1.pdf",
        file_type="pdf",
        disk_path="/tmp/doc1.pdf",
        size_bytes=1024,
    )
    await crud.create_file(
        db_session,
        original_name="audio1.mp3",
        file_type="audio",
        disk_path="/tmp/audio1.mp3",
        size_bytes=2048,
    )
    await db_session.commit()

    files, total = await crud.get_files(db_session)
    assert total >= 2
    assert len(files) >= 2


@pytest.mark.asyncio
async def test_list_files_filter_by_type(db_session):
    await crud.create_file(
        db_session,
        original_name="filter_test.pdf",
        file_type="pdf",
        disk_path="/tmp/filter_test.pdf",
        size_bytes=512,
    )
    await db_session.commit()

    files, total = await crud.get_files(db_session, file_type="pdf")
    assert total >= 1
    for f in files:
        assert f.file_type == "pdf"


@pytest.mark.asyncio
async def test_list_files_sort_options(db_session):
    await crud.create_file(
        db_session,
        original_name="alpha.pdf",
        file_type="pdf",
        disk_path="/tmp/alpha.pdf",
        size_bytes=100,
    )
    await crud.create_file(
        db_session,
        original_name="zeta.pdf",
        file_type="pdf",
        disk_path="/tmp/zeta.pdf",
        size_bytes=200,
    )
    await db_session.commit()

    files_desc, _ = await crud.get_files(db_session, sort="date_desc")
    assert len(files_desc) >= 2

    files_name, _ = await crud.get_files(db_session, sort="name")
    names = [f.original_name for f in files_name]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_delete_file_valid(db_session):
    db_file = await crud.create_file(
        db_session,
        original_name="to_delete.pdf",
        file_type="pdf",
        disk_path="/tmp/to_delete.pdf",
        size_bytes=100,
    )
    await db_session.commit()

    result = await crud.delete_file(db_session, db_file.id)
    assert result is True

    check = await crud.get_file(db_session, db_file.id)
    assert check is None


@pytest.mark.asyncio
async def test_delete_file_invalid_id(db_session):
    result = await crud.delete_file(db_session, "nonexistent-id")
    assert result is False
