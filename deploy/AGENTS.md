# deploy

服务器 `101.35.223.219`（Ubuntu 24.04），域名 `network-agent.test.chatgqt.top`，
部署根 `/srv/network-teaching-agent`，只放 `.env`、`docker-compose.yml`、`secrets/`。
nginx 由 `bootstrap.sh` 一次性安装，CD 不改 nginx。不要动同机 docx-check。

## 文件

| 路径 | 作用 |
|---|---|
| `docker-compose.yml` | web/api/reaper/agent + postgres/langgraph-pg/redis |
| `nginx.conf` | 系统 nginx 站点配置 |
| `bootstrap.sh` | 一次性初始化，sudo 幂等 |
| `docker/{api,agent,web}.Dockerfile` | CI 构建，服务器不构建 |

路由：`/api/`、`/.well-known/jwks.json`、`/health` → 8082；`/agent/` → 8083（去前缀，支持 SSE）；其余 → 8081。业务端口只绑 `127.0.0.1`。

## 配置

- 唯一配置源 `apps/.env`（样板 `.env.example`），服务器 `.env` 直接复制并 `chmod 600`。
- 镜像 tag 只允许 `sha-<40 位 commit>`，写在 `.env` 的 `TAG`；CD 不传其他变量。
- 镜像推 GHCR + Docker Hub，服务器从 Docker Hub 拉；三个仓库必须 public。
- 缺少 `.env` 或 `TAG` 格式不对，CD 直接失败。

## 部署 / 回滚

```bash
ssh ubuntu@101.35.223.219 "sed -i 's/^TAG=.*/TAG=sha-<40位commit>/' /srv/network-teaching-agent/.env"
gh workflow run cd.yml
```

回滚把 `TAG` 改成旧 commit 再执行。首次部署：同步 `deploy/` 后 `sudo bash bootstrap.sh`。

## 约束

1. CD 只同步 `docker-compose.yml`，不改 nginx，不执行 bootstrap。
2. 改 `.env` 后跑 CD；`up --force-recreate` 会重建全部容器。
3. 迁移由 api 容器启动时执行；远端脚本走 stdin，`docker compose run/exec` 必须加 `</dev/null>`。
4. agent 官方镜像需要 `LANGSMITH_API_KEY` 许可校验。
