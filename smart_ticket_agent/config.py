from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
    openai_model: str = os.getenv("OPENAI_MODEL", "glm-4-flash")
    database_url: str = os.getenv("DATABASE_URL", "")


def default_sqlite_url() -> str:
    if os.getenv("VERCEL"):
        data_dir = Path(tempfile.gettempdir()) / "smart_ticket_agent"
    else:
        data_dir = Path.cwd() / "tmp"

    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'company_data.db').as_posix()}"


settings = Settings()
