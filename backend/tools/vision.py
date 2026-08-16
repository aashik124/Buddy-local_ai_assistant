"""Local image understanding using a vision-capable Ollama model.

Requires a multimodal model pulled in Ollama, e.g.:
    ollama pull llava
    ollama pull qwen2.5vl:7b
    ollama pull moondream   (very small/fast, good for quick captions)

Uses the same OpenAI-compatible /v1/chat/completions endpoint as the text
LLM, but sends the image as a base64 data URL inside the message content.
"""
from __future__ import annotations

import base64

import httpx

from backend.config import OLLAMA_CHAT_URL

VISION_MODEL = "llava"


async def describe_image(image_bytes: bytes, question: str = "Describe this image in detail.",
                          mime_type: str = "image/jpeg", model: str = VISION_MODEL) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64}"

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(OLLAMA_CHAT_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        return "The vision model returned no response."
    return choices[0].get("message", {}).get("content", "").strip() or "The vision model returned an empty response."
