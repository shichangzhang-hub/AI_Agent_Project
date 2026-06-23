from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from smart_ticket_agent.agent import AgentConfigError, AgentRuntimeError, handle_chat_message
from smart_ticket_agent.database import get_db, init_database
from smart_ticket_agent.schemas import (
    BudgetResponse,
    ChatRequest,
    ChatResponse,
    EmployeeSummary,
    TicketCreateRequest,
    TicketResponse,
)
from smart_ticket_agent.service import ServiceError, create_ticket, get_employee_budget, list_employees


app = FastAPI(
    title="智能工单 Agent",
    version="2.0.0",
    description="企业智能工单与报销 Agent 的云端 API。",
)

init_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

public_dir = Path(__file__).resolve().parent.parent / "public"
default_home_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>智能工单 Agent</title>
</head>
<body>
  <h1>智能工单 Agent</h1>
  <p>请打开 public/index.html 使用完整前端页面。</p>
</body>
</html>
""".strip()

home_html = (
    (public_dir / "index.html").read_text(encoding="utf-8")
    if (public_dir / "index.html").exists()
    else default_home_html
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index() -> HTMLResponse:
    return HTMLResponse(home_html)


@app.get("/api/employees", response_model=list[EmployeeSummary])
def employee_list(db: Session = Depends(get_db)) -> list[EmployeeSummary]:
    return list_employees(db)


@app.get("/api/budgets/{employee_name}", response_model=BudgetResponse)
def budget_query(employee_name: str, db: Session = Depends(get_db)) -> BudgetResponse:
    try:
        return get_employee_budget(db, employee_name)
    except ServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/tickets", response_model=TicketResponse)
def ticket_create(
    payload: TicketCreateRequest,
    db: Session = Depends(get_db),
) -> TicketResponse:
    try:
        result = create_ticket(db, payload)
        db.commit()
        return result
    except ServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    try:
        result = handle_chat_message(payload.message, db, payload.session_id)
        db.commit()
        return result
    except (AgentConfigError, AgentRuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if public_dir.exists():
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
