# API

登录、会话列表与 JWKS。**不提供注册接口**，账号由管理员在服务器上创建。

## 本地启动

```bash
cd apps/api
cp ../.env.example ../.env   # 首次；按需填写
uv sync
```

生成 JWT 密钥（首次）：

```bash
mkdir -p .keys
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out .keys/jwt_private.pem
openssl rsa -pubout -in .keys/jwt_private.pem -out .keys/jwt_public.pem
chmod 600 .keys/jwt_private.pem
```

`.keys/` 已在根 `.gitignore` 中忽略，不要提交私钥。

启动数据库与 API：

```bash
cd apps
docker compose -f docker-compose.dev.yml up -d --wait
cd api
uv run fastapi dev app/main.py --port 8000
```

## 账号管理

```bash
cd apps/api

# 创建（交互式输入密码）
uv run python -m app.scripts.cli create-user --username student

# 重置密码 / 禁用 / 启用 / 列表
uv run python -m app.scripts.cli reset-password --username student
uv run python -m app.scripts.cli disable-user --username student
uv run python -m app.scripts.cli enable-user --username student
uv run python -m app.scripts.cli list-users
```

自动化场景可加 `--password`，但注意它会进入 shell history。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/auth/login` | 用户名 + 密码登录 |
| POST | `/api/v1/auth/refresh` | refresh token 换发新 token |
| GET | `/api/v1/auth/me` | 当前用户 |
| GET | `/api/v1/sessions` | 当前用户的会话列表 |
| POST | `/api/v1/sessions` | 新建会话 |
| GET | `/api/v1/sessions/{id}` | 会话详情（仅本人） |
| PATCH | `/api/v1/sessions/{id}` | 重命名（仅本人） |
| POST | `/api/v1/sessions/{id}/touch` | 更新最近使用时间 |
| DELETE | `/api/v1/sessions/{id}` | 删除（仅本人） |
| GET | `/.well-known/jwks.json` | Agent 验签用公钥 |
| GET | `/health` | 健康检查 |

会话的 `session_id` 同时作为 LangGraph 的 `thread_id`，前端打开会话时用它补建运行时线程。

## JWT 配置

在 `apps/.env` 中配置（没有代码内默认值，缺少任一项都会启动失败）：

```dotenv
JWT_PRIVATE_KEY_PATH=.keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH=.keys/jwt_public.pem
JWT_ISSUER=computer-network-agent
JWT_AUDIENCE=agent
JWT_ACCESS_TOKEN_TTL_SECONDS=1800
JWT_REFRESH_TOKEN_TTL_SECONDS=604800
```

私钥/公钥的相对路径以 `apps/api` 为基准，也可填绝对路径。

无状态 JWT 下，禁用用户或重置密码不会立即吊销已签发的 access token；最长在 `JWT_ACCESS_TOKEN_TTL_SECONDS` 后失效，refresh 时会重新检查账号状态。

Agent 通过 `apps/.env` 中的 `JWT_JWKS_URL` 拉取公钥验签。

## 测试

```bash
cd apps/api
uv run ruff check .
uv run ty check .
uv run pytest -q
```

测试使用临时 SQLite 和临时 RSA 密钥，不依赖本地 Postgres。
