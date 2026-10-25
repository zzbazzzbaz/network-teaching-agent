# deploy —— 服务器部署

先应用仓库内各 `apps/*/AGENTS.md`，再应用本文件。

服务器 `101.35.223.219`（腾讯云 CVM，Ubuntu 24.04，4 vCPU / 3.6 GiB + 1.9 GiB swap），
部署根 `/srv/network-teaching-agent`（属主 = 部署用户 `ubuntu`，已在 docker 组），
域名 `network-agent.test.chatgqt.top`，由**系统级 nginx + certbot** 终止 TLS
（服务器上还跑着 `docx-check.test.chatgqt.top`，不要动它的站点/证书；本项目的站点是独立文件）。

## 文件职责

| 路径 | 作用 | 谁在用 |
|---|---|---|
| `docker-compose.yml` | 服务器全部 7 个容器（web/api/reaper/agent/postgres/langgraph-pg/langgraph-redis） | `.github/workflows/cd.yml` / 手工 `docker compose` |
| `docker/{api,agent,web}.Dockerfile` | 三个业务镜像，构建上下文分别是 `apps/api`、`apps/agent`、`apps/agent-ui` | **只在 CI 构建**，服务器从不构建镜像 |
| `nginx/network-agent.conf` | 系统级 nginx 站点：HTTPS + 同源反代 + SSE/WebSocket | 软链为 `/etc/nginx/sites-enabled/network-agent` |
| `nginx/http-only.conf` | 首次签发证书前的临时 HTTP 站点 | `scripts/bootstrap.sh` 一次性使用 |
| `scripts/bootstrap.sh` | 一次性初始化：docker 组、目录与权限、JWT 密钥、nginx 站点、证书、renew hook、sudoers | 手工 `sudo` 跑，幂等 |

**部署/回滚动作不在本目录**：步骤内联在 `.github/workflows/cd.yml`
（`gh workflow run cd.yml -f tag=…`），服务器上不再有部署脚本。

服务器本地文件（**不进 git**）：`.env`（600，唯一业务配置源）、`secrets/jwt/`（JWT 密钥对，属主 uid 10001）。

## 容器、端口与网络

| 服务 | 镜像 | 端口 | 网络 | 内存上限 |
|---|---|---|---|---|
| `web` | `${WEB_IMAGE}:${TAG}` | `127.0.0.1:8081` → 80 | app | 96m |
| `api` | `${API_IMAGE}:${TAG}` | `127.0.0.1:8082` → 8000 | app, data | 512m |
| `reaper` | `${API_IMAGE}:${TAG}` | 不发布 | data | 192m |
| `agent` | `${AGENT_IMAGE}:${TAG}` | `127.0.0.1:8083` → 8000 | app, data | 1280m |
| `postgres` | `postgres:17.11` | 不发布 | data | 384m |
| `langgraph-pg` | `pgvector/pgvector:pg17` | 不发布 | data | 256m |
| `langgraph-redis` | `redis:7-alpine` | 不发布 | data | 128m |

- 卷：`pg-data`（业务库）、`langgraph-pg-data`（LangGraph 线程/检查点），**删卷即删数据**。
- 绑定挂载：`./secrets/jwt:/app/.keys:ro`（api / reaper）。
- `api` 的 `DB_DATABASE_URL` 由 compose 用 `POSTGRES_*` 拼出来，`.env` 里不用重复维护。
- `agent` 使用 `POSTGRES_URI` + `DATABASE_URI` + `REDIS_URI` 持久化线程状态与流式队列；
  `JWT_JWKS_URL` 指向内网 `http://api:8000/.well-known/jwks.json`。
- `reaper` 每 5 分钟执行一轮 `python -m app.job.sandbox_reaper`，替代原先的宿主机 cron。
- 所有业务端口只绑 `127.0.0.1`，公网唯一入口是系统级 nginx。

## nginx 路由（系统级，公网唯一入口）

| 匹配 | 上游 | 说明 |
|---|---|---|
| `/api/` | `127.0.0.1:8082` | FastAPI（保留 `/api/v1` 前缀） |
| `/.well-known/jwks.json` | `127.0.0.1:8082` | Agent 校验 JWT |
| `/health` | `127.0.0.1:8082` | 健康检查 |
| `/agent/` | `127.0.0.1:8083` | 去掉 `/agent` 前缀；`proxy_buffering off` + 长超时是 SSE 必需 |
| 其余 | `127.0.0.1:8081` | SPA |

- 80 → 443 301；`/.well-known/acme-challenge/` 保留给 certbot。
- 证书：`/etc/letsencrypt/live/network-agent.test.chatgqt.top/`；`certbot.timer` 续期，
  `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx` 负责 `nginx -t && systemctl reload nginx`。
- 站点文件通过软链指向部署根，CD 更新文件后 `nginx -t` + reload 即可，不需要 `restart`。

## 硬约束

1. **配置只放 `.env`**：compose 的 `${...}` 插值全部来自 `/srv/network-teaching-agent/.env`
   （`docker compose --env-file .env ...`）；`.env` 不进 git、保持 600。
   新增变量必须同时补进 `apps/.env.example`（如适用于本地）和本文件。
2. **镜像 tag 必须显式**：只接受 `main` 或 `sha-<40 位 commit>`（`cd.yml` 第一步校验），`latest` 一律不用。
3. **端口纪律**：业务容器只绑 `127.0.0.1`，公网只经 nginx。
4. **文件权限**（CD 每次部署会兜底修一部分）：
   - `nginx/*.conf` 644（nginx master 以 root 读，但 reload 前会 `nginx -t`）
   - `scripts/*.sh` 755；`docker-compose.yml` 644
   - `secrets/jwt/*` 属主 **10001**（api 镜像内 app 用户），`jwt_private.pem` 600、`jwt_public.pem` 644
   - `.env` 600
5. **改 nginx 配置必须先 `nginx -t` 再 reload**；reload 走 sudoers 白名单
   `sudo -n nginx -t`、`sudo -n systemctl reload nginx`，不要 `restart`（会掐断在途 SSE）。
6. **不要在服务器上手改 `docker-compose.yml` / `nginx/` / `scripts/`**：CD 每次先 `rm -rf` 这三处再 `scp -r`，
   服务器内容始终等于仓库（仓库里删掉的文件也会跟着消失）。配置改 `.env`，其余改仓库。
7. **不要动 docx-check 的 nginx 站点和证书**：本项目的站点文件是独立的
   `/etc/nginx/sites-available/network-agent`（软链到部署根），只操作它。
8. **迁移在 CD 中执行**：`docker compose run --rm --no-deps api alembic upgrade head`，
   在基础库启动后、业务容器重建前。迁移失败会终止部署并打印日志。
9. **前端构建只依赖相对路径**：`apps/agent-ui` 浏览器侧请求 `/api/v1` 与 `/agent`，
   容器内 nginx 只做 SPA 静态托管，反代全部在宿主机 nginx。
10. **`apps/agent/langgraph.json` 变更后必须重新生成 `deploy/docker/agent.Dockerfile`**：
    graph / auth 路径写在 Dockerfile 的 `LANGSERVE_GRAPHS` / `LANGGRAPH_AUTH` 里。
    生成命令：`cd apps/agent && uv run langgraph dockerfile /tmp/agent.Dockerfile`，再把基础镜像固定为
    `langchain/langgraph-api:0.16.5-py3.14`。

## 首次初始化

```bash
# 1) 本地把 deploy/ 同步到服务器部署根
rsync -az deploy/ ubuntu@101.35.223.219:/srv/network-teaching-agent/

# 2) 服务器上跑一次性初始化（sudo、幂等）
ssh ubuntu@101.35.223.219
sudo DOMAIN=network-agent.test.chatgqt.top ACME_EMAIL=admin@chatgqt.top \
  bash /srv/network-teaching-agent/scripts/bootstrap.sh

# 3) 放业务配置（从本地 apps/.env 复制后改下面这些）
#    见下一节“服务器 .env”
chmod 600 /srv/network-teaching-agent/.env

# 4) 本地生成部署密钥，把公钥装到服务器，把私钥写进 GitHub secret
ssh-keygen -t ed25519 -N '' -C 'gha-network-agent-deploy' -f /tmp/network-agent-deploy
ssh-copy-id -i /tmp/network-agent-deploy.pub ubuntu@101.35.223.219
gh secret set DEPLOY_SSH_KEY < /tmp/network-agent-deploy
rm -f /tmp/network-agent-deploy /tmp/network-agent-deploy.pub
```

> 首次部署必须先有 CI 镜像：push main 等 `ci` 成功，再
> `gh workflow run cd.yml -f tag=main`。

## 服务器 `.env`

以 `apps/.env.example` 为底，至少修改/补充以下项：

```dotenv
# 镜像（与 ci.yml 的 ghcr.io/<owner>/<repo>/<app> 保持一致）
WEB_IMAGE=ghcr.io/zzbazzzbaz/network-teaching-agent/web
API_IMAGE=ghcr.io/zzbazzzbaz/network-teaching-agent/api
AGENT_IMAGE=ghcr.io/zzbazzzbaz/network-teaching-agent/agent

# 业务库（compose 会用它拼 DB_DATABASE_URL）
POSTGRES_USER=agent
POSTGRES_PASSWORD=<随机强口令>
POSTGRES_DB=agent

# LangGraph 专用库
LANGGRAPH_PG_PASSWORD=<随机强口令>

# API JWT密钥（容器内绝对路径）
JWT_PRIVATE_KEY_PATH=/app/.keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/app/.keys/jwt_public.pem

# Agent 从内网 API 取 JWKS（compose 也会覆盖）
JWT_JWKS_URL=http://api:8000/.well-known/jwks.json

# 同源前端，CORS 可留空；填也只填正式域名
CORS_ORIGINS=https://network-agent.test.chatgqt.top

# 可观测性环境标识
LANGFUSE_TRACING_ENVIRONMENT=production
```

其余 `DEEPSEEK_*`、`LANGFUSE_*`、`E2B_*`、`AGS_*` 原样保留。
`POSTGRES_*`、`LANGGRAPH_PG_PASSWORD` 只用于 compose 插值，不会被 API 读取。

## 日常操作

```bash
# 部署最新一次 CI 构建
gh workflow run cd.yml -f tag=main

# 回滚到某个历史构建
gh workflow run cd.yml -f tag=sha-<40 位 commit>

# 看部署状态
gh run list --workflow=cd.yml --limit 5
gh run watch

# 服务器状态 / 日志
ssh ubuntu@101.35.223.219
cd /srv/network-teaching-agent
docker compose --env-file .env ps
docker compose --env-file .env logs -f --tail=100 api
docker compose --env-file .env logs -f --tail=100 agent

# 创建账号（无注册接口）
docker compose --env-file .env exec -T api \
  python -m app.scripts.cli create-user --username student --password '<口令>'
docker compose --env-file .env exec -T api python -m app.scripts.cli list-users

# nginx
sudo nginx -t && sudo systemctl reload nginx
journalctl -u nginx -n 50 --no-pager

# 证书
sudo certbot certificates
sudo systemctl list-timers certbot.timer
```

## 排错

| 症状 | 原因 | 处置 |
|---|---|---|
| `docker compose pull` 报 unauthorized | 服务器未登录 GHCR（包为私有） | `cd.yml` 已用任务级 `GITHUB_TOKEN` 登录；手工部署则先 `docker login ghcr.io` |
| `TAG 必须显式指定` | 手工执行时没带 TAG | `TAG=main docker compose --env-file .env ...` |
| `systemctl reload nginx` permission denied | sudoers 未装 / 站点文件权限不对 | 重跑 `scripts/bootstrap.sh`；`chmod 644 nginx/*.conf` |
| 站点 502 | 上游容器没起来 | `docker compose ps` / `logs --tail=100 web api agent` |
| Agent 对话卡住、消息不流式 | nginx 缓冲或超时太短 | 确认 `/agent/` 有 `proxy_buffering off`、`proxy_read_timeout 3600s` |
| 证书签发失败 | 80 端口不可达 / DNS 未解析到本机 | 控制台放行 80/443；`dig +short network-agent.test.chatgqt.top` |
| 续期后浏览器仍是旧证书 | nginx 未 reload | 检查 `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx` 可执行 |
| 容器起来就 unhealthy | `.env` 缺变量（配置 fail-fast） | `docker compose --env-file .env logs <svc>` 找缺失项，补 `.env` 后 `up -d` |
| 沙箱不回收 | reaper 容器未运行 / AGS 凭证失效 | `docker compose logs reaper`；确认 `E2B_*`、`AGS_*` |
| `role "agent" does not exist` | 改过 `POSTGRES_USER` 但卷是旧的 | 改回原值，或备份后重建卷（**删卷即删库**） |

## 与仓库其余部分的契约

- **唯一配置样板是 `apps/.env.example`**；服务器 `.env` = 照抄后按上节修改。`deploy/` 下不保留第二份样板。
- 前端只发相对路径（`/api/v1`、`/agent`），靠宿主机 nginx 同源反代；换正式前端只需改 `WEB_IMAGE`。
- 三个 Dockerfile 的构建上下文是各工程根目录：工程内新增「运行期需要」的文件必须同步 Dockerfile。
- `deploy/` 的改动要生效必须提交并走 CD —— push 只构建镜像，**部署是手动的**（`cd.yml` 的 `workflow_dispatch`）。
- CI/CD 的 GitHub 配置：`DEPLOY_SSH_KEY`（ed25519 私钥）是唯一手工 secret；GHCR 读写用 `GITHUB_TOKEN`。
