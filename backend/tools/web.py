"""Real web search using DuckDuckGo (no API key required)."""
from __future__ import annotations

import asyncio

from ddgs import DDGS


def _search_sync(query: str, max_results: int) -> list[dict]:
    with DDGS() as ddgs:
        raw = list(ddgs.text(query, max_results=max_results))
    return [
        {
            "title": item.get("title", ""),
            "snippet": item.get("body", ""),
            "url": item.get("href", ""),
        }
        for item in raw
    ]


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Runs the (blocking) DuckDuckGo search in a thread so it doesn't block the event loop."""
    try:
        return await asyncio.to_thread(_search_sync, query, max_results)
    except Exception as exc:
        return [{"title": "Search failed", "snippet": str(exc), "url": ""}]


def format_results_for_prompt(results: list[dict]) -> str:
    if not results:
        return "No web results found."
    lines = []
    for item in results:
        title = item.get("title") or "Untitled"
        snippet = item.get("snippet") or ""
        url = item.get("url") or ""
        lines.append(f"- {title}: {snippet} ({url})")
    return "\n".join(lines)
