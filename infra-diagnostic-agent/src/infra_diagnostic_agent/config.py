import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def get_env(name: str, default: str = "") -> str:
    """Return an environment variable with a default fallback."""
    return os.getenv(name, default)


@dataclass(frozen=True)
class ExecutionSettings:
    """Runtime settings for the controlled command executor."""

    default_timeout_seconds: int = int(get_env("COMMAND_TIMEOUT_SECONDS", "10"))


@dataclass(frozen=True)
class AgentSettings:
    """Runtime settings for the ReAct agent loop and LLM integration."""

    openai_api_key: str = get_env("OPENAI_API_KEY", "")
    openai_base_url: str = get_env("OPENAI_BASE_URL", "")
    openai_model: str = get_env("OPENAI_MODEL", "gpt-4.1-mini")
    max_history_entries: int = int(get_env("AGENT_HISTORY_MAX_ENTRIES", "12"))
    max_history_characters: int = int(get_env("AGENT_HISTORY_MAX_CHARACTERS", "5000"))


@dataclass(frozen=True)
class EmbeddingSettings:
    """Runtime settings for the embedding backend."""

    backend: str = get_env("EMBEDDING_BACKEND", "local")
    openai_model: str = get_env("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    local_dimensions: int = int(get_env("LOCAL_EMBEDDING_DIMENSIONS", "256"))


@dataclass(frozen=True)
class KnowledgeBaseSettings:
    """Runtime settings for loading and chunking local knowledge-base docs."""

    knowledge_base_dir: Path = BASE_DIR / "data" / "knowledge_base"
    chunk_size: int = int(get_env("RAG_CHUNK_SIZE", "800"))
    chunk_overlap: int = int(get_env("RAG_CHUNK_OVERLAP", "120"))


execution_settings = ExecutionSettings()
agent_settings = AgentSettings()
embedding_settings = EmbeddingSettings()
knowledge_base_settings = KnowledgeBaseSettings()
