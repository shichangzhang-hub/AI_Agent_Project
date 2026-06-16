from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from smart_ticket_agent.config import default_sqlite_url, settings


class Base(DeclarativeBase):
    pass


class EmployeeBudget(Base):
    __tablename__ = "employee_budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    remaining_budget: Mapped[float] = mapped_column(Float, nullable=False)


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="已提交")


DATABASE_URL = settings.database_url or default_sqlite_url()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

DEFAULT_BUDGETS = [
    ("张三", 2000.0),
    ("李四", 500.0),
]


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    with session_scope() as session:
        existing = session.scalar(select(EmployeeBudget.id).limit(1))
        if existing is not None:
            return

        session.add_all(
            EmployeeBudget(employee_name=name, remaining_budget=budget)
            for name, budget in DEFAULT_BUDGETS
        )


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
