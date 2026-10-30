# 计算机网络教学智能体

面向计算机网络课程的教学智能体：学生在 Web 端与苏格拉底式 Agent 对话、答题，并在云端沙箱做实验。

## 目录

```text
.
├── apps/
│   ├── agent/                  # LangGraph 运行时（:2024）
│   ├── web/                    # React 学生端（:5173）
│   ├── api/                    # FastAPI 账号 / 会话 / 沙箱（:8000）
│   ├── sandbox/                # AGS 镜像：code-server + ttyd
│   ├── .env                    # 唯一配置源
│   └── docker-compose.dev.yml
├── deploy/
├── docs/
├── .agents/skills/
├── Makefile
└── opencode.json
```

## 应用

| 目录 | 技术栈 | 职责 | 端口 | 约定 |
|---|---|---|---|---|
| `apps/web` | React 19 + Vite 8 + assistant-ui + TanStack Router | 学生端前端 | 5173 | `apps/web/AGENTS.md` |
| `apps/api` | FastAPI + SQLAlchemy + Postgres | 账号、会话元数据、沙箱生命周期 | 8000 | `apps/api/AGENTS.md` |
| `apps/agent` | LangGraph + deepagents + Langfuse | 教学 Agent 运行时 | 2024 | `apps/agent/AGENTS.md` |
| `apps/sandbox` | AGS/E2B 镜像 | code-server + ttyd 实验环境 | 9000 | `apps/sandbox/AGENTS.md` |
| `deploy` | nginx + docker compose | 生产部署 | — | `deploy/AGENTS.md` |
