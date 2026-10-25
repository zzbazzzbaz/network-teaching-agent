# deploy

服务器 `101.35.223.219`（Ubuntu 24.04），域名 `network-agent.test.chatgqt.top`，
部署根 `/srv/network-teaching-agent`，只放 `.env`、`docker-compose.yml`、`secrets/`。
nginx 由 `bootstrap.sh` 一次性安装，CD 不改 nginx。不要动同机 docx-check。

## 文件

| 路径 | 作用 |
|---|---|
| `docker-compose.yml` | web/api/agent + postgres/langgraph-pg/redis |
| `nginx.conf` | 系统 nginx 站点配置 |
| `bootstrap.sh` | 一次性初始化，sudo 幂等 |
| `docker/{api,agent,web}.Dockerfile` | CI 构建，服务器不构建 |

路由：`/api/`、`/.well-known/jwks.json`、`/health` → 8082；`/agent/` → 8083（去前缀，支持 SSE）；其余 → 8081。业务端口只绑 `127.0.0.1`。

## 配置

- 唯一配置源 `apps/.env`（样板 `.env.example`），服务器 `.env` 直接复制并 `chmod 600`。
- compose 能硬编码的直接硬编码；镜像仓库写死，tag 由 CD 动态传入，只允许 `sha-<40 位 commit>`。
- 缺少 `.env` 或 tag 格式不对，直接失败；不设默认值、不回退、不兜底、不要隐形行为。

## 部署 / 回滚

```bash
gh workflow run cd.yml -f tag=sha-<40位commit>
```

回滚传旧 commit。首次部署：同步 `deploy/` 后 `sudo bash bootstrap.sh`。
CD 分 `validate` → `deploy` → `verify`；只同步 `docker-compose.yml`。