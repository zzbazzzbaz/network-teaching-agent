# deploy

服务器 `101.35.223.219`（Ubuntu 24.04），域名 `network-agent.test.chatgqt.top`，
部署根 `/srv/network-teaching-agent`，系统级 nginx + certbot 终止 TLS；不要动同机 docx-check。

## 文件

| 路径 | 作用 |
|---|---|
| `docker-compose.yml` | web/api/reaper/agent + postgres/langgraph-pg/redis |
| `docker/{api,agent,web}.Dockerfile` | CI 构建，服务器不构建 |
| `nginx/*.conf` | nginx 站点与首次签证书临时配置 |
| `scripts/bootstrap.sh` | 一次性初始化，sudo 幂等 |

路由：`/api/`、`/.well-known/jwks.json`、`/health` → 8082；`/agent/` → 8083（去前缀，支持 SSE）；其余 → 8081。业务端口只绑 `127.0.0.1`。

## 配置

- 唯一配置源 `apps/.env`（样板 `.env.example`），服务器 `.env` 直接复制并 `chmod 600`。
- compose 只覆盖数据库地址、JWT 路径、JWKS 地址和 `CORS_ORIGINS`。
- 镜像推 GHCR + Docker Hub，服务器从 Docker Hub 拉；三个仓库必须 public。
- `TAG` 只允许 `main` 或 `sha-<40 位 commit>`。

## 部署 / 回滚

首次：同步 `deploy/` 后执行 `sudo bash scripts/bootstrap.sh`。

```bash
gh workflow run cd.yml -f tag=main
gh workflow run cd.yml -f tag=sha-<40位commit>
```

## 约束

1. nginx 改动先 `nginx -t` 再 `systemctl reload nginx`。
2. CD 会删除并重传 `nginx/`、`scripts/`、`docker-compose.yml`，不要服务器手改。
3. 迁移在 CD 中执行；`docker compose run/exec` 必须加 `</dev/null>`。
4. 改 `.env` 后重跑 CD；业务容器每次 `--force-recreate`。
5. agent 需要 `LANGSMITH_API_KEY` 许可校验；`langgraph.json` 变更后同步 Dockerfile 的 ENV。

## 常用

```bash
cd /srv/network-teaching-agent
docker compose --env-file .env ps
docker compose --env-file .env logs -f --tail=100 api
docker compose --env-file .env exec -T api python -m app.scripts.cli create-user --username student
```
