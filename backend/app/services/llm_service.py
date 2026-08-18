"""Thin wrapper around the OpenAI API.

Phase 2 modules (Chat Copilot, Code-RAG, command parsing for Design
Generation) call these functions rather than instantiating an OpenAI
client directly, so the API key, model names, and error handling stay in
one place.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from openai import APIError, AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Return a lazily-initialized, process-wide `AsyncOpenAI` client.

    Lazy init means importing this module never fails even if
    `OPENAI_API_KEY` is unset (useful for Phase 1 boot/tests); the error
    surfaces only when a call is actually attempted.
    """
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is not set; LLM calls will fail until it is configured.")
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def chat_completion(
    messages: Sequence[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    tools: Sequence[dict[str, Any]] | None = None,
) -> str:
    """Request a chat completion and return the assistant's text content.

    `messages` follows the OpenAI chat format: `[{"role": "user", "content": "..."}]`.
    `tools` (OpenAI function/tool-calling schema) is accepted for Phase 2's
    command-parsing use case (Design Generation) but not yet consumed
    beyond being passed through.
    """
    settings = get_settings()
    client = get_client()
    try:
        response = await client.chat.completions.create(
            model=model or settings.OPENAI_CHAT_MODEL,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,  # type: ignore[arg-type]
        )
    except APIError:
        logger.exception("OpenAI chat completion request failed")
        raise

    content = response.choices[0].message.content
    return content or ""


async def create_embedding(text: str, *, model: str | None = None) -> list[float]:
    """Return the embedding vector for `text`, used by Code-RAG ingestion/search."""
    settings = get_settings()
    client = get_client()
    try:
        response = await client.embeddings.create(
            model=model or settings.OPENAI_EMBEDDING_MODEL,
            input=text,
        )
    except APIError:
        logger.exception("OpenAI embedding request failed")
        raise

    return response.data[0].embedding


async def create_embeddings_batch(texts: Sequence[str], *, model: str | None = None) -> list[list[float]]:
    """Return embedding vectors for a batch of texts (Code-RAG bulk ingestion)."""
    settings = get_settings()
    client = get_client()
    try:
        response = await client.embeddings.create(
            model=model or settings.OPENAI_EMBEDDING_MODEL,
            input=list(texts),
        )
    except APIError:
        logger.exception("OpenAI batch embedding request failed")
        raise

    return [item.embedding for item in response.data]
