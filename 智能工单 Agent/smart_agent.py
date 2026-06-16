from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from smart_ticket_agent.agent import AgentConfigError, handle_chat_message
from smart_ticket_agent.database import init_database, session_scope
from smart_ticket_agent.service import ServiceError


def chat_with_agent(user_message: str) -> None:
    init_database()
    print(f"\n员工消息：{user_message}")
    with session_scope() as session:
        try:
            result = handle_chat_message(user_message, session)
            print(f"Agent 回复：{result.reply}")
            if result.tool_result:
                print(f"动作：{result.action}")
                print(f"结果：{result.tool_result}")
        except (AgentConfigError, ServiceError) as exc:
            print(f"处理失败：{exc}")


if __name__ == "__main__":
    print("=== 企业智能工单 Agent 已启动 ===")
    chat_with_agent("我是李四，帮我查一下我还剩多少报销额度")
    chat_with_agent("我是李四，刚买办公用品花了 200 元，帮我报销一下")
    chat_with_agent("我是张三，电脑频繁蓝屏，帮我提交一个 IT 报修工单")
