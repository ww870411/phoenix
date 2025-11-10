# 2025-11-19 Dashboard 净投诉量累计
- 场景：数据看板“0.5 卡片”新增“净投诉量（件）”行，同期需要在 9 号累计卡片展示“集团汇总净投诉量”。
- 处理：`backend/services/dashboard_expression.py` 的 `_fill_cumulative_cards` 新增 `"集团汇总净投诉量" → "amount_daily_net_complaints"` 映射；原有 `_fill_summary_fold_section` 已可通过 `项目字典` 中“当日净投诉量”别名解析“净投诉量（件）”，无需额外硬编码。
- 验证要点：调用 `/api/v1/projects/daily_report_25_26/dashboard`，检查 `data["9.累计卡片"]["集团汇总净投诉量"]` 是否含 `本期/同期`；前端折叠表是否展示“净投诉量（件）”三列数据。
- 附注：Serena MCP 仅负责 Python 函数替换，Markdown（`configs/progress.md`、`backend/README.md`、`frontend/README.md`）通过 `apply_patch` 记录，回滚时恢复上述文件即可。