# agent-ui

React 19 + Vite 8 聊天前端，后端为 `apps/api` 与 `apps/agent`。

## 目录

```text
apps/agent-ui/
├── src/
│   ├── app/          入口、router、全局样式
│   ├── routes/       TanStack Router 路由
│   ├── features/     auth、chat、sandbox、sessions
│   └── shared/       请求、登录态、LangGraph Client
├── e2e/              Playwright 用例与账号
├── env.ts            读取 apps/.env
├── vite.config.ts    开发端口 5173、代理
├── playwright.config.ts  E2E 端口 5174
└── package.json
```

## 配置

运行时只读取 `apps/.env`：`AGENT_URL=http://127.0.0.1:2024`、`API_URL=http://127.0.0.1:8000`。

缺少变量时 Vite 报错。开发端口 `5173`，E2E 端口 `5174`。
CI 构建镜像时没有 `apps/.env`，`env.ts` 会优先读取同名 `process.env`（由 Dockerfile 注入占位值）。

## 启动与命令

```bash
cd apps/agent-ui
npm install
npm run dev
npm run build
npm run lint
npm run test:e2e
```

`/api` 代理到 `API_URL`，`/agent` 代理到 `AGENT_URL`。

沙箱入口在全局 `SandboxProvider` 中：进入页面调用 `GET /api/v1/sandbox`，运行中每 5 分钟调用 `POST /sandbox/heartbeat`，暂停/恢复/销毁分别调用 `/sandbox/pause`、`POST /sandbox`、`DELETE /sandbox`。启动/恢复按钮和打开 VSCode/ttyd 前仍显式调用 `POST /sandbox`。

发送消息和恢复中断时**不再**调用 `sandbox.ensure()`，也不再向 LangGraph 的 `configurable` 写 `sandbox_id`。Agent 根据 JWT 用户身份调用 API 内部接口创建/恢复沙箱；前端只在 run 进行中及结束后调用只读 `GET /api/v1/sandbox` 同步状态栏。

打开 VSCode/ttyd 前必须先 `POST /sandbox` 确保沙箱为 `running`，再导航新标签页；暂停后旧链接会返回 404。

## E2E

前置：API、Agent、Postgres 已启动，数据库中已有测试账号。

```bash
cd apps/api
uv run python -m app.scripts.cli create-user --username e2e_student --password e2e-password-123
uv run python -m app.scripts.cli create-user --username e2e_other --password e2e-password-456
```

测试账号定义在 `e2e/helpers.ts`。E2E 自动启动 `http://localhost:5174`。

## assistant-ui 技能

`.agents/skills/` 里有 5 个官方技能，覆盖 `@assistant-ui/react` 0.15.x（项目锁 `0.15.31`）。改消息、运行时、工具卡片前先读对应技能。

| 技能 | 覆盖 | 本项目落点 |
|---|---|---|
| `runtime` | `useLocalRuntime` / `useExternalStoreRuntime` / `useAui*` / `AuiConfig` | `features/chat/model/ChatRuntimeProvider.tsx`；细节见 `runtime/references/external-store.md` |
| `primitives` | `ThreadPrimitive`、`ComposerPrimitive`、`MessagePrimitive`、`MessagePartPrimitive` | `features/chat/ui/ChatPage.tsx`、`MessageParts.tsx` |
| `markdown` | `MarkdownTextPrimitive`、`defer`、代码高亮、Mermaid、KaTeX | `features/chat/ui/MessageParts.tsx` 的 `MarkdownText` |
| `tools` | `ToolCallMessagePartProps`、tool UI、审批、MCP | `features/chat/ui/ToolCallCard.tsx` |
| `assistant-ui` | 分层与总览，用来判断该看哪个子技能 | — |

两个不要照抄的地方：

- `tools` 的 `"use generative"` + `defineToolkit` + `withAui` 是前端定义工具的模型。本项目工具在 `apps/agent` 的 Python 侧，经 LangGraph 流回，只参考 `ToolCallMessagePartProps` 与 `references/tool-ui.md`。
- `markdown` 里的 `npx assistant-ui add markdown-text` 走 elements registry。本项目直接 import primitive，跳过安装步骤。

`@assistant-ui/react-langchain` 虽然导出 `useStreamRuntime`，但不要替换现有桥接：`ChatRuntimeProvider` 还承担 URL 驱动 `threadId`、401 续期（`ensureFreshToken`）和沙箱状态刷新，换掉会把这些挤回组件层。API 以 <https://www.assistant-ui.com/llms.txt> 为准。

## 工具边界

**Playwright 只做 E2E 测试。** 用例写在 `e2e/`，用 `npm run test:e2e` 运行，结果进 CI。不要用它临时翻页面，也不要拿它替代排查。

**chrome-devtools 只做 Agent 调试。** 通过仓库根目录 `opencode.json` 的 `chrome-devtools-mcp` 调用，用于临时打开页面、点击、看 console/network、录性能 trace、查 React 组件树与 commit。它没有断言，跑在本机真实 Chrome 上，结果不可复现，不能作为测试结论，也不进 CI。

用 chrome-devtools 定位到根因后，补一个 Playwright 用例复现该问题，再提交修复。

React 的组件、hooks、重渲染用 `react_*` 工具。这些工具只在 `npm run dev` 下生效：`src/app/main.tsx` 首行引入 `react-devtools-cdt-mcp/register`，`vite.config.ts` 在 build 时把它 alias 成空实现，生产包不含该插桩。

调试类 skill 在 `.agents/skills/`：`chrome-devtools`、`chrome-devtools-cli`。后者需要全局 `chrome-devtools` 命令，只用 MCP 可以不装；两者默认共用 Chrome profile，不要同时操作同一页面。
