# API 层

```text
app/api/
├── AGENTS.md
├── dependencies.py      # 会话、配置、JWT、内部 token/用户依赖
├── errors.py            # AppError -> JSON 响应
├── internal/
│   ├── router.py        # /internal 路由汇总
│   ├── sandbox.py       # 内部沙箱接口
│   └── question_bank.py # 内部题库接口
├── schemas/             # Pydantic 请求/响应
└── v1/
    ├── router.py        # 公共 /api/v1 路由汇总
    └── endpoints/       # 公共和基础端点
```

## 职责

- 只处理 HTTP 入参、鉴权、状态码和响应模型；
- 业务逻辑放 `app/services/`，数据访问放 `app/repositories/`；
- 请求/响应模型放 `app/api/schemas/`，不要在 endpoint 里临时拼裸 dict；
- 业务错误抛 `app.core.exceptions.AppError` 子类，由 `errors.py` 统一转换。

## DTO 与分页

- 请求体统一继承 `ApiRequest`（`extra="forbid"`）；
- 响应体统一继承 `ApiResponse`（`from_attributes=True`）；
- endpoint 返回类型必须是响应 DTO，不能返回 ORM 模型或裸 dict；
- 多字段查询参数使用 Pydantic 查询 DTO（`Annotated[Model, Query()]`）；
- 分页使用 `PageQuery` + `Page[T]`，不同资源可继承并覆盖默认 `limit` / 最大值；
- 分页结果在 service/repository 内使用 `PageRequest` / `PageResult`，endpoint 负责转成 `Page[T]`；
- 静态全量数据（知识点）和树形快照（记忆树）不分页。

## 路由

- 公共接口挂到 `v1/router.py`，最终由 `app/main.py` 加上 `/api/v1` 前缀；
- `/health`、`/.well-known/jwks.json` 由 `app/main.py` 直接挂载，不要塞进 v1 router；
- 题库公共接口在 `/api/v1/question-bank/*`：
  - 公共题只读；
  - 私有题只允许 owner 新增、编辑、删除；
  - 不提供作答/attempt 接口；
- 列表分页：`GET /sessions` 和题库搜索返回 `Page[T]`；
- 会话创建 / 删除同步管理 LangGraph thread；打开会话时调 `POST /sessions/{id}/ensure-thread`；
- 记忆只读 BFF 在 `/api/v1/memory/*`，API 通过 `AgentDep` 调 Agent 的 `/store/*`；
- 自动标题回写接口在 `/internal/sessions/{id}/title`，只允许 Agent 用内部 token 调用；
- 内部接口放在 `internal/` 包，由 `internal/router.py` 汇总，使用 `/internal/*` 前缀，直接挂到 `app/main.py`，不挂 `/api/v1`，并设置 `include_in_schema=False`；
- 内部接口不能经过 nginx 公网转发。

## 依赖

统一定义在 `app/api/dependencies.py`：

- `SessionDep`：数据库 session；
- `SettingsDep`：应用配置；
- `AgentDep`：Agent 端网关，统一访问 Store 和 thread 生命周期；
- `UserIdDep`：从 JWT `sub` 取当前用户；
- `InternalUserDep`：内部接口统一使用；先校验 `X-Internal-Token`，再从 `X-User-Id` 校验用户存在且启用。

不要在 endpoint 里重复实现 JWT 解析、内部 token 比较或用户状态查询。

## 安全

- 公共接口的用户身份只来自 JWT，不接受请求体里的 `user_id`；
- 题库私有题必须按 `owner_id` 过滤；公共题不能通过学生 API 编辑或删除；
- 记忆 BFF 只读，只能读当前 JWT 用户的 namespace；API 不直连 `langgraph-pg`；
- 内部接口只信任通过 `X-Internal-Token` 校验后的 `X-User-Id`；
- 查询/修改资源时必须做 owner 过滤，越权统一返回 404 或 403；
- 日志不记录 token、密码、题干、答案等敏感内容。

## 检查

```bash
cd apps/api
uv run ruff check .
uv run ty check .
uv run pytest -q
```
