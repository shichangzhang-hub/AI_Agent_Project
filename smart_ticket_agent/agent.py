from __future__ import annotations

import json
from typing import Any

from openai import APIConnectionError, APIStatusError, OpenAI

from smart_ticket_agent.config import settings
from smart_ticket_agent.schemas import ChatResponse, TicketCreateRequest
from smart_ticket_agent.service import ServiceError, create_ticket, get_employee_budget


SYSTEM_PROMPT = """
你是企业内部的智能工单助理。
你的职责：
1. 查询员工预算时，调用 check_budget。
2. 员工明确要提交 IT 报修或财务报销时，调用 create_ticket。
3. 财务报销必须收集完整的员工姓名、金额、报销事由后才能调用 create_ticket。
4. 如果信息不足，直接用中文追问，不要编造数据。
5. 回复必须简洁、专业、适合企业内部员工阅读。
""".strip()


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_budget",
            "description": "当员工想查询剩余报销额度时调用。",
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
            "name": "create_ticket",
            "description": "当员工要提交 IT 报修或财务报销工单时调用。",
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
                        "description": "具体问题或报销事由",
                    },
                    "amount": {
                        "type": "number",
                        "description": "报销金额；如果是 IT 报修则填写 0",
                    },
                },
                "required": ["employee_name", "issue_type", "description", "amount"],
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


def handle_chat_message(user_message: str, session) -> ChatResponse:
    client = _build_client()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
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
        return ChatResponse(reply=ai_message.content or "请提供更多信息。")

    tool_result: dict[str, Any] | None = None
    action: str | None = None
    tool_payloads: list[dict[str, Any]] = []

    for tool_call in ai_message.tool_calls:
        arguments = json.loads(tool_call.function.arguments or "{}")
        if tool_call.function.name == "check_budget":
            result_model = get_employee_budget(session, arguments["employee_name"])
            tool_result = result_model.model_dump()
            action = "check_budget"
        elif tool_call.function.name == "create_ticket":
            request = TicketCreateRequest(**arguments)
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

    return ChatResponse(reply=reply, action=action, tool_result=tool_result)
