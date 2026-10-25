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
│   ├── job/                      sandbox reaper 等后台任务
│   ├── models/                   SQLAlchemy 模型
│   ├── repositories/             数据访问
│   ├── services/                 业务逻辑
│   └── scripts/cli.py            账号管理命令
├── deploy/sandbox-reaper/        cron reaper 容器
├── migrations/                   Alembic 迁移
├── alembic.ini
├── tests/                        pytest
├── .keys/                        JWT 私钥/公钥
└── pyproject.toml
```

## 配置

只读取 `apps/.env`：`DB_DATABASE_URL`、`JWT_PRIVATE_KEY_PATH`、`JWT_PUBLIC_KEY_PATH`、`E2B_DOMAIN`、`E2B_API_KEY`、`AGS_TOOL_NAME`、`AGS_SANDBOX_TIMEOUT_SECONDS`、`AGS_SANDBOX_IDLE_SECONDS`、`AGS_SANDBOX_PAUSED_RETENTION_SECONDS`、`AGS_SANDBOX_MAX_LIFETIME_SECONDS`、`AGS_SANDBOX_HEARTBEAT_SECONDS`、`CORS_ORIGINS`。

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

## 沙箱回收

`user_sandboxes` 的生命周期由 API 维护，回收任务由独立的 cron 容器触发：

```bash
cd apps/api/deploy/sandbox-reaper
docker compose up -d --build
```

容器内每 5 分钟执行一次：

```bash
python -m app.job.sandbox_reaper
```

脚本只执行一轮并退出，`flock` 防止上一轮未结束时重复启动。cron 容器只应保持一个副本。

每个用例在 `DB_DATABASE_URL` 指向的 Postgres 中创建独立 schema。
