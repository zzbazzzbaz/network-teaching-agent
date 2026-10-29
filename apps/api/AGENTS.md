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

## 图片文件

- 公共接口：`POST /api/v1/files`、`GET /api/v1/files/{id}/raw|thumb`、`DELETE /api/v1/files/{id}`；
- 内部接口：`GET /internal/files/{id}`、`GET /internal/files/{id}/raw`，只允许 Agent 使用内部 token 访问；
- 图片按 `owner_id` 隔离，owner 不匹配统一 404；`file_id` 是唯一引用，消息和 checkpoint 不存图片字节；
- 存储布局固定为 `FILES_ROOT/<owner_id>/<file_id>/original.<ext>` + `thumb.webp`，`storage_key` 只存相对路径；
- MIME 不落库，由 `storage_key` 后缀推导；上传时只信 magic，拒绝 SVG/GIF/HEIC/PDF；
- 不做用户级配额；单文件 10MB、单边 8192px、总像素 40MP 是技术保护。

## 会话与线程

- `session_id` 就是 LangGraph `thread_id`；
- 创建 / 删除会话时由 API 同步管理 Agent thread；
- 打开会话时前端调 `POST /api/v1/sessions/{id}/ensure-thread`；
- 浏览器只在聊天运行时直连 `/agent`，生命周期管理走 API BFF；
- 自动标题由 Agent 调 `POST /internal/sessions/{id}/title` 写入；API 用 `sessions.title_source` 保护手动改名。
