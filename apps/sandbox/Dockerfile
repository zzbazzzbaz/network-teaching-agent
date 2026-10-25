# syntax=docker/dockerfile:1.7
FROM node:22-bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive

# Mirror used while installing packages. CI can override this (for example
# with deb.debian.org) without changing the runtime mirror below.
ARG APT_MIRROR=mirrors.cloud.tencent.com

# Mirror written into the final image for runtime apt usage.
ARG RUNTIME_APT_MIRROR=mirrors.cloud.tencent.com

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Bootstrap CA certificates from the default mirror first.
# The Node base image has no ca-certificates, so HTTPS mirrors cannot be used yet.
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
      util-linux python3 python3-pip python3-venv \
      nginx openssh-client \
    && rm -rf /var/lib/apt/lists/*

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
