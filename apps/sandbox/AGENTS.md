# AGS 沙盒

自定义 AGS 镜像：code-server、ttyd、envd、nginx。镜像由 GitHub Actions 构建并推送到 Docker Hub。

## Tool

- ToolName：`network-teaching-agent-sandbox`
- ToolId：`sdt-rynngtwo`
- 镜像：`mirror.ccs.tencentyun.com/15688463267/network-teaching-agent-sandbox:sha-<commit>`
- 端口 `9000` Web、`49983` envd；资源 `1C1G / 10GiB`；AuthMode `PUBLIC`

## 进程

- `nginx`：PID 1，`0.0.0.0:9000`；`envd`：`0.0.0.0:49983`
- `code-server`：`127.0.0.1:8080`；`ttyd`：`127.0.0.1:7681`
- 工作目录 `/home/user/workspace`，日志 `/logs/`

## 构建

改动 `Dockerfile`、`nginx.conf`、`start.sh`、`fetch-vendor.sh` 或 `.github/workflows/sandbox-image.yml` 后 push 到 `main` 触发构建。

```bash
gh workflow run sandbox-image.yml && gh run watch
```

产物：`15688463267/network-teaching-agent-sandbox:sha-<commit>`；AGS 使用 `mirror.ccs.tencentyun.com/15688463267/network-teaching-agent-sandbox:sha-<commit>`。

## 更新 Tool

```bash
tccli ags UpdateSandboxTool --region ap-shanghai --ToolId sdt-rynngtwo \
  --CustomConfiguration '{"Image":"mirror.ccs.tencentyun.com/15688463267/network-teaching-agent-sandbox:sha-<commit>","ImageRegistryType":"custom","Command":["/opt/start.sh"],"Ports":[{"Name":"web","Port":9000,"Protocol":"TCP"},{"Name":"envd","Port":49983,"Protocol":"TCP"}],"Resources":{"CPU":"1000m","Memory":"1Gi","Storage":"10Gi"}}'
```

`CustomConfiguration` 必须包含 `Image`、`ImageRegistryType`、`Command`、`Ports`、`Resources`；`ImageRegistryType` 固定为 `custom`。

```bash
tccli ags DescribeSandboxToolList --region ap-shanghai --ToolIds '["sdt-rynngtwo"]'
```

## 启动/停止

```bash
tccli ags StartSandboxInstance --region ap-shanghai --ToolId sdt-rynngtwo --Timeout 2h --AuthMode PUBLIC
tccli ags StopSandboxInstance --region ap-shanghai --InstanceId <instance-id>
```

## 约束

- 镜像必须使用 `mirror.ccs.tencentyun.com`；`AuthMode PUBLIC` 下 `9000` 无鉴权；生产固定 `sha-<commit>`；修改 ToolName 需新建 Tool。
- 使用 E2B `Sandbox.create` 时必须显式传 `network={"allow_public_traffic": True}`；否则 AGS 公网链接返回 `401`。
