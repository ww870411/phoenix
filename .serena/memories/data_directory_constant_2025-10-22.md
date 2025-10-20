# 数据目录常量化 2025-10-22
- 时间：2025-10-22
- 变更：新增 `backend/config.py` 定义 `DATA_DIRECTORY`（默认 `/app/data`，可由环境变量覆盖），后端 API 模块统一引用该常量，移除对仓库内 `backend_data` 目录的硬编码。
- 影响文件：backend/config.py（新增）、backend/api/v1/daily_report_25_26.py、backend/api/v1/routes.py、backend/README.md、configs/progress.md。
- 说明：错误提示信息改为动态输出目录路径；Docker Compose 继续挂载 `./backend_data` → `/app/data`。