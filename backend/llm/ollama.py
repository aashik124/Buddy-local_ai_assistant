import json
from collections.abc import AsyncIterator

import httpx

from backend.config import DEFAULT_MODEL, OLLAMA_CHAT_URL


async def stream_chat(messages: list[dict], model: str = DEFAULT_MODEL) -> AsyncIterator[str]:
    payload = {
        "model": model,
        "stream": True,
        "messages": messages,
    }

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", OLLAMA_CHAT_URL, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line.removeprefix("data:").strip()
                if raw == "[DONE]":
                    break
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                delta = data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content


async def complete_chat(messages: list[dict], model: str = DEFAULT_MODEL) -> str:
    parts = []
    async for chunk in stream_chat(messages, model=model):
        parts.append(chunk)
    return "".join(parts).strip()
