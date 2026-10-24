# agent-ui

面向 `apps/agent` 的自建聊天前端。React SPA，不使用 Next.js。

完整范围与验收标准见 [`docs/chat/10.23/agent-ui-spec.md`](../../docs/chat/10.23/agent-ui-spec.md)。

目录分层与依赖规则见 [`docs/chat/10.23/agent-ui-architecture.md`](../../docs/chat/10.23/agent-ui-architecture.md)。

## 技术栈

- Vite 8 + React 19 + TypeScript
- TanStack Router（文件路由）
- `@assistant-ui/react` 组件原语
- `@langchain/react` 的 `useStream`
- Playwright（E2E）

## 功能

- 登录（无注册，账号由管理员创建）
- access token 自动续期；401 自动回登录页
- 会话列表：新建、切换、重命名、删除
- 聊天、工具调用展示、`ask_human` 中断
- 所有请求带 Bearer token；LangGraph 侧按用户隔离 thread

## 本地运行

需要先启动 API 和 agent：

```bash
# 终端 1：API (:8000)
cd ../api
uv run fastapi dev main.py --port 8000

# 终端 2：agent (:2024)
cd ../agent
uv run langgraph dev --port 2024

# 终端 3：前端 (:5173)
cd ../agent-ui
npm install
npm run dev
```

打开 http://localhost:5173 。`/api/*` 代理到 API，`/agent/*` 代理到 LangGraph；可用 `API_URL` / `AGENT_URL` 覆盖。

首次使用先建账号：

```bash
cd ../api
uv run python -m scripts.cli create-user --username student
```

## E2E

```bash
npx playwright install chromium   # 首次
npm run test:e2e
```

E2E 对接**真实启动的后端**，测试脚本不负责启动 API 和 Agent。

### 前置

- API 已启动（默认 `http://127.0.0.1:8000`）
- Agent 已启动（默认 `http://127.0.0.1:2024`）
- 真实后端数据库中已有测试账号（默认 `e2e_student` / `e2e_other`）：

```bash
cd ../api
uv run python -m scripts.cli create-user --username e2e_student --password e2e-password-123
uv run python -m scripts.cli create-user --username e2e_other --password e2e-password-456
```

E2E 只负责启动前端 dev server（默认 `localhost:5174`），并把 Vite 的 `/api`、`/agent` 代理指向上述真实后端。

可用环境变量覆盖：

```bash
E2E_API_URL=http://127.0.0.1:8000 \
E2E_AGENT_URL=http://127.0.0.1:2024 \
E2E_APP_URL=http://localhost:5174 \
E2E_STUDENT_USERNAME=e2e_student \
E2E_STUDENT_PASSWORD=e2e-password-123 \
E2E_OTHER_USERNAME=e2e_other \
E2E_OTHER_PASSWORD=e2e-password-456 \
npm run test:e2e
```

测试覆盖登录、会话列表、跨用户会话拒绝、LangGraph thread 隔离，以及原有的聊天/中断用例。API 自身由 `pytest` 覆盖，不单独跑 E2E。

- `npm run test:e2e:ui` 调试模式
- `npm run test:e2e:report` 查看报告

测试会真实调用模型，单条最长 180 秒。

## 常用命令

```bash
npm run dev
npm run build
npm run lint
npm run test:e2e
```
