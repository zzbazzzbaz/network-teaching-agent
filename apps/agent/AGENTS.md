# agent

LangGraph 智能体：DeepAgents 编排、JWT 鉴权、`ask_human` 中断。

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
