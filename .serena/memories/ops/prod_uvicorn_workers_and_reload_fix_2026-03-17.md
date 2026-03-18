时间：2026-03-17
背景：用户要求保留 lo1_new_server.yml 中镜像名手动处理，仅由我修正其余生产部署相关部分。
变更文件：
- backend/Dockerfile.prod
- lo1_new_server.yml
- configs/progress.md
- frontend/README.md
- backend/README.md
实现摘要：
1. backend/Dockerfile.prod：将生产启动命令从 `uvicorn ... --workers 1 --reload` 改为 `uvicorn ... --workers ${UVICORN_WORKERS:-2}`，移除 reload，并将 worker 数改为环境变量可配置。
2. lo1_new_server.yml：为 backend 容器新增 `UVICORN_WORKERS: ${UVICORN_WORKERS:-2}`。
3. 三个文档已同步记录本次生产启动参数修正及其原因。
结论：
- 重建并部署最新后端镜像后，Web 层默认 2 worker；
- 缓存发布链路仍会按当前代码启用独立发布进程与业务分块子进程；
- 用户仍需自行更新镜像 tag，使生产真正使用 2026-03-17 之后的最新镜像。