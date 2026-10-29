# 学生端前端：后端能力缺口记录

> 更新：2026-10-29  
> 范围：`apps/web` 对接现有 `apps/api` / `apps/agent`。前端不修改后端契约，以下能力先以只读或降级方式处理。

## 1. 会话列表

- `GET /api/v1/sessions` 只返回 `session_id / agent_id / title / created_at / updated_at`，没有最后一条消息摘要和消息数。
  - 当前前端：侧栏只展示标题与最后活跃时间，不伪造摘要或数量。
  - 建议：列表 DTO 增加 `last_message_preview`、`message_count`，或提供单独的 session summary。
- 新建会话自动标题已实现：Agent 首轮生成 + API 内部接口落库；前端在 run 结束刷新 detail/list。
  - 说明：前端不再做截断重命名；标题由 Agent 生成，手动改名受 `title_source` 保护。见 `docs/chat/10.29/session-auto-title-v1-spec.md`。
- 发送消息不会自动刷新 `sessions.updated_at`；前端只在打开会话时调用 `POST /sessions/{id}/touch`。
  - 建议：Agent run 完成后由 API 或前端统一 touch；若由前端统一处理，需要避免和聊天层耦合。

## 2. 用户信息

- `GET /auth/me` 只有 `user_id`、`username`，没有姓名、学号、专业、头像。
  - 当前前端：账户区显示 `username` 和「学生账号」，头像使用首字符。
  - 建议：增加 `display_name` / `student_no` / `major` 等可选资料字段。

## 3. 题库

- 知识点题量统计已补齐：`GET /api/v1/question-bank/knowledge-points/counts` 一次返回 `all/public/mine` 三个 scope 的知识点子树计数。
  - 当前前端：题库树直接使用该接口，不再按 scope 额外发起 `limit=1` 查询。
  - 列表支持 `knowledge_point_match=any|primary`，题库树固定使用 `primary`（只按主知识点）。
- OpenAPI 中 `QuestionSearchItem` 被描述为宽松 object（Pydantic 动态裁字段导致）。
  - 当前前端：在 `src/shared/api/types.ts` 维护最小边界类型；详情仍使用生成的 DTO。
  - 建议：为 summary 定义独立 Pydantic response model，使 OpenAPI 精确。
- 列表 summary 的 `last_attempt_at` 只对私有题有意义；公共题没有练习记录，前端按设计不显示。
  - 当前前端：符合 P0 契约。
- 删除已有作答记录的私有题返回 409；没有归档/回收站。
  - 当前前端：直接提示不可删除，并保留题目。

## 4. 沙盒

- `SandboxResponse` 没有展示名和创建时间。
  - 当前前端：显示「实验沙盒」、沙盒 ID、最后活跃时间、到期时间。
  - 建议：增加 `name`、`created_at`（若产品需要）。
- 没有 `stopped` 状态；未启动时 `GET /sandbox` 返回 404。
  - 当前前端：把 404 映射为「尚未启动」，不当作错误。
- 销毁返回 202 + `stopping` 或 204；状态机需要前端轮询。
  - 当前前端：进入 stopping 后每 10 秒刷新，直到 404 / 状态变化。
- 沙盒是账户级，多个实验会话共享 workspace；前端已在面板提示。
- 打开 VSCode / ttyd 前没有单独的短时签名接口；当前直接使用响应里的链接，链接过期需重新 ensure。
  - 建议：如果链接有时效，提供显式的 open/refresh 接口或在 ensure 响应中保证新鲜。

## 5. 记忆

- `GET /memory/tree` 是扁平 entries；目录以 `/` 结尾，前端自行构树。
  - 当前前端：实现了纯函数构树；没有写入/删除。
- 没有记忆文件搜索、分页或版本信息。
  - 当前前端：一次拉全量，目录内滚动。
  - 建议：记忆规模变大后增加分页或懒加载接口。
- 空记忆返回 `entries: []`，不是 404；前端展示空态。

## 6. 聊天 / Agent 契约

- 聊天直接走 `/agent` LangGraph SSE；没有 API BFF，符合架构。
- 工具结果大多是自然语言字符串，没有统一的结构化结果 schema。
  - 当前前端：`search_questions`、`execute` 等做通用可折叠卡片；未知工具展示参数/原始结果。
  - 建议：为常用工具提供稳定的结构化 result，前端才能做更精确的卡片。
- `ask_student` 的 interrupt payload 已包含答案；前端在提交前隐藏。
  - 当前前端：使用 Zod 校验，未知 payload 展示可折叠 JSON，不白屏。
  - 刷新后通过「最后一个 AI tool call 是否还有 tool result」判断 interrupt 是否已消费。
- `ask_student` 的 `single_choice` 工具在本地联调时曾出现 Agent 侧参数校验失败：模型传入的 options 没有按 `A.` / `B.` 前缀格式化，导致工具调用报错并退回简答。前端两种 payload 都支持；需要 Agent 提示词或工具 schema 继续约束模型输出。
- DeepAgents 的 todo 结构未在契约中固定。
  - 当前前端：未强行展示 Todo 面板，避免依赖不稳定字段。
  - 建议：固定 `todos` 的 schema 后再做计划面板。
- 没有单独的「已读/未读」或消息反馈接口；前端不做相关状态。

## 7. 其他

- 没有 `/agents` catalog；前端静态映射 `teach_agent → 学习`、`exp_agent → 实验`，符合 P0。
- 没有会话级沙盒；实验会话共享账户级 workspace，前端已提示。
- 没有题库练习提交接口；题库只读/维护，练习继续通过对话。
- 没有前端可用的全局搜索接口；侧栏搜索只在题库内部做。
