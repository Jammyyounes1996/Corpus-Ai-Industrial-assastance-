"""Tests for CRUD filename length validation."""
import pytest

from backend.database.crud import create_file


@pytest.mark.asyncio
async def test_create_file_normal_filename(db_session):
    """Test creating a file with normal filename."""
    file = await create_file(
        db_session,
        original_name="test_document.pdf",
        file_type="pdf",
        disk_path="/tmp/test.pdf",
        size_bytes=1024,
    )
    assert file.id
    assert file.original_name == "test_document.pdf"


@pytest.mark.asyncio
async def test_create_file_max_length_filename(db_session):
    """Test creating a file with exactly 500 char filename."""
    filename = "a" * 500
    file = await create_file(
        db_session,
        original_name=filename,
        file_type="pdf",
        disk_path="/tmp/test.pdf",
        size_bytes=1024,
    )
    assert file.original_name == filename


@pytest.mark.asyncio
async def test_create_file_too_long_filename(db_session):
    """Test creating a file with >500 char filename raises ValueError."""
    filename = "a" * 501

    with pytest.raises(ValueError, match="Filename too long"):
        await create_file(
            db_session,
            original_name=filename,
            file_type="pdf",
            disk_path="/tmp/test.pdf",
            size_bytes=1024,
        )
