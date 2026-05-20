import sys

from loguru import logger

from backend.config.settings import get_settings


def configure_logging() -> None:
    """Configure loguru logging for the application.

    Removes the default handler and adds configured sinks
    based on the application settings.
    """
    settings = get_settings()

    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    logger.add(
        "logs/app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )

    logger.info("Logging configured at level {}", settings.LOG_LEVEL)


def get_logger(name: str = __name__):
    """Return a logger instance bound with a module name.

    Args:
        name: Module name to bind to the logger.

    Returns:
        A loguru logger instance with the module name bound.
    """
    return logger.bind(name=name)
