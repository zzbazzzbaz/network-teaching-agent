# syntax=docker/dockerfile:1
FROM langchain/langgraph-api:0.16.5-py3.14

ADD . /deps/agent

# 基础镜像把 OTel 锁在 1.42.1，与 langfuse 5.x 冲突；版本由 pyproject 的 override 决定
RUN grep -v -E '^opentelemetry-' /api/constraints.txt > /tmp/constraints.txt

RUN for dep in /deps/*; do \
        if [ -d "$dep" ]; then \
            (cd "$dep" && PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir -c /tmp/constraints.txt -e .); \
        fi; \
    done

ENV LANGGRAPH_AUTH='{"path": "/deps/agent/agent/core/auth.py:auth"}'
ENV LANGSERVE_GRAPHS='{"exp_agent": "/deps/agent/agent/main.py:build_exp_agent", "teach_agent": "/deps/agent/agent/main.py:build_teach_agent"}'

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
