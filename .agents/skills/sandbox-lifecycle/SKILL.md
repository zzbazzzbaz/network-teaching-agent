---
name: Sandbox Lifecycle
description: Use when touching sandbox status, start/resume/pause/destroy, heartbeat, VSCode/ttyd links, or the /sandbox API. Covers the frontend state machine, API semantics, and the Agent's internal ensure call.
---

# 沙箱生命周期

## 归属

| 层 | 文件 | 职责 |
|---|---|---|
| 前端状态机 | `apps/agent-ui/src/features/sandbox/SandboxProvider.tsx` | 状态、心跳、去重、轮询 |
| 前端传输 | `apps/agent-ui/src/features/sandbox/api.ts` | 5 个接口与 DTO |
| 前端 UI | `apps/agent-ui/src/features/sandbox/SandboxBar.tsx` | 按钮与链接 |
| 用户接口 | `apps/api/app/api/v1/endpoints/sandbox.py` | `/api/v1/sandbox` |
| 业务服务 | `apps/api/app/services/sandbox_service.py` | 创建/恢复/暂停/销毁 |
| 内部接口 | `apps/api/app/api/v1/endpoints/internal.py` | Agent 专用 ensure |
| Agent | `apps/agent/agent/infra/sandbox_api.py`、`runtime/backends.py` | 每次 run 前确保可用 |

## 接口语义

| 调用 | 行为 | 关键返回 |
|---|---|---|
| `GET /api/v1/sandbox` | 只读查询，页面进入时调用 | 无记录 404；前端转 `idle` |
| `POST /api/v1/sandbox` | 创建 / 续期 / 恢复；过期则重建 | 409 = 正在销毁 |
| `POST /sandbox/heartbeat` | 只续期 running；**不会创建或恢复** | paused 原样返回 |
| `POST /sandbox/pause` | running → paused | 409 = 正在销毁 |
| `DELETE /sandbox` | 销毁 | 204 已删除；202 + `{"status":"stopping"}` |

## 前端状态机

`idle | starting | running | paused | stopping | error`（后端只有 `running | paused | stopping`）。

- 进入页面只 `GET`，**不主动创建**。
- `running` 时按 `sandbox.heartbeat_seconds`（默认 300s，最小 30s）心跳；404 → idle，409 → stopping。
- `stopping` 时每 10s `refresh()`，直到状态变化。
- `ensure()` 用 in-flight Promise 去重；按钮连点不会发多个 POST。
- `stop()` 遇到 503 视为 `stopping`，不要直接报错。

## 硬规则

- 打开 VSCode/ttyd 前必须 `POST /sandbox` 确保 `running`；暂停后旧链接会返回 404。
- 先同步 `window.open("about:blank")` 占位，再 `await ensure()`，最后 `popup.location.replace(url)`；顺序反了会被浏览器拦截。
- 发送消息、恢复中断都不调用 ensure。
- 前端不向 LangGraph 的 `configurable` 写 `sandbox_id`。Agent 用 JWT 身份调 `POST /internal/sandbox/ensure`（`X-Internal-Token`）并拿到 `sandbox_id`。
- `/internal/*` 不挂 `/api/v1`，不得经 nginx 暴露。

## 改动清单

- **改字段**：`apps/api/app/api/schemas/sandbox.py` → `sandbox_service.SandboxInfo` → 前端 `sandbox/api.ts` 的 `SandboxInfo` → `SandboxBar` 展示 → `e2e/sandbox.spec.ts`。
- **改状态/错误码**：同步 `toUiStatus`、`SandboxProvider` 的 refresh/heartbeat/stop 三个分支、E2E。
- **改生命周期**：检查 `apps/.env` 的 `AGS_SANDBOX_*` 与 `sandbox_service` 的过期、暂停保留逻辑；Agent 侧通常无需改，除非 ensure 的失败语义变了。
- **改鉴权**：用户接口走 JWT；内部接口只认 `AGENT_INTERNAL_TOKEN`。

## 验证

沙箱用例打真实 AGS，单条可能耗时数分钟：

```bash
cd apps/agent-ui
npx playwright test e2e/sandbox.spec.ts
```

E2E 清理用 `helpers.stopSandbox(page)`（直接 `DELETE /api/v1/sandbox`）。用例失败后若怀疑残留，先 `GET /api/v1/sandbox` 确认再处理，避免污染下一个用例。
