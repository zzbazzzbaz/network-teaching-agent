# syntax=docker/dockerfile:1
# 构建上下文：apps/agent
# 由 `uv run langgraph dockerfile` 生成后固化，仅把基础镜像从浮动的 :3.14 锚定到具体版本。
# ⚠️ apps/agent/langgraph.json 变更后需重新生成（graph / auth 路径写死在下面的 ENV）。
FROM langchain/langgraph-api:0.16.5-py3.14

ADD . /deps/agent

RUN for dep in /deps/*; do \
        if [ -d "$dep" ]; then \
            (cd "$dep" && PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir -c /api/constraints.txt -e .); \
        fi; \
    done

ENV LANGGRAPH_AUTH='{"path": "/deps/agent/agent/core/auth.py:auth"}'
ENV LANGSERVE_GRAPHS='{"exp_agent": "/deps/agent/agent/main.py:build_exp_agent"}'

RUN mkdir -p /api/langgraph_api /api/langgraph_runtime /api/langgraph_license \
 && touch /api/langgraph_api/__init__.py /api/langgraph_runtime/__init__.py /api/langgraph_license/__init__.py
RUN PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir --no-deps -e /api

RUN pip uninstall -y pip setuptools wheel
RUN rm -rf /usr/local/lib/python*/site-packages/pip* /usr/local/lib/python*/site-packages/setuptools* /usr/local/lib/python*/site-packages/wheel* \
 && find /usr/local/bin -name "pip*" -delete || true
RUN rm -rf /usr/lib/python*/site-packages/pip* /usr/lib/python*/site-packages/setuptools* /usr/lib/python*/site-packages/wheel* \
 && find /usr/bin -name "pip*" -delete || true
RUN uv pip uninstall --system pip setuptools wheel && rm /usr/bin/uv /usr/bin/uvx

WORKDIR /deps/agent
