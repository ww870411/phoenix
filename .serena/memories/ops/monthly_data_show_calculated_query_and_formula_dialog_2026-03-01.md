时间：2026-03-01
主题：monthly_data_show 计算指标无法显示修复 + 公式弹窗

用户诉求：
1) 月报查询页“计算指标（19项）”无法查询显示；
2) 在“计算指标（19项）”右侧增加按钮，弹出公式说明。

根因：
- backend/projects/monthly_data_show/services/extractor.py 在提取入库阶段过滤了 19 项计算指标（不落库）；
- 原查询接口仅查 month_data_show，不做实时计算，导致计算指标为空。

实现变更：
1) 后端：backend/projects/monthly_data_show/api/workspace.py
- 新增：
  - CALCULATED_ITEM_SET
  - CALCULATED_ITEM_UNITS
  - CALCULATED_DEPENDENCY_MAP
- 新增函数：
  - _collect_required_base_items
  - _compute_calculated_indicator
  - _build_calculated_rows
  - 相关辅助：_safe_div/_normalize_calc_value/_resolve_day_count/_resolve_group_day_count
- 调整 query 主流程：
  - 选中计算指标时，自动补查依赖基础指标；
  - 查询后按维度分组实时计算计算指标，再与基础指标/平均气温合并返回。
- 调整 _fetch_compare_map：
  - 对比窗口（当前/同比/环比）下同样支持计算指标实时计算。

2) 前端：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 新增按钮：计算指标标题右侧“查看公式”；
- 新增弹窗：展示 19 项计算指标的公式与单位；
- 新增常量：calculatedFormulaRows；
- 新增样式：section-title-row、formula-dialog-*、formula-table。

留痕文件：
- configs/progress.md
- backend/README.md
- frontend/README.md

验证建议：
- 在 /projects/monthly_data_show/query-tool 仅勾选一个或多个计算指标后执行查询，确认有返回；
- 勾选同比/环比分析时，确认计算指标也参与对比；
- 点击“查看公式”按钮，确认弹窗内容与关闭交互正常。