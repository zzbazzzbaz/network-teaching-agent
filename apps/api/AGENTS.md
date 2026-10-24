# API

FastAPI 服务：登录、会话列表、JWKS。无注册接口，账号由管理员创建。

## 配置

只读取 `apps/.env`，缺少必填项时启动失败：

`DB_DATABASE_URL`、`JWT_PRIVATE_KEY_PATH`、`JWT_PUBLIC_KEY_PATH`、`E2B_DOMAIN`、`E2B_API_KEY`、`AGS_TOOL_NAME`、`AGS_SANDBOX_TIMEOUT_SECONDS`、`CORS_ORIGINS`。

密钥路径相对 `apps/api`。JWT 签发方、受众、有效期定义在 `app/core/constants.py`。

## 启动

```bash
cd apps && docker compose -f docker-compose.dev.yml up -d --wait
cd api
cp ../.env.example ../.env
uv sync
uv run fastapi dev app/main.py --port 8000
```

首次生成密钥：

```bash
mkdir -p .keys
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out .keys/jwt_private.pem
openssl rsa -pubout -in .keys/jwt_private.pem -out .keys/jwt_public.pem
```

## 账号管理

```bash
cd apps/api
uv run python -m app.scripts.cli create-user --username student
# 其余子命令：reset-password / disable-user / enable-user / list-users
```

## 测试

每个用例在 `DB_DATABASE_URL` 指向的 Postgres 中创建独立 schema。

```bash
cd apps/api
uv run ruff check .
uv run ty check .
uv run pytest -q
```
