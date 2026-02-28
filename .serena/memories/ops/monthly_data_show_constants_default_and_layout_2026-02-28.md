时间：2026-02-28
主题：monthly_data_show 常量注入默认与位置调整

用户要求：
1) 常量注入默认选中（启用）
2) 常量注入位置放在“源字段（计划/实际口径）”下方
3) 常量注入默认选中源字段与“源字段（计划/实际口径）”一致

已实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
  - 常量注入面板已移动到源字段面板下方
  - constantsEnabled 默认值改为 true
  - inspect 后若后端未给默认开关也回退为 true
  - 常量规则初始化时 source_columns 统一对齐为 default_selected_source_columns（即源字段默认选中集合）

留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md