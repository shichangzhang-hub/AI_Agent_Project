from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from smart_ticket_agent.database import EmployeeBudget, Ticket
from smart_ticket_agent.schemas import BudgetResponse, TicketCreateRequest, TicketResponse


class ServiceError(Exception):
    pass


def get_employee_budget(session: Session, employee_name: str) -> BudgetResponse:
    budget = session.scalar(
        select(EmployeeBudget).where(EmployeeBudget.employee_name == employee_name)
    )
    if budget is None:
        raise ServiceError(f"未找到员工 {employee_name} 的预算信息，请确认姓名是否正确。")

    return BudgetResponse(
        employee_name=employee_name,
        remaining_budget=budget.remaining_budget,
        message=f"员工 {employee_name} 当前剩余报销额度为 {budget.remaining_budget:.2f} 元。",
    )


def create_ticket(session: Session, request: TicketCreateRequest) -> TicketResponse:
    amount = request.amount if request.issue_type == "财务报销" else 0

    if request.issue_type == "财务报销":
        budget = session.scalar(
            select(EmployeeBudget).where(EmployeeBudget.employee_name == request.employee_name)
        )
        if budget is None:
            raise ServiceError("提交失败：未找到该员工的财务账户。")
        if budget.remaining_budget < amount:
            raise ServiceError(
                f"提交失败：额度不足。当前仅剩 {budget.remaining_budget:.2f} 元，无法报销 {amount:.2f} 元。"
            )
        budget.remaining_budget -= amount

    ticket = Ticket(
        employee_name=request.employee_name,
        issue_type=request.issue_type,
        description=request.description,
        amount=amount,
        status="已提交",
    )
    session.add(ticket)
    session.flush()

    return TicketResponse(
        ticket_id=ticket.ticket_id,
        employee_name=ticket.employee_name,
        issue_type=ticket.issue_type,
        description=ticket.description,
        amount=ticket.amount,
        status=ticket.status,
        message=(
            f"工单已创建，单号为 {ticket.ticket_id}。"
            if request.issue_type == "IT报修"
            else f"报销工单已创建，单号为 {ticket.ticket_id}，金额 {amount:.2f} 元。"
        ),
    )
