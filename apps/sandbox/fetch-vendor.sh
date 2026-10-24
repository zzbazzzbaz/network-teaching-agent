#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p vendor

CODE_SERVER_VERSION="${CODE_SERVER_VERSION:-4.106.3}"
TTYD_VERSION="${TTYD_VERSION:-1.7.7}"
MIRROR="${MIRROR:-https://gh-proxy.com/}"

curl -fL --retry 3 -o "vendor/code-server-${CODE_SERVER_VERSION}-linux-amd64.tar.gz" \
  "${MIRROR}https://github.com/coder/code-server/releases/download/v${CODE_SERVER_VERSION}/code-server-${CODE_SERVER_VERSION}-linux-amd64.tar.gz"

curl -fL --retry 3 -o vendor/ttyd.x86_64 \
  "${MIRROR}https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.x86_64"

chmod 755 vendor/ttyd.x86_64
ls -lh vendor
