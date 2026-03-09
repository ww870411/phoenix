时间：2026-03-09
主题：线上登录 504 故障排查（platform.smartview.top）

前置说明：
- 已执行 serena__activate_project 与 serena__check_onboarding_performed。
- 代码检索优先使用 Serena；文档留痕因 README/progress 为非符号大文件，使用 apply_patch 追加记录，属于仓库 AGENTS.md 允许的降级场景。

用户现象：
- 登录页点击“登录”后长时间等待。
- 用户提供文件 `configs/3.9 登录错误.md`，内容显示：
  - POST https://platform.smartview.top/api/v1/auth/login 504
  - 返回 Cloudflare `504 Gateway time-out` HTML 页面。

关键证据：
1. 前端登录链路
- `frontend/src/pages/LoginView.vue` 调用 auth store 的 `login(...)`。
- `frontend/src/projects/daily_report_25_26/services/api.js` 中 `login(credentials)` 固定请求 `${API_BASE}/auth/login`。

2. 后端登录链路
- `backend/api/v1/auth.py` 的 `/api/v1/auth/login` 仅调用 `auth_manager.login(...)`。
- `backend/services/auth_manager.py` 中 `login(...)` 主要执行：
  - 加载账号/权限 JSON
  - 校验用户名密码
  - 生成 session
  - remember=true 时调用 `_persist_session(...)` 写 PostgreSQL `auth_sessions`

3. 本地代码/容器验证
- 本地 `docker ps`：`phoenix_backend`、`phoenix_frontend`、`phoenix_db` 均在运行。
- `curl http://127.0.0.1:8001/healthz` 返回 200。
- `curl http://127.0.0.1:8001/api/v1/auth/me` 返回 401（缺少认证信息），为预期行为。
- 本地 `docker logs phoenix_backend` 中可见 `POST /api/v1/auth/login` 返回 200 OK。

4. 部署结构比对
- `docker-compose.server.yml` / `docker-compose.server_new_server.yml` 的生产结构是 `web -> backend -> db`。
- Nginx 配置 `deploy/nginx.prod.conf` 与 `deploy/nginx.http-only.conf` 均通过 `proxy_pass http://backend:8000` 转发 `/api/`。
- 生产容器名应重点关注：`phoenix-web`、`phoenix-backend`、`phoenix-db`。
- 本地当前运行的是开发态容器名：`phoenix_frontend`、`phoenix_backend`、`phoenix_db`。

结论：
- 当前最可能根因不是仓库登录代码回归，而是服务器部署/回源链路异常。
- 504 表明线上入口已收到 `/api/v1/auth/login`，但服务器把 `/api` 转发给 Phoenix backend 时超时。
- 优先怀疑两类问题：
  1) `web` 容器无法正确访问 `backend`（网络、错误栈、错误容器、旧 upstream IP）；
  2) `backend` 在处理登录时访问 PostgreSQL 卡住（尤其 remember 登录涉及 `auth_sessions` 持久化）。

建议的服务器核查顺序：
1. 确认线上当前运行的是哪套 compose 容器，而非开发态容器。
2. 确认 `phoenix-web` 和 `phoenix-backend` 在同一 network（通常 `phoenix_phoenix_net`）。
3. 在 `phoenix-web` 容器内执行：
   - `curl http://backend:8000/healthz`
   - `curl -i -X POST http://backend:8000/api/v1/auth/login ...`
4. 查看 `phoenix-web` Nginx error log 与 `phoenix-backend` 日志。
5. 若 backend 收到请求但迟迟不回，继续检查 PostgreSQL 连接、锁等待、崩溃恢复。

本轮变更：
- 更新 `configs/progress.md`
- 更新 `frontend/README.md`
- 更新 `backend/README.md`

验证状态：
- 仅完成代码链路与本地容器验证，未直接登录用户服务器执行修复。