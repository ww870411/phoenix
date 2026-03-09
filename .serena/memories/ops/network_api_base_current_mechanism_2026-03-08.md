时间：2026-03-08
主题：Phoenix 当前前端访问后端 API 与地址配置机制核对。

关键结论：
1) 后端统一前缀为 /api/v1（backend/main.py: API_PREFIX='/api', API_VERSION='v1', include_router 挂载）。
2) 前端 API 基址来自 VITE_API_BASE；若为空默认 /api/v1；若未带 /api 前缀会自动补齐。
3) 本机开发下新增 same-origin 优先策略：当前端 origin 与 base 都是 localhost/127.0.0.1 时，API_BASE 强制 '/api/v1'，优先走 Vite 代理，规避 CORS。
4) 开发编排：frontend 在 5173，backend 外部映射 8001:8000；Vite 代理 '/api' -> http://backend:8000（容器内服务名）。
5) 开发环境文件 frontend/.env.development 仍有 VITE_API_BASE=http://127.0.0.1:8001；但 same-origin 策略可将本机请求转为 '/api/v1'。
6) 生产构建默认 VITE_API_BASE=/api/v1（frontend/Dockerfile.prod 与 deploy/Dockerfile.web 构建参数）。
7) 生产 Nginx（deploy/nginx.prod.conf 或 http-only 版本）均将 /api/ 反代到 http://backend:8000，浏览器不感知 backend 容器地址。
8) server_new_server 编排中 web 暴露 8001:80，backend 不对外映射，web 与 backend 通过 docker network（phoenix_net）互通。

涉及证据文件：
- frontend/src/projects/daily_report_25_26/services/api.js
- frontend/vite.config.js
- frontend/.env.development
- backend/main.py
- docker-compose.yml
- docker-compose.server_new_server.yml
- deploy/nginx.prod.conf
- deploy/nginx.http-only.conf
- frontend/Dockerfile.prod
- deploy/Dockerfile.web