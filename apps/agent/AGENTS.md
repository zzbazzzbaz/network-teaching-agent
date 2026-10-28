# agent

## 目录

```text
apps/agent/
├── agent/
│   ├── main.py                  # build_exp_agent / build_teach_agent
│   ├── core/
│   ├── infra/
│   ├── runtime/
│   ├── resources/
│   │   ├── prompt/
│   │   │   ├── base.md
│   │   │   ├── lab.md
│   │   │   └── teaching.md
│   │   └── skills/
│   │       ├── common/
│   │       │   └── memory-maintenance/
│   │       ├── lab/
│   │       │   └── traceroute-lab/
│   │       └── teaching/
│   │           ├── ask-student/
│   │           ├── question-bank/
│   │           └── computer-networks/
│   │               └── textbook/
│   └── tools/
│       ├── ask_student.py
│       ├── question_bank.py
│       └── schemas/
├── tests/
├── langgraph.json
├── pyproject.toml
└── uv.lock
```

## Agent

| Agent | 提示词 | Skill | 工具 | 后端 |
|---|---|---|---|---|
| `exp_agent` | `base.md` + `lab.md` | `memory-maintenance`、`traceroute-lab` | 默认工具；无 `ask_student` | `AgsBackend` |
| `teach_agent` | `base.md` + `teaching.md` | `memory-maintenance`、`ask-student`、`question-bank`、`computer-networks` | 默认工具 + `ask_student`、`search_questions`、`save_question` | `StateBackend` |

默认工具：

```text
read_file
write_file
edit_file
delete
ls
glob
grep
execute
task
```

## 说明

- `ask_student` 只在 `teach_agent` 挂载；`exp_agent` 用普通文本追问。
- `ask_student` 的中断 payload 包含 `answer`：单选题带 `correct_option`，简答题带 `reference_answer`；前端负责在提交前隐藏。
- `teach_agent` 的 `execute` 使用 `StateBackend`，不连接 AGS，提示词要求不要使用。
- `exp_agent` 的 `execute` 连接当前用户的 AGS 沙箱。
- Skill 挂载路径：
  - `exp_agent`：`/skills/common/`、`/skills/lab/`；
  - `teach_agent`：`/skills/common/`、`/skills/teaching/`。
- `question-bank` skill 只在 `teach_agent` 可见。
- 两个 graph 都在 `langgraph.json` 注册，入口是 `agent/main.py`。

## 记忆 Store

- 记忆 namespace 固定为 `("users", <identity>, "memory")`。
- Agent 运行时的 `StoreBackend` 直接读写 Store，不经过 HTTP 授权。
- 浏览器不能直接访问 `/store/*`；API 作为内部服务访问时使用：
  - `X-Internal-Token`；
  - `X-User-Id`。
- `/store/*` 只允许 `get` / `search`，只允许当前用户的 `memory` namespace；`put` / `delete` 返回 403。
- 内部 token 不能访问 `/threads/*`、`/runs/*`。
