from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


IssueType = Literal["IT报修", "财务报销"]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="员工自然语言消息")
    session_id: str | None = Field(default=None, description="同一会话的唯一标识")


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    action: str | None = None
    tool_result: dict[str, Any] | None = None


class EmployeeSummary(BaseModel):
    employee_name: str
    department: str
    title: str
    manager_name: str
    remaining_budget: float
    reimbursement_limit: float


class BudgetResponse(BaseModel):
    employee_name: str
    department: str
    title: str
    manager_name: str
    monthly_budget: float
    remaining_budget: float
    reimbursement_limit: float
    message: str


class TicketCreateRequest(BaseModel):
    employee_name: str = Field(..., min_length=1)
    issue_type: IssueType
    description: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(default=0, ge=0)
    expense_category: str | None = Field(default=None, max_length=80)
    expense_date: str | None = Field(default=None, max_length=40)
    vendor: str | None = Field(default=None, max_length=120)
    receipt_attached: bool = False
    session_id: str | None = None


class TicketResponse(BaseModel):
    ticket_id: int
    employee_name: str
    issue_type: IssueType
    description: str
    amount: float
    status: str
    workflow_stage: str
    approval_required: bool
    approver_name: str | None = None
    expense_category: str | None = None
    expense_date: str | None = None
    vendor: str | None = None
    receipt_attached: bool
    message: str
