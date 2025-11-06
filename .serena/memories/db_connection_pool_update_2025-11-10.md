# 2025-11-10 数据库连接池扩容
- 背景：仪表盘高频刷新导致 SQLAlchemy QueuePool 抛出 `TimeoutError`（size 5 overflow 10 reached, timeout 30s）。
- 变更文件：backend/db/database_daily_report_25_26.py。
- 调整：`create_engine` 新增 `pool_size=20`, `max_overflow=40`, `pool_timeout=60`, `pool_recycle=1800`，保持 `pool_pre_ping=True`。
- 回滚提示：如需恢复默认池配置，移除新增参数即可。
- 验证：重启后端后重复访问 `/dashboard`，确认日志不再出现 QueuePool timeout 且连接数保持在新阈值内。