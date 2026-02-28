时间：2026-02-28
主题：monthly_data_show 页面流程展示优化

用户反馈：步骤2在未上传前不显示，页面只见步骤1和步骤3，不美观。

已调整：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
  1) 步骤2改为常驻显示（移除 v-if 条件）。
  2) 未读取文件前显示引导文案：先上传并读取口径与字段。
  3) 三个复选分组（源字段/口径/字段）无数据时显示空态提示。
  4) 各分组“全选/全不选”在无可选项时禁用。

影响：
- 仅前端交互与展示层优化；后端接口与提取逻辑不变。

留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md