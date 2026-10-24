ENV_FILE := $(CURDIR)/apps/.env
COMPOSE  := docker compose -f apps/docker-compose.dev.yml

up:
	cd apps && docker compose -f docker-compose.dev.yml up -d --wait

down:
	cd apps && docker compose -f docker-compose.dev.yml down

install:
	cd apps/api && uv sync
	cd apps/agent && uv sync
	cd apps/agent-ui && npm ci

jwt-keys:
	cd apps/api && mkdir -p .keys \
		&& openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out .keys/jwt_private.pem \
		&& openssl rsa -pubout -in .keys/jwt_private.pem -out .keys/jwt_public.pem \
		&& echo "已生成 apps/api/.keys/jwt_{private,public}.pem"

run-api:
	cd apps/api && uv run --env-file $(ENV_FILE) fastapi run --no-reload --port 8000

run-agent:
	cd apps/agent && uv run --env-file $(ENV_FILE) langgraph dev --no-reload --n-jobs-per-worker 4

run-ui:
	cd apps/agent-ui && npm run dev

dev:
	@echo "启动 agent (:2024) / api (:8000) / agent-ui (:5173)，Ctrl-C 退出"
	$(MAKE) -j3 run-agent run-api run-ui

test:
	cd apps/api && uv run pytest
