"""Search helper that exposes local RAG retrieval as a tool."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from infra_diagnostic_agent.config import knowledge_base_settings
from infra_diagnostic_agent.core.embeddings import get_default_embedding_function
from infra_diagnostic_agent.core.knowledge_base import load_markdown_documents
from infra_diagnostic_agent.core.rag import (
    RagIndex,
    RetrievalResult,
    build_index,
    chunk_documents,
    search,
)


EmbeddingFunction = Callable[[str], list[float]]

_configured_index: RagIndex | None = None
_configured_embedding_fn: EmbeddingFunction | None = None
_configured_sources: list[str] = []


def configure_doc_search(
    index: RagIndex,
    embedding_fn: EmbeddingFunction,
    source_labels: list[str] | None = None,
) -> None:
    """Register the in-memory document index used by search_docs()."""
    global _configured_index, _configured_embedding_fn, _configured_sources
    _configured_index = index
    _configured_embedding_fn = embedding_fn
    _configured_sources = list(source_labels or [])


def clear_doc_search() -> None:
    """Remove the currently configured search index."""
    global _configured_index, _configured_embedding_fn, _configured_sources
    _configured_index = None
    _configured_embedding_fn = None
    _configured_sources = []


def bootstrap_doc_search(knowledge_base_dir: Path | None = None) -> str:
    """Load Markdown docs, build an index, and register it for search."""
    base_dir = knowledge_base_dir or knowledge_base_settings.knowledge_base_dir
    documents = load_markdown_documents(base_dir)
    if not documents:
        clear_doc_search()
        return f"No Markdown knowledge-base documents found in {base_dir}."

    embedding_fn = get_default_embedding_function()
    chunks = chunk_documents(
        [document.text for document in documents],
        chunk_size=knowledge_base_settings.chunk_size,
        overlap=knowledge_base_settings.chunk_overlap,
    )
    index = build_index(chunks, embedding_fn=embedding_fn)
    configure_doc_search(
        index=index,
        embedding_fn=embedding_fn,
        source_labels=[document.source_name for document in documents],
    )
    return (
        "Knowledge base ready: "
        f"{len(documents)} documents, {len(chunks)} chunks, "
        f"backend={get_default_embedding_function().__name__}."
    )


def _format_results(results: list[RetrievalResult]) -> str:
    """Format retrieval results for Agent observations."""
    if not results:
        return "No relevant documentation snippets were found."

    lines: list[str] = []
    for position, result in enumerate(results, start=1):
        source_label = (
            _configured_sources[result.source_index]
            if 0 <= result.source_index < len(_configured_sources)
            else f"source-{result.source_index}"
        )
        lines.append(
            f"[{position}] score={result.score:.4f} source={source_label} "
            f"chunk={result.chunk_index} text={result.text}"
        )
    return "\n".join(lines)


def search_docs(query: str) -> str:
    """Search the configured local document index."""
    if not query or not query.strip():
        return "Query is empty. Provide an error message or diagnostic question."
    if _configured_index is None or _configured_embedding_fn is None:
        bootstrap_message = bootstrap_doc_search()
        if _configured_index is None or _configured_embedding_fn is None:
            return bootstrap_message

    results = search(
        query=query,
        index=_configured_index,
        embedding_fn=_configured_embedding_fn,
        top_k=3,
    )
    return _format_results(results)
