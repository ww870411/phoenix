###########
# Builder #
###########
FROM node:20-alpine AS builder
WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci --prefer-offline --no-audit --progress=false

COPY frontend/ ./
RUN npm run build

##########
# Runner #
##########
FROM nginx:alpine AS runner

# 将自定义 nginx 配置拷贝进来，反向代理 /api 到 backend 服务
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 静态资源
COPY --from=builder /app/dist/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

