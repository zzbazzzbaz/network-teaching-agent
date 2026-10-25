# Sandbox Reaper

独立的 cron 容器每 5 分钟执行一次：

```bash
python -m app.job.sandbox_reaper
```

脚本只执行一轮并退出；周期由容器内的 cron 负责。`flock` 防止上一轮未结束时重复启动。

## 构建与启动

```bash
cd apps/api/deploy/sandbox-reaper
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f sandbox-reaper
```

## 环境变量

Compose 将 `apps/.env` 只读挂载为 `/run/secrets/app.env`。容器启动时只提取 reaper 需要的 `DB_*`、`E2B_*`、`AGS_*`、`JWT_*`、`CORS_ORIGINS` 到 `/etc/reaper.env`，cron 任务启动前加载该文件。LLM、Langfuse 等密钥不会进入 reaper 容器。

## 单实例

该服务应只运行一个副本。`flock` 只能防止同一容器内重叠执行，不能替代跨容器单例。

## 网络与数据库

这个 Compose 文件是独立模板。生产环境建议把 `sandbox-reaper` 服务合并进现有 API Compose 项目，使其加入同一个 network。

容器内的 `DB_DATABASE_URL` 不能使用 `127.0.0.1` 访问宿主机数据库；请改为 Compose 服务名（如 `postgres:5432`）或实际可达地址。独立运行本模板时，也需要注意与数据库容器共享 network。

## 手动执行

```bash
docker compose exec sandbox-reaper /app/.venv/bin/python -m app.job.sandbox_reaper
```
