时间戳：2026-02-15
任务：春节看板两张表新增末尾合计行，并将净投诉量合计显示为“-”。

前置说明：
- Serena 已执行 activate_project 与 check_onboarding_performed。
- 本次改动仅涉及前端页面渲染与计算属性，不改后端接口、数据库与配置。

变更文件清单：
1) frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

代码改动摘要：
- SpringFestivalDashboardView.vue：
  - 新增 sumRowsByField(rows, field) 统一汇总函数；
  - 新增 coalRowsWithTotal（由 coalVisibleRows 追加“合计”行）；
  - 新增 complaintRowsWithTotal（由 complaintVisibleRows 追加“合计”行）；
  - 原煤表 v-for 改为遍历 coalRowsWithTotal；
  - 投诉表 v-for 改为遍历 complaintRowsWithTotal；
  - 投诉表“净投诉量（本期/同期）”在合计行渲染为 '-'（row.isTotal 条件）。

结果：
- “当日各口径耗原煤量对比（剔除庄河改造锅炉房）”表格新增末尾“合计”行。
- “投诉量分项”表格新增末尾“合计”行。
- “净投诉量（本期）/净投诉量（同期）”合计显示“-”，避免无意义求和。