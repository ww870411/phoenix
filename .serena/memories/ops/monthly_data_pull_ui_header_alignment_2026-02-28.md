时间：2026-02-28
主题：monthly_data_pull 页面头部样式与主项目对齐

用户反馈：
- monthly_data_pull 页面缺少与其他项目一致的顶部 banner。

处理：
- 文件：frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
- 改动：
  1) 引入并渲染 AppHeader
  2) 引入并渲染 Breadcrumbs（项目选择 -> 月报导表工作台）
  3) 微调主容器内边距

结果：
- 页面顶部视觉与主项目一致，导航体验恢复统一。