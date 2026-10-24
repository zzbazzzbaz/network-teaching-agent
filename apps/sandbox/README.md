# AGS VSCode + Web Shell 沙盒

基于 AGS 自定义镜像的沙盒，提供：

- **code-server**（浏览器版 VSCode）：`/vscode/`
- **ttyd**（Web Shell）：`/ttyd/`
- **envd**（`49983`，AGS 管理面：命令执行、文件读写、健康检查）
- **nginx**（`9000`，统一 Web 入口）

工具使用 `custom` 类型创建，因此支持 1C2G、2C4G 等自定义规格。AIO 类型固定 4C8G，无法修改。

## 目录结构

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 镜像构建 |
| `nginx.conf` | `/vscode/`、`/ttyd/`、`/health` 和 WebSocket 反向代理 |
| `start.sh` | 启动 envd、code-server、ttyd、nginx |
| `fetch-vendor.sh` | 下载固定版本的 code-server / ttyd 到 `vendor/` |
| `vendor/` | 本地构建输入，已被 git 忽略 |

## 构建镜像

### GitHub Actions（推荐）

推送到 `main` 且改动 `apps/sandbox/**` 时，仓库根目录的
`.github/workflows/sandbox-image.yml` 会自动：

1. 下载 code-server / ttyd 到 `vendor/`
2. 用 Buildx 构建 `linux/amd64` 镜像
3. 推送到 Docker Hub 公开仓库
   `15688463267/network-teaching-agent-sandbox`
4. 生成 `latest` 和 `sha-<commit>` 两个标签

首次使用需要在 GitHub 仓库的
Settings → Secrets and variables → Actions 中添加：

| Secret | 值 |
|---|---|
| `DOCKERHUB_USERNAME` | `15688463267` |
| `DOCKERHUB_TOKEN` | Docker Hub PAT，至少 Read & Write |

也可以手动触发：

```bash
gh workflow run sandbox-image.yml
gh run watch
```

镜像构建完成后，工作流 Summary 会输出镜像 digest。AGS 拉取时使用 `latest`
或固定的 `sha-<commit>` 标签。

### 本地构建（可选）

```bash
./fetch-vendor.sh

docker build --platform=linux/amd64 -t dev-sandbox:v2 .

docker tag dev-sandbox:v2 ccr.ccs.tencentyun.com/aigame/dev-sandbox:v2
docker push ccr.ccs.tencentyun.com/aigame/dev-sandbox:v2
```

`vendor/` 只保留在本地，不提交到 git。换一台机器构建前，先执行一次
`./fetch-vendor.sh`。

## 创建 AGS 沙箱工具

```bash
tccli ags CreateSandboxTool --region ap-shanghai \
  --ToolName dev-sandbox-2c4g \
  --ToolType custom \
  --Description "VSCode + Web Shell 沙盒（Docker Hub）" \
  --NetworkConfiguration '{"NetworkMode":"PUBLIC"}' \
  --DefaultTimeout 30m \
  --RoleArn 'qcs::cam::uin/100037354656:roleName/ai-game-platform-test-role' \
  --CustomConfiguration '{
    "Image":"docker.io/15688463267/network-teaching-agent-sandbox:latest",
    "ImageRegistryType":"custom",
    "Command":["/opt/start.sh"],
    "Ports":[
      {"Name":"web","Port":9000,"Protocol":"TCP"},
      {"Name":"envd","Port":49983,"Protocol":"TCP"}
    ],
    "Resources":{"CPU":"2000m","Memory":"4Gi","Storage":"10Gi"},
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

`ImageRegistryType` 使用 `custom` 表示第三方公开镜像仓库。Docker Hub 仓库必须
是 **Public**；AGS 会通过腾讯云的公开镜像源拉取，不需要在工具里配置 Docker Hub
用户名和密码。

如果仍使用腾讯云 CCR 个人版，把 `Image` 改回
`ccr.ccs.tencentyun.com/aigame/dev-sandbox:v2`，并把 `ImageRegistryType` 改成
`personal`。

## 启动实例

**重要：必须使用 `AuthMode PUBLIC`。**

浏览器加载页面后，后续的 JS、CSS、字体和 WebSocket 请求不会携带 AGS 的 `access_token`。如果使用默认的 `DEFAULT` 模式，这些请求会返回 401，VSCode 工作台会报 WebSocket `1006` 错误。

`PUBLIC` 的语义是：`49983`（envd）仍需要 token，其他端口不需要。这样 VSCode 和 ttyd 才能正常工作。

```bash
tccli ags StartSandboxInstance --region ap-shanghai \
  --ToolId <tool-id> \
  --Timeout 2h \
  --AuthMode PUBLIC
```

### 1C2G 实例级覆盖

`custom` 类型支持按实例覆盖资源，同一个工具可以启动 1C2G 沙盒：

```bash
tccli ags StartSandboxInstance --region ap-shanghai \
  --ToolId <tool-id> \
  --Timeout 2h \
  --AuthMode PUBLIC \
  --CustomConfiguration '{"Resources":{"CPU":"1000m","Memory":"2Gi","Storage":"10Gi"}}'
```

该方式对 `aio` 类型无效，AIO 始终是 4C8G。

## 访问地址

根据实例 ID 拼接：

```text
VSCode: https://9000-<instance-id>.ap-shanghai.tencentags.com/vscode/
Shell:  https://9000-<instance-id>.ap-shanghai.tencentags.com/ttyd/
健康检查: https://9000-<instance-id>.ap-shanghai.tencentags.com/health
```

## 安全说明

`AuthMode PUBLIC` 意味着：**任何拿到 URL 的人都能打开 IDE 和 Shell**。

如果沙盒需要长期运行或多人共享，建议增加应用层认证，例如：

- code-server 使用 `--auth password`；
- ttyd 使用 `--credential`；
- 或在前面再加一层带认证的反向代理。

## 进入沙盒验证

```bash
agr instance exec <instance-id> --region ap-shanghai --non-interactive -- bash -lc '
  echo "CPU 配额: $(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us)/$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us)"

  if [ -f /sys/fs/cgroup/memory.max ]; then
    echo "内存上限: $(cat /sys/fs/cgroup/memory.max)"
  else
    echo "内存上限: $(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)"
  fi

  ps -eo pid,user,comm,args | grep -E "envd|code-server|ttyd|nginx" | grep -v grep

  curl -s -o /dev/null -w "envd=%{http_code}\n" http://127.0.0.1:49983/health
  curl -s -L -o /dev/null -w "vscode=%{http_code}\n" http://127.0.0.1:9000/vscode/
  curl -s -o /dev/null -w "ttyd=%{http_code}\n" http://127.0.0.1:9000/ttyd/
'
```

预期结果：

| 规格 | CPU quota | 内存上限 |
|---|---|---|
| 2C4G | `200000/100000`（2 核） | `4294967296`（4 GiB） |
| 1C2G | `100000/100000`（1 核） | `2147483648`（2 GiB） |

服务健康检查：

```text
envd=204
vscode=200
ttyd=200
```

## 停止与清理

```bash
# 停止实例
tccli ags StopSandboxInstance --region ap-shanghai \
  --InstanceId <instance-id>

# 删除工具
tccli ags DeleteSandboxTool --region ap-shanghai \
  --ToolId <tool-id>
```

## 常见问题

### VSCode 报 WebSocket 1006

检查启动实例时是否使用了 `--AuthMode PUBLIC`。默认的 `DEFAULT` 模式会拦截不带 token 的子请求和 WebSocket。

### 实例一直无法进入 RUNNING

按顺序检查：

1. 镜像是否为 `linux/amd64`；
2. 镜像地址和 CAM 角色是否可拉取；
3. `/usr/bin/envd` 是否存在且可执行；
4. 健康检查是否配置为 `49983/health`；
5. `start.sh` 是否正常启动了 nginx、code-server、ttyd。

### 1C2G 覆盖不生效

确认工具类型是 `custom`。`aio` 类型会忽略资源覆盖，始终使用 4C8G。
