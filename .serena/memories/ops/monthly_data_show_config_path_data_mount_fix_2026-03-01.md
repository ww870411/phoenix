时间：2026-03-01
问题：用户修改配置后，页面分组名称与顺序未完全按配置生效。
根因：后端容器读取路径指向 /app/backend_data/... 旧副本；实际挂载为 /app/data/...。
处理：
- 文件：backend/projects/monthly_data_show/services/indicator_config.py
- 配置读取改为候选路径优先级：
  1) /app/data/projects/monthly_data_show/indicator_config.json
  2) /app/backend_data/projects/monthly_data_show/indicator_config.json
验证：
- 容器内读取分组名称已是用户最新配置。
- 数据库指标与配置指标差集 missing=0（未分组补全完成）。
留痕：configs/progress.md、frontend/README.md、backend/README.md 已更新。