from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from smart_ticket_agent.database import init_database, session_scope
from smart_ticket_agent.schemas import TicketCreateRequest
from smart_ticket_agent.service import (
    ServiceError,
    create_ticket as service_create_ticket,
    get_employee_budget as service_get_employee_budget,
)


def get_employee_budget_text(employee_name: str) -> str:
    init_database()
    with session_scope() as session:
        try:
            result = service_get_employee_budget(session, employee_name)
            return result.message
        except ServiceError as exc:
            return str(exc)


def submit_ticket(employee_name: str, issue_type: str, description: str, amount: float = 0) -> str:
    init_database()
    with session_scope() as session:
        try:
            result = service_create_ticket(
                session,
                TicketCreateRequest(
                    employee_name=employee_name,
                    issue_type=issue_type,
                    description=description,
                    amount=amount,
                ),
            )
            return result.message
        except ServiceError as exc:
            return str(exc)


get_employee_budget = get_employee_budget_text


if __name__ == "__main__":
    print("--- 本地数据库工具测试 ---")
    print(get_employee_budget("张三"))
    print(submit_ticket("张三", "财务报销", "上周加班打车", 150))
    print(get_employee_budget("张三"))
    print(submit_ticket("李四", "IT报修", "电脑频繁蓝屏", 0))
