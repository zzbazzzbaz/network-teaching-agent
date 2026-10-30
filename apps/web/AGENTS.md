# web

学生端前端（`apps/web`），生产镜像由 `deploy/docker/web.Dockerfile` 构建。

## 技术栈

- React 19 + Vite 8 + TypeScript strict
- TanStack Router（代码式路由，`src/app/router.tsx`）
- TanStack Query（服务端状态）
- assistant-ui 0.15.x + LangGraph SDK（聊天）
- Tailwind CSS 4 + Radix/shadcn 结构
- assistant-ui 运行时：`useStream` + `useExternalStoreRuntime`。`useStreamRuntime` 当前版本要求由 remote thread list 提供 threadId，与平台 session_id 外部管理方式不匹配，因此在 `features/chat/model/ChatRuntime.tsx` 做适配；UI 仍全部使用 assistant-ui primitives。

## 目录

```text
src/
├── app/              # 入口、router、Provider、全局样式
├── routes/           # 路由组件（当前主要页面组件在 widgets）
├── widgets/          # mode-shell、session 页面
├── features/
│   ├── auth/
│   ├── chat/
│   ├── course/       # 教材章节与章节入口
│   ├── files/        # 图片上传与预览
│   ├── memory/
│   ├── questions/
│   ├── sandbox/
│   └── sessions/
└── shared/
    ├── api/          # fetch client + OpenAPI 生成类型
    ├── auth/         # token 存储
    ├── langgraph/    # LangGraph Client（仅聊天运行时）
    ├── lib/
    └── ui/
```

## 命令

```bash
npm install
npm run dev
npm run typecheck
npm run lint
npm run build
npm run api:types     # 需要 api 已启动在 :8000
```

## 约束

- `session_id` 必须原样作为 LangGraph `thread_id`；打开会话前调用 API 的 `ensureSessionThread`。
- 学习和实验模式的首页都是草稿态：点「新建会话」、点章节或示例问题都不立即建会话，首条消息发送时才创建。
- 首页用 `?panel=questions|memory|sandbox` 打开面板，不依赖会话；会话页沿用同一套 `WorkspacePanel`。
- 登录态只保存在浏览器；API/LangGraph 都走 `apiFetch` 的 JWT 注入与 401 刷新。
- 题目答案在用户主动查看前不渲染。
- 题库面板是「左侧知识点树 + 右侧题目列表」；URL 的 `kp` 是教材目录编号（如 `5.8`），列表用 `knowledge_point_match=primary` 只按主知识点筛选。
- 后端缺口记录在 `BACKEND_GAPS.md`。
- 不提交 `.env`、token、记忆内容或私有题库缓存。
- 附件只允许 JPEG/PNG/WebP；消息里只放 `[图片] <name> (file_id=<uuid>)` marker 和 `additional_kwargs.attachments`，不把 base64 放进消息或 React state。
- 历史缩略图走 `/api/v1/files/{id}/thumb`，点开大图走 `/raw`；两者都用 `authedFetch` 拉 blob + `URL.createObjectURL`，卸载时 revoke。
