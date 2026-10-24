#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR=/home/user/workspace

mkdir -p /logs "$WORKSPACE_DIR" /home/user/.config /home/user/.local/share
chown -R user:user /home/user /logs

# envd: AGS management daemon on 49983
(
  while true; do
    /usr/bin/envd
    echo "[$(date -Is)] envd exited, restarting..." >&2
    sleep 1
  done
) >>/logs/envd.log 2>&1 &

# code-server: browser VSCode on 127.0.0.1:8080
(
  while true; do
    runuser -u user -- env HOME=/home/user \
      code-server \
        --bind-addr 127.0.0.1:8080 \
        --auth none \
        --abs-proxy-base-path=/vscode \
        --disable-telemetry \
        --disable-update-check \
        "$WORKSPACE_DIR"
    echo "[$(date -Is)] code-server exited, restarting..." >&2
    sleep 1
  done
) >>/logs/code-server.log 2>&1 &

# ttyd: web shell on 127.0.0.1:7681, starting in the shared workspace
(
  while true; do
    runuser -u user -- env HOME=/home/user \
      ttyd \
        --port 7681 \
        --interface 127.0.0.1 \
        --base-path /ttyd \
        --writable \
        /bin/bash -c "cd $WORKSPACE_DIR && exec /bin/bash -l"
    echo "[$(date -Is)] ttyd exited, restarting..." >&2
    sleep 1
  done
) >>/logs/ttyd.log 2>&1 &

exec nginx -g 'daemon off;'
