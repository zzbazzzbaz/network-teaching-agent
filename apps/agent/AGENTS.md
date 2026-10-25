# agent

LangGraph 智能体：DeepAgents 编排、JWT 鉴权、中断。

## 目录

```text
apps/agent/
├── agent/
│   ├── main.py          build_agent / graph 入口
│   ├── core/            auth（JWKS、资源隔离）、config
│   ├── infra/           LLM、E2B 沙盒、DeepAgents 后端
│   ├── prompt/          系统提示词
│   └── tools/           ask_human 等工具
├── langgraph.json       graph 与 auth 入口
├── pyproject.toml
└── uv.lock
```

## 配置

只读取 `apps/.env`：`DEEPSEEK_*`、`LANGFUSE_*`、`E2B_*`、`JWT_JWKS_URL`。

Agent 运行时必须从 `config.configurable.sandbox_id` 获取账户沙箱；`AgsBackend` 按需连接，不创建、暂停、销毁或续期沙箱。沙箱运行用户和工作目录固定为 `root` / `/root/workspace`，所有命令和文件操作显式使用 root。

## 可观测性

Langfuse 通过 LangChain `CallbackHandler` 自动生成 trace / generation / tool observation：

- `agent/core/observability.py` 显式初始化客户端，并在进程内复用 handler；
- `agent/main.py` 把 handler 绑定到 graph 默认 config，LangGraph Server 的每次 run 自动上报；
- `create_deep_agent(name=...)` 的名字同时作为 Langfuse trace 名；
- `agent/core/auth.py` 在 run metadata 注入 `langfuse_user_id` 与 `langfuse_session_id`（`thread_id`），一次对话聚合为一个 session。

`LANGFUSE_TRACING_ENVIRONMENT` / `LANGFUSE_RELEASE` 可选，用于在 Langfuse 中区分环境与构建版本。

## 启动

```bash
cd apps/agent
uv sync
uv run langgraph dev --port 2024 --no-browser
```

健康检查：`GET http://127.0.0.1:2024/ok`。

## 检查

```bash
cd apps/agent
uv run ruff check .
uv run ty check .
```
