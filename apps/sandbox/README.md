# AGS VSCode + Web Shell 沙盒

自定义 AGS 镜像，包含：

- **code-server**（浏览器版 VSCode）：`/vscode/`
- **ttyd**（Web Shell）：`/ttyd/`
- **envd**（`49983`）：AGS 管理面
- **nginx**（`9000`）：统一入口

镜像只通过 GitHub Actions 构建并推送到 Docker Hub。AGS 使用腾讯云内网镜像源
`mirror.ccs.tencentyun.com` 拉取公开镜像。

## 文件

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 镜像构建 |
| `nginx.conf` | 反向代理和 WebSocket |
| `start.sh` | 启动 envd / code-server / ttyd / nginx |
| `fetch-vendor.sh` | CI 构建前下载 code-server / ttyd |
| `.gitignore` | 忽略 `vendor/` 和日志 |

## 构建

工作流：`.github/workflows/sandbox-image.yml`

触发方式：

- push 到 `main`，且改动 `Dockerfile`、`nginx.conf`、`start.sh`、`fetch-vendor.sh`
- 手动执行：`gh workflow run sandbox-image.yml`

流程：

```text
fetch-vendor.sh
  → docker buildx build --platform linux/amd64
  → push Docker Hub
  → tags: latest, sha-<commit>
```

需要 GitHub Secrets：

| Secret | 值 |
|---|---|
| `DOCKERHUB_USERNAME` | `15688463267` |
| `DOCKERHUB_TOKEN` | Docker Hub PAT（Read & Write） |

Docker Hub 仓库：

```text
15688463267/network-teaching-agent-sandbox
```

## AGS 镜像地址

AGS 不能直接使用 `docker.io/...`。使用腾讯云内网镜像源：

```text
mirror.ccs.tencentyun.com/15688463267/network-teaching-agent-sandbox:<tag>
```

`ImageRegistryType` 固定为 `custom`。首次创建工具需要 3–5 分钟拉取镜像；
AGS 会把 tag 解析成 `ImageDigest` 固定下来。

当前验证过的 tag 是 `sha-1d5f643`：

```text
sha256:518a4747709766e940a6ccc46a4cfca5b4933fd469b268fa81f37b096f558e8c
```

## 创建 AGS 工具

```bash
tccli ags CreateSandboxTool --region ap-shanghai \
  --ToolName dev-sandbox-dockerhub \
  --ToolType custom \
  --Description "VSCode + Web Shell 沙盒（1C2G）" \
  --NetworkConfiguration '{"NetworkMode":"PUBLIC"}' \
  --DefaultTimeout 30m \
  --RoleArn 'qcs::cam::uin/100037354656:roleName/ai-game-platform-test-role' \
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

确认状态为 `ACTIVE`：

```bash
tccli ags DescribeSandboxToolList --region ap-shanghai --Limit 20
```

## 启动实例

必须使用 `AuthMode PUBLIC`，否则 VSCode 的 WebSocket 会因为子请求不带
`access_token` 报 `1006`。

```bash
tccli ags StartSandboxInstance --region ap-shanghai \
  --ToolId <tool-id> \
  --Timeout 2h \
  --AuthMode PUBLIC
```

工具默认 1C2G。需要 2C4G 时追加：

```bash
--CustomConfiguration '{"Resources":{"CPU":"2000m","Memory":"4Gi","Storage":"10Gi"}}'
```

## 访问

```text
VSCode: https://9000-<instance-id>.ap-shanghai.tencentags.com/vscode/
Shell:  https://9000-<instance-id>.ap-shanghai.tencentags.com/ttyd/
健康检查: https://9000-<instance-id>.ap-shanghai.tencentags.com/health
```

code-server、ttyd 和 agent 的 shell 默认工作目录统一为 `/home/user/workspace`。

## 验证

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

## 停止与清理

```bash
tccli ags StopSandboxInstance --region ap-shanghai --InstanceId <instance-id>
tccli ags DeleteSandboxTool --region ap-shanghai --ToolId <tool-id>
```

## 注意

- `AuthMode PUBLIC` 下，拿到 URL 的人可以直接打开 IDE 和 Shell；长期使用建议增加应用层认证。
- 镜像地址必须使用 `mirror.ccs.tencentyun.com/...`，不要使用 `docker.io/...`。
- `personal` 类型只接受 `ccr.ccs.tencentyun.com` 域名，不适用于 Docker Hub。
- 更新镜像后需要创建新的 Sandbox Tool；已创建的工具固定使用创建时的 digest。
