# syntax=docker/dockerfile:1.7
FROM python:3.14-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive

# Mirror used while installing packages. CI can override this (for example
# with deb.debian.org) without changing the runtime mirror below.
ARG APT_MIRROR=mirrors.cloud.tencent.com

# Mirror written into the final image for runtime apt usage.
ARG RUNTIME_APT_MIRROR=mirrors.cloud.tencent.com

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Bootstrap CA certificates from the default mirror first.
# The slim base image may not include ca-certificates yet.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Switch to the build-time Debian mirror.
RUN set -e; \
    for f in /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list; do \
      [ -f "$f" ] || continue; \
      sed -i -E "s|https?://[^/]+/debian-security|http://${APT_MIRROR}/debian-security|g; s|https?://[^/]+/debian|http://${APT_MIRROR}/debian|g" "$f"; \
    done

# Prevent apt from trying to start services during build
RUN printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d \
    && chmod +x /usr/sbin/policy-rc.d

RUN apt-get update && apt-get install -y --no-install-recommends \
      coreutils ca-certificates curl git jq procps iproute2 less vim-tiny nano \
      util-linux nginx openssh-client libatomic1 \
      busybox traceroute iputils-ping xxd bsdextrautils \
      tcpdump bind9-dnsutils bind9-host netcat-openbsd mtr-tiny \
    && rm -rf /var/lib/apt/lists/*

# The base image ships Python 3.14 under /usr/local; make python3/python
# explicitly resolve to it as the system interpreter.
RUN ln -sf /usr/local/bin/python3.14 /usr/local/bin/python3 \
    && ln -sf /usr/local/bin/python3.14 /usr/local/bin/python \
    && python3 --version \
    && python --version \
    && pip --version

# AGS PUBLIC 出网 NAT 会改写 ICMP 错误包的内层源地址，标准 traceroute
# 依赖 IP_RECVERR 匹配不到，会全部显示 *；BusyBox 用 raw socket 按内层
# UDP 端口匹配，能正常显示路径。标准 /usr/sbin/traceroute 仍然保留，
# 方便对比 NAT 行为。
RUN rm -f /usr/local/bin/traceroute \
    && printf '#!/bin/sh\nexec /usr/bin/busybox traceroute -n -q 1 -w 1 "$@"\n' \
         > /usr/local/bin/traceroute \
    && chmod 755 /usr/local/bin/traceroute

# Point runtime apt sources at the Tencent Cloud mirror, even when the image
# was built with a different mirror (for example on GitHub Actions).
RUN set -e; \
    for f in /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list; do \
      [ -f "$f" ] || continue; \
      sed -i -E "s|https?://[^/]+/debian-security|http://${RUNTIME_APT_MIRROR}/debian-security|g; s|https?://[^/]+/debian|http://${RUNTIME_APT_MIRROR}/debian|g" "$f"; \
    done

# code-server: use the official amd64 tarball, bundled Node, no runtime download
COPY vendor/code-server-4.106.3-linux-amd64.tar.gz /tmp/code-server.tar.gz
RUN mkdir -p /usr/local/lib/code-server \
    && tar -xzf /tmp/code-server.tar.gz -C /usr/local/lib/code-server --strip-components=1 \
    && ln -s /usr/local/lib/code-server/bin/code-server /usr/local/bin/code-server \
    && rm -f /tmp/code-server.tar.gz \
    && code-server --version

# ttyd static binary
COPY vendor/ttyd.x86_64 /usr/local/bin/ttyd
RUN chmod 755 /usr/local/bin/ttyd && ttyd --version

# AGS management daemon
COPY --from=ccr.ccs.tencentyun.com/ags-image/envd:v0.5.14 \
     --chmod=755 /usr/bin/envd /usr/bin/envd

# Run everything as root; no dedicated user is kept in the image.
RUN mkdir -p /root/workspace /logs

# Course starter files baked into the default workspace.
COPY workspace/ /root/workspace/

COPY nginx.conf /etc/nginx/conf.d/sandbox.conf
COPY start.sh /opt/start.sh
RUN chmod 755 /opt/start.sh \
    && rm -f /etc/nginx/sites-enabled/default \
    && nginx -t

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    HOME=/root \
    PIP_BREAK_SYSTEM_PACKAGES=1

WORKDIR /root/workspace

EXPOSE 9000 49983
CMD ["/opt/start.sh"]
