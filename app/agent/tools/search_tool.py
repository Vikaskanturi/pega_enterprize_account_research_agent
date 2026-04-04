"""
Search tool — DuckDuckGo-based web search with optional SerpAPI fallback.
Returns structured results with title, URL, and snippet.
"""
import os
import asyncio
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
async def web_search(query: str, max_results: int = 5, site: Optional[str] = None) -> list[dict]:
    """
    Perform a web search and return a list of results.

    Args:
        query: Search query string
        max_results: Number of results to return
        site: Optional site filter (e.g. 'linkedin.com')

    Returns:
        List of dicts with keys: title, url, snippet
    """
    if site:
        query = f"site:{site} {query}"

    serpapi_key = os.getenv("SERPAPI_KEY", "")
    if serpapi_key:
        try:
            return await _serpapi_search(query, max_results, serpapi_key)
        except Exception as e:
            print(f"SerpAPI failed: {e}. Falling back to DuckDuckGo.")
            return await _duckduckgo_search(query, max_results)
    else:
        return await _duckduckgo_search(query, max_results)


async def _duckduckgo_search(query: str, max_results: int) -> list[dict]:
    from duckduckgo_search import DDGS
    loop = asyncio.get_event_loop()

    def _call():
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in results
        ]

    return await loop.run_in_executor(None, _call)


async def _serpapi_search(query: str, max_results: int, api_key: str) -> list[dict]:
    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": api_key, "num": max_results, "engine": "google"},
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("organic_results", [])
        return [
            {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
            for r in results[:max_results]
        ]


def format_results_as_text(results: list[dict]) -> str:
    """Format search results into a readable text block for LLM consumption."""
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}")
        lines.append(f"    URL: {r['url']}")
        lines.append(f"    {r['snippet']}")
        lines.append("")
    return "\n".join(lines)
