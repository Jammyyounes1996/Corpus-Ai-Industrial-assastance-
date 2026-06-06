from collections.abc import AsyncGenerator

import httpx
from loguru import logger

from backend.config.settings import get_settings


class OllamaClient:
    """Async client for Ollama LLM and embedding operations."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._base_url = self._settings.OLLAMA_BASE_URL

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a completion from the LLM.

        Args:
            prompt: The user prompt.
            model: Model name override. Defaults to OLLAMA_MODEL from settings.
            system: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            The generated text.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        model = model or self._settings.OLLAMA_MODEL
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def generate_stream(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the LLM.

        Args:
            prompt: The user prompt.
            model: Model name override.
            system: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Yields:
            Individual tokens as they are generated.
        """
        model = model or self._settings.OLLAMA_MODEL
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    import json
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

    async def embed_text(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        """Generate an embedding vector for the given text.

        Uses nomic-embed-text by default for 768-dimensional vectors.

        Args:
            text: The text to embed.
            model: Embedding model name override. Defaults to OLLAMA_EMBED_MODEL.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            httpx.HTTPError: If the request fails.
            ValueError: If no embedding is returned.
        """
        model = model or self._settings.OLLAMA_EMBED_MODEL
        payload = {
            "model": model,
            "input": text,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/api/embed",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            if not embeddings or not embeddings[0]:
                raise ValueError(f"No embedding returned for model '{model}'")
            return embeddings[0]

    async def embed_texts(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: List of texts to embed.
            model: Embedding model name override.

        Returns:
            List of embedding vectors.

        Raises:
            httpx.HTTPError: If the request fails.
            ValueError: If embeddings are not returned.
        """
        model = model or self._settings.OLLAMA_EMBED_MODEL
        payload = {
            "model": model,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/embed",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            if not embeddings:
                raise ValueError(f"No embeddings returned for model '{model}'")
            return embeddings


ollama_client = OllamaClient()
