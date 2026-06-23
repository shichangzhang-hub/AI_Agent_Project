from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from openai import APIConnectionError, APIStatusError, OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from smart_ticket_agent.config import settings
from smart_ticket_agent.database import ConversationTurn
from smart_ticket_agent.schemas import ChatResponse, TicketCreateRequest
from smart_ticket_agent.service import ServiceError, create_ticket, get_employee_budget, list_employees


SYSTEM_PROMPT = """
你是企业内部的智能工单与报销助理。

你的工作规则：
1. 必须结合当前会话历史理解用户补充信息，不能把每一句都当成全新需求。
2. 查询预算时调用 check_budget。
3. 用户不确定员工姓名、想看可用员工时调用 list_employees。
4. IT 报修和财务报销都通过 create_ticket 提交。
5. 财务报销至少需要这些字段：员工姓名、报销金额、报销事由、报销类别、消费日期、消费对象/供应商、是否有凭证。
6. 如果信息不足，直接中文追问，不能编造。
7. 如果用户是在补充上一轮缺失的信息，要把前文已有信息一起带上再决定是否调用工具。
8. 回复保持简洁、专业，适合企业内部员工阅读。
""".strip()


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_budget",
            "description": "查询某位员工当前剩余报销额度和免审批额度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name": {
                        "type": "string",
                        "description": "员工姓名，例如：张三",
                    }
                },
                "required": ["employee_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_employees",
            "description": "列出当前系统中的员工，用于用户不确定姓名或想查看可用员工时。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "提交 IT 报修或财务报销工单。",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name": {"type": "string", "description": "员工姓名"},
                    "issue_type": {
                        "type": "string",
                        "enum": ["IT报修", "财务报销"],
                        "description": "工单类型",
                    },
                    "description": {
                        "type": "string",
                        "description": "IT 问题描述或报销事由",
                    },
                    "amount": {
                        "type": "number",
                        "description": "报销金额；如果是 IT 报修则填写 0",
                    },
                    "expense_category": {
                        "type": "string",
                        "description": "报销类别，例如交通、差旅、办公用品",
                    },
                    "expense_date": {
                        "type": "string",
                        "description": "消费日期，例如 2026-06-20",
                    },
                    "vendor": {
                        "type": "string",
                        "description": "消费对象、商家或供应商名称",
                    },
                    "receipt_attached": {
                        "type": "boolean",
                        "description": "是否已提供发票或凭证",
                    },
                },
                "required": ["employee_name", "issue_type", "description", "amount", "receipt_attached"],
            },
        },
    },
]


class AgentConfigError(Exception):
    pass


class AgentRuntimeError(Exception):
    pass


def _build_client() -> OpenAI:
    if not settings.openai_api_key:
        raise AgentConfigError("未配置 OPENAI_API_KEY，当前无法使用对话式 Agent。")
    return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)


def _tool_result_text(result: dict[str, Any]) -> str:
    if "message" in result:
        return str(result["message"])
    return json.dumps(result, ensure_ascii=False)


def _load_history(session: Session, session_id: str, limit: int = 12) -> list[dict[str, str]]:
    turns = session.scalars(
        select(ConversationTurn)
        .where(ConversationTurn.session_id == session_id)
        .order_by(ConversationTurn.id.desc())
        .limit(limit)
    ).all()
    return [
        {"role": turn.role, "content": turn.content}
        for turn in reversed(turns)
    ]


def _save_turn(session: Session, session_id: str, role: str, content: str) -> None:
    if not content:
        return
    session.add(
        ConversationTurn(
            session_id=session_id,
            role=role,
            content=content[:4000],
        )
    )


def handle_chat_message(user_message: str, session: Session, session_id: str | None = None) -> ChatResponse:
    client = _build_client()
    current_session_id = session_id or uuid4().hex
    history = _load_history(session, current_session_id)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_message},
    ]

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
    except (APIConnectionError, APIStatusError) as exc:
        raise AgentRuntimeError("模型服务暂时不可用，请稍后重试。") from exc

    ai_message = response.choices[0].message

    if not ai_message.tool_calls:
        reply = ai_message.content or "请提供更多信息。"
        _save_turn(session, current_session_id, "user", user_message)
        _save_turn(session, current_session_id, "assistant", reply)
        return ChatResponse(reply=reply, session_id=current_session_id)

    tool_result: dict[str, Any] | None = None
    action: str | None = None
    tool_payloads: list[dict[str, Any]] = []

    for tool_call in ai_message.tool_calls:
        arguments = json.loads(tool_call.function.arguments or "{}")
        if tool_call.function.name == "check_budget":
            result_model = get_employee_budget(session, arguments["employee_name"])
            tool_result = result_model.model_dump()
            action = "check_budget"
        elif tool_call.function.name == "list_employees":
            employees = list_employees(session)
            tool_result = {
                "employees": [employee.model_dump() for employee in employees],
                "message": "当前系统中的员工包括："
                + "、".join(employee.employee_name for employee in employees),
            }
            action = "list_employees"
        elif tool_call.function.name == "create_ticket":
            request = TicketCreateRequest(**arguments, session_id=current_session_id)
            result_model = create_ticket(session, request)
            tool_result = result_model.model_dump()
            action = "create_ticket"
        else:
            raise ServiceError(f"未知工具调用：{tool_call.function.name}")

        tool_payloads.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result, ensure_ascii=False),
            }
        )

    messages.append(
        {
            "role": "assistant",
            "content": ai_message.content or "",
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in ai_message.tool_calls
            ],
        }
    )
    messages.extend(tool_payloads)

    try:
        final_response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
        )
        reply = final_response.choices[0].message.content or _tool_result_text(tool_result or {})
    except (APIConnectionError, APIStatusError):
        reply = _tool_result_text(tool_result or {})

    _save_turn(session, current_session_id, "user", user_message)
    _save_turn(session, current_session_id, "assistant", reply)

    return ChatResponse(
        reply=reply,
        session_id=current_session_id,
        action=action,
        tool_result=tool_result,
    )
