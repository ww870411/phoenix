## 2025-11-10 仪表盘加载提示 & 填报提交反馈
- 修改文件：frontend/src/daily_report_25_26/pages/DashBoard.vue、frontend/src/daily_report_25_26/pages/DataEntryView.vue、frontend/README.md、configs/progress.md、backend/README.md。
- 主要变更：
  - DashBoard.vue 引入 `isLoading` 计数状态与顶部提示条 `dashboard-loading-hint`，所有仪表盘数据请求期间显示“数据载入中，请稍候…”，请求完成后隐藏。
  - DataEntryView.vue 新增 `isSubmitting` 状态与 `submitFeedback` 提示条，提交成功/失败分别展示绿色/红色反馈且 3.2 秒后淡出，并在组件销毁时清理定时器；提交异常时记录日志并提示错误原因。
  - README/进度记录同步更新描述，说明加载提示与提交反馈的实现与验证方式；后端 README 标注本次改动对 API 无影响。
- 回滚方式：恢复上述文件至本次改动前版本即可。