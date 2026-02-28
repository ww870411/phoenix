时间：2026-02-28
反馈：查询页布局过于展开；常量指标不应单独成栏；计算指标栏为空。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 布局紧凑化：关键筛选区由 span-full 回调为 span-2，复选网格列宽从 220 调整为 170，减少留白与间距。
- 指标分组改为两段：
  1) 当前指标（尾部含常量指标）
  2) 计算指标（19项）
- 常量指标并入当前指标尾部，不再单独成栏。
- 计算指标采用固定19项清单始终显示，避免空栏。
结果：
- 页面从“太开”回调为“紧凑有序”，指标结构符合最新要求。