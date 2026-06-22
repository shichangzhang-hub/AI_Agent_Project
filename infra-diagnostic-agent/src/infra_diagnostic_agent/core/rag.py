"""Minimal local RAG utilities backed by NumPy cosine similarity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


EmbeddingFunction = Callable[[str], list[float]]


@dataclass(frozen=True)
class DocumentChunk:
    """A retrievable text fragment derived from a source document."""

    text: str
    source_index: int
    chunk_index: int


@dataclass(frozen=True)
class RetrievalResult:
    """Search result with text payload and cosine similarity score."""

    text: str
    score: float
    index: int
    source_index: int
    chunk_index: int


@dataclass(frozen=True)
class RagIndex:
    """In-memory index of chunks and their embeddings."""

    chunks: list[DocumentChunk]
    embeddings: np.ndarray
    norms: np.ndarray
    dimension: int


def get_embedding(text: str) -> list[float]:
    """Placeholder embedding hook for future API integration.

    Replace this implementation with a real embedding call in later stages.
    """
    raise NotImplementedError(
        "get_embedding(text) is a placeholder. Inject a real embedding function into build_index() and search()."
    )


def chunk_documents(
    documents: list[str],
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[DocumentChunk]:
    """Split documents into overlapping character windows.

    This keeps the implementation lightweight and deterministic while still
    preserving local context through overlap.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to 0.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    chunks: list[DocumentChunk] = []
    stride = chunk_size - overlap

    for source_index, document in enumerate(documents):
        if not isinstance(document, str):
            raise TypeError("Each document must be a string.")

        normalized = document.strip()
        if not normalized:
            continue

        chunk_index = 0
        for start in range(0, len(normalized), stride):
            piece = normalized[start : start + chunk_size].strip()
            if not piece:
                continue

            chunks.append(
                DocumentChunk(
                    text=piece,
                    source_index=source_index,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

            if start + chunk_size >= len(normalized):
                break

    return chunks


def _coerce_embedding(vector: list[float], expected_dim: int | None = None) -> np.ndarray:
    """Convert embedding output into a stable float32 NumPy vector."""
    array = np.asarray(vector, dtype=np.float32)
    if array.ndim != 1:
        raise ValueError("Embedding must be a one-dimensional vector.")
    if array.size == 0:
        raise ValueError("Embedding vector cannot be empty.")
    if expected_dim is not None and array.size != expected_dim:
        raise ValueError(
            f"Embedding dimension mismatch: expected {expected_dim}, got {array.size}."
        )
    return array


def build_index(
    chunks: list[DocumentChunk],
    embedding_fn: EmbeddingFunction = get_embedding,
) -> RagIndex:
    """Generate embeddings for chunks and store them in an in-memory index."""
    if not chunks:
        return RagIndex(
            chunks=[],
            embeddings=np.empty((0, 0), dtype=np.float32),
            norms=np.empty((0,), dtype=np.float32),
            dimension=0,
        )

    vectors: list[np.ndarray] = []
    dimension: int | None = None

    for chunk in chunks:
        vector = _coerce_embedding(embedding_fn(chunk.text), expected_dim=dimension)
        if dimension is None:
            dimension = int(vector.size)
        vectors.append(vector)

    embedding_matrix = np.vstack(vectors).astype(np.float32, copy=False)
    norms = np.linalg.norm(embedding_matrix, axis=1)

    return RagIndex(
        chunks=chunks,
        embeddings=embedding_matrix,
        norms=norms,
        dimension=dimension or 0,
    )


def search(
    query: str,
    index: RagIndex,
    embedding_fn: EmbeddingFunction = get_embedding,
    top_k: int = 3,
) -> list[RetrievalResult]:
    """Return the top-k most relevant chunks for a query."""
    if top_k <= 0:
        return []
    if not query or not query.strip():
        return []
    if not index.chunks or index.dimension == 0:
        return []

    query_vector = _coerce_embedding(embedding_fn(query), expected_dim=index.dimension)
    query_norm = float(np.linalg.norm(query_vector))
    if query_norm == 0.0:
        return []

    dot_products = index.embeddings @ query_vector
    denominator = index.norms * query_norm
    similarities = np.divide(
        dot_products,
        denominator,
        out=np.zeros_like(dot_products, dtype=np.float32),
        where=denominator > 0,
    )

    candidate_count = min(top_k, similarities.size)
    if candidate_count == 0:
        return []

    # argpartition is cheaper than a full sort for small top-k retrieval.
    top_indices = np.argpartition(-similarities, candidate_count - 1)[:candidate_count]
    sorted_indices = top_indices[np.argsort(-similarities[top_indices], kind="stable")]

    results: list[RetrievalResult] = []
    for chunk_position in sorted_indices.tolist():
        chunk = index.chunks[chunk_position]
        results.append(
            RetrievalResult(
                text=chunk.text,
                score=float(similarities[chunk_position]),
                index=chunk_position,
                source_index=chunk.source_index,
                chunk_index=chunk.chunk_index,
            )
        )

    return results
