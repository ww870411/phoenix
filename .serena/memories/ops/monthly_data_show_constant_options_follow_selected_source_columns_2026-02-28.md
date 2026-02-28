时间：2026-02-28
主题：常量注入源字段选项与源字段复选实时一致

用户澄清：常量注入中的源字段选项要与“源字段（计划/实际口径）”中的选项一致，不只是默认值一致。

实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
  1) 新增 constantSourceColumnOptions = selectedSourceColumns
  2) 常量表格复选项改为 v-for constantSourceColumnOptions
  3) 监听 selectedSourceColumns 变化，自动裁剪每条常量的 source_columns
  4) 无可选源字段时显示提示文案

说明：
- 本轮仅前端联动逻辑改动，后端接口与提取逻辑无变更。

留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md