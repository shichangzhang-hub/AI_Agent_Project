"""Helpers for loading local Markdown knowledge-base documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from infra_diagnostic_agent.config import knowledge_base_settings


@dataclass(frozen=True)
class KnowledgeBaseDocument:
    """Single Markdown document loaded from the knowledge base."""

    source_name: str
    path: Path
    text: str


def load_markdown_documents(directory: Path | None = None) -> list[KnowledgeBaseDocument]:
    """Load Markdown files from the configured knowledge-base directory."""
    base_dir = directory or knowledge_base_settings.knowledge_base_dir
    if not base_dir.exists():
        return []

    documents: list[KnowledgeBaseDocument] = []
    for path in sorted(base_dir.rglob("*.md")):
        if path.name.startswith("."):
            continue

        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        documents.append(
            KnowledgeBaseDocument(
                source_name=path.relative_to(base_dir).as_posix(),
                path=path,
                text=text,
            )
        )

    return documents
