"""Verify that all required services and configurations are in place."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from loguru import logger

from backend.config.settings import get_settings
from backend.utils.logging import configure_logging


def check_database() -> bool:
    """Check if the SQLite database exists and has tables.

    Returns:
        True if the database is healthy.
    """
    db_path = Path("industrial_ai.db")
    if not db_path.exists():
        logger.error("[FAIL] Database file not found: industrial_ai.db")
        return False

    import sqlite3

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "projects",
            "chats",
            "messages",
            "files",
            "ocr_results",
            "transcripts",
            "app_settings",
            "evaluation_results",
        }

        missing = expected - tables
        if missing:
            logger.error("[FAIL] Missing tables: {}", missing)
            return False

        logger.info("[PASS] Database: all {} tables present", len(expected))
        return True
    except Exception as exc:
        logger.error("[FAIL] Database check failed: {}", exc)
        return False


def check_qdrant() -> bool:
    """Check if Qdrant is accessible and the collection exists.

    Returns:
        True if Qdrant is healthy and the collection exists.
    """
    settings = get_settings()
    try:
        response = httpx.get(f"{settings.QDRANT_URL}/collections", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            collections = {c.get("name", "") for c in data.get("result", {}).get("collections", [])}
            if settings.QDRANT_COLLECTION in collections:
                logger.info("[PASS] Qdrant: connected, collection '{}' exists", settings.QDRANT_COLLECTION)
                return True
            logger.error("[FAIL] Qdrant: collection '{}' not found. Available: {}", settings.QDRANT_COLLECTION, list(collections))
            return False
        logger.error("[FAIL] Qdrant: unexpected status {}", response.status_code)
        return False
    except httpx.HTTPError as exc:
        logger.error("[FAIL] Qdrant: unreachable at {} - {}", settings.QDRANT_URL, exc)
        return False


def check_ollama() -> bool:
    """Check if Ollama is accessible.

    Returns:
        True if Ollama is healthy.
    """
    settings = get_settings()
    try:
        response = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            logger.info("[PASS] Ollama: connected, {} models available", len(models))
            return True
        logger.error("[FAIL] Ollama: unexpected status {}", response.status_code)
        return False
    except httpx.HTTPError as exc:
        logger.error("[FAIL] Ollama: unreachable at {} - {}", settings.OLLAMA_BASE_URL, exc)
        return False


def check_env_file() -> bool:
    """Check if the .env file exists.

    Returns:
        True if the .env file is present.
    """
    env_path = Path(".env")
    if env_path.exists():
        logger.info("[PASS] .env file exists")
        return True
    logger.warning("[WARN] .env file not found (copy from .env.example)")
    return False


def check_data_dirs() -> bool:
    """Check if data directories exist.

    Returns:
        True if all data directories are present.
    """
    dirs = ["data/uploads", "data/audio", "data/images"]
    all_exist = True
    for d in dirs:
        if Path(d).exists():
            logger.info("[PASS] Directory exists: {}", d)
        else:
            logger.error("[FAIL] Directory missing: {}", d)
            all_exist = False
    return all_exist


def main() -> None:
    """Run all environment checks and report results."""
    configure_logging()
    logger.info("=== Environment Verification ===\n")

    results = {
        "Database": check_database(),
        "Qdrant": check_qdrant(),
        "Ollama": check_ollama(),
        "Env File": check_env_file(),
        "Data Directories": check_data_dirs(),
    }

    print("\n=== Results ===")
    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All checks passed!")
    else:
        print("Some checks failed. See logs above for details.")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
