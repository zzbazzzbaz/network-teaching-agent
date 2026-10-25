#!/bin/sh
set -eu

APP_ENV=/run/secrets/app.env
REAPER_ENV=/etc/reaper.env

required_keys="
DB_DATABASE_URL
E2B_DOMAIN
E2B_API_KEY
AGS_TOOL_NAME
AGS_SANDBOX_TIMEOUT_SECONDS
AGS_SANDBOX_IDLE_SECONDS
AGS_SANDBOX_PAUSED_RETENTION_SECONDS
AGS_SANDBOX_MAX_LIFETIME_SECONDS
AGS_SANDBOX_HEARTBEAT_SECONDS
JWT_PRIVATE_KEY_PATH
JWT_PUBLIC_KEY_PATH
CORS_ORIGINS
"

if [ ! -f "$APP_ENV" ]; then
  echo "missing $APP_ENV" >&2
  exit 1
fi

: > "$REAPER_ENV"
missing=""
for key in $required_keys; do
  line="$(grep -m 1 "^${key}=" "$APP_ENV" || true)"
  if [ -z "$line" ]; then
    missing="$missing $key"
  else
    printf '%s\n' "$line" >> "$REAPER_ENV"
  fi
done

if [ -n "$missing" ]; then
  echo "missing required env:$missing" >&2
  exit 1
fi

chmod 0600 "$REAPER_ENV"
exec "$@"
