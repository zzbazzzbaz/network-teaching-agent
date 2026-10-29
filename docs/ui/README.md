# 链路 · 学生端 UI 原型

> 这个目录只回答一个问题：学生端的界面长什么样、信息怎么排、移动端怎么退化。
>
> 所有内容都是 mock：没有 API、没有 LangGraph、没有 AGS。`src/lib/mock.ts` 是唯一数据源。
>
> 它不是 `apps/agent-ui` 的实现版本，也不套用生产架构（TanStack Router / TanStack Query / assistant-ui）。原型为了改版方便，用了 React Router 和一份内存 store，请不要把这里的路由和状态管理当成实现建议。

## 运行

```bash
npm install
npm run dev -- --port 5178
```

构建与类型检查：

```bash
npm run build
npm run typecheck
```

重新生成截图（需要本地 dev server 在 5178）：

```bash
npm run screenshots
```

## 布局

参考早期 `html2` 原型的侧栏 + 整页切换结构重写（该原型未纳入 git）。

```text
┌──────────────────┬─────────────────────────────────────────────┐
│ 侧栏 284 / 72    │ 主区（整页切换）                              │
│ 品牌              │                                             │
│ 学习 / 实验       │ 对话                                        │
│ 题库 · 记忆       │ 或 题库 / 记忆 / 沙盒                        │
│ + 新建会话        │                                             │
│ 会话列表          │                                             │
│ 用户              │                                             │
└──────────────────┴─────────────────────────────────────────────┘
```

- 没有全局顶栏，也没有右侧上下文面板。
- 侧栏可收起到 72px 图标栏；收起后保留品牌、模式、功能、新建和账户，隐藏会话列表。
- 功能入口不显示数量或状态；题库/记忆/沙盒页头只有标题（题库带新建按钮），不再放说明文字或返回按钮；回对话靠点侧栏已激活的功能入口。
- 点击侧栏的 `题库 / 记忆 / 沙盒`，主区整页切换；再点一次同一个入口回到对话。
- 桌面端聊天内容宽 840；题库/沙盒内容宽 960；记忆是 300 目录 + 预览两栏。
- `< 1024`：侧栏变成左侧 Sheet；主区加一条 52px 顶栏（菜单 + 当前会话）；面板打开时顶栏右侧出现返回图标。
- 登录后默认进入学习工作台的最新会话；学习 / 实验只在侧栏切换。模式选择页不再保留。

## 路由

| 路由 | 内容 |
|---|---|
| `/login` | 登录，桌面整页左右分栏（品牌 / 协议图版 + 表单），移动端只保留表单；禁用滚轮 |
| `/` | 重定向到 `/learn` |
| `/learn` | 重定向到该模式最近的会话 |
| `/learn/$sessionId` | 学习工作台：对话 / 题库 / 记忆 |
| `/lab` | 重定向到实验模式最近的会话 |
| `/lab/$sessionId` | 实验工作台：对话 / 沙盒 / 记忆 |
| `/styleguide` | 设计规范页 |

面板与详情都在 URL 里：

```text
/learn/s-tcp-handshake?panel=questions
/learn/s-tcp-handshake?panel=questions&question=q-why-three
/learn/s-tcp-handshake?panel=memory&path=/memory/profile.md
/lab/s-tcpdump?panel=sandbox
```

## 已经做出来的交互

- 新建、重命名、删除会话；发送消息后有“思考中 → 流式输出”的演示（内容为固定回复）。
- `ask_student` 作答检查点：选择 → 提交 → 折叠为已作答 → Agent 追问。
- 工具调用卡片：检索题库、保存题目、确保沙盒、执行命令；终端输出可展开。
- 题库：来源和题型筛选、知识点筛选、搜索、两列卡片、详情 Dialog、答案显式展开、私有题新增/编辑/删除。
- 记忆：目录树 + 文件预览；桌面自动选中 `profile.md`；移动端列表 → 文件。
- 沙盒：运行 / 暂停 / 恢复 / 销毁的状态与确认；VSCode / 终端入口；账户级 workspace 提示。
- 桌面侧栏可收起 + 整页切换；移动端 52px 顶栏 + 左侧 Sheet + 返回图标。
- 设计规范页 `/styleguide` 同时是组件的可视化清单。

## 目录

```text
src/
├── components/
│   ├── ui/              # shadcn 结构 + Radix primitives
│   ├── chat/            # 消息、Markdown、工具卡、检查点、Composer
│   ├── panels/          # 题库页、记忆页、沙盒页、题目编辑器
│   ├── brand.tsx
│   ├── handshake-diagram.tsx
│   └── layer-diagram.tsx
├── layout/              # 侧栏、工作台壳、移动端顶栏
├── lib/                 # mock 数据、内存 store、模式配置、工具函数
├── pages/               # 登录、模式入口、会话、规范页
└── index.css            # 设计令牌 + 少量排版规则
```

`archive/` 存放上一版基于“顶栏 + 右侧上下文面板”的页面和截图，只作本地对比，不参与构建，也不纳入 git。

## 组件与实现说明

- **组件库**：Radix UI primitives + shadcn 的组件结构（Button / Dialog / Sheet / Tabs / Select / RadioGroup / AlertDialog / DropdownMenu / Tooltip），样式用 Tailwind 4 令牌覆盖。没有第二套 CSS-in-JS。
- **字体**：IBM Plex Sans / IBM Plex Mono 由 `@fontsource` 自托管；中文回退到 PingFang SC / Noto Sans CJK。
- **图标**：lucide-react。
- **通知**：sonner。
- **聊天渲染**：react-markdown + remark-gfm，不启用 raw HTML。
- **没有接入**：OpenAPI 生成类型、assistant-ui、TanStack Router/Query、真实 Markdown 代码高亮、Mermaid、KaTeX。

## 已知边界

- 刷新即回到初始 mock 数据，没有持久化。
- 发送消息后的回复是按模式生成的固定文本，用于看排版和流式状态，不代表 Agent 行为。
- 题库筛选（来源/题型/知识点/关键词）存在组件内，不在 URL；面板、题目、记忆路径在 URL。
- 深色模式没有做，令牌已按语义分层，后续可替换。
- 只做了浅色主题和中文文案。
- 截图脚本会用 Playwright 检查控制台错误、横向溢出和移动端布局视口，但不做视觉回归。

## 截图

`screenshots/` 下有 25 张：

- 桌面：`01-login` / `02-learn-chat` / `03-learn-questions` / `04-question-detail` / `05-memory` / `06-lab-chat` / `07-sandbox` / `08-styleguide` / `25-sidebar-collapsed`
- 状态：`18-checkpoint-answered` / `19-sandbox-stopped` / `20-empty-chat` / `21-question-editor` / `22-question-revealed`
- 移动：`09-mobile-login` / `10-mobile-chat` / `11-mobile-questions` / `12-mobile-memory` / `13-mobile-memory-file` / `14-mobile-sandbox` / `15-mobile-rail` / `16-mobile-editor` / `23-mobile-question-detail` / `24-mobile-styleguide`
- 平板：`17-tablet-chat`

更完整的设计理由见 [DESIGN.md](./DESIGN.md)。

## 自查

- 截图脚本在 1440 / 1024 / 390 三个宽度检查 `document.scrollWidth` 与 `window.innerWidth`，并收集控制台错误；当前无溢出、无报错。
- 另用 Playwright 在 320 / 360 / 390 / 768 / 1024 / 1280 / 1440 检查过关键路由的横向溢出、`#main` 和单一 `h1`，当前全部通过。
- 图标按钮有 `aria-label`；表单控件有 label/`aria-label`；破坏性操作二次确认。
- `prefers-reduced-motion` 下关闭脉冲和光标动画；Composer 处理 `env(safe-area-inset-bottom)`。
- 未做：axe 全量扫描、读屏实测、表单未保存离开提示、虚拟列表。
- `npm run lint` 会跑 oxlint，目前只有 fast-refresh / set-state-in-effect 警告，没有 error。
