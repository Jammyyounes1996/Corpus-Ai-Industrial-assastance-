from __future__ import annotations

from urllib.parse import urlparse

import httpx

from backend.config.settings import get_settings


def _normalize_brave_result(item: dict) -> dict:
    url = str(item.get("url") or "").strip()
    title = str(item.get("title") or url or "Untitled source").strip()
    snippet = str(item.get("description") or "").strip()
    parsed = urlparse(url) if url else None
    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "source": parsed.netloc if parsed and parsed.netloc else "",
        "published_date": item.get("age") or item.get("page_age") or item.get("published") or None,
    }


def _normalize_tavily_result(item: dict) -> dict:
    url = str(item.get("url") or "").strip()
    title = str(item.get("title") or url or "Untitled source").strip()
    snippet = str(item.get("content") or item.get("snippet") or "").strip()
    parsed = urlparse(url) if url else None
    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "source": parsed.netloc if parsed and parsed.netloc else "",
        "published_date": item.get("published_date") or None,
    }


def _deduplicate_results(results: list[dict], max_results: int) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict] = []
    for result in results:
        key = (
            str(result.get("url") or "").strip().lower(),
            str(result.get("source") or "").strip().lower(),
            str(result.get("title") or "").strip().lower(),
        )
        if key in seen or not key[0]:
            continue
        seen.add(key)
        deduped.append(result)
        if len(deduped) >= max_results:
            break
    return deduped


class WebSearchProvider:
    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def provider_name(self) -> str:
        return self._settings.WEB_SEARCH_PROVIDER.strip().lower()

    def is_configured(self) -> bool:
        return bool(
            self._settings.WEB_SEARCH_ENABLED
            and self.provider_name
            and self._settings.WEB_SEARCH_API_KEY.strip()
        )

    async def search(self, query: str) -> list[dict]:
        if self.provider_name == "brave":
            return await self._search_brave(query)
        if self.provider_name == "tavily":
            return await self._search_tavily(query)
        raise ValueError(f"Unsupported web search provider: {self._settings.WEB_SEARCH_PROVIDER}")

    async def _search_brave(self, query: str) -> list[dict]:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self._settings.WEB_SEARCH_API_KEY,
        }
        params = {
            "q": query,
            "count": min(max(self._settings.WEB_SEARCH_MAX_RESULTS, 1), 10),
            "text_decorations": False,
            "extra_snippets": True,
        }
        timeout = float(max(self._settings.WEB_SEARCH_TIMEOUT_SECONDS, 1))
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        raw_results = data.get("web", {}).get("results", [])
        normalized = [_normalize_brave_result(item) for item in raw_results if isinstance(item, dict)]
        return _deduplicate_results(normalized, self._settings.WEB_SEARCH_MAX_RESULTS)

    async def _search_tavily(self, query: str) -> list[dict]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._settings.WEB_SEARCH_API_KEY}",
        }
        payload = {
            "query": query,
            "max_results": max(self._settings.WEB_SEARCH_MAX_RESULTS, 1),
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
        }
        timeout = float(max(self._settings.WEB_SEARCH_TIMEOUT_SECONDS, 1))
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        raw_results = data.get("results", [])
        normalized = [_normalize_tavily_result(item) for item in raw_results if isinstance(item, dict)]
        return _deduplicate_results(normalized, self._settings.WEB_SEARCH_MAX_RESULTS)
