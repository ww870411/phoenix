时间：2026-02-28
背景：用户更正“审批进度”仅在 monthly_data_show 项目 pages 页不需要，其他项目需保留。
变更文件：
1) frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
代码变更摘要：
- 在 PageSelectView 恢复审批进度模块的 UI 与行为逻辑（状态加载、审批、取消批准、发布）。
- 新增项目级条件 isMonthlyDataShowProject（projectKey === "monthly_data_show"）。
- 新增 showWorkflowCardForProject：仅当非 monthly_data_show 时按原条件显示审批模块。
- onMounted 中仅非 monthly_data_show 调用 refreshWorkflow，避免该项目不必要请求。
结果：
- monthly_data_show 的 /pages 页面不显示审批进度。
- 其他项目页面选择页恢复审批进度模块，不再被全局移除。