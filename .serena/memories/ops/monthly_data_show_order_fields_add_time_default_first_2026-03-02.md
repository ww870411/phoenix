时间：2026-03-02
主题：monthly_data_show 查询层次顺序新增时间并默认第一位

用户诉求：
- 数据层次顺序新增“时间”选项；
- 默认先按时间，再按口径、指标；
- 跨月查询按 26.1 -> 26.2 顺序展示每月下的口径/指标。

前端改动：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
1) layerOptions 增加 time
2) filters.orderFields 默认值改为 ['time','company','item']
3) buildPayload 的 order_fields 允许 time
4) resetFilters 同步默认值
5) 简要分析分层中当 field=time 时使用当前窗口标签作为分组键，避免空键

后端改动：backend/projects/monthly_data_show/api/workspace.py
1) _resolve_order_fields 允许 time，并将默认字段改为时间优先
2) _merge_and_sort_rows：
- 当 order_fields 包含 time 时，report_month/date 按升序
- 否则保持历史降序逻辑
3) _sort_comparison_rows 对 time 字段忽略（比较结果无月维度分列）

验证：
- python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过。

结果：
- 查询结果支持按“时间->口径->指标”展示，跨月按月份先后顺序输出。