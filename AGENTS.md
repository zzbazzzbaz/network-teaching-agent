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
│   └── docker-compose.dev.yml  # 本地 Postgres
├── deploy/                     # nginx + compose
├── docs/                       # pdf_ocr；ui/ 学生端 UI 原型；chat/ 为个人笔记（gitignored）
├── .agents/skills/             # 项目技能
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

> `apps/agent-ui` 是废弃的旧前端，仅作参考，不再作为运行入口。

## 命令

```bash
make install     # uv sync（api / agent）+ npm ci（web）
make jwt-keys    # 首次：生成 apps/api/.keys/jwt_*.pem
make up          # 启动 Postgres（5432）
make dev         # 并行启动 agent / api / web
make down
make test        # apps/api pytest
```

单服务：`make run-agent` / `make run-api` / `make run-ui`。

```bash
cd apps/agent && uv run pytest
cd apps/web && npm run typecheck && npm run lint && npm run build
```

## 配置与路由

- 唯一配置源 `apps/.env`，样板 `apps/.env.example`。缺变量必须报错，不允许默认值或静默回退。
- 开发：Vite 把 `/api` 代理到 `API_URL`，`/agent` 代理到 `AGENT_URL` 并去掉前缀。
- 生产：`/api/`、`/.well-known/jwks.json`、`/health` → API；`/agent/` → LangGraph（支持 SSE）；其余 → 前端。
- `/internal/*` 只走容器内网，不经过 nginx，不得公网暴露。

## 跨应用不变量

1. 平台 `session_id` 就是 LangGraph 的 `thread_id`。API 在创建/删除会话时同步创建/删除 thread；打开会话时前端调 `POST /api/v1/sessions/{id}/ensure-thread` 幂等补建。
2. 用户身份只来自 JWT `sub`。前端不向 LangGraph 的 `configurable` 写 `sandbox_id`；Agent 用 `X-Internal-Token` 调 `POST /internal/sandbox/ensure` 获取沙箱。
3. API 与 Agent 共享 `SERVER_AUTH_TOKEN`，轮换时必须同时重启两者。
4. 聊天内容只有纯文本，不要假设附件或多模态。
5. 真实模型调用很慢。E2E 的 180s 超时、60s 断言超时是刻意设置，不要调小。
6. 浏览器只在聊天运行时直连 `/agent`；thread 生命周期和其他业务能力走 API BFF。