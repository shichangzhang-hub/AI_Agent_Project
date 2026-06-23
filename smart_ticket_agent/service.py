from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from smart_ticket_agent.database import Employee, Ticket
from smart_ticket_agent.schemas import BudgetResponse, EmployeeSummary, TicketCreateRequest, TicketResponse


class ServiceError(Exception):
    pass


def list_employees(session: Session) -> list[EmployeeSummary]:
    employees = session.scalars(
        select(Employee)
        .where(Employee.is_active.is_(True))
        .order_by(Employee.department, Employee.employee_name)
    ).all()
    return [
        EmployeeSummary(
            employee_name=employee.employee_name,
            department=employee.department,
            title=employee.title,
            manager_name=employee.manager_name,
            remaining_budget=employee.remaining_budget,
            reimbursement_limit=employee.reimbursement_limit,
        )
        for employee in employees
    ]


def get_employee_budget(session: Session, employee_name: str) -> BudgetResponse:
    employee = _get_employee(session, employee_name)
    return BudgetResponse(
        employee_name=employee.employee_name,
        department=employee.department,
        title=employee.title,
        manager_name=employee.manager_name,
        monthly_budget=employee.monthly_budget,
        remaining_budget=employee.remaining_budget,
        reimbursement_limit=employee.reimbursement_limit,
        message=(
            f"{employee.employee_name}，你属于{employee.department}，当前剩余报销额度为 "
            f"{employee.remaining_budget:.2f} 元，单笔免审批额度为 {employee.reimbursement_limit:.2f} 元。"
        ),
    )


def create_ticket(session: Session, request: TicketCreateRequest) -> TicketResponse:
    employee = _get_employee(session, request.employee_name)
    amount = request.amount if request.issue_type == "财务报销" else 0
    receipt_attached = bool(request.receipt_attached)

    status = "已提交"
    workflow_stage = "待处理"
    approval_required = False
    approver_name: str | None = None

    if request.issue_type == "财务报销":
        _validate_reimbursement_request(request)
        if amount > employee.remaining_budget:
            raise ServiceError(
                f"提交失败：当前剩余报销额度仅为 {employee.remaining_budget:.2f} 元，无法提交 {amount:.2f} 元报销。"
            )

        approval_required = amount > employee.reimbursement_limit
        if amount >= 1000 and not receipt_attached:
            raise ServiceError("提交失败：1000 元及以上报销必须上传或声明已附带发票/凭证。")

        if approval_required:
            status = "待审批"
            workflow_stage = "经理审批中"
            approver_name = employee.manager_name
        else:
            status = "已受理"
            workflow_stage = "财务处理中"
            approver_name = "财务专员"
            employee.remaining_budget -= amount
    else:
        status = "已提交"
        workflow_stage = "IT排队中"
        approver_name = "IT服务台"

    ticket = Ticket(
        employee_name=employee.employee_name,
        issue_type=request.issue_type,
        description=request.description,
        amount=amount,
        status=status,
        expense_category=request.expense_category,
        expense_date=request.expense_date,
        vendor=request.vendor,
        receipt_attached=receipt_attached,
        approval_required=approval_required,
        approver_name=approver_name,
        workflow_stage=workflow_stage,
        session_id=request.session_id,
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
        workflow_stage=ticket.workflow_stage,
        approval_required=ticket.approval_required,
        approver_name=ticket.approver_name,
        expense_category=ticket.expense_category,
        expense_date=ticket.expense_date,
        vendor=ticket.vendor,
        receipt_attached=ticket.receipt_attached,
        message=_build_ticket_message(ticket),
    )


def _get_employee(session: Session, employee_name: str) -> Employee:
    employee = session.scalar(
        select(Employee)
        .where(Employee.employee_name == employee_name, Employee.is_active.is_(True))
    )
    if employee is None:
        raise ServiceError(f"未找到员工 {employee_name}，请确认姓名是否正确。")
    return employee


def _validate_reimbursement_request(request: TicketCreateRequest) -> None:
    missing_fields: list[str] = []
    if not request.expense_category:
        missing_fields.append("报销类别")
    if not request.expense_date:
        missing_fields.append("消费日期")
    if not request.vendor:
        missing_fields.append("消费对象/供应商")
    if not request.description:
        missing_fields.append("报销事由")
    if request.amount <= 0:
        missing_fields.append("报销金额")

    if missing_fields:
        raise ServiceError(
            "提交财务报销前还缺少这些信息："
            + "、".join(missing_fields)
            + "。请补全后再提交。"
        )


def _build_ticket_message(ticket: Ticket) -> str:
    if ticket.issue_type == "IT报修":
        return (
            f"IT 工单已创建，单号 {ticket.ticket_id}。当前阶段：{ticket.workflow_stage}，"
            f"受理人：{ticket.approver_name}。"
        )

    if ticket.approval_required:
        return (
            f"报销单 {ticket.ticket_id} 已提交，金额 {ticket.amount:.2f} 元。"
            f"当前进入 {ticket.workflow_stage}，审批人：{ticket.approver_name}。"
        )

    return (
        f"报销单 {ticket.ticket_id} 已受理，金额 {ticket.amount:.2f} 元。"
        f"当前阶段：{ticket.workflow_stage}，预计由 {ticket.approver_name} 继续处理。"
    )
