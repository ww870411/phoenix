# 2025-11-10 后端容器缺失 psycopg2 依赖
- 现象：远端部署后 `/api/v1/auth/login` 全部 404，backend 日志报 `Failed to import v1 routes: No module named 'psycopg2'`，导致 v1_router 未挂载。
- 处理：在 backend/requirements.txt 新增 `psycopg2-binary`，重新构建镜像即可恢复 PostgreSQL 驱动。
- 验证：重建推送镜像后，`docker logs phoenix-backend` 中应看到 `Mounted v1 router at /api/v1`，curl `/api/v1/auth/login` 不再 404。