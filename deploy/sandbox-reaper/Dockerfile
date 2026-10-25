# syntax=docker/dockerfile:1.7
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates cron util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.12.23

WORKDIR /app

RUN mkdir -p /run/secrets

COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/api/app ./app
COPY deploy/sandbox-reaper/crontab /etc/cron.d/sandbox-reaper
COPY deploy/sandbox-reaper/entrypoint.sh /usr/local/bin/reaper-entrypoint
RUN chmod 0644 /etc/cron.d/sandbox-reaper \
    && chmod 0755 /usr/local/bin/reaper-entrypoint

ENTRYPOINT ["/usr/local/bin/reaper-entrypoint"]
CMD ["cron", "-f"]
