#!/usr/bin/env python
"""Run the FastAPI backend server.

Uses BACKEND_HOST and BACKEND_PORT from settings (.env file).
"""

import sys

import uvicorn


def main() -> None:
    from backend.config.settings import get_settings

    settings = get_settings()
    host = settings.BACKEND_HOST
    port = settings.BACKEND_PORT
    reload = settings.DEBUG

    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Server: http://{host}:{port}")
    print(f"Debug: {reload}")

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()