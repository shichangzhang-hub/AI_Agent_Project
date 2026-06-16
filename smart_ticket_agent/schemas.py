from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


IssueType = Literal["IT报修", "财务报销"]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="员工自然语言消息")


class ChatResponse(BaseModel):
    reply: str
    action: str | None = None
    tool_result: dict[str, Any] | None = None


class BudgetResponse(BaseModel):
    employee_name: str
    remaining_budget: float
    message: str


class TicketCreateRequest(BaseModel):
    employee_name: str = Field(..., min_length=1)
    issue_type: IssueType
    description: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(default=0, ge=0)


class TicketResponse(BaseModel):
    ticket_id: int
    employee_name: str
    issue_type: IssueType
    description: str
    amount: float
    status: str
    message: str
