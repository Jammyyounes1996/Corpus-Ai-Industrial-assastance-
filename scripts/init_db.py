"""Initialize the SQLite database with all tables and default settings."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database.database import engine, Base
from backend.database.models import AppSettings
from backend.utils.logging import configure_logging

from loguru import logger
from sqlalchemy import text


async def init_db() -> None:
    """Create all database tables and insert default AppSettings row."""
    configure_logging()
    logger.info("Initializing database...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All tables created successfully")

        result = await conn.execute(
            text("SELECT COUNT(*) FROM app_settings WHERE id = 1")
        )
        count = result.scalar()

        if count == 0:
            await conn.execute(
                AppSettings.__table__.insert().values(
                    id=1,
                    model_provider="ollama",
                    model_name="gemma4:latest",
                    theme="light",
                )
            )
            logger.info("Default AppSettings row created (id=1)")
        else:
            logger.info("AppSettings row already exists, skipping")

    db_path = Path("industrial_ai.db")
    if db_path.exists():
        logger.info("Database created: {}", db_path.resolve())
    else:
        logger.error("Database file not found after creation")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
