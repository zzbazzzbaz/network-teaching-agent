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

## 本地运行

先启动 agent：

```bash
cd ../agent
uv run langgraph dev --port 2024
```

再启动前端：

```bash
npm install
npm run dev
```

打开 http://localhost:5173 。`/agent/*` 会由 Vite 代理到 `http://127.0.0.1:2024`，可用 `AGENT_URL` 覆盖。

## E2E

```bash
npx playwright install chromium   # 首次
npm run test:e2e
```

`playwright.config.ts` 会复用已运行的 agent 和前端；没有则自动拉起。

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
