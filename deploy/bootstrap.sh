#!/usr/bin/env bash
# 服务器一次性初始化，sudo 执行，幂等。
# HTTPS 由系统级 Caddy 按域名分流，CD 不改 Caddy。
set -euo pipefail

DOMAIN="${DOMAIN:-network-agent.test.chatgqt.top}"
ACME_EMAIL="${ACME_EMAIL:-admin@chatgqt.top}"
DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
ROOT="${DEPLOY_ROOT:-/srv/network-teaching-agent}"
API_UID=10001
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CADDY_SNIPPET="$SCRIPT_DIR/Caddyfile"
CADDY_SITE=/etc/caddy/sites.d/network-agent.caddy

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
	echo "请用 sudo 执行本脚本" >&2
	exit 1
fi

log "docker"
getent group docker >/dev/null || groupadd docker
usermod -aG docker "$DEPLOY_USER"

log "caddy"
if ! command -v caddy >/dev/null; then
	apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq debian-keyring debian-archive-keyring \
		apt-transport-https curl gnupg
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' |
		gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
	curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
		>/etc/apt/sources.list.d/caddy-stable.list
	apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq caddy
fi
install -d -m 755 -o root -g caddy /etc/caddy/sites.d
if ! grep -q 'import /etc/caddy/sites.d/\*.caddy' /etc/caddy/Caddyfile; then
	if grep -q '^:80' /etc/caddy/Caddyfile; then
		printf '{\n\temail %s\n}\n\nimport /etc/caddy/sites.d/*.caddy\n' "$ACME_EMAIL" >/etc/caddy/Caddyfile
	else
		printf '\nimport /etc/caddy/sites.d/*.caddy\n' >>/etc/caddy/Caddyfile
	fi
fi
install -o root -g caddy -m 644 "$CADDY_SNIPPET" "$CADDY_SITE"
caddy validate --config /etc/caddy/Caddyfile
systemctl enable caddy >/dev/null 2>&1 || true
systemctl reload caddy 2>/dev/null || systemctl restart caddy

log "目录"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT"/{secrets,secrets/jwt}

log "JWT 密钥"
if [ ! -f "$ROOT/secrets/jwt/jwt_private.pem" ]; then
	openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
		-out "$ROOT/secrets/jwt/jwt_private.pem" 2>/dev/null
	openssl rsa -pubout -in "$ROOT/secrets/jwt/jwt_private.pem" \
		-out "$ROOT/secrets/jwt/jwt_public.pem" 2>/dev/null
fi
chown "$API_UID:$API_UID" "$ROOT/secrets/jwt/jwt_private.pem" "$ROOT/secrets/jwt/jwt_public.pem"
chmod 600 "$ROOT/secrets/jwt/jwt_private.pem"
chmod 644 "$ROOT/secrets/jwt/jwt_public.pem"

[ -s "$ROOT/.env" ] || echo "缺少 $ROOT/.env（从 apps/.env 复制并 chmod 600）" >&2
log "完成：$ROOT（域名 $DOMAIN 由 $CADDY_SITE 提供）"
