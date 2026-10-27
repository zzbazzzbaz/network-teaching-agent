# API

FastAPI 服务：登录、会话列表、JWKS。无注册接口，账号由管理员创建。

## 目录

```text
apps/api/
├── app/
│   ├── main.py / lifespan.py     应用入口、DB 初始化
│   ├── api/                      路由、依赖、错误、schemas
│   ├── core/                     config、database、security、constants
│   ├── gateway/                  AGS 网关
│   ├── job/                      APScheduler 调度、sandbox reaper 等后台任务
│   ├── models/                   SQLAlchemy 模型
│   ├── repositories/             数据访问
│   ├── services/                 业务逻辑
│   └── scripts/cli.py            账号管理命令
├── migrations/                   Alembic 迁移
├── alembic.ini
├── tests/                        pytest
├── .keys/                        JWT 私钥/公钥
└── pyproject.toml
```

## 配置

只读取 `apps/.env`：`DB_DATABASE_URL`、`JWT_PRIVATE_KEY_PATH`、`JWT_PUBLIC_KEY_PATH`、`E2B_DOMAIN`、`E2B_API_KEY`、`AGS_TOOL_NAME`、`AGS_SANDBOX_TIMEOUT_SECONDS`、`AGS_SANDBOX_IDLE_SECONDS`、`AGS_SANDBOX_PAUSED_RETENTION_SECONDS`、`AGS_SANDBOX_MAX_LIFETIME_SECONDS`、`AGS_SANDBOX_HEARTBEAT_SECONDS`、`SCHEDULER_ENABLED`、`SCHEDULER_REAPER_INTERVAL_SECONDS`、`CORS_ORIGINS`、`AGENT_INTERNAL_TOKEN`。

`AGENT_INTERNAL_TOKEN` 只用于 Agent 调用的内部接口；必须与 Agent 环境中的同名变量一致，不能进入前端或公网。

密钥路径相对 `apps/api`。JWT 签发方、受众、有效期定义在 `app/core/constants.py`。

## 启动

```bash
cd apps && docker compose -f docker-compose.dev.yml up -d --wait
cd api
cp ../.env.example ../.env
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py --port 8000
```

已有库如果此前由 `create_all` 建过表：

```bash
cd apps/api
uv run alembic stamp 0001_initial
uv run alembic upgrade head
```

首次生成密钥：`mkdir -p .keys && openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out .keys/jwt_private.pem && openssl rsa -pubout -in .keys/jwt_private.pem -out .keys/jwt_public.pem`

## 账号与测试

```bash
cd apps/api
uv run python -m app.scripts.cli create-user --username student
uv run ruff check . && uv run ty check . && uv run pytest -q
```

## 内部沙箱接口

Agent 使用 `POST /internal/sandbox/ensure` 获取当前用户可用的 `sandbox_id`：

- 请求头 `X-Internal-Token` 必须匹配 `AGENT_INTERNAL_TOKEN`；
- 请求体 `{"user_id": "<uuid>"}`；
- API 校验用户存在且启用后，复用 `sandbox_service.ensure_user_sandbox` 创建/恢复/续期/轮换；
- 返回 `{"sandbox_id": "...", "status": "running"}`，不返回 VSCode/ttyd 链接；
- 路由不挂在 `/api/v1` 下，`include_in_schema=False`，nginx 不转发 `/internal/`。

## 沙箱回收

`user_sandboxes` 的生命周期由 API 维护，回收规则位于 `app/services/sandbox_reaper.py`，入口位于 `app/job/sandbox_reaper.py`，调度器位于 `app/job/scheduler.py`。

API 以单容器单进程部署，进程启动时由 APScheduler 注册回收任务，默认每 5 分钟执行一轮，随 API 一起停止。不再使用独立 `reaper` 容器、宿主机 cron 或手动调度入口。多副本部署时必须只让一个副本设置 `SCHEDULER_ENABLED=true`，否则会重复扫描（行锁只能降低冲突，不能替代单调度入口）。

每个用例在 `DB_DATABASE_URL` 指向的 Postgres 中创建独立 schema。
