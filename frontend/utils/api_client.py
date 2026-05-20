from dataclasses import dataclass

import httpx


@dataclass
class APIClient:
    """HTTP client for communicating with the FastAPI backend."""

    base_url: str = "http://localhost:8000"

    async def get(self, path: str, params: dict | None = None) -> dict:
        """Send a GET request to the backend.

        Args:
            path: API endpoint path (e.g., '/health').
            params: Optional query parameters.

        Returns:
            JSON response as a dictionary.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{path}",
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, json_data: dict | None = None) -> dict:
        """Send a POST request to the backend.

        Args:
            path: API endpoint path.
            json_data: Optional JSON body.

        Returns:
            JSON response as a dictionary.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json=json_data,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    def delete(self, path: str) -> dict:
        """Send a DELETE request to the backend (synchronous for Streamlit).

        Args:
            path: API endpoint path.

        Returns:
            JSON response as a dictionary.
        """
        response = httpx.delete(
            f"{self.base_url}{path}",
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def upload_file(self, path: str, file_data: bytes, filename: str) -> dict:
        """Upload a file to the backend (synchronous for Streamlit).

        Args:
            path: API endpoint path (e.g., '/api/ingest/pdf').
            file_data: Raw file bytes.
            filename: Original filename.

        Returns:
            JSON response as a dictionary.

        Raises:
            httpx.HTTPStatusError: If the server returns an error status.
            httpx.HTTPError: If the request fails.
        """
        files = {"file": (filename, file_data)}
        response = httpx.post(
            f"{self.base_url}{path}",
            files=files,
            timeout=300.0,
        )
        response.raise_for_status()
        return response.json()

    def health_check(self) -> dict:
        """Check backend health status (synchronous for Streamlit).

        Returns:
            Health check response dictionary.
        """
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {"status": "error", "message": "Backend unreachable"}
