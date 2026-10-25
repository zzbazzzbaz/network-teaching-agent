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

沙箱入口在全局 `SandboxProvider` 中：进入页面调用 `GET /api/v1/sandbox`，启动或首次发送消息时调用 `POST`，运行中每 5 分钟调用 `POST /sandbox/heartbeat`，暂停/恢复/销毁分别调用 `/sandbox/pause`、`POST /sandbox`、`DELETE /sandbox`。发送消息和恢复中断时把 `sandbox_id` 写入 LangGraph 的 `configurable`。

打开 VSCode/ttyd 前必须先 `POST /sandbox` 确保沙箱为 `running`，再导航新标签页；暂停后旧链接会返回 404。

## E2E

前置：API、Agent、Postgres 已启动，数据库中已有测试账号。

```bash
cd apps/api
uv run python -m app.scripts.cli create-user --username e2e_student --password e2e-password-123
uv run python -m app.scripts.cli create-user --username e2e_other --password e2e-password-456
```

测试账号定义在 `e2e/helpers.ts`。E2E 自动启动 `http://localhost:5174`。
