#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p vendor

CODE_SERVER_VERSION="${CODE_SERVER_VERSION:-4.106.3}"
TTYD_VERSION="${TTYD_VERSION:-1.7.7}"

# Use an empty MIRROR to download directly from GitHub (for example in CI).
# The default proxy is useful from networks where GitHub releases are slow.
MIRROR="${MIRROR-https://gh-proxy.com/}"

fetch() {
  local url="$1"
  local out="$2"

  if [ -s "$out" ]; then
    echo "using cached $out"
    return 0
  fi

  echo "downloading $out"
  curl -fL --retry 3 -o "$out" "${MIRROR}${url}"
}

fetch \
  "https://github.com/coder/code-server/releases/download/v${CODE_SERVER_VERSION}/code-server-${CODE_SERVER_VERSION}-linux-amd64.tar.gz" \
  "vendor/code-server-${CODE_SERVER_VERSION}-linux-amd64.tar.gz"

fetch \
  "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.x86_64" \
  "vendor/ttyd.x86_64"

chmod 755 vendor/ttyd.x86_64
ls -lh vendor
