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

public_dir = Path(__file__).resolve().parent.parent / "public"
default_home_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>智能工单 Agent</title>
  <style>
    body { margin: 0; font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5efe6; color: #1c1a17; }
    main { width: min(960px, calc(100% - 32px)); margin: 0 auto; padding: 40px 0 56px; }
    h1 { font-size: clamp(32px, 6vw, 56px); margin: 0 0 12px; }
    p { color: #645d55; line-height: 1.7; }
    .card { background: rgba(255,255,255,0.82); border: 1px solid rgba(28,26,23,0.12); border-radius: 24px; padding: 22px; box-shadow: 0 18px 50px rgba(58,45,29,0.12); }
    .messages { display: grid; gap: 12px; min-height: 180px; margin: 18px 0; }
    .message { padding: 14px 16px; border-radius: 18px; border: 1px solid rgba(28,26,23,0.12); white-space: pre-wrap; line-height: 1.6; }
    .agent { background: rgba(255,255,255,0.78); }
    .user { background: rgba(182,92,47,0.12); }
    textarea { width: 100%; min-height: 140px; resize: vertical; padding: 16px; border-radius: 18px; border: 1px solid rgba(28,26,23,0.12); font: inherit; }
    button { cursor: pointer; border: 0; border-radius: 999px; padding: 13px 20px; font: inherit; background: #b65c2f; color: #fffaf4; }
    .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 12px; }
    .status { color: #645d55; font-size: 14px; }
  </style>
</head>
<body>
  <main>
    <h1>智能工单 Agent</h1>
    <p>业务人员可以直接通过网页发起预算查询、IT 报修和财务报销。</p>
    <section class="card">
      <div id="messages" class="messages">
        <div class="message agent">欢迎使用智能工单 Agent。你可以直接说：“我是李四，帮我查一下还能报销多少钱？”</div>
      </div>
      <textarea id="messageInput" placeholder="例如：我是张三，电脑蓝屏了，帮我提一个 IT 报修工单"></textarea>
      <div class="row">
        <button id="sendButton" type="button">发送请求</button>
        <span id="status" class="status">等待请求</span>
      </div>
    </section>
  </main>
  <script>
    const messages = document.getElementById("messages");
    const input = document.getElementById("messageInput");
    const sendButton = document.getElementById("sendButton");
    const statusEl = document.getElementById("status");
    function appendMessage(role, text) {
      const el = document.createElement("div");
      el.className = `message ${role}`;
      el.textContent = text;
      messages.appendChild(el);
    }
    async function sendMessage() {
      const text = input.value.trim();
      if (!text) {
        statusEl.textContent = "请输入内容后再发送";
        return;
      }
      appendMessage("user", text);
      input.value = "";
      statusEl.textContent = "Agent 正在处理中...";
      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "请求失败");
        appendMessage("agent", data.reply);
        statusEl.textContent = data.action ? `已完成：${data.action}` : "处理完成";
      } catch (error) {
        appendMessage("agent", `请求失败：${error.message}`);
        statusEl.textContent = "调用失败";
      }
    }
    sendButton.addEventListener("click", sendMessage);
  </script>
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

if public_dir.exists():
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
