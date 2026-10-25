# syntax=docker/dockerfile:1
# 构建上下文：apps/agent-ui
# 前端只发相对路径（/api/v1、/agent），生产由宿主机 nginx 同源反代。
FROM node:24-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# vite.config.ts 通过 env.ts 读取这两个变量；生产构建只需要它们存在以便加载配置。
# 浏览器侧实际使用相对路径，不会把容器内地址打进产物。
ENV API_URL=http://api:8000 \
    AGENT_URL=http://agent:8000
RUN npm run build

FROM nginx:1.30-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
