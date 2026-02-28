时间：2026-02-28
主题：常量注入源字段“显示与勾选联动”修正

用户最终口径：
- 常量注入中的源字段选项要始终全量显示
- 不能因上方“源字段（计划/实际口径）”取消而消失
- 但勾选状态需联动：上方取消 -> 常量区全取消；上方重选 -> 常量区全重选

实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
  1) 常量区源字段选项恢复为 sourceColumns 全量显示
  2) watch(selectedSourceColumns) 使用增量差异同步所有常量规则 source_columns：
     - removed 字段从全部规则移除
     - added 字段加入全部规则

影响：
- 后端无改动，仅前端联动策略修正。

留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md