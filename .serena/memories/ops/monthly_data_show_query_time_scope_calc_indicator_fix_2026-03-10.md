时间：2026-03-10
问题：monthly_data_show 查询页勾选计算指标后，结果会出现查询窗口外的 2026-01、2026-02 零值行。
最终定位：
1) 查询主口径应以 `date`（业务月份）为准，`report_month` 仅表示来源月份，不能作为默认主筛选口径。
2) 前端结果时间列与导出月份统计原先优先展示 `report_month`，会把来源月份误显示成业务月份。
3) 后端 `_build_calculated_rows` 原先按 `(company, period, type, date, report_month)` 分组，导致同一业务月份被不同来源月份拆开计算；当某个来源月份分组内基础指标不全时，会产出 0 值计算行。
处理：
- 前端 `MonthlyDataShowQueryToolView.vue`
  - 回退错误修复：`buildPayload()` 继续只传 `date_from/date_to`，不强绑 `report_month_*`。
  - 结果时间列改为优先显示 `date`，导出月份统计也改为优先使用 `date`。
- 后端 `backend/projects/monthly_data_show/api/workspace.py`
  - `_build_calculated_rows` 默认按 `date` 聚合；仅在显式传 `report_month_from/report_month_to` 时才保留 `report_month` 分组。
  - `_merge_and_sort_rows` 的时间排序改为优先使用 `date`。
- 同步更新：`configs/progress.md`、`frontend/README.md`、`backend/README.md`。
降级说明：
- Serena 不支持直接编辑 Vue / Markdown，故按规则使用 `apply_patch` 完成对应文件修改。
验证：
- `python -m py_compile backend/projects/monthly_data_show/api/workspace.py` 通过。
- `cd frontend && npm run build` 通过。
回滚：
- 恢复 `MonthlyDataShowQueryToolView.vue` 中时间列与 payload 的旧逻辑；恢复 `workspace.py` 中计算指标按 `date + report_month` 分组与旧排序逻辑。