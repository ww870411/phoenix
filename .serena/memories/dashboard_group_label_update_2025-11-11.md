# 数据看板“集团汇总”命名统一（2025-11-11）
- 目标：将数据看板页面中所有“集团全口径”字样更新为“集团汇总”，保持配置、API 输出与前端展示一致。
- 改动：更新 `backend_data/数据结构_数据看板.json`、`backend/services/dashboard_expression.py`、`frontend/src/daily_report_25_26/pages/DashBoard.vue` 及 `DashBoard888.vue`，统一段标题、单位字典、fallback 数组与别名匹配逻辑。
- 降级说明：Serena 对 JSON/Vue/py 大文件符号写入受限，本次通过 `desktop-commander::read_file` + `apply_patch` 执行；需回滚时恢复上述文件。
- 验证：调用 `/api/v1/projects/daily_report_25_26/dashboard` 与前端仪表盘，确认公司名称均显示“集团汇总”且图例表格无残留旧称谓。