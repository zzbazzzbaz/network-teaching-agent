# agent

LangGraph 智能体：DeepAgents 编排、JWT 鉴权、中断。

## 目录

```text
apps/agent/
├── agent/
│   ├── main.py          build_agent / graph 入口
│   ├── core/            auth（JWKS、资源隔离）、config
│   ├── infra/           LLM、E2B 沙盒、DeepAgents 后端
│   ├── resources/       系统提示词、课程资料与 DeepAgents skill（只读）
│   └── tools/           ask_human 等工具
├── langgraph.json       graph 与 auth 入口
├── pyproject.toml
└── uv.lock
```

## 配置

只读取 `apps/.env`：`DEEPSEEK_*`、`LANGFUSE_*`、`E2B_*`、`JWT_JWKS_URL`。
自托管生产 Server（官方 `langgraph-api` 镜像）还需要 `LANGSMITH_API_KEY` 做启动许可校验；
它不用于 trace（生产 `LANGSMITH_TRACING=false`，trace 走 Langfuse）。

Agent 运行时必须从 `config.configurable.sandbox_id` 获取账户沙箱；`AgsBackend` 按需连接，不创建、暂停、销毁或续期沙箱。沙箱运行用户和工作目录固定为 `root` / `/root/workspace`，所有命令和文件操作显式使用 root。

## 系统提示词、课程资料与 Skill

固定系统提示词在 `agent/resources/prompt/system.md`，`agent/main.py` 启动时读入并传给 `create_deep_agent(system_prompt=...)`。它不属于 DeepAgents 的 memory，不会自动加载，也不允许 agent 修改。

`agent/resources/skills/traceroute-lab/SKILL.md` 以 CS168 Project 1: Traceroute 的核心 8 章（对应 1A）为范围。修改课程结构时，同步更新系统提示词、skill 和 `materials/traceroute/`。

`agent/main.py` 用 `CompositeBackend` 把两个只读路径挂到 agent 侧：

- `/skills/` → `agent/resources/skills/`
- `/materials/` → `agent/resources/materials/`

`create_deep_agent(skills=["/skills/"])` 自动发现各技能目录下的 `SKILL.md`；`permissions` 禁止 agent 写入这两个路径。资料不写入沙箱，因此不随沙箱镜像发布，也不会因暂停/销毁丢失。

`agent/resources/materials/traceroute/` 是 `docs/chat/10.26/教程/成品/` 的副本。更新教程后重新同步：

```bash
rsync -a --delete docs/chat/10.26/教程/成品/ apps/agent/agent/resources/materials/traceroute/
```

Skill 元数据按 thread 缓存在 state；新增或重命名 skill 后，已有 thread 需要新开对话，或把 `skills_metadata` 置为 `None` 触发重新加载。

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
