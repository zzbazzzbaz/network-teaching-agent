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

只读取 `apps/.env`：`DEEPSEEK_*`、`LANGFUSE_*`、`E2B_*`、`JWT_JWKS_URL`、`AGENT_API_BASE_URL`、`AGENT_INTERNAL_TOKEN`、`AGENT_API_TIMEOUT_SECONDS`。
自托管生产 Server（官方 `langgraph-api` 镜像）还需要 `LANGSMITH_API_KEY` 做启动许可校验；
它不用于 trace（生产 `LANGSMITH_TRACING=false`，trace 走 Langfuse）。

Agent 运行时从 LangGraph auth 注入的 `user_id` 调 API 内部接口 `POST /internal/sandbox/ensure`，获取当前账户的 `sandbox_id`。API 负责创建、恢复、续期和轮换；`AgsBackend` 按需连接，不直接调用 AGS 生命周期，也不信任前端传入的 `sandbox_id`。沙箱运行用户和工作目录固定为 `root` / `/root/workspace`，所有命令和文件操作显式使用 root。

缺少 auth user、`AGENT_INTERNAL_TOKEN` 或 API 不可用时本次 run 失败，不静默降级到共享沙箱。

## 系统提示词、课程资料与 Skill

固定系统提示词在 `agent/resources/prompt/system.md`，`agent/main.py` 启动时读入并传给 `create_deep_agent(system_prompt=...)`。它不属于 DeepAgents 的 memory，不会自动加载，也不允许 agent 修改。

`system.md` 只保留实验无关的通用规则：角色、教学原则、用户记忆、工具和安全。实验目标、环境、章节地图、诊断决策树、运行命令和验收标准放在对应的实验 skill（当前是 `traceroute-lab`）。

`agent/resources/skills/traceroute-lab/SKILL.md` 以 CS168 Project 1: Traceroute 的核心 8 章（对应 1A）为范围。修改课程结构时，同步更新系统提示词、skill 和 `materials/traceroute/`。

`agent/main.py` 用 `CompositeBackend` 挂三个路径：

- `/skills/` → `agent/resources/skills/`（只读）
- `/materials/` → `agent/resources/materials/`（只读）
- `/memory/` → LangGraph Store（用户级，可写）

`create_deep_agent(skills=["/skills/"])` 自动发现各技能目录下的 `SKILL.md`；`permissions` 禁止 agent 写入 `/skills`、`/materials`，允许写 `/memory`。资料不写入沙箱，因此不随沙箱镜像发布，也不会因暂停/销毁丢失。

`agent/resources/skills/memory-maintenance/SKILL.md` 定义学生记忆的文件模板和更新规则。首次创建或重建记忆时，agent 必须先读它。

`agent/resources/materials/traceroute/` 是 `docs/chat/10.26/教程/成品/` 的副本。更新教程后重新同步：

```bash
rsync -a --delete docs/chat/10.26/教程/成品/ apps/agent/agent/resources/materials/traceroute/
```

Skill 元数据按 thread 缓存在 state；新增或重命名 skill 后，已有 thread 需要新开对话，或把 `skills_metadata` 置为 `None` 触发重新加载。

## 用户级记忆

`/memory/` 通过 `StoreBackend` 存放在 LangGraph Store，namespace 为 `("users", <identity>, "memory")`。v1 目录：

```text
/memory/
├── AGENTS.md              # 唯一常驻注入
├── profile.md             # 稳定背景/偏好/目标
├── learning.md            # 进度/掌握/误解/有效策略
└── sessions/YYYY-MM.md    # 按月追加
```

- `create_deep_agent(memory=["/memory/AGENTS.md"])`，其他文件由 agent 按需 `read_file`。
- 记忆只存在 Store，不放沙箱；沙箱销毁/轮换不影响。
- `AGENTS.md` 在同一个 thread 内不会重新加载，更新后新 thread 生效。
- 本地 `langgraph dev` 无 auth user 时使用 `("users", "local", "memory")`（通过 `LANGSMITH_LANGGRAPH_API_VARIANT=local_dev` 识别）；生产必须 fail closed。
- 记忆规范见 `docs/chat/10.26/user-profile-memory-v1-spec.md`。

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
uv run pytest -q
```
