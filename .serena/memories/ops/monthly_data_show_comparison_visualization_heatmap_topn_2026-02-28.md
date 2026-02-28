时间：2026-02-28
变更摘要：
1) monthly_data_show 查询页新增同比/环比可视化总览模块。
2) 新增交互控件：同比/环比切换、TopN 指标数量切换（10/15/20/30）。
3) 新增图形：
   - 热力图（指标×口径，颜色表示涨跌幅）
   - 波动 TopN 条形图（绝对涨跌幅排序）
4) 可视化数据来源统一复用 query-comparison 后端实时接口，避免分页样本偏差。
5) 文档留痕同步更新 progress.md、frontend/README.md、backend/README.md。
涉及文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md