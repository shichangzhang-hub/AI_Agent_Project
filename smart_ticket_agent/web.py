from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from smart_ticket_agent.agent import AgentConfigError, AgentRuntimeError, handle_chat_message
from smart_ticket_agent.database import get_db, init_database
from smart_ticket_agent.schemas import (
    BudgetResponse,
    ChatRequest,
    ChatResponse,
    TicketCreateRequest,
    TicketResponse,
)
from smart_ticket_agent.service import ServiceError, create_ticket, get_employee_budget


app = FastAPI(
    title="智能工单 Agent",
    version="1.0.0",
    description="企业智能工单 Agent 的云端 API。",
)

init_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


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
        result = handle_chat_message(payload.message, db)
        db.commit()
        return result
    except (AgentConfigError, AgentRuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


public_dir = Path(__file__).resolve().parent.parent / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
