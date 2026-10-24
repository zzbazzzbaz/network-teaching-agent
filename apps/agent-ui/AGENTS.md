# agent-ui

React 19 + Vite 8 聊天前端，后端为 `apps/api` 与 `apps/agent`。

## 配置

运行时只读取 `apps/.env`：

```dotenv
AGENT_URL=http://127.0.0.1:2024
API_URL=http://127.0.0.1:8000
```

缺少变量时 Vite 报错。开发端口固定 `5173`，E2E 端口固定 `5174`。

## 启动

```bash
cd apps/agent-ui
npm install
npm run dev
```

`/api` 代理到 `API_URL`，`/agent` 代理到 `AGENT_URL`。

## 命令

```bash
npm run dev
npm run build
npm run lint
npm run test:e2e
npm run test:e2e:ui
npm run test:e2e:report
```

## E2E

前置：API、Agent、Postgres 已启动，数据库中已有测试账号。

```bash
cd apps/api
uv run python -m app.scripts.cli create-user --username e2e_student --password e2e-password-123
uv run python -m app.scripts.cli create-user --username e2e_other --password e2e-password-456
```

测试账号定义在 `e2e/helpers.ts`。E2E 自动启动 `http://localhost:5174`。
