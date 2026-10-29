# 学生端 Web

`apps/web` 是新的学生端前端。旧 `apps/agent-ui` 已废弃，只作历史参考。

## 运行

```bash
# 根目录
make up          # Postgres
make run-api     # :8000
make run-agent   # :2024
make run-ui      # 本目录，:5173

# 或在本目录
npm install
npm run dev
```

Vite 将 `/api` 代理到 `API_URL`，将 `/agent` 去掉前缀后代理到 `AGENT_URL`，两者都来自 `apps/.env`。

## 路由

| 路由 | 说明 |
|---|---|
| `/login` | 学号/账号登录，桌面左侧协议图版 |
| `/learn` | 学习模式；有会话时进入最近会话，否则空态 |
| `/learn/$sessionId` | 学习聊天；`?panel=questions|memory` 切换到题库/记忆 |
| `/lab` | 实验模式；有会话时进入最近会话，否则空态 |
| `/lab/$sessionId` | 实验聊天；`?panel=sandbox|memory` |
| `/` | 重定向到 `/learn` |

URL 还支持：

```text
/learn/$sessionId?panel=questions&question=<uuid>
/learn/$sessionId?panel=memory&path=/memory/profile.md
/lab/$sessionId?panel=sandbox
```

## 技术结构

```text
src/
├── app/              # main、router、QueryClient、Provider、设计 token
├── routes/           # 预留的路由目录；当前路由表在 app/router.tsx
├── widgets/          # mode-shell、SessionPage、ModeHomePage
├── features/
│   ├── auth/         # 登录、登录态、401 刷新
│   ├── sessions/     # 平台会话 + LangGraph thread 生命周期
│   ├── chat/         # assistant-ui runtime、消息、工具卡、ask_student
│   ├── questions/    # 题库、筛选、详情、私有题 CRUD
│   ├── memory/       # 记忆目录树、文件预览
│   └── sandbox/      # 账户级 AGS 沙盒
└── shared/
    ├── api/          # fetch、ApiError、OpenAPI 生成类型
    ├── auth/         # localStorage token session
    ├── langgraph/    # Client、ensure/delete thread
    ├── lib/
    └── ui/           # shadcn 结构 + Radix primitives
```

- 聊天使用 assistant-ui primitives (`ThreadPrimitive` / `MessagePrimitive` / `ComposerPrimitive` / `AuiIf`)。
- LangGraph 适配在 `features/chat/model/ChatRuntime.tsx`：`useStream` + `useExternalStoreRuntime`。当前 `useStreamRuntime` 要求 remote thread list 管理 threadId，而平台要求 `session_id` 即外部 thread_id，因此采用适配层；UI 不使用自研 ChatStreamContext 状态层。
- `ask_student` 中断用 Zod 解析；未知 payload 显示可折叠 JSON；刷新后根据最后一个 AI tool call 是否有 tool result 判断是否已消费。
- 题库详情答案默认隐藏；记忆只读；沙盒按账户共享。
- 移动端侧栏是 Sheet；聊天与面板都使用全屏主区，面板有返回按钮。

## 类型

`src/shared/api/schema.d.ts` 由 FastAPI OpenAPI 生成：

```bash
npm run api:types   # api 必须在 :8000
```

列表摘要 `QuestionSearchItem` 在 OpenAPI 中是宽松 object，`src/shared/api/types.ts` 维护了最小边界类型。

## 后端缺口

见 [`BACKEND_GAPS.md`](./BACKEND_GAPS.md)。当前主要缺口：

- 会话列表没有消息摘要/消息数、没有自动标题；
- 用户只有 username；
- 沙盒响应没有展示名/创建时间，且无 stopped 状态；
- 题库没有 scope counts 端点；
- 工具结果没有统一的结构化 schema。

## 检查

```bash
npm run typecheck
npm run lint
npm run build
npm run test:e2e
```

`test:e2e` 默认只覆盖入口页和未登录深链跳转；真实模型/沙盒的 live smoke 不作为普通提交门禁。
