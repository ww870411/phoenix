时间：2025-11-01
主题：ww.ps1 与 ww-http-only.yml 目的与结构梳理
结论：
- ww.ps1 是用于 Phoenix 项目（backend + frontend）镜像构建与推送的 PowerShell 脚本。核心流程：
  1) 生成时间戳/读取环境变量 → 组装镜像名（默认注册用户 ww870411）。
  2) 处理前端 VITE_API_BASE：仅在 http/https 绝对 URL 时作为 build-arg 传入，否则使用源码默认 “/api/v1”。
  3) 构建并推送：
     - 后端镜像（Dockerfile.prod）
     - 前端镜像（deploy/Dockerfile.web）
     - 前端 HTTP-only 变体镜像（额外 build-arg HTTP_ONLY=true）
  4) 对每个镜像：按时间戳 tag 推送，并额外 tag 为 latest 再推送。
  5) 支持 NO_CACHE=1 触发无缓存构建，BUILD_TIMESTAMP 作为构建参数注入。
- ww-http-only.yml 是 Docker Compose（HTTP-only 部署）编排文件：
  - services/backend：镜像名来自 BACKEND_IMAGE，挂载 /app/data（宿主 /home/ww870411/25-26/backend_data），数据库连接通过 DATABASE_URL 环境变量注入。
  - services/db：Postgres 15，健康检查 pg_isready，命名卷 db_data。
  - services/web（HTTP-only）：镜像名来自 WEB_HTTP_IMAGE，映射 80:80。
  - 使用 bridge 网络 phoenix_net。
留痕/偏差：
- 当前运行环境为只读（sandbox read-only），未能按“每次对话写入 configs/progress.md 和更新 backend/frontend README”执行持久化记录；待获得写权限后补录。
- 本次仅进行只读分析，未改动任何文件。
建议：
- 若需构建推送：PowerShell 执行 .\ww.ps1（可设 NO_CACHE=1，或设 VITE_API_BASE 为绝对 URL）。
- 若需部署 HTTP-only：docker compose -f ww-http-only.yml up -d（确保 BACKEND_IMAGE/WEB_HTTP_IMAGE 环境变量已指向目标标签）。
证据：
- 文件：D:\编程项目\phoenix\ww.ps1, D:\编程项目\phoenix\ww-http-only.yml