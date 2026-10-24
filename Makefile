# 计算机网络教学智能体 —— 本地开发入口
#
# 常用：
#   make dev      # 一键启动 Postgres + agent + api + agent-ui
#   make up       # 仅启动 apps/docker-compose.dev.yml
#   make agent    # 启动 LangGraph agent（:2024）
#   make api      # 启动 FastAPI（:8000）
#   make ui       # 启动 agent-ui（:5173）
#   make down     # 停止 Postgres

SHELL := /bin/bash

APPS_DIR    := apps
COMPOSE     := docker compose -f $(APPS_DIR)/docker-compose.dev.yml
AGENT_DIR   := $(APPS_DIR)/agent
API_DIR     := $(APPS_DIR)/api
UI_DIR      := $(APPS_DIR)/agent-ui

AGENT_PORT  ?= 2024
API_PORT    ?= 8000

.DEFAULT_GOAL := help

.PHONY: help install up down logs ps agent api ui dev

help: ## 显示帮助
	@echo "计算机网络教学智能体 —— 本地开发"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "端口：agent $(AGENT_PORT) | api $(API_PORT) | agent-ui 5173"

install: ## 安装三个应用的依赖
	cd $(AGENT_DIR) && uv sync
	cd $(API_DIR) && uv sync
	cd $(UI_DIR) && npm ci

up: ## 启动 docker-compose.dev.yml（Postgres，等待 healthy）
	$(COMPOSE) up -d --wait

down: ## 停止并移除 docker-compose 服务（保留数据卷）
	$(COMPOSE) down

logs: ## 跟随 docker-compose 日志
	$(COMPOSE) logs -f

ps: ## 查看 docker-compose 服务状态
	$(COMPOSE) ps

agent: ## 启动 agent（LangGraph dev server）
	cd $(AGENT_DIR) && uv run langgraph dev --port $(AGENT_PORT) --no-browser

api: ## 启动 api（FastAPI dev server）
	cd $(API_DIR) && uv run fastapi dev app/main.py --port $(API_PORT)

ui: ## 启动 agent-ui（Vite dev server）
	cd $(UI_DIR) && npm run dev

dev: up ## 一键启动全部服务（Ctrl-C 同时退出）
	@set -euo pipefail; \
	pids=""; \
	cleanup() { \
		trap - INT TERM EXIT; \
		[ -z "$$pids" ] || kill $$pids 2>/dev/null || true; \
	}; \
	trap cleanup INT TERM EXIT; \
	echo "启动 agent (:$(AGENT_PORT)) / api (:$(API_PORT)) / agent-ui (:5173)，Ctrl-C 退出"; \
	( cd $(AGENT_DIR) && exec uv run langgraph dev --port $(AGENT_PORT) --no-browser ) & pids="$$pids $$!"; \
	( cd $(API_DIR) && exec uv run fastapi dev app/main.py --port $(API_PORT) ) & pids="$$pids $$!"; \
	( cd $(UI_DIR) && exec npm run dev ) & pids="$$pids $$!"; \
	wait
