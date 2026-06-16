from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from smart_ticket_agent.database import init_database


def setup_database() -> None:
    init_database()
    print("数据库初始化完成。")


if __name__ == "__main__":
    setup_database()
