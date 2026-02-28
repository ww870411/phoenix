时间：2026-02-28
需求：期间默认 month，类型默认 real；当无选择时不提取任何数据。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) backend/projects/monthly_data_show/api/workspace.py
3) configs/progress.md
4) backend/README.md
5) frontend/README.md
实现：
- 前端：
  - 初始化/重置时 periods 默认 month、types 默认 real（不存在则回退首项）。
  - periods 或 types 为空时：查询按钮禁用、显示提示、前端直接清空结果。
- 后端：
  - query 接口增加空选保护：periods 或 types 为空直接返回空数据。
结果：
- 默认筛选对齐 month/real，且确保空选不会返回数据。