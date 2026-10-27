# agent

LangGraph 智能体：DeepAgents 编排、JWT 鉴权、中断。当前有两个 graph：

- `exp_agent`：实验 agent，带 AGS 沙盒；
- `teach_agent`：教学 agent，无沙盒，覆盖预习、习题、考研。

## 目录

```text
apps/agent/
├── agent/
│   ├── main.py          build_exp_agent / build_teach_agent + graph 组装
│   ├── runtime/         paths / prompts / memory / backends
│   ├── core/            auth（JWKS、资源隔离）、config
│   ├── infra/           LLM、E2B 沙盒、DeepAgents 后端
│   ├── resources/
│   │   ├── prompt/      base.md / lab.md / teaching.md
│   │   └── skills/
│   │       ├── common/  ask-student、memory-maintenance
│   │       ├── lab/     traceroute-lab（含 chapters/）
│   │       └── teaching/computer-networks（占位，含 textbook/）
│   └── tools/           ask_student
├── langgraph.json       graph 与 auth 入口
├── pyproject.toml
└── uv.lock
```

`agent/main.py` 直接组装两个 graph；共享运行支撑在 `agent/runtime/`。`langgraph.json` 和 Docker 入口仍指向 `agent/main.py`。

## 配置

只读取 `apps/.env`：`DEEPSEEK_*`、`LANGFUSE_*`、`E2B_*`、`JWT_JWKS_URL`、`AGENT_API_BASE_URL`、`AGENT_INTERNAL_TOKEN`、`AGENT_API_TIMEOUT_SECONDS`。
自托管生产 Server（官方 `langgraph-api` 镜像）还需要 `LANGSMITH_API_KEY` 做启动许可校验；
它不用于 trace（生产 `LANGSMITH_TRACING=false`，trace 走 Langfuse）。

`exp_agent` 运行时从 LangGraph auth 注入的 `user_id` 调 API 内部接口 `POST /internal/sandbox/ensure`，获取当前账户的 `sandbox_id`。API 负责创建、恢复、续期和轮换；`AgsBackend` 按需连接，不直接调用 AGS 生命周期，也不信任前端传入的 `sandbox_id`。沙箱运行用户和工作目录固定为 `root` / `/root/workspace`，所有命令和文件操作显式使用 root。

缺少 auth user、`AGENT_INTERNAL_TOKEN` 或 API 不可用时本次 run 失败，不静默降级到共享沙箱。

`teach_agent` 不接 `AgsBackend`，不调用 sandbox ensure。它和 `exp_agent` 同进程、同环境部署；当前 `E2BSettings` 仍是必填，所以同一部署下继续保留 `E2B_*` 配置即可。

## 提示词、课程资料与 Skill

系统提示词分层：

```text
agent/resources/prompt/
├── base.md          # 通用：角色、语言、记忆、教学原则、ask_student、格式、安全
├── lab.md           # 实验：AGS 沙盒、execute、学生文件、traceroute-lab
└── teaching.md      # 教学：无沙盒、三种模式、资料使用
```

`agent/runtime/prompts.py` 的 `load_prompt` 负责拼接：

- `exp_agent`：`base.md` + `lab.md`；
- `teach_agent`：`base.md` + `teaching.md`。

提示词不属于 DeepAgents 的 memory，不会自动加载，也不允许 agent 修改。

实验目标、环境、章节地图、诊断决策树、运行命令和验收标准放在 `agent/resources/skills/lab/traceroute-lab/SKILL.md`，实验资料放在同目录的 `chapters/`。教学三种模式的教学法放在 `agent/resources/prompt/teaching.md`；教材 skill 当前是 `agent/resources/skills/teaching/computer-networks/` 的占位版本，教材正文尚未接入。

`agent/runtime/backends.py` 用 `CompositeBackend` 挂两个路径：

- `/skills/` → `agent/resources/skills/`（只读）
- `/memory/` → LangGraph Store（用户级，可写）

Skill 目录：

```text
agent/resources/skills/
├── common/
│   ├── ask-student/SKILL.md
│   └── memory-maintenance/SKILL.md
├── lab/
│   └── traceroute-lab/
│       ├── SKILL.md
│       └── chapters/          # traceroute 8 章资料
└── teaching/
    └── computer-networks/
        ├── SKILL.md
        └── textbook/          # 占位索引；教材正文后续接入
```

- `exp_agent` 挂载 `["/skills/common/", "/skills/lab/"]`；
- `teach_agent` 挂载 `["/skills/common/", "/skills/teaching/"]`；
- 教学 agent 看不到实验 skill，实验 agent 看不到教材 skill。

`agent/resources/skills/common/memory-maintenance/SKILL.md` 定义学生记忆的 v2 目录、模板和更新规则。首次创建或重建记忆时，agent 必须先读它。

`agent/resources/skills/common/ask-student/SKILL.md` 定义 `ask_student` 的出题规范：单选/简答选择、题干和选项设计、难度控制、Markdown/Mermaid 图表、答后反馈和反模式。设计检查题前先读它。

`agent/resources/skills/lab/traceroute-lab/chapters/` 是 `docs/chat/10.26/教程/成品/` 的副本。更新教程后重新同步：

```bash
rsync -a --delete docs/chat/10.26/教程/成品/ apps/agent/agent/resources/skills/lab/traceroute-lab/chapters/
```

Skill 元数据按 thread 缓存在 state；新增或重命名 skill 后，已有 thread 需要新开对话，或把 `skills_metadata` 置为 `None` 触发重新加载。

## 两个 Agent

### `exp_agent`

- 有 AGS 沙盒，保留 `execute`；
- 系统提示词 `base.md` + `lab.md`；
- 工具：`ask_student` + 文件工具 + `execute`；
- 记忆：`["/memory/AGENTS.md", "/memory/lab/AGENTS.md"]`；
- 写权限：`/memory/lab/**`、`/memory/AGENTS.md`、`/memory/profile.md`；

### `teach_agent`

- 无沙盒，`CompositeBackend(default=StateBackend(), routes=skills/memory)`；
- 系统提示词 `base.md` + `teaching.md`；
- 工具：`ask_student` + 默认文件工具 + `task`；默认文件工具中的 `execute` 使用 `StateBackend`，不会连接 AGS，调用会报错，提示词要求不要使用；
- 记忆：`["/memory/AGENTS.md", "/memory/teaching/AGENTS.md"]`；
- 写权限：`/memory/teaching/**`、`/memory/AGENTS.md`、`/memory/profile.md`；其他写路径拒绝；

两个 agent 保留 DeepAgents 默认的 `task` 工具；不额外配置 subagent，也不专门移除 `task`。

## 用户级记忆

`/memory/` 通过 `StoreBackend` 存放在 LangGraph Store，namespace 为 `("users", <identity>, "memory")`。v2 目录：

```text
/memory/
├── AGENTS.md                    # 全局卡：稳定画像 + 两个 agent 的索引
├── profile.md                   # 稳定画像明细：背景、偏好、目标、考研信息
│
├── lab/
│   ├── AGENTS.md                # 实验卡
│   ├── learning.md              # 实验学习状态
│   └── sessions/YYYY-MM.md
│
└── teaching/
    ├── AGENTS.md                # 教学卡
    ├── learning.md              # 教学学习状态（预习/习题/考研）
    └── sessions/YYYY-MM.md
```

- 常驻加载：`/memory/AGENTS.md` + 当前 agent 的 track 卡；
- `profile.md`、`learning.md`、`sessions/` 由 agent 按需 `read_file`；
- 实验只写 `lab/`，教学只写 `teaching/`；全局卡和 `profile.md` 只在学生明确自述时低频更新；
- 记忆只存在 Store，不放沙箱；沙箱销毁/轮换不影响；
- `AGENTS.md` 在同一个 thread 内不会重新加载，更新后新 thread 生效；
- 本地 `langgraph dev` 无 auth user 时使用 `("users", "local", "memory")`（通过 `LANGSMITH_LANGGRAPH_API_VARIANT=local_dev` 识别）；生产必须 fail closed；
- v2 不做历史迁移，上线前清空旧 namespace；旧根 `learning.md` / 根 `sessions/` 不再读取；
- 记忆规范见 `docs/chat/10.27/memory-v2-teach-agent-skeleton-v1-spec.md`。

## 可观测性

Langfuse 通过 LangChain `CallbackHandler` 自动生成 trace / generation / tool observation：

- `agent/core/observability.py` 显式初始化客户端，并在进程内复用 handler；
- `agent/main.py` 把 handler 绑定到 graph 默认 config，LangGraph Server 的每次 run 自动上报；
- `create_deep_agent(name=...)` 的名字同时作为 Langfuse trace 名（`exp_agent` / `teach_agent`）；
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
