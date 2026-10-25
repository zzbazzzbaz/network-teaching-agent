#!/usr/bin/env bash
# 服务器一次性初始化，sudo 执行，幂等。
set -euo pipefail

DOMAIN="${DOMAIN:-network-agent.test.chatgqt.top}"
ACME_EMAIL="${ACME_EMAIL:-admin@chatgqt.top}"
DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
ROOT="${DEPLOY_ROOT:-/srv/network-teaching-agent}"
API_UID=10001
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF="$SCRIPT_DIR/nginx.conf"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
	echo "请用 sudo 执行本脚本" >&2
	exit 1
fi

log "docker"
getent group docker >/dev/null || groupadd docker
usermod -aG docker "$DEPLOY_USER"

log "nginx / certbot"
command -v nginx >/dev/null || {
	apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx
}
command -v certbot >/dev/null || {
	apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot python3-certbot-nginx
}
install -d -m 755 /var/www/certbot

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

log "nginx 站点 / 证书"
[ -f "$NGINX_CONF" ] || {
	echo "缺少 $NGINX_CONF" >&2
	exit 1
}

CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
if [ ! -f "$CERT" ]; then
	BOOTSTRAP_CONF=/etc/nginx/sites-available/network-agent-bootstrap
	rm -f /etc/nginx/sites-enabled/network-agent
	cat >"$BOOTSTRAP_CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    location ^~ /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 404; }
}
EOF
	ln -sfn "$BOOTSTRAP_CONF" /etc/nginx/sites-enabled/network-agent
	nginx -t
	systemctl reload nginx
	certbot certonly --nginx -d "$DOMAIN" \
		--non-interactive --agree-tos --email "$ACME_EMAIL" --keep-until-expiring
	rm -f /etc/nginx/sites-enabled/network-agent "$BOOTSTRAP_CONF"
fi

install -m 644 "$NGINX_CONF" /etc/nginx/sites-available/network-agent
ln -sfn /etc/nginx/sites-available/network-agent /etc/nginx/sites-enabled/network-agent
nginx -t
systemctl reload nginx
systemctl enable --now certbot.timer >/dev/null 2>&1 || true

install -d -m 755 /etc/letsencrypt/renewal-hooks/deploy
cat >/etc/letsencrypt/renewal-hooks/deploy/reload-nginx <<'EOF'
#!/bin/sh
set -e
nginx -t
systemctl reload nginx
EOF
chmod 755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx

rm -f /etc/sudoers.d/network-agent-deploy

[ -s "$ROOT/.env" ] || echo "缺少 $ROOT/.env（从 apps/.env 复制并 chmod 600）" >&2
log "完成：$ROOT"
