# 智能工单 Agent 云端版

这个版本把原本只能在本地终端运行的 Python 脚本改造成了可部署的 Web 服务：

- `FastAPI` 提供标准 HTTP API
- `public/index.html` 提供业务人员可直接访问的网页入口
- `vercel.json` 支持部署到 Vercel
- `DATABASE_URL` 支持后续切换到云数据库

## 目录

- `api/index.py`：Vercel Python Serverless 入口
- `public/index.html`：浏览器访问页
- `smart_ticket_agent/`：核心业务、数据库、Agent、接口模型
- `智能工单 Agent/`：保留原本脚本入口，改为兼容新服务层

## 本地运行

1. 创建虚拟环境并安装依赖
2. 复制 `.env.example` 为 `.env` 并填入模型密钥
3. 启动服务：

```bash
uvicorn api.index:app --reload
```

打开 `http://127.0.0.1:8000` 即可访问页面。

## API

- `GET /api/health`
- `GET /api/budgets/{employee_name}`
- `POST /api/tickets`
- `POST /api/chat`

`POST /api/chat` 示例：

```json
{
  "message": "我是李四，刚买办公用品花了 200，帮我报销一下"
}
```

## Vercel 部署

1. 推送代码到 GitHub
2. 在 Vercel 导入该仓库
3. 配置环境变量：
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL`
   - `OPENAI_MODEL`
   - `DATABASE_URL`（生产建议使用 PostgreSQL；未配置时会退回本地临时 SQLite，仅适合演示）

## 重要说明

Vercel 的本地文件系统不适合作为正式生产数据库，因此：

- 未配置 `DATABASE_URL` 时，服务会自动使用临时 SQLite 并写入演示数据
- 正式商用时应接入外部持久化数据库，例如 Vercel Postgres、Neon、Supabase 或 Turso
