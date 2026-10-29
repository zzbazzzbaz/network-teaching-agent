# API

```text
apps/api/
├── app/
│   ├── api/
│   │   ├── AGENTS.md
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   ├── internal/
│   │   │   ├── router.py
│   │   │   ├── sandbox.py
│   │   │   └── question_bank.py
│   │   ├── schemas/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   ├── core/
│   ├── data/
│   │   └── question_bank/
│   ├── gateway/
│   ├── job/
│   ├── models/
│   ├── repositories/
│   ├── scripts/
│   ├── services/
│   ├── lifespan.py
│   └── main.py
├── migrations/
│   └── versions/
├── tests/
├── .keys/
├── alembic.ini
├── pyproject.toml
└── uv.lock
```

## Agent 网关

- `app/gateway/http_client.py` 是与业务无关的 HTTP 工具：共享 `httpx.Client`、`request_json`、`Upstream*` 错误；
- `app/gateway/agent.py` 是 Agent 端唯一网关，`AgentGateway` 统一处理 Store 读取和 thread 生命周期；
- endpoint / service 通过 `AgentDep` 注入 `AgentGateway`，不直接创建 `httpx` 请求；
- Agent 不可用统一转 503；不要在 service 里解析裸 `dict`。

## 会话与线程

- `session_id` 就是 LangGraph `thread_id`；
- 创建 / 删除会话时由 API 同步管理 Agent thread；
- 打开会话时前端调 `POST /api/v1/sessions/{id}/ensure-thread`；
- 浏览器只在聊天运行时直连 `/agent`，生命周期管理走 API BFF。
