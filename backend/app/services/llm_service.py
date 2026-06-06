from __future__ import annotations
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def openai_llm_rewrite(
    section_heading: str,
    original_content: str,
    diff_context: str,
    api_key: str,
    model: str,
) -> str:
    """Request a rewrite from an LLM provider using the provided API key."""
    if not api_key:
        raise ValueError("LLM API key is required for real LLM rewrites")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful technical writing assistant. "
                "Rewrite the documentation section to reflect the code changes described in the diff context. "
                "Keep Markdown formatting and preserve the original meaning while making the text current."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Section heading: {section_heading}\n\n"
                f"Original documentation:\n{original_content}\n\n"
                f"Code diff context:\n{diff_context}\n\n"
                "Please return a revised documentation section only, without commentary."
            ),
        },
    ]

    url = f"{settings.LLM_API_BASE}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 800,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.exception("LLM rewrite request failed")
        return original_content


async def choose_llm_rewrite(
    section_heading: str,
    original_content: str,
    diff_context: str,
    api_key: Optional[str],
) -> str:
    """Use a real LLM if an API key is provided, otherwise return an empty string to let caller decide."""
    if not api_key:
        raise ValueError("No API key provided")

    return await openai_llm_rewrite(
        section_heading,
        original_content,
        diff_context,
        api_key,
        settings.LLM_MODEL,
    )
