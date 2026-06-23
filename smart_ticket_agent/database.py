from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import Boolean, DateTime, Float, Integer, String, create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from smart_ticket_agent.config import default_sqlite_url, settings


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    manager_name: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_budget: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_budget: Mapped[float] = mapped_column(Float, nullable=False)
    reimbursement_limit: Mapped[float] = mapped_column(Float, nullable=False, default=1000)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="已提交")
    expense_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expense_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    receipt_attached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approver_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    workflow_stage: Mapped[str] = mapped_column(String(50), nullable=False, default="待处理")
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


DATABASE_URL = settings.database_url or default_sqlite_url()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

DEFAULT_EMPLOYEES = [
    {
        "employee_name": "张三",
        "department": "技术部",
        "title": "后端开发工程师",
        "manager_name": "王敏",
        "monthly_budget": 3000.0,
        "remaining_budget": 2200.0,
        "reimbursement_limit": 1200.0,
    },
    {
        "employee_name": "李四",
        "department": "市场部",
        "title": "招商主管",
        "manager_name": "周洁",
        "monthly_budget": 1800.0,
        "remaining_budget": 650.0,
        "reimbursement_limit": 800.0,
    },
    {
        "employee_name": "王五",
        "department": "销售部",
        "title": "客户经理",
        "manager_name": "赵磊",
        "monthly_budget": 2500.0,
        "remaining_budget": 1600.0,
        "reimbursement_limit": 1000.0,
    },
    {
        "employee_name": "赵六",
        "department": "财务部",
        "title": "财务专员",
        "manager_name": "陈晨",
        "monthly_budget": 1200.0,
        "remaining_budget": 1200.0,
        "reimbursement_limit": 500.0,
    },
    {
        "employee_name": "孙七",
        "department": "行政部",
        "title": "行政主管",
        "manager_name": "刘芳",
        "monthly_budget": 1500.0,
        "remaining_budget": 900.0,
        "reimbursement_limit": 700.0,
    },
    {
        "employee_name": "周八",
        "department": "产品部",
        "title": "产品经理",
        "manager_name": "吴凯",
        "monthly_budget": 2800.0,
        "remaining_budget": 2100.0,
        "reimbursement_limit": 1000.0,
    },
]


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_existing_ticket_table()
    _seed_employees()


def _migrate_existing_ticket_table() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "tickets" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("tickets")}
    additions = {
        "expense_category": "ALTER TABLE tickets ADD COLUMN expense_category VARCHAR(80)",
        "expense_date": "ALTER TABLE tickets ADD COLUMN expense_date VARCHAR(40)",
        "vendor": "ALTER TABLE tickets ADD COLUMN vendor VARCHAR(120)",
        "receipt_attached": "ALTER TABLE tickets ADD COLUMN receipt_attached BOOLEAN DEFAULT 0 NOT NULL",
        "approval_required": "ALTER TABLE tickets ADD COLUMN approval_required BOOLEAN DEFAULT 0 NOT NULL",
        "approver_name": "ALTER TABLE tickets ADD COLUMN approver_name VARCHAR(100)",
        "workflow_stage": "ALTER TABLE tickets ADD COLUMN workflow_stage VARCHAR(50) DEFAULT '待处理' NOT NULL",
        "session_id": "ALTER TABLE tickets ADD COLUMN session_id VARCHAR(64)",
        "created_at": "ALTER TABLE tickets ADD COLUMN created_at DATETIME",
    }

    with engine.begin() as connection:
        for column_name, statement in additions.items():
            if column_name not in columns:
                connection.execute(text(statement))

        connection.execute(
            text(
                "UPDATE tickets SET workflow_stage = COALESCE(workflow_stage, '待处理'), "
                "created_at = COALESCE(created_at, CURRENT_TIMESTAMP)"
            )
        )


def _seed_employees() -> None:
    with session_scope() as session:
        existing_names = {
            row[0]
            for row in session.execute(select(Employee.employee_name))
        }
        for employee in DEFAULT_EMPLOYEES:
            if employee["employee_name"] in existing_names:
                continue
            session.add(Employee(**employee))


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
