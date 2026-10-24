# AGS VSCode + Web Shell 沙盒

自定义 AGS 镜像，提供浏览器版 VSCode、Web Shell、envd 管理面和 nginx 统一入口。
镜像只通过 GitHub Actions 构建并推送到 Docker Hub，AGS 通过腾讯云内网镜像源拉取。

当前 AGS 工具：

| 项目 | 值 |
|---|---|
| ToolName | `network-teaching-agent-sandbox` |
| ToolId | `sdt-rynngtwo` |
| Status | `ACTIVE` |
| Image | `mirror.ccs.tencentyun.com/15688463267/network-teaching-agent-sandbox:sha-2421885` |
| ImageDigest | `sha256:d9b134b20f270be839a2b1dd9539e25a29dc36b47e53a48d750db06ecb461422` |
| 默认规格 | `1C2G / 10GiB` |
| 网络 | `PUBLIC` |

## 1. 沙盒内运行什么进程

`start.sh` 是容器入口，最终由 nginx 作为 PID 1 保持容器运行。

| 进程 | 运行用户 | 监听地址 | 作用 |
|---|---|---|---|
| `nginx` | root | `0.0.0.0:9000` | 统一 Web 入口：`/health`、`/vscode/`、`/ttyd/`、WebSocket |
| `envd` | root | `0.0.0.0:49983` | AGS 管理面：命令执行、文件读写、健康检查 |
| `code-server` | `user` | `127.0.0.1:8080` | 浏览器版 VSCode，通过 nginx 暴露为 `/vscode/` |
| `ttyd` | `user` | `127.0.0.1:7681` | Web Shell，通过 nginx 暴露为 `/ttyd/` |

启动关系：

```text
start.sh
  ├─ envd         后台循环，退出后自动重启
  ├─ code-server  后台循环，退出后自动重启
  ├─ ttyd         后台循环，退出后自动重启
  └─ nginx        exec 成 PID 1，daemon off
```

关键约定：

- `code-server`、`ttyd` 和 agent shell 的默认工作目录统一为 `/home/user/workspace`。
- `8080` 和 `7681` 只监听 `127.0.0.1`，不直接对外。
- `9000` 是对外 Web 入口，`49983` 是 AGS 管理面。
- `AuthMode PUBLIC` 下，`9000` 无需 token；`49983` 仍然需要 token。
- 日志在 `/logs/`：
  - `/logs/envd.log`
  - `/logs/code-server.log`
  - `/logs/ttyd.log`
  - `/logs/nginx-access.log`
  - `/logs/nginx-error.log`

## 2. 这个目录下文件有什么

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 构建 `linux/amd64` 镜像：Node 22、nginx、code-server、ttyd、envd、非 root 用户 |
| `nginx.conf` | `/vscode/`、`/ttyd/`、`/health` 反向代理和 WebSocket 配置 |
| `start.sh` | 容器入口：启动 envd、code-server、ttyd、nginx |
| `fetch-vendor.sh` | CI 构建前下载固定版本的 code-server / ttyd 到 `vendor/` |
| `README.md` | 本文档 |
| `.gitignore` | 忽略 `vendor/` 和 `*.log` |

补充说明：

- `vendor/` 不提交到 git，由 GitHub Actions 在构建时下载；本地目录不存在也不影响 CI。
- GitHub Actions 工作流在仓库根目录：
  `.github/workflows/sandbox-image.yml`
- 修改 `README.md` 不会触发镜像构建；只有改动 `Dockerfile`、`nginx.conf`、
  `start.sh`、`fetch-vendor.sh` 或 workflow 才会触发。

## 3. 更新远程：CI 构建 → Docker Hub → 本地 CLI 更新 AGS

整体链路：

```text
修改 apps/sandbox/
  → push 到 main
  → GitHub Actions 构建 linux/amd64
  → push Docker Hub: latest + sha-<commit>
  → 本地 tccli 更新 AGS Tool 的 Image
  → StartSandboxInstance 创建沙盒
```

### 3.1 推送代码

```bash
git add apps/sandbox
git commit -m "feat(sandbox): ..."
git push origin main
```

也可以手动触发：

```bash
gh workflow run sandbox-image.yml
gh run watch
```

工作流需要 GitHub Secrets：

| Secret | 值 |
|---|---|
| `DOCKERHUB_USERNAME` | `15688463267` |
| `DOCKERHUB_TOKEN` | Docker Hub PAT（Read & Write） |

构建产物：

```text
Docker Hub:
15688463267/network-teaching-agent-sandbox:latest
15688463267/network-teaching-agent-sandbox:sha-<commit>
```

### 3.2 AGS 使用的镜像地址

AGS 不能直接使用 `docker.io/...`，必须使用腾讯云内网 Docker Hub 镜像源：

```text
mirror.ccs.tencentyun.com/15688463267/network-teaching-agent-sandbox:sha-<commit>
```

`ImageRegistryType` 固定为 `custom`。首次拉取需要 3–5 分钟，之后会命中镜像缓存。
AGS 在创建或更新 Tool 时会把 tag 解析成 `ImageDigest` 固定下来。

### 3.3 本地 CLI 原地更新 Tool

推荐原地更新，ToolId 和 ToolName 都不变：

```bash
tccli ags UpdateSandboxTool --region ap-shanghai \
  --ToolId sdt-rynngtwo \
  --CustomConfiguration '{
    "Image":"mirror.ccs.tencentyun.com/15688463267/network-teaching-agent-sandbox:sha-<commit>",
    "ImageRegistryType":"custom",
    "Command":["/opt/start.sh"],
    "Ports":[
      {"Name":"web","Port":9000,"Protocol":"TCP"},
      {"Name":"envd","Port":49983,"Protocol":"TCP"}
    ],
    "Resources":{"CPU":"1000m","Memory":"2Gi","Storage":"10Gi"},
    "Probe":{
      "HttpGet":{"Path":"/health","Port":49983,"Scheme":"HTTP"},
      "ReadyTimeoutMs":30000,
      "ProbeTimeoutMs":3000,
      "ProbePeriodMs":3000,
      "SuccessThreshold":1,
      "FailureThreshold":100
    }
  }'
```

注意：

- 建议每次传完整的 `CustomConfiguration`，不要只传 `Image`。
- `RoleArn`、`StorageMounts`、网络配置不会因为只更新 `CustomConfiguration` 而改变。
- 更新后确认状态和 digest：

```bash
tccli ags DescribeSandboxToolList --region ap-shanghai \
  --ToolIds '["sdt-rynngtwo"]'
```

### 3.4 启动沙盒实例

```bash
tccli ags StartSandboxInstance --region ap-shanghai \
  --ToolId sdt-rynngtwo \
  --Timeout 2h \
  --AuthMode PUBLIC
```

返回的 `InstanceId` 用于拼接访问地址：

```text
VSCode: https://9000-<instance-id>.ap-shanghai.tencentags.com/vscode/
Shell:  https://9000-<instance-id>.ap-shanghai.tencentags.com/ttyd/
健康检查: https://9000-<instance-id>.ap-shanghai.tencentags.com/health
```

需要 2C4G 时追加：

```bash
--CustomConfiguration '{"Resources":{"CPU":"2000m","Memory":"4Gi","Storage":"10Gi"}}'
```

### 3.5 验证

```bash
agr instance exec <instance-id> --region ap-shanghai --non-interactive -- bash -lc '
  echo "CPU: $(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us)/$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us)"
  if [ -f /sys/fs/cgroup/memory.max ]; then
    echo "Memory: $(cat /sys/fs/cgroup/memory.max)"
  else
    echo "Memory: $(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)"
  fi
  curl -s -o /dev/null -w "envd=%{http_code}\n" http://127.0.0.1:49983/health
  curl -s -L -o /dev/null -w "vscode=%{http_code}\n" http://127.0.0.1:9000/vscode/
  curl -s -o /dev/null -w "ttyd=%{http_code}\n" http://127.0.0.1:9000/ttyd/
'
```

预期：

```text
CPU: 100000/100000
Memory: 2147483648
envd=204
vscode=200
ttyd=200
```

### 3.6 新建 Tool 或改名

AGS 不支持原地修改 ToolName。需要换名字时：

1. `CreateSandboxTool` 创建新名字的 Tool，得到新的 `sdt-...`。
2. 更新应用配置里的 Tool 名称/ID。
3. 确认新 Tool 可用后，再删除旧 Tool。

当前 E2B 路径使用 Tool 名称：

```text
AGS_TOOL_NAME=network-teaching-agent-sandbox
```

AGS 原生 SDK 使用 Tool ID：

```text
AGS_TOOL_ID=sdt-rynngtwo
```

不要再用 `AGS_IMAGE_ID`，它既不是镜像 ID，也不是 Tool ID。

## 4. 停止与清理

```bash
# 停止实例
tccli ags StopSandboxInstance --region ap-shanghai \
  --InstanceId <instance-id>

# 删除 Tool
tccli ags DeleteSandboxTool --region ap-shanghai \
  --ToolId <tool-id>
```

## 注意

- `AuthMode PUBLIC` 下，拿到 URL 的人可以直接打开 IDE 和 Shell；长期使用建议增加应用层认证。
- 镜像地址必须使用 `mirror.ccs.tencentyun.com/...`，不要使用 `docker.io/...`。
- `personal` 类型只接受 `ccr.ccs.tencentyun.com` 域名，不适用于 Docker Hub。
- 生产环境建议把 Tool 固定到 `sha-<commit>`，不要依赖会移动的 `latest`。
