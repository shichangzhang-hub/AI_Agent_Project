"""Embedding backends for local RAG indexing."""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache

import numpy as np
from openai import OpenAI

from infra_diagnostic_agent.config import agent_settings, embedding_settings


def _tokenize(text: str) -> list[str]:
    """Tokenize text into stable units for the local fallback embedding."""
    lowered = text.lower()
    word_tokens = re.findall(r"[a-z0-9_./:-]+", lowered)
    if word_tokens:
        return word_tokens
    return [character for character in lowered if not character.isspace()]


def local_hash_embedding(text: str, dimensions: int | None = None) -> list[float]:
    """Deterministic local embedding for offline demos and tests.

    This is not a semantic embedding model. It is a lightweight fallback so the
    project can still demonstrate chunking and retrieval without external APIs.
    """
    embedding_dimensions = dimensions or embedding_settings.local_dimensions
    if embedding_dimensions <= 0:
        raise ValueError("Embedding dimensions must be greater than 0.")

    vector = np.zeros(embedding_dimensions, dtype=np.float32)
    tokens = _tokenize(text)
    if not tokens:
        return vector.tolist()

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        primary_bucket = int.from_bytes(digest[:4], byteorder="big") % embedding_dimensions
        secondary_bucket = int.from_bytes(digest[4:8], byteorder="big") % embedding_dimensions
        vector[primary_bucket] += 1.0
        vector[secondary_bucket] += 0.5

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector /= norm
    return vector.tolist()


@lru_cache(maxsize=1)
def _get_openai_client() -> OpenAI:
    """Create and cache the OpenAI-compatible client."""
    if not agent_settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for the openai embedding backend.")

    client_kwargs: dict[str, str] = {"api_key": agent_settings.openai_api_key}
    if agent_settings.openai_base_url:
        client_kwargs["base_url"] = agent_settings.openai_base_url
    return OpenAI(**client_kwargs)


def openai_embedding(text: str) -> list[float]:
    """Generate an embedding using the configured OpenAI-compatible API."""
    client = _get_openai_client()
    response = client.embeddings.create(
        model=embedding_settings.openai_model,
        input=text,
    )
    return list(response.data[0].embedding)


def get_default_embedding_function():
    """Return the embedding function selected by configuration."""
    backend = embedding_settings.backend.strip().lower()
    if backend == "local":
        return local_hash_embedding
    if backend == "openai":
        return openai_embedding
    raise ValueError(f"Unsupported embedding backend: {embedding_settings.backend}")
